"""CV coach: chat turns what you say into reviewable CV additions; invented facts never get through."""
import json
from sqlalchemy import select
from app.models import Job
from app.services import llm_service as llm
from tests.test_tailor import _setup, A, CV

C = f"{A}/cv-coach"


def _say(monkeypatch, reply): monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(reply))


def test_a_stated_skill_becomes_a_proposal_and_an_invented_one_is_dropped(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    _say(monkeypatch, {"reply": "Added.", "proposals": [{"kind": "skill", "text": "Kubernetes"}, {"kind": "skill", "text": "Rust"}, {"kind": "bullet", "role": 0, "text": "Deployed services to Kubernetes for 3 teams."}]})
    r = client.post(C, json={"message": "I have used Kubernetes at Acme", "job_id": j.id, "history": []}, headers=h)
    assert r.status_code == 200, r.text; d = r.json()
    kinds = [(p["kind"], p["text"]) for p in d["proposals"]]
    assert ("skill", "Kubernetes") in kinds                              # you said it
    assert not any("Rust" in t for _, t in kinds)                         # you did not
    assert not any("3 teams" in t for _, t in kinds)                      # an invented number never passes


def test_gaps_lists_what_the_posting_asks_for_and_the_cv_lacks(client, make_user, db):
    h, j = _setup(client, make_user, db)
    assert "Kubernetes" in client.get(f"{C}/gaps/{j.id}", headers=h).json()["missing"]


def test_accepted_additions_reach_the_stored_cv_and_the_match(client, make_user, db):
    h, j = _setup(client, make_user, db)
    r = client.post(f"{C}/apply", json={"proposals": [{"kind": "skill", "text": "Kubernetes"}, {"kind": "bullet", "role": 0, "text": "Ran services on Kubernetes."},
                                                       {"kind": "project", "title": "Tracker", "text": "A job tracker.", "tech": "Python"}]}, headers=h)
    assert r.status_code == 200, r.text
    cv = client.get(f"{A}/cv", headers=h).json()["cv"]
    assert "Kubernetes" in cv["skills"] and cv["experience"][0]["bullets"][-1] == "Ran services on Kubernetes." and cv["projects"][0]["title"] == "Tracker"
    assert "Kubernetes" not in client.get(f"{C}/gaps/{j.id}", headers=h).json()["missing"]


def test_needs_a_saved_cv(client, make_user):
    h, _ = make_user()
    assert client.post(C, json={"message": "hi"}, headers=h).status_code == 400


def test_adding_a_skill_by_name_is_never_blocked_by_questions(client, make_user, db, monkeypatch):
    h, j = _setup(client, make_user, db)
    _say(monkeypatch, {"reply": "Could you share a public project?", "proposals": []})        # the model keeps asking
    r = client.post(C, json={"message": "add a skills of image processing", "job_id": j.id, "history": []}, headers=h).json()
    assert [(p["kind"], p["text"]) for p in r["proposals"]] == [("skill", "Image processing")]
    r2 = client.post(C, json={"message": "how are you", "history": []}, headers=h).json()
    assert r2["proposals"] == []
