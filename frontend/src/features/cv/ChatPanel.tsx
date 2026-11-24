import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "@/shared/api/client";
import { isExternalAi, useAiSettings } from "@/features/ai/AiPanel";
import { getConsent, setConsentStored } from "@/features/fit/api";

interface Change { section: string; title: string; before: string; after: string }
interface Suggestion { id: string; target: "cv" | "cover"; label: string; prompt: string; needs_detail?: boolean }
interface Turn { role: "user" | "assistant"; content: string; changes?: Change[]; cv?: Record<string, unknown> | null; letter?: string | null; undo?: Record<string, unknown> | string; copy?: string; state?: "applied" | "discarded" }
type Target = "cv" | "cover";

/** Ask the AI to change your CV or cover letter. It returns a reviewed copy; nothing changes until you press Apply, and Apply can be undone.
 * When you come from a job, it also suggests what to change for that posting. */
export function ChatPanel({ target, docName, cv, letter, jobId, folders, applyCv, applyLetter, copyCv, copyLetter }: {
  target: Target; docName: string; cv: Record<string, unknown>; letter: string; jobId: string; folders: string[];
  applyCv(next: Record<string, unknown>): void; applyLetter(text: string): void; copyCv(next: Record<string, unknown>, folder: string): void; copyLetter(text: string, folder: string): void;
}) {
  const ai = useAiSettings(); const [mode, setMode] = useState<"inplace" | "copy">("inplace"); const [folder, setFolder] = useState(""); const [turns, setTurns] = useState<Turn[]>([]); const [text, setText] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [consent, setConsent] = useState(getConsent()); const end = useRef<HTMLDivElement>(null);
  const [sugg, setSugg] = useState<{ job: { title: string; company: string }; suggestions: Suggestion[] } | null>(null);
  const external = isExternalAi(ai.data); const ready = !!ai.data?.provider && (!external || consent); const jid = jobId && /^\d+$/.test(jobId) ? +jobId : null;
  useEffect(() => { end.current?.scrollIntoView?.({ block: "end" }); }, [turns, busy]);
  const cvKey = JSON.stringify(cv).length;
  useEffect(() => {          // suggestions for the job you came from (deterministic: no AI call, so they appear at once)
    if (!jid) { setSugg(null); return; }
    let stale = false; api.post<typeof sugg>(`/me/cv-chat/suggest/${jid}`, { cv }).then((r) => { if (!stale) setSugg(r); }).catch(() => { if (!stale) setSugg(null); });
    return () => { stale = true; };
  }, [jid, Math.floor(cvKey / 400)]);   // eslint-disable-line react-hooks/exhaustive-deps

  const send = async (m: string, t: Target = target) => {
    if (!m.trim() || busy) return; setBusy(true); setErr(""); const history = turns.map((x) => ({ role: x.role, content: x.content }));
    setTurns((x) => [...x, { role: "user", content: m }]); setText("");
    try {
      const r = await api.post<{ reply: string; changes?: Change[]; cv?: Record<string, unknown> | null; letter?: string | null }>("/me/cv-chat", { message: m, target: t, cv, letter, job_id: jid, history, consent });
      setTurns((x) => [...x, { role: "assistant", content: r.reply, changes: r.changes, cv: r.cv, letter: r.letter }]);
    } catch (e) { setErr(e instanceof ApiError ? e.message : (e as Error).message); } finally { setBusy(false); }
  };
  const mark = (i: number, patch: Partial<Turn>) => setTurns((ts) => ts.map((t, j) => (j === i ? { ...t, ...patch } : t)));
  const apply = (i: number, t: Turn) => {
    if (mode === "copy") { if (t.cv) copyCv(t.cv, folder); else if (t.letter) copyLetter(t.letter, folder); mark(i, { state: "applied", copy: folder }); return; }
    if (t.cv) { mark(i, { state: "applied", undo: cv }); applyCv(t.cv); }
    else if (t.letter) { mark(i, { state: "applied", undo: letter }); applyLetter(t.letter); }
  };
  const undo = (i: number, t: Turn) => { if (t.cv && t.undo && typeof t.undo === "object") applyCv(t.undo); else if (t.letter && typeof t.undo === "string") applyLetter(t.undo); mark(i, { state: "discarded" }); };
  const pick = (s: Suggestion) => { if (s.target !== target) return; if (s.needs_detail) setText(s.prompt); else send(s.prompt, s.target); };

  return (<div className="stack aidock"><div className="row"><h2 style={{ margin: 0 }}>AI assistant</h2><span className="chip plain right" style={{ margin: 0, maxWidth: 170, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={docName}>{target === "cv" ? "CV" : "Letter"}: {docName || "none selected"}</span></div>
    <div className="small muted">Tell it what to change in the selected {target === "cv" ? "CV" : "cover letter"}. You see every change first; nothing is applied until you press Apply. It never adds a tool, number or employer that your CV and your words do not show.</div>
    <div className="savebox" role="group" aria-label="Where to save the result">
      <label><input type="radio" name="savemode" checked={mode === "inplace"} onChange={() => setMode("inplace")} /> Update this {target === "cv" ? "CV" : "letter"}</label>
      <label><input type="radio" name="savemode" checked={mode === "copy"} onChange={() => setMode("copy")} /> Save as a new copy in
        <select aria-label="Folder for the copy" value={folder} disabled={mode !== "copy"} onChange={(e) => { if (e.target.value === "\u0000new") { const n = window.prompt("Folder name")?.trim(); if (n) setFolder(n); } else setFolder(e.target.value); }}>
          <option value="">Default folder</option>{[...new Set([...folders, folder].filter(Boolean))].map((f) => <option key={f} value={f}>{f}</option>)}<option value={"\u0000new"}>+ New folder…</option></select></label></div>
    {ai.data && !ai.data.provider && <div className="notice small">First <Link to="/profile">choose an AI model</Link> in your profile (a local Ollama model keeps everything on your computer).</div>}
    {external && <label className="small"><input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); setConsentStored(e.target.checked); }} /> I agree that my CV{jid ? ", this posting" : ""} and my messages are sent to <b>{ai.data?.provider}</b>.</label>}
    {sugg && <div className="stack" style={{ gap: 6 }}><div className="small"><b>Suggested for {sugg.job.title} at {sugg.job.company}</b></div>
      <div>{sugg.suggestions.map((s) => <button key={s.id} className="chip plain" style={{ cursor: "pointer", border: "1px solid var(--line)" }} disabled={!ready || busy} onClick={() => pick(s)} title={s.prompt}>{s.label}</button>)}</div></div>}
    <div className="chatlog" style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: "46vh", overflow: "auto" }}>
      {!turns.length && <div className="small muted">Try: {target === "cv" ? "“Make my summary shorter and focus on mobile”, or “Move Flutter to the top of my skills”." : "“Write a letter for this job”, or “Make it shorter and warmer”."}</div>}
      {turns.map((t, i) => (<div key={i} className={"bubble " + t.role} style={{ padding: "8px 12px", borderRadius: 12, border: "1px solid var(--line)", maxWidth: "94%", alignSelf: t.role === "user" ? "flex-end" : "flex-start", whiteSpace: "pre-wrap", fontSize: 14, background: t.role === "user" ? "var(--chip)" : undefined }}>
        {t.content}
        {!!t.changes?.length && <div className="stack" style={{ gap: 6, marginTop: 8 }}>{t.changes.map((c, k) => <div key={k} className="card" style={{ padding: 10, boxShadow: "none" }}><div className="small muted">{c.section}{c.title ? ` · ${c.title}` : ""}</div>
          {c.before && <div className="small" style={{ textDecoration: "line-through", opacity: .6 }}>{c.before}</div>}<div className="small">{c.after}</div></div>)}</div>}
        {t.letter && <textarea readOnly rows={8} value={t.letter} style={{ width: "100%", marginTop: 8, fontFamily: "inherit", fontSize: 13 }} />}
        {(t.cv || t.letter) && <div className="row" style={{ marginTop: 8, gap: 8 }}>
          {!t.state && <><button className="btn small" onClick={() => apply(i, t)}>{mode === "copy" ? "Save as copy" : "Apply"}</button><button className="btn ghost small" onClick={() => mark(i, { state: "discarded" })}>Discard</button></>}
          {t.state === "applied" && t.copy === undefined && <><span className="chip ok" style={{ margin: 0 }}>Applied</span><button className="btn ghost small" onClick={() => undo(i, t)}>Undo</button></>}
          {t.state === "applied" && t.copy !== undefined && <span className="chip ok" style={{ margin: 0 }}>Saved as a copy in {t.copy || "Default"}</span>}
          {t.state === "discarded" && <span className="small muted">Not applied</span>}</div>}
      </div>))}
      {busy && <div className="small muted">Thinking…</div>}<div ref={end} /></div>
    {err && <div className="notice err small">{err}</div>}
    <form className="stack" style={{ gap: 8 }} onSubmit={(e) => { e.preventDefault(); send(text); }}>
      <textarea rows={2} value={text} placeholder={target === "cv" ? "What should I change in this CV?" : "What should I write or change in this letter?"} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }} style={{ width: "100%", resize: "vertical" }} aria-label="Message" maxLength={2000} />
      <button className="btn" style={{ alignSelf: "flex-end" }} disabled={!ready || busy || !text.trim()}>Send</button></form>
  </div>);
}
