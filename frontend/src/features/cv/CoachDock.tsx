import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/shared/api/client";
import { Dock } from "@/shared/ui/kit";
import { isExternalAi, useAiSettings } from "@/features/ai/AiPanel";
import { getConsent, setConsentStored } from "@/features/fit/api";

interface Proposal { kind: "skill" | "bullet" | "project" | "summary"; text: string; role?: number; role_title?: string; title?: string; tech?: string }
interface Turn { role: "user" | "assistant"; content: string; proposals?: Proposal[]; done?: Record<number, "yes" | "no"> }
const KIND: Record<Proposal["kind"], string> = { skill: "Skill", bullet: "Bullet", project: "Project", summary: "Summary" };

/** A floating chat: tell the AI what you can do, it writes it as CV additions, you edit and accept each one. Never changes the CV by itself. */
export function CoachDock({ jobId, title, onClose }: { jobId: number; title: string; onClose(): void }) {
  const qc = useQueryClient(); const ai = useAiSettings();
  const gaps = useQuery({ queryKey: ["coach-gaps", jobId], retry: false, queryFn: () => api.get<{ missing: string[] }>(`/me/cv-coach/gaps/${jobId}`) });
  const [turns, setTurns] = useState<Turn[]>([]); const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [consent, setConsent] = useState(getConsent()); const end = useRef<HTMLDivElement>(null);
  const external = isExternalAi(ai.data); const ready = !!ai.data?.provider && (!external || consent);
  useEffect(() => { end.current?.scrollIntoView?.({ block: "end" }); }, [turns, busy]);

  const send = async (m: string) => {
    if (!m.trim() || busy) return; setBusy(true); setErr(""); const history = turns.map((t) => ({ role: t.role, content: t.content }));
    setTurns((t) => [...t, { role: "user", content: m }]); setText("");
    try {
      const r = await api.post<{ reply: string; proposals: Proposal[] }>("/me/cv-coach", { message: m, job_id: jobId, history, consent });
      setTurns((t) => [...t, { role: "assistant", content: r.reply, proposals: r.proposals, done: {} }]);
    } catch (e) { setErr(e instanceof ApiError ? e.message : (e as Error).message); } finally { setBusy(false); }
  };
  const edit = (ti: number, pi: number, v: string) => setTurns((ts) => ts.map((t, i) => i !== ti ? t : { ...t, proposals: t.proposals!.map((p, j) => j === pi ? { ...p, text: v } : p) }));
  const decide = async (ti: number, pis: number[], yes: boolean) => {
    const t = turns[ti]; if (yes) {
      try { await api.post("/me/cv-coach/apply", { proposals: pis.map((i) => t.proposals![i]) }); await Promise.all([qc.invalidateQueries({ queryKey: ["stored-cv"] }), qc.invalidateQueries({ queryKey: ["coach-gaps", jobId] }), qc.invalidateQueries({ queryKey: ["jobs"] })]); }
      catch (e) { setErr(e instanceof ApiError ? e.message : (e as Error).message); return; }
    }
    setTurns((ts) => ts.map((x, i) => i !== ti ? x : { ...x, done: { ...x.done, ...Object.fromEntries(pis.map((p) => [p, yes ? "yes" : "no"])) } }));
  };
  const missing = (gaps.data?.missing ?? []).filter((m) => !turns.some((t) => t.role === "user" && t.content.toLowerCase().includes(m.toLowerCase()))).slice(0, 6);

  return (<Dock id="coach" title={<>✦ CV coach <span className="muted small">· {title}</span></>} onClose={onClose} width={400}>
    <div className="coach">
      {!turns.length && <div className="small muted">Missing something you have actually done? Tell me in your own words and I will add it to your CV. You review every change.</div>}
      {ai.data && !ai.data.provider && <div className="small notice">First <Link to="/profile">choose an AI model</Link>.</div>}
      {external && <label className="small"><input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); setConsentStored(e.target.checked); }} /> I agree my CV and messages are sent to <b>{ai.data?.provider}</b>.</label>}
      {!turns.length && missing.length > 0 && <div className="coach-q"><span className="small muted">This job asks for things your CV does not show. Tap one if you have done it:</span>
        <div>{missing.map((m) => <button key={m} className="qtoggle" onClick={() => setText(`I have experience with ${m}: `)}>{m}</button>)}</div></div>}
      <div className="coach-log" aria-live="polite">
        {turns.map((t, ti) => <div key={ti} className={`cbub ${t.role}`}>
          <div>{t.content}</div>
          {t.proposals?.map((p, pi) => { const d = t.done?.[pi]; return (<div key={pi} className={"cprop" + (d ? " " + d : "")}>
            <div className="small muted">{KIND[p.kind]}{p.kind === "bullet" && p.role_title ? ` · under ${p.role_title}` : ""}{p.kind === "project" && p.title ? ` · ${p.title}` : ""}</div>
            {d === "yes" ? <div className="small okc">✓ Added to your CV: {p.text}</div> : d === "no" ? <div className="small muted">Skipped</div> : <>
              <textarea rows={p.kind === "skill" ? 1 : 3} value={p.text} onChange={(e) => edit(ti, pi, e.target.value)} aria-label={`Edit ${KIND[p.kind]}`} />
              <div className="row"><button className="btn small" onClick={() => decide(ti, [pi], true)}>Add to my CV</button><button className="btn ghost small" onClick={() => decide(ti, [pi], false)}>Skip</button></div></>}
          </div>); })}
        </div>)}
        {busy && <div className="cbub assistant muted">Thinking…</div>}
        <div ref={end} />
      </div>
      {err && <div className="small err">{err}</div>}
      <form className="coach-in" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. I used Docker and Kubernetes at my last job to deploy our services" aria-label="Tell the coach"
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }} />
        <button className="btn" disabled={!ready || busy || !text.trim()}>Send</button>
      </form>
      {turns.some((t) => Object.values(t.done ?? {}).includes("yes")) && <div className="small muted">Your saved CV is updated. Open the “My CV” tab and press Redo tailoring to use it.</div>}
    </div>
  </Dock>);
}
