"""EXPERIMENTAL job boards: what a board search will look for (the plan), each board's health, and the run itself.

plan()   -> which boards, which search terms (and why each term is there), which countries, and the term x country searches in order.
           Shown on the Crawler page before anything runs, so nobody has to guess what "Search job boards" searches for.
health() -> per board: last success, last error, jobs found, and a cool-down after a block (rest first, ask again later).
run()    -> executes a plan, one board at a time, skipping boards that are resting, and reports per search and per board."""
import datetime as dt, json, re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.crawler import boards, places, sectors
from app.models import KV, User, Company
from . import policy_service

KEY = "board_health"
BLOCK_RX = re.compile(r"\b(429|403|blocked|too many requests|rate.?limit|captcha)\b", re.I)
REST_AFTER_BLOCK = {"linkedin": 10, "glassdoor": 15}                         # minutes; doubles for each block in a row, at most 4 hours
REST_AFTER_ERROR = 5
MAX_TERMS = 12
now = lambda: dt.datetime.now(dt.timezone.utc)


# ------------------------------------------------------------------ health
def _load(db: Session) -> dict:
    r = db.get(KV, KEY)
    try: return json.loads(r.v) if r and r.v else {}
    except ValueError: return {}


def _save(db: Session, h: dict):
    r = db.get(KV, KEY) or KV(k=KEY); r.v = json.dumps(h); db.add(r); db.commit()


def resting(h: dict, site: str) -> str | None:
    until = (h.get(site) or {}).get("rest_until")
    return until if until and until > now().isoformat() else None


def record(db: Session, site: str, found: int, error: str | None) -> dict:
    """Remember how a board answered. A block makes it rest; a success clears the streak."""
    h = _load(db); s = h.get(site) or {}
    s["last_run"] = now().isoformat(); s["runs"] = s.get("runs", 0) + 1
    if error:
        blocked = bool(BLOCK_RX.search(error)); s["blocks_in_row"] = s.get("blocks_in_row", 0) + 1 if blocked else s.get("blocks_in_row", 0)
        mins = min(240, REST_AFTER_BLOCK.get(site, 15) * 2 ** max(0, s["blocks_in_row"] - 1)) if blocked else REST_AFTER_ERROR
        s.update(last_error=error[:300], error_at=s["last_run"], kind="blocked" if blocked else "error", errors=s.get("errors", 0) + 1,
                 rest_until=(now() + dt.timedelta(minutes=mins)).isoformat())
    else:
        s.update(last_ok=s["last_run"], blocks_in_row=0, rest_until=None, found_last=found, found_total=s.get("found_total", 0) + found)
    h[site] = s; _save(db, h); return s


def health(db: Session) -> list[dict]:
    h = _load(db); on = configured()
    return [{"site": k, "label": v["label"], "note": v["note"], "enabled": k in on, "resting_until": resting(h, k), **(h.get(k) or {})} for k, v in boards.INFO.items()]


def configured() -> list[str]:
    return [s for s in (x.strip().lower() for x in settings.board_sites.split(",")) if s in boards.SITES]


# ------------------------------------------------------------------ plan
def default_terms(db: Session) -> list[dict]:
    """Search terms with their origin: titles people typed in their preferences first, then the preset titles of the fields they chose."""
    typed: dict[str, int] = {}; preset: dict[str, set] = {}
    for u in db.scalars(select(User).where(User.is_active.is_(True))):
        pr = u.profile or {}
        for t in pr.get("titles") or []:
            k = t.strip()
            if k: typed[k] = typed.get(k, 0) + 1
        if not pr.get("titles"):
            for s in pr.get("sectors") or []:
                for t in sectors.PRESETS.get(s, {}).get("titles", [])[:3]: preset.setdefault(t, set()).add(sectors.PRESETS[s]["label"])
    out = [{"term": t, "from": f"job title in {n} user{'s’' if n > 1 else '’s'} preferences"} for t, n in sorted(typed.items(), key=lambda x: -x[1])]
    out += [{"term": t, "from": f"suggested title for {', '.join(sorted(f))} (users chose that field, no titles)"} for t, f in preset.items() if t not in typed]
    if not out: out = [{"term": t, "from": "fallback: nobody has chosen titles or fields yet"} for t in ("software engineer", "data engineer", "developer")]
    return out[:MAX_TERMS]


def plan(db: Session, sites: list[str] | None = None, terms: list[str] | None = None, countries: list[str] | None = None) -> dict:
    h = _load(db)
    sites = [s for s in (sites or configured()) if s in boards.SITES]
    tlist = [{"term": t.strip(), "from": "chosen for this run"} for t in dict.fromkeys(terms or []) if t and t.strip()] or default_terms(db)
    cs = [c for c in (countries or policy_service.current()["countries"] or ["NL"]) if c in places.COUNTRIES]
    cap = max(1, settings.board_max_searches)
    pairs = [(t["term"], c) for c in cs for t in tlist]
    searches = []
    for term, c in pairs[:cap]:
        per = []
        for s in sites:
            skip = boards.applies(s, c) or (f"resting after an error until {resting(h, s)[11:16]} UTC" if resting(h, s) else None)
            per.append({"site": s, "where": boards.where_for(s, c), "skip": skip})
        searches.append({"term": term, "country": c, "boards": per})
    return {"sites": sites, "terms": tlist, "countries": cs, "searches": searches, "dropped": max(0, len(pairs) - cap), "cap": cap,
            "results_per_board": settings.board_results, "requests": sum(1 for s in searches for b in s["boards"] if not b["skip"])}


# ------------------------------------------------------------------ run
def run(db: Session, p: dict, progress=None, on_step=None) -> dict:
    """Execute a plan. Each finished search is stored before the next starts, so a stopped run keeps what it found."""
    from . import ingest_service as ing
    stats = dict(searches=0, found=0, new_jobs=0, blocked=0, errors=0, skipped=0); per_site: dict[str, dict] = {}; logs: list[str] = []
    for i, s in enumerate(p["searches"]):
        line = []; new = 0
        for b in s["boards"]:
            site = b["site"]; ps = per_site.setdefault(site, dict(found=0, new=0, errors=0, skipped=0))
            reason = b["skip"] or (f"resting until {resting(_load(db), site)[11:16]} UTC" if resting(_load(db), site) else None)   # a block earlier in this run counts too
            if reason: ps["skipped"] += 1; stats["skipped"] += 1; line.append(f"{boards.INFO[site]['label']}: skipped ({reason})"); continue
            if on_step: on_step(current=f"{s['term']} in {s['country']}", current_site=site, current_where=b["where"], done=i, total=len(p["searches"]))
            age = policy_service.current()["max_job_age_days"]                      # "How recent" on the Crawler page: boards only return postings that new
            rows, err = boards.search_site(site, s["term"], s["country"], results=settings.board_results, hours_old=age * 24 if age else 168)
            st = record(db, site, len(rows), err)
            if err: ps["errors"] += 1; stats["blocked" if st.get("kind") == "blocked" else "errors"] += 1
            n = 0
            for company, job in rows:
                existed = ing.find_company(db, company)
                co = ing.add_company(db, company, website=job.get("company_site"), source=f"board:{site}")
                if not existed: co.country = s["country"]
                n += ing.store_jobs(db, co, [job], source=f"board:{site}", expire=False)
            db.commit(); ps["found"] += len(rows); ps["new"] += n; new += n; stats["found"] += len(rows)
            line.append(f"{boards.INFO[site]['label']}: {len(rows)} found, {n} new" + (f", {'blocked' if st.get('kind') == 'blocked' else 'error'}: {err[:80]}" if err else ""))
        stats["searches"] += 1; stats["new_jobs"] += new
        logs = (logs + [f"“{s['term']}” in {s['country']} → " + " · ".join(line)])[-20:]
        if progress: progress(done=i + 1, total=len(p["searches"]), current=f"{s['term']} in {s['country']}", current_site=None, per_site=per_site, log=logs, **stats)
    return stats
