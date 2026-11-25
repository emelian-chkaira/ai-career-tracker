"""Crawler speed settings, the IT-only default and the shortcuts that keep a full scan short."""
from app.core.config import settings
from app.crawler import boards
from app.services import perf_service


def test_focus_follows_the_profile_and_cv_not_a_global_default():
    from app.services import focus_service as fo
    secs, doms, ok = fo.signal({"titles": ["Mobile Developer"], "skills": ["Flutter", "Dart"]}, {})
    assert ok and "tech" in secs and "mobile" in doms and "software" in doms
    secs, doms, ok = fo.signal({"sectors": ["architecture"], "titles": ["Architect"]}, {})
    assert ok and "architecture" in secs and "tech" not in secs and not doms
    assert fo.signal({}, {})[2] is False                                              # nothing said yet -> no restriction
    secs, _, ok = fo.signal({}, {"experience": [{"title": "Backend Engineer"}], "skills": ["Python", "Postgres"]})
    assert ok and "tech" in secs                                                      # the CV alone is enough


def test_google_jobs_is_gone():
    assert "google" not in boards.SITES and "google" not in boards.INFO


def test_speed_settings_are_validated_and_saved(client, make_user, db):
    h, _ = make_user("admin@example.com")
    r = client.get("/api/v1/admin/perf", headers=h); assert r.status_code == 200 and r.json()["browser_slots"] >= 1
    r = client.put("/api/v1/admin/perf", json={"browser_slots": 99, "scan_threads": 0, "page_wait_ms": 100, "ats_first": False, "internship_pass": False}, headers=h).json()
    assert r["browser_slots"] == perf_service.MAX_SLOTS and r["scan_threads"] == 1 and r["page_wait_ms"] == 500 and r["ats_first"] is False
    assert client.delete("/api/v1/admin/perf", headers=h).json()["browser_slots"] == perf_service.defaults()["browser_slots"]


def test_only_admins_change_the_speed(client, make_user):
    h, _ = make_user("someone@example.com")
    assert client.put("/api/v1/admin/perf", json={"browser_slots": 2}, headers=h).status_code in (401, 403)


def test_scan_due_is_a_task_kind(client, make_user):
    h, _ = make_user("admin@example.com")
    assert client.post("/api/v1/admin/tasks", json={"kind": "scan_due"}, headers=h).status_code == 202
