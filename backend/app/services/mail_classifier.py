"""Find job-search e-mails, classify them, extract company/role/dates, and link them to the user's pipeline.

An AI model (any provider from llm_service) reads each message and returns the category, company, role and dates.
A cheap keyword pre-filter only decides which messages are worth sending to the model at all (it never classifies anything)."""
import re, time, datetime as dt
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.models import MailEvent, Company, Job, UserJob
from . import llm_service as llm

CATEGORIES = ("application_received", "interview_invite", "assessment", "offer", "rejection", "recruiter_outreach")
STAGE_OF = {"application_received": "applied", "assessment": "assessment", "interview_invite": "interview", "offer": "offer", "rejection": "rejected"}

_R = lambda p: re.compile(p, re.I)
JOBISH = _R(r"applic|interview|position|vacanc|vacature|sollicit|recruit|candidate|kandidaat|career|hiring|offer|role\b|bewerbung|stelle|assess|challenge|assignment|take-?home|opdracht|aufgabe|opportunit|your profile|your cv|your resume|jobs?\b")
NOISE_SENDER = _R(r"(no-?reply@)?(newsletter|digest|marketing|promo|deals|noreply@(medium|linkedin|facebook|twitter|instagram|pinterest|quora)\.)")


def looks_job_related(mail: dict) -> bool:
    hay = f"{mail.get('subject','')} {mail.get('body','')[:1500]}"
    return bool(JOBISH.search(hay)) and not NOISE_SENDER.search(mail.get("sender_addr", "") or "")


SYSTEM = """You read one e-mail from a person's inbox and decide whether it is part of THEIR job search.
Answer with ONE JSON object and nothing else:
{"category": one of ["application_received","interview_invite","assessment","offer","rejection","recruiter_outreach","not_job_related"],
 "company": string or null, "role": string or null, "location": string or null,
 "event_date": interview/deadline date-time as written or ISO, or null,
 "summary": one short sentence (max 160 chars), "confidence": number 0..1}
Rules: rejection = they will not continue with the candidate. offer = a job offer or contract. interview_invite = asks to schedule or confirms an interview/call.
assessment = a test, coding challenge or take-home. application_received = automatic confirmation of an application. recruiter_outreach = someone approaches the candidate.
Newsletters, job-alert digests, marketing and anything not about the candidate's own applications are not_job_related. Never invent facts: use null when unknown."""


def classify(cfg: llm.Cfg, mail: dict) -> dict | None:
    user = f"From: {mail.get('sender','')}\nSubject: {mail.get('subject','')}\nDate: {mail.get('date')}\n\n{mail.get('body','')[:3500]}"
    d = llm.complete_json(cfg, SYSTEM, user, max_tokens=400)
    cat = str(d.get("category", "")).strip()
    if cat not in CATEGORIES: return None
    s = lambda k, n: (str(d[k]).strip()[:n] or None) if d.get(k) not in (None, "", "null") else None
    try: conf = max(0.0, min(1.0, float(d.get("confidence", 0.7))))
    except (TypeError, ValueError): conf = 0.7
    return dict(category=cat, company=s("company", 200), role=s("role", 250), location=s("location", 200), event_date=s("event_date", 80), summary=s("summary", 300), confidence=conf, classifier=cfg.label)


def _norm(s: str | None) -> str: return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def link(db: Session, user_id, res: dict, sender_addr: str = "") -> tuple[int | None, int | None]:
    """Find the company (by name, then by the sender's domain) and the user's pipeline job at that company (best title overlap)."""
    cid = None
    n = _norm(res.get("company"))
    if n and len(n) >= 3:
        rows = db.execute(text("SELECT id, name FROM companies")).all() if False else db.execute(select(Company.id, Company.name).where(Company.name.ilike(f"%{res['company'][:40]}%")).limit(25)).all()
        best = sorted(rows, key=lambda r: (_norm(r[1]) != n, abs(len(_norm(r[1])) - len(n))))
        if best: cid = best[0][0]
    if not cid and sender_addr and "@" in sender_addr:
        dom = sender_addr.split("@")[1].split(".")[-2] if sender_addr.count(".") else ""
        if len(dom) >= 4:
            r = db.scalar(select(Company.id).where(Company.website.ilike(f"%{dom}%")).limit(1))
            cid = r or cid
    if not cid: return None, None
    jobs = db.execute(select(Job.id, Job.title).join(UserJob, UserJob.job_id == Job.id).where(UserJob.user_id == user_id, Job.company_id == cid)).all()
    if not jobs: return cid, None
    want = _words(res.get("role"))
    if not want: return cid, (jobs[0][0] if len(jobs) == 1 else None)       # the e-mail names no role: only an unambiguous job
    best = max(jobs, key=lambda j: len(want & _words(j[1])))
    # words like "intern" are shared by unrelated roles; at least half of the telling words must match, or it is another application
    return cid, (best[0] if len(want & _words(best[1])) * 2 >= len(want) else None)


_GENERIC = {"intern", "internship", "internships", "junior", "senior", "student", "graduate", "trainee", "traineeship", "placement", "role", "position", "the", "and", "for", "with", "our"}


def _words(s: str | None) -> set[str]:
    return set(re.findall(r"[a-z0-9+#]{2,}", (s or "").lower())) - _GENERIC


def add_applied_job(db: Session, user_id, ev: MailEvent) -> int | None:
    """You applied for a role the crawler never collected: keep it in the pipeline anyway. Stored as a closed entry, so it never shows up in search."""
    if ev.job_id or ev.category != "application_received" or not ev.company_id or not _words(ev.role): return ev.job_id
    url = f"email://{user_id}/{ev.company_id}/{_norm(ev.role)}"
    j = db.scalar(select(Job).where(Job.url == url))
    if not j:
        j = Job(company_id=ev.company_id, title=ev.role, location=ev.location, url=url, source="email", status="expired"); db.add(j); db.flush()
    ev.job_id = j.id; return j.id


def process(db: Session, user_id, cfg: llm.Cfg, mails: list[dict], account_id: int | None = None, progress=None, auto_apply: float | None = None) -> dict:
    """Classify messages and store the extracted facts as MailEvents (new ones only). Returns counters."""
    if not cfg.configured: raise RuntimeError("Choose an AI model first: open the web app, Inbox, AI model.")
    stats = dict(scanned=0, skipped=0, found=0, duplicate=0, ai_failed=0, auto_applied=0); fails = 0
    known = {r[0] for r in db.execute(select(MailEvent.message_id).where(MailEvent.user_id == user_id))}
    last = 0.0
    for i, m in enumerate(mails):
        stats["scanned"] += 1
        if progress and time.monotonic() - last > 1.5: progress(**stats); last = time.monotonic()        # every few seconds, whatever happens to this message
        if m["message_id"] in known: stats["duplicate"] += 1; continue
        if not looks_job_related(m): stats["skipped"] += 1; continue
        try: res = classify(cfg, m); fails = 0
        except llm.LlmError as e:
            stats["ai_failed"] += 1; stats["ai_error"] = str(e)[:200]; fails += 1
            if e.kind == "config" or fails >= 5: db.commit(); raise RuntimeError(f"The AI model keeps failing: {e}")          # stop instead of burning through the whole mailbox
            continue
        if not res: stats["skipped"] += 1; continue
        cid, jid = link(db, user_id, res, m.get("sender_addr", ""))
        ev = MailEvent(user_id=user_id, account_id=account_id, message_id=m["message_id"], sender=m.get("sender"), subject=m.get("subject"), received_at=m.get("date"),
                       company_id=cid, job_id=jid, **res); db.add(ev); known.add(m["message_id"]); stats["found"] += 1
        if auto_apply is not None and res["confidence"] >= auto_apply and res["category"] in STAGE_OF and (jid or res["category"] == "application_received"):  # high confidence: apply it, the user can undo
            db.flush()
            if not add_applied_job(db, user_id, ev): continue
            if apply_stage(db, user_id, ev): ev.status = "auto"; stats["auto_applied"] += 1
        if stats["found"] % 10 == 0: db.commit()
    db.commit(); return stats


def apply_stage(db: Session, user_id, ev: MailEvent, job_id: int | None = None) -> str | None:
    """Move the linked job in the user's pipeline according to the e-mail. Rejections/offers/interviews are never silently downgraded."""
    jid = job_id or ev.job_id; stage = STAGE_OF.get(ev.category)
    if not jid or not stage: return None
    from . import tracking_service as ts
    uj = db.get(UserJob, (user_id, jid)) or UserJob(user_id=user_id, job_id=jid, stage=None)
    order = ["shortlisted", "applied", "screening", "assessment", "team_match", "interview", "final_round", "offer"]
    if uj.stage in order and stage in order and order.index(uj.stage) > order.index(stage): return uj.stage            # keep the further stage
    ts.log(db, user_id, jid, "email", ev.subject or "E-mail", ev.summary, at=ev.received_at, meta={"mail_event_id": ev.id, "category": ev.category})
    ts.change_stage(db, user_id, jid, stage, source="email", uj=uj); return stage


def undo_auto(db: Session, user_id, ev: MailEvent) -> str | None:
    """Revert an automatically applied e-mail: put the job back where it was before that e-mail moved it. Returns the restored stage."""
    from . import tracking_service as ts
    from app.models import JobEvent
    ev.status = "new"
    if not ev.job_id: return None
    last = next((e for e in db.scalars(select(JobEvent).where(JobEvent.user_id == user_id, JobEvent.job_id == ev.job_id, JobEvent.kind == "stage").order_by(JobEvent.at.desc(), JobEvent.id.desc()))
                 if (e.meta or {}).get("source") == "email"), None)
    uj = db.get(UserJob, (user_id, ev.job_id))
    if not last or not uj or uj.stage != (last.meta or {}).get("to"): return uj.stage if uj else None
    prev = (last.meta or {}).get("from")
    if prev: ts.change_stage(db, user_id, ev.job_id, prev, source="undo", uj=uj); return prev
    db.delete(uj); db.delete(last); return None
