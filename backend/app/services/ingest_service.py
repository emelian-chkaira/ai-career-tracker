"""Write path of the crawler: companies, jobs (NL-only, deduped, skills/city extracted), scan results, logos."""
import re, hashlib, datetime as dt, os
from bs4 import BeautifulSoup
from sqlalchemy import select, update, func, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from app.core.config import settings
from app.crawler import discovery, nl, scoring, dates, domains, sectors, places
from app.cvtools import cv as cvmod
from app.models import Company, Job, JobSkill
from app.services import sponsor_service, policy_service

NOT_JOB_URL = re.compile(r"/(news|nieuws|press|blog|articles?|media|insights|stories|events|podcast|perspectives|whitepapers?)(/|$)|#\d+$", re.I)
NOT_JOB_TITLE = re.compile(r"\b(receives|announces|announced|approval|press release|partners with|wins|launches|appoints|acquires|acquisition of)\b", re.I)
CITY_RE = sorted({c for c in nl.CITIES if c and len(c) > 3}, key=len, reverse=True)
_CITY_PAT = re.compile(r"(?<![\w])(" + "|".join(re.escape(c) for c in CITY_RE) + r")(?![\w])", re.I)
LOGO_DIR = os.path.join(settings.data_dir, "logos")
now = lambda: dt.datetime.now(dt.timezone.utc)


def looks_like_job(title, url): return not (NOT_JOB_URL.search(url or "") or NOT_JOB_TITLE.search(title or ""))
def city_of(location: str) -> str | None:
    m = _CITY_PAT.search(location or "")
    if not m: return places.city_of(location)                                   # outside the Netherlands: the big cities of every covered country
    c = m.group(1).lower()
    return {"the hague": "Den Haag", "hague": "Den Haag", "haag": "Den Haag", "gravenhage": "Den Haag", "'s-gravenhage": "Den Haag", "bosch": "Den Bosch", "s-hertogenbosch": "Den Bosch", "'s-hertogenbosch": "Den Bosch"}.get(c, c.title())
def money(text):
    m = re.search(r"€\s?(\d{1,3}(?:[.,]\d{3})+|\d{4,6})(?:\s?[-–]\s?€?\s?(\d{1,3}(?:[.,]\d{3})+|\d{4,6}))?", text or "")
    if not m: return None, None, None
    f = lambda s: float(re.sub(r"[.,]", "", s)) if s else None
    lo, hi = f(m.group(1)), f(m.group(2))
    return lo, hi, ("year" if (lo or 0) > 15000 else "month")
def dedupe_key(cid, title, location):
    n = lambda t: re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()
    return hashlib.sha1(f"{cid}|{n(title)}|{n((location or '').split(',')[0])}".encode()).hexdigest()[:16]
def skills_of(title: str, desc: str) -> list[str]:
    return list(dict.fromkeys(cvmod.find_terms((title or "") + " \n " + (desc or "")[:8000])))[:25]


def add_company(db: Session, name, website=None, careers_url=None, kvk=None, city=None, address=None, source=None) -> Company:
    import html as _h
    name = _h.unescape(name).strip()
    c = db.scalar(select(Company).where(Company.name == name))
    if not c:
        st, match = sponsor_service.check(db, name, kvk)
        c = Company(name=name, website=website, careers_url=careers_url, kvk=kvk, sponsor_status=st, sponsor_match=match, city=city, address=address, source=source)
        db.add(c); db.flush()
    else:
        c.website = c.website or website; c.city = c.city or city; c.address = c.address or address; c.source = c.source or source
    return c


_TLD = {"nl": "NL", "be": "BE", "lu": "LU", "de": "DE", "at": "AT", "ch": "CH", "uk": "GB", "ie": "IE", "fr": "FR", "es": "ES", "pt": "PT", "it": "IT", "pl": "PL", "cz": "CZ", "sk": "SK",
        "hu": "HU", "ro": "RO", "bg": "BG", "gr": "GR", "dk": "DK", "se": "SE", "no": "NO", "fi": "FI", "ee": "EE", "lv": "LV", "lt": "LT", "si": "SI", "hr": "HR", "rs": "RS",
        "ae": "AE", "sa": "SA", "qa": "QA", "kw": "KW", "bh": "BH", "om": "OM", "eg": "EG", "ma": "MA", "za": "ZA", "tr": "TR"}


def place_of(location: str | None, url: str = "", source: str = "", company: Company | None = None, title: str = "") -> places.Place:
    """Where the posting is. When the location names no country, fall back to the site's country (.de, workable-nl ...) or the company's."""
    from urllib.parse import urlparse
    p = places.parse(location, title)
    if p.countries or p.remote_scope not in (None, "world") or (p.work_mode == "remote" and p.remote_scope == "world" and (location or "").strip().lower() not in ("remote", "")): return p
    host = urlparse(url or "").netloc.lower(); tld = host.rsplit(".", 1)[-1] if "." in host else ""
    guess = "NL" if ("werkenbij" in host or source.endswith("-nl")) else _TLD.get(tld) or (company.country if company is not None and company.country else None)
    if guess: p.countries = [guess]; p.remote_scope = None                       # bare "Remote" on a Dutch site: remote within the Netherlands
    return p


def store_jobs(db: Session, company: Company, jobs: list[dict], source="company-site", expire=True) -> int:
    seen, new = set(), 0
    for j in jobs:
        url, title = j.get("url"), (j.get("title") or "").strip()
        if not url or not title or not looks_like_job(title, url): continue
        seen.add(url)
        pol = policy_service.current()
        pl = place_of(j.get("location"), url, source, company, title)
        if not places.wanted(pl, pol["countries"], pol["keep_remote"]): continue        # storage policy: only the countries the operator crawls for
        desc = j.get("description") or ""
        sk = skills_of(title, desc)
        domain = domains.classify(title, desc, sk)
        keep = pol["keep_domains"]
        if keep and domain not in keep: continue                            # storage policy: only the domains the operator asked for
        lang = scoring.language(title, desc)
        jt = "internship" if j.get("kind") == "internship" and scoring.job_type(title, j.get("location", "")) in ("job", "junior") else scoring.job_type(title, j.get("location", ""))
        lo, hi, per = money(desc)
        posted = dates.norm_date(j.get("posted_at"))
        posted = dt.date.fromisoformat(posted) if posted else None
        if pol["max_job_age_days"] and posted and (dt.date.today() - posted).days > pol["max_job_age_days"]: continue   # storage policy: no old postings
        loc = j.get("location") or ""
        dk = dedupe_key(company.id, title, loc)
        ex = db.scalar(select(Job).where(Job.url == url))
        if ex:
            ex.last_seen = now(); ex.status = "open"; ex.posted_at = ex.posted_at or posted
            if len(desc) > len(ex.description or ""): ex.description = desc
            continue
        if db.scalar(select(Job.id).where(Job.dedupe_key == dk, Job.status == "open")):
            continue                                                        # same posting under another URL
        job = Job(company_id=company.id, title=title, location=loc, city=city_of(loc), url=url, source=source, description=desc, category=sectors.category_of(sec := sectors.classify(title)), sector=sec, country=pl.country or "NL", countries=pl.countries, work_mode=pl.work_mode, remote_scope=pl.remote_scope, domain=domain,
                  job_type=jt, language=lang, remote=pl.work_mode != "onsite", salary_min=lo, salary_max=hi, salary_period=per,
                  posted_at=posted, dedupe_key=dk)
        job.skills = [JobSkill(skill=s) for s in sk]
        db.add(job); new += 1
    if seen and expire:
        db.execute(update(Job).where(Job.company_id == company.id, Job.status == "open", Job.url.notin_(seen)).values(status="expired"))
    db.flush()
    return new


def ensure_logo(db: Session, c: Company):
    path = os.path.join(LOGO_DIR, os.path.basename(c.logo)) if c.logo else None
    if not c.website or (c.logo and c.description and path and os.path.exists(path)): return
    try:
        html = discovery.get(c.website, check_robots=False)
        if not html: return
        p = discovery.fetch_logo(c.website, html, c.id)
        if p: c.logo = p
        soup = BeautifulSoup(html, "lxml")
        m = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if m and m.get("content") and not c.description: c.description = m["content"].strip()[:400]
    except Exception: pass


def scan_company(db: Session, company_id: int) -> int:
    """Crawl one company's own career site and store what it lists. Returns number of NEW jobs."""
    c = db.get(Company, company_id)
    if not c or (c.ats or "").startswith("board:"): return 0
    cd = {k: getattr(c, k) for k in ("name", "website", "careers_url", "ats", "ats_slug", "resolved_via")}
    try: r = discovery.scan_company(cd)
    except Exception as e: r = dict(jobs=[], note=f"error: {e}", website=c.website, careers_url=c.careers_url, ats=c.ats, ats_slug=c.ats_slug, resolved_via=c.resolved_via)
    c.website, c.careers_url, c.ats, c.ats_slug, c.resolved_via = r["website"], r["careers_url"], r["ats"], r["ats_slug"], r["resolved_via"]
    n = len(r["jobs"])
    c.last_scan, c.scan_note = now(), f"{r['note']} ({n} postings)"
    c.sponsor_status, c.sponsor_match = sponsor_service.check(db, c.name, c.kvk)
    failed = n == 0 and any(k in r["note"] for k in ("not found", "no careers", "error"))
    c.fail_count = 0 if n else min((c.fail_count or 0) + (1 if failed else 0), 6)
    from . import schedule_service
    hours = schedule_service.current()["revisit_hours"] if n else 168 * (1 + c.fail_count)      # back off on dead ends
    c.next_scan = now() + dt.timedelta(hours=hours)
    db.commit()
    ensure_logo(db, c); db.commit()
    new = store_jobs(db, c, r["jobs"]); db.commit()
    return new
