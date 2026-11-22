from fastapi import APIRouter
from . import auth, jobs, companies, me, analytics, cv, admin, tasks, mail, fit, track, cv_tailor, assistant, account, rr

api = APIRouter(prefix="/api/v1")
for m in (auth, jobs, companies, me, analytics, cv, admin, tasks, mail, fit, track, cv_tailor, assistant, account, rr): api.include_router(m.router)
api.include_router(mail.ai)
