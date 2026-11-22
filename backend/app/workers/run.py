"""Worker process: `python -m app.workers.run`.
 - executes queued tasks (scan, discovery, live search, embeddings…)
 - scheduler: refreshes stale companies, embeds new jobs, runs job alerts and sends the e-mail outbox.
Scale out by running more worker containers (tasks are claimed with SKIP LOCKED)."""
import logging, os, threading, time, traceback, signal
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, exists
from app.core.db import SessionLocal
from app.core.config import settings
from app.models import Company, Job
from app.services import task_service, alert_service, tracking_service, sponsor_service, maintenance_service, schedule_service
from . import tasks, embeddings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
for _n in ("httpx", "httpcore", "playwright"): logging.getLogger(_n).setLevel(logging.WARNING)      # one INFO line per fetched page (incl. harmless 301/302 redirects) drowns the real worker logs
log = logging.getLogger("worker")
STOP = False
HANDLERS = {
    "scan_all": lambda t, db: tasks.scan_all(t, db), "scan_unscanned": lambda t, db: tasks.scan_all(t, db, unscanned=True), "scan_company": tasks.scan_company,
    "discover": tasks.discover, "discover_country": tasks.discover_country, "board_search": tasks.board_search, "dedupe_jobs": tasks.dedupe_jobs, "census": tasks.census, "internships": tasks.internships, "broad_sources": tasks.broad_sources, "logos": tasks.logos, "live_search": tasks.live_search,
    "sponsors_refresh": lambda t, db: (sponsor_service.refresh(db), sponsor_service.recheck_all(db)),
    "mail_sync": tasks.mail_sync,
    "embed": lambda t, db: task_service.progress(db, t, embedded=embeddings.backfill()),
}


_now: dict = {"state": "idle", "task": None, "note": "just started"}       # what the worker is doing, written by the main loop


def _heartbeat():
    """Own thread: report every 10 s even while the main loop is busy with a long task (discovery can take many minutes)."""
    while not STOP:
        try:
            with SessionLocal() as db: schedule_service.beat(db, _now["state"], len(_inflight), task=_now["task"], note=_now["note"])
        except Exception: log.warning("could not write the heartbeat")
        time.sleep(10)


GRACE = 30                                             # seconds a stopping worker may take to finish what it started


def _stop(*_):
    """Ctrl+C / kill: finish the current step, drop queued scans, and exit within GRACE seconds even if a page read hangs
    (a worker that lingers keeps its database connections and can starve the next one)."""
    global STOP
    if STOP: os._exit(1)                                                           # second Ctrl+C: leave now
    STOP = True
    log.info("stopping: finishing current work, exiting within %ss", GRACE)
    _pool.shutdown(wait=False, cancel_futures=True)
    t = threading.Timer(GRACE, lambda: (log.warning("still busy after %ss; exiting anyway", GRACE), engine_dispose(), os._exit(0)))
    t.daemon = True; t.start()


def engine_dispose():
    try:
        from app.core.db import engine
        engine.dispose()
    except Exception: pass


def _boards_due(db) -> bool:
    """Automatic board search is due when the last one (any, also started by hand) began more than CAREERS_BOARD_EVERY_HOURS ago.
    Read from the tasks table, so restarting the worker does not start a new search."""
    import datetime as dt
    from app.models import Task
    from sqlalchemy import func
    last_at = db.scalar(select(func.max(Task.created_at)).where(Task.kind == "board_search"))
    return last_at is None or dt.datetime.now(dt.timezone.utc) - last_at > dt.timedelta(hours=settings.board_every_hours)


def _every(last: dict, key: str, seconds: float) -> bool:
    if time.time() - last.get(key, 0) >= seconds: last[key] = time.time(); return True
    return False


def main():
    global STOP
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    last: dict = {}
    log.info("worker started")
    import threading
    threading.Thread(target=_heartbeat, daemon=True, name="heartbeat").start()
    while not STOP:
        did = False
        with SessionLocal() as db:
            t = task_service.claim(db)
            if t:
                did = True; log.info("task %s #%s %s", t.kind, t.id, t.payload)
                _now.update(state="running", task=t.kind, note=f"running task #{t.id}")
                try:
                    HANDLERS[t.kind](t, db); task_service.finish(db, t)
                    _now.update(task=None, note="")
                except Exception as e:
                    db.rollback(); log.error("task failed: %s", traceback.format_exc()); task_service.finish(db, db.get(type(t), t.id), str(e)[:300])
        if not did:
            try:
                with SessionLocal() as db:
                    if _every(last, "alerts", 300): n = alert_service.run_due(db); alert_service.send_outbox(db); n and log.info("alerts created: %s", n); m = tracking_service.notify_due(db); m and log.info("follow-up reminders: %s", m)
                    if _every(last, "embed", 120): embeddings.backfill(limit=500)
                    if _every(last, "purge", 86400): r = maintenance_service.purge_old(db); any(r.values()) and log.info("retention purge: %s", r)      # daily retention
                    if _every(last, "dedupe", 86400): r = maintenance_service.collapse_duplicates(db); r["jobs_merged"] and log.info("duplicates merged: %s", r)      # daily: one role, one job
                    if _every(last, "refresh", 5):                  # keep jobs fresh: top up the scan pool with the next due companies, inside the schedule
                        ok, why, nxt = schedule_service.window()
                        if ok:
                            _refresh(db)
                            if settings.board_sites.strip() and settings.board_every_hours and _every(last, "boards-check", 300) and _boards_due(db):
                                task_service.enqueue(db, "board_search")              # EXPERIMENTAL job boards, only when switched on
                        elif _every(last, "paused-log", 600): log.info("automatic crawling paused: %s%s", why, f" (next start {nxt})" if nxt else "")
                        last["state"] = ("running" if _inflight else "idle") if ok else "paused"; last["why"] = why
                    _now.update(state=last.get("state", "idle"), task=None, note=last.get("why", ""))
            except Exception: log.error("scheduler error: %s", traceback.format_exc())
            time.sleep(3)
    log.info("worker stopped"); engine_dispose(); os._exit(0)                     # do not wait for hung scan threads


POOL_SIZE = 40; STUCK_AFTER = 900                      # scans in flight at once; a scan older than 15 min is treated as hung and its slot is reused
_pool = ThreadPoolExecutor(POOL_SIZE + 8); _inflight: dict[int, float] = {}


def _refresh(db):
    """Continuously keep POOL_SIZE company scans running. One hung scan can no longer stall the others (no batch barrier)."""
    import datetime as dt
    now = time.time()
    for cid, t0 in list(_inflight.items()):
        if now - t0 > STUCK_AFTER: log.warning("scan of company %s looks hung (>%ss); freeing its slot", cid, STUCK_AFTER); _inflight.pop(cid, None)
    free = min(POOL_SIZE, schedule_service.current()["parallel"]) - len(_inflight)
    if free <= 0: return
    has_open = exists().where(Job.company_id == Company.id, Job.status == "open")      # companies that actually have live postings are refreshed first
    q = select(Company.id).where((Company.website.is_not(None)) | (Company.ats_slug.is_not(None)),
                                 Company.ats.is_(None) | ~Company.ats.like("board:%"),      # board-level sources are scanned per board, never per company (they would return instantly and clog the queue)
                                 (Company.next_scan.is_(None)) | (Company.next_scan <= dt.datetime.now(dt.timezone.utc)))
    if _inflight: q = q.where(Company.id.not_in(list(_inflight)))
    fresh = list(db.scalars(q.where(Company.last_scan.is_(None)).order_by(Company.id.desc()).limit(max(1, free // 2))))     # half the slots: employers never read (new countries fill fast)
    rest = list(db.scalars(q.where(Company.id.not_in(fresh or [-1])).order_by(has_open.desc(), Company.next_scan.asc().nullsfirst()).limit(free - len(fresh))))
    for cid in fresh + rest:
        _inflight[cid] = time.time()
        _pool.submit(_run_scan, cid)


def _run_scan(cid: int):
    try: _safe(tasks._scan_one, cid)
    finally: _inflight.pop(cid, None)


def _safe(fn, *a):
    try: return fn(*a)
    except Exception as e: log.warning("%s failed: %s", fn.__name__, e)


if __name__ == "__main__": main()
