"""CV Studio library: several CVs and cover letters per account."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import current_user
from app.models import User
from app.services import docs_service as ds

router = APIRouter(prefix="/me/docs", tags=["cv-library"])


def _err(e: ds.DocError) -> HTTPException: return HTTPException(404 if str(e) == "not found" else 400, str(e))


class DocIn(BaseModel):
    kind: str
    name: str = Field("", max_length=120)
    data: dict
    job_id: int | None = None
    make_default: bool = False
    folder: str | None = Field(None, max_length=60)


class DocPatch(BaseModel):
    name: str | None = Field(None, max_length=120)
    data: dict | None = None
    job_id: int | None = None
    folder: str | None = Field(None, max_length=60)


@router.get("", summary="Your CVs and cover letters (metadata only)")
def list_docs(kind: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if kind not in (None, "cv", "cover"): raise HTTPException(400, "kind must be cv or cover")
    return {"docs": ds.list_docs(db, user, kind), "folders": ds.folders(db, user)}


@router.post("", status_code=201, summary="Add a CV or a cover letter to the library")
def create(body: DocIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: r = ds.create(db, user, body.kind, body.name, body.data, body.job_id, body.make_default, folder=body.folder)
    except ds.DocError as e: raise _err(e)
    return ds.full(r)


@router.get("/{doc_id}", summary="One document with its content")
def read(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: return ds.full(ds.get(db, user, doc_id))
    except ds.DocError as e: raise _err(e)


@router.put("/{doc_id}", summary="Rename or save a document")
def save(doc_id: int, body: DocPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: r = ds.update(db, user, doc_id, body.name, body.data, body.job_id, body.folder)
    except ds.DocError as e: raise _err(e)
    return ds._meta(r)


@router.post("/{doc_id}/default", summary="Use this CV for AI scoring when no CV is chosen for a job")
def make_default(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: return ds._meta(ds.set_default(db, user, doc_id))
    except ds.DocError as e: raise _err(e)


@router.delete("/{doc_id}", status_code=204)
def remove(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: ds.delete(db, user, doc_id)
    except ds.DocError as e: raise _err(e)
