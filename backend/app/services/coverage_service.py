"""Users' places drive the crawler.

When someone picks countries (or regions) in their preferences, the crawler starts collecting them: the countries join the storage
policy and, for countries it knows few employers in, a "find employers" task is queued. report() tells the job list how far each
country is, so the page can say "collecting jobs in the UAE, new ones appear as they are read" instead of looking empty.

Only when the crawler is open to users (CAREERS_OPEN_CRAWLER, the self-hosted default) or the user is an admin; otherwise the
countries are just remembered as requested and an admin turns them on from the Crawler page."""
import datetime as dt
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.crawler import places
from app.models import User
from . import policy_service, task_service, schedule_service

ENOUGH_EMPLOYERS = 40          # below this many known employers in a country, look for more
MAX_NEW_DISCOVERIES = 6        # per preference save (a region like EMEA must not queue 60 searches at once)
REDISCOVER_AFTER = dt.timedelta(days=7)


def wanted_countries(profile: dict) -> list[str]:
    explicit = [c for c in (profile.get("countries") or ([profile["country"]] if profile.get("country") else [])) if c in places.COVERED]
    return list(dict.fromkeys(explicit + [c for c in places.expand([], profile.get("regions") or []) if c in places.COVERED]))


def _employers(db: Session, codes: list[str]) -> dict[str, int]:
    return dict(db.execute(text("SELECT country, count(*) FROM companies WHERE country = ANY(:c) GROUP BY 1"), {"c": codes}).all()) if codes else {}


def _recent_discovery(db: Session, code: str) -> bool:
    return bool(db.execute(text("SELECT 1 FROM tasks WHERE kind='discover_country' AND payload->>'country' = :c AND (status IN ('queued','running') OR finished_at > :since) LIMIT 1"),
                           {"c": code, "since": dt.datetime.now(dt.timezone.utc) - REDISCOVER_AFTER}).first())


def ensure(db: Session, user: User, codes: list[str] | None = None) -> dict:
    """Make the crawler cover this user's places (or the given countries). -> {"added": [...], "discovering": [...], "requested": [...]} for the UI to report."""
    want = [c for c in dict.fromkeys(x.upper() for x in codes) if c in places.COVERED] if codes is not None else wanted_countries(user.profile or {})
    if not want: return {"added": [], "discovering": [], "requested": []}
    pol = policy_service.current(); have = pol["countries"]
    missing = [c for c in want if have and c not in have]
    if not (settings.open_crawler or user.role == "admin"):
        return {"added": [], "discovering": [], "requested": missing}
    if missing:
        policy_service.save(db, pol["keep_domains"], pol["max_job_age_days"], pol["delete_expired_after_days"], countries=have + missing, keep_remote=pol["keep_remote"])
    emp = _employers(db, want); explicit = [c for c in (codes if codes is not None else (user.profile or {}).get("countries") or []) if c in want]
    order = explicit + [c for c in want if c not in explicit]                     # countries picked one by one first, then region members
    discovering = []
    for c in order:
        if len(discovering) >= MAX_NEW_DISCOVERIES: break
        if c == "NL" or emp.get(c, 0) >= ENOUGH_EMPLOYERS or _recent_discovery(db, c): continue
        task_service.enqueue(db, "discover_country", {"country": c}); discovering.append(c)
    return {"added": missing, "discovering": discovering, "requested": []}


def report(db: Session, codes: list[str]) -> dict:
    """Per country: collected?, open jobs, known employers, employers still to read, and whether employers are being searched for now."""
    codes = [c for c in dict.fromkeys(c.upper() for c in codes) if c in places.COUNTRIES][:80]
    pol = policy_service.current(); st = schedule_service.status(db)
    jobs = dict(db.execute(text("SELECT cc, count(*) FROM jobs, unnest(countries) cc WHERE status='open' AND cc = ANY(:c) GROUP BY 1"), {"c": codes}).all()) if codes else {}
    rows = db.execute(text("SELECT country, count(*), count(*) FILTER (WHERE last_scan IS NULL AND (website IS NOT NULL OR ats_slug IS NOT NULL)) FROM companies WHERE country = ANY(:c) GROUP BY 1"), {"c": codes}).all() if codes else []
    emp = {r[0]: (r[1], r[2]) for r in rows}
    busy = {r[0]: r[1] for r in db.execute(text("SELECT payload->>'country', status FROM tasks WHERE kind='discover_country' AND status IN ('queued','running')")).all()}
    out = []
    for c in codes:
        e, pending = emp.get(c, (0, 0)); collected = not pol["countries"] or c in pol["countries"]
        phase = ("off" if not collected else "finding_employers" if c in busy else "reading" if pending else "ready")
        out.append({"code": c, "name": places.COUNTRIES[c][0], "collected": collected, "jobs": jobs.get(c, 0), "employers": e, "to_read": pending, "finding": busy.get(c), "phase": phase})
    return {"countries": out, "worker": {"state": st["state"], "next_start": st["next_start"], "why": st["why"]},
            "active": st["state"] in ("running", "idle") and any(x["phase"] in ("finding_employers", "reading") for x in out)}
