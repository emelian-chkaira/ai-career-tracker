"""The storage policy (which job domains to keep, how old jobs may be, when expired jobs are deleted).

Defaults come from the environment (CAREERS_KEEP_DOMAINS ...). An operator can override them in the Crawler page; overrides are saved in the database (kv table),
so they survive restarts and are shared by the API and the worker (which re-reads them every few seconds)."""
import json, time
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import SessionLocal
from app.crawler.domains import DOMAINS, parse
from app.crawler import places
from app.models import KV

KEY = "policy"
_cache: dict = {"at": 0.0, "v": None}


def defaults() -> dict:
    raw = [x.strip() for x in (settings.crawl_countries or "").split(",") if x.strip()]
    return {"countries": places.expand([x for x in raw if len(x) == 2], [x.lower() for x in raw if len(x) > 2]), "keep_remote": bool(settings.keep_remote),
            "keep_domains": sorted(parse(settings.keep_domains)), "max_job_age_days": int(settings.max_job_age_days or 0), "delete_expired_after_days": int(settings.delete_expired_after_days or 0)}


def current() -> dict:
    """Effective policy (env defaults + saved overrides). Cheap: cached for 5 seconds."""
    if time.time() - _cache["at"] < 5 and _cache["v"] is not None and _cache["env"] == (settings.keep_domains, settings.max_job_age_days, settings.delete_expired_after_days, settings.crawl_countries, settings.keep_remote): return _cache["v"]
    p = defaults()
    try:
        with SessionLocal() as db:
            raw = db.scalar(select(KV.v).where(KV.k == KEY))
        if raw: p.update({k: v for k, v in json.loads(raw).items() if k in p})
    except Exception: pass
    _cache.update(at=time.time(), v=p, env=(settings.keep_domains, settings.max_job_age_days, settings.delete_expired_after_days, settings.crawl_countries, settings.keep_remote)); return p


def save(db: Session, keep_domains: list[str], max_job_age_days: int, delete_expired_after_days: int, countries: list[str] | None = None, keep_remote: bool | None = None) -> dict:
    bad = [d for d in keep_domains if d not in DOMAINS]
    if bad: raise ValueError(f"unknown domain(s): {', '.join(bad)}")
    if max_job_age_days < 0 or delete_expired_after_days < 0: raise ValueError("days cannot be negative")
    cur = current()
    cs = [c.upper() for c in (countries if countries is not None else cur["countries"])]
    badc = [c for c in cs if c not in places.COVERED]
    if badc: raise ValueError(f"unknown or unsupported country code(s): {', '.join(badc)}")
    p = {"countries": list(dict.fromkeys(cs)), "keep_remote": cur["keep_remote"] if keep_remote is None else bool(keep_remote),
         "keep_domains": sorted(set(keep_domains)), "max_job_age_days": int(max_job_age_days), "delete_expired_after_days": int(delete_expired_after_days)}
    row = db.get(KV, KEY) or KV(k=KEY); row.v = json.dumps(p); db.add(row); db.commit()
    _cache["v"] = None; return p


def reset(db: Session) -> dict:
    row = db.get(KV, KEY)
    if row: db.delete(row); db.commit()
    _cache["v"] = None; return current()
