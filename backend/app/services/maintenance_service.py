"""Database housekeeping: retention purge, applying the storage policy to existing rows, domain backfill, and clearing data.

Every action has a PREVIEW (how many rows it would touch) and returns counts. Jobs that someone saved to a pipeline (user_jobs) are never removed by purge/prune."""
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.crawler import domains
from . import policy_service

SAVED = "NOT EXISTS (SELECT 1 FROM user_jobs u WHERE u.job_id = jobs.id)"


def _count(db: Session, sql: str, **a) -> int: return db.execute(text(f"SELECT count(*) FROM jobs WHERE {sql}"), a).scalar() or 0
def _del(db: Session, sql: str, **a) -> int: return db.execute(text(f"DELETE FROM jobs WHERE {sql}"), a).rowcount


def _purge_clauses(p: dict) -> dict[str, tuple[str, dict]]:
    out = {}
    if p["delete_expired_after_days"]: out["expired_deleted"] = (f"status = 'expired' AND last_seen < now() - make_interval(days => :d) AND {SAVED}", {"d": p["delete_expired_after_days"]})
    if p["max_job_age_days"]: out["too_old_deleted"] = (f"COALESCE(posted_at, first_seen::date) < current_date - :d AND {SAVED}", {"d": p["max_job_age_days"]})
    return out


def _prune_clause(p: dict) -> tuple[str, dict] | None:
    """Jobs outside the fields collected: a tech job whose domain is not kept, or a job of a sector nobody here looks for."""
    if not p["keep_domains"] and not p["keep_sectors"]: return None
    sql = ("domain IS NOT NULL AND NOT ((sector = 'tech' AND (coalesce(array_length(CAST(:s AS text[]), 1), 0) = 0 OR 'tech' = ANY(CAST(:s AS text[]))) "
           "AND (coalesce(array_length(CAST(:k AS text[]), 1), 0) = 0 OR domain = ANY(CAST(:k AS text[])))) OR (sector <> 'tech' AND sector = ANY(CAST(:s AS text[])))) AND " + SAVED)
    return (sql, {"k": list(p["keep_domains"]), "s": list(p["keep_sectors"])})


def backfill_domains(db: Session, only_missing: bool = True) -> int:
    """Classify jobs that have no domain yet (or all of them) with the current rules."""
    q = "SELECT j.id, j.title, left(j.description, 3000), coalesce(string_agg(s.skill, ','), '') FROM jobs j LEFT JOIN job_skills s ON s.job_id = j.id " \
        + ("WHERE j.domain IS NULL " if only_missing else "") + "GROUP BY j.id"
    done = 0
    for jid, title, desc, sk in db.execute(text(q)).all():
        db.execute(text("UPDATE jobs SET domain = :d WHERE id = :i"), {"d": domains.classify(title, desc or "", sk.split(",") if sk else []), "i": jid}); done += 1
    db.commit(); return done


def purge_old(db: Session) -> dict:
    """Retention: delete long-expired jobs and jobs older than the age limit (never saved/pipeline jobs)."""
    out = {"expired_deleted": 0, "too_old_deleted": 0}
    for k, (sql, a) in _purge_clauses(policy_service.current()).items(): out[k] = _del(db, sql, **a)
    db.commit(); return out


def prune_to_policy(db: Session) -> dict:
    """Apply the CURRENT storage policy to jobs already stored: drop domains you no longer keep, plus everything purge_old removes."""
    backfill_domains(db)
    out = {"other_domains_deleted": 0}
    c = _prune_clause(policy_service.current())
    if c: out["other_domains_deleted"] = _del(db, c[0], **c[1])
    db.commit(); out.update(purge_old(db)); return out


def clear_jobs(db: Session) -> dict:
    """Delete ALL jobs (also removes users' pipeline entries for them). Companies, users and settings stay."""
    n = _del(db, "TRUE"); db.commit(); return {"jobs_deleted": n}


def clear_all(db: Session) -> dict:
    """Delete all jobs AND all companies. Users, accounts, saved searches and alerts stay."""
    j = _del(db, "TRUE"); c = db.execute(text("DELETE FROM companies")).rowcount; db.commit(); return {"jobs_deleted": j, "companies_deleted": c}


def preview(db: Session, action: str) -> dict:
    """What the action WOULD do right now, without changing anything."""
    p = policy_service.current()
    if action == "backfill_domains": return {"jobs_to_classify": _count(db, "domain IS NULL")}
    if action == "purge": return {k.replace("_deleted", "_to_delete"): _count(db, sql, **a) for k, (sql, a) in _purge_clauses(p).items()} or {"nothing_to_do": 0}
    if action == "prune":
        out = {}
        c = _prune_clause(p)
        if c: out["other_domains_to_delete"] = _count(db, c[0], **c[1])
        out.update({k.replace("_deleted", "_to_delete"): _count(db, sql, **a) for k, (sql, a) in _purge_clauses(p).items()})
        return out or {"nothing_to_do": 0}
    if action == "clear_jobs": return {"jobs_to_delete": _count(db, "TRUE"), "pipeline_entries_lost": db.execute(text("SELECT count(*) FROM user_jobs")).scalar() or 0}
    if action == "clear_all": return {"jobs_to_delete": _count(db, "TRUE"), "companies_to_delete": db.execute(text("SELECT count(*) FROM companies")).scalar() or 0,
                                      "pipeline_entries_lost": db.execute(text("SELECT count(*) FROM user_jobs")).scalar() or 0}
    raise KeyError(action)


ACTIONS = {"backfill_domains": lambda db: {"classified": backfill_domains(db)}, "purge": purge_old, "prune": prune_to_policy, "clear_jobs": clear_jobs, "clear_all": clear_all}
DESTRUCTIVE = {"clear_jobs", "clear_all"}


def merge_companies(db, keep_id: int, drop_ids: list[int]) -> dict:
    """Fold duplicate employers into one: their jobs (minus postings the kept one already has), inbox links and follows move over,
    empty fields are filled from the duplicates, then the duplicates are deleted. Jobs someone tracks are always kept."""
    from sqlalchemy import select, text as sql
    from app.models import Company, Job, UserJob, SavedSearch
    from . import ingest_service as ing
    keep = db.get(Company, keep_id); moved = dropped = 0
    have = set(db.scalars(select(Job.dedupe_key).where(Job.company_id == keep_id, Job.status == "open")))
    tracked = set(db.scalars(select(UserJob.job_id)))
    for did in drop_ids:
        d = db.get(Company, did)
        if not d or did == keep_id: continue
        for k in ("website", "careers_url", "ats", "ats_slug", "city", "address", "logo", "description", "kvk"):
            if not getattr(keep, k) and getattr(d, k): setattr(keep, k, getattr(d, k))
        for j in db.scalars(select(Job).where(Job.company_id == did)):
            key = ing.dedupe_key(keep_id, j.title, j.location)
            if key in have and j.status == "open" and j.id not in tracked: db.delete(j); dropped += 1; continue
            j.company_id, j.dedupe_key = keep_id, key; have.add(key); moved += 1
        db.execute(sql("UPDATE mail_events SET company_id = :k WHERE company_id = :d"), {"k": keep_id, "d": did})
        for s in db.scalars(select(SavedSearch)):
            p = dict(s.params or {})
            if str(p.get("follow_company")) == str(did) or p.get("company_id") == did:
                if "follow_company" in p: p["follow_company"] = keep_id
                if p.get("company_id") == did: p["company_id"] = keep_id
                s.params = p
        db.flush(); db.delete(d)
    db.commit()
    return {"kept": keep.name, "jobs_moved": moved, "duplicate_jobs_removed": dropped}


def collapse_duplicates(db, progress=None) -> dict:
    """One role, one job, for what is already stored (new postings are folded on arrival, see ingest_service.fold).
    1. Titles that are link labels ('Skip to main content') get the title from their link, or are removed.
    2. Every job gets the new role key; open jobs with the same key at the same employer are folded into one:
       a job someone tracks wins, then the employer's own page over a job board, then the oldest. Tracked duplicates are never deleted."""
    from sqlalchemy import select, text as sql
    from app.crawler import dedupe, sectors, places
    from app.models import Job
    from . import ingest_service as ing
    tracked = {r[0] for r in db.execute(sql("SELECT DISTINCT job_id FROM user_jobs"))}
    fixed = removed = 0
    for j in db.scalars(select(Job).where(Job.status == "open")):
        if not dedupe.nav_label(j.title): continue
        t = dedupe.title_from_url(j.url)
        if t:
            j.title = t; j.sector = sectors.classify(t); j.category = sectors.category_of(j.sector); fixed += 1
        elif j.id not in tracked:
            db.delete(j); removed += 1
    db.flush()
    split = _split_wrong_groups(db)
    rows = db.execute(sql("SELECT id, company_id, title FROM jobs")).all()
    keys = [dict(id=i, k=dedupe.role_key(c, t)) for i, c, t in rows]
    for k in range(0, len(keys), 2000):
        db.execute(sql("UPDATE jobs SET dedupe_key = :k WHERE id = :id AND dedupe_key IS DISTINCT FROM :k"), keys[k:k + 2000])
    db.commit()
    groups = db.execute(sql("""SELECT company_id, dedupe_key, array_agg(id ORDER BY id) FROM jobs WHERE status = 'open' GROUP BY 1, 2 HAVING count(*) > 1""")).all()
    merged = 0
    for n, (_cid, _key, ids) in enumerate(groups):
        jobs = list(db.scalars(select(Job).where(Job.id.in_(ids))))
        jobs.sort(key=lambda x: (x.id not in tracked, ing.BOARD(x.source), not x.city, x.first_seen or x.last_seen, x.id))
        keep, rest = jobs[0], jobs[1:]
        for d in rest:
            if d.id in tracked: continue                                       # someone follows this one: leave it alone
            pl = places.Place(list(d.countries or []), d.work_mode or "onsite", d.remote_scope)
            ing.fold(keep, d.url, d.location or "", pl, d.source or "company-site", d.description or "")
            for a in d.alternates or []:
                if a["url"] != keep.url and all(a["url"] != b["url"] for b in keep.alternates or []): keep.alternates = [*(keep.alternates or []), a]
            db.delete(d); merged += 1
        if n % 50 == 0:
            db.commit()
            if progress: progress(groups=len(groups), done=n, merged=merged)
    for j in db.scalars(select(Job).where(Job.status == "open", sql("jsonb_array_length(jobs.alternates) > 0"))):      # tidy locations kept from before
        alts = [{**a, "location": dedupe.sane_location(a.get("location"))} for a in j.alternates]
        alts = [{**a, "city": a.get("city") or ing.city_of(a["location"])} for a in alts]
        if alts != j.alternates: j.alternates = alts
    db.commit()
    return {"titles_fixed": fixed, "link_labels_removed": removed, "wrong_groups_split": split, "duplicate_groups": len(groups), "jobs_merged": merged}



def _split_wrong_groups(db) -> int:
    """Undo groups that were formed by a junk title: when most of a job's other links name a different job in their address
    ('/jobs/factory-manager/' under 'Petroleum Engineer'), those links become jobs of their own again."""
    from sqlalchemy import select, text as sql
    from app.crawler import dedupe
    from app.models import Job, Company
    from . import ingest_service as ing
    n = 0
    for j in list(db.scalars(select(Job).where(Job.status == "open", sql("jsonb_array_length(jobs.alternates) > 1")))):
        named = [(a, dedupe.title_from_url(a["url"])) for a in j.alternates]
        other = [(a, t) for a, t in named if t and not dedupe.similar(t, j.title)]
        if len(other) * 2 < len(j.alternates): continue                          # most links agree with the title: a real multi-location role
        keep = [a for a in j.alternates if all(a["url"] != o["url"] for o, _ in other)]
        j.alternates = keep; db.flush()
        co = db.get(Company, j.company_id)
        for a, t in other:
            n += ing.store_jobs(db, co, [dict(title=t, location=a.get("location") or "", url=a["url"], description="")], source=a.get("source") or "company-site", expire=False)
    db.commit()
    return n
