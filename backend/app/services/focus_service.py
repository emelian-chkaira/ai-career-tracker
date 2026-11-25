"""Which fields of work the crawler should collect, worked out from the people who use it.

Every account says what it looks for (sectors chosen in setup, job titles, skills) and has a CV. From that, per account:
  - sectors: the ones chosen, plus the ones the job titles and the CV show (a CV full of Flutter and Python is "tech");
  - for a tech account, the domains its titles and skills point to (mobile, backend, data ...). When nothing specific shows, every tech domain counts.
The crawler collects the union over all active accounts, so a mobile developer gets mobile and software jobs, an architect gets architecture jobs,
and neither gets accountants. An install with no profiles yet collects everything. Read-only: nothing here is written to the database."""
import time
from sqlalchemy import select
from app.core.db import SessionLocal
from app.crawler import domains, sectors
from app.cvtools import cv as cvmod
from app.models import User

_cache: dict = {"at": 0.0, "v": None}
TTL = 120


def reset():
    _cache.update(at=0.0, v=None)


def _cv_of(db, user):
    from . import fit_service as fs
    try: return fs.get_cv(db, user) or {}
    except Exception: return {}


def signal(profile: dict, cv: dict | None) -> tuple[set[str], set[str], bool]:
    """-> (sectors, domains, has_signal) for one account."""
    pr, cv = profile or {}, cv or {}
    titles = [str(t) for t in (pr.get("titles") or [])] + [str(b.get("title") or "") for b in (cv.get("experience") or []) if isinstance(b, dict)]
    skills = [str(s) for s in (pr.get("skills") or [])] + [str(s) for s in (cv.get("skills") or [])]
    secs = {s for s in (pr.get("sectors") or []) if s in sectors.SECTORS and s != "other"}
    for t in titles:
        s = sectors.classify(t)
        if s != "other": secs.add(s)
    if not secs and skills and cvmod.find_terms(" ".join(skills)): secs.add("tech")
    doms: set[str] = set()
    if "tech" in secs:
        for t in titles:
            d = domains.classify(t)
            if d != "other": doms.add(d)
        d = domains.classify("", " ".join(skills), skills)
        if d != "other": doms.add(d)
        if doms: doms.add("software")                      # generic "Software Engineer" postings suit every developer
    return secs, doms, bool(secs)


def derive() -> dict:
    """-> {"sectors": [...], "domains": [...], "users": n}. Empty lists mean "no restriction" (nobody has said what they look for yet)."""
    if time.time() - _cache["at"] < TTL and _cache["v"] is not None: return _cache["v"]
    secs: set[str] = set(); doms: set[str] = set(); n = 0; tech_open = False
    try:
        with SessionLocal() as db:
            for u in db.scalars(select(User).where(User.is_active.is_(True))):
                s, d, ok = signal(u.profile, _cv_of(db, u))
                if not ok: continue
                n += 1; secs |= s
                if "tech" in s:
                    if d: doms |= d
                    else: tech_open = True                  # a tech account with nothing specific: every tech domain
    except Exception: pass
    v = {"sectors": sorted(secs), "domains": [] if tech_open else sorted(doms), "users": n}
    _cache.update(at=time.time(), v=v); return v
