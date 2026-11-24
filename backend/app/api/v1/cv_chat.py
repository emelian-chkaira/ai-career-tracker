"""CV Studio chat: ask the AI to change the CV or the cover letter; nothing is saved here, the studio shows the result for review."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.db import get_db
from app.core.deps import current_user
from app.models import Job, User
from app.services import chat_service as cs, docs_service as ds, fit_service as fs, llm_service as llm
from app.services.ai_cfg import require, http_error

router = APIRouter(prefix="/me/cv-chat", tags=["cv-chat"])


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    target: str = Field("cv", pattern="^(cv|cover)$")
    cv: dict
    letter: str = Field("", max_length=8000)
    job_id: int | None = None
    history: list[dict] = Field(default_factory=list, max_length=20)
    consent: bool = False


def _job(db: Session, jid: int | None) -> Job | None:
    if jid is None: return None
    j = db.scalar(select(Job).where(Job.id == jid).options(selectinload(Job.company)))
    if not j: raise HTTPException(404, "job not found")
    return j


@router.post("", summary="Ask the AI to change your CV or cover letter; returns a reviewable result")
def chat(body: ChatIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not (body.cv.get("experience") or body.cv.get("skills") or body.cv.get("summary")): raise HTTPException(400, "Open a CV first.")
    cfg = require(db, user, body.consent, "Your CV, the job posting and what you type", "coach"); job = _job(db, body.job_id)
    try:
        if body.target == "cover": return cs.chat_cover(user, job, cfg, body.cv, body.letter, body.history, body.message, ds.letter_examples(db, user))
        return cs.chat_cv(user, job, cfg, body.cv, body.history, body.message)
    except llm.LlmError as e: raise http_error(e, "The assistant could not answer")


class SuggestIn(BaseModel):
    cv: dict


@router.post("/suggest/{job_id}", summary="Suggested changes for one job (no AI call)")
def suggest(job_id: int, body: SuggestIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    job = _job(db, job_id); assert job
    score = fs.scores_for(db, user.id, [job_id]).get(job_id)
    return {"job": {"id": job.id, "title": job.title, "company": job.company.name}, "suggestions": cs.suggestions(body.cv, job, fs.out(score))}
