"""When the crawler may visit career sites on its own, and the worker's heartbeat (so the UI can tell running, paused and stopped apart).

The schedule is stored in the kv table (key "crawl_schedule") and re-read by the worker every few seconds, like the storage policy.
Only the automatic refresh follows it; tasks someone starts from the Crawler page always run."""
import datetime as dt, json, os, socket, time
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import KV

KEY, BEAT = "crawl_schedule", "worker_heartbeat"
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


# ------------------------------------------------------------------ heartbeat
def beat(db: Session, state: str, inflight: int, task: str | None = None, note: str = ""):
    row = db.get(KV, BEAT) or KV(k=BEAT)
    row.v = json.dumps({"at": time.time(), "pid": os.getpid(), "host": socket.gethostname(), "state": state, "inflight": inflight, "task": task, "note": note})
    db.add(row); db.commit()


def status(db: Session) -> dict:
    """What the worker said last, and how long ago. 'stopped' when it has been silent for over a minute."""
    r = db.get(KV, BEAT)
    try: b = json.loads(r.v) if r and r.v else None
    except ValueError: b = None
    ok, why, nxt = window(current(db))
    if not b: return {"state": "stopped", "seen_seconds": None, "inflight": 0, "allowed": ok, "why": why, "next_start": nxt, "note": "no worker has reported yet: start it with ./run.sh worker"}
    age = time.time() - b["at"]
    state = "stopped" if age > 60 else b["state"]
    return {"state": state, "seen_seconds": round(age), "pid": b.get("pid"), "host": b.get("host"), "inflight": b.get("inflight", 0) if state != "stopped" else 0,
            "task": b.get("task") if state != "stopped" else None, "allowed": ok, "why": why, "next_start": nxt,
            "note": "the worker has not reported for over a minute: it is not running" if state == "stopped" else b.get("note", "")}
