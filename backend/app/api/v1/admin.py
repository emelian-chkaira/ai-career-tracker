"""Crawler / operator endpoints (open to any signed-in user unless CAREERS_OPEN_CRAWLER=false; user management and deletes stay admin-only). They only ENQUEUE work; the worker process executes it."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.db import get_db
from app.core.deps import admin_user, current_user, operator_user
from app.models import Task, Company, Job, User, Sponsor, EmailOutbox
from app.services import task_service, maintenance_service, policy_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(operator_user)])
KINDS = {"dedupe_jobs", "board_search", "discover_country", "scan_all", "scan_unscanned", "scan_company", "discover", "census", "internships", "broad_sources", "logos", "sponsors_refresh", "embed", "live_search"}


class TaskIn(BaseModel):
    kind: str
    payload: dict = {}


@router.post("/tasks", status_code=202)
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    if body.kind not in KINDS: raise HTTPException(400, f"kind must be one of {sorted(KINDS)}")
    t = task_service.enqueue(db, body.kind, body.payload); return {"id": t.id, "status": t.status}


@router.get("/tasks")
def tasks(db: Session = Depends(get_db)):
    return [{"id": t.id, "kind": t.kind, "status": t.status, "progress": t.progress, "error": t.error, "created_at": t.created_at, "finished_at": t.finished_at}
            for t in db.scalars(select(Task).order_by(Task.id.desc()).limit(30))]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    one = lambda sql: db.execute(text(sql)).scalar()
    return {"users": one("SELECT count(*) FROM users"), "companies": one("SELECT count(*) FROM companies"), "companies_scanned": one("SELECT count(*) FROM companies WHERE last_scan IS NOT NULL"),
            "companies_with_jobs": one("SELECT count(DISTINCT company_id) FROM jobs WHERE status='open'"), "open_jobs": one("SELECT count(*) FROM jobs WHERE status='open'"),
            "embedded_jobs": one("SELECT count(*) FROM jobs WHERE embedding IS NOT NULL"), "sponsors": one("SELECT count(*) FROM sponsors"),
            "saved_searches": one("SELECT count(*) FROM saved_searches"), "emails_pending": one("SELECT count(*) FROM email_outbox WHERE status='pending'"),
            "scan_outcomes": [dict(note=r[0], n=r[1]) for r in db.execute(text("SELECT split_part(scan_note,' (',1) n, count(*) FROM companies WHERE last_scan IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 12"))]}


@router.get("/pipeline", summary="The crawler step by step: what each step does, when it runs, and what it did lately")
def pipeline(db: Session = Depends(get_db)):
    from app.services import schedule_service as sch, policy_service
    from app.core.config import settings
    one = lambda sql, **a: db.execute(text(sql), a).scalar()
    last = lambda kinds: (lambda r: {"kind": r[0], "status": r[1], "at": (r[2] or r[3]).isoformat() if (r[2] or r[3]) else None} if r else None)(
        db.execute(text("SELECT kind, status, finished_at, created_at FROM tasks WHERE kind = ANY(:k) ORDER BY id DESC LIMIT 1"), {"k": kinds}).first())
    sc = sch.current(db); pol = policy_service.current()
    return {
        "discover": {"companies": one("SELECT count(*) FROM companies"), "by_source": [dict(source=r[0], n=r[1]) for r in db.execute(text(
            "SELECT coalesce(split_part(source,' (',1),'seed list'), count(*) FROM companies GROUP BY 1 ORDER BY 2 DESC LIMIT 6"))],
            "last": last(["discover", "discover_country", "broad_sources", "census"])},
        "locate": {"with_careers_page": one("SELECT count(*) FROM companies WHERE careers_url IS NOT NULL OR ats_slug IS NOT NULL"),
                   "with_job_system": one("SELECT count(*) FROM companies WHERE ats IS NOT NULL AND ats NOT LIKE 'board:%'"),
                   "not_found": one("SELECT count(*) FROM companies WHERE scan_note ILIKE '%not found%'"), "never_visited": one("SELECT count(*) FROM companies WHERE last_scan IS NULL")},
        "read": {"visited_hour": one("SELECT count(*) FROM companies WHERE last_scan > now() - interval '1 hour'"), "visited_day": one("SELECT count(*) FROM companies WHERE last_scan > now() - interval '1 day'"),
                 "due": one("SELECT count(*) FROM companies WHERE (website IS NOT NULL OR ats_slug IS NOT NULL) AND (next_scan IS NULL OR next_scan <= now())"),
                 "revisit_hours": sc["revisit_hours"], "parallel": sc["parallel"]},
        "understand": {"open_jobs": one("SELECT count(*) FROM jobs WHERE status='open'"), "embedded": one("SELECT count(*) FROM jobs WHERE status='open' AND embedding IS NOT NULL"),
                       "by_sector": [dict(key=r[0], n=r[1]) for r in db.execute(text("SELECT sector, count(*) FROM jobs WHERE status='open' GROUP BY 1 ORDER BY 2 DESC LIMIT 6"))],
                       "by_mode": [dict(key=r[0], n=r[1]) for r in db.execute(text("SELECT work_mode, count(*) FROM jobs WHERE status='open' GROUP BY 1 ORDER BY 2 DESC"))]},
        "keep": {"countries": pol["countries"], "keep_remote": pol["keep_remote"], "max_job_age_days": pol["max_job_age_days"], "delete_expired_after_days": pol["delete_expired_after_days"],
                 "new_day": one("SELECT count(*) FROM jobs WHERE first_seen > now() - interval '1 day'"), "expired_day": one("SELECT count(*) FROM jobs WHERE status='expired' AND last_seen > now() - interval '1 day'")},
        "notify": {"saved_searches": one("SELECT count(*) FROM saved_searches"), "alerts_day": one("SELECT count(*) FROM notifications WHERE created_at > now() - interval '1 day'"),
                   "emails_pending": one("SELECT count(*) FROM email_outbox WHERE status='pending'")},
        "boards": {"enabled": bool(settings.board_sites.strip()), "jobs": one("SELECT count(*) FROM jobs WHERE status='open' AND source LIKE 'board:%'"),
                   "last": last(["board_search"]), "every_hours": settings.board_every_hours},
    }


@router.get("/worker", summary="Live view of the crawler worker: throughput, backlog and the latest scans")
def worker(db: Session = Depends(get_db)):
    one = lambda sql: db.execute(text(sql)).scalar()
    per_min = [{"t": r[0].isoformat(), "n": r[1]} for r in db.execute(text(
        "SELECT date_trunc('minute', last_scan) m, count(*) FROM companies WHERE last_scan > now() - interval '30 minutes' GROUP BY 1 ORDER BY 1"))]
    recent = [{"name": r[0], "ats": r[1], "note": r[2], "at": r[3].isoformat()} for r in db.execute(text(
        "SELECT name, ats, scan_note, last_scan FROM companies WHERE last_scan IS NOT NULL ORDER BY last_scan DESC LIMIT 15"))]
    idle = one("SELECT extract(epoch FROM now() - max(last_scan)) FROM companies")
    total = one("SELECT count(*) FROM companies WHERE (website IS NOT NULL OR ats_slug IS NOT NULL) AND coalesce(ats,'') NOT LIKE 'board:%'")
    due = one("SELECT count(*) FROM companies WHERE (website IS NOT NULL OR ats_slug IS NOT NULL) AND coalesce(ats,'') NOT LIKE 'board:%' AND (next_scan IS NULL OR next_scan <= now())")
    last10 = one("SELECT count(*) FROM companies WHERE last_scan > now() - interval '10 minutes'")
    from app.services import schedule_service
    st = schedule_service.status(db)
    running_tasks = [{"id": r[0], "kind": r[1], "started_at": r[2].isoformat() if r[2] else None, "progress": r[3]} for r in db.execute(text(
        "SELECT id, kind, started_at, progress FROM tasks WHERE status='running' ORDER BY started_at DESC LIMIT 5"))]
    return {"running": st["state"] in ("running", "idle") and idle is not None and idle < 300, "idle_seconds": int(idle) if idle is not None else None,
            "status": st, "tasks": running_tasks, "schedule": schedule_service.current(db),
            "total": total, "due": due, "per_min": per_min, "recent": recent,
            "rate_per_min": round(last10 / 10, 1), "eta_minutes": round(due / (last10 / 10)) if last10 else None,
            "open_jobs": one("SELECT count(*) FROM jobs WHERE status='open'"),
            "new_jobs_hour": one("SELECT count(*) FROM jobs WHERE first_seen > now() - interval '1 hour'"),
            "saved_careers_pages": one("SELECT count(*) FROM companies WHERE careers_url IS NOT NULL")}


@router.get("/policy", summary="The storage policy in effect (env defaults + overrides saved from the Crawler page)")
def policy(db: Session = Depends(get_db)):
    from app.crawler import places
    return {**policy_service.current(), "defaults": policy_service.defaults(), "places": places.public(),
            "by_country": dict(db.execute(text("SELECT cc, count(*) FROM jobs, unnest(countries) cc WHERE status='open' GROUP BY 1 ORDER BY 2 DESC")).all()),
            "by_age": dict(zip(("older_10", "older_30", "older_90", "older_180", "undated", "open"), db.execute(text(      # for the "How recent" choice: what each limit would remove
                "SELECT " + ", ".join(f"count(*) FILTER (WHERE COALESCE(posted_at, first_seen::date) < current_date - {d})" for d in (10, 30, 90, 180)) + ", count(*) FILTER (WHERE posted_at IS NULL), count(*) FROM jobs WHERE status='open'")).one())), "by_domain": {(r[0] or "unclassified"): r[1] for r in db.execute(text("SELECT domain, count(*) FROM jobs WHERE status='open' GROUP BY 1 ORDER BY 2 DESC"))}}


class BoardPlanIn(BaseModel):
    sites: list[str] = []
    terms: list[str] = []
    countries: list[str] = []


@router.get("/boards", summary="EXPERIMENTAL job boards: are they on, each board's health, and what the next search will look for")
def boards_overview(db: Session = Depends(get_db)):
    from app.crawler import boards
    from app.services import boards_service as bs
    from app.core.config import settings
    return {"enabled": bool(bs.configured()), "installed": boards.available(), "every_hours": settings.board_every_hours,
            "health": bs.health(db), "plan": bs.plan(db)}


@router.post("/boards/plan", summary="Preview a board search with your own terms / countries / boards (nothing runs)")
def boards_plan(body: BoardPlanIn, db: Session = Depends(get_db)):
    from app.services import boards_service as bs
    return bs.plan(db, body.sites or None, body.terms or None, [c.upper() for c in body.countries] or None)


class ScheduleIn(BaseModel):
    enabled: bool = True
    days: list[int] = [0, 1, 2, 3, 4, 5, 6]
    start: str = "00:00"
    end: str = "24:00"
    tz: str = "Europe/Amsterdam"
    revisit_hours: int = 12
    parallel: int = 20


@router.get("/schedule", summary="When the crawler visits career sites on its own, and whether that is now")
def get_schedule(db: Session = Depends(get_db)):
    from app.services import schedule_service as sch
    v = sch.current(db); ok, why, nxt = sch.window(v)
    return {**v, "allowed_now": ok, "why": why, "next_start": nxt}


@router.put("/schedule", dependencies=[Depends(admin_user)], summary="Save the crawl schedule (the worker follows it within seconds)")
def put_schedule(body: ScheduleIn, db: Session = Depends(get_db)):
    from app.services import schedule_service as sch
    try: v = sch.save(db, body.model_dump())
    except ValueError as e: raise HTTPException(400, str(e))
    ok, why, nxt = sch.window(v); return {**v, "allowed_now": ok, "why": why, "next_start": nxt}


class PolicyIn(BaseModel):
    countries: list[str] | None = None            # ISO codes to store jobs for; None = keep the current list
    keep_remote: bool | None = None
    keep_domains: list[str] = []
    max_job_age_days: int = 0
    delete_expired_after_days: int = 0


@router.put("/policy", dependencies=[Depends(admin_user)], summary="Save the storage policy (takes effect for the API and the worker within seconds)")
def set_policy(body: PolicyIn, db: Session = Depends(get_db)):
    try: policy_service.save(db, body.keep_domains, body.max_job_age_days, body.delete_expired_after_days, body.countries, body.keep_remote)
    except ValueError as e: raise HTTPException(400, str(e))
    return policy(db)


@router.delete("/policy", dependencies=[Depends(admin_user)], summary="Drop the saved overrides and go back to the environment defaults")
def reset_policy(db: Session = Depends(get_db)):
    policy_service.reset(db); return policy(db)


@router.get("/maintenance/{action}/preview", summary="How many rows an action would affect right now (changes nothing)")
def maintenance_preview(action: str, db: Session = Depends(get_db)):
    if action not in maintenance_service.ACTIONS: raise HTTPException(404, f"action must be one of {sorted(maintenance_service.ACTIONS)}")
    return maintenance_service.preview(db, action)


@router.post("/maintenance/{action}", dependencies=[Depends(admin_user)], summary="Housekeeping: backfill_domains | purge | prune | clear_jobs | clear_all (destructive ones need confirm=true)")
def maintenance(action: str, body: dict | None = None, db: Session = Depends(get_db)):
    if action not in maintenance_service.ACTIONS: raise HTTPException(404, f"action must be one of {sorted(maintenance_service.ACTIONS)}")
    if action in maintenance_service.DESTRUCTIVE and not (body or {}).get("confirm"): raise HTTPException(400, "this deletes data and cannot be undone: send {\"confirm\": true}")
    return maintenance_service.ACTIONS[action](db)


@router.get("/users", dependencies=[Depends(admin_user)])
def users(db: Session = Depends(get_db)):
    return [{"id": str(u.id), "email": u.email, "role": u.role, "active": u.is_active, "created_at": u.created_at} for u in db.scalars(select(User).order_by(User.created_at.desc()).limit(200))]


@router.patch("/users/{uid}", dependencies=[Depends(admin_user)])
def update_user(uid: str, body: dict, db: Session = Depends(get_db)):
    import uuid
    u = db.get(User, uuid.UUID(uid))
    if not u: raise HTTPException(404)
    if "role" in body and body["role"] in ("user", "admin"): u.role = body["role"]
    if "is_active" in body: u.is_active = bool(body["is_active"])
    db.commit(); return {"ok": True}


@router.post("/companies", status_code=201)
def add_company(body: dict, db: Session = Depends(get_db)):
    from app.services import ingest_service as ing
    c = ing.add_company(db, body["name"], body.get("website"), body.get("careers_url"), body.get("kvk")); db.commit()
    return {"id": c.id, "name": c.name}


@router.delete("/companies/{cid}", status_code=204, dependencies=[Depends(admin_user)])
def delete_company(cid: int, db: Session = Depends(get_db)):
    c = db.get(Company, cid)
    if c: db.delete(c); db.commit()


# ------------------------------------------------------------------ companies: list / add / edit / rescan / delete / export
import csv, io, re as _re
from fastapi.responses import StreamingResponse
from app.models import UserJob

CO_FILTERS = {
    "has_jobs": "EXISTS (SELECT 1 FROM jobs j WHERE j.company_id = c.id AND j.status = 'open')",
    "no_jobs": "c.last_scan IS NOT NULL AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.company_id = c.id AND j.status = 'open')",
    "failing": "c.fail_count > 0",
    "never": "c.last_scan IS NULL",
    "due": "(c.website IS NOT NULL OR c.ats_slug IS NOT NULL) AND (c.next_scan IS NULL OR c.next_scan <= now())",
    "no_site": "c.website IS NULL AND c.ats_slug IS NULL",
}
CO_SORT = {"name": "name ASC", "last_scan": "last_scan DESC NULLS LAST", "jobs": "open_jobs DESC, name ASC", "failing": "fail_count DESC, name ASC", "newest": "id DESC"}


def _co_where(q: str | None, status: str | None, country: str | None = None, city: str | None = None, source: str | None = None) -> tuple[str, dict]:
    w, a = ["TRUE"], {}
    if country: w.append("c.country = :ct"); a["ct"] = country.upper()
    if city: w.append("c.city ILIKE :cy"); a["cy"] = city
    if source == "board": w.append("c.source LIKE 'board:%'")
    elif source and source.startswith("board:"): w.append("c.source = :src"); a["src"] = source
    elif source == "site": w.append("(c.source IS NULL OR c.source NOT LIKE 'board:%')")
    if q: w.append("(c.name ILIKE :q OR c.website ILIKE :q OR c.careers_url ILIKE :q)"); a["q"] = f"%{q}%"
    if status and status != "all":
        if status not in CO_FILTERS: raise HTTPException(400, f"status must be one of {['all', *CO_FILTERS]}")
        w.append(CO_FILTERS[status])
    return " AND ".join(w), a


@router.get("/source-health", summary="How healthy is the crawl: per-ATS coverage, failing and stale companies")
def source_health(db: Session = Depends(get_db)):
    by_ats = [dict(r) for r in db.execute(text("""SELECT coalesce(c.ats, 'unknown') AS ats, count(*) AS companies, count(*) FILTER (WHERE c.fail_count >= 3) AS failing,
        coalesce(sum((SELECT count(*) FROM jobs j WHERE j.company_id = c.id AND j.status = 'open')), 0) AS open_jobs FROM companies c GROUP BY 1 ORDER BY companies DESC""")).mappings()]
    tot = db.execute(text("""SELECT count(*) AS companies, count(*) FILTER (WHERE last_scan IS NULL) AS never_scanned, count(*) FILTER (WHERE fail_count >= 3) AS failing,
        count(*) FILTER (WHERE last_scan < now() - interval '14 days') AS stale FROM companies""")).mappings().one()
    failing = [dict(r) for r in db.execute(text("""SELECT id, name, ats, fail_count, last_scan, scan_note FROM companies WHERE fail_count >= 3 ORDER BY fail_count DESC, last_scan LIMIT 30""")).mappings()]
    return {"totals": dict(tot), "by_ats": by_ats, "failing": failing}


@router.get("/filters", summary="Values to filter the Companies and Jobs lists by, with counts")
def filters(db: Session = Depends(get_db)):
    rows = lambda sql: [dict(value=r[0], n=r[1]) for r in db.execute(text(sql)) if r[0]]
    return {"companies": {"country": rows("SELECT country, count(*) FROM companies GROUP BY 1 ORDER BY 2 DESC"),
                          "city": rows("SELECT city, count(*) FROM companies WHERE city IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 60"),
                          "source": rows("SELECT CASE WHEN source LIKE 'board:%' THEN source ELSE 'site' END, count(*) FROM companies GROUP BY 1 ORDER BY 2 DESC")},
            "jobs": {"country": rows("SELECT cc, count(*) FROM jobs, unnest(countries) cc WHERE status='open' GROUP BY 1 ORDER BY 2 DESC"),
                     "city": rows("SELECT city, count(*) FROM jobs WHERE status='open' AND city IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 60"),
                     "sector": rows("SELECT sector, count(*) FROM jobs WHERE status='open' GROUP BY 1 ORDER BY 2 DESC"),
                     "work_mode": rows("SELECT work_mode, count(*) FROM jobs WHERE status='open' GROUP BY 1 ORDER BY 2 DESC"),
                     "source": rows("SELECT CASE WHEN source LIKE 'board:%' THEN source ELSE 'site' END, count(*) FROM jobs WHERE status='open' GROUP BY 1 ORDER BY 2 DESC")}}


@router.get("/companies", summary="Browse the companies the crawler knows")
def list_companies(q: str | None = None, status: str | None = None, country: str | None = None, city: str | None = None, source: str | None = None,
                   sort: str = "name", page: int = 1, limit: int = 25, db: Session = Depends(get_db)):
    if sort not in CO_SORT: raise HTTPException(400, f"sort must be one of {sorted(CO_SORT)}")
    limit = max(1, min(limit, 100)); where, a = _co_where(q, status, country, city, source)
    total = db.execute(text(f"SELECT count(*) FROM companies c WHERE {where}"), a).scalar()
    rows = db.execute(text(f"""SELECT * FROM (SELECT c.id, c.name, c.website, c.careers_url, c.ats, c.city, c.country, c.source, c.last_scan, c.next_scan, c.scan_note, c.fail_count, c.notes,
        (SELECT count(*) FROM jobs j WHERE j.company_id = c.id AND j.status = 'open') open_jobs FROM companies c WHERE {where}) t ORDER BY {CO_SORT[sort]} LIMIT :l OFFSET :o"""),
        {**a, "l": limit, "o": (max(page, 1) - 1) * limit}).mappings().all()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "limit": limit}


class CompanyPatch(BaseModel):
    name: str | None = None
    website: str | None = None
    careers_url: str | None = None
    notes: str | None = None


def _url(v: str | None) -> str | None:
    v = (v or "").strip()
    if not v: return None
    if not _re.match(r"https?://", v): v = "https://" + v
    return v


@router.patch("/companies/{cid}", summary="Edit a company. Changing the careers URL clears the saved ATS and schedules a re-scan.")
def patch_company(cid: int, body: CompanyPatch, db: Session = Depends(get_db)):
    c = db.get(Company, cid)
    if not c: raise HTTPException(404)
    if body.name is not None:
        n = body.name.strip()
        if not n: raise HTTPException(400, "name cannot be empty")
        if n != c.name and db.scalar(select(Company.id).where(Company.name == n)): raise HTTPException(409, "a company with that name already exists")
        c.name = n
    if body.website is not None: c.website = _url(body.website)
    if body.notes is not None: c.notes = body.notes.strip() or None
    if body.careers_url is not None and _url(body.careers_url) != c.careers_url:
        c.careers_url = _url(body.careers_url); c.ats = c.ats_slug = c.resolved_via = None; c.next_scan = None; c.fail_count = 0
    db.commit(); return {"ok": True}


@router.post("/companies/{cid}/scan", status_code=202, summary="Queue a re-scan of one company now")
def scan_one(cid: int, db: Session = Depends(get_db)):
    c = db.get(Company, cid)
    if not c: raise HTTPException(404)
    c.next_scan = None; db.commit()
    t = task_service.enqueue(db, "scan_company", {"id": cid}); return {"task_id": t.id}


class BulkCompanies(BaseModel):
    text: str
    scan: bool = True


@router.post("/companies/bulk", status_code=201, summary="Add many companies at once: one per line as 'Name', 'Name, website' or 'Name | website' (or just a website)")
def bulk_companies(body: BulkCompanies, db: Session = Depends(get_db)):
    from urllib.parse import urlparse
    from app.services import ingest_service as ing
    added, existing, bad = 0, 0, []
    for raw in body.text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        parts = [x.strip() for x in _re.split(r"\s*[|,;\t]\s*", line, maxsplit=1)]
        name, site = (parts[0], parts[1] if len(parts) > 1 else None)
        if _re.match(r"^(https?://)?[\w-]+(\.[\w-]+)+(/.*)?$", name) and not site:                     # just a website: derive the name from the domain
            site, host = name, urlparse(_url(name)).netloc.lower().removeprefix("www.")
            name = host.split(".")[-2].capitalize() if host.count(".") else host
        if not name or len(name) > 200: bad.append(line[:60]); continue
        before = db.scalar(select(Company.id).where(Company.name == name))
        ing.add_company(db, name, website=_url(site), source="manual")
        existing += bool(before); added += not before
    db.commit()
    task = task_service.enqueue(db, "scan_unscanned").id if body.scan and added else None
    return {"added": added, "already_known": existing, "ignored": bad, "scan_task_id": task}


# ------------------------------------------------------------------ jobs: browse / bulk change / export
JOB_SORT = {"newest": "j.first_seen DESC, j.id DESC", "oldest": "j.first_seen ASC, j.id ASC", "company": "c.name ASC, j.title ASC", "title": "j.title ASC"}


def _job_where(q, status, domain, company_id, older_than_days, no_domain=False, country=None, city=None, sector=None, work_mode=None, source=None) -> tuple[str, dict]:
    w, a = ["TRUE"], {}
    if country: w.append(":ct = ANY(j.countries)"); a["ct"] = country.upper()
    if city: w.append("j.city ILIKE :cy"); a["cy"] = city
    if sector: w.append("j.sector = :sec"); a["sec"] = sector
    if work_mode: w.append("j.work_mode = :wm"); a["wm"] = work_mode
    if source == "board": w.append("j.source LIKE 'board:%'")
    elif source and source.startswith("board:"): w.append("j.source = :src"); a["src"] = source
    elif source == "site": w.append("(j.source IS NULL OR j.source NOT LIKE 'board:%')")
    if q: w.append("(j.title ILIKE :q OR c.name ILIKE :q)"); a["q"] = f"%{q}%"
    if status and status != "all": w.append("j.status = :st"); a["st"] = status
    if domain: w.append("j.domain = :dm"); a["dm"] = domain
    if company_id: w.append("j.company_id = :cid"); a["cid"] = company_id
    if older_than_days: w.append("COALESCE(j.posted_at, j.first_seen::date) < current_date - :od"); a["od"] = older_than_days
    return " AND ".join(w), a


@router.get("/jobs", summary="Browse stored jobs")
def list_jobs(q: str | None = None, status: str | None = "open", domain: str | None = None, company_id: int | None = None, older_than_days: int | None = None,
              country: str | None = None, city: str | None = None, sector: str | None = None, work_mode: str | None = None, source: str | None = None,
              sort: str = "newest", page: int = 1, limit: int = 25, db: Session = Depends(get_db)):
    if sort not in JOB_SORT: raise HTTPException(400, f"sort must be one of {sorted(JOB_SORT)}")
    limit = max(1, min(limit, 100)); where, a = _job_where(q, status, domain, company_id, older_than_days, country=country, city=city, sector=sector, work_mode=work_mode, source=source)
    base = f"FROM jobs j JOIN companies c ON c.id = j.company_id WHERE {where}"
    total = db.execute(text(f"SELECT count(*) {base}"), a).scalar()
    rows = db.execute(text(f"""SELECT j.id, j.title, j.url, j.location, j.city, j.country, j.countries, j.work_mode, j.sector, j.source, j.status, j.domain, j.job_type, j.posted_at, j.first_seen, j.last_seen, c.id company_id, c.name company,
        (SELECT count(*) FROM user_jobs u WHERE u.job_id = j.id) saved_by {base} ORDER BY {JOB_SORT[sort]} LIMIT :l OFFSET :o"""), {**a, "l": limit, "o": (max(page, 1) - 1) * limit}).mappings().all()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "limit": limit}


class JobBulk(BaseModel):
    action: str                                   # delete | expire | reopen
    ids: list[int] = []                           # explicit selection ...
    all_matching: bool = False                    # ... or everything the filters below match
    q: str | None = None
    status: str | None = None
    domain: str | None = None
    company_id: int | None = None
    older_than_days: int | None = None
    country: str | None = None
    city: str | None = None
    sector: str | None = None
    work_mode: str | None = None
    source: str | None = None
    confirm: bool = False


@router.post("/jobs/bulk", summary="Delete / expire / reopen the selected jobs (or all jobs matching the filters). Deleting is admin-only.")
def jobs_bulk(body: JobBulk, user: User = Depends(operator_user), db: Session = Depends(get_db)):
    if body.action not in ("delete", "expire", "reopen"): raise HTTPException(400, "action must be delete, expire or reopen")
    if body.action == "delete" and user.role != "admin": raise HTTPException(403, "only an admin can delete jobs")
    if body.all_matching:
        if not body.confirm: raise HTTPException(400, "this changes every matching job: send confirm=true")
        where, a = _job_where(body.q, body.status, body.domain, body.company_id, body.older_than_days,
                              country=body.country, city=body.city, sector=body.sector, work_mode=body.work_mode, source=body.source)
        ids = [r[0] for r in db.execute(text(f"SELECT j.id FROM jobs j JOIN companies c ON c.id = j.company_id WHERE {where}"), a)]
    else: ids = body.ids[:5000]
    if not ids: return {"changed": 0}
    if body.action == "delete": n = db.execute(text("DELETE FROM jobs WHERE id = ANY(:i)"), {"i": ids}).rowcount
    else: n = db.execute(text("UPDATE jobs SET status = :s WHERE id = ANY(:i)"), {"s": "expired" if body.action == "expire" else "open", "i": ids}).rowcount
    db.commit(); return {"changed": n}


@router.get("/export/{what}.csv", summary="Download jobs or companies as CSV")
def export(what: str, db: Session = Depends(get_db)):
    if what == "jobs":
        sql = "SELECT j.id, c.name company, j.title, j.domain, j.job_type, j.location, j.city, j.status, j.posted_at, j.first_seen, j.last_seen, j.url FROM jobs j JOIN companies c ON c.id = j.company_id ORDER BY j.id"
    elif what == "companies":
        sql = "SELECT id, name, website, careers_url, ats, ats_slug, city, source, sponsor_status, last_scan, next_scan, fail_count, scan_note FROM companies ORDER BY id"
    else: raise HTTPException(404, "export jobs or companies")
    def rows():
        res = db.execute(text(sql)); buf = io.StringIO(); w = csv.writer(buf); w.writerow(res.keys()); yield buf.getvalue()
        for r in res:
            buf.seek(0); buf.truncate(); w.writerow(["" if v is None else str(v) for v in r]); yield buf.getvalue()
    return StreamingResponse(rows(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={what}.csv"})


# ------------------------------------------------------------------ task queue controls
@router.post("/tasks/{tid}/cancel", summary="Stop a task: a queued one never starts, a running or paused one stops at its next step")
def cancel_task(tid: int, db: Session = Depends(get_db)):
    import datetime as dt
    t = db.get(Task, tid)
    if not t: raise HTTPException(404)
    if t.status in ("queued", "running", "paused"):
        t.status, t.error, t.finished_at = "failed", task_service.STOPPED, dt.datetime.now(dt.timezone.utc); db.commit()
    return {"ok": True, "status": t.status}


@router.post("/tasks/{tid}/pause", summary="Pause a running task at its next step (it keeps what it has done)")
def pause_task(tid: int, db: Session = Depends(get_db)):
    t = db.get(Task, tid)
    if not t: raise HTTPException(404)
    if t.status == "running": t.status = "paused"; db.commit()
    return {"ok": True, "status": t.status}


@router.post("/tasks/{tid}/resume", summary="Carry on with a paused task")
def resume_task(tid: int, db: Session = Depends(get_db)):
    t = db.get(Task, tid)
    if not t: raise HTTPException(404)
    if t.status == "paused": t.status = "running"; db.commit()
    return {"ok": True, "status": t.status}


@router.delete("/tasks", summary="Remove finished and failed tasks from the history")
def clear_tasks(db: Session = Depends(get_db)):
    n = db.execute(text("DELETE FROM tasks WHERE status IN ('done', 'failed')")).rowcount; db.commit(); return {"removed": n}
