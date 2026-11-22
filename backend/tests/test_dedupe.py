"""One role, one job: the same role in several cities / links / sources is one job; link labels are not titles."""
from app.crawler import dedupe
from app.models import Job
from app.services import ingest_service as ing, maintenance_service as maint, policy_service


def J(title, loc="Amsterdam", url=None, n=[0]):
    n[0] += 1
    return dict(title=title, location=loc, url=url or f"https://acme.nl/jobs/{n[0]}", description="")


def test_canonical_titles():
    c = dedupe.canonical
    assert c("Projektleiter Industrieanlagen (m/w/d)") == c("Projektleiter Industrieanlagen") == "projektleiter industrieanlagen"
    assert c("Winkelmedewerker Amsterdam (24 uur)") == c("Winkelmedewerker Utrecht (32 uur)") == "winkelmedewerker"
    assert c("Backend Developer – Amsterdam") == c("Backend Developer (Remote)") == c("backend developer")
    assert c("Software Engineer Industriële Automatisering") == c("Software Engineer Industriele Automatisering")
    assert dedupe.similar("Software Engineer Industriële Automatisering", "Software Engineer Industriele Automatisering V") and not dedupe.similar("Site Engineer", "Petroleum Engineer")
    assert c("Senior Data Engineer") != c("Data Engineer") and c("Docent 1e graads") != c("Docent 2e graads")


def test_link_labels_and_titles_from_links():
    assert all(dedupe.nav_label(t) for t in ["Skip to main content", "mehr\xa0Informationen\xa0›", "Bekijk vacature", "View Job & Apply", "Details ansehen"])
    assert not dedupe.nav_label("Data Engineer")
    u = dedupe.title_from_url
    assert u("https://bau.de/jobs/bauleiter-hochbau") == "Bauleiter Hochbau" and u("https://x.com/jobs/senior-data-engineer-12345") == "Senior Data Engineer"
    assert u("https://airbus.com/careers/international-women-at-airbus") is None and u("https://airbus.com/careers/apprentices/a") is None
    assert dedupe.sane_location("Amsterdam, Netherlands") == "Amsterdam, Netherlands" and dedupe.sane_location("✔ Werken aan de automatisering van grote fabrieksprocessen, van proceslogica tot besturing in de controlekamer") == ""


def test_same_role_in_three_cities_is_one_job(db):
    policy_service.save(db, [], 0, 0, countries=[])
    c = ing.add_company(db, "Acme")
    n = ing.store_jobs(db, c, [J("Projektleiter (m/w/d)", "Mainz, Germany"), J("Projektleiter (m/w/d)", "Munich, Germany"), J("Projektleiter", "Amsterdam, Netherlands"),
                               J("Data Engineer"), J("Skip to main content", url="https://acme.nl/jobs/bauleiter-hochbau"), J("Skip to main content", url="https://acme.nl/about/life-at-acme")]); db.commit()
    jobs = {j.title: j for j in db.query(Job)}
    assert n == 3 and set(jobs) == {"Projektleiter (m/w/d)", "Data Engineer", "Bauleiter Hochbau"}
    p = jobs["Projektleiter (m/w/d)"]
    assert [a["city"] for a in p.alternates] == ["Munich", "Amsterdam"] and set(p.countries) == {"DE", "NL"}
    policy_service.reset(db)


def test_employer_link_wins_over_board_and_vanished_links_are_handled(db):
    policy_service.save(db, [], 0, 0, countries=[])
    c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [J("Data Engineer (f/m/x)", "Netherlands; Remote", url="https://indeed.com/job/1")], source="board:indeed", expire=False)
    ing.store_jobs(db, c, [J("Data Engineer", url="https://acme.nl/jobs/de"), J("Data Engineer", "Utrecht", url="https://acme.nl/jobs/de-utrecht")]); db.commit()
    (j,) = db.query(Job).all()
    assert j.url == "https://acme.nl/jobs/de" and j.source == "company-site" and {a["url"] for a in j.alternates} == {"https://indeed.com/job/1", "https://acme.nl/jobs/de-utrecht"}
    ing.store_jobs(db, c, [J("Data Engineer", "Utrecht", url="https://acme.nl/jobs/de-utrecht")]); db.commit()      # the main link vanished, Utrecht is still listed
    db.refresh(j)
    assert j.status == "open" and j.url == "https://acme.nl/jobs/de-utrecht" and [a["url"] for a in j.alternates] == ["https://indeed.com/job/1"]
    ing.store_jobs(db, c, [J("Other job", url="https://acme.nl/jobs/x")]); db.commit()                                 # listed nowhere on the site any more
    db.refresh(j); assert j.status == "expired"
    policy_service.reset(db)


def test_collapse_existing_duplicates(db):
    policy_service.save(db, [], 0, 0, countries=[])
    c = ing.add_company(db, "Acme")
    for i, city in enumerate(["Mainz", "Munich", "Berlin"]):                       # stored before folding existed: three rows, three keys
        db.add(Job(company_id=c.id, title="Projektleiter (m/w/d)", location=city, city=city, url=f"https://acme.de/{i}", dedupe_key=f"old{i}", countries=["DE"], alternates=[]))
    db.add(Job(company_id=c.id, title="Skip to main content", url="https://acme.de/jobs/bauleiter-hochbau", dedupe_key="x", alternates=[]))
    db.add(Job(company_id=c.id, title="View Job & Apply", url="https://acme.de/jobs/petroleum-engineer", dedupe_key="y", countries=["DE"],
               alternates=[{"url": f"https://acme.de/jobs/{t}", "location": "Berlin", "city": "Berlin", "countries": ["DE"], "source": "company-site"} for t in ("factory-manager", "plant-technician", "site-engineer")]))
    db.commit()
    r = maint.collapse_duplicates(db)
    titles = sorted(j.title for j in db.query(Job).filter(Job.status == "open"))
    assert r["jobs_merged"] == 2 and r["titles_fixed"] == 2 and r["wrong_groups_split"] == 3
    assert titles == ["Bauleiter Hochbau", "Factory Manager", "Petroleum Engineer", "Plant Technician", "Projektleiter (m/w/d)", "Site Engineer"]
    policy_service.reset(db)
