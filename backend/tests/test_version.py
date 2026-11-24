"""One version number everywhere, and a changelog entry for it."""
import json, pathlib
from app import version as v

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_version_is_the_same_in_code_frontend_and_changelog():
    assert v.__version__ == "1.0.2"
    assert json.loads((ROOT / "frontend/package.json").read_text())["version"] == v.__version__
    log = v.changelog(); assert log and log[0]["version"] == v.__version__ and log[0]["date"]
    assert [e["version"] for e in log] == ["1.0.2", "1.0.1", "1.0.0"]
    assert log[0]["sections"]["Added"] and "Changed" in log[0]["sections"]


def test_version_endpoint_is_public_and_lists_the_changelog(client):
    r = client.get("/api/v1/version"); assert r.status_code == 200, r.text; d = r.json()
    assert d["version"] == "1.0.2" and d["released"] == "2026-11-24"
    assert d["changelog"][0]["sections"]["Fixed"] and len(d["changelog"]) == 3
    assert client.get("/api/openapi.json").json()["info"]["version"] == "1.0.2"
