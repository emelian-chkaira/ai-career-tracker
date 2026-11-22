"""One small client for many AI providers, so users can pick what they trust and what they can afford.

  anthropic    Claude with the user's own API key
  openai-compatible: Ollama (local, free), GLM/Zhipu, Qwen/DashScope, DeepSeek, Moonshot/Kimi, xAI Grok, Groq, OpenRouter (incl. free models), OpenAI, or any custom endpoint

Presets are editable defaults, not promises: model names, prices and free tiers change, so every field can be overridden in the UI."""
import json, re, time
from dataclasses import dataclass
import httpx

PROVIDERS: dict[str, dict] = {
    "ollama": dict(label="Ollama — run a model on your own computer", kind="openai", needs_key=False, base_url="http://localhost:11434/v1", tier="free",
                   models=["qwen2.5:7b", "qwen2.5:14b", "deepseek-r1:8b", "llama3.1:8b", "mistral:7b"],
                   note="Free and private. Install Ollama, run `ollama pull qwen2.5:7b`. Works only when the server can reach your machine."),
    "zhipu": dict(label="GLM (Zhipu AI, China)", kind="openai", needs_key=True, base_url="https://open.bigmodel.cn/api/paas/v4", tier="free tier",
                  models=["glm-4-flash", "glm-4-air", "glm-4-plus"], note="glm-4-flash has had a free tier; check Zhipu's current terms."),
    "qwen": dict(label="Qwen (Alibaba Cloud DashScope, China)", kind="openai", needs_key=True, base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1", tier="free quota",
                 models=["qwen-turbo", "qwen-plus", "qwen-max", "qwen2.5-72b-instruct"], note="New accounts usually get a free token quota; check Alibaba's current terms."),
    "deepseek": dict(label="DeepSeek (China)", kind="openai", needs_key=True, base_url="https://api.deepseek.com/v1", tier="very cheap",
                     models=["deepseek-chat"], note="Pay-as-you-go, very low prices."),
    "moonshot": dict(label="Kimi (Moonshot AI, China)", kind="openai", needs_key=True, base_url="https://api.moonshot.ai/v1", tier="paid",
                     models=["moonshot-v1-8k", "moonshot-v1-32k", "kimi-k2-0905-preview"], note="Pay-as-you-go."),
    "xai": dict(label="Grok (xAI)", kind="openai", needs_key=True, base_url="https://api.x.ai/v1", tier="paid",
                models=["grok-4", "grok-3", "grok-3-mini"], note="Pay-as-you-go with your key from console.x.ai. The model list changes: type any current model name."),
    "groq": dict(label="Groq (fast, free tier)", kind="openai", needs_key=True, base_url="https://api.groq.com/openai/v1", tier="free tier",
                 models=["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
                 note="Free key from console.groq.com/keys, with rate limits (requests and tokens per minute/day). Not the same company as xAI's Grok. Which models a key can use varies by account and changes: if you get \"model not found\", pick another or check console.groq.com/docs/models."),
    "openrouter": dict(label="OpenRouter (one key, many models, some free)", kind="openai", needs_key=True, base_url="https://openrouter.ai/api/v1", tier="free models available",
                       models=["deepseek/deepseek-chat-v3-0324:free", "qwen/qwen-2.5-72b-instruct:free", "meta-llama/llama-3.3-70b-instruct:free", "anthropic/claude-haiku-4.5"],
                       note="Models ending in :free cost nothing but are rate-limited, and the list changes often."),
    "anthropic": dict(label="Claude (Anthropic) — your own API key", kind="anthropic", needs_key=True, base_url="https://api.anthropic.com", tier="paid",
                      models=["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2"],
                      note="Haiku is fastest and cheapest and is enough for classifying e-mails. Sonnet writes better replies."),
    "openai": dict(label="OpenAI — your own API key", kind="openai", needs_key=True, base_url="https://api.openai.com/v1", tier="paid", models=["gpt-4o-mini", "gpt-4o"], note="Pay-as-you-go."),
    "custom": dict(label="Custom (any OpenAI-compatible endpoint)", kind="openai", needs_key=False, base_url="", tier="varies", models=[],
                   note="vLLM, LM Studio, LiteLLM, a company gateway… Enter the base URL ending in /v1, a model name and (if needed) a key."),
}


class LlmError(Exception):
    """Something went wrong talking to the model. `kind` tells the caller what to do about it."""
    kind = "error"


class LlmConfigError(LlmError):
    """The user's settings are the problem (no key, wrong key, unknown model, bad URL). Retrying will not help: fix the settings."""
    kind = "config"


class LlmTransientError(LlmError):
    """The provider had a hiccup (rate limit, overload, timeout, an unusable answer). Trying again later is the right move; the settings are fine."""
    kind = "transient"


def classify_status(status: int, msg: str) -> LlmError:
    if status in (401, 403): return LlmConfigError(f"{status}: the provider rejected the API key: {msg}")
    if status == 404: return LlmConfigError(f"{status}: {msg} (this key cannot use that model: choose another model from the list or type one your provider offers)")
    if status in (400, 422): return LlmConfigError(f"{status}: {msg}")
    return LlmTransientError(f"{status}: {msg}")


# Which models refuse `response_format` (learned at run time, so one failed call teaches all later ones in this process).
_NO_JSON_MODE: set[str] = set()


@dataclass
class Cfg:
    provider: str = ""                  # empty = no AI chosen yet
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None

    task_models: dict | None = None
    style: dict | None = None

    def for_task(self, task: str) -> "Cfg":
        """The same provider and key, with the model chosen for this task (scoring, tailoring, inbox, assistant) when there is one."""
        m = (self.task_models or {}).get(task)
        return Cfg(self.provider, m or self.model, self.base_url, self.api_key, self.task_models, self.style) if m else self

    @property
    def configured(self) -> bool: return self.provider in PROVIDERS
    @property
    def kind(self) -> str: return PROVIDERS[self.provider]["kind"] if self.configured else "none"
    @property
    def external(self) -> bool: return self.configured and self.provider != "ollama" and not (self.base_url or "").startswith(("http://localhost", "http://127.0.0.1"))
    @property
    def label(self) -> str: return f"{self.provider}:{self.model}" if self.configured else "none"


def _clean(text: str, key: str | None) -> str:
    t = re.sub(r"\s+", " ", text or "")[:240]
    return t.replace(key, "***") if key else t


def _post(c: httpx.Client, url: str, **kw) -> httpx.Response:
    """POST, waiting and retrying a few times when the provider says "too many requests" (free tiers have per-minute limits)."""
    for attempt in range(4):
        r = c.post(url, **kw)
        if r.status_code != 429 or attempt == 3: return r
        try: wait = float(r.headers.get("retry-after", 0))
        except ValueError: wait = 0
        time.sleep(min(max(wait, 3 * (attempt + 1)), 25))
    return r


def complete(cfg: Cfg, system: str, user: str, max_tokens: int = 700, timeout: float = 60, json_mode: bool = False) -> str:
    """Send one prompt, return the model's text. Raises LlmConfigError / LlmTransientError (both LlmError) with a short, key-free message.
    json_mode asks the provider for a JSON object; models that do not support it are remembered and asked without."""
    if not cfg.configured: raise LlmConfigError("no AI model chosen yet")
    p = PROVIDERS[cfg.provider]; base = (cfg.base_url or p["base_url"] or "").rstrip("/"); model = cfg.model or (p["models"][0] if p["models"] else "")
    if not base or not model: raise LlmConfigError("base URL and model are required")
    if p["needs_key"] and not cfg.api_key: raise LlmConfigError("an API key is required for this provider")
    try:
        with httpx.Client(timeout=timeout) as c:
            if cfg.kind == "anthropic":
                r = _post(c, f"{base}/v1/messages", headers={"x-api-key": cfg.api_key or "", "anthropic-version": "2023-06-01"},
                           json={"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]})
                if r.status_code >= 400: raise classify_status(r.status_code, _clean(r.text, cfg.api_key))
                out = "".join(b.get("text", "") for b in r.json().get("content", []))
            else:
                h = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
                body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
                if model.startswith("openai/gpt-oss"):                       # reasoning models (Groq): hidden thinking uses the same token budget as the answer
                    body.pop("max_tokens"); body.update(max_completion_tokens=max(max_tokens, 1500), reasoning_effort="low")
                want_json = json_mode and f"{cfg.provider}:{model}" not in _NO_JSON_MODE
                if want_json: body["response_format"] = {"type": "json_object"}
                r = _post(c, f"{base}/chat/completions", headers=h, json=body)
                if r.status_code == 400 and want_json and re.search(r"response_format|json_object|json mode|structured", r.text, re.I):        # capability ladder: JSON mode -> plain text
                    _NO_JSON_MODE.add(f"{cfg.provider}:{model}"); body.pop("response_format", None); r = _post(c, f"{base}/chat/completions", headers=h, json=body)
                if r.status_code >= 400: raise classify_status(r.status_code, _clean(r.text, cfg.api_key))
                data = r.json()
                try: out = (data["choices"][0].get("message") or {}).get("content") or ""     # reasoning models may omit `content`
                except (KeyError, IndexError, TypeError, AttributeError): raise LlmTransientError("unexpected response: " + _clean(r.text, cfg.api_key)[:200])
                if not out.strip(): raise LlmTransientError("the model returned no text (a reasoning model may have used up its token budget): try again or choose another model")
    except LlmError: raise
    except httpx.HTTPError as e: raise LlmTransientError(_clean(str(e), cfg.api_key))
    except ValueError: raise LlmTransientError("the provider did not return JSON")
    return re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()           # reasoning models (DeepSeek-R1, Qwen3) prepend their thoughts


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m: raise LlmTransientError("the model did not return JSON")
    try: d = json.loads(m.group(0))
    except ValueError: raise LlmTransientError("the model returned invalid JSON")
    if not isinstance(d, dict): raise LlmTransientError("the model returned invalid JSON")
    return d


def complete_json(cfg: Cfg, system: str, user: str, max_tokens: int = 700, timeout: float = 60, tries: int = 2) -> dict:
    """Ask for a JSON object, parse it, and on a malformed answer ask once more with a firmer reminder. Raises LlmError."""
    last: LlmError | None = None
    for i in range(max(1, tries)):
        try: return parse_json(complete(cfg, system, user if i == 0 else user + "\n\nReturn ONLY one valid JSON object, no prose, no code fences.", max_tokens=max_tokens, timeout=timeout, json_mode=True))
        except LlmTransientError as e: last = e
    raise last or LlmTransientError("the model did not return JSON")


def test(cfg: Cfg) -> dict:
    """Cheap round trip used by the 'Test' button."""
    if not cfg.configured: raise LlmError("no AI model chosen yet")
    out = complete(cfg, "Reply with exactly: ok", "ping", max_tokens=10, timeout=30)
    return {"ok": True, "detail": f"{cfg.label} answered: {out[:40]}"}
