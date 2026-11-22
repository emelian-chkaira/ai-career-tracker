import { useRef, useState } from "react";
import { api } from "@/shared/api/client";

/** Renders the small markup the PDF understands: **bold** and [label](url). */
export function Rich({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g);
  return <>{parts.map((p, i) => { const b = /^\*\*(.+)\*\*$/.exec(p); if (b) return <b key={i}>{b[1]}</b>; const l = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(p); return l ? <span key={i} className="lnk">{l[1]}</span> : <span key={i}>{p}</span>; })}</>;
}

/** Text box with a formatting toolbar (bold, link) and an AI sparkle that rewrites the field. The rewrite is checked on the server: it may not add numbers or skills the CV lacks. */
export function RichField({ label, value, onChange, rows = 4, kind = "bullet", help, aiReady }: { label: string; value: string; onChange(v: string): void; rows?: number; kind?: string; help?: string; aiReady: boolean }) {
  const ref = useRef<HTMLTextAreaElement>(null); const [ai, setAi] = useState(false); const [instr, setInstr] = useState(""); const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [sugg, setSugg] = useState("");
  const wrap = (a: string, b: string, ph: string) => { const t = ref.current; if (!t) return; const s = t.selectionStart, e = t.selectionEnd; const sel = value.slice(s, e) || ph; onChange(value.slice(0, s) + a + sel + b + value.slice(e)); };
  const link = () => { const u = window.prompt("Link address (https://…)"); if (u) wrap("[", `](${u.trim()})`, "link text"); };
  const run = async () => { setBusy(true); setErr(""); try { setSugg((await api.post<{ text: string }>("/me/tailor/field", { text: value, instruction: instr, kind, consent })).text); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } };
  return (<div className="field rich"><div className="row" style={{ gap: 6 }}><label>{label}</label>
    <span className="rtools"><button type="button" className="kicon" onClick={() => wrap("**", "**", "bold text")} aria-label="Bold"><b>B</b></button><button type="button" className="kicon" onClick={link} aria-label="Insert link">🔗</button>
      <button type="button" className={"kicon" + (ai ? " on" : "")} onClick={() => setAi(!ai)} aria-label="AI assist" title={aiReady ? "Improve this with AI" : "Choose an AI model in Profile & AI first"} disabled={!aiReady}>✨</button></span></div>
    <textarea ref={ref} rows={rows} value={value} onChange={(e) => onChange(e.target.value)} />
    {help && <div className="small muted">{help}</div>}
    {/\*\*|\]\(/.test(value) && <div className="rprev small"><Rich text={value} /></div>}
    {ai && <div className="notice stack" style={{ gap: 8 }}>
      <input type="text" value={instr} placeholder="What should change? e.g. shorter, more concrete, mention teamwork" onChange={(e) => setInstr(e.target.value)} />
      <label className="small row" style={{ gap: 6 }}><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />I agree that this text and my CV are sent to my chosen AI provider (not needed for local models).</label>
      <div className="row"><button type="button" className="btn small" disabled={busy || !value.trim()} onClick={run}>{busy ? "Thinking…" : "Rewrite"}</button><span className="small muted">Edits that add new numbers or skills are dropped.</span></div>
      {err && <div className="small err">{err}</div>}
      {sugg && <div className="stack" style={{ gap: 6 }}><div className="rprev"><Rich text={sugg} /></div><div className="row"><button type="button" className="btn small" onClick={() => { onChange(sugg); setSugg(""); setAi(false); }}>Use this</button><button type="button" className="btn ghost small" onClick={() => setSugg("")}>Discard</button></div></div>}
    </div>}
  </div>);
}
