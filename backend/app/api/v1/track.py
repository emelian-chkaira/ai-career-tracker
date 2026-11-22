"""Application tracking: timeline, follow-ups, contact/offer details and funnel statistics."""
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import current_user
from app.models import Job, JobEvent, JobTask, User, UserJob
from app.services import tracking_service as ts

router = APIRouter(prefix="/me", tags=["tracking"])


def _uj(db, user, job_id) -> UserJob:
    uj = db.get(UserJob, (user.id, job_id))
    if not uj: raise HTTPException(404, "this job is not in your pipeline yet")
    return uj


class TrackIn(BaseModel):
    notes: str | None = Field(None, max_length=8000)
    applied_at: dt.datetime | None = None
    follow_up_at: dt.datetime | None = None
    clear_follow_up: bool = False
    follow_up_note: str | None = Field(None, max_length=200)
    contact: str | None = Field(None, max_length=200)
    offer_details: str | None = Field(None, max_length=200)


class EventIn(BaseModel):
    kind: str = "note"
    title: str = Field(..., min_length=1, max_length=200)
    body: str | None = Field(None, max_length=4000)
    at: dt.datetime | None = None


@router.get("/jobs/{job_id}/track")
def get_track(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    uj = db.get(UserJob, (user.id, job_id))
    return {"track": ts.view(uj) if uj else None, "events": ts.timeline(db, user.id, job_id)}


@router.patch("/jobs/{job_id}/track")
def patch_track(job_id: int, body: TrackIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    uj = _uj(db, user, job_id); d = body.model_dump(exclude_unset=True)
    for k in ("notes", "applied_at", "follow_up_note", "contact", "offer_details"):
        if k in d: setattr(uj, k, d[k])
    if body.clear_follow_up: uj.follow_up_at = None; uj.follow_up_note = None
    elif body.follow_up_at: uj.follow_up_at = body.follow_up_at; ts.log(db, user.id, job_id, "follow_up", "Follow-up scheduled", uj.follow_up_note, at=body.follow_up_at)
    db.add(uj); db.commit(); return ts.view(uj)


@router.post("/jobs/{job_id}/events", status_code=201)
def add_event(job_id: int, body: EventIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.kind not in ts.KINDS: raise HTTPException(400, f"kind must be one of {', '.join(ts.KINDS)}")
    _uj(db, user, job_id); e = ts.log(db, user.id, job_id, body.kind, body.title, body.body, body.at); db.commit(); return ts.event_out(e)


@router.delete("/jobs/{job_id}/events/{eid}", status_code=204)
def del_event(job_id: int, eid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    e = db.get(JobEvent, eid)
    if not e or e.user_id != user.id or e.job_id != job_id: raise HTTPException(404, "event not found")
    if e.kind == "stage": raise HTTPException(400, "stage history cannot be deleted")
    db.delete(e); db.commit()


@router.get("/stats")
def my_stats(days: int = Query(30, ge=7, le=180), db: Session = Depends(get_db), user: User = Depends(current_user)): return ts.stats(db, user.id, days)


@router.get("/follow-ups")
def my_follow_ups(days: int = 14, db: Session = Depends(get_db), user: User = Depends(current_user)): return ts.follow_ups(db, user.id, min(max(days, 1), 90))


# ------------------------------------------------------------------ tasks per job
class TaskIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_at: dt.datetime | None = None


class TaskPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    due_at: dt.datetime | None = None
    done: bool | None = None


def _task_out(t: JobTask) -> dict: return {"id": t.id, "job_id": t.job_id, "title": t.title, "due_at": t.due_at, "done": t.done_at is not None, "done_at": t.done_at}


@router.get("/jobs/{job_id}/tasks")
def list_tasks(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(JobTask).where(JobTask.user_id == user.id, JobTask.job_id == job_id).order_by(JobTask.done_at.is_not(None), JobTask.due_at.is_(None), JobTask.due_at, JobTask.id))
    return [_task_out(t) for t in rows]


@router.post("/jobs/{job_id}/tasks", status_code=201)
def add_task(job_id: int, body: TaskIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _uj(db, user, job_id)
    if db.scalar(select(func.count()).select_from(JobTask).where(JobTask.user_id == user.id, JobTask.job_id == job_id)) >= 50: raise HTTPException(400, "too many tasks on this job")
    t = JobTask(user_id=user.id, job_id=job_id, title=body.title.strip(), due_at=body.due_at); db.add(t); db.commit(); return _task_out(t)


@router.patch("/tasks/{tid}")
def patch_task(tid: int, body: TaskPatch, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = db.get(JobTask, tid)
    if not t or t.user_id != user.id: raise HTTPException(404, "task not found")
    d = body.model_dump(exclude_unset=True)
    if "title" in d and d["title"]: t.title = d["title"].strip()
    if "due_at" in d: t.due_at = d["due_at"]
    if "done" in d: t.done_at = dt.datetime.now(dt.timezone.utc) if d["done"] else None
    db.commit(); return _task_out(t)


@router.delete("/tasks/{tid}", status_code=204)
def delete_task(tid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = db.get(JobTask, tid)
    if not t or t.user_id != user.id: raise HTTPException(404, "task not found")
    db.delete(t); db.commit()


@router.get("/tasks", summary="Open tasks across all jobs, soonest first")
def all_tasks(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.execute(select(JobTask, Job).join(Job, Job.id == JobTask.job_id).where(JobTask.user_id == user.id, JobTask.done_at.is_(None)).order_by(JobTask.due_at.is_(None), JobTask.due_at).limit(100)).all()
    return [_task_out(t) | {"job_title": j.title, "company": j.company.name} for t, j in rows]
