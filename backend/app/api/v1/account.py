"""Your data and your sessions: export everything we hold, delete the account, see and end signed-in devices."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import current_user
from app.models import (User, RefreshToken, UserJob, JobEvent, JobTask, SavedSearch, MailEvent, MailAccount, JobChatMessage, JobScore, Notification, UserAiSettings)
from app.services import fit_service as fs

router = APIRouter(prefix="/me", tags=["account"])
iso = lambda v: v.isoformat() if isinstance(v, (dt.datetime, dt.date)) else v
row = lambda r, cols: {c: iso(getattr(r, c)) for c in cols}


@router.get("/export", summary="Download everything we store about you as JSON (no passwords, tokens or API keys)")
def export(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = lambda m: db.scalars(select(m).where(m.user_id == user.id)).all()
    ai = db.get(UserAiSettings, user.id)
    data = {
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "account": {"email": user.email, "name": user.name, "created_at": iso(user.created_at), "profile": user.profile},
        "cv": fs.get_cv(db, user), "cv_draft": fs.get_draft(db, user),
        "ai_settings": {"provider": ai.provider, "model": ai.model, "base_url": ai.base_url, "task_models": ai.task_models, "style": ai.style} if ai else None,
        "pipeline": [row(r, ("job_id", "stage", "notes", "applied_at", "follow_up_at", "follow_up_note", "contact", "offer_details")) for r in q(UserJob)],
        "timeline": [row(r, ("job_id", "kind", "title", "body", "at", "meta")) for r in q(JobEvent)],
        "tasks": [row(r, ("job_id", "title", "due_at", "done_at")) for r in q(JobTask)],
        "saved_searches": [row(r, ("name", "params", "alert_frequency")) for r in q(SavedSearch)],
        "ai_scores": [row(r, ("job_id", "score", "verdict", "reason", "strengths", "gaps", "flags")) for r in q(JobScore)],
        "assistant_messages": [row(r, ("job_id", "role", "content", "at")) for r in q(JobChatMessage)],
        "mail_events": [row(r, ("subject", "sender", "received_at", "category", "company", "role", "summary", "status")) for r in q(MailEvent)],
        "mail_accounts": [row(r, ("label", "username", "days_back", "last_sync_at")) for r in q(MailAccount)],
        "notifications": [row(r, ("kind", "title", "body", "created_at")) for r in q(Notification)],
    }
    response.headers["Content-Disposition"] = 'attachment; filename="career-tracker-export.json"'; return data


class DeleteIn(BaseModel):
    confirm_email: str


@router.post("/account/delete", status_code=204, summary="Permanently delete your account and everything attached to it")
def delete_account(body: DeleteIn, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.confirm_email.strip().lower() != user.email.lower(): raise HTTPException(400, "type your e-mail address exactly to confirm")
    db.execute(delete(User).where(User.id == user.id)); db.commit()            # every user-owned table cascades
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/sessions", summary="Signed-in devices (active refresh tokens)")
def sessions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = dt.datetime.now(dt.timezone.utc); fam: dict = {}
    for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False), RefreshToken.expires_at > now).order_by(RefreshToken.created_at)):
        f = fam.setdefault(str(t.family), {"id": str(t.family), "started": t.created_at, "last_active": t.created_at, "expires_at": t.expires_at})
        f["last_active"] = max(f["last_active"], t.created_at); f["expires_at"] = max(f["expires_at"], t.expires_at)
    return sorted(fam.values(), key=lambda f: f["last_active"], reverse=True)


@router.delete("/sessions/{family}", status_code=204)
def end_session(family: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.family == family).values(revoked=True)); db.commit()


@router.delete("/sessions", status_code=204, summary="Sign out everywhere")
def end_all(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)); db.commit(); response.delete_cookie("refresh_token", path="/api/v1/auth")
