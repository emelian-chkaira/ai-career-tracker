from fastapi import APIRouter
from . import auth, jobs, companies, me, analytics, cv, admin, tasks, mail, fit, track, cv_tailor, assistant, account, rr, cv_coach, docs, cv_chat, about

api = APIRouter(prefix="/api/v1")
for m in (auth, jobs, companies, me, analytics, cv, admin, tasks, mail, fit, track, cv_tailor, assistant, account, rr, cv_coach, docs, cv_chat, about): api.include_router(m.router)
api.include_router(mail.ai)
