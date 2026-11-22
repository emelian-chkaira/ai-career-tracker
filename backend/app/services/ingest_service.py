"""Write path of the crawler: companies, jobs (NL-only, deduped, skills/city extracted), scan results, logos."""
import re, hashlib, datetime as dt, os
from bs4 import BeautifulSoup
from sqlalchemy import select, update, func, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from app.core.config import settings
from app.crawler import discovery, nl, scoring, dates, domains, sectors, places, dedupe
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
def dedupe_key(cid, title, location=None):
    """The identity of a role at an employer (crawler/dedupe.py). Location is NOT part of it: the same role in three cities is one job."""
    return dedupe.role_key(cid, title)


def skills_of(title: str, desc: str) -> list[str]:
    return list(dict.fromkeys(cvmod.find_terms((title or "") + " \n " + (desc or "")[:8000])))[:25]


_LEGAL = re.compile(r"\b(b\.?\s?v\.?|n\.?\s?v\.?|v\.?\s?o\.?\s?f\.?|gmbh(\s*&\s*co\.?\s*kg)?|ag|kg|se|ltd\.?|limited|llc|l\.?l\.?c\.?|inc\.?|incorporated|corp\.?|corporation|co\.?|plc|s\.?\s?a\.?|s\.?p\.?a\.?|s\.?r\.?l\.?|sarl|sas|sp\.?\s?z\s?o\.?\s?o\.?|a/s|ab|oy|as|bvba|nl|nederland|netherlands|europe|international|holding|holdings)\s*$", re.I)


def norm_name(name: str | None) -> str:
    """Employer name for matching: no legal form (B.V., GmbH, Ltd, Inc ...), no 'Part of X' / '| tagline', no punctuation or case.
    'Prodrive Technologies B.V.' and 'Prodrive Technologies' match; so do 'Awin AG' and 'Awin'."""
    n = re.split(r"\s+[|–—]\s+|\s+-\s+part of\b|\s*\(", (name or "").strip(), maxsplit=1, flags=re.I)[0]
    for _ in range(3): n = _LEGAL.sub("", n.strip(" ,.-"))
    return re.sub(r"[^a-z0-9]+", "", n.lower().replace("&", "and"))


def find_company(db: Session, name: str) -> Company | None:
    """Exact name first, then the same name without legal form / punctuation / case."""
    c = db.scalar(select(Company).where(Company.name == name))
    if c: return c
    key = norm_name(name)
    if len(key) < 3: return None
    first = re.split(r"[^\w]+", name.strip(), maxsplit=1)[0]
    for cand in db.scalars(select(Company).where(Company.name.ilike(f"{first[:40]}%")).limit(50)):
        if norm_name(cand.name) == key: return cand
    return None


def add_company(db: Session, name, website=None, careers_url=None, kvk=None, city=None, address=None, source=None) -> Company:
    import html as _h
    name = _h.unescape(name).strip()
    c = find_company(db, name)
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


BOARD = lambda src: (src or "").startswith("board:")


def _alt(url, loc, pl, source) -> dict:
    loc = dedupe.sane_location(loc)
    return {"url": url, "location": loc[:200], "city": city_of(loc), "countries": pl.countries, "work_mode": pl.work_mode, "source": source, "seen": now().date().isoformat()}


def fold(job: Job, url: str, loc: str, pl, source: str, desc: str = "") -> None:
    """Add another posting of the same role to `job`: an extra location / link instead of a duplicate row.
    The employer's own page wins over a job board as the main link; countries are merged so country filters still find it."""
    alts = [dict(a) for a in (job.alternates or [])]
    if BOARD(job.source) and not BOARD(source):                                    # promote the employer's own posting to the main link
        alts.append(_alt(job.url, job.location, places.Place(list(job.countries or []), job.work_mode or "onsite", job.remote_scope), job.source))
        job.url, job.location, job.city, job.source = url, loc, city_of(loc), source
    elif url != job.url:
        hit = next((a for a in alts if a["url"] == url), None)
        if hit: hit["seen"] = now().date().isoformat()
        else: alts.append(_alt(url, loc, pl, source))
    job.alternates = alts[:60]
    job.countries = list(dict.fromkeys([*(job.countries or []), *pl.countries]))
    if len(desc) > len(job.description or ""): job.description = desc
    job.last_seen = now(); job.status = "open"


def clean_title(title: str, url: str) -> str | None:
    """The posting's real title: link labels such as 'Skip to main content' or 'mehr Informationen' are replaced by the title in the
    link ('/jobs/bauleiter-hochbau' -> 'Bauleiter Hochbau'), or the posting is dropped when the link names no job either."""
    t = dedupe.clean(title)
    if dedupe.nav_label(t): return dedupe.title_from_url(url)
    return t


def store_jobs(db: Session, company: Company, jobs: list[dict], source="company-site", expire=True) -> int:
    """Store what one source lists for one employer. Returns the number of NEW roles.
    One role = one job: the same role from another city, link or source is folded into the existing job (see fold)."""
    seen, new = set(), 0
    for j in jobs:
        url = j.get("url")
        title = clean_title(j.get("title") or "", url or "")
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
        loc = dedupe.sane_location(j.get("location") or "")
        dk = dedupe_key(company.id, title)
        ex = db.scalar(select(Job).where(Job.url == url))
        if ex:
            ex.last_seen = now(); ex.status = "open"; ex.posted_at = ex.posted_at or posted
            if len(desc) > len(ex.description or ""): ex.description = desc
            continue
        same = db.scalar(select(Job).where(Job.company_id == company.id, Job.dedupe_key == dk, Job.status == "open").order_by(Job.id).limit(1))
        if same:                                                            # the same role: another location, link or source
            fold(same, url, loc, pl, source, desc); continue
        job = Job(company_id=company.id, title=title, location=loc, city=city_of(loc), url=url, source=source, description=desc, category=sectors.category_of(sec := sectors.classify(title)), sector=sec, country=pl.country or "NL", countries=pl.countries, work_mode=pl.work_mode, remote_scope=pl.remote_scope, domain=domain,
                  job_type=jt, language=lang, remote=pl.work_mode != "onsite", salary_min=lo, salary_max=hi, salary_period=per,
                  posted_at=posted, dedupe_key=dk, alternates=[])
        job.skills = [JobSkill(skill=s) for s in sk]
        db.add(job); db.flush(); new += 1
    if seen and expire: _expire_missing(db, company.id, seen)
    db.flush()
    return new


def _expire_missing(db: Session, company_id: int, seen: set[str]):
    """After a full read of an employer's site: a role whose main link vanished but that is still listed elsewhere keeps living
    (one of its other links becomes the main one); links that vanished are dropped; a role listed nowhere any more expires."""
    for jb in db.scalars(select(Job).where(Job.company_id == company_id, Job.status == "open")):
        if BOARD(jb.source) and not jb.alternates: continue                       # job-board postings are not part of the employer's own list
        alts = [a for a in (jb.alternates or []) if a["url"] in seen or BOARD(a.get("source"))]
        if jb.url in seen or BOARD(jb.source):
            if len(alts) != len(jb.alternates or []): jb.alternates = alts
            continue
        live = [a for a in alts if a["url"] in seen]
        if live:
            top = live[0]; jb.url, jb.location, jb.city, jb.source = top["url"], top["location"], top.get("city"), top.get("source") or jb.source
            jb.alternates = [a for a in alts if a["url"] != top["url"]]
        else:
            jb.status = "expired"


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
