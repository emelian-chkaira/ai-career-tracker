"""Talk to a Reactive Resume instance with the user's API key (header x-api-key, base path /api/openapi).

Verified against the public docs only (no live instance was available while writing this): list GET /resumes, read GET /resumes/{id},
PDF GET /resumes/{id}/exports/pdf, and import of a Reactive Resume JSON file via POST /resumes/file-imports (multipart, format REACTIVE_RESUME).
Responses are read defensively, and every failure becomes an RrError with a message a person can act on. The key never leaves the server."""
import json
import httpx
from sqlalchemy.orm import Session
from app.core.netguard import check_url
from app.core.secretbox import seal, unseal
from app.models import UserRr
from app.cvtools import rxresume

HOSTED = "https://rxresu.me"
TIMEOUT = 30


class RrError(Exception):
    def __init__(self, msg: str, status: int = 502): super().__init__(msg); self.status = status


def get_conn(db: Session, user_id) -> UserRr | None: return db.get(UserRr, user_id)


def _api(base: str) -> str: return base.rstrip("/") + "/api/openapi"


def _call(conn_base: str, key: str, method: str, path: str, **kw) -> httpx.Response:
    try:
        r = httpx.request(method, _api(conn_base) + path, headers={"x-api-key": key, "Accept": "application/json"}, timeout=kw.pop("timeout", TIMEOUT), follow_redirects=False, **kw)
    except httpx.HTTPError as e: raise RrError(f"Could not reach Reactive Resume: {type(e).__name__}")
    if r.status_code in (401, 403): raise RrError("Reactive Resume refused the key. Create one with read, write and delete access under Settings, Developer, API keys." if r.status_code == 403 else "Reactive Resume did not accept the API key.", 400)
    if r.status_code == 429: raise RrError("Reactive Resume is rate limiting this key. Wait a minute and try again.", 429)
    if r.status_code >= 400: raise RrError(f"Reactive Resume answered {r.status_code}.")
    return r


def save_conn(db: Session, user_id, base_url: str, api_key: str) -> UserRr:
    base = check_url((base_url or HOSTED).strip()); _call(base, api_key, "GET", "/resumes", params={"limit": 1})          # proves URL and key before saving
    row = db.get(UserRr, user_id) or UserRr(user_id=user_id)
    row.base_url, row.api_key_enc = base, seal(api_key); db.add(row); db.commit(); return row


def delete_conn(db: Session, user_id):
    r = db.get(UserRr, user_id)
    if r: db.delete(r); db.commit()


def _conn(db: Session, user_id) -> tuple[str, str]:
    r = db.get(UserRr, user_id)
    if not r: raise RrError("Connect Reactive Resume first.", 400)
    return r.base_url, unseal(r.api_key_enc) or ""


def list_resumes(db: Session, user_id) -> list[dict]:
    base, key = _conn(db, user_id); d = _call(base, key, "GET", "/resumes", params={"limit": 100}).json()
    items = d if isinstance(d, list) else (d.get("data") or d.get("items") or [])
    return [{"id": str(i.get("id")), "name": i.get("name") or i.get("title") or "Untitled", "updated_at": i.get("updatedAt"), "slug": i.get("slug")} for i in items if isinstance(i, dict) and i.get("id")]


def fetch_cv(db: Session, user_id, resume_id: str) -> dict:
    """Read one resume and turn it into our CV structure. Raises RrError when the document is not a shape we understand."""
    base, key = _conn(db, user_id); d = _call(base, key, "GET", f"/resumes/{resume_id}").json()
    data = d.get("data") if isinstance(d, dict) and isinstance(d.get("data"), dict) else d
    if not rxresume.looks_like_rx(data): raise RrError("That resume has a format this app cannot read yet. Export it as JSON from Reactive Resume and import the file instead.", 422)
    return rxresume.from_rx(data)


def push_cv(db: Session, user_id, cv: dict, template: str, paper: str, name: str) -> dict:
    """Create a new resume in Reactive Resume from our CV (never overwrites an existing one)."""
    base, key = _conn(db, user_id); doc = json.dumps(rxresume.to_rx(cv, template, paper)).encode()
    r = _call(base, key, "POST", "/resumes/file-imports", files={"file": (f"{name or 'cv'}.json", doc, "application/json")}, data={"format": "REACTIVE_RESUME"}, timeout=60)
    try: rid = r.json()
    except ValueError: rid = None
    rid = rid.get("id") if isinstance(rid, dict) else rid
    return {"id": str(rid) if rid else None, "url": f"{base}/builder/{rid}" if rid else base}


def pdf(db: Session, user_id, resume_id: str) -> bytes:
    base, key = _conn(db, user_id); r = _call(base, key, "GET", f"/resumes/{resume_id}/exports/pdf", timeout=90)
    if not r.content.startswith(b"%PDF"): raise RrError("Reactive Resume did not return a PDF.")
    return r.content
