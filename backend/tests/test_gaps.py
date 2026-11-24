"""CV gap suggestions: proposals are pre-filled and editable, and once accepted they become CV facts the tailoring guard allows."""
from app.cvtools import gaps
from app.services import tailor_service as ts

CV = {"name": "Sam", "email": "s@x.nl", "phone": "", "location": "Utrecht", "links": ["https://linkedin.com/in/sam"], "summary": "Flutter developer", "skills": ["Flutter", "Dart", "Firebase"], "languages": ["English"], "certifications": [],
      "experience": [{"heading": "Mobile Developer", "title": "Mobile Developer", "place": "Acme", "date": "2021 – 2024", "desc": "", "bullets": ["Built Flutter apps", "Cut load time by 40%"]}], "projects": [], "education": []}


def test_mobile_gaps_are_proposed_with_editable_text():
    r = gaps.analyse(CV, "mobile"); ids = {p["term"]: p for p in r["proposals"]}
    assert "Flutter" in r["covered"] and "Flutter" not in ids
    assert ids["CI/CD"]["kind"] == "experience" and ids["CI/CD"]["index"] == 0 and ids["CI/CD"]["text"]       # a ready-to-edit bullet for the Mobile Developer role
    assert ids["Agile / Scrum"]["kind"] == "skill"
    assert any(t["id"] == "tip-github" for t in r["tips"])                                                       # GitHub link missing


def test_job_gaps_list_only_missing_keywords():
    r = gaps.analyse(CV, "", {"title": "Flutter Developer", "company": "Acme", "description": "Flutter, Dart, Kubernetes and Terraform. " * 6})
    terms = {p["term"] for p in r["proposals"]}
    assert {"Kubernetes", "Terraform"} <= terms and "Flutter" not in terms


def test_accepted_proposal_passes_the_fact_guard():
    new = "Automated builds and releases to TestFlight and Google Play with a CI/CD pipeline."
    assert ts.make_guard(CV)(new)                                              # before accepting: a new skill, rejected
    cv2 = {**CV, "experience": [{**CV["experience"][0], "bullets": CV["experience"][0]["bullets"] + [new]}]}
    assert ts.make_guard(cv2)(new) == []                                       # once it is a CV fact, the tailor may use it


def test_gaps_endpoint(client):
    r = client.post("/api/v1/cv/gaps", json={"cv": CV, "target": "internship"}); assert r.status_code == 200, r.text
    assert r.json()["label"] == "Internship" and r.json()["proposals"]
