"""The starter data must be visible in search, not only present in the database."""
from app.services import seed_service as seed


def test_starter_jobs_can_be_found(client, db, monkeypatch):
    rows = {"companies.csv.gz": [{k: "" for k in seed.CO} | {"name": "Acme", "website": "https://acme.nl", "sponsor_status": "unknown"}],
            "jobs.csv.gz": [{k: "" for k in seed.JB} | {"company": "Acme", "title": "Backend Engineer", "location": "Amsterdam", "city": "Amsterdam", "url": "https://acme.nl/1", "remote": "False"}], "sponsors.csv.gz": []}
    monkeypatch.setattr(seed, "_read", lambda name: rows[name])
    assert seed.load(db)["jobs"] == 1
    for query in ("", "?country=NL", "?sector=tech", "?q=backend"):
        assert client.get(f"/api/v1/jobs{query}").json()["total"] == 1, query
