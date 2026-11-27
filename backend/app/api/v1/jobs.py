from typing import Annotated
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload
from app.core import ratelimit
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import optional_user, current_user, client_ip
from app.models import Job, User, UserJob
from app.schemas.job import JobOut, SearchOut
from app.services import jobs_service, search_service as ss, task_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=SearchOut, summary="Search jobs (full-text + semantic + filters)")
def list_jobs(p: Annotated[ss.SearchParams, Query()], db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    return jobs_service.search(db, p, user)


@router.post("/search", response_model=SearchOut, summary="Same as GET /jobs, parameters in the JSON body (used by saved searches)")
def search_post(p: ss.SearchParams, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    return jobs_service.search(db, p, user)


@router.get("/sectors", summary="Sector presets (label, suggested titles and skills) and countries, with how many open jobs each has")
def sectors_list(db: Session = Depends(get_db)):
    from sqlalchemy import text
    from app.crawler import sectors
    n = dict(db.execute(text("SELECT sector, count(*) FROM jobs WHERE status='open' GROUP BY 1")).all())
    from app.crawler import places
    c = dict(db.execute(text("SELECT cc, count(*) FROM jobs, unnest(countries) cc WHERE status='open' GROUP BY 1")).all())
    m = dict(db.execute(text("SELECT work_mode, count(*) FROM jobs WHERE status='open' GROUP BY 1")).all())
    geo = places.public()
    return {"sectors": [{**x, "jobs": n.get(x["key"], 0)} for x in sectors.public()],
            "countries": [{**x, "jobs": c.get(x["code"], 0)} for x in geo["countries"]],
            "regions": [{**r, "jobs": db.execute(text("SELECT count(*) FROM jobs WHERE status='open' AND countries && CAST(:cs AS varchar[])"), {"cs": r["countries"]}).scalar()} for r in geo["regions"]],
            "work_modes": [{"key": k, "label": l, "jobs": m.get(k, 0)} for k, l in (("onsite", "On-site"), ("hybrid", "Hybrid"), ("remote", "Remote"))]}


@router.get("/coverage", summary="How far the crawler is for these countries/regions (default: your preferences): collected, jobs, employers, still to read")
def coverage(country: list[str] = Query([]), region: list[str] = Query([]), db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    from app.crawler import places
    from app.services import coverage_service
    codes = places.expand(country, region) if (country or region) else (coverage_service.wanted_countries(user.profile or {}) if user else [])
    return coverage_service.report(db, codes)


class CollectIn(BaseModel):
    country: list[str] = []
    region: list[str] = []


@router.post("/coverage/collect", summary="Ask the crawler to start collecting these countries (signed-in users; admins only when the crawler is closed)")
def collect(body: CollectIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    from app.crawler import places
    from app.services import coverage_service
    codes = places.expand(body.country, body.region)
    if len(codes) > 60: raise HTTPException(400, "too many countries at once")
    return coverage_service.ensure(db, user, codes)


@router.get("/suggest", summary="Autocomplete: skills, companies, job titles, concepts")
def suggest(q: str = Query("", max_length=60), db: Session = Depends(get_db)):
    q = q.strip().lower()
    if len(q) < 2: return {"skills": [], "companies": [], "titles": [], "concepts": []}
    from app.crawler.search import ONTOLOGY
    like = q + "%"
    return {
        "skills": db.execute(text("SELECT skill FROM job_skills WHERE skill LIKE :l GROUP BY skill ORDER BY count(*) DESC LIMIT 6"), {"l": like}).scalars().all(),
        "companies": db.execute(text("SELECT name FROM companies WHERE lower(name) LIKE :l OR lower(name) LIKE :l2 ORDER BY name LIMIT 6"), {"l": like, "l2": "% " + like}).scalars().all(),
        "titles": db.execute(text("SELECT title FROM jobs WHERE status='open' AND lower(title) LIKE :l2 GROUP BY title ORDER BY count(*) DESC LIMIT 6"), {"l2": "%" + like}).scalars().all(),
        "concepts": [k for k in ONTOLOGY if k.startswith(q)][:5],
    }


@router.post("/live-search", summary="Ask the worker to re-read the most relevant companies' career pages right now")
def live_search(request: Request, q: str = Query(..., min_length=2, max_length=120), db: Session = Depends(get_db)):
    if not ratelimit.allow("live:" + client_ip(request), 6, 120): raise HTTPException(429, "live search is rate limited")
    t = task_service.enqueue(db, "live_search", {"q": q.strip()})
    return {"task_id": t.id, "status": t.status}


@router.get("/{job_id}", response_model=JobOut)
def job_detail(job_id: int, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    j = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.company), selectinload(Job.skills)))
    if not j: raise HTTPException(404, "job not found")
    if j.source == "company-site" and (len(j.description or "") < 200 or (not j.posted_at and not j.date_checked_at)):   # lazily read the employer's own page
        from app.services import ingest_service
        try: ingest_service.read_posting(db, j); db.commit()
        except Exception: db.rollback()
    stage = db.get(UserJob, (user.id, j.id)) if user else None
    ai = None
    if user:
        from app.services import fit_service
        fit_service.ensure_match(db, user)
        ai = fit_service.out(fit_service.scores_for(db, user.id, [j.id]).get(j.id))
    return jobs_service.to_out(j, user, {j.id: stage.stage} if stage else {}, full=True, ai=ai)
