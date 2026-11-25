"""How hard the crawler works: browser slots, scan threads, how long a page may take, and which shortcuts are on.

Defaults come from the environment (CAREERS_BROWSER_SLOTS, CAREERS_SCAN_THREADS). The Crawler page can override them; the overrides live in the
kv table and the worker re-reads them every few seconds, so a change needs no restart. (Browser windows already open finish their page first.)"""
import json, time
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import SessionLocal
from app.models import KV

KEY = "crawler_perf"
MAX_SLOTS = 12
LIMITS = {"browser_slots": (1, MAX_SLOTS), "scan_threads": (1, 40), "page_wait_ms": (500, 15000)}
_cache: dict = {"at": 0.0, "v": None}


def defaults() -> dict:
    return {"browser_slots": max(1, min(int(settings.browser_slots), MAX_SLOTS)), "scan_threads": max(1, min(int(settings.scan_threads), 40)),
            "page_wait_ms": 3000, "ats_first": True, "internship_pass": True}


def current() -> dict:
    if time.time() - _cache["at"] < 5 and _cache["v"] is not None: return _cache["v"]
    v = defaults()
    try:
        with SessionLocal() as db: raw = db.scalar(select(KV.v).where(KV.k == KEY))
        if raw: v.update({k: x for k, x in json.loads(raw).items() if k in v})
    except Exception: pass
    _cache.update(at=time.time(), v=v); return v


def validate(v: dict) -> dict:
    out = {**defaults(), **{k: x for k, x in v.items() if k in defaults()}}
    for k, (lo, hi) in LIMITS.items():
        try: out[k] = max(lo, min(int(out[k]), hi))
        except (TypeError, ValueError): raise ValueError(f"{k} must be a number")
    out["ats_first"] = bool(out["ats_first"]); out["internship_pass"] = bool(out["internship_pass"]); return out


def save(db: Session, v: dict) -> dict:
    v = validate(v); row = db.get(KV, KEY) or KV(k=KEY); row.v = json.dumps(v); db.add(row); db.commit(); _cache["v"] = None; return v


def reset(db: Session) -> dict:
    row = db.get(KV, KEY)
    if row: db.delete(row); db.commit()
    _cache["v"] = None; return current()
