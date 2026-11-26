"""Several workers: one heartbeat each, one lead, no task or company taken twice, and a reason for every waiting task."""
from app.models import Company, Task
from app.services import schedule_service as sch, task_service as ts

H = "/api/v1"


def _wipe(db):
    from sqlalchemy import text
    db.execute(text("DELETE FROM kv WHERE k LIKE 'worker%'")); db.commit()


def _worker(db, wid, task=None):
    sch.beat(db, "running" if task else "idle", 0, task=task.kind if task else None, task_id=task.id if task else None, wid=wid)


def test_each_worker_has_its_own_heartbeat(db):
    _wipe(db)
    sch.beat(db, "idle", 2, wid="a:1", lead=True); sch.beat(db, "running", 1, task="internships", task_id=7, wid="b:2")
    st = sch.status(db)
    assert st["state"] == "running" and st["inflight"] == 3 and [w["id"] for w in st["workers"]] == ["a:1", "b:2"]
    sch.forget(db, "a:1")
    assert [w["id"] for w in sch.status(db)["workers"]] == ["b:2"]
    _wipe(db)


def test_only_one_lead(db):
    _wipe(db)
    assert sch.take_lead(db, "a:1") and sch.take_lead(db, "a:1") and not sch.take_lead(db, "b:2")
    sch.release_lead(db, "b:2")                                      # only the holder can hand it over
    assert not sch.take_lead(db, "b:2")
    sch.release_lead(db, "a:1")
    assert sch.take_lead(db, "b:2")
    _wipe(db)


def test_a_silent_lead_is_replaced(db, monkeypatch):
    _wipe(db)
    assert sch.take_lead(db, "a:1")
    real = sch.time.time; monkeypatch.setattr(sch.time, "time", lambda: real() + 120)
    assert sch.take_lead(db, "b:2")
    monkeypatch.undo(); _wipe(db)


def test_conflicting_tasks_wait_and_keep_their_order(client, make_user, db):
    _wipe(db); h, _ = make_user()
    first = ts.enqueue(db, "internships"); boards = ts.enqueue(db, "board_search")
    merge = ts.enqueue(db, "dedupe_jobs"); rescan = ts.enqueue(db, "scan_all")
    a = ts.claim(db, on_claim=lambda t: sch.beat(db, "running", 0, task=t.kind, task_id=t.id, wid="a:1", commit=False))
    assert a.id == first.id
    b = ts.claim(db, on_claim=lambda t: sch.beat(db, "running", 0, task=t.kind, task_id=t.id, wid="b:2", commit=False))
    assert b.id == boards.id                                          # does not get in the way of the internship sweep
    assert ts.claim(db) is None                                       # merging waits for the writers; the re-scan waits behind both
    why = {t["id"]: t["waiting"] for t in client.get(f"{H}/admin/tasks", headers=h).json()}
    assert why[merge.id] == {"why": "conflict", "task_id": first.id, "kind": "internships"}
    assert why[rescan.id]["why"] == "conflict" and why[rescan.id]["task_id"] == first.id and why[a.id] is None
    _wipe(db)


def test_waiting_reasons_without_a_free_worker(db):
    _wipe(db)
    t = ts.enqueue(db, "logos")
    assert ts.waiting_reasons(db)[t.id] == {"why": "no_worker"}
    busy = ts.enqueue(db, "census"); busy.status = "running"; db.commit(); _worker(db, "a:1", busy)
    assert ts.waiting_reasons(db)[t.id] == {"why": "busy", "workers": 1, "task_id": busy.id, "kind": "census"}
    _worker(db, "b:2")
    assert ts.waiting_reasons(db)[t.id] == {"why": "next"}
    _wipe(db)


def test_a_dead_workers_task_blocks_nothing(db):
    _wipe(db)
    old = ts.enqueue(db, "internships"); old.status = "running"; db.commit()        # no live worker reports it
    new = ts.enqueue(db, "scan_all")
    assert ts.claim(db).id == new.id


def test_an_older_workers_task_still_counts(db):
    """During an upgrade a worker running the previous code names its task only in the note."""
    import json, time
    from app.models import KV
    _wipe(db)
    old = ts.enqueue(db, "internships"); old.status = "running"; db.commit()
    db.add(KV(k="worker_heartbeat", v=json.dumps({"at": time.time(), "pid": 1, "host": "h", "state": "running", "inflight": 0, "task": "internships", "note": f"running task #{old.id}"}))); db.commit()
    ts.enqueue(db, "scan_all")
    assert ts.claim(db) is None and sch.status(db)["workers"][0]["old"]
    _wipe(db)


def test_a_company_is_claimed_once(db):
    from app.workers.run import _claim_companies
    c = Company(name="Acme", website="https://acme.example"); db.add(c); db.commit()
    assert _claim_companies(db, [c.id]) == [c.id]
    assert _claim_companies(db, [c.id]) == []


def test_a_stopped_worker_leaves_no_task_running(db, monkeypatch):
    from app.workers import run
    _wipe(db)
    t = ts.enqueue(db, "internships"); ts.claim(db); _worker(db, sch.worker_id(), t); sch.take_lead(db)
    monkeypatch.setitem(run._now, "task_id", t.id)
    run._sign_off()
    db.refresh(t)
    assert t.status == "failed" and "stopped" in t.error and sch.status(db)["workers"] == []
    assert sch.take_lead(db, "b:2")
    _wipe(db)
