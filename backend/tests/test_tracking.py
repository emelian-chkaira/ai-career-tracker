"""Application tracking: timeline, applied/follow-up dates, reminders, funnel stats, mail-accept events."""
import datetime as dt
from sqlalchemy import select
from app.models import Job, Notification
from app.services import ingest_service as ing, tracking_service as ts

A = "/api/v1/me"


def _job(db, title="Backend Engineer", url="https://acme.nl/1"):
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [dict(title=title, location="Amsterdam, Netherlands", url=url, description="Python. " * 30, posted_at=None)]); db.commit()
    return db.scalar(select(Job).where(Job.title == title))


def test_stage_changes_write_timeline_and_dates(client, make_user, db):
    h, _ = make_user(); j = _job(db)
    client.put(f"{A}/jobs/{j.id}", json={"stage": "shortlisted"}, headers=h)
    r = client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h).json()
    assert r["applied_at"] and r["follow_up_at"] and r["follow_up_note"]                                   # stamped + a follow-up a week later
    client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h)                                   # same stage again: no duplicate entry
    ev = client.get(f"{A}/jobs/{j.id}/track", headers=h).json()["events"]
    assert [e["meta"]["to"] for e in ev][::-1] == ["shortlisted", "applied"]
    r = client.put(f"{A}/jobs/{j.id}", json={"stage": "rejected"}, headers=h).json()
    assert r["follow_up_at"] is None                                                                       # nothing left to chase


def test_notes_contact_follow_up_and_events(client, make_user, db):
    h, _ = make_user(); j = _job(db)
    assert client.post(f"{A}/jobs/{j.id}/events", json={"title": "x"}, headers=h).status_code == 404        # not in the pipeline yet
    client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h)
    when = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=3)).isoformat()
    r = client.patch(f"{A}/jobs/{j.id}/track", json={"contact": "Ana, recruiter", "follow_up_at": when, "follow_up_note": "Ask for feedback", "offer_details": "4800/mo"}, headers=h).json()
    assert r["contact"] == "Ana, recruiter" and r["follow_up_note"] == "Ask for feedback"
    e = client.post(f"{A}/jobs/{j.id}/events", json={"kind": "interview", "title": "Technical interview", "body": "Zoom, 14:00"}, headers=h); assert e.status_code == 201
    assert client.post(f"{A}/jobs/{j.id}/events", json={"kind": "bogus", "title": "x"}, headers=h).status_code == 400
    assert client.delete(f"{A}/jobs/{j.id}/events/{e.json()['id']}", headers=h).status_code == 204
    stage_ev = next(x for x in client.get(f"{A}/jobs/{j.id}/track", headers=h).json()["events"] if x["kind"] == "stage")
    assert client.delete(f"{A}/jobs/{j.id}/events/{stage_ev['id']}", headers=h).status_code == 400          # history is kept
    assert client.patch(f"{A}/jobs/{j.id}/track", json={"clear_follow_up": True}, headers=h).json()["follow_up_at"] is None
    assert client.get(f"{A}/pipeline", headers=h).json()["items"][0]["contact"] == "Ana, recruiter"


def test_other_users_cannot_touch_my_events(client, make_user, db):
    h, _ = make_user(); h2, _ = make_user("other@example.com"); j = _job(db)
    client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h)
    e = client.post(f"{A}/jobs/{j.id}/events", json={"title": "note"}, headers=h).json()
    assert client.delete(f"{A}/jobs/{j.id}/events/{e['id']}", headers=h2).status_code == 404
    assert client.get(f"{A}/jobs/{j.id}/track", headers=h2).json() == {"track": None, "events": []}


def test_due_follow_up_notifies_once(client, make_user, db):
    h, u = make_user(); j = _job(db)
    client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h)
    past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
    client.patch(f"{A}/jobs/{j.id}/track", json={"follow_up_at": past}, headers=h)
    assert ts.notify_due(db) == 1 and ts.notify_due(db) == 0                                                # reminded once per date
    assert db.scalar(select(Notification.title).where(Notification.kind == "follow_up")).startswith("Follow up")
    fu = client.get(f"{A}/follow-ups", headers=h).json(); assert fu[0]["overdue"] and fu[0]["title"] == "Backend Engineer"


def test_funnel_stats(client, make_user, db):
    h, _ = make_user(); a = _job(db, "Job A", "https://acme.nl/a"); b = _job(db, "Job B", "https://acme.nl/b"); _job(db, "Job C", "https://acme.nl/c")
    for j, stages in ((a, ["applied", "interview", "rejected"]), (b, ["applied"])):
        for s in stages: client.put(f"{A}/jobs/{j.id}", json={"stage": s}, headers=h)
    s = client.get(f"{A}/stats", headers=h).json()
    assert s["funnel"]["applied"] == 2 and s["funnel"]["interview"] == 1 and s["by_stage"]["rejected"] == 1 and s["active"] == 1
    assert s["response_rate"] == 0.5 and s["avg_days_to_response"] is not None


def test_tasks_crud_privacy_and_daily_series(client, make_user, db):
    from sqlalchemy import select
    from app.models import Job
    from app.services import ingest_service as ing
    h, _ = make_user(); c = ing.add_company(db, "Acme"); ing.store_jobs(db, c, [dict(title="Dev", location="Amsterdam", url="https://a.nl/1", description="x", posted_at=None)]); db.commit()
    j = db.scalar(select(Job)); A = "/api/v1/me"
    assert client.post(f"{A}/jobs/{j.id}/tasks", json={"title": "x"}, headers=h).status_code == 404            # not in the pipeline yet
    client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h)
    t = client.post(f"{A}/jobs/{j.id}/tasks", json={"title": "Send portfolio", "due_at": "2030-01-01T10:00:00Z"}, headers=h).json()
    assert client.get(f"{A}/tasks", headers=h).json()[0]["job_title"] == "Dev"
    assert client.patch(f"{A}/tasks/{t['id']}", json={"done": True}, headers=h).json()["done"] is True and client.get(f"{A}/tasks", headers=h).json() == []
    h2, _ = make_user("other@example.com"); assert client.patch(f"{A}/tasks/{t['id']}", json={"done": False}, headers=h2).status_code == 404
    assert client.delete(f"{A}/tasks/{t['id']}", headers=h).status_code == 204 and client.get(f"{A}/jobs/{j.id}/tasks", headers=h).json() == []
    s = client.get(f"{A}/stats", headers=h).json()["applications_per_day"]; assert len(s) == 30 and s[-1]["count"] == 1


def test_finer_stages_count_as_active_and_in_funnel(client, make_user, db):
    h, _ = make_user(); j = _job(db)
    for st in ("applied", "assessment", "team_match", "final_round"): assert client.put(f"{A}/jobs/{j.id}", json={"stage": st}, headers=h).status_code == 200
    s = client.get(f"{A}/stats", headers=h).json()
    assert s["active"] == 1 and s["by_stage"]["final_round"] == 1 and s["funnel"]["team_match"] == 1 and s["funnel"]["interview"] == 1 and s["funnel"]["offer"] == 0
    assert client.put(f"{A}/jobs/{j.id}", json={"stage": "nonsense"}, headers=h).status_code in (400, 422)


def test_stats_day_range_and_sponsor_company_filter(client, make_user, db):
    h, _ = make_user(); _job(db)
    assert len(client.get(f"{A}/stats?days=7", headers=h).json()["applications_per_day"]) == 7
    assert len(client.get(f"{A}/stats?days=90", headers=h).json()["applications_per_day"]) == 90
    assert client.get(f"{A}/stats?days=3", headers=h).status_code == 422
    assert client.get("/api/v1/companies?sponsor=true").json()["total"] == 0             # Acme is not an IND sponsor
