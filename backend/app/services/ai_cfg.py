"""The signed-in user's AI settings (one provider/model/key for the Inbox, fit scoring and CV tailoring)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.secretbox import unseal
from app.models import User, UserAiSettings
from . import llm_service as llm


TASKS = ("scoring", "tailoring", "inbox", "assistant")


def cfg_of(db: Session, user: User, task: str | None = None) -> llm.Cfg:
    """The user's model. With `task`, the model chosen for that task (falling back to the default model)."""
    s = db.get(UserAiSettings, user.id)
    cfg = llm.Cfg(s.provider, s.model, s.base_url, unseal(s.api_key_enc), dict(s.task_models or {}), dict(s.style or {})) if s and s.provider in llm.PROVIDERS else llm.Cfg()      # old "rules" setting = not chosen
    return cfg.for_task(task) if task else cfg


STYLE_TONES = ("professional", "friendly", "confident", "concise", "casual")


def style_block(style: dict | None) -> str:
    """The user's writing preferences as extra instructions for writing tasks (letters, assistant). Never used for fact-bound tasks like scoring."""
    st = style or {}; lines = []
    if st.get("tone") in STYLE_TONES: lines.append(f"Tone: {st['tone']}.")
    if st.get("formality") in ("formal", "neutral", "informal"): lines.append(f"Formality: {st['formality']}.")
    if st.get("language"): lines.append(f"Write in {str(st['language'])[:40]} (the posting's language does not matter).")
    avoid = [str(x)[:30] for x in (st.get("avoid") or [])[:20] if str(x).strip()]
    if avoid: lines.append("Never use these words or phrases: " + ", ".join(avoid) + ".")
    if st.get("instructions"): lines.append("Extra instructions from the candidate (they never override the rule to use only facts from the CV): " + str(st["instructions"])[:600])
    return ("\n\nWriting preferences:\n" + "\n".join(lines)) if lines else ""


def require(db: Session, user: User, consent: bool, what: str, task: str | None = None) -> llm.Cfg:
    """The user's AI config, or a clear 400: no model chosen, or text would leave the server without consent."""
    cfg = cfg_of(db, user, task)
    if not cfg.configured: raise HTTPException(400, "Choose an AI model first (Profile, AI model, or the Inbox).")
    if cfg.external and not consent:
        raise HTTPException(400, f"{what} is sent to {llm.PROVIDERS[cfg.provider]['label']} to be analysed. Confirm with consent=true, or choose a local Ollama model.")
    return cfg


def http_error(e: llm.LlmError, what: str) -> HTTPException:
    """Map a model failure to an honest HTTP answer: settings problems are 400 (fix them), hiccups are 503 (try again), anything else 502."""
    if e.kind == "config": return HTTPException(400, f"{what}: check your AI settings. {e}")
    if e.kind == "transient": return HTTPException(503, f"{what}: the AI provider had a hiccup, try again in a moment. {e}")
    return HTTPException(502, f"{what}: {e}")
