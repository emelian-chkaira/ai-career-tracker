"""The date shown is the employer's own; without one it is unknown, and unknown is never counted as recent."""
import datetime as dt
from app.crawler import dates, discovery
from app.models import Company, Job
from app.services import ingest_service as ing, search_service as ss

today = dt.date.today()


def ld(value):
    return f'<script type="application/ld+json">{{"@type":"JobPosting","datePosted":{value}}}</script>'


def test_page_date():
    assert discovery.page_date(ld('"2026-11-10T08:00:00+01:00"')) == "2026-11-10"
    assert discovery.page_date(ld('{"date":"2026-11-09"}')) == "2026-11-09"
    assert discovery.page_date('<meta itemprop="datePosted" content="2026-11-11">') == "2026-11-11"
    assert discovery.page_date(ld('"2999-01-01"')) is None and discovery.page_date("<p>apply now</p>") is None


def test_thirty_plus_days_is_not_a_date():
    assert dates.norm_date("Posted 30+ Days Ago") is None
    assert dates.norm_date("Posted 3 Days Ago") == (today - dt.timedelta(days=3)).isoformat()


def jobs(db):
    c = Company(name="Acme"); db.add(c); db.flush()
    made = {k: Job(company_id=c.id, title=f"Developer {k}", url=f"https://acme.nl/jobs/{k}", description="x" * 300, posted_at=d, category="tech", sector="tech")
            for k, d in {"new": today, "old": today - dt.timedelta(days=60), "unknown": None}.items()}
    db.add_all(made.values()); db.commit()
    return {k: j.id for k, j in made.items()}


def test_filter_and_order(db):
    j = jobs(db)
    run = lambda **p: ss.run(db, ss.SearchParams(**p))["ids"]
    assert set(run()) == set(j.values())
    assert run(days=7) == [j["new"]]
    assert run(sort="newest") == [j["new"], j["old"], j["unknown"]]
    assert run(sort="oldest") == [j["old"], j["new"], j["unknown"]]


def test_fill_missing_dates_reads_each_page_once(db, monkeypatch):
    j = jobs(db); asked = []
    monkeypatch.setattr(discovery, "fetch_detail", lambda url: asked.append(url) or {"description": "", "posted_at": None})
    assert ing.fill_missing_dates(db) == {"checked": 1, "dated": 0}
    assert ing.fill_missing_dates(db) == {"checked": 0, "dated": 0} and len(asked) == 1
    assert db.get(Job, j["unknown"]).posted_at is None


def test_opening_a_job_reads_the_employers_date(client, db, monkeypatch):
    j = jobs(db)
    monkeypatch.setattr(discovery, "fetch_detail", lambda url: {"description": "short", "posted_at": "2026-11-10"})
    r = client.get(f"/api/v1/jobs/{j['unknown']}").json()
    assert r["posted_at"] == "2026-11-10" and r["description"] == "x" * 300      # a good description is kept


def test_a_page_that_does_not_answer_is_tried_again(db, monkeypatch):
    j = jobs(db)
    monkeypatch.setattr(discovery, "fetch_detail", lambda url: {})
    ing.fill_missing_dates(db)
    assert db.get(Job, j["unknown"]).date_checked_at is None
