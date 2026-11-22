import { useAuth } from "@/features/auth/AuthContext";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";

export type Provider = { id: string; label: string; kind: string; needs_key: boolean; base_url: string | null; models: string[]; tier: string; note: string };
export type AiStyle = { tone?: string; formality?: string; language?: string; avoid?: string[]; instructions?: string };
export type AiSettings = { provider: string | null; model: string | null; base_url: string | null; has_key: boolean; task_models?: Record<string, string>; style?: AiStyle; tasks?: string[]; tones?: string[]; resolved?: Record<string, string> };
const TASK_HELP: Record<string, string> = { scoring: "Job fit scores", tailoring: "CV and cover letter", inbox: "Reading your e-mail", assistant: "The per-job assistant" };
export const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
export const useAiSettings = () => { const { user } = useAuth(); return useQuery({ queryKey: ["ai-settings"], enabled: !!user, queryFn: () => api.get<AiSettings>("/ai/settings") }); };
/** True when the chosen model runs on someone else's server, so the user must agree before text is sent. */
export const isExternalAi = (a?: AiSettings | null) => !!a?.provider && a.provider !== "ollama";

export function AiPanel({ onSaved }: { onSaved: () => void }) {
  const qc = useQueryClient();
  const provs = useQuery({ queryKey: ["ai-providers"], queryFn: () => api.get<Provider[]>("/ai/providers"), staleTime: Infinity });
  const cur = useQuery({ queryKey: ["ai-settings"], queryFn: () => api.get<AiSettings>("/ai/settings") });
  const [f, setF] = useState({ provider: "", model: "", base_url: "", api_key: "" });
  const [msg, setMsg] = useState(""); const [busy, setBusy] = useState(false);
  const [tm, setTm] = useState<Record<string, string>>({}); const [style, setStyle] = useState<AiStyle>({}); const [avoid, setAvoid] = useState("");
  useEffect(() => { if (cur.data?.provider) setF({ provider: cur.data.provider, model: cur.data.model ?? "", base_url: cur.data.base_url ?? "", api_key: "" }); setTm(cur.data?.task_models ?? {}); setStyle(cur.data?.style ?? {}); setAvoid((cur.data?.style?.avoid ?? []).join(", ")); }, [cur.data]);
  const p = provs.data?.find((x) => x.id === f.provider);
  const pick = (id: string) => { const q = provs.data?.find((x) => x.id === id); setF({ provider: id, model: q?.models[0] ?? "", base_url: "", api_key: "" }); setMsg(""); };
  const save = async (test = false) => {
    setBusy(true); setMsg("");
    try {
      await api.put("/ai/settings", { provider: f.provider, model: f.model || null, base_url: f.base_url || null, ...(f.api_key ? { api_key: f.api_key } : {}), task_models: tm, style: { ...style, avoid: avoid.split(",").map((x) => x.trim()).filter(Boolean) } });
      await qc.invalidateQueries({ queryKey: ["ai-settings"] });
      if (test) { const r = await api.post<{ detail: string }>("/ai/test"); setMsg("✓ " + r.detail); } else { setMsg("Saved."); onSaved(); }
    } catch (e) { setMsg("✗ " + errText(e)); } finally { setBusy(false); }
  };
  const groups: [string, string[]][] = [["Free and private (runs on your computer)", ["ollama"]], ["Chinese models (free tiers or very cheap)", ["zhipu", "qwen", "deepseek", "moonshot"]], ["Free tiers and many models", ["groq", "openrouter"]], ["Bring your own paid key", ["anthropic", "openai", "xai"]], ["Your own endpoint", ["custom"]]];
  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Which AI model should do the reading?</h2>
      <div className="small muted">One choice for the Inbox, the job fit scores and CV tailoring.</div>
      <div className="field"><label htmlFor="prov">Provider</label>
        <select id="prov" value={f.provider} onChange={(e) => pick(e.target.value)}>
          <option value="" disabled>Choose a provider…</option>
          {groups.map(([g, ids]) => <optgroup key={g} label={g}>{ids.map((id) => { const q = provs.data?.find((x) => x.id === id); return q ? <option key={id} value={id}>{q.label}</option> : null; })}</optgroup>)}
        </select></div>
      {p && <div className="small muted">{p.note} {p.tier !== "free" && <span className="chip plain">{p.tier}</span>}</div>}
      {p && <>
        <div className="field"><label htmlFor="model">Model <span className="muted small">(pick one or type any model name)</span></label>
          <input id="model" type="text" list="models" value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })} placeholder="model name" />
          <datalist id="models">{p.models.map((m) => <option key={m} value={m} />)}</datalist></div>
        {(f.provider === "custom" || f.provider === "ollama" || f.base_url) && <div className="field"><label htmlFor="url">Base URL</label>
          <input id="url" type="text" value={f.base_url} onChange={(e) => setF({ ...f, base_url: e.target.value })} placeholder={p.base_url || "https://your-server/v1"} /></div>}
        {(p.needs_key || f.provider === "custom") && <div className="field"><label htmlFor="key">API key {cur.data?.has_key && cur.data.provider === f.provider && <span className="chip ok">saved</span>}</label>
          <input id="key" type="password" value={f.api_key} onChange={(e) => setF({ ...f, api_key: e.target.value })} autoComplete="off" placeholder={cur.data?.has_key && cur.data.provider === f.provider ? "leave empty to keep the saved key" : "paste your key"} />
          <div className="small muted">Stored encrypted on the server, never shown again. Remove it any time by saving an empty key.</div></div>}
        {f.provider !== "ollama" && <div className="small muted">⚠ The text you ask it to analyse (e-mails, your CV, job postings) is sent to this provider, so the provider's privacy terms apply. Choose a local Ollama model to keep everything on your machine.</div>}
      </>}
      {p && <details className="adv"><summary>Advanced: a model per task and your writing style</summary>
        <div className="stack" style={{ marginTop: 10 }}>
          <div className="small muted">Use a cheap, fast model for reading e-mail and a stronger one for tailoring. Leave a task empty to use the model above.</div>
          <div className="adv-grid">{(cur.data?.tasks ?? ["scoring", "tailoring", "inbox", "assistant"]).map((t) => <label key={t} className="field"><span className="small">{TASK_HELP[t] ?? t}</span>
            <input type="text" list="models" value={tm[t] ?? ""} placeholder={f.model || "default model"} onChange={(e) => setTm({ ...tm, [t]: e.target.value })} /></label>)}</div>
          <div className="small"><b>Writing style</b> <span className="muted">(letters and the assistant; never changes what facts may be used)</span></div>
          <div className="adv-grid">
            <label className="field"><span className="small">Tone</span><select value={style.tone ?? ""} onChange={(e) => setStyle({ ...style, tone: e.target.value })}><option value="">Default</option>{(cur.data?.tones ?? []).map((t) => <option key={t} value={t}>{t}</option>)}</select></label>
            <label className="field"><span className="small">Formality</span><select value={style.formality ?? ""} onChange={(e) => setStyle({ ...style, formality: e.target.value })}><option value="">Default</option><option value="formal">Formal</option><option value="neutral">Neutral</option><option value="informal">Informal</option></select></label>
            <label className="field"><span className="small">Write in (language)</span><input type="text" value={style.language ?? ""} placeholder="e.g. English, Dutch" onChange={(e) => setStyle({ ...style, language: e.target.value })} /></label>
            <label className="field"><span className="small">Words to avoid (comma separated)</span><input type="text" value={avoid} placeholder="synergy, passionate" onChange={(e) => setAvoid(e.target.value)} /></label></div>
          <label className="field"><span className="small">Extra instructions</span><textarea rows={2} value={style.instructions ?? ""} placeholder="e.g. Keep letters under 180 words" onChange={(e) => setStyle({ ...style, instructions: e.target.value })} /></label>
          {cur.data?.resolved && <table className="resolved"><tbody>{Object.entries(cur.data.resolved).map(([k, v]) => <tr key={k}><td>{TASK_HELP[k] ?? k}</td><td><code>{v}</code>{(cur.data?.task_models ?? {})[k] ? "" : <span className="muted"> (default)</span>}</td></tr>)}</tbody></table>}
        </div></details>}
      <div className="row" style={{ gap: 8 }}>
        <button className="btn" disabled={busy || !p} onClick={() => save(true)}>Save and test</button>
        <button className="btn ghost" disabled={busy || !p} onClick={() => save(false)}>Save only</button>
      </div>
      {msg && <div className={`small ${msg.startsWith("✗") ? "err" : "ok"}`}>{msg}</div>}
    </div>
  );
}

