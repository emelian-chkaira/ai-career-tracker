"""Data export, account deletion, sessions."""
A = "/api/v1/me"


def test_export_has_data_but_no_secrets(client, make_user):
    h, _ = make_user(); client.put(f"{A}/cv", json={"cv": {"name": "Sam", "skills": ["python"]}}, headers=h)
    client.put("/api/v1/ai/settings", json={"provider": "groq", "model": "m", "api_key": "sk-secret-123"}, headers=h)
    r = client.get(f"{A}/export", headers=h); assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    d = r.json(); assert d["account"]["email"] == "user@example.com" and d["cv"]["name"] == "Sam" and d["ai_settings"]["provider"] == "groq"
    assert "sk-secret-123" not in r.text and "password" not in r.text.lower()


def test_delete_account_needs_exact_email_and_removes_everything(client, make_user):
    h, _ = make_user(); client.put(f"{A}/cv", json={"cv": {"name": "Sam"}}, headers=h)
    assert client.post(f"{A}/account/delete", json={"confirm_email": "nope@example.com"}, headers=h).status_code == 400
    assert client.post(f"{A}/account/delete", json={"confirm_email": "USER@example.com"}, headers=h).status_code == 204
    assert client.get("/api/v1/auth/me", headers=h).status_code in (401, 403)
    h2, _ = make_user(); assert client.get(f"{A}/cv", headers=h2).status_code == 404            # same e-mail can register again, with nothing left over


def test_sessions_list_and_sign_out_everywhere(client, make_user):
    h, reg = make_user(); client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "correct-horse-1"})
    s = client.get(f"{A}/sessions", headers=h).json(); assert len(s) >= 2
    assert client.delete(f"{A}/sessions/{s[0]['id']}", headers=h).status_code == 204 and len(client.get(f"{A}/sessions", headers=h).json()) == len(s) - 1
    assert client.delete(f"{A}/sessions", headers=h).status_code == 204 and client.get(f"{A}/sessions", headers=h).json() == []


def test_follow_company_radius_and_source_health(client, make_user, db):
    from sqlalchemy import select
    from app.models import Job
    from app.services import ingest_service as ing, geo, search_service as ss
    h, _ = make_user(); c = ing.add_company(db, "Acme"); ing.store_jobs(db, c, [dict(title="Dev", location="Amsterdam", url="https://a.nl/1", description="python", posted_at=None)]); db.commit()
    assert client.post(f"{A}/following/{c.id}", headers=h).status_code == 201 and client.post(f"{A}/following/{c.id}", headers=h).status_code == 201     # idempotent
    f = client.get(f"{A}/following", headers=h).json(); assert len(f) == 1 and f[0]["name"] == "Acme"
    assert client.delete(f"{A}/following/{c.id}", headers=h).status_code == 204 and client.get(f"{A}/following", headers=h).json() == []
    assert "haarlem" in geo.within("Amsterdam", 30) and "groningen" not in geo.within("Amsterdam", 30) and geo.within("Nowhereville", 10) is None
    j = db.scalar(select(Job)); j.city = "Haarlem"; db.commit()
    assert j.id in ss.run(db, ss.SearchParams(near="Amsterdam", radius_km=30, category=None))["ids"] and j.id not in ss.run(db, ss.SearchParams(near="Groningen", radius_km=30, category=None))["ids"]
    assert client.get("/api/v1/admin/source-health", headers=h).json()["totals"]["companies"] >= 1
