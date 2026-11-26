"""The public demo's snapshot of a real crawl: employers, their logos and open jobs, so the demo looks like a live install.

backend/seed_live/ holds companies.csv.gz, jobs.csv.gz, logos/*.png and VERSION. It is deliberately limited, because it is public:
  - only jobs read from employers' own career pages (nothing from job boards);
  - a short excerpt of each description, with e-mail addresses, phone numbers and links removed: the full text stays on the employer's site;
  - nothing about any user (no accounts, CVs, mail, applications or operator notes).
`export` is run by a maintainer on a machine with a real crawl; `apply` runs when the demo server starts."""
import csv, gzip, io, json, os, re, shutil, datetime as dt
from pathlib import Path
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Company, Job, JobSkill, KV
from . import ingest_service as ing

DIR = Path(__file__).resolve().parents[2] / "seed_live"
VERSION_KEY = "demo_snapshot"
CO = ["name", "website", "careers_url", "ats", "ats_slug", "sponsor_status", "sponsor_match", "kvk", "city", "country", "description", "logo"]
JB = ["company", "title", "location", "city", "url", "category", "sector", "country", "countries", "work_mode", "remote_scope", "domain", "job_type", "language", "remote",
      "posted_at", "first_seen", "excerpt", "skills"]
MORE = "Open the original posting for the full text."
_PRIVATE = re.compile(r"(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.-]+|(?<![\w/])\+?\d[\d\s().-]{7,}\d)")


def excerpt(description: str | None, limit: int = 280) -> str:
    """The first sentences of a posting, without contact details or links."""
    s = re.sub(r"\s+", " ", _PRIVATE.sub("", description or "")).strip()
    if len(s) < 40: return ""
    if len(s) > limit: s = s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-") + "…"
    return f"{s}\n\n{MORE}"


def _write(path: Path, cols: list[str], rows: list[dict]) -> int:
    buf = io.StringIO(); w = csv.DictWriter(buf, cols); w.writeheader(); w.writerows(rows)
    path.write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))            # no timestamp: the same data gives the same file
    return len(rows)


def _read(name: str, base: Path) -> list[dict]:
    csv.field_size_limit(1_000_000)
    with gzip.open(base / name, "rt", newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def _small_logo(src: str, dest: Path, size: int = 96) -> bool:
    """Copy a logo as a small PNG. Re-encoding also drops anything that is not picture data; SVG files (which can carry script) are left out."""
    from PIL import Image                                                        # only the maintainer exporting needs Pillow
    if src.lower().endswith(".svg"): return False
    try:
        with Image.open(src) as im:
            im = im.convert("RGBA"); im.thumbnail((size, size)); im.save(dest, "PNG", optimize=True)
        return True
    except Exception: return False


def export(db: Session, base: Path = DIR, logo_dir: str | None = None) -> dict:
    logo_dir = logo_dir or ing.LOGO_DIR
    base.mkdir(parents=True, exist_ok=True); shutil.rmtree(base / "logos", ignore_errors=True); (base / "logos").mkdir()
    jobs = list(db.scalars(select(Job).where(Job.status == "open", Job.source == "company-site").order_by(Job.url)))
    with_jobs = {j.company_id for j in jobs}
    cos = [c for c in db.scalars(select(Company).order_by(Company.name, Company.id))
           if c.id in with_jobs or (c.website and not (c.source or "").startswith("board") and not (c.ats or "").startswith("board:"))]    # not employers known only through a job board
    names, rows, logos = {}, [], 0
    for c in cos:
        if c.name in names.values(): names[c.id] = c.name; continue
        names[c.id] = c.name; file = ""
        src = os.path.join(logo_dir, os.path.basename(c.logo)) if c.logo else ""
        if src and os.path.exists(src) and _small_logo(src, base / "logos" / f"seed-{c.id}.png"): file = f"seed-{c.id}.png"; logos += 1
        rows.append({**{k: getattr(c, k) or "" for k in CO if k not in ("logo", "description")}, "description": excerpt(c.description, 200).replace(f"\n\n{MORE}", ""), "logo": file})
    skills: dict[int, list[str]] = {}
    for jid, s in db.execute(select(JobSkill.job_id, JobSkill.skill).order_by(JobSkill.job_id, JobSkill.skill)): skills.setdefault(jid, []).append(s)
    out = [{"company": names[j.company_id], "title": j.title, "location": j.location or "", "city": j.city or "", "url": j.url, "category": j.category, "sector": j.sector,
            "country": j.country, "countries": "|".join(j.countries or []), "work_mode": j.work_mode, "remote_scope": j.remote_scope or "", "domain": j.domain or "",
            "job_type": j.job_type, "language": j.language, "remote": "1" if j.remote else "", "posted_at": j.posted_at.isoformat() if j.posted_at else "",
            "first_seen": j.first_seen.date().isoformat(), "excerpt": excerpt(j.description), "skills": "|".join(skills.get(j.id, []))} for j in jobs if j.company_id in names]
    n_c = _write(base / "companies.csv.gz", CO, rows); n_j = _write(base / "jobs.csv.gz", JB, out)
    (base / "VERSION").write_text(dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d.%H%M") + "\n")
    return {"companies": n_c, "jobs": n_j, "logos": logos, "employers_with_jobs": len({r["company"] for r in out})}


def install_logos(base: Path = DIR, logo_dir: str | None = None) -> int:
    """Every start: the host's disk is wiped on each deploy, so the logo files are copied again."""
    logo_dir = logo_dir or ing.LOGO_DIR; os.makedirs(logo_dir, exist_ok=True); n = 0
    for p in (base / "logos").glob("seed-*.png"): shutil.copyfile(p, os.path.join(logo_dir, p.name)); n += 1
    return n


def apply(db: Session, base: Path = DIR, logo_dir: str | None = None) -> dict:
    """Bring the demo database to this snapshot, once per version. Nothing is deleted: jobs that are not in the snapshot are marked
    expired (they leave every list but stay in people's pipelines), employers are updated or added by name."""
    if not settings.demo_mode: return {"skipped": "only the public demo loads the snapshot"}
    if not (base / "VERSION").exists(): return {"skipped": "no snapshot"}
    out = {"logos": install_logos(base, logo_dir), "companies": 0, "jobs_added": 0, "jobs_updated": 0, "jobs_expired": 0}
    version = (base / "VERSION").read_text().strip()
    mark = db.get(KV, VERSION_KEY)
    if mark and mark.v == version: return {**out, "skipped": "this snapshot is already loaded"}
    now = dt.datetime.now(dt.timezone.utc)
    have: dict[str, Company] = {}
    for c in db.scalars(select(Company).order_by(Company.id)): have.setdefault(c.name, c)
    for r in _read("companies.csv.gz", base):
        c = have.get(r["name"])
        if not c: c = have[r["name"]] = Company(name=r["name"], source="snapshot", next_scan=None); db.add(c); out["companies"] += 1
        for k in CO[1:-1]:
            if r[k]: setattr(c, k, r[k])
        if r["logo"]: c.logo = f"logos/{r['logo']}"
    db.flush()
    existing = {j.url: j for j in db.scalars(select(Job))}
    seen: set[str] = set()
    for r in _read("jobs.csv.gz", base):
        c = have.get(r["company"])
        if not c or r["url"] in seen: continue
        seen.add(r["url"])
        values = dict(company_id=c.id, title=r["title"], location=r["location"] or None, city=r["city"] or None, source="company-site", description=r["excerpt"] or None,
                      category=r["category"] or "other", sector=r["sector"] or "other", country=r["country"] or "NL", countries=[x for x in r["countries"].split("|") if x] or [r["country"] or "NL"],
                      work_mode=r["work_mode"] or "onsite", remote_scope=r["remote_scope"] or None, domain=r["domain"] or None, job_type=r["job_type"] or "job",
                      language=r["language"] or "english_ok", remote=bool(r["remote"]), posted_at=dt.date.fromisoformat(r["posted_at"]) if r["posted_at"] else None,
                      first_seen=dt.datetime.fromisoformat(r["first_seen"]).replace(tzinfo=dt.timezone.utc), last_seen=now, status="open", dedupe_key=ing.dedupe_key(c.id, r["title"]))
        j = existing.get(r["url"])
        if j:
            for k, v in values.items(): setattr(j, k, v)
            out["jobs_updated"] += 1
        else:
            j = Job(url=r["url"], **values)
            j.skills = [JobSkill(skill=s) for s in dict.fromkeys(filter(None, r["skills"].split("|")))]
            db.add(j); out["jobs_added"] += 1
    db.flush()
    old = [j.id for url, j in existing.items() if url not in seen and j.status == "open"]
    if old: db.execute(update(Job).where(Job.id.in_(old)).values(status="expired")); out["jobs_expired"] = len(old)
    mark = mark or KV(k=VERSION_KEY); mark.v = version; db.add(mark)
    db.commit(); return out
