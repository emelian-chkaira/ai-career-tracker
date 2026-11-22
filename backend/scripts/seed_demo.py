"""Seed the local demo account used for the README screenshots and video (docs-media). Talks to a LOCAL API only.
Run:  CAREERS_FIREBASE_API_KEY= .venv/bin/uvicorn app.main:app --port 8790   then   PYTHONPATH=. .venv/bin/python scripts/seed_demo.py"""
import os
import httpx
from app.core.db import SessionLocal
from sqlalchemy import text
B = os.environ.get("MEDIA_URL", "http://localhost:8790") + "/api/v1"; c = httpx.Client(timeout=90, trust_env=False)
def auth(email, pw="demo-password-1", name="Alex Demo"):
    r = c.post(f"{B}/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200: r = c.post(f"{B}/auth/register", json={"email": email, "password": pw, "name": name})
    r.raise_for_status(); return {"Authorization": "Bearer " + r.json()["access_token"]}
h = auth("demo@example.com")
db = SessionLocal(); db.execute(text("update users set email_verified_at = now() where email = 'demo@example.com'")); db.commit()
c.put(f"{B}/auth/profile", headers=h, json={"sectors": ["tech"], "countries": ["NL", "DE", "BE"], "regions": [], "cities": [], "titles": ["Backend Developer", "Data Engineer", "Python Developer"],
      "skills": ["Python", "SQL", "Docker", "Kubernetes", "AWS", "FastAPI", "PostgreSQL"], "job_types": [], "work_modes": [], "english_only": True, "onboarded": True}).raise_for_status()
CV = open(os.path.join(os.path.dirname(__file__), "demo_cv.txt")).read()
r = c.post(f"{B}/cv/extract", headers={**h, "Content-Type": "text/plain"}, params={"filename": "cv.txt"}, content=CV.encode())   # raw body, like the web app
print("extract", r.status_code, r.text[:120] if r.status_code >= 400 else "")
if r.status_code < 400:
    d = r.json(); c.put(f"{B}/me/cv/draft", headers=h, json={"draft": {**d, "template": "modern"}}); print("cv for AI", c.put(f"{B}/me/cv", headers=h, json={"cv": d["cv"]}).status_code)
jobs = c.get(f"{B}/jobs", headers=h, params={"scope": "mine", "limit": 40}).json()["items"]
plan = ["offer", "interview", "interview", "assessment", "applied", "applied", "applied", "shortlisted", "shortlisted", "shortlisted", "rejected", "screening"]
for j, st in zip(jobs[2:], plan):
    if st != "shortlisted": c.put(f"{B}/me/jobs/{j['id']}", headers=h, json={"stage": "applied"})
    c.put(f"{B}/me/jobs/{j['id']}", headers=h, json={"stage": st})
c.post(f"{B}/me/searches", headers=h, json={"name": "My feed", "params": {"scope": "mine"}, "alert_frequency": "daily"})
print("feed", len(jobs), "pipeline", len(plan))
