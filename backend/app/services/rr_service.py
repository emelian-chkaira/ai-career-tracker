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


def normalize_base(url: str) -> str:
    """Accept whatever address the user copies (site, /mcp, /api/openapi, a dashboard or builder link) and keep the site root.
    The MCP endpoint is a JSON-RPC server and answers 405 to REST calls; the REST API lives under <root>/api/openapi."""
    from urllib.parse import urlsplit
    u = urlsplit((url or HOSTED).strip()); path = u.path.rstrip("/")
    for marker in ("/mcp", "/api", "/dashboard", "/builder", "/auth"):
        i = path.find(marker)
        if i >= 0: path = path[:i]; break
    return f"{u.scheme}://{u.netloc}{path}"


def _api(base: str) -> str: return base.rstrip("/") + "/api/openapi"


def _call(conn_base: str, key: str, method: str, path: str, **kw) -> httpx.Response:
    try:
        r = httpx.request(method, _api(conn_base) + path, headers={"x-api-key": key, "Accept": "application/json"}, timeout=kw.pop("timeout", TIMEOUT), follow_redirects=False, **kw)
    except httpx.HTTPError as e: raise RrError(f"Could not reach Reactive Resume: {type(e).__name__}")
    if r.status_code in (401, 403): raise RrError("Reactive Resume refused the key. Create one with read, write and delete access under Settings, Developer, API keys." if r.status_code == 403 else "Reactive Resume did not accept the API key.", 400)
    if r.status_code == 429: raise RrError("Reactive Resume is rate limiting this key. Wait a minute and try again.", 429)
    if r.status_code == 405: raise RrError("Reactive Resume answered 405: this address is not its REST API. Use the site address (https://rxresu.me or your own server), not /mcp.", 400)
    if r.status_code >= 400: raise RrError(f"Reactive Resume answered {r.status_code}{_why(r)}.")
    return r


def _why(r: httpx.Response) -> str:
    """The server's own explanation of a 4xx (its structured error message), so a person can act on it. Never includes the request."""
    try: j = r.json(); m = j.get("message") or j.get("code") if isinstance(j, dict) else None
    except ValueError: m = None
    return f": {str(m)[:200]}" if m and r.status_code < 500 else ""


def save_conn(db: Session, user_id, base_url: str, api_key: str) -> UserRr:
    base = check_url(normalize_base(base_url)); _call(base, api_key, "GET", "/resumes", params={"limit": 1})          # proves URL and key before saving
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
    """Create a NEW resume in Reactive Resume from our CV (never overwrites an existing one).
    Three calls: create a blank resume, read its valid default document, write our content into it."""
    base, key = _conn(db, user_id); name = (name or "CV")[:80]
    r = _call(base, key, "POST", "/resumes", json={"name": name, "tags": ["ai-career-tracker"], "withSampleData": False}, timeout=60)
    rid = _id_of(r)
    if not rid: raise RrError("Reactive Resume created the resume but did not say which one.")
    try:
        d = _call(base, key, "GET", f"/resumes/{rid}").json(); data = d.get("data") if isinstance(d, dict) and isinstance(d.get("data"), dict) else d
        _call(base, key, "PUT", f"/resumes/{rid}", json={"data": rxresume.fill_rx6(data, cv, template, paper)}, timeout=60)
    except RrError as e: raise RrError(f"The resume was created in Reactive Resume (named '{name}') but could not be filled: {e}", e.status)
    return {"id": rid, "url": f"{base}/builder/{rid}"}


def _id_of(r: httpx.Response) -> str | None:
    try: v = r.json()
    except ValueError: return None
    v = v.get("id") if isinstance(v, dict) else v
    return str(v) if v else None


def pdf(db: Session, user_id, resume_id: str) -> bytes:
    base, key = _conn(db, user_id); r = _call(base, key, "GET", f"/resumes/{resume_id}/exports/pdf", timeout=90)
    if not r.content.startswith(b"%PDF"): raise RrError("Reactive Resume did not return a PDF.")
    return r.content
