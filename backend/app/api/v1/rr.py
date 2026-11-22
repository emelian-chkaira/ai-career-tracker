"""Reactive Resume integration: connect with an API key, list and import resumes, push the CV, fetch its PDF."""
import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import current_user
from app.models import User
from app.services import rr_service as rr

router = APIRouter(prefix="/me/rr", tags=["reactive-resume"])


def _wrap(fn, *a):
    try: return fn(*a)
    except rr.RrError as e: raise HTTPException(e.status, str(e))


class ConnIn(BaseModel):
    base_url: str = Field(rr.HOSTED, max_length=300)
    api_key: str = Field(..., min_length=8, max_length=400)


@router.get("", summary="Is Reactive Resume connected? (never returns the key)")
def status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = rr.get_conn(db, user.id); return {"connected": bool(c), "base_url": c.base_url if c else None, "default_url": rr.HOSTED}


@router.put("", summary="Connect (the URL and key are checked before they are saved)")
def connect(body: ConnIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _wrap(rr.save_conn, db, user.id, body.base_url, body.api_key); return {"connected": True, "base_url": c.base_url}


@router.delete("", status_code=204)
def disconnect(db: Session = Depends(get_db), user: User = Depends(current_user)): rr.delete_conn(db, user.id)


@router.get("/resumes")
def resumes(db: Session = Depends(get_db), user: User = Depends(current_user)): return _wrap(rr.list_resumes, db, user.id)


@router.post("/import/{resume_id}", summary="Read a resume from Reactive Resume as a CV")
def import_resume(resume_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not resume_id.replace("-", "").isalnum(): raise HTTPException(400, "bad resume id")
    return {"cv": _wrap(rr.fetch_cv, db, user.id, resume_id)}


class PushIn(BaseModel):
    cv: dict
    template: str = "classic"
    paper: str = "a4"
    name: str = Field("CV", max_length=80)


@router.post("/push", status_code=201, summary="Create a new resume in Reactive Resume from this CV")
def push(body: PushIn, db: Session = Depends(get_db), user: User = Depends(current_user)): return _wrap(rr.push_cv, db, user.id, body.cv, body.template, body.paper, body.name)


@router.get("/pdf/{resume_id}", summary="The PDF Reactive Resume renders for a resume")
def pdf(resume_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not resume_id.replace("-", "").isalnum(): raise HTTPException(400, "bad resume id")
    return {"pdf_b64": base64.b64encode(_wrap(rr.pdf, db, user.id, resume_id)).decode()}
