"""CV Studio library (several CVs and cover letters), scoring with a chosen CV, and the chat that edits them."""
import json
from sqlalchemy import select, text
from app.models import Job
from app.services import llm_service as llm
from tests.test_tailor import _setup, A, CV

D = f"{A}/docs"
CV2 = {**CV, "summary": "Mobile engineer", "skills": ["Flutter", "Dart"], "experience": [{"heading": "Mobile Developer", "title": "Mobile Developer", "place": "Beta", "date": "2022-2024", "desc": "", "bullets": ["Shipped Flutter apps"]}]}


def _score(monkeypatch, n=70): monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps({"score": n, "reason": "ok", "strengths": [], "gaps": ["Kubernetes"], "flags": [], "summary": "s"}))


def test_library_keeps_several_cvs_and_one_default(client, make_user, db):
    h, _ = make_user()
    a = client.post(D, json={"kind": "cv", "name": "Backend", "data": {"cv": CV, "latex": ""}}, headers=h); assert a.status_code == 201, a.text
    b = client.post(D, json={"kind": "cv", "name": "Mobile", "data": {"cv": CV2, "latex": ""}}, headers=h).json()
    docs = client.get(D, headers=h).json()["docs"]; assert {d["name"] for d in docs} == {"Backend", "Mobile"}
    assert [d["name"] for d in docs if d["is_default"]] == ["Backend"]                       # the first CV becomes the scoring default
    assert client.get(f"{A}/cv", headers=h).json()["cv"]["summary"] == "Backend developer"    # and the stored CV every feature reads
    assert client.post(f"{D}/{b['id']}/default", headers=h).status_code == 200
    assert client.get(f"{A}/cv", headers=h).json()["cv"]["summary"] == "Mobile engineer"
    assert client.get(f"{D}/{b['id']}", headers=h).json()["data"]["cv"]["skills"] == ["Flutter", "Dart"]
    assert "Backend developer" not in (db.scalar(text("select string_agg(data_enc, '') from user_docs")) or "")   # encrypted at rest
    client.delete(f"{D}/{b['id']}", headers=h)                                               # deleting the default promotes another
    assert client.get(f"{A}/cv", headers=h).json()["cv"]["summary"] == "Backend developer"


def test_cover_letters_are_kept_and_other_accounts_cannot_see_them(client, make_user):
    h, _ = make_user(); h2, _ = make_user("other@example.com")
    c = client.post(D, json={"kind": "cover", "name": "Acme letter", "data": {"text": "Dear team,"}, "job_id": 5}, headers=h).json()
    assert client.get(f"{D}?kind=cover", headers=h).json()["docs"][0]["note"] == "Dear team,"
    assert client.get(f"{D}/{c['id']}", headers=h2).status_code == 404
    assert client.delete(f"{D}/{c['id']}", headers=h2).status_code == 404
    assert client.post(D, json={"kind": "cover", "name": "x", "data": {"cv": {}}}, headers=h).status_code == 400
    assert client.put(f"{D}/{c['id']}", json={"name": "Renamed", "data": {"text": "Hello"}}, headers=h).status_code == 200
    assert client.get(f"{D}/{c['id']}", headers=h).json()["data"]["text"] == "Hello"


def test_an_old_stored_cv_becomes_the_first_library_cv(client, make_user):
    h, _ = make_user(); client.put(f"{A}/cv", json={"cv": CV}, headers=h)
    docs = client.get(D, headers=h).json()["docs"]
    assert len(docs) == 1 and docs[0]["is_default"] and docs[0]["name"] == "My CV"


def test_a_job_is_scored_with_the_cv_you_pick(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db); _score(monkeypatch)
    a = client.post(D, json={"kind": "cv", "name": "Backend", "data": {"cv": CV}}, headers=h).json()
    b = client.post(D, json={"kind": "cv", "name": "Mobile", "data": {"cv": CV2}}, headers=h).json()
    r = client.post(f"{A}/fit/{j.id}", json={"consent": True}, headers=h); assert r.status_code == 200, r.text
    assert r.json()["cv_name"] == "Backend"                                                   # no choice: the default CV
    r = client.post(f"{A}/fit/{j.id}", json={"consent": True, "cv_id": b["id"]}, headers=h)
    assert r.json()["cv_name"] == "Mobile"                                                    # chosen CV replaces the score for this job
    assert client.get(f"{A}/fit/{j.id}", headers=h).json()["cv_name"] == "Mobile"
    assert client.post(f"{A}/fit/{j.id}", json={"consent": True, "cv_id": 99999}, headers=h).status_code == 404
    client.post(D, json={"kind": "cover", "name": "L", "data": {"text": "x"}}, headers=h)
    cover_id = client.get(f"{D}?kind=cover", headers=h).json()["docs"][0]["id"]
    assert client.post(f"{A}/fit/{j.id}", json={"consent": True, "cv_id": cover_id}, headers=h).status_code == 404   # a letter is not a CV


def test_batch_scoring_uses_the_chosen_cv(client, make_user, db, monkeypatch):
    import time
    h, j = _setup(client, make_user, db); _score(monkeypatch)
    b = client.post(D, json={"kind": "cv", "name": "Mobile", "data": {"cv": CV2}}, headers=h).json()
    t = client.post(f"{A}/fit-batch", json={"job_ids": [j.id], "consent": True, "cv_id": b["id"]}, headers=h); assert t.status_code == 202, t.text
    for _ in range(50):
        s = client.get(f"{A}/fit-batch/{t.json()['task_id']}", headers=h).json()
        if s["status"] != "running": break
        time.sleep(0.1)
    assert s["status"] == "done", s
    assert client.get(f"{A}/fit/{j.id}", headers=h).json()["cv_name"] == "Mobile"


def _say(monkeypatch, reply): monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(reply))
CH = f"{A}/cv-chat"


def test_chat_edits_a_copy_of_the_cv_and_drops_invented_facts(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    _say(monkeypatch, {"reply": "Done.", "edits": [{"field": "summary", "text": "Backend developer who builds Python APIs."},
                                                    {"field": "bullet", "role": 0, "index": 0, "text": "Built REST APIs in Python for 5 million users"},
                                                    {"field": "bullet", "role": 0, "index": 1, "text": "Deployed services on Kubernetes"},
                                                    {"field": "skills", "items": ["SQL", "Python", "Docker"]}]})
    r = client.post(CH, json={"message": "make my summary about APIs", "cv": CV, "job_id": j.id}, headers=h); assert r.status_code == 200, r.text; d = r.json()
    assert d["cv"]["summary"].startswith("Backend developer who builds") and d["cv"]["skills"] == ["SQL", "Python", "Docker"]
    assert d["cv"]["experience"][0]["bullets"][0] == "Built REST APIs in Python"             # invented "5 million" rejected
    assert d["cv"]["experience"][0]["bullets"][1] == "Cut query time by 60%"                  # invented Kubernetes rejected
    assert "left out" in d["reply"] and {c["section"] for c in d["changes"]} == {"Summary", "Skills"}
    assert CV["summary"] == "Backend developer"                                               # the request body copy was not mutated server-side state


def test_what_you_say_in_chat_counts_as_a_fact(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    _say(monkeypatch, {"reply": "Added.", "edits": [{"field": "bullet", "role": 0, "index": -1, "text": "Ran services on Kubernetes"}]})
    d = client.post(CH, json={"message": "I ran services on Kubernetes at Acme", "cv": CV}, headers=h).json()
    assert d["cv"]["experience"][0]["bullets"][-1] == "Ran services on Kubernetes"


def test_chat_writes_and_guards_a_cover_letter(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    _say(monkeypatch, {"reply": "Written.", "letter": "Dear Acme team,\n\nI build Python APIs and would like to join as Python Backend Engineer."})
    d = client.post(CH, json={"message": "write a letter", "target": "cover", "cv": CV, "job_id": j.id}, headers=h).json()
    assert d["letter"].startswith("Dear Acme team")
    _say(monkeypatch, {"reply": "Written.", "letter": "I have 12 years of Rust experience."})
    d = client.post(CH, json={"message": "write a letter", "target": "cover", "cv": CV}, headers=h).json()
    assert d["letter"] is None and "did not use" in d["reply"]


def test_chat_needs_a_model_and_a_cv(client, make_user, db):
    h, _ = make_user()
    assert client.post(CH, json={"message": "hi", "cv": {}}, headers=h).status_code == 400
    assert client.post(CH, json={"message": "hi", "cv": CV}, headers=h).status_code == 400   # no AI model chosen


def test_suggestions_for_a_job_name_what_the_posting_asks(client, make_user, db):
    h, j = _setup(client, make_user, db)
    s = client.post(f"{CH}/suggest/{j.id}", json={"cv": CV}, headers=h).json()
    assert s["job"]["company"] == "Acme" and any("Kubernetes" in x["label"] for x in s["suggestions"])
    assert any(x["target"] == "cover" for x in s["suggestions"])
    assert client.post(f"{CH}/suggest/999999", json={"cv": CV}, headers=h).status_code == 404


# ---- the "My CV" layout, the letter PDF and letters that sound like yours
from app.cvtools import latexcv, cv as cvmod
from app.services import chat_service as chats

MY = {**CV, "links": ["linkedin.com/in/sam", "https://linkedin.com/in/sam", "github.com/sam"], "header": {"note": "Portfolio: [sam.dev](https://sam.dev) Software Engineer | Mobile and AI"},
      "skill_groups": [{"label": "Mobile", "items": ["Flutter", "Dart"]}, {"label": "Backend", "items": ["Python", "FastAPI"]}]}


def test_my_cv_layout_has_my_look_and_clean_header_links():
    src = latexcv.render(MY, "mine")
    assert "\\cvsec{Summary}" in src and "\\sk{Mobile}{Flutter, Dart}" in src and "\\job{Backend Developer}{Acme}{}{2021-2024}" in src
    assert src.count("\\href{https://linkedin.com/in/sam}") == 1 and "sam.dev" in src               # duplicates folded, portfolio link from the import's note kept
    assert "Software Engineer | Mobile and AI" in src and "\\sep" in src.split("\\begin{document}")[0]   # headline recovered; \sep defined
    assert "mine" in latexcv.TEMPLATES and latexcv.render(MY, "nope") == latexcv.render(MY, "classic")


def test_bold_skill_labels_from_a_layout_read_become_groups():
    g = cvmod._skill_groups(["**Mobile:** Flutter, Dart, Swift", "**Backend:** Python, FastAPI,", "Laravel"])
    assert [(x["label"], x["items"]) for x in g] == [("Mobile", ["Flutter", "Dart", "Swift"]), ("Backend", ["Python", "FastAPI", "Laravel"])]


def test_letter_pdf_in_the_cv_look(client, make_user, db):
    h, j = _setup(client, make_user, db)
    src = latexcv.letter_latex("Dear team,\n\nI build APIs.", MY, {"title": "Backend Engineer", "company": "Acme"})
    assert "Dear team," in src and "I build APIs." in src and "Backend Engineer, Acme" in src and "\\LARGE" in src
    if latexcv.compiler():
        r = client.post("/api/v1/cv/letter-pdf", json={"text": "Dear team,\n\nI build APIs.", "cv": MY, "job_id": j.id})
        assert r.status_code == 200 and r.json()["bytes"] > 1000
    assert client.post("/api/v1/cv/letter-pdf", json={"text": "", "cv": MY}).status_code == 422


def test_ai_letters_are_written_in_the_voice_of_your_saved_letters(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db); seen = {}
    def fake(cfg, system, user, **k): seen["system"], seen["user"] = system, user; return json.dumps({"reply": "Written.", "letter": "Hello Acme team,\n\nI build Python APIs."})
    monkeypatch.setattr(llm, "complete", fake)
    client.post(D, json={"kind": "cover", "name": "Old", "data": {"text": "Dear Hiring Manager,\n\nWhat I bring: Python and SQL.\n\nKind regards, Sam"}}, headers=h)
    r = client.post(CH, json={"message": "write a letter for this job", "target": "cover", "cv": CV, "job_id": j.id}, headers=h).json()
    assert r["letter"].startswith("Hello Acme team")
    assert "<examples>" in seen["user"] and "What I bring: Python and SQL." in seen["user"] and "<cv>" in seen["user"] and "write a letter for this job" in seen["user"]
    assert "voice" in seen["system"].lower()
    # the letter being edited is not repeated as its own example
    seen.clear(); client.post(CH, json={"message": "shorter", "target": "cover", "cv": CV, "letter": "Dear Hiring Manager,\n\nWhat I bring: Python and SQL.\n\nKind regards, Sam"}, headers=h)
    assert "<examples>" not in seen["user"]


def test_documents_live_in_folders_and_the_default_folder_is_empty_name(client, make_user):
    h, _ = make_user()
    a = client.post(D, json={"kind": "cv", "name": "NL", "data": {"cv": CV}, "folder": "Netherlands"}, headers=h).json()
    b = client.post(D, json={"kind": "cv", "name": "IT", "data": {"cv": CV2}, "folder": "Default"}, headers=h).json()
    c = client.post(D, json={"kind": "cover", "name": "L", "data": {"text": "x"}, "folder": "  Netherlands  "}, headers=h).json()
    assert (a["folder"], b["folder"], c["folder"]) == ("Netherlands", "", "Netherlands")      # "Default" is the unnamed folder; names are trimmed
    r = client.get(D, headers=h).json(); assert r["folders"] == ["Netherlands"]
    client.put(f"{D}/{b['id']}", json={"folder": "Italy"}, headers=h)                       # move
    assert {d["name"]: d["folder"] for d in client.get(D, headers=h).json()["docs"]} == {"NL": "Netherlands", "IT": "Italy", "L": "Netherlands"}
    assert client.get(D, headers=h).json()["folders"] == ["Italy", "Netherlands"]
    client.put(f"{D}/{a['id']}", json={"data": {"cv": CV}}, headers=h)                      # saving content keeps the folder
    assert client.get(f"{D}/{a['id']}", headers=h).json()["folder"] == "Netherlands"


def test_extract_text_for_letter_upload(client, make_user):
    h, _ = make_user()
    r = client.post("/api/v1/cv/extract-text?filename=letter.txt", content=b"Dear team,\nI would like to join you.", headers=h)
    assert r.status_code == 200 and "Dear team" in r.json()["text"]
    assert client.post("/api/v1/cv/extract-text?filename=x.txt", content=b"", headers=h).status_code == 400


def test_an_uploaded_letter_loses_its_letterhead_and_gets_its_paragraphs_back():
    from app.cvtools import cv as cvmod
    raw = ("Jane Roe\nUtrecht | +31 6 1 | jane@x.nl\n24 November 2026\nApplication for an internship\nDear Hiring Manager,\n"
           "I am writing to apply for an internship. I build mobile apps and I really want to keep learning on a team that\nships real products.\n"
           "I have worked with more than ten live projects and deliv-\nered them all on time for several different clients over the years.\n"
           "What I bring\n- Mobile: Flutter and Swift with clean architecture across several shipped apps and a long list of\nreleases.\n- Backend: Python and FastAPI.\n"
           "Kind regards,\nJane Roe")
    out = cvmod.clean_letter(raw)
    assert out.startswith("Dear Hiring Manager,") and "jane@x.nl" not in out
    assert "delivered them all" in out and "\n\nWhat I bring\n\n- Mobile" in out and "releases.\n- Backend" in out
    assert out.endswith("Kind regards,\n\nJane Roe")
