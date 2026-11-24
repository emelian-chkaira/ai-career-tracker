import re
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload
from app.crawler import scoring, thresholds, search as onto
from app.models import Job, User, UserJob, JobScore
from app.schemas.job import JobOut, CompanyMini, SearchOut
from . import search_service as ss, fit_service as fs


def _salary(j: Job, profile: dict | None):
    if j.salary_min is None and j.salary_max is None: return None
    cat = (profile or {}).get("salary_category", "hsm_under30")
    return {"min": j.salary_min, "max": j.salary_max, "period": j.salary_period, "verdict": thresholds.verdict(j.salary_min, j.salary_max, j.salary_period, cat)}


def logo_url(v: str | None) -> str | None:
    """Stored as a bare filename or 'logos/x.png'; always expose an absolute path the API serves."""
    if not v: return None
    if v.startswith(('http://', 'https://', '/')): return v
    return '/logos/' + v.removeprefix('logos/')


def personalize(p: ss.SearchParams, user: User | None) -> tuple[ss.SearchParams, dict]:
    """scope=mine: fill every filter the user left empty from THEIR profile. The catalogue is shared; this is what makes it their own feed.
    Returns (params, applied) where applied lists what came from the profile, so the UI can say so and offer "All jobs"."""
    if not user:                                       # visitors: the catalogue's home ground, tech (they can pick another sector)
        if not p.sector and not p.category: return p.model_copy(update={"sector": ["tech"]}), {}
        return p, {}
    if p.scope != "mine": return p, {}
    pr = user.profile or {}; q = p.model_copy(deep=True); applied: dict = {}
    if not q.sector and not q.category and pr.get("sectors"): q.sector = list(pr["sectors"]); applied["sector"] = q.sector
    if not q.country and not q.region:
        cs = pr.get("countries") or ([pr["country"]] if pr.get("country") else []); rg = pr.get("regions") or []
        if cs or rg: q.country, q.region = list(cs), list(rg); applied.update({k: v for k, v in (("country", q.country), ("region", q.region)) if v})
    if not q.work_mode and pr.get("work_modes"): q.work_mode = list(pr["work_modes"]); applied["work_mode"] = q.work_mode
    if not q.city and not q.near and pr.get("cities") and pr.get("remote_ok", True) is not False: q.near_cities = list(pr["cities"]); applied["cities"] = q.near_cities
    if not q.job_type and not q.kind and pr.get("job_types"):
        want = list(pr["job_types"]); applied["job_type"] = want
        # most postings do not state a level ("job"): keep them unless the user only wants internships/traineeships
        q.job_type = want + (["job"] if "job" not in want and set(want) - {"internship", "traineeship"} else [])
    if not q.language and pr.get("english_only"): q.language = ["english_ok", "dutch_plus"]; applied["language"] = q.language
    if q.sponsor is None and pr.get("sponsor_needed"): q.sponsor = True; applied["sponsor"] = True
    # no automatic "fit" order: the feed opens newest first (a well-matched posting from weeks ago must not bury today's); "Profile match" stays one click away
    return q, applied


def to_out(j: Job, user: User | None = None, stages: dict | None = None, relevance=None, matched=None, snippet=None, full=False, ai: dict | None = None) -> JobOut:
    p = user.profile if user else None
    fit = why = None
    if user and scoring.has_signal(p):
        fit, why = scoring.fit(j.title, j.description or "", j.location or "", j.job_type, j.language, p, j.sector)
    c = j.company
    return JobOut(id=j.id, title=j.title, company=CompanyMini(id=c.id, name=c.name, logo=logo_url(c.logo), website=c.website, sponsor_status=c.sponsor_status, sponsor_match=c.sponsor_match),
                  location=j.location, city=j.city, country=j.country, countries=list(j.countries or []), work_mode=j.work_mode, remote_scope=j.remote_scope, url=j.url, source=j.source,
                  alternates=[{k: a.get(k) for k in ("url", "location", "city", "countries", "source", "work_mode")} for a in (j.alternates or [])][:30], job_type=j.job_type, category=j.category, sector=j.sector, domain=j.domain, language=j.language, remote=j.remote, salary=_salary(j, p),
                  posted_at=j.posted_at, first_seen=j.first_seen, status=j.status, skills=[s.skill for s in j.skills][:8], snippet=snippet if snippet is not None else (j.description or "")[:240],
                  relevance=relevance, matched=matched or [], fit=fit, fit_reason=why, ai=ai, stage=(stages or {}).get(j.id), description=(j.description if full else None))


def _snippets(db: Session, ids: list[int], q: str) -> dict[int, str]:
    pq = ss.parse_query(q); words = [w for g in onto.parse(pq["text"]) for w in g["strong"][:3]] + pq["phrases"]
    if not words or not ids: return {}
    tsq = " OR ".join(f'"{w}"' for w in dict.fromkeys(words) if w.strip())[:300]
    rows = db.execute(text("SELECT id, ts_headline('english', left(coalesce(description,''), 4000), websearch_to_tsquery('english', :q), 'MaxWords=32,MinWords=14,StartSel=<mark>,StopSel=</mark>,ShortWord=2') FROM jobs WHERE id = ANY(:ids)"), {"q": tsq, "ids": ids}).all()
    return {r[0]: r[1] for r in rows}


def search(db: Session, p: ss.SearchParams, user: User | None = None) -> SearchOut:
    if user: fs.ensure_match(db, user)
    p, applied = personalize(p, user)
    res = ss.run(db, p)
    res["info"]["profile"] = applied
    ids = res["ids"]
    if res["sort"] == "fit" and user:                    # personalised order: needs the candidate rows
        cand = db.scalars(select(Job).where(Job.id.in_(ids[:1500])).options(selectinload(Job.company))).all()
        fits = {j.id: scoring.fit(j.title, j.description or "", j.location or "", j.job_type, j.language, user.profile, j.sector)[0] for j in cand}
        ids = sorted(ids[:1500], key=lambda i: -fits.get(i, 0)) + ids[1500:]
    if res["sort"] == "best" and user:                   # one "match" order: the AI score; jobs the AI has not read yet count at 60% of the instant estimate
        cand = db.scalars(select(Job).where(Job.id.in_(ids[:1500])).options(selectinload(Job.company))).all()
        sc = {r.job_id: r.score for r in db.scalars(select(JobScore).where(JobScore.user_id == user.id, JobScore.job_id.in_(ids[:1500])))}
        best = {j.id: sc[j.id] if j.id in sc else 0.6 * scoring.fit(j.title, j.description or "", j.location or "", j.job_type, j.language, user.profile, j.sector)[0] for j in cand}   # an unscored job is only a guess: it ranks below an AI-confirmed good one
        ids = sorted(ids[:1500], key=lambda i: -best.get(i, 0)) + ids[1500:]
    if res["sort"] == "ai_fit" and user:                 # AI-scored jobs first (best first), unscored ones keep their order
        sc = {r.job_id: r.score for r in db.scalars(select(JobScore).where(JobScore.user_id == user.id, JobScore.job_id.in_(ids[:3000])))}
        ids = sorted(ids[:3000], key=lambda i: -sc.get(i, -1)) + ids[3000:]
    total = len(ids)
    page_ids = ids[(p.page - 1) * p.limit: p.page * p.limit]
    jobs = {j.id: j for j in db.scalars(select(Job).where(Job.id.in_(page_ids)).options(selectinload(Job.company), selectinload(Job.skills)))}
    stages = {}
    if user and page_ids: stages = {r.job_id: r.stage for r in db.scalars(select(UserJob).where(UserJob.user_id == user.id, UserJob.job_id.in_(page_ids)))}
    ai = {i: fs.out(r) for i, r in fs.scores_for(db, user.id, page_ids).items()} if user and page_ids else {}
    snips = _snippets(db, page_ids, p.q) if p.q.strip() and res["info"]["groups"] else {}
    items = [to_out(jobs[i], user, stages, res["relevance"].get(i), res["matched"].get(i), snips.get(i) or None, ai=ai.get(i)) for i in page_ids if i in jobs]
    return SearchOut(items=items, total=total, page=p.page, limit=p.limit, facets=ss.facets(db, ids), query=res["info"], sort=res["sort"])
