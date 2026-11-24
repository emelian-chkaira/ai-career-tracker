"""Per-job tailored CVs: fact guard, coverage report, templates, cover letter, PDF consent."""
import json
from sqlalchemy import select, text, func
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


# ---------------------------------------------------------------- tailor + rebuild in Reactive Resume, and automatic tailoring for followed jobs
def _reply(): return json.dumps({"summary": "Python backend developer who builds APIs.", "sections": {}, "skills_first": ["Python"], "gaps": [], "notes": "ok"})


def test_rebuild_pushes_the_tailored_cv_to_reactive_resume(client, make_user, db, monkeypatch):
    from app.services import rr_service
    h, j = _setup(client, make_user, db); monkeypatch.setattr(llm, "complete", lambda *a, **k: _reply())
    r = client.post(f"{A}/tailor/{j.id}/rebuild", json={}, headers=h).json()
    assert r["report"]["reactive_resume_error"].startswith("Reactive Resume is not connected") and r["cv"]["summary"].startswith("Python backend")     # tailored CV kept even without Reactive Resume
    pushed = []
    monkeypatch.setattr(rr_service, "get_conn", lambda db, uid: object()); monkeypatch.setattr(rr_service, "push_cv", lambda db, uid, cv, tpl, paper, name: pushed.append((cv["summary"], name)) or {"id": "r1", "url": "https://rr/builder/r1"})
    r = client.post(f"{A}/tailor/{j.id}/rebuild", json={}, headers=h).json()
    assert r["report"]["reactive_resume"]["id"] == "r1" and "reactive_resume_error" not in r["report"]
    assert pushed and pushed[0][0].startswith("Python backend") and "Python Backend Engineer @ Acme" in pushed[0][1]
    assert r["cv"]["summary"] == client.get(f"{A}/tailor/{j.id}", headers=h).json()["cv"]["summary"]


def test_following_a_job_queues_a_background_rebuild_only_when_opted_in(client, make_user, db, monkeypatch):
    from app.models import Task
    from app.services import rr_service
    h, j = _setup(client, make_user, db); queued = lambda: db.scalar(select(func.count()).select_from(Task).where(Task.kind == "tailor_cv"))
    client.put(f"{A}/jobs/{j.id}", json={"stage": "shortlisted"}, headers=h); assert queued() == 0                     # off by default
    assert client.put(f"{A}/tailor/auto", json={"on": False}, headers=h).json()["on"] is False
    client.put("/api/v1/ai/settings", json={"provider": "groq", "model": "x", "api_key": "k" * 12}, headers=h)
    assert client.put(f"{A}/tailor/auto", json={"on": True, "consent": False}, headers=h).status_code == 400            # an external model needs consent before it runs by itself
    client.put("/api/v1/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"}, headers=h)
    assert client.put(f"{A}/tailor/auto", json={"on": True, "stages": ["shortlisted"]}, headers=h).json()["on"] is True
    client.delete(f"{A}/jobs/{j.id}", headers=h); client.put(f"{A}/jobs/{j.id}", json={"stage": "shortlisted"}, headers=h); assert queued() == 1
    client.put(f"{A}/jobs/{j.id}", json={"stage": "shortlisted"}, headers=h); assert queued() == 1                       # idempotent
    # the worker side
    from app.services import tailor_service as ts, auth_service
    monkeypatch.setattr(llm, "complete", lambda *a, **k: _reply()); monkeypatch.setattr(rr_service, "get_conn", lambda db, uid: object()); monkeypatch.setattr(rr_service, "push_cv", lambda *a: {"id": "r2", "url": "u"})
    t = db.scalar(select(Task).where(Task.kind == "tailor_cv"))
    assert ts.run_queued(db, t.payload["user_id"], t.payload["job_id"]) == "tailored and rebuilt in Reactive Resume"
    from app.models import Notification
    assert db.scalar(select(Notification.title).where(Notification.kind == "cv")).startswith("Tailored CV ready")
    assert client.put(f"{A}/jobs/{j.id}", json={"stage": "applied"}, headers=h).status_code == 200 and queued() == 1       # already tailored: not queued again


def test_reactive_resume_address_is_reduced_to_the_site_root():
    from app.services.rr_service import normalize_base as n
    assert n("https://rxresu.me/mcp") == "https://rxresu.me" and n("https://rxresu.me/api/openapi/") == "https://rxresu.me" and n("") == "https://rxresu.me"
    assert n("https://rxresu.me/builder/abc-123") == "https://rxresu.me" and n("https://cv.example.nl/rr/mcp") == "https://cv.example.nl/rr" and n("https://cv.example.nl") == "https://cv.example.nl"


def test_push_creates_a_blank_resume_then_fills_it(monkeypatch):
    """Reactive Resume 6: POST /resumes, GET its default document, PUT our content into it (the old one-shot import was rejected with 400)."""
    import httpx
    from types import SimpleNamespace
    from app.services import rr_service as rr
    calls = []
    def fake(method, url, **kw):
        path = url.split("/api/openapi")[1]; calls.append((method, path, kw.get("json")))
        body = {("POST", "/resumes"): "rid-1", ("GET", "/resumes/rid-1"): {"id": "rid-1", "data": {"basics": {"name": "", "customFields": []}, "summary": {"content": ""}, "sections": {"experience": {"items": []}, "awards": {"items": [1]}}, "metadata": {"template": "azurill", "page": {"format": "a4"}}}},
                ("PUT", "/resumes/rid-1"): {"id": "rid-1"}}[(method, path)]
        return httpx.Response(200, json=body, request=httpx.Request(method, url))
    monkeypatch.setattr(httpx, "request", fake); monkeypatch.setattr(rr, "_conn", lambda db, uid: ("https://rr.example", "k" * 12))
    out = rr.push_cv(None, "u", CV, "classic", "a4", "CV - Dev @ Acme")
    assert out == {"id": "rid-1", "url": "https://rr.example/builder/rid-1"} and [c[:2] for c in calls] == [("POST", "/resumes"), ("GET", "/resumes/rid-1"), ("PUT", "/resumes/rid-1")]
    data = calls[2][2]["data"]
    assert data["basics"]["name"] == "Sam" and data["metadata"]["template"] == "azurill"                           # content filled, the server's design left alone
    assert data["sections"]["experience"]["items"][0]["company"] == "Acme" and data["sections"]["experience"]["items"][0]["website"]["inlineLink"] is False
    assert data["sections"]["awards"] == {"items": [], "hidden": True}                                              # sections we do not fill stay empty


# ---------------------------------------------------------------- quality of the tuning itself
CV2 = {**CV, "summary": "Backend developer building machine-learning features and mobile apps", "experience": [{"heading": "Backend Developer", "title": "Backend Developer", "place": "Acme", "date": "2021 – 2024", "desc": "",
       "bullets": ["Built REST APIs in Python", "Cut query time by 60%", "Set up Docker builds"]}]}


def test_guard_allows_honest_rewording_and_refuses_new_tools():
    from app.services.tailor_service import make_guard
    g = make_guard(CV2)
    assert g("Machine learning and mobile application development in Python") == []                 # hyphen vs space, words already in the CV
    assert any("kubernetes" in b.lower() for b in g("Deployed to Kubernetes")) and any("new number" in b for b in g("Cut query time by 90%"))


def test_tuning_never_copies_the_header_line_into_bullets_and_keeps_good_bullets():
    from app.cvtools import cv as cvmod
    reply = {"summary": "Backend developer building ML features.", "fit": "partial", "notes": "n", "gaps": [], "skills_first": [],
             "sections": {"experience": [{"i": 0, "bullets": ["Backend Developer | Acme 2021 – 2024",                                    # the header echoed back as a bullet
                                                               "Built REST APIs in Python for 10 million users",                         # invented number: refused on its own
                                                               "Reduced query time by 60%",                                              # good rewrite: kept
                                                               "Set up Docker builds"]}]}}
    out = cvmod.ai_tailor_with(CV2, {"title": "Backend Engineer", "company": "X", "description": "Python Docker"}, lambda s, u: json.dumps(reply), make_guard_for(CV2))
    b = out["cv"]["experience"][0]["bullets"]
    assert len(b) == 3 and not any("Acme" in x for x in b)                                      # no header echo, same count
    assert "Reduced query time by 60%" in b and "Built REST APIs in Python" in b              # good edit kept; the bullet with the invented number fell back to its original
    assert out["fit"] == "partial" and out["rejected"]


def make_guard_for(cv):
    from app.services.tailor_service import make_guard
    return make_guard(cv)


def test_one_repair_round_recovers_a_refused_summary():
    from app.cvtools import cv as cvmod
    answers = iter([{"summary": "Backend developer with Kubernetes experience.", "sections": {}, "fit": "partial"}, {"summary": "Backend developer building machine learning features.", "sections": {}, "fit": "partial"}])
    asked = []
    out = cvmod.ai_tailor_with(CV2, {"title": "t", "company": "c", "description": "d"}, lambda s, u: (asked.append(u), json.dumps(next(answers)))[1], make_guard_for(CV2))
    assert out["cv"]["summary"].startswith("Backend developer building machine learning") and not out["rejected"] and len(asked) == 2 and "kubernetes" in asked[1].lower()


def test_poor_match_is_flagged_in_plain_words():
    from app.services.tailor_service import poor_match
    assert "no recognisable skills" in poor_match([], {"percent": 0}, "") and poor_match(["a", "b"], {"percent": 5}, "").startswith("Poor match: only 5%") and poor_match(["a"], {"percent": 60}, "strong") == ""
