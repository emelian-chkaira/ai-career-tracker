"""When the crawler may visit career sites on its own, the heartbeat of every worker (so the UI can tell running, paused and stopped apart)
and the lease that makes one of them the lead.

The schedule is stored in the kv table (key "crawl_schedule") and re-read by the worker every few seconds, like the storage policy.
Only the automatic refresh follows it; tasks someone starts from the Crawler page always run."""
import datetime as dt, json, os, re, socket, time
from zoneinfo import ZoneInfo
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import KV

KEY = "crawl_schedule"
BEAT, OLD_BEAT, LEAD = "worker:", "worker_heartbeat", "worker_lead"     # one row per worker; OLD_BEAT is what workers before 2026-11 wrote
SILENT, FORGET = 60, 3600          # seconds without a beat until a worker counts as stopped / until its row is removed
DEFAULT = {"enabled": True, "days": [0, 1, 2, 3, 4, 5, 6], "start": "00:00", "end": "24:00", "tz": "Europe/Amsterdam", "revisit_hours": 12, "parallel": 20}
_cache: dict = {"at": 0.0, "v": None}


def current(db: Session | None = None) -> dict:
    if db is None and time.time() - _cache["at"] < 5 and _cache["v"] is not None: return _cache["v"]
    v = dict(DEFAULT)
    try:
        if db is not None: raw = db.get(KV, KEY); raw = raw.v if raw else None
        else:
            with SessionLocal() as s: r = s.get(KV, KEY); raw = r.v if r else None
        if raw: v.update({k: x for k, x in json.loads(raw).items() if k in DEFAULT})
    except Exception: pass
    _cache.update(at=time.time(), v=v); return v


def _hm(s: str) -> int:
    h, m = s.split(":"); return int(h) * 60 + int(m)


def validate(v: dict) -> dict:
    out = {**DEFAULT, **{k: x for k, x in v.items() if k in DEFAULT}}
    out["days"] = sorted({int(d) for d in out["days"] if 0 <= int(d) <= 6})
    for k in ("start", "end"):
        if not isinstance(out[k], str) or ":" not in out[k] or not (0 <= _hm(out[k]) <= 1440): raise ValueError(f"{k} must look like 08:30")
    try: ZoneInfo(out["tz"])
    except Exception: raise ValueError("unknown time zone")
    out["revisit_hours"] = max(1, min(int(out["revisit_hours"]), 24 * 14)); out["parallel"] = max(1, min(int(out["parallel"]), 40))
    out["enabled"] = bool(out["enabled"]); return out


def save(db: Session, v: dict) -> dict:
    v = validate(v); row = db.get(KV, KEY) or KV(k=KEY); row.v = json.dumps(v); db.add(row); db.commit(); _cache["v"] = None; return v


def window(v: dict | None = None, now: dt.datetime | None = None) -> tuple[bool, str, str | None]:
    """-> (allowed now?, why not, next start ISO time when paused)."""
    v = v or current(); tz = ZoneInfo(v["tz"]); now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(tz)
    if not v["enabled"]: return False, "automatic crawling is switched off", None
    if not v["days"]: return False, "no days selected", None
    s, e = _hm(v["start"]), _hm(v["end"])
    def inside(t: dt.datetime) -> bool:
        m = t.hour * 60 + t.minute
        if s <= e: return t.weekday() in v["days"] and s <= m < e
        return (t.weekday() in v["days"] and m >= s) or ((t - dt.timedelta(days=1)).weekday() in v["days"] and m < e)        # window over midnight
    if inside(now): return True, "", None
    t = now.replace(second=0, microsecond=0)
    for _ in range(8 * 1440):                                                      # next minute inside the window (at most 8 days ahead)
        t += dt.timedelta(minutes=1)
        if inside(t): return False, "outside the crawl schedule", t.isoformat()
    return False, "outside the crawl schedule", None


# ------------------------------------------------------------------ heartbeats (one per worker)
def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"[-70:]


def beat(db: Session, state: str, inflight: int, task: str | None = None, note: str = "", task_id: int | None = None, lead: bool = False,
         wid: str | None = None, commit: bool = True):
    wid = wid or worker_id()
    row = db.get(KV, BEAT + wid) or KV(k=BEAT + wid)
    row.v = json.dumps({"id": wid, "at": time.time(), "pid": os.getpid(), "host": socket.gethostname(), "state": state, "inflight": inflight,
                        "task": task, "task_id": task_id, "lead": lead, "note": note})
    db.add(row)
    if commit: db.commit()
    else: db.flush()


def forget(db: Session, wid: str | None = None):
    """A worker that stops cleanly leaves the list at once."""
    db.execute(text("DELETE FROM kv WHERE k = :k"), {"k": BEAT + (wid or worker_id())}); db.commit()


def _beats(db: Session) -> list[dict]:
    out = []
    for r in db.scalars(select(KV).where(or_(KV.k.like(BEAT + "%"), KV.k == OLD_BEAT)).execution_options(populate_existing=True)):
        try: b = json.loads(r.v or "")
        except ValueError: continue
        if r.k == OLD_BEAT:                                                    # an older worker still running: it only names its task in the note
            m = re.search(r"#(\d+)", b.get("note") or "")
            b = {**b, "id": f"{b.get('host')}:{b.get('pid')}", "task_id": int(m.group(1)) if m and b.get("task") else None, "old": True}
        b["age"] = time.time() - b["at"]
        out.append(b)
    return sorted(out, key=lambda b: (not b.get("lead"), b["id"]))


def workers(db: Session) -> list[dict]:
    """Workers heard from within the last minute, the lead first."""
    return [b for b in _beats(db) if b["age"] <= SILENT]


def prune(db: Session):
    cut = time.time() - FORGET
    db.execute(text("DELETE FROM kv WHERE (k LIKE :p OR k = :o) AND (v::json->>'at')::float < :cut"), {"p": BEAT + "%", "o": OLD_BEAT, "cut": cut}); db.commit()


# ------------------------------------------------------------------ lead: the one worker that runs the automatic work
def take_lead(db: Session, wid: str | None = None) -> bool:
    """Take or renew the lead. Only one worker holds it; it passes on when the holder releases it or is silent for a minute.
    The lead alone starts automatic company scans, alerts, e-mails, embeddings and the daily clean-up, so nothing happens twice."""
    wid = wid or worker_id(); now = time.time()
    row = db.execute(text("""INSERT INTO kv (k, v) VALUES (:k, :v)
        ON CONFLICT (k) DO UPDATE SET v = excluded.v WHERE kv.v::json->>'id' = :id OR (kv.v::json->>'at')::float < :stale RETURNING k"""),
        {"k": LEAD, "v": json.dumps({"id": wid, "at": now}), "id": wid, "stale": now - SILENT}).first()
    db.commit()
    return row is not None


def release_lead(db: Session, wid: str | None = None):
    db.execute(text("DELETE FROM kv WHERE k = :k AND v::json->>'id' = :id"), {"k": LEAD, "id": wid or worker_id()}); db.commit()


def status(db: Session) -> dict:
    """All workers together, plus each one. 'stopped' when none has been heard from for over a minute."""
    beats = _beats(db); live = [b for b in beats if b["age"] <= SILENT]
    ok, why, nxt = window(current(db))
    base = {"allowed": ok, "why": why, "next_start": nxt}
    if not beats: return {**base, "state": "stopped", "seen_seconds": None, "inflight": 0, "workers": [], "note": "no worker has reported yet: start it with ./run.sh worker"}
    if not live:
        b = min(beats, key=lambda x: x["age"])
        return {**base, "state": "stopped", "seen_seconds": round(b["age"]), "pid": b.get("pid"), "host": b.get("host"), "inflight": 0, "task": None, "workers": [],
                "note": "the worker has not reported for over a minute: it is not running"}
    states = [b["state"] for b in live]
    state = next((x for x in ("running", "idle", "paused") if x in states), states[0])
    first = live[0]
    return {**base, "state": state, "seen_seconds": round(min(b["age"] for b in live)), "pid": first.get("pid"), "host": first.get("host"),
            "inflight": sum(b.get("inflight", 0) for b in live), "task": next((b["task"] for b in live if b.get("task")), None), "note": first.get("note", ""),
            "workers": [{"id": b["id"], "pid": b.get("pid"), "host": b.get("host"), "state": b["state"], "task": b.get("task"), "task_id": b.get("task_id"),
                         "inflight": b.get("inflight", 0), "lead": bool(b.get("lead")), "old": bool(b.get("old")), "seen_seconds": round(b["age"])} for b in live]}
