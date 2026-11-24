"""Everything that belongs to the signed-in user: pipeline, saved searches (alerts), notifications."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session, selectinload
from app.core.db import get_db
from app.core.deps import current_user
from app.models import User, UserJob, SavedSearch, Notification, Job
from app.services import jobs_service, search_service as ss, alert_service, tracking_service as ts, tailor_service

router = APIRouter(prefix="/me", tags=["me"])
STAGES = ["shortlisted", "applied", "screening", "assessment", "team_match", "interview", "final_round", "offer", "accepted", "rejected", "withdrawn", "skipped"]


# ---------- pipeline
class StageIn(BaseModel):
    stage: str | None = None
    notes: str | None = None


@router.get("/pipeline")
def pipeline(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.execute(select(UserJob, Job).join(Job, Job.id == UserJob.job_id).where(UserJob.user_id == user.id).options(selectinload(Job.company), selectinload(Job.skills)).order_by(UserJob.updated_at.desc())).all()
    out = []; from app.services import fit_service as fs; ai = fs.scores_for(db, user.id, [j.id for _, j in rows])
    for uj, j in rows:
        o = jobs_service.to_out(j, user, {j.id: uj.stage}, ai=fs.out(ai.get(j.id))).model_dump(mode="json"); o.update(ts.view(uj)); o["updated_at"] = uj.updated_at; out.append(o)
    return {"stages": STAGES, "items": out}


@router.put("/jobs/{job_id}")
def set_stage(job_id: int, body: StageIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.stage and body.stage not in STAGES: raise HTTPException(400, "bad stage")
    if not db.get(Job, job_id): raise HTTPException(404, "job not found")
    uj = db.get(UserJob, (user.id, job_id)) or UserJob(user_id=user.id, job_id=job_id, stage=None)
    ts.change_stage(db, user.id, job_id, body.stage or uj.stage or "shortlisted", uj=uj)
    if body.notes is not None: uj.notes = body.notes
    db.commit()
    try: tailor_service.queue_if_auto(db, user, job_id, uj.stage)          # followed job: tailor + rebuild in the background when the user opted in
    except Exception: db.rollback()
    return {"job_id": job_id, **ts.view(uj)}


@router.delete("/jobs/{job_id}", status_code=204)
def remove_from_pipeline(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.execute(delete(UserJob).where(UserJob.user_id == user.id, UserJob.job_id == job_id)); db.commit()


# ---------- saved searches / alerts
class SearchIn(BaseModel):
    name: str
    params: dict
    alert_frequency: str = "daily"
    channel_email: bool = True


def _ss_out(s: SavedSearch): return {"id": s.id, "name": s.name, "params": s.params, "alert_frequency": s.alert_frequency, "channel_email": s.channel_email, "last_run_at": s.last_run_at, "created_at": s.created_at}


@router.get("/searches")
def list_searches(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [_ss_out(s) for s in db.scalars(select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.id.desc()))]


def _validate(params):
    try: ss.SearchParams(**params)
    except Exception as e: raise HTTPException(422, f"invalid search params: {str(e)[:200]}")


@router.post("/searches", status_code=201)
def create_search(body: SearchIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.alert_frequency not in ("off", "instant", "daily", "weekly"): raise HTTPException(400, "bad frequency")
    if db.scalar(select(func.count()).select_from(SavedSearch).where(SavedSearch.user_id == user.id)) >= 25: raise HTTPException(400, "limit of 25 saved searches reached")
    _validate(body.params)
    s = SavedSearch(user_id=user.id, name=body.name.strip()[:120] or "Saved search", params=body.params, alert_frequency=body.alert_frequency, channel_email=body.channel_email, last_run_at=dt.datetime.now(dt.timezone.utc))
    db.add(s); db.commit(); return _ss_out(s)


@router.patch("/searches/{sid}")
def update_search(sid: int, body: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(SavedSearch, sid)
    if not s or s.user_id != user.id: raise HTTPException(404)
    for k in ("name", "alert_frequency", "channel_email", "params"):
        if k in body:
            if k == "alert_frequency" and body[k] not in ("off", "instant", "daily", "weekly"): raise HTTPException(400, "bad frequency")
            if k == "params": _validate(body[k])
            setattr(s, k, body[k])
    db.commit(); return _ss_out(s)


@router.delete("/searches/{sid}", status_code=204)
def delete_search(sid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(SavedSearch, sid)
    if not s or s.user_id != user.id: raise HTTPException(404)
    db.delete(s); db.commit()


@router.get("/searches/{sid}/preview")
def preview_search(sid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(SavedSearch, sid)
    if not s or s.user_id != user.id: raise HTTPException(404)
    return jobs_service.search(db, ss.SearchParams(**{**s.params, "limit": 10}), user)


# ---------- notifications
@router.get("/notifications")
def notifications(unread: bool = False, limit: int = Query(30, le=100), db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(limit)
    if unread: q = q.where(Notification.read.is_(False))
    n_unread = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read.is_(False)))
    return {"unread": n_unread, "items": [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "data": n.data, "read": n.read, "created_at": n.created_at} for n in db.scalars(q)]}


@router.post("/notifications/{nid}/read", status_code=204)
def mark_read(nid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = db.get(Notification, nid)
    if n and n.user_id == user.id: n.read = True; db.commit()


@router.post("/notifications/read-all", status_code=204)
def mark_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.read.is_(False)).update({"read": True}); db.commit()


# ---------- follow a company (a saved search on one employer, with alerts)
@router.get("/following")
def following(db: Session = Depends(get_db), user: User = Depends(current_user)):
    from app.models import Company
    out = []
    for s in db.scalars(select(SavedSearch).where(SavedSearch.user_id == user.id, SavedSearch.params["follow_company"].astext.is_not(None))):
        c = db.get(Company, int(s.params["follow_company"])); 
        if c: out.append({"company_id": c.id, "name": c.name, "search_id": s.id, "alert_frequency": s.alert_frequency})
    return out


@router.post("/following/{company_id}", status_code=201, summary="Get an alert whenever this employer posts a new job")
def follow(company_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    from app.models import Company
    c = db.get(Company, company_id)
    if not c: raise HTTPException(404, "company not found")
    for s in db.scalars(select(SavedSearch).where(SavedSearch.user_id == user.id)):
        if (s.params or {}).get("follow_company") == company_id: return {"search_id": s.id}
    s = SavedSearch(user_id=user.id, name=f"New jobs at {c.name}", params={"company_id": company_id, "follow_company": company_id, "category": None}, alert_frequency="daily"); db.add(s); db.commit(); return {"search_id": s.id}


@router.delete("/following/{company_id}", status_code=204)
def unfollow(company_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    for s in db.scalars(select(SavedSearch).where(SavedSearch.user_id == user.id)):
        if (s.params or {}).get("follow_company") == company_id: db.delete(s)
    db.commit()
