"""Application tracking beyond a stage column: a per-job timeline, follow-up reminders and funnel statistics.

Every stage change (made by hand, by drag and drop, or by accepting a mail suggestion) is written to the job's timeline,
so the history of an application is always complete. Moving a job to "applied" stamps the date and, unless the user
chose one, schedules a follow-up a week later."""
import datetime as dt
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Job, JobEvent, Notification, User, UserJob

STAGES = ["shortlisted", "applied", "screening", "assessment", "team_match", "interview", "final_round", "offer", "accepted", "rejected", "withdrawn", "skipped"]
ACTIVE = ("applied", "screening", "assessment", "team_match", "interview", "final_round", "offer")
FUNNEL = ("applied", "screening", "assessment", "team_match", "interview", "final_round", "offer", "accepted")          # reached at least this far
SKIPPABLE = ("screening", "assessment", "team_match")          # many processes skip these: counted only when really visited
RANK = {s: i for i, s in enumerate(["shortlisted", "applied", "screening", "assessment", "team_match", "interview", "final_round", "offer", "accepted"])}
RESPONDED = ("screening", "assessment", "team_match", "interview", "final_round", "offer", "rejected", "accepted")
KINDS = ("note", "interview", "email", "follow_up", "offer")
FOLLOW_UP_DAYS = 7
now = lambda: dt.datetime.now(dt.timezone.utc)


def log(db: Session, user_id, job_id: int, kind: str, title: str, body: str | None = None, at: dt.datetime | None = None, meta: dict | None = None) -> JobEvent:
    e = JobEvent(user_id=user_id, job_id=job_id, kind=kind, title=title[:200], body=(body or None), at=at or now(), meta=meta or {}); db.add(e); return e


def change_stage(db: Session, user_id, job_id: int, stage: str, source: str = "manual", uj: UserJob | None = None) -> UserJob:
    """Set the stage of a user's job (creating the pipeline entry), writing the timeline and the applied/follow-up dates. Caller commits."""
    uj = uj or db.get(UserJob, (user_id, job_id)) or UserJob(user_id=user_id, job_id=job_id, stage=None)
    old = uj.stage
    if old == stage: db.add(uj); return uj
    uj.stage = stage
    if stage == "applied" and not uj.applied_at: uj.applied_at = now()
    if stage == "applied" and not uj.follow_up_at: uj.follow_up_at = now() + dt.timedelta(days=FOLLOW_UP_DAYS); uj.follow_up_note = uj.follow_up_note or "Check in on your application"
    if stage in ("rejected", "withdrawn", "accepted", "skipped", "offer"): uj.follow_up_at = None if stage != "offer" else uj.follow_up_at     # nothing left to chase
    db.add(uj)
    log(db, user_id, job_id, "stage", f"Moved to {stage}" if old else f"Saved as {stage}", meta={"from": old, "to": stage, "source": source})
    return uj


def view(uj: UserJob) -> dict:
    return {"stage": uj.stage, "notes": uj.notes, "applied_at": uj.applied_at, "follow_up_at": uj.follow_up_at, "follow_up_note": uj.follow_up_note, "contact": uj.contact, "offer_details": uj.offer_details}


def event_out(e: JobEvent) -> dict: return {"id": e.id, "kind": e.kind, "title": e.title, "body": e.body, "at": e.at, "meta": e.meta}


def timeline(db: Session, user_id, job_id: int) -> list[dict]:
    return [event_out(e) for e in db.scalars(select(JobEvent).where(JobEvent.user_id == user_id, JobEvent.job_id == job_id).order_by(JobEvent.at.desc(), JobEvent.id.desc()))]


def stats(db: Session, user_id, days: int = 30) -> dict:
    """Funnel and speed of the user's search. 'Reached' counts jobs that got at least that far (using the timeline, so a later rejection does not hide an interview)."""
    jobs = {r.job_id: r for r in db.scalars(select(UserJob).where(UserJob.user_id == user_id))}
    reached = {s: 0 for s in FUNNEL}; first_resp: list[float] = []
    stage_events: dict[int, list[JobEvent]] = {}
    for e in db.scalars(select(JobEvent).where(JobEvent.user_id == user_id, JobEvent.kind == "stage").order_by(JobEvent.at)): stage_events.setdefault(e.job_id, []).append(e)
    for jid, uj in jobs.items():
        seen = {uj.stage} | {(e.meta or {}).get("to") for e in stage_events.get(jid, [])}
        best = max((RANK[s] for s in seen if s in RANK), default=-1)
        for s in FUNNEL:
            if (s in seen) if s in SKIPPABLE else best >= RANK[s]: reached[s] += 1      # a test without a recruiter call is not a "recruiter screen"
        if uj.applied_at:
            nxt = [e.at for e in stage_events.get(jid, []) if (e.meta or {}).get("to") in RESPONDED and e.at > uj.applied_at]
            if nxt: first_resp.append((min(nxt) - uj.applied_at).total_seconds() / 86400)
    applied = reached["applied"]
    by_stage = {s: sum(1 for u in jobs.values() if u.stage == s) for s in STAGES}
    due = sum(1 for u in jobs.values() if u.follow_up_at and u.follow_up_at <= now() and u.stage in ACTIVE + ("shortlisted",))
    today = now().date(); per_day = {(today - dt.timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for u in jobs.values():
        if u.applied_at and u.applied_at.date().isoformat() in per_day: per_day[u.applied_at.date().isoformat()] += 1
    return {"applications_per_day": [{"day": d, "count": c} for d, c in per_day.items()], "total": len(jobs), "by_stage": by_stage, "funnel": reached, "active": sum(by_stage[s] for s in ACTIVE),
            "response_rate": round(sum(1 for jid, u in jobs.items() if jid in {j for j in jobs if u.applied_at} and any((e.meta or {}).get("to") in RESPONDED for e in stage_events.get(jid, []))) / applied, 2) if applied else None,
            "avg_days_to_response": round(sum(first_resp) / len(first_resp), 1) if first_resp else None, "follow_ups_due": due}


def follow_ups(db: Session, user_id, days: int = 14) -> list[dict]:
    rows = db.execute(select(UserJob, Job).join(Job, Job.id == UserJob.job_id).where(UserJob.user_id == user_id, UserJob.follow_up_at.is_not(None), UserJob.follow_up_at <= now() + dt.timedelta(days=days)).order_by(UserJob.follow_up_at)).all()
    return [{"job_id": j.id, "title": j.title, "company": j.company.name, "stage": u.stage, "at": u.follow_up_at, "note": u.follow_up_note, "overdue": u.follow_up_at <= now()} for u, j in rows]


def notify_due(db: Session) -> int:
    """Worker: one in-app reminder per follow-up that has come due (the follow-up date is cleared from 'due' by notifying once per date)."""
    n = 0
    for uj, j in db.execute(select(UserJob, Job).join(Job, Job.id == UserJob.job_id).where(UserJob.follow_up_at.is_not(None), UserJob.follow_up_at <= now())).all():
        key = uj.follow_up_at.isoformat()
        dup = db.scalar(select(Notification.id).where(Notification.user_id == uj.user_id, Notification.kind == "follow_up", Notification.data["job_id"].astext == str(j.id), Notification.data["due"].astext == key).limit(1))
        if dup: continue
        db.add(Notification(user_id=uj.user_id, kind="follow_up", title=f"Follow up: {j.title}", body=uj.follow_up_note or f"Time to check in with {j.company.name}.", data={"job_id": j.id, "due": key})); n += 1
    if n: db.commit()
    return n


def open_task_count(db: Session, user_id) -> int:
    from app.models import JobTask
    return db.scalar(select(func.count()).select_from(JobTask).where(JobTask.user_id == user_id, JobTask.done_at.is_(None))) or 0
