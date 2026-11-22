"""Per-job assistant chat."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.db import get_db
from app.core.deps import current_user
from app.models import Job, User
from app.services import assistant_service as sv, llm_service as llm
from app.services.ai_cfg import require, http_error

router = APIRouter(prefix="/me/assistant", tags=["assistant"])


def _job(db: Session, jid: int) -> Job:
    j = db.scalar(select(Job).where(Job.id == jid).options(selectinload(Job.company)))
    if not j: raise HTTPException(404, "job not found")
    return j


class AskIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=sv.MAX_MESSAGE)
    consent: bool = False
    cv: bool = True
    notes: bool = True
    emails: bool = True


@router.get("/{job_id}", summary="The conversation about this job")
def get_chat(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _job(db, job_id); return {"messages": [sv.out(m) for m in sv.history(db, user, job_id)]}


@router.post("/{job_id}", summary="Ask the assistant something about this job")
def ask(job_id: int, body: AskIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    j = _job(db, job_id); cfg = require(db, user, body.consent, "Your question, the job posting and the context you selected", "assistant")
    try: u, a = sv.ask(db, user, j, cfg, body.message, {"cv": body.cv, "notes": body.notes, "emails": body.emails})
    except llm.LlmError as e: raise http_error(e, "The assistant could not answer")
    return {"user": sv.out(u), "assistant": sv.out(a)}


@router.delete("/{job_id}", status_code=204)
def clear(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)): sv.clear(db, user, job_id)
