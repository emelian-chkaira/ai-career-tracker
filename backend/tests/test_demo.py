import datetime as dt
from sqlalchemy import select
from app.core.config import settings
from app.models import User, Company, Job, UserJob
from app.services import demo_service


def _jobs(db, n=3):
    for i in range(n):
        c = Company(name=f"Demo Co {i}"); db.add(c); db.flush()
        db.add(Job(company_id=c.id, title="Software Engineer", url=f"https://example.com/{i}", status="open", source="company-site", dedupe_key=f"demo-{i}"))
    db.commit()


def test_demo_endpoint_is_off_by_default(client):
    assert client.get("/api/v1/auth/config").json()["demo"] is False
    assert client.post("/api/v1/auth/demo").status_code == 404


def test_guest_gets_a_private_account_with_sample_pipeline(client, db, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True); monkeypatch.setattr(settings, "first_user_admin", True); _jobs(db)
    a, b = client.post("/api/v1/auth/demo"), client.post("/api/v1/auth/demo")
    assert a.status_code == b.status_code == 201
    u = a.json()["user"]
    assert u["role"] == "user" and u["email_verified"] and u["profile"]["onboarded"] and u["email"] != b.json()["user"]["email"]
    stages = sorted(x.stage for x in db.scalars(select(UserJob).join(User, User.id == UserJob.user_id).where(User.email == u["email"])))
    assert stages == ["applied", "interview", "shortlisted"]


def test_old_guests_are_deleted_and_real_accounts_kept(client, db, make_user, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True); make_user()
    guest = client.post("/api/v1/auth/demo").json()["user"]["email"]
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=settings.demo_guest_days + 1)
    for u in db.scalars(select(User)): u.created_at = old
    db.commit()
    assert demo_service.purge_old(db) == 1
    left = [u.email for u in db.scalars(select(User))]
    assert left == ["user@example.com"] and guest not in left


def test_live_search_explains_itself_in_the_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    r = client.post("/api/v1/jobs/live-search?q=python")
    assert r.status_code == 409 and "own computer" in r.text
