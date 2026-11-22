"""Countries, regions and work mode; which postings the crawler keeps; search by place; the crawl schedule and the worker heartbeat."""
import datetime as dt
from app.crawler import places
from app.services import ingest_service as ing, policy_service, schedule_service as sch

H = "/api/v1"


def J(title, loc, n=[0]):
    n[0] += 1
    return dict(title=title, location=loc, url=f"https://acme.com/jobs/{n[0]}", description="")


def test_parse_locations():
    p = places.parse
    assert p("Berlin, de").countries == ["DE"] and p("Milano, Italia").countries == ["IT"] and p("Warszawa").countries == ["PL"]
    assert p("Dubai - United Arab Emirates").countries == ["AE"] and p("Riyadh").countries == ["SA"] and p("Doha, Qatar").countries == ["QA"]
    x = p("Finland; France; Germany; Netherlands; Remote - Europe; Spain")
    assert x.countries == ["FI", "FR", "DE", "NL", "ES"] and x.work_mode == "remote" and x.remote_scope == "europe"
    assert p("Remote - EMEA").remote_scope == "emea" and p("Remote").remote_scope == "world"
    assert p("Kraków, Poland (Hybrid)").work_mode == "hybrid" and p("Remote, Netherlands").countries == ["NL"]
    assert p("Drunen Eindstraat 53 5151 AE Drunen Netherlands").countries == ["NL"] and p("1012AB Amsterdam").countries == ["NL"]
    assert p("West Midlands").countries == ["GB"] and p("Austin, TX").countries == ["US"] and p("Berlin, DE").countries == ["DE"] and p("Cincinnati").countries == ["US"]
    assert p("Remote in the US").countries == ["US"] and p("Best").countries == [] and p("Bergen op Zoom").countries == ["NL"]


def test_regions_and_storage_rule():
    assert set(places.expand(["IT"], ["gcc"])) == {"IT", "AE", "SA", "QA", "KW", "BH", "OM"}
    assert "europe" in places.scopes_for(["NL"]) and "gcc" not in places.scopes_for(["NL"]) and "world" in places.scopes_for(["AE"])
    keep = ["NL", "DE"]
    assert places.wanted(places.parse("Berlin, Germany"), keep) and not places.wanted(places.parse("Paris, France"), keep)
    assert places.wanted(places.parse("Remote - Europe"), keep) and not places.wanted(places.parse("Remote - Europe"), keep, keep_remote=False)
    assert not places.wanted(places.parse("Remote in the US"), keep) and places.wanted(places.parse("Paris"), [])        # empty list = everywhere


def test_crawler_keeps_the_configured_countries(db):
    from app.models import Job
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Dev Amsterdam", "Amsterdam"), J("Dev Berlin", "Berlin, Germany"), J("Dev Dubai", "Dubai, UAE"), J("Dev EU", "Remote - Europe")]); db.commit()
    assert {j.title for j in db.query(Job)} == {"Dev Amsterdam", "Dev EU"}                                              # default: NL + remote open to it
    policy_service.save(db, [], 0, 0, countries=["NL", "DE", "AE"])
    ing.store_jobs(db, c, [J("Dev Berlin 2", "Berlin, Germany"), J("Dev Dubai 2", "Dubai, UAE"), J("Dev Paris", "Paris")]); db.commit()
    rows = {j.title: (j.countries, j.work_mode, j.city) for j in db.query(Job)}
    assert rows["Dev Berlin 2"] == (["DE"], "onsite", "Berlin") and rows["Dev Dubai 2"] == (["AE"], "onsite", "Dubai") and "Dev Paris" not in rows
    assert rows["Dev EU"][1] == "remote"
    policy_service.reset(db)


def test_search_by_country_region_and_work_mode(client, make_user, db):
    policy_service.save(db, [], 0, 0, countries=[])                                                                   # store everything for this test
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Python Developer", "Amsterdam"), J("Python Developer DE", "Munich, Germany (Hybrid)"), J("Python Developer Gulf", "Riyadh, Saudi Arabia"),
                           J("Python Developer Remote", "Remote - Europe"), J("Python Developer US", "Austin, TX, USA")]); db.commit()
    g = lambda **kw: {j["title"] for j in client.get(f"{H}/jobs", params={"sector": "tech", **kw}).json()["items"]}
    assert g(country="DE") == {"Python Developer DE", "Python Developer Remote"}                                     # remote open to Europe counts
    assert g(country="DE", remote_open="false") == {"Python Developer DE"}
    assert g(region="gcc") == {"Python Developer Gulf"}
    assert g(region="dach", work_mode="hybrid") == {"Python Developer DE"}
    assert g(work_mode="remote") == {"Python Developer Remote"}
    r = client.get(f"{H}/jobs/sectors").json()
    assert any(x["key"] == "gcc" and x["jobs"] == 1 for x in r["regions"]) and any(x["key"] == "remote" and x["jobs"] == 1 for x in r["work_modes"])
    h, _ = make_user(); client.put(f"{H}/auth/profile", headers=h, json={"sectors": ["tech"], "countries": ["SA", "XX"], "regions": ["dach", "mars"], "work_modes": ["onsite", "hybrid"]})
    me = client.get(f"{H}/auth/me", headers=h).json()["profile"]
    assert me["countries"] == ["SA"] and me["regions"] == ["dach"] and me["country"] == "SA"
    assert {j["title"] for j in client.get(f"{H}/jobs", headers=h, params={"scope": "mine"}).json()["items"]} == {"Python Developer DE", "Python Developer Gulf"}
    policy_service.reset(db)


def test_schedule_window():
    sun_noon = dt.datetime(2026, 11, 22, 11, 0, tzinfo=dt.timezone.utc)                                               # Sunday 12:00 in Amsterdam
    week = {**sch.DEFAULT, "days": [0, 1, 2, 3, 4], "start": "09:00", "end": "18:00"}
    ok, why, nxt = sch.window(week, sun_noon)
    assert not ok and why == "outside the crawl schedule" and nxt.startswith("2026-11-23T09:00")
    assert sch.window({**sch.DEFAULT, "start": "22:00", "end": "06:00"}, sun_noon)[0] is False
    assert sch.window({**sch.DEFAULT, "start": "22:00", "end": "06:00"}, dt.datetime(2026, 11, 23, 3, 0, tzinfo=dt.timezone.utc))[0] is True   # over midnight
    assert sch.window({**sch.DEFAULT, "enabled": False}, sun_noon)[1] == "automatic crawling is switched off"
    assert sch.window(sch.DEFAULT, sun_noon)[0] is True


def test_schedule_api_and_worker_status(client, make_user, db, monkeypatch):
    from app.models import KV
    for k in (sch.BEAT, sch.KEY):
        r = db.get(KV, k)
        if r: db.delete(r)
    db.commit(); sch._cache["v"] = None
    ha, _ = make_user("admin@example.com")                                                                             # first user is admin
    hu, _ = make_user("user@example.com")
    assert client.put(f"{H}/admin/schedule", headers=hu, json={"enabled": False}).status_code == 403
    r = client.put(f"{H}/admin/schedule", headers=ha, json={"enabled": True, "days": [0, 1, 2, 3, 4], "start": "08:00", "end": "20:00", "revisit_hours": 6, "parallel": 99})
    assert r.status_code == 200 and r.json()["parallel"] == 40 and r.json()["revisit_hours"] == 6
    assert client.put(f"{H}/admin/schedule", headers=ha, json={"start": "8am"}).status_code == 400
    st = client.get(f"{H}/admin/worker", headers=hu).json()["status"]
    assert st["state"] == "stopped" and "./run.sh worker" in st["note"]                                                # nobody has reported yet
    sch.beat(db, "running", 3, task="scan_all")
    st = client.get(f"{H}/admin/worker", headers=hu).json()["status"]
    assert st["state"] == "running" and st["inflight"] == 3 and st["task"] == "scan_all" and st["seen_seconds"] <= 2
    import time as _t; real = _t.time; monkeypatch.setattr("app.services.schedule_service.time.time", lambda: real() + 120)
    assert client.get(f"{H}/admin/worker", headers=hu).json()["status"]["state"] == "stopped"                          # silent for 2 minutes
    client.put(f"{H}/admin/schedule", headers=ha, json={})                                                             # back to defaults


def test_policy_countries_validation(client, make_user):
    ha, _ = make_user("admin@example.com")
    r = client.put(f"{H}/admin/policy", headers=ha, json={"countries": ["NL", "DE", "AE"], "keep_remote": False})
    assert r.status_code == 200 and r.json()["countries"] == ["NL", "DE", "AE"] and r.json()["keep_remote"] is False and r.json()["by_country"] is not None
    assert client.put(f"{H}/admin/policy", headers=ha, json={"countries": ["US"]}).status_code == 400                  # only Europe, Middle East and Africa are offered
    client.delete(f"{H}/admin/policy", headers=ha)


def test_preferences_drive_the_crawler(client, make_user, db, monkeypatch):
    from app.models import Task
    policy_service.save(db, [], 0, 0, countries=["NL"])
    h, _ = make_user()
    r = client.put(f"{H}/auth/profile", headers=h, json={"countries": ["NL", "AE"], "regions": ["dach"]}).json()
    assert r["crawl"]["added"] == ["AE", "DE", "AT", "CH"] and r["crawl"]["discovering"] == ["AE", "DE", "AT", "CH"]
    assert policy_service.current()["countries"] == ["NL", "AE", "DE", "AT", "CH"]
    assert {t.payload["country"] for t in db.query(Task).filter(Task.kind == "discover_country")} == {"AE", "DE", "AT", "CH"}
    again = client.put(f"{H}/auth/profile", headers=h, json={"countries": ["NL", "AE"], "regions": ["dach"]}).json()["crawl"]
    assert again == {"added": [], "discovering": [], "requested": []}                                                  # nothing twice
    assert client.put(f"{H}/auth/profile", headers=h, json={"titles": ["x"]}).json().get("crawl") is None           # other fields: crawler untouched
    cov = client.get(f"{H}/jobs/coverage", headers=h).json()
    ae = next(x for x in cov["countries"] if x["code"] == "AE")
    assert ae["collected"] and ae["phase"] == "finding_employers" and ae["finding"] == "queued"
    assert client.get(f"{H}/jobs/coverage", params={"country": "PL"}).json()["countries"][0]["phase"] == "off"     # not collected
    # a closed crawler (public deployment): only remembered as requested
    monkeypatch.setattr("app.services.coverage_service.settings.open_crawler", False)
    h2, _ = make_user("other@example.com")
    assert client.put(f"{H}/auth/profile", headers=h2, json={"countries": ["PL"]}).json()["crawl"] == {"added": [], "discovering": [], "requested": ["PL"]}
    assert "PL" not in policy_service.current()["countries"]
    policy_service.reset(db)


def test_collect_button(client, make_user, db):
    policy_service.save(db, [], 0, 0, countries=["NL"])
    h, _ = make_user()
    assert client.post(f"{H}/jobs/coverage/collect", json={"country": ["PL"]}).status_code == 401
    r = client.post(f"{H}/jobs/coverage/collect", headers=h, json={"country": ["PL", "US"]}).json()
    assert r["added"] == ["PL"] and r["discovering"] == ["PL"] and "PL" in policy_service.current()["countries"]
    policy_service.reset(db)
