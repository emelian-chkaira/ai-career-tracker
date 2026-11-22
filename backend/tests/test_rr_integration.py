"""Reactive Resume integration against a fake RR server (no network)."""
import json, httpx
from app.cvtools import rxresume
from app.services import rr_service

A = "/api/v1/me/rr"
CV = {"name": "Sam Doe", "email": "s@example.com", "summary": "Backend developer", "skills": ["python"], "experience": [{"heading": "Acme | Dev  2020 - 2022", "title": "Dev", "place": "Acme", "date": "2020 - 2022", "bullets": ["Built APIs"]}]}


class Fake:
    """Pretends to be an RR instance: records requests and answers like the documented API."""
    def __init__(self): self.calls = []; self.rx = rxresume.to_rx(CV)
    def __call__(self, method, url, **kw):
        self.calls.append((method, url, kw)); req = httpx.Request(method, url); h = kw.get("headers") or {}
        if h.get("x-api-key") != "rr_goodkey123": return httpx.Response(403, request=req)
        path = url.split("/api/openapi", 1)[1]
        if method == "GET" and path == "/resumes": return httpx.Response(200, json=[{"id": "abc-123", "name": "My CV", "updatedAt": "2026-01-01"}], request=req)
        if method == "GET" and path == "/resumes/abc-123": return httpx.Response(200, json={"id": "abc-123", "data": self.rx}, request=req)
        if method == "POST" and path == "/resumes/file-imports": return httpx.Response(201, json="new-id-9", request=req)
        if method == "GET" and path.endswith("/exports/pdf"): return httpx.Response(200, content=b"%PDF-1.4 fake", request=req)
        return httpx.Response(404, request=req)


def test_connect_list_import_push_pdf(client, make_user, monkeypatch):
    h, _ = make_user(); fake = Fake(); monkeypatch.setattr(rr_service.httpx, "request", fake)
    monkeypatch.setattr("app.core.netguard.check_host", lambda host: None)
    assert client.get(A, headers=h).json()["connected"] is False
    bad = client.put(A, json={"base_url": "https://rr.example.org", "api_key": "rr_wrongkey123"}, headers=h); assert bad.status_code == 400 and "read, write" in bad.text
    ok = client.put(A, json={"base_url": "https://rr.example.org/", "api_key": "rr_goodkey123"}, headers=h); assert ok.status_code == 200 and "rr_goodkey123" not in ok.text
    st = client.get(A, headers=h); assert st.json() == {"connected": True, "base_url": "https://rr.example.org", "default_url": "https://rxresu.me"} and "rr_goodkey123" not in st.text
    assert client.get(f"{A}/resumes", headers=h).json()[0]["name"] == "My CV"
    cv = client.post(f"{A}/import/abc-123", headers=h).json()["cv"]; assert cv["name"] == "Sam Doe" and cv["experience"]
    p = client.post(f"{A}/push", json={"cv": CV, "name": "Tailored"}, headers=h); assert p.status_code == 201 and p.json()["id"] == "new-id-9" and p.json()["url"].endswith("/builder/new-id-9")
    sent = [c for c in fake.calls if c[0] == "POST"][0]; assert sent[2]["data"]["format"] == "REACTIVE_RESUME" and json.loads(sent[2]["files"]["file"][1])
    import base64; assert base64.b64decode(client.get(f"{A}/pdf/abc-123", headers=h).json()["pdf_b64"]).startswith(b"%PDF")
    assert client.delete(A, headers=h).status_code == 204 and client.get(A, headers=h).json()["connected"] is False


def test_private_hosts_refused_and_isolation(client, make_user, monkeypatch):
    monkeypatch.setattr("app.core.netguard.settings.allow_private_hosts", False)
    h, _ = make_user(); r = client.put(A, json={"base_url": "http://127.0.0.1:3000", "api_key": "rr_goodkey123"}, headers=h); assert r.status_code == 400
    h2, _ = make_user("other@example.com"); assert client.get(f"{A}/resumes", headers=h2).status_code == 400          # not connected
    assert client.post(f"{A}/import/..%2Fx", headers=h).status_code in (400, 404, 405)
