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


# Which tasks must not run at the same time (only matters with more than one worker).
SITES = {"scan_all", "scan_unscanned", "scan_due", "internships"}                     # each walks the same employers' pages
HEAVY = SITES | {"board_search", "discover", "discover_country", "census", "broad_sources", "dedupe_jobs", "sponsors_refresh"}   # one of each at a time
WRITERS = (HEAVY - {"dedupe_jobs", "sponsors_refresh"}) | {"scan_company", "live_search"}   # they add or change jobs: merging duplicates waits for them


def conflicts(a: str, b: str) -> bool:
    if a == b: return a in HEAVY
    if a in SITES and b in SITES: return True
    return (a == "dedupe_jobs" and b in WRITERS) or (b == "dedupe_jobs" and a in WRITERS)


def active(db: Session) -> list[Task]:
    """Tasks a live worker is on right now (paused ones included). A task left 'running' by a worker that died does not count."""
    from . import schedule_service
    ids = [w["task_id"] for w in schedule_service.workers(db) if w.get("task_id")]
    return list(db.scalars(select(Task).where(Task.id.in_(ids), Task.status.in_(("running", "paused"))).order_by(Task.id))) if ids else []


def claim(db: Session, on_claim=None) -> Task | None:
    """Atomically take the oldest queued task that may run now. One claim at a time across all workers; a task also waits for
    an older queued task it conflicts with, so the order people asked for is kept. on_claim(task) runs inside the same transaction."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('careers:claim'))"))
    ahead = [t.kind for t in active(db)]
    for tid, kind in db.execute(select(Task.id, Task.kind).where(Task.status == "queued").order_by(Task.id)).all():
        if any(conflicts(kind, k) for k in ahead): ahead.append(kind); continue
        row = db.execute(text("UPDATE tasks SET status='running', started_at=now() WHERE id = :i AND status='queued' RETURNING id"), {"i": tid}).first()
        if not row: continue                                                          # stopped a moment ago
        t = db.get(Task, tid, populate_existing=True)
        if on_claim: on_claim(t)
        db.commit()
        return t
    db.commit()
    return None


def waiting_reasons(db: Session) -> dict[int, dict]:
    """For every queued task: why it has not started yet."""
    from . import schedule_service
    live = schedule_service.workers(db); on = active(db)
    busy = sum(1 for w in live if w.get("task_id")); free = len(live) - busy
    ahead = list(on); out: dict[int, dict] = {}
    for t in db.scalars(select(Task).where(Task.status == "queued").order_by(Task.id)):
        blocker = next((x for x in ahead if conflicts(t.kind, x.kind)), None)
        if not live: out[t.id] = {"why": "no_worker"}
        elif blocker: out[t.id] = {"why": "conflict", "task_id": blocker.id, "kind": blocker.kind}
        elif free <= 0:
            first = on[0] if on else None
            out[t.id] = {"why": "busy", "workers": len(live), "task_id": first.id if first else None, "kind": first.kind if first else None}
        else: out[t.id] = {"why": "next"}; free -= 1
        ahead.append(t)
    return out


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
