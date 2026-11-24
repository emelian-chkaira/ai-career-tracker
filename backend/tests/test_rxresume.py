"""Reactive Resume v5 interchange: rich text, section mapping, hidden items, round trip."""
import json
import pytest
from app.cvtools import rxresume as rx, cv as cvmod, latexcv

CV = {"name": "Sam Doe", "email": "sam@x.nl", "phone": "+31 6 1234 5678", "location": "Utrecht", "links": ["https://github.com/sam", "https://linkedin.com/in/sam"],
      "header": {"tagline": ["Backend Developer"], "contact": []}, "summary": "Backend developer who loves **APIs**.",
      "skills": ["Python", "SQL", "Docker"], "skill_groups": [{"label": "Languages", "items": ["Python", "SQL"]}, {"label": "Tools", "items": ["Docker"]}], "languages": ["English (C1)", "Dutch (A2)"],
      "experience": [{"heading": "", "title": "Backend Developer", "place": "Acme", "date": "2021 - 2024", "meta": "", "links": [], "desc": "Built the platform.", "tech": "", "kind": "entry", "bullets": ["Built REST APIs in Python", "Cut query time by **60%**"]}],
      "education": [{"heading": "", "title": "BSc Computer Science", "place": "TU Delft", "date": "2017 - 2021", "meta": "", "links": [], "desc": "", "tech": "", "kind": "entry", "bullets": []}],
      "projects": [{"heading": "", "title": "Tracker", "place": "", "date": "2024", "meta": "", "links": [{"label": "repo", "url": "https://github.com/sam/tracker"}], "desc": "Job tracker.", "tech": "FastAPI, React", "kind": "project", "bullets": []}],
      "certifications": ["AWS Cloud Practitioner"], "extras": [], "order": ["summary", "experience", "education", "projects", "skills"], "titles": {}}


def test_export_has_the_v5_shape():
    d = rx.to_rx(CV)
    assert d["basics"]["name"] == "Sam Doe" and d["basics"]["headline"] == "Backend Developer" and d["basics"]["url"]["url"].endswith("github.com/sam")
    assert d["summary"]["content"] == "<p>Backend developer who loves <strong>APIs</strong>.</p>"
    e = d["sections"]["experience"]["items"][0]
    assert e["company"] == "Acme" and e["position"] == "Backend Developer" and e["period"] == "2021 - 2024" and "<li><p>Built REST APIs in Python</p></li>" in e["description"] and e["id"] and e["hidden"] is False
    assert d["sections"]["education"]["items"][0]["school"] == "TU Delft"
    assert d["sections"]["skills"]["items"][0] == {**d["sections"]["skills"]["items"][0], "name": "Languages", "keywords": ["Python", "SQL"]}
    assert [l["level"] for l in d["sections"]["languages"]["items"]] == [4, 1]
    assert {p["network"] for p in d["sections"]["profiles"]["items"]} == {"GitHub", "LinkedIn"}
    assert d["metadata"]["page"]["format"] == "a4"
    json.dumps(d)


def test_round_trip_keeps_the_facts():
    back = rx.from_rx(rx.to_rx(CV))
    assert back["name"] == "Sam Doe" and back["email"] == "sam@x.nl" and back["location"] == "Utrecht"
    assert back["summary"] == "Backend developer who loves **APIs**."
    b = back["experience"][0]; assert (b["title"], b["place"], b["date"]) == ("Backend Developer", "Acme", "2021 - 2024") and b["bullets"] == ["Built REST APIs in Python", "Cut query time by **60%**"] and b["desc"] == "Built the platform."
    assert back["education"][0]["place"] == "TU Delft" and back["education"][0]["title"] == "BSc Computer Science"
    assert back["projects"][0]["links"][0]["url"].endswith("tracker") and back["projects"][0]["kind"] == "project"
    assert back["skills"] == ["Python", "SQL", "Docker"] and back["languages"] == ["English (C1)", "Dutch (A2)"] and back["certifications"] == ["AWS Cloud Practitioner"]
    assert "Backend Developer" in latexcv.to_latex(back) and "Acme" in latexcv.to_latex(back)                 # the imported CV renders


def test_hidden_items_and_unknown_shapes():
    d = rx.to_rx(CV); d["sections"]["experience"]["items"][0]["hidden"] = True; d["summary"]["hidden"] = True
    back = rx.from_rx(d); assert back["experience"] == [] and back["summary"] == ""
    assert rx.from_rx({"data": rx.to_rx(CV)})["name"] == "Sam Doe"                                              # API shape: {id, name, data}
    with pytest.raises(ValueError): rx.from_rx({"hello": 1})


def test_html_with_links_and_nested_lists():
    text, bullets = rx._from_html('<p>See <a href="https://x.dev">my site</a> and <strong>more</strong></p><ul><li><p>One</p></li><li>Two <b>bold</b></li></ul>')
    assert text == "See [my site](https://x.dev) and **more**" and bullets == ["One", "Two **bold**"]


def test_import_cv_accepts_a_json_export():
    out = cvmod.import_cv(json.dumps(rx.to_rx(CV)).encode(), "resume.json")
    assert out["source"] == "rxresume" and out["cv"]["name"] == "Sam Doe" and "\\begin{document}" in out["latex"]


def test_layouts_and_paper_sizes():
    for t in ("classic", "compact", "modern"):
        for p in ("a4", "letter"):
            src = latexcv.render(CV, t, p)
            assert "\\begin{document}" in src and ("a4paper" in src) == (p == "a4") and ("letterpaper" in src) == (p == "letter")
    assert "sfdefault" in latexcv.render(CV, "modern") and "sfdefault" not in latexcv.render(CV, "classic")
    assert latexcv.render(CV, "nope", "nope") == latexcv.render(CV, "classic", "a4")


def test_endpoints_export_preview_and_import(client):
    r = client.post("/api/v1/cv/rx/export", json={"cv": CV}); assert r.status_code == 200 and r.json()["basics"]["name"] == "Sam Doe"
    assert [t["id"] for t in client.get("/api/v1/cv/templates").json()["templates"]] == ["mine", "classic", "compact", "modern"]
    r = client.post("/api/v1/cv/extract?filename=resume.json", content=json.dumps(r.json()).encode(), headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 200 and r.json()["source"] == "rxresume"
    p = client.post("/api/v1/cv/preview", json={"cv": CV, "template": "modern", "paper": "letter"}); assert p.status_code == 200 and p.json()["bytes"] > 1000
    assert client.post("/api/v1/cv/preview", json={"cv": CV, "template": "modern", "paper": "letter"}).json()["cached"] is True


def test_hidden_sections_are_left_out_of_the_pdf_source():
    from app.cvtools import latexcv
    cv = {"name": "Sam", "summary": "Hello there", "skills": ["python"], "experience": [{"heading": "Acme | Dev  2020 - 2022", "bullets": ["Built things"]}]}
    for tpl in latexcv.TEMPLATES:
        full = latexcv.render(cv, tpl, "a4"); hid = latexcv.render({**cv, "hidden": ["experience"]}, tpl, "a4")
        assert "Built things" in full and "Built things" not in hid, tpl
