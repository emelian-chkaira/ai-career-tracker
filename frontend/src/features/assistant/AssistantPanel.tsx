import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { isExternalAi, useAiSettings } from "@/features/ai/AiPanel";
import { getConsent, setConsentStored } from "@/features/fit/api";

type Msg = { id: number; role: "user" | "assistant"; content: string; model?: string | null; at: string };
const QUICK = ["Draft a short cover letter for this role", "Which interview questions should I prepare?", "Why this company? Give me talking points", "What should I ask about salary and visa?"];

/** Chat about ONE job. The model sees the posting, your saved CV, your notes and the e-mails linked to the job. */
export function AssistantPanel({ jobId, embedded = false }: { jobId: number; embedded?: boolean }) {
  const { user } = useAuth(); const qc = useQueryClient(); const ai = useAiSettings();
  const chat = useQuery({ queryKey: ["assistant", jobId], enabled: !!user, queryFn: () => api.get<{ messages: Msg[] }>(`/me/assistant/${jobId}`) });
  const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [consent, setConsent] = useState(getConsent()); const [open, setOpen] = useState(embedded);
  if (!user) return null;
  const msgs = chat.data?.messages ?? []; const external = isExternalAi(ai.data); const ready = !!ai.data?.provider && (!external || consent);
  const send = async (m: string) => {
    if (!m.trim() || busy) return; setBusy(true); setErr("");
    try { await api.post(`/me/assistant/${jobId}`, { message: m, consent }); setText(""); await qc.invalidateQueries({ queryKey: ["assistant", jobId] }); }
    catch (e) { setErr(e instanceof ApiError ? e.message : (e as Error).message); } finally { setBusy(false); }
  };
  const clear = async () => { await api.del(`/me/assistant/${jobId}`); await qc.invalidateQueries({ queryKey: ["assistant", jobId] }); };
  return (<div className="assist stack">{!embedded && <button className="btn ghost small" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Hide" : "Ask the assistant about this job"}{!open && !!msgs.length && ` (${msgs.length})`}</button>}
    {open && <>
      {ai.data && !ai.data.provider && <div className="small">First <Link to="/profile">choose an AI model</Link>.</div>}
      {external && <label className="small"><input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); setConsentStored(e.target.checked); }} /> I agree that my question, this posting and my CV are sent to <b>{ai.data?.provider}</b>.</label>}
      <div className="chatlog" aria-live="polite">{msgs.map((m) => <div key={m.id} className={`bubble ${m.role}`}>{m.content}{m.role === "assistant" && <button className="btn ghost small" onClick={() => navigator.clipboard.writeText(m.content)}>Copy</button>}</div>)}
        {busy && <div className="bubble assistant muted">Thinking…</div>}</div>
      {!msgs.length && <div className="row wrap">{QUICK.map((q) => <button key={q} className="chip" disabled={!ready || busy} onClick={() => send(q)}>{q}</button>)}</div>}
      <form className="row" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask anything about this job…" maxLength={4000} aria-label="Message" style={{ flex: 1 }} />
        <button className="btn" disabled={!ready || busy || !text.trim()}>Send</button>{!!msgs.length && <button type="button" className="btn ghost small" onClick={clear}>Clear</button>}</form>
      {err && <div className="small err">{err}</div>}
    </>}
  </div>);
}
