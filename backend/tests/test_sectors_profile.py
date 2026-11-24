"""Sectors, countries, the per-user feed on the shared catalogue, profile merging, and per-account CV drafts."""
from app.crawler import sectors
from app.services import ingest_service as ing

H = "/api/v1"


def J(title, loc="Amsterdam, Netherlands", desc="", n=[0]):
    n[0] += 1
    return dict(title=title, location=loc, url=f"https://acme.nl/jobs/{n[0]}", description=desc)


def test_classify_sector():
    c = sectors.classify
    assert c("Architect") == "architecture" and c("Landschapsarchitect") == "architecture" and c("Werkvoorbereider Installatietechniek") == "architecture"
    assert c("Software Architect") == "tech" and c("Senior Solutions Architect - SIEM") == "tech" and c("Klant Architect") == "tech"
    assert c("Senior Data Engineer") == "tech" and c("Flutter Developer") == "tech"
    assert c("Mechanical Engineer") == "engineering" and c("Monteur Elektrotechniek") == "engineering"
    assert c("Sales Engineer") == "sales_marketing" and c("Account Manager") == "sales_marketing"
    assert c("Verpleegkundige") == "healthcare" and c("Docent wiskunde") == "education" and c("Recruiter") == "people_legal"
    assert c("PhD candidate machine learning") == "tech" and c("Controller") == "finance" and c("") == "other"
    assert sectors.category_of("tech") == "tech" and sectors.category_of("architecture") == "other"


def test_country_of_first_place():
    assert sectors.country_of("Amsterdam, Netherlands; Berlin, Germany") == "NL"
    assert sectors.country_of("Berlin, de") == "DE" and sectors.country_of("Brussels, Belgium") == "BE"
    assert sectors.country_of("The Hague") == "NL" and sectors.country_of("") == "NL"


def test_ingest_sets_sector_and_country(db):
    from app.models import Job
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Junior Architect", "Rotterdam"), J("Backend Developer"), J("Brussels Developer", "Brussels, Belgium")]); db.commit()
    rows = {j.title: (j.sector, j.category, j.country) for j in db.query(Job)}
    assert rows["Junior Architect"] == ("architecture", "other", "NL")
    assert rows["Backend Developer"] == ("tech", "tech", "NL")
    assert "Brussels Developer" not in rows                                         # the crawler keeps Dutch postings only


def test_sectors_endpoint(client, db):
    c = ing.add_company(db, "Acme"); ing.store_jobs(db, c, [J("Architect"), J("Python Developer")]); db.commit()
    r = client.get(f"{H}/jobs/sectors").json()
    by = {s["key"]: s for s in r["sectors"]}
    assert by["architecture"]["jobs"] == 1 and by["tech"]["jobs"] == 1 and "Revit" in by["architecture"]["skills"]
    assert any(x["code"] == "NL" and x["jobs"] == 2 for x in r["countries"]) and "other" not in by


def test_profile_update_merges_and_validates(client, make_user):
    h, _ = make_user()
    client.put(f"{H}/auth/profile", headers=h, json={"titles": ["Architect"], "sectors": ["architecture", "nonsense"], "country": "NL"})
    p = client.put(f"{H}/auth/profile", headers=h, json={"onboarded": True, "prefs": {"cv_template": "modern"}}).json()["profile"]
    assert p["titles"] == ["Architect"] and p["sectors"] == ["architecture"] and p["onboarded"] is True and p["prefs"] == {"cv_template": "modern"}
    p = client.put(f"{H}/auth/profile", headers=h, json={"prefs": {"ai_consent": True}}).json()["profile"]
    assert p["prefs"] == {"cv_template": "modern", "ai_consent": True}                 # prefs merge too
    assert client.put(f"{H}/auth/profile", headers=h, json={"country": "Netherlands"}).status_code == 422


def test_my_feed_follows_each_users_profile(client, make_user, db):
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Junior Architect", "Rotterdam"), J("BIM Modeller", "Utrecht"), J("Backend Developer", "Rotterdam"), J("Account Manager")]); db.commit()
    ha, _ = make_user("arch@example.com"); hd, _ = make_user("dev@example.com")
    client.put(f"{H}/auth/profile", headers=ha, json={"sectors": ["architecture"], "cities": ["Rotterdam"], "titles": ["Architect"]})
    client.put(f"{H}/auth/profile", headers=hd, json={"sectors": ["tech"], "titles": ["Backend Developer"]})
    arch = client.get(f"{H}/jobs", headers=ha, params={"scope": "mine"}).json()
    assert [j["title"] for j in arch["items"]] == ["Junior Architect"]                      # architecture + Rotterdam (or remote)
    assert arch["query"]["profile"]["sector"] == ["architecture"] and arch["sort"] == "newest"                     # newest first; profile match is a choice
    assert arch["items"][0]["sector"] == "architecture" and arch["items"][0]["fit"] > 50
    dev = client.get(f"{H}/jobs", headers=hd, params={"scope": "mine"}).json()
    assert [j["title"] for j in dev["items"]] == ["Backend Developer"]
    # an explicit filter overrides the profile; "all" ignores it
    assert {j["title"] for j in client.get(f"{H}/jobs", headers=ha, params={"scope": "mine", "sector": "tech"}).json()["items"]} == {"Backend Developer"}
    assert client.get(f"{H}/jobs", headers=ha, params={"scope": "all"}).json()["total"] == 4
    # visitors see the tech catalogue unless they pick a sector
    assert {j["title"] for j in client.get(f"{H}/jobs").json()["items"]} == {"Backend Developer"}
    assert client.get(f"{H}/jobs", params={"sector": ["architecture", "sales_marketing"]}).json()["total"] == 3


def test_cv_draft_is_per_account(client, make_user):
    ha, _ = make_user("a@example.com"); hb, _ = make_user("b@example.com")
    draft = {"cv": {"name": "Alice", "skills": ["Revit", "Rhino"], "experience": []}, "latex": "", "template": "modern"}
    assert client.put(f"{H}/me/cv/draft", headers=ha, json={"draft": draft}).status_code == 200
    assert client.get(f"{H}/me/cv/draft", headers=ha).json()["draft"]["cv"]["name"] == "Alice"
    assert client.get(f"{H}/me/cv/draft", headers=hb).status_code == 404                 # the other account never sees it
    assert client.get(f"{H}/me/cv/draft").status_code == 401
    assert client.get(f"{H}/auth/me", headers=ha).json()["profile"]["cv_skills"] == ["Revit", "Rhino"]
    assert client.delete(f"{H}/me/cv/draft", headers=ha).status_code == 204 and client.get(f"{H}/me/cv/draft", headers=ha).status_code == 404


def test_resend_verification_has_its_own_limit(client, make_user):
    h, _ = make_user()
    assert client.post(f"{H}/auth/verify/send", headers=h).status_code == 202              # right after sign-up: not blocked by the sign-in limit
    for _ in range(2): client.post(f"{H}/auth/verify/send", headers=h)
    r = client.post(f"{H}/auth/verify/send", headers=h)
    assert r.status_code == 429 and "spam" in r.json()["detail"]


def test_level_preference_keeps_postings_without_a_level(client, make_user, db):
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Junior Python Developer"), J("Python Developer"), J("Senior Python Developer"), J("Python Developer Internship")]); db.commit()
    h, _ = make_user(); client.put(f"{H}/auth/profile", headers=h, json={"sectors": ["tech"], "job_types": ["junior"]})
    assert {j["title"] for j in client.get(f"{H}/jobs", headers=h, params={"scope": "mine"}).json()["items"]} == {"Junior Python Developer", "Python Developer"}
    client.put(f"{H}/auth/profile", headers=h, json={"job_types": ["internship"]})
    assert {j["title"] for j in client.get(f"{H}/jobs", headers=h, params={"scope": "mine"}).json()["items"]} == {"Python Developer Internship"}


def test_best_match_sort_puts_the_closest_jobs_first(client, make_user, db):
    from sqlalchemy import select
    from app.models import Job, JobScore
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Account Manager"), J("Backend Developer"), J("Data Engineer"), J("Office Cleaner")]); db.commit()
    h, u = make_user("best@example.com"); client.put(f"{H}/auth/profile", headers=h, json={"sectors": ["tech"], "titles": ["Backend Developer"], "skills": ["python"]})
    jid = {j.title: j.id for j in db.scalars(select(Job))}
    r = client.get(f"{H}/jobs", headers=h, params={"scope": "all", "sort": "best"}).json()
    assert r["sort"] == "best" and r["items"][0]["title"] == "Backend Developer"                    # profile match ranks the developer role first
    from app.models import User
    uid = db.scalar(select(User.id).where(User.email == "best@example.com"))
    db.add(JobScore(user_id=uid, job_id=jid["Office Cleaner"], score=99, verdict="strong", reason="x", model="m", basis_hash="h")); db.commit()
    r = client.get(f"{H}/jobs", headers=h, params={"scope": "all", "sort": "best"}).json()
    assert r["items"][0]["title"] == "Office Cleaner"                                                    # an AI score of 99 outranks any profile match
