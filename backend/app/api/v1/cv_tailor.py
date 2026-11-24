"""Tailored CVs and cover letters kept per job (written by the user's chosen AI model)."""
import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.db import get_db
from app.core.deps import current_user
from app.cvtools import latexcv
from app.models import Job, JobCv, User
from app.services import fit_service as fs, llm_service as llm, tailor_service as ts
from app.services.ai_cfg import require, http_error, style_block

router = APIRouter(prefix="/me/tailor", tags=["cv"])


def _job(db: Session, jid: int) -> Job:
    j = db.scalar(select(Job).where(Job.id == jid).options(selectinload(Job.company)))
    if not j: raise HTTPException(404, "job not found")
    return j


class RunIn(BaseModel):
    consent: bool = False
    tone: str = "professional"
    extra: str = ""


def _ready(db, user, consent, what, task="tailoring"):
    cv = fs.get_cv(db, user)
    if cv is None: raise HTTPException(409, "Save your CV first (CV Studio, “Use for AI scoring”).")
    return cv, require(db, user, consent, what, task)


class FieldIn(BaseModel):
    text: str
    instruction: str = ""
    kind: str = "bullet"
    consent: bool = False


@router.post("/field", summary="AI-assist ONE field of the CV (rewrites only; new numbers or skills are refused)")
def field(body: FieldIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not body.text.strip(): raise HTTPException(400, "nothing to rewrite")
    cv, cfg = _ready(db, user, body.consent, "improve this field")
    try: new, bad = ts.rewrite_field(cfg, cv, body.text, body.instruction, body.kind)
    except llm.LlmError as e: raise http_error(e, "AI rewrite failed")
    if bad: raise HTTPException(422, "The rewrite added facts your CV does not contain (" + ", ".join(bad) + "), so it was dropped. Try a different instruction.")
    return {"text": new}


class AutoIn(BaseModel):
    on: bool = False
    stages: list[str] = ["shortlisted"]
    push_rr: bool = True
    consent: bool = False


@router.get("/auto", summary="Automatic tailoring for followed jobs: current setting")
def auto_get(user: User = Depends(current_user)): return {**ts.auto_cfg(user), "available_stages": list(ts.AUTO_STAGES)}


@router.put("/auto", summary="Turn automatic tailor-and-rebuild on or off for the stages you choose")
def auto_set(body: AutoIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.on:
        cfg = require(db, user, True, "tailor your CV", "tailoring")        # needs a chosen model
        if cfg.external and not body.consent: raise HTTPException(400, "Automatic tailoring sends your CV and each posting to your AI provider. Tick the consent box, or choose a local Ollama model.")
    return {**ts.set_auto(db, user, body.on, body.stages, body.push_rr, body.consent), "available_stages": list(ts.AUTO_STAGES)}


@router.get("/{job_id}", summary="The tailored CV kept for this job (404 when none)")
def get_one(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = ts.get(db, user, job_id)
    if not r: raise HTTPException(404, "no tailored CV for this job yet")
    return ts.view(r)


@router.post("/{job_id}", summary="Tailor the saved CV to this job with the chosen AI model")
def run(job_id: int, body: RunIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    j = _job(db, job_id); cv, cfg = _ready(db, user, body.consent, "tailor your CV")
    try: return ts.view(ts.tailor(db, user, j, cfg, cv))
    except llm.LlmError as e: raise http_error(e, "AI tailoring failed")


class RebuildIn(RunIn):
    push: bool = True


@router.post("/{job_id}/rebuild", summary="AI-tailor the CV to this job and rebuild it as a new resume in Reactive Resume")
def rebuild(job_id: int, body: RebuildIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    j = _job(db, job_id); cv, cfg = _ready(db, user, body.consent, "tailor your CV")
    try: return ts.rebuild(db, user, j, cfg, cv, body.push)
    except llm.LlmError as e: raise http_error(e, "AI tailoring failed")


@router.post("/{job_id}/cover-letter", summary="Write a cover letter for this job")
def cover(job_id: int, body: RunIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    j = _job(db, job_id); cv, cfg = _ready(db, user, body.consent, "write the cover letter")
    try: return ts.view(ts.letter(db, user, j, cfg, cv, body.tone, body.extra))
    except llm.LlmError as e: raise http_error(e, "AI cover letter failed")


class EditIn(BaseModel):
    cv: dict | None = None
    template: str | None = None
    paper: str | None = None
    cover_letter: str | None = None


@router.put("/{job_id}", summary="Save edits (CV, template, cover letter) of the tailored version")
def edit(job_id: int, body: EditIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = ts.get(db, user, job_id); _job(db, job_id)
    if body.template and body.template not in ts.TEMPLATES: raise HTTPException(400, "unknown template")
    cv = body.cv or (ts.view(r)["cv"] if r else fs.get_cv(db, user))
    if cv is None: raise HTTPException(409, "Save your CV first.")
    if body.paper and body.paper not in ("a4", "letter"): raise HTTPException(400, "unknown paper size")
    report = {**(r.report or {}), "paper": body.paper} if (r and body.paper) else None
    return ts.view(ts.save(db, user, job_id, cv, body.template, report=report, cover_letter=body.cover_letter))


@router.delete("/{job_id}", status_code=204)
def drop(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = ts.get(db, user, job_id)
    if r: db.delete(r); db.commit()


class PdfIn(BaseModel):
    mode: str = "auto"
    allow_public: bool = False


@router.post("/{job_id}/pdf", summary="Build the PDF of the tailored CV (local compiler, or a public one with consent)")
def pdf(job_id: int, body: PdfIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = ts.get(db, user, job_id)
    if not r: raise HTTPException(404, "no tailored CV for this job yet")
    if body.mode == "public" and not body.allow_public: raise HTTPException(400, "sending the CV to a public LaTeX service needs allow_public=true")
    src = ts.view(r)["latex"]
    if not latexcv.is_safe(src): raise HTTPException(400, "LaTeX contains disallowed commands")
    out = latexcv.compile_any(src, body.mode if body.mode in ("local", "public", "auto") else "auto")
    if not out["pdf"]: raise HTTPException(422, {"error": out["error"] or "compilation failed", "local_available": out["local_available"]})
    return {"pdf_b64": base64.b64encode(out["pdf"]).decode(), "engine": out["engine"], "bytes": len(out["pdf"])}
