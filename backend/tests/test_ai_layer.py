"""AI layer: error kinds, JSON-mode fallback, per-task models, writing style."""
import json, httpx, pytest
from app.services import llm_service as llm, ai_cfg

CFG = llm.Cfg("groq", "openai/gpt-oss-20b", None, "k")
OPENAI = llm.Cfg("openai", "gpt-4o-mini", None, "k")


REAL = httpx.Client


def _http(handler):
    real = REAL
    return lambda *a, **k: real(*a, transport=httpx.MockTransport(handler), **{x: y for x, y in k.items() if x != "transport"})


def _ok(content): return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_status_codes_become_config_or_transient(monkeypatch):
    for status, cls in ((401, llm.LlmConfigError), (404, llm.LlmConfigError), (400, llm.LlmConfigError), (500, llm.LlmTransientError), (503, llm.LlmTransientError)):
        monkeypatch.setattr(llm.httpx, "Client", _http(lambda r, s=status: httpx.Response(s, text="nope")))
        with pytest.raises(cls): llm.complete(OPENAI, "s", "u")
    monkeypatch.setattr(llm.httpx, "Client", _http(lambda r: _ok("")))
    with pytest.raises(llm.LlmTransientError): llm.complete(OPENAI, "s", "u")                     # an empty answer is a hiccup, not a settings problem
    with pytest.raises(llm.LlmConfigError): llm.complete(llm.Cfg(), "s", "u")


def test_json_mode_falls_back_and_is_remembered(monkeypatch):
    seen = []
    def handler(req):
        body = json.loads(req.content); seen.append("response_format" in body)
        return httpx.Response(400, text="response_format is not supported by this model") if "response_format" in body else _ok('{"a": 1}')
    llm._NO_JSON_MODE.clear(); monkeypatch.setattr(llm.httpx, "Client", _http(handler))
    assert llm.complete_json(OPENAI, "s", "u") == {"a": 1} and seen == [True, False]
    seen.clear(); assert llm.complete_json(OPENAI, "s", "u") == {"a": 1} and seen == [False]       # learned: no JSON mode for this model


def test_malformed_json_is_retried_once(monkeypatch):
    answers = iter(["here you go: not json", '{"ok": true}'])
    monkeypatch.setattr(llm.httpx, "Client", _http(lambda r: _ok(next(answers))))
    assert llm.complete_json(OPENAI, "s", "u") == {"ok": True}
    monkeypatch.setattr(llm.httpx, "Client", _http(lambda r: _ok("never json")))
    with pytest.raises(llm.LlmTransientError): llm.complete_json(OPENAI, "s", "u")


def test_per_task_model_and_style_block():
    c = llm.Cfg("groq", "default-model", None, "k", {"scoring": "small-model"}, {"tone": "confident", "avoid": ["synergy"], "instructions": "Mention Bologna."})
    assert c.for_task("scoring").model == "small-model" and c.for_task("tailoring").model == "default-model" and c.for_task("scoring").api_key == "k"
    b = ai_cfg.style_block(c.style); assert "confident" in b and "synergy" in b and "Mention Bologna" in b and ai_cfg.style_block({}) == ""


def test_settings_api_roundtrip_and_resolved(client, make_user):
    h, _ = make_user()
    r = client.put("/api/v1/ai/settings", headers=h, json={"provider": "groq", "model": "openai/gpt-oss-20b", "api_key": "k", "task_models": {"scoring": "openai/gpt-oss-120b", "bogus": "x"},
                                                           "style": {"tone": "friendly", "formality": "nope", "avoid": ["synergy", " "], "instructions": "Be brief"}}).json()
    assert r["task_models"] == {"scoring": "openai/gpt-oss-120b"} and r["resolved"]["scoring"] == "openai/gpt-oss-120b" and r["resolved"]["tailoring"] == "openai/gpt-oss-20b"
    assert r["style"] == {"tone": "friendly", "avoid": ["synergy"], "instructions": "Be brief"} and "friendly" in r["tones"]
    r = client.put("/api/v1/ai/settings", headers=h, json={"provider": "groq", "task_models": {}}).json(); assert r["task_models"] == {} and r["has_key"] is True


def test_config_errors_are_400_and_transient_503(client, make_user, monkeypatch):
    h, _ = make_user(); client.put("/api/v1/ai/settings", headers=h, json={"provider": "ollama", "model": "q"})
    monkeypatch.setattr(llm.httpx, "Client", _http(lambda r: httpx.Response(401, text="bad key")))
    assert client.post("/api/v1/ai/test", headers=h).status_code == 400
    monkeypatch.setattr(llm.httpx, "Client", _http(lambda r: httpx.Response(503, text="overloaded")))
    assert client.post("/api/v1/ai/test", headers=h).status_code == 503
