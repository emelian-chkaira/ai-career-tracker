"""AI providers, mailbox sync, classification and the review inbox (no network: HTTP and IMAP are faked)."""
import json, httpx, pytest
from sqlalchemy import select, text
from app.core.config import settings
from app.models import MailEvent, UserJob, Job, Company, Task, User
from app.services import llm_service as llm, mail_service as ms, mail_classifier as mc, ingest_service as ing, task_service
from app.workers import tasks


def mail(subject, body, sender="Acme Talent <jobs@acme.com>", mid="m1"):
    return {"message_id": mid, "sender": sender, "sender_addr": sender.split("<")[-1].strip(">").lower(), "subject": subject, "date": None, "body": body}


# ---------------------------------------------------------------- providers
def test_provider_presets_cover_free_chinese_and_paid():
    assert "rules" not in llm.PROVIDERS        # the offline keyword classifier is gone: an AI model is required
    ids = {p["id"] for p in llm.PROVIDERS.values() and [dict(id=k) for k in llm.PROVIDERS]}
    assert {"ollama", "zhipu", "qwen", "deepseek", "moonshot", "xai", "groq", "openrouter", "anthropic", "openai", "custom"} <= ids


def _fake_http(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **{k: v for k, v in kw.items() if k != "transport"}))


def test_openai_compatible_request_and_think_stripping(monkeypatch):
    seen = {}
    def h(req):
        seen.update(url=str(req.url), auth=req.headers.get("authorization"), body=json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "<think>hmm</think>{\"category\": \"offer\"}"}}]})
    _fake_http(monkeypatch, h)
    out = llm.complete(llm.Cfg("deepseek", "deepseek-chat", None, "sk-secret"), "sys", "user")
    assert out == '{"category": "offer"}' and seen["url"] == "https://api.deepseek.com/v1/chat/completions" and seen["auth"] == "Bearer sk-secret"
    assert seen["body"]["model"] == "deepseek-chat" and seen["body"]["messages"][0]["role"] == "system"


def test_grok_uses_xai_endpoint(monkeypatch):
    seen = {}
    def h(req):
        seen.update(url=str(req.url), auth=req.headers.get("authorization"), model=json.loads(req.content)["model"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    _fake_http(monkeypatch, h)
    assert llm.complete(llm.Cfg("xai", "grok-3-mini", None, "xai-key"), "s", "u") == "ok"
    assert seen == {"url": "https://api.x.ai/v1/chat/completions", "auth": "Bearer xai-key", "model": "grok-3-mini"}
    assert llm.complete(llm.Cfg("groq", "llama-3.1-8b-instant", None, "gsk-key"), "s", "u") == "ok"
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions" and seen["auth"] == "Bearer gsk-key"


def test_gpt_oss_gets_reasoning_settings(monkeypatch):
    seen = {}
    def h(req):
        seen.update(body=json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    _fake_http(monkeypatch, h)
    llm.complete(llm.Cfg("groq", "openai/gpt-oss-20b", None, "k"), "s", "u", max_tokens=10)
    b = seen["body"]
    assert b["reasoning_effort"] == "low" and b["max_completion_tokens"] >= 1500 and "max_tokens" not in b


def test_missing_content_field_is_handled(monkeypatch):
    _fake_http(monkeypatch, lambda req: httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "reasoning": "hmm"}}]}))
    with pytest.raises(llm.LlmError) as e: llm.complete(llm.Cfg("groq", "openai/gpt-oss-20b", None, "k"), "s", "u")
    assert "no text" in str(e.value)


def test_empty_model_answer_is_an_error(monkeypatch):
    _fake_http(monkeypatch, lambda req: httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}))
    with pytest.raises(llm.LlmError): llm.complete(llm.Cfg("groq", "openai/gpt-oss-20b", None, "k"), "s", "u")


def test_anthropic_request_shape(monkeypatch):
    seen = {}
    def h(req):
        seen.update(url=str(req.url), key=req.headers.get("x-api-key"), body=json.loads(req.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "{\"ok\": 1}"}]})
    _fake_http(monkeypatch, h)
    assert llm.complete(llm.Cfg("anthropic", "claude-haiku-5-5", None, "sk-ant-x"), "s", "u") == '{"ok": 1}'
    assert seen["url"].endswith("/v1/messages") and seen["key"] == "sk-ant-x" and seen["body"]["system"] == "s"


def test_errors_never_leak_the_key(monkeypatch):
    _fake_http(monkeypatch, lambda req: httpx.Response(401, text="invalid key sk-secret-123"))
    with pytest.raises(llm.LlmError) as e: llm.complete(llm.Cfg("openai", "gpt-4o-mini", None, "sk-secret-123"), "s", "u")
    assert "sk-secret-123" not in str(e.value)


# ---------------------------------------------------------------- settings API
def test_ai_settings_store_key_encrypted_and_never_return_it(client, make_user, db):
    h, _ = make_user()
    r = client.put("/api/v1/ai/settings", json={"provider": "qwen", "model": "qwen-plus", "api_key": "sk-qwen-secret"}, headers=h).json()
    assert {k: r[k] for k in ("provider", "model", "base_url", "has_key")} == {"provider": "qwen", "model": "qwen-plus", "base_url": None, "has_key": True}
    assert "sk-qwen-secret" not in json.dumps(client.get("/api/v1/ai/settings", headers=h).json())
    assert "sk-qwen-secret" not in (db.scalar(text("select api_key_enc from user_ai_settings")) or "")
    assert client.put("/api/v1/ai/settings", json={"provider": "qwen", "api_key": ""}, headers=h).json()["has_key"] is False       # "" removes it
    assert client.put("/api/v1/ai/settings", json={"provider": "nope"}, headers=h).status_code == 400
    assert any(p["id"] == "zhipu" for p in client.get("/api/v1/ai/providers").json())


def test_private_endpoints_blocked_when_not_allowed(client, make_user, monkeypatch):
    h, _ = make_user(); monkeypatch.setattr(settings, "allow_private_hosts", False)
    assert client.put("/api/v1/ai/settings", json={"provider": "custom", "base_url": "http://127.0.0.1:11434/v1", "model": "x"}, headers=h).status_code == 400
    assert client.post("/api/v1/mail/accounts", json={"host": "localhost", "username": "a", "password": "b"}, headers=h).status_code == 405      # IMAP was removed


# ---------------------------------------------------------------- classification
def _reply(**d):
    return lambda *a, **k: json.dumps({"confidence": 0.9, "summary": "s", **d})


def test_classify_uses_the_model_and_skips_not_job_related(monkeypatch):
    cfg = llm.Cfg("deepseek", "deepseek-chat", None, "k")
    monkeypatch.setattr(llm, "complete", _reply(category="rejection", company="Acme", role="Backend Engineer"))
    r = mc.classify(cfg, mail("Update", "We will not be moving forward"))
    assert (r["category"], r["company"], r["role"], r["classifier"]) == ("rejection", "Acme", "Backend Engineer", "deepseek:deepseek-chat")
    monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps({"category": "not_job_related"}))
    assert mc.classify(cfg, mail("Interview", "invite you to an interview")) is None


def test_prefilter_drops_newsletters():
    assert mc.looks_job_related(mail("Interview invitation", "We would like to invite you to an interview"))
    assert not mc.looks_job_related(mail("Big deals this week", "50% off everything", sender="newsletter@shop.com"))


def test_process_needs_a_model_and_stops_when_the_model_keeps_failing(db, make_user, monkeypatch):
    make_user(); u = db.scalar(select(User))
    with pytest.raises(RuntimeError, match="Choose an AI model"): mc.process(db, u.id, llm.Cfg(), [mail("Interview", "interview")])
    def boom(*a, **k): raise llm.LlmError("429: rate limited")
    monkeypatch.setattr(llm, "complete", boom)
    with pytest.raises(RuntimeError, match="keeps failing"):
        mc.process(db, u.id, llm.Cfg("groq", "openai/gpt-oss-20b", None, "k"), [mail("Interview", "interview invite", mid=f"m{i}") for i in range(8)])


def test_sync_is_refused_until_an_ai_model_is_chosen(client, make_user, db):
    from app.models import MailAccount
    h, _ = make_user(); u = db.scalar(select(User))
    db.add(MailAccount(user_id=u.id, provider="gmail", label="g", host="h", port=1, username="a@b.c", folder="INBOX", days_back=30)); db.commit()
    aid = client.get("/api/v1/mail/accounts", headers=h).json()[0]["id"]
    r = client.post("/api/v1/mail/sync", json={"account_id": aid}, headers=h); assert r.status_code == 400 and "AI model" in r.text
    assert client.get("/api/v1/ai/settings", headers=h).json()["provider"] is None
    for gone in ("import", "import-eml"): assert client.post(f"/api/v1/mail/{gone}", headers=h, json={}).status_code in (404, 405)       # manual import was removed


def _event(db, user, category, company="Acme", role="Backend Engineer", n=[0]):
    n[0] += 1; cid, jid = mc.link(db, user.id, {"company": company, "role": role})
    e = MailEvent(user_id=user.id, message_id=f"t{n[0]}-{category}", sender=f"{company} <hr@acme.com>", subject=f"{category} at {company}", category=category, company=company, role=role,
                  summary="s", confidence=0.9, classifier="test", company_id=cid, job_id=jid); db.add(e); db.commit(); return e


# ---------------------------------------------------------------- mailbox sync through the worker
# ---------------------------------------------------------------- review inbox
def _pipeline(db, user_email="user@example.com", stage="shortlisted"):
    u = db.scalar(select(User).where(User.email == user_email)); c = ing.add_company(db, "Acme")
    ing.store_jobs(db, c, [dict(title="Backend Engineer", location="Amsterdam, Netherlands", url="https://acme.nl/1", description="python", posted_at=None)]); db.commit()
    j = db.scalar(select(Job)); db.add(UserJob(user_id=u.id, job_id=j.id, stage=stage)); db.commit(); return j


def test_accept_moves_pipeline_and_never_downgrades(client, make_user, db):
    h, _ = make_user(); j = _pipeline(db); u = db.scalar(select(User))
    e1 = _event(db, u, "application_received")
    ev = client.get("/api/v1/mail/events", headers=h).json()["items"][0]
    assert ev["job_id"] == j.id and ev["suggested_stage"] == "applied" and ev["company_known"] == "Acme"
    assert client.post(f"/api/v1/mail/events/{e1.id}/accept", headers=h).json()["stage"] == "applied"
    assert db.scalar(select(UserJob.stage)) == "applied"
    e2 = _event(db, u, "interview_invite")
    client.post(f"/api/v1/mail/events/{e2.id}/accept", headers=h); db.expire_all(); assert db.scalar(select(UserJob.stage)) == "interview"
    e3 = _event(db, u, "application_received")
    client.post(f"/api/v1/mail/events/{e3.id}/accept", headers=h); db.expire_all(); assert db.scalar(select(UserJob.stage)) == "interview"      # not moved back to applied


def test_edit_dismiss_bulk_and_delete(client, make_user, db):
    h, _ = make_user(); u = db.scalar(select(User))
    for i, c in enumerate(["offer", "rejection", "recruiter_outreach"]): _event(db, u, c, company=f"Co{i}")
    items = client.get("/api/v1/mail/events", headers=h).json()["items"]; assert len(items) == 3
    e = items[0]
    assert client.patch(f"/api/v1/mail/events/{e['id']}", json={"category": "assessment", "company": "Fixed Co", "role": "QA"}, headers=h).status_code == 200
    assert client.patch(f"/api/v1/mail/events/{e['id']}", json={"category": "nope"}, headers=h).status_code == 400
    top = [x for x in client.get("/api/v1/mail/events", headers=h).json()["items"] if x["id"] == e["id"]][0]
    assert (top["category"], top["company"], top["role"]) == ("assessment", "Fixed Co", "QA")
    assert client.post(f"/api/v1/mail/events/{items[1]['id']}/dismiss", headers=h).status_code == 200
    assert client.post("/api/v1/mail/events/bulk", json={"ids": [items[2]["id"]], "action": "accept"}, headers=h).json()["changed"] == 1
    c = client.get("/api/v1/mail/events", headers=h).json()["counts"]["status"]; assert c == {"new": 1, "dismissed": 1, "accepted": 1}
    assert len(client.get("/api/v1/mail/events", headers=h, params={"status": "accepted"}).json()["items"]) == 1
    assert client.delete("/api/v1/mail/events", headers=h).status_code == 204
    assert client.get("/api/v1/mail/events", headers=h).json()["items"] == []


def test_mail_endpoints_require_sign_in(client):
    for path in ("/api/v1/mail/events", "/api/v1/mail/accounts", "/api/v1/ai/settings"): assert client.get(path).status_code == 401


# ---------------------------------------------------------------- Gmail OAuth
def test_gmail_oauth_flow(client, make_user, db, monkeypatch):
    from app.services import gmail_service as gm
    h, _ = make_user()
    monkeypatch.setattr(settings, "google_client_id", "cid.apps.googleusercontent.com"); monkeypatch.setattr(settings, "google_client_secret", None)
    st = client.get("/api/v1/mail/gmail/status", headers=h).json()
    assert st["configured"] is False and st["redirect_uri"].endswith("/api/v1/mail/gmail/callback")
    assert client.post("/api/v1/mail/gmail/start", headers=h).status_code == 400                      # not configured
    monkeypatch.setattr(settings, "google_client_secret", "shh")
    url = client.post("/api/v1/mail/gmail/start", headers=h).json()["url"]
    assert url.startswith("https://accounts.google.com/") and "gmail.readonly" in url and "access_type=offline" in url
    state = url.split("state=")[1].split("&")[0]
    monkeypatch.setattr(gm, "exchange", lambda code: {"refresh_token": "r-token", "access_token": "a", "email": "me@gmail.com"})
    r = client.get("/api/v1/mail/gmail/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert r.status_code in (302, 307) and "gmail=connected" in r.headers["location"]
    assert "r-token" not in (db.scalar(text("select secret_enc from mail_accounts")) or "")          # stored encrypted
    acc = client.get("/api/v1/mail/accounts", headers=h).json()
    assert len(acc) == 1 and acc[0]["provider"] == "gmail" and acc[0]["username"] == "me@gmail.com" and "r-token" not in str(acc)
    # reconnecting the same address updates instead of duplicating
    client.get("/api/v1/mail/gmail/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert len(client.get("/api/v1/mail/accounts", headers=h).json()) == 1
    # a forged state is refused
    bad = client.get("/api/v1/mail/gmail/callback", params={"code": "c", "state": "nope"}, follow_redirects=False)
    assert "gmail=error" in bad.headers["location"] and len(client.get("/api/v1/mail/accounts", headers=h).json()) == 1
    assert "gmail=denied" in client.get("/api/v1/mail/gmail/callback", params={"error": "access_denied"}, follow_redirects=False).headers["location"]
    # sync uses the Gmail API reader, not IMAP
    monkeypatch.setattr(gm, "fetch", lambda token, days=60, limit=400: [mail("Interview", "We would like to invite you to an interview.", mid="g1")] if token == "r-token" else [])
    client.put("/api/v1/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"}, headers=h)
    monkeypatch.setattr(llm, "complete", _reply(category="interview_invite", company="Acme"))
    tid = client.post("/api/v1/mail/sync", json={"account_id": acc[0]["id"]}, headers=h).json()["task_id"]
    import time
    for _ in range(100):                                               # the sync runs in a background thread of the API
        st = client.get(f"/api/v1/mail/sync/{tid}", headers=h).json()
        if st["status"] != "running": break
        time.sleep(0.1)
    assert st["status"] == "done" and st["progress"]["found"] == 1
    assert client.get("/api/v1/mail/accounts", headers=h).json()[0]["last_sync_at"]
    h2, _ = make_user("other@example.com")
    assert client.get(f"/api/v1/mail/sync/{tid}", headers=h2).status_code == 404                  # someone else's task
    assert client.post(f"/api/v1/mail/accounts/{acc[0]['id']}/test", headers=h2).status_code == 404
    assert client.get("/api/v1/mail/events", headers=h2).json()["items"] == []


def test_auto_apply_high_confidence_and_undo(client, make_user, db, monkeypatch):
    from sqlalchemy import select
    from app.models import Job, MailEvent, UserJob
    from app.services import ingest_service as ing, mail_classifier as mc, llm_service as llm
    h, reg = make_user(); import uuid; uid = uuid.UUID(client.get("/api/v1/auth/me", headers=h).json()["id"]); c = ing.add_company(db, "Acme"); ing.store_jobs(db, c, [dict(title="Backend Engineer", location="Amsterdam", url="https://a.nl/1", description="x", posted_at=None)]); db.commit()
    j = db.scalar(select(Job)); db.add(UserJob(user_id=uid, job_id=j.id, stage="applied")); db.commit()
    res = lambda conf: dict(category="interview_invite", company="Acme", role="Backend Engineer", location=None, event_date=None, summary="Interview", confidence=conf, classifier="t")
    monkeypatch.setattr(mc, "classify", lambda cfg, mail: res(0.95 if mail["message_id"] == "a" else 0.5))
    mail = lambda i: dict(message_id=i, subject="Interview for Backend Engineer at Acme", body="interview position", sender="HR <hr@acme.nl>", sender_addr="hr@acme.nl", date=None)
    cfg = llm.Cfg("ollama", "m", None, None)
    st = mc.process(db, uid, cfg, [mail("a"), mail("b")], auto_apply=0.9)
    assert st["auto_applied"] == 1 and db.get(UserJob, (uid, j.id)).stage == "interview"
    evs = {e.message_id: e for e in db.scalars(select(MailEvent))}; assert evs["a"].status == "auto" and evs["b"].status == "new"
    r = client.post(f"/api/v1/mail/events/{evs['a'].id}/undo", headers=h); assert r.status_code == 200 and r.json()["stage"] == "applied"
    db.expire_all(); assert db.get(UserJob, (uid, j.id)).stage == "applied"
    assert client.post(f"/api/v1/mail/events/{evs['b'].id}/undo", headers=h).status_code == 400
    assert client.get("/api/v1/mail/sync-history", headers=h).status_code == 200
