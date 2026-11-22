"""Employers are matched without legal form, so job boards do not create duplicates; duplicates can be merged."""
from app.models import Company, Job
from app.services import ingest_service as ing, maintenance_service as maint


def test_norm_name():
    n = ing.norm_name
    assert n("Prodrive Technologies B.V.") == n("Prodrive Technologies") == n("prodrive technologies bv")
    assert n("Awin AG") == n("Awin") and n("Mozilla Corporation") == n("Mozilla") and n("Lobster DATA GmbH") == n("Lobster Data")
    assert n("Xccelerated | Part of Xebia") == n("Xccelerated") and n("ASML Netherlands B.V.") == n("ASML")
    assert n("ICT Group") != n("ICT") and n("AS Watson") != n("Watson")


def test_add_company_reuses_the_existing_employer(db):
    a = ing.add_company(db, "Prodrive Technologies"); db.commit()
    assert ing.add_company(db, "Prodrive Technologies B.V.").id == a.id and db.query(Company).count() == 1


def test_merge_companies(db):
    a = Company(name="Datamaran"); b = Company(name="Datamaran Ltd", website="https://datamaran.com"); db.add_all([a, b]); db.flush()
    J = lambda t, n=[0]: dict(title=t, location="Amsterdam", url=f"https://x.nl/{(n.__setitem__(0, n[0] + 1), n[0])[1]}", description="")
    ing.store_jobs(db, a, [J("Staff Engineer")]); ing.store_jobs(db, b, [J("Staff Engineer"), J("Data Scientist")]); db.commit()
    r = maint.merge_companies(db, a.id, [b.id])
    assert r == {"kept": "Datamaran", "jobs_moved": 1, "duplicate_jobs_removed": 1}
    assert db.query(Company).count() == 1 and db.get(Company, a.id).website == "https://datamaran.com"
    assert {j.title for j in db.query(Job)} == {"Staff Engineer", "Data Scientist"}
