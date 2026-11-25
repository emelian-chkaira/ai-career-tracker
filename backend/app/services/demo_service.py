"""Public online demo (CAREERS_DEMO_MODE=true): a visitor gets a private guest account in one click, with a few sample applications.
Guests are deleted after CAREERS_DEMO_GUEST_DAYS days so a free database does not fill up."""
import datetime as dt, secrets
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.models import User, Job
from app.services import tracking_service as ts
from app.services.auth_service import DEFAULT_PROFILE

DOMAIN = "@guest.demo.example.com"          # reserved example domain: no mail can ever reach it
SAMPLES = [("shortlisted", "Sample: saved to look at later"), ("applied", "Sample: sent the tailored CV"), ("interview", "Sample: technical interview booked")]


def purge_old(db: Session) -> int:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=settings.demo_guest_days)
    n = db.execute(delete(User).where(User.email.like("guest-%" + DOMAIN), User.created_at < cutoff)).rowcount   # their rows cascade
    db.commit(); return n


def create_guest(db: Session) -> User:
    purge_old(db)
    u = User(email=f"guest-{secrets.token_hex(6)}{DOMAIN}", password_hash=security.hash_password(secrets.token_urlsafe(24)), name="Guest",
             role="user",                                                       # never admin, even on an empty database
             email_verified_at=dt.datetime.now(dt.timezone.utc), profile={**DEFAULT_PROFILE, "onboarded": True, "sectors": ["tech"]})   # same field a signed-out visitor sees
    db.add(u); db.flush()
    _sample_pipeline(db, u)
    db.commit(); return u


def _sample_pipeline(db: Session, u: User) -> None:
    rows = db.execute(select(Job.id, Job.company_id).where(Job.title.ilike("%software%engineer%"), Job.status == "open").order_by(Job.id).limit(200)).all()
    picked = list({company: job for job, company in rows}.values())[:len(SAMPLES)]     # one job per employer
    for job_id, (stage, note) in zip(picked, SAMPLES):
        uj = ts.change_stage(db, u.id, job_id, "applied" if stage == "interview" else stage)
        if stage == "interview": db.flush(); uj = ts.change_stage(db, u.id, job_id, stage, uj=uj)
        uj.notes = note
