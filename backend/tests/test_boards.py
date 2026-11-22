"""Job boards (experimental): the search plan, block handling with cool-downs, and storing results. The boards are never called."""
from app.crawler import boards
from app.services import boards_service as bs, policy_service
from app.models import Job


def _on(monkeypatch, sites="linkedin,indeed,bayt"):
    monkeypatch.setattr(bs.settings, "board_sites", sites); monkeypatch.setattr(bs.settings, "board_max_searches", 10)


def test_plan_explains_every_term(client, make_user, db, monkeypatch):
    _on(monkeypatch); policy_service.save(db, [], 0, 0, countries=["NL", "AE"])
    h, _ = make_user(); client.put("/api/v1/auth/profile", headers=h, json={"titles": ["Junior Architect"]})
    h2, _ = make_user("b@example.com"); client.put("/api/v1/auth/profile", headers=h2, json={"sectors": ["finance"]})
    p = bs.plan(db)
    origin = {t["term"]: t["from"] for t in p["terms"]}
    assert origin["Junior Architect"].startswith("job title in 1 user") and "Finance" in origin["Accountant"]
    nl = next(s for s in p["searches"] if s["country"] == "NL")
    assert {b["site"]: b["skip"] for b in nl["boards"]}["bayt"] == "Bayt only lists Gulf and Middle East jobs"
    assert bs.plan(db, terms=["Revit"], countries=["DE"])["searches"] == [{"term": "Revit", "country": "DE", "boards": [
        {"site": "linkedin", "where": "Germany", "skip": None}, {"site": "indeed", "where": "Germany", "skip": None}, {"site": "bayt", "where": "Germany", "skip": "Bayt only lists Gulf and Middle East jobs"}]}]
    assert boards.where_for("glassdoor", "DE") == "Berlin"                                   # Glassdoor gets a city
    policy_service.reset(db)


def test_blocks_make_a_board_rest_and_count_as_failures(db, monkeypatch):
    _on(monkeypatch, "linkedin,indeed")
    calls = []
    def fake(site, term, country, location="", results=30, hours_old=168):
        calls.append(site)
        if site == "linkedin": return [], "response status code 429 (blocked: use a proxy)"
        return [("Acme B.V.", dict(title=f"{term} dev", location="Amsterdam, Netherlands", url=f"https://acme.nl/{term}", description="", posted_at=None, board=site))], None
    monkeypatch.setattr(boards, "search_site", fake)
    p = bs.plan(db, terms=["python", "java"], countries=["NL"])
    r = bs.run(db, p)
    assert calls == ["linkedin", "indeed", "indeed"]                                         # LinkedIn rests after its block, Indeed carries on
    assert r["blocked"] == 1 and r["skipped"] == 1 and r["new_jobs"] == 2
    li = next(x for x in bs.health(db) if x["site"] == "linkedin")
    assert li["kind"] == "blocked" and li["resting_until"] and li["blocks_in_row"] == 1
    assert {j.source for j in db.query(Job)} == {"board:indeed"}
    assert "resting" in bs.plan(db, terms=["x"], countries=["NL"])["searches"][0]["boards"][0]["skip"]
    from app.models import KV
    db.delete(db.get(KV, bs.KEY)); db.commit()


def test_board_endpoints(client, make_user, monkeypatch):
    _on(monkeypatch)
    h, _ = make_user()
    r = client.get("/api/v1/admin/boards", headers=h).json()
    assert r["enabled"] and {x["site"] for x in r["health"]} == set(boards.SITES) and "searches" in r["plan"]
    p = client.post("/api/v1/admin/boards/plan", headers=h, json={"terms": ["Revit"], "countries": ["be"]}).json()
    assert p["terms"] == [{"term": "Revit", "from": "chosen for this run"}] and p["countries"] == ["BE"]
    pl = client.get("/api/v1/admin/pipeline", headers=h).json()
    assert set(pl) == {"discover", "locate", "read", "understand", "keep", "notify", "boards"}
