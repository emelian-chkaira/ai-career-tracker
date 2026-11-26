"""The public demo's snapshot: what goes into it, and loading it over older demo data without deleting anything."""
from PIL import Image
from app.models import Company, Job, UserJob
from app.services import snapshot_service as snap
from app.core.config import settings


def test_excerpt_is_short_and_has_no_contact_details():
    text = "We build energy software. Mail jane.doe@acme.com or call +31 6 1234 5678, see https://acme.com/x. " + "More words follow here. " * 40
    out = snap.excerpt(text)
    assert "@" not in out and "1234" not in out and "http" not in out and out.endswith(snap.MORE) and len(out) < 340
    assert snap.excerpt("too short") == ""


def test_export_leaves_out_boards_and_apply_expires_instead_of_deleting(db, make_user, tmp_path, monkeypatch):
    logos = tmp_path / "logos"; logos.mkdir(); Image.new("RGB", (400, 400), "red").save(logos / "1.png")
    real = Company(name="Acme", website="https://acme.nl", logo="logos/1.png", notes="my private note"); only_board = Company(name="Boardco", website="https://b.nl", source="board:indeed")
    db.add_all([real, only_board]); db.flush()
    job = lambda c, url, **kw: Job(company_id=c.id, title=kw.pop("title", "Backend Engineer"), url=url, description="We make good software for real people. " * 20, **kw)
    db.add_all([job(real, "https://acme.nl/1"), job(only_board, "https://indeed.com/2", source="board:indeed")]); db.commit()
    got = snap.export(db, base=tmp_path / "snap", logo_dir=str(logos))
    assert got == {"companies": 1, "jobs": 1, "logos": 1, "employers_with_jobs": 1}
    assert Image.open(next((tmp_path / "snap" / "logos").glob("*.png"))).size == (96, 96)

    # an older demo database: another job that someone is tracking
    db.query(Job).delete(); old = job(real, "https://acme.nl/old", title="Old Role"); db.add(old); db.commit()
    _, user = make_user()
    uid = user["user"]["id"] if "user" in user else user["id"]
    db.add(UserJob(user_id=uid, job_id=old.id, stage="applied")); db.commit()
    assert "skipped" in snap.apply(db, base=tmp_path / "snap")                       # a normal install is never touched
    monkeypatch.setattr(settings, "demo_mode", True)
    out = snap.apply(db, base=tmp_path / "snap", logo_dir=str(tmp_path / "served"))
    assert out["jobs_added"] == 1 and out["jobs_expired"] == 1 and (tmp_path / "served").exists()
    db.expire_all()
    assert {j.url: j.status for j in db.query(Job)} == {"https://acme.nl/1": "open", "https://acme.nl/old": "expired"}
    assert db.query(UserJob).count() == 1 and db.query(Company).filter_by(name="Acme").one().logo.startswith("logos/seed-")
    assert snap.apply(db, base=tmp_path / "snap", logo_dir=str(tmp_path / "served"))["skipped"]        # once per version
    from sqlalchemy import text; db.execute(text("DELETE FROM kv WHERE k = :k"), {"k": snap.VERSION_KEY}); db.commit()


def test_the_demo_never_fetches_the_full_posting(client, db, monkeypatch):
    from app.crawler import discovery
    c = Company(name="Acme"); db.add(c); db.flush()
    j = Job(company_id=c.id, title="Role", url="https://acme.nl/9", description=snap.MORE); db.add(j); db.commit()
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(discovery, "fetch_detail", lambda url: (_ for _ in ()).throw(AssertionError("fetched")))
    assert client.get(f"/api/v1/jobs/{j.id}").json()["description"] == snap.MORE
