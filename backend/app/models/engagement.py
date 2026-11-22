import uuid, datetime as dt
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class UserJob(Base):
    """Per-user pipeline state for a job (replaces the old global stage/notes columns)."""
    __tablename__ = "user_jobs"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    stage: Mapped[str] = mapped_column(String(20), default="shortlisted", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), index=True)     # when to chase / prepare next
    follow_up_note: Mapped[str | None] = mapped_column(String(200))
    contact: Mapped[str | None] = mapped_column(String(200))                                          # recruiter / hiring manager
    offer_details: Mapped[str | None] = mapped_column(String(200))                                    # e.g. "EUR 4,800 / month, 30 days leave"
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SavedSearch(Base):
    """A saved query (+filters). With alert_frequency != 'off' the worker notifies the user about new matching jobs."""
    __tablename__ = "saved_searches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    params: Mapped[dict] = mapped_column(JSONB, default=dict)               # same keys as GET /jobs/search
    alert_frequency: Mapped[str] = mapped_column(String(10), default="daily")   # off | instant | daily | weekly
    channel_email: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="alert")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)                 # {saved_search_id, job_ids:[...]}
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    __table_args__ = (Index("ix_notif_user_unread", "user_id", "read"),)


class EmailOutbox(Base):
    """Emails are queued here and sent by the worker (SMTP when configured, otherwise kept for inspection)."""
    __tablename__ = "email_outbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    to_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body_text: Mapped[str] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)   # pending | sent | failed | skipped
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class Task(Base):
    """DB-backed job queue: the API enqueues, the worker process executes (scan, discovery, live search, embeddings…)."""
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="queued", index=True)    # queued | running | done | failed
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class JobEvent(Base):
    """One entry in a job's timeline: stage changes, notes, interviews, e-mails, follow-ups."""
    __tablename__ = "job_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))                 # stage | note | interview | email | offer | follow_up
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())      # when it happened (or is scheduled)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)       # {from, to} for stages, {mail_event_id}, ...
    __table_args__ = (Index("ix_job_events_user_job_at", "user_id", "job_id", "at"),)


class UserCvDraft(Base):
    """CV Studio's working copy for this user (structured CV, LaTeX source, layout), encrypted. Keeps every account's CV on the server
    instead of in the browser, so a second account on the same computer never sees it."""
    __tablename__ = "user_cv_drafts"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data_enc: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserCv(Base):
    """The user's CV kept server-side (encrypted) so AI fit scoring and tailoring can use it. Optional: the CV tools also work without it."""
    __tablename__ = "user_cvs"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data_enc: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobScore(Base):
    """AI assessment of one job against the user's CV. Cached by a hash of (CV, posting, model)."""
    __tablename__ = "job_scores"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, index=True)       # 0..100
    verdict: Mapped[str] = mapped_column(String(16))              # strong | good | stretch | weak
    reason: Mapped[str] = mapped_column(Text)
    strengths: Mapped[list] = mapped_column(JSONB, default=list)
    gaps: Mapped[list] = mapped_column(JSONB, default=list)
    flags: Mapped[list] = mapped_column(JSONB, default=list)      # deal-breakers: Dutch required, visa, onsite far away ...
    summary: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100), default="")
    basis_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobCv(Base):
    """A CV tailored for one job (kept so the user can re-open, edit and export it)."""
    __tablename__ = "job_cvs"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    data_enc: Mapped[str] = mapped_column(Text)
    template: Mapped[str] = mapped_column(String(20), default="classic")
    report: Mapped[dict] = mapped_column(JSONB, default=dict)     # keyword coverage before/after, changes, fact check
    cover_letter: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100), default="")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobChatMessage(Base):
    """One message of the per-job assistant conversation."""
    __tablename__ = "job_chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(10))                 # user | assistant
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100))
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_job_chat_user_job_at", "user_id", "job_id", "at"),)


class JobTask(Base):
    """A to-do attached to a job in the user's pipeline ("send portfolio", "prepare system design") with an optional due date."""
    __tablename__ = "job_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    due_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
