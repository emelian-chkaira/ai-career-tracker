"""Pause, resume and stop for worker tasks, and the new Companies / Jobs filters."""
import threading, time, pytest
from app.models import Task
from app.services import task_service as ts, ingest_service as ing


def test_pause_resume_stop(client, make_user, db):
    h, _ = make_user()
    t = ts.enqueue(db, "embed"); ts.claim(db); db.refresh(t)
    assert client.post(f"/api/v1/admin/tasks/{t.id}/pause", headers=h).json()["status"] == "paused"
    released = []
    def resume_later():
        time.sleep(0.5); client.post(f"/api/v1/admin/tasks/{t.id}/resume", headers=h); released.append(1)
    threading.Thread(target=resume_later).start()
    ts.progress(db, t, done=1)                                                     # waits while paused, carries on after resume
    assert released and t.status == "running" and t.progress == {"done": 1}
    client.post(f"/api/v1/admin/tasks/{t.id}/cancel", headers=h)
    with pytest.raises(ts.TaskStopped): ts.progress(db, t, done=2)
    ts.finish(db, t, "stopped by operator")
    db.refresh(t); assert t.status == "failed" and t.error == ts.STOPPED and t.finished_at
    ts.finish(db, t)                                                               # a late 'done' must not overwrite the stop
    db.refresh(t); assert t.status == "failed"


def test_gate_for_threads(db):
    t = ts.enqueue(db, "logos"); ts.claim(db); ts._gate.clear()
    ts.gate(t.id)                                                                  # running: passes
    t.status = "failed"; t.error = ts.STOPPED; db.commit(); ts._gate.clear()
    with pytest.raises(ts.TaskStopped): ts.gate(t.id)


def test_list_filters(client, make_user, db):
    h, _ = make_user()
    from app.services import policy_service
    policy_service.save(db, [], 0, 0, countries=[])
    c = ing.add_company(db, "Acme", city="Berlin"); c.country = "DE"
    J = lambda t, loc, n=[0]: dict(title=t, location=loc, url=f"https://acme.de/{(n.__setitem__(0, n[0] + 1), n[0])[1]}", description="")
    ing.store_jobs(db, c, [J("Python Developer", "Berlin, Germany (Hybrid)"), J("Architect", "Amsterdam")]); db.commit()
    ing.store_jobs(db, c, [J("Data Engineer", "Munich, Germany")], source="board:indeed", expire=False); db.commit()
    g = lambda **kw: {j["title"] for j in client.get("/api/v1/admin/jobs", headers=h, params=kw).json()["items"]}
    assert g(country="de") == {"Python Developer", "Data Engineer"} and g(city="berlin") == {"Python Developer"}
    assert g(work_mode="hybrid") == {"Python Developer"} and g(sector="architecture") == {"Architect"}
    assert g(source="board") == {"Data Engineer"} and g(source="site") == {"Python Developer", "Architect"}
    co = client.get("/api/v1/admin/companies", headers=h, params={"country": "DE", "city": "Berlin"}).json()
    assert [x["name"] for x in co["items"]] == ["Acme"] and co["items"][0]["country"] == "DE"
    f = client.get("/api/v1/admin/filters", headers=h).json()
    assert {"value": "DE", "n": 2} in f["jobs"]["country"] and {"value": "board:indeed", "n": 1} in f["jobs"]["source"]
    policy_service.reset(db)


def test_bulk_delete_respects_place_filters(client, make_user, db):
    h, _ = make_user("admin@example.com")                                          # an admin (deleting is admin-only)
    from app.services import policy_service
    from app.models import Job
    policy_service.save(db, [], 0, 0, countries=[])
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [dict(title="Go Developer", location="Berlin, Germany", url="https://a.de/1", description=""), dict(title="Java Developer", location="Amsterdam", url="https://a.nl/2", description="")]); db.commit()
    r = client.post("/api/v1/admin/jobs/bulk", headers=h, json={"action": "delete", "all_matching": True, "confirm": True, "country": "DE"}).json()
    assert r["changed"] == 1 and [j.title for j in db.query(Job)] == ["Java Developer"]
    policy_service.reset(db)


def test_board_search_is_not_restarted_by_a_worker_restart(db, monkeypatch):
    from app.workers import run
    monkeypatch.setattr(run.settings, "board_every_hours", 12)
    assert run._boards_due(db)                                                     # never ran
    ts.enqueue(db, "board_search")
    assert not run._boards_due(db)                                                 # ran just now: wait 12 h, restart or not
