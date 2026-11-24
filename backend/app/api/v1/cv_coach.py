"""Chat with the AI to add missing skills, bullets or projects to the stored CV (every addition is reviewed by the user)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.db import get_db
from app.core.deps import current_user
from app.models import Job, User
from app.services import coach_service as cs, fit_service as fs, llm_service as llm
from app.services.ai_cfg import require, http_error

router = APIRouter(prefix="/me/cv-coach", tags=["cv-coach"])


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    job_id: int | None = None
    history: list[dict] = Field(default_factory=list, max_length=20)
    consent: bool = False


@router.post("", summary="Tell the AI what you can do; get CV additions to review")
def chat(body: ChatIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = fs.get_cv(db, user)
    if cv is None: raise HTTPException(400, "Save your CV for AI first (CV Studio).")
    cfg = require(db, user, body.consent, "Your CV and what you tell the coach", "coach")
    job = db.scalar(select(Job).where(Job.id == body.job_id).options(selectinload(Job.company))) if body.job_id else None
    try: return cs.chat(db, user, job, cfg, cv, body.history, body.message)
    except llm.LlmError as e: raise http_error(e, "The CV coach could not answer")


@router.get("/gaps/{job_id}", summary="What this posting asks for that your CV does not show (no AI call)")
def gaps(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = fs.get_cv(db, user) or {}
    job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.company)))
    if not job: raise HTTPException(404, "job not found")
    return {"missing": cs.missing_for(cv, job)}


class ApplyIn(BaseModel):
    proposals: list[dict] = Field(..., min_length=1, max_length=10)


@router.post("/apply", summary="Write the accepted (and edited) additions into the stored CV")
def apply(body: ApplyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = fs.get_cv(db, user)
    if cv is None: raise HTTPException(400, "no CV saved")
    new = cs.apply(cv, body.proposals)
    try: fs.put_cv(db, user, new)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"ok": True, "skills": len(new.get("skills") or []), "projects": len(new.get("projects") or [])}
