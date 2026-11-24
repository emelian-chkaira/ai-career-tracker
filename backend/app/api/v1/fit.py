"""The user's stored CV and AI fit scores (how well each job matches that CV)."""
import threading
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.db import get_db
from app.core.deps import current_user
from app.models import User, Job, Task
from app.services import docs_service as ds, fit_service as fs, llm_service as llm, task_service
from app.services.ai_cfg import require, http_error

router = APIRouter(prefix="/me", tags=["fit"])


# ------------------------------------------------------------------ stored CV
@router.get("/cv", summary="The CV kept on the server for AI features (404 when none)")
def get_cv(user: User = Depends(current_user), db: Session = Depends(get_db)):
    cv = fs.get_cv(db, user)
    if cv is None: raise HTTPException(404, "no CV saved")
    return {"cv": cv, "updated_at": db.get(fs.UserCv, user.id).updated_at}


class CvIn(BaseModel):
    cv: dict


@router.put("/cv", summary="Save the CV (encrypted at rest) so fit scoring and tailoring can use it")
def put_cv(body: CvIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not (body.cv.get("experience") or body.cv.get("skills") or body.cv.get("skill_groups") or body.cv.get("summary")): raise HTTPException(400, "the CV looks empty")
    try: r = fs.put_cv(db, user, body.cv)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"ok": True, "updated_at": r.updated_at}


@router.delete("/cv", status_code=204)
def delete_cv(user: User = Depends(current_user), db: Session = Depends(get_db)): fs.delete_cv(db, user)


class DraftIn(BaseModel):
    draft: dict                       # {cv, latex, source, template, paper}


@router.get("/cv/draft", summary="CV Studio's working copy for this account (404 when none)")
def get_draft(user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = fs.get_draft(db, user)
    if d is None: raise HTTPException(404, "no draft")
    return {"draft": d, "updated_at": db.get(fs.UserCvDraft, user.id).updated_at}


@router.put("/cv/draft", summary="Save CV Studio's working copy (encrypted, per account)")
def put_draft(body: DraftIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: r = fs.put_draft(db, user, body.draft)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"ok": True, "updated_at": r.updated_at}


@router.delete("/cv/draft", status_code=204)
def delete_draft(user: User = Depends(current_user), db: Session = Depends(get_db)): fs.delete_draft(db, user)


# ------------------------------------------------------------------ scores
def _need_cv(db: Session, user: User, cv_id: int | None = None) -> tuple[dict, str | None]:
    try: cv, name = ds.cv_for_scoring(db, user, cv_id)
    except ds.DocError as e: raise HTTPException(404, str(e))
    if not cv: raise HTTPException(409, "Save your CV first (CV Studio, “Use for AI scoring”).")
    return cv, name


def _job(db: Session, jid: int) -> Job:
    j = db.scalar(select(Job).where(Job.id == jid).options(selectinload(Job.company)))
    if not j: raise HTTPException(404, "job not found")
    return j


class ScoreOne(BaseModel):
    consent: bool = False
    force: bool = False
    cv_id: int | None = None      # a CV of the CV Studio library; none = the default one


@router.get("/fit/{job_id}", summary="The cached score of one job (404 when not scored yet)")
def get_score(job_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = fs.scores_for(db, user.id, [job_id]).get(job_id)
    if not r: raise HTTPException(404, "not scored yet")
    return fs.out(r)


@router.post("/fit/{job_id}", summary="Score one job against the saved CV (waits for the model, usually a few seconds)")
def score_one(job_id: int, body: ScoreOne, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cv, name = _need_cv(db, user, body.cv_id); cfg = require(db, user, body.consent, "Your CV and the job posting", "scoring"); j = _job(db, job_id)
    try: return fs.out(fs.score_job(db, user, j, cfg, cv, force=body.force, cv_name=name))
    except llm.LlmError as e: raise http_error(e, "The AI model failed")


class ScoreMany(BaseModel):
    job_ids: list[int] = Field(min_length=1, max_length=60)
    consent: bool = False
    cv_id: int | None = None


def _run(tid: int):
    import logging
    from app.core.db import SessionLocal
    with SessionLocal() as db:
        t = db.get(Task, tid); p = t.payload or {}
        try:
            user = db.get(User, __import__("uuid").UUID(p["user_id"])); cfg = require(db, user, True, "x", "scoring"); cv, cv_name = ds.cv_for_scoring(db, user, p.get("cv_id")); cv = cv or {}
            ids = p["job_ids"]; st = dict(total=len(ids), done=0, scored=0, cached=0, failed=0)
            task_service.progress(db, t, **st); fails = 0
            known = fs.scores_for(db, user.id, ids)
            for jid in ids:
                j = db.scalar(select(Job).where(Job.id == jid).options(selectinload(Job.company)))
                if not j: st["done"] += 1; continue
                before = known[jid].created_at if jid in known else None
                try:
                    r = fs.score_job(db, user, j, cfg, cv, cv_name=cv_name)
                    st["cached" if before is not None and before == r.created_at else "scored"] += 1; fails = 0
                except llm.LlmError as e:
                    st["failed"] += 1; st["error"] = str(e)[:200]; fails += 1
                    if e.kind == "config" or fails >= 4: raise RuntimeError(f"The AI model keeps failing: {e}")
                st["done"] += 1; task_service.progress(db, t, **st)
            task_service.finish(db, t)
        except Exception as e:
            db.rollback(); logging.getLogger("fit").exception("fit batch failed"); task_service.finish(db, db.get(Task, tid), str(e)[:300])


@router.post("/fit-batch", status_code=202, summary="Score several jobs in the background (cached ones are skipped)")
def score_many(body: ScoreMany, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _need_cv(db, user, body.cv_id); require(db, user, body.consent, "Your CV and the job postings", "scoring")
    ids = list(dict.fromkeys(body.job_ids))
    t = Task(kind="fit_score", status="running", payload={"user_id": str(user.id), "job_ids": ids, "cv_id": body.cv_id}); db.add(t); db.commit()
    threading.Thread(target=_run, args=(t.id,), daemon=True).start(); return {"task_id": t.id}


@router.get("/fit-batch/{tid}")
def batch_status(tid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Task, tid)
    if not t or t.kind != "fit_score" or (t.payload or {}).get("user_id") != str(user.id): raise HTTPException(404)
    return {"id": t.id, "status": t.status, "progress": t.progress, "error": t.error}
