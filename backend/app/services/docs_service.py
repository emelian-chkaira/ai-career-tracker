"""CV Studio library: several CVs and cover letters per account (encrypted), one CV marked as the default for AI scoring.

The older single "stored CV" (UserCv) stays the scoring default so every existing feature keeps working: the default library CV is mirrored into it."""
import json, re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.secretbox import seal, unseal
from app.models import User, UserCv, UserDoc
from . import fit_service as fs

KINDS = ("cv", "cover")
MAX_PER_KIND = 30
MAX_BYTES = 600_000


class DocError(ValueError): pass


def _open(r: UserDoc) -> dict:
    try: return json.loads(unseal(r.data_enc) or "{}") or {}
    except ValueError: return {}


def _meta(r: UserDoc, data: dict | None = None) -> dict:
    d = data if data is not None else _open(r)
    cv = d.get("cv") or {}
    note = (cv.get("name") or "") if r.kind == "cv" else (d.get("text") or "")[:90].replace("\n", " ")
    return {"id": r.id, "kind": r.kind, "name": r.name, "is_default": r.is_default, "folder": r.folder or "", "job_id": r.job_id, "note": note, "updated_at": r.updated_at}


def _rows(db: Session, user: User, kind: str) -> list[UserDoc]:
    return list(db.scalars(select(UserDoc).where(UserDoc.user_id == user.id, UserDoc.kind == kind).order_by(UserDoc.id)))


def _bootstrap(db: Session, user: User):
    """Accounts from before the library: turn the working copy / stored CV into the first library CV, once."""
    if db.scalar(select(UserDoc.id).where(UserDoc.user_id == user.id, UserDoc.kind == "cv").limit(1)): return
    draft = fs.get_draft(db, user); stored = fs.get_cv(db, user)
    if isinstance(draft, dict) and isinstance(draft.get("cv"), dict): data = draft
    elif stored: data = {"cv": stored, "latex": "", "source": "text"}
    else: return
    create(db, user, "cv", "My CV", data, make_default=True, sync=False)


def list_docs(db: Session, user: User, kind: str | None = None) -> list[dict]:
    _bootstrap(db, user)
    kinds = [kind] if kind else list(KINDS)
    return [_meta(r) for k in kinds for r in _rows(db, user, k)]


def get(db: Session, user: User, doc_id: int) -> UserDoc:
    r = db.get(UserDoc, doc_id)
    if not r or r.user_id != user.id: raise DocError("not found")
    return r


def full(r: UserDoc) -> dict:
    d = _open(r); return {**_meta(r, d), "data": d}


def _check(kind: str, data: dict) -> str:
    if kind not in KINDS: raise DocError("kind must be cv or cover")
    if not isinstance(data, dict): raise DocError("data must be an object")
    raw = json.dumps(data, ensure_ascii=False)
    if len(raw) > MAX_BYTES: raise DocError("the document is too large")
    if kind == "cv" and not isinstance(data.get("cv"), dict): raise DocError("a CV document needs a structured cv")
    if kind == "cover" and not isinstance(data.get("text"), str): raise DocError("a cover letter needs text")
    return raw


def _mirror(db: Session, user: User, r: UserDoc, data: dict):
    cv = data.get("cv") or {}
    if cv.get("experience") or cv.get("skills") or cv.get("skill_groups") or cv.get("summary"): fs.put_cv(db, user, cv, sync_docs=False)


def refresh_default(db: Session, user: User, cv: dict):
    """The stored CV was saved directly (older clients, the CV coach): keep the default library CV in step. Caller commits."""
    d = next((x for x in _rows(db, user, "cv") if x.is_default), None)
    if d: data = _open(d); data["cv"] = cv; d.data_enc = seal(json.dumps(data, ensure_ascii=False))


def clean_folder(f: str | None) -> str:
    f = re.sub(r"\s+", " ", (f or "").strip())[:60]
    return "" if f.lower() in ("default", "default folder") else f


def folders(db: Session, user: User) -> list[str]:
    """Folders in use (the default folder, "", is not listed)."""
    return sorted({r.folder for k in KINDS for r in _rows(db, user, k) if r.folder}, key=str.lower)


def create(db: Session, user: User, kind: str, name: str, data: dict, job_id: int | None = None, make_default: bool = False, sync: bool = True, folder: str | None = None) -> UserDoc:
    raw = _check(kind, data)
    if len(_rows(db, user, kind)) >= MAX_PER_KIND: raise DocError(f"you can keep up to {MAX_PER_KIND} {'CVs' if kind == 'cv' else 'cover letters'}")
    first = kind == "cv" and not any(x.is_default for x in _rows(db, user, "cv"))
    r = UserDoc(user_id=user.id, kind=kind, name=(name or "").strip()[:120] or ("Untitled CV" if kind == "cv" else "Untitled cover letter"), data_enc=seal(raw), job_id=job_id, folder=clean_folder(folder), is_default=False)
    db.add(r); db.flush()
    if kind == "cv" and (make_default or first): _set_default(db, user, r, data, sync)
    db.commit(); return r


def _set_default(db: Session, user: User, r: UserDoc, data: dict, sync: bool = True):
    for o in _rows(db, user, "cv"):
        if o.id != r.id and o.is_default: o.is_default = False
    r.is_default = True
    if sync: _mirror(db, user, r, data)


def update(db: Session, user: User, doc_id: int, name: str | None = None, data: dict | None = None, job_id: int | None = None, folder: str | None = None) -> UserDoc:
    r = get(db, user, doc_id)
    if folder is not None: r.folder = clean_folder(folder)
    if name is not None and name.strip(): r.name = name.strip()[:120]
    if job_id is not None: r.job_id = job_id
    if data is not None:
        r.data_enc = seal(_check(r.kind, data))
        if r.kind == "cv" and r.is_default: _mirror(db, user, r, data)
    db.commit(); return r


def set_default(db: Session, user: User, doc_id: int) -> UserDoc:
    r = get(db, user, doc_id)
    if r.kind != "cv": raise DocError("only a CV can be the scoring default")
    _set_default(db, user, r, _open(r)); db.commit(); return r


def delete(db: Session, user: User, doc_id: int):
    r = get(db, user, doc_id); was_default = r.is_default and r.kind == "cv"; kind = r.kind
    db.delete(r); db.flush()
    if was_default:
        rest = _rows(db, user, "cv")
        if rest: _set_default(db, user, rest[0], _open(rest[0]))
        else: fs.delete_cv(db, user)
    db.commit()


def letter_examples(db: Session, user: User, limit: int = 3) -> list[str]:
    """The user's own saved cover letters (newest first): the AI writes new letters in their voice."""
    return [t for t in ((_open(r).get("text") or "") for r in _rows(db, user, "cover")[:limit + 2]) if t.strip()][:limit]


def cv_for_scoring(db: Session, user: User, cv_id: int | None) -> tuple[dict | None, str | None]:
    """The CV to score with: the chosen library CV, else the default one, else the older stored CV. Returns (cv, library name)."""
    if cv_id is not None:
        r = get(db, user, cv_id)
        if r.kind != "cv": raise DocError("that document is not a CV")
        return (_open(r).get("cv") or None), r.name
    _bootstrap(db, user)
    d = next((x for x in _rows(db, user, "cv") if x.is_default), None)
    if d: return (_open(d).get("cv") or None), d.name
    return fs.get_cv(db, user), None
