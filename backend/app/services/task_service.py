import datetime as dt, time
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.models import Task


def enqueue(db: Session, kind: str, payload: dict | None = None, dedupe: bool = True) -> Task:
    """Queue a task; if the same kind is already queued/running, return that one instead (idempotent triggers)."""
    if dedupe:
        t = db.scalar(select(Task).where(Task.kind == kind, Task.status.in_(("queued", "running", "paused"))).order_by(Task.id.desc()))
        if t and (payload or {}) == (t.payload or {}): return t
    t = Task(kind=kind, payload=payload or {}); db.add(t); db.commit(); return t


def claim(db: Session) -> Task | None:
    """Atomically take the oldest queued task (SKIP LOCKED: safe with several workers)."""
    row = db.execute(text("""UPDATE tasks SET status='running', started_at=now() WHERE id = (
        SELECT id FROM tasks WHERE status='queued' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id""")).first()
    db.commit()
    return db.get(Task, row[0]) if row else None


STOPPED = "stopped by operator"


class TaskStopped(Exception):
    pass


def progress(db: Session, t: Task, **kw):
    """Save progress, then obey the operator: wait while the task is paused, stop when it was stopped.
    Every long task reports progress, so this is where pause / resume / stop take effect (between steps, never in the middle of one)."""
    t.progress = {**(t.progress or {}), **kw}; db.commit()
    checkpoint(db, t)


def checkpoint(db: Session, t: Task):
    db.refresh(t)
    while t.status == "paused":
        time.sleep(2); db.refresh(t)
    if t.status != "running": raise TaskStopped(STOPPED)


def finish(db: Session, t: Task, error: str | None = None):
    db.refresh(t)
    if t.error == STOPPED:                                                     # stopped by someone: keep that, only stamp the end
        t.finished_at = t.finished_at or dt.datetime.now(dt.timezone.utc); db.commit(); return
    t.status = "failed" if error else "done"; t.error = error; t.finished_at = dt.datetime.now(dt.timezone.utc); db.commit()


_gate: dict[int, tuple[float, str]] = {}


def gate(task_id: int):
    """For work spread over threads: before each item, wait while the task is paused and stop when it was stopped.
    Reads the status at most every 2 seconds (shared by all threads), so it costs almost nothing."""
    from app.core.db import SessionLocal
    while True:
        at, st = _gate.get(task_id, (0.0, "running"))
        if time.time() - at > 2:
            with SessionLocal() as s: st = (s.get(Task, task_id) or Task(status="failed")).status
            _gate[task_id] = (time.time(), st)
        if st == "paused": time.sleep(1); continue
        if st != "running": raise TaskStopped(STOPPED)
        return
