"""Per-job tailored CVs: fact guard, coverage report, templates, cover letter, PDF consent."""
import json
from sqlalchemy import select, text
from app.models import Job
from app.services import llm_service as llm, ingest_service as ing

CV = {"name": "Sam", "email": "s@x.nl", "phone": "", "location": "Utrecht", "links": [], "summary": "Backend developer", "skills": ["Python", "SQL", "Docker"], "languages": ["English"], "certifications": [],
      "experience": [{"heading": "Backend Developer", "title": "Backend Developer", "place": "Acme", "date": "2021-2024", "desc": "", "bullets": ["Built REST APIs in Python", "Cut query time by 60%"]}], "projects": [], "education": []}
A = "/api/v1/me"


def _setup(client, make_user, db):
    h, _ = make_user(); c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [dict(title="Python Backend Engineer", location="Amsterdam", url="https://acme.nl/1", description="We need Python, SQL and Docker. Kubernetes is a plus. " * 8, posted_at=None)]); db.commit()
    j = db.scalar(select(Job)); client.put(f"{A}/cv", json={"cv": CV}, headers=h)
    client.put("/api/v1/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"}, headers=h); return h, j


def test_tailor_rejects_invented_facts_and_reports_coverage(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    reply = {"summary": "Python backend developer who builds APIs.", "sections": {"experience": [{"i": 0, "bullets": ["Built REST APIs in Python for 10 million users using Kubernetes", "Cut query time by 60%"]}]}, "skills_first": ["Python", "Rust"], "gaps": ["Kubernetes"], "notes": "ok"}
    monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(reply))
    r = client.post(f"{A}/tailor/{j.id}", json={}, headers=h); assert r.status_code == 200, r.text; r = r.json()
    assert r["cv"]["summary"].startswith("Python backend")                                              # harmless edit kept
    assert r["cv"]["experience"][0]["bullets"][0] == "Built REST APIs in Python"                         # invented "10 million" + Kubernetes edit rejected
    assert r["report"]["rejected"] and "new" in r["report"]["rejected"][0]["why"]
    assert r["cv"]["skills"][0] == "Python" and "Rust" not in r["cv"]["skills"]
    assert r["report"]["after"]["percent"] >= r["report"]["before"]["percent"] and "\\begin{document}" in r["latex"]
    assert client.get(f"{A}/tailor/{j.id}", headers=h).json()["model"] == "ollama:qwen2.5:7b"
    assert "Backend Developer" not in (db.scalar(text("select data_enc from job_cvs")) or "")            # encrypted at rest


def test_needs_cv_and_consent(client, make_user, db):
    h, _ = make_user(); c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [dict(title="Dev", location="Amsterdam", url="https://acme.nl/2", description="Python " * 40, posted_at=None)]); db.commit(); j = db.scalar(select(Job))
    assert client.post(f"{A}/tailor/{j.id}", json={}, headers=h).status_code == 409                       # no CV saved
    client.put(f"{A}/cv", json={"cv": CV}, headers=h)
    assert client.post(f"{A}/tailor/{j.id}", json={}, headers=h).status_code == 400                       # no model chosen
    client.put("/api/v1/ai/settings", json={"provider": "groq", "model": "openai/gpt-oss-20b", "api_key": "k"}, headers=h)
    assert "consent" in client.post(f"{A}/tailor/{j.id}", json={}, headers=h).text


def test_cover_letter_template_edit_and_pdf_consent(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "Dear team, I build Python APIs at Acme. [why this company]\n\nKind regards,\nSam " + "x" * 60)
    r = client.post(f"{A}/tailor/{j.id}/cover-letter", json={}, headers=h).json(); assert r["cover_letter"].startswith("Dear team") and r["cv"]["name"] == "Sam"
    c = client.put(f"{A}/tailor/{j.id}", json={"template": "compact"}, headers=h).json(); assert c["template"] == "compact" and c["cover_letter"].startswith("Dear")
    assert client.put(f"{A}/tailor/{j.id}", json={"template": "nope"}, headers=h).status_code == 400
    assert client.post(f"{A}/tailor/{j.id}/pdf", json={"mode": "public"}, headers=h).status_code == 400    # third-party compiler needs consent
    assert client.delete(f"{A}/tailor/{j.id}", headers=h).status_code == 204 and client.get(f"{A}/tailor/{j.id}", headers=h).status_code == 404


def test_ai_field_assist_and_project_rule(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "Built REST APIs in Python.")
    ok = client.post(f"{A}/tailor/field", json={"text": "Built REST APIs in Python", "instruction": "shorter", "kind": "bullet"}, headers=h); assert ok.status_code == 200 and ok.json()["text"] == "Built REST APIs in Python."
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "Built REST APIs in Python for 10 million users")
    bad = client.post(f"{A}/tailor/field", json={"text": "Built REST APIs in Python"}, headers=h); assert bad.status_code == 422 and "10" in bad.text      # invented number dropped
    assert client.post(f"{A}/tailor/field", json={"text": " "}, headers=h).status_code == 400
    from app.services import tailor_service as ts
    cv = dict(CV, projects=[{"title": "A", "use": "exclude", "bullets": []}, {"title": "B", "use": "always", "bullets": []}, {"title": "C", "bullets": []}])
    assert [p["title"] for p in ts.apply_use_rule(cv)["projects"]] == ["B", "C"]
