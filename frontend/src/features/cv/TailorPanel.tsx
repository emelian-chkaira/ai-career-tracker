import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { isExternalAi, useAiSettings } from "@/features/ai/AiPanel";
import { getConsent, setConsentStored, useStoredCv } from "@/features/fit/api";

type Cov = { matched: string[]; missing: string[]; percent: number };
type Tailored = { latex: string; template: string; cover_letter: string | null; model: string; cv: Record<string, unknown>;
  report: { before: Cov; after: Cov; changes: { section: string; title: string; before: string; after: string }[]; rejected: { section: string; title?: string; why: string }[]; gaps: string[]; notes: string; fit?: string; poor_match?: string; reactive_resume?: { id: string | null; url: string; name: string }; reactive_resume_error?: string } };
type Auto = { on: boolean; stages: string[]; push_rr: boolean; consent: boolean; available_stages: string[] };

const download = (name: string, data: BlobPart, type: string) => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([data], { type })); a.download = name; a.click(); };

/** A CV rewritten for this one job by the user's AI model. Reworded only: invented numbers and skills are rejected and listed. */
export function TailorPanel({ jobId, title }: { jobId: number; title: string }) {
  const { user } = useAuth(); const qc = useQueryClient(); const cv = useStoredCv(!!user); const ai = useAiSettings();
  const saved = useQuery({ queryKey: ["tailor", jobId], enabled: !!user, retry: false, queryFn: async () => { try { return await api.get<Tailored>(`/me/tailor/${jobId}`); } catch (e) { if (e instanceof ApiError && e.status === 404) return null; throw e; } } });
  const auto = useQuery({ queryKey: ["tailor-auto"], enabled: !!user, retry: false, queryFn: () => api.get<Auto>("/me/tailor/auto") });
  const rr = useQuery({ queryKey: ["rr-conn"], enabled: !!user, retry: false, queryFn: () => api.get<{ connected: boolean }>("/me/rr") });
  const [busy, setBusy] = useState(""); const [err, setErr] = useState(""); const [consent, setConsent] = useState(getConsent()); const [pubOk, setPubOk] = useState(false); const [letter, setLetter] = useState<string | null>(null);
  if (!user) return null;
  const t = saved.data; const external = isExternalAi(ai.data); const ready = !!cv.data && !!ai.data?.provider && (!external || consent);
  const call = async (key: string, fn: () => Promise<unknown>) => { setBusy(key); setErr(""); try { await fn(); await qc.invalidateQueries({ queryKey: ["tailor", jobId] }); } catch (e) { setErr(e instanceof ApiError ? e.message : (e as Error).message); } finally { setBusy(""); } };
  const run = () => call("tailor", () => api.post(`/me/tailor/${jobId}`, { consent }));
  const rebuild = () => call("rebuild", () => api.post(`/me/tailor/${jobId}/rebuild`, { consent, push: true }));
  const setAuto = (p: Partial<Auto>) => call("auto", async () => { const a = { ...auto.data!, ...p }; await api.put("/me/tailor/auto", { on: a.on, stages: a.stages, push_rr: a.push_rr, consent: a.consent }); await qc.invalidateQueries({ queryKey: ["tailor-auto"] }); });
  const writeLetter = () => call("letter", async () => { await api.post(`/me/tailor/${jobId}/cover-letter`, { consent }); setLetter(null); });
  const pdf = () => call("pdf", async () => { const r = await api.post<{ pdf_b64: string }>(`/me/tailor/${jobId}/pdf`, { mode: pubOk ? "auto" : "local", allow_public: pubOk }); const b = atob(r.pdf_b64); download(`cv-${jobId}.pdf`, Uint8Array.from(b, (c) => c.charCodeAt(0)), "application/pdf"); });
  const saveLetter = () => call("saveletter", () => api.put(`/me/tailor/${jobId}`, { cover_letter: letter }));
  const setTemplate = (template: string) => call("tpl", () => api.put(`/me/tailor/${jobId}`, { template }));
  const autoBox = auto.data ? (<div className="stack" style={{ gap: 6 }}>
    <label className="small row" style={{ gap: 8 }}><input type="checkbox" checked={auto.data.on} disabled={!!busy || (external && !consent && !auto.data.on)} onChange={(e) => setAuto({ on: e.target.checked, consent: external ? consent : auto.data!.consent })} /><b>Tailor automatically when I follow a job</b></label>
    <div className="small muted">When a job reaches one of these stages, the worker tailors your CV and rebuilds it in Reactive Resume. Review it before you send it.</div>
    <div className="row">{auto.data.available_stages.map((s) => <label key={s} className="small row" style={{ gap: 4 }}><input type="checkbox" checked={auto.data!.stages.includes(s)} disabled={!!busy} onChange={(e) => setAuto({ stages: e.target.checked ? [...auto.data!.stages, s] : auto.data!.stages.filter((x) => x !== s) })} />{s}</label>)}</div>
    {external && !auto.data.on && !consent && <div className="small muted">Tick the consent box first: automatic runs send your CV to {ai.data?.provider}.</div>}
  </div>) : null;
  const inRR = !!rr.data?.connected; const go = inRR ? rebuild : run;
  const pct = t ? t.report.after.percent : 0;
  return (<div className="tailor stack">
    {!t ? <>
      <div className="tstep"><span className="tnum">1</span><div className="grow"><b>Tailor my CV for this job</b><div className="small muted">The AI rewords your saved CV with the posting's keywords for “{title}”. It never adds facts you do not have.</div></div></div>
      {!cv.data && <div className="small notice">First <Link to="/cv">save your CV for AI</Link>.</div>}
      {ai.data && !ai.data.provider && <div className="small notice">Then <Link to="/profile">choose an AI model</Link>.</div>}
      {external && <label className="small"><input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); setConsentStored(e.target.checked); }} /> I agree that my CV and this posting are sent to <b>{ai.data?.provider}</b>.</label>}
      <button className="btn tprimary" disabled={!ready || !!busy} onClick={go}>{busy ? "Tailoring…" : inRR ? "Tailor & rebuild in Reactive Resume" : "Tailor my CV"}</button>
      {inRR && <button className="linkbtn small" disabled={!ready || !!busy} onClick={run}>Tailor only, do not send to Reactive Resume</button>}
    </> : <>
      <div className="tcov"><div className="tcov-top"><b>{pct}%</b><span className="small muted">of this posting's keywords are in your CV{t.report.before.percent !== pct ? ` (was ${t.report.before.percent}%)` : ""}</span></div>
        <div className="mbar"><i style={{ width: `${Math.min(100, pct)}%` }} /></div></div>
      {t.report.poor_match && <div className="notice small" role="alert">⚠ {t.report.poor_match} <Link to="/cv">Add what is true in CV Studio, Missing keywords.</Link></div>}
      {t.report.notes && <div className="small muted">{t.report.notes}</div>}
      {!!t.report.after.missing.length && <div className="small"><span className="muted">Not in your CV, so not added: </span>{t.report.after.missing.slice(0, 8).join(", ")}</div>}
      <div className="row"><button className="btn tprimary" disabled={!!busy} onClick={pdf}>{busy === "pdf" ? "Building…" : "Download PDF"}</button>
        {t.report.reactive_resume ? <a className="btn ghost" href={t.report.reactive_resume.url} target="_blank" rel="noreferrer noopener">Open it in Reactive Resume ↗</a>
          : inRR && <button className="btn ghost" disabled={!ready || !!busy} onClick={rebuild}>{busy === "rebuild" ? "Sending…" : "Send to Reactive Resume"}</button>}</div>
      {t.report.reactive_resume_error && !t.report.reactive_resume && <div className="small muted">Not in Reactive Resume yet: {t.report.reactive_resume_error}</div>}
      <details className="fold"><summary>What changed ({t.report.changes.length})</summary>
        {!!t.report.rejected.length && <div className="small muted">{t.report.rejected.length} edit{t.report.rejected.length > 1 ? "s were" : " was"} dropped because {t.report.rejected.length > 1 ? "they" : "it"} added facts your CV does not contain.</div>}
        <div className="stack">{t.report.changes.map((c, i) => <div key={i} className="diff"><div className="small muted">{c.section}{c.title ? ` · ${c.title}` : ""}</div><div className="del">{c.before}</div><div className="add">{c.after}</div></div>)}{!t.report.changes.length && <div className="small muted">Nothing needed rewording.</div>}</div></details>
      <details className="fold"><summary>Cover letter</summary>
        {t.cover_letter == null ? <div className="row"><button className="btn ghost small" disabled={!ready || !!busy} onClick={writeLetter}>{busy === "letter" ? "Writing…" : "Write a cover letter"}</button></div> : <>
          <textarea rows={10} value={letter ?? t.cover_letter} onChange={(e) => setLetter(e.target.value)} style={{ fontFamily: "inherit", fontSize: 14 }} />
          <div className="row"><button className="btn ghost small" onClick={() => navigator.clipboard.writeText(letter ?? t.cover_letter ?? "")}>Copy</button><button className="btn ghost small" onClick={() => download("cover-letter.txt", letter ?? t.cover_letter ?? "", "text/plain")}>Download</button>
            {letter != null && letter !== t.cover_letter && <button className="btn small" disabled={!!busy} onClick={saveLetter}>Save edits</button>}<button className="btn ghost small right" disabled={!ready || !!busy} onClick={writeLetter}>Rewrite</button></div></>}</details>
      <details className="fold"><summary>More options</summary>
        <div className="row"><select value={t.template} onChange={(e) => setTemplate(e.target.value)} title="Layout"><option value="mine">My CV layout</option><option value="classic">Classic layout</option><option value="compact">Compact layout</option></select>
          <button className="btn ghost small" onClick={() => download(`cv-${jobId}.tex`, t.latex, "text/x-tex")}>Get .tex</button>
          <button className="btn ghost small" disabled={!ready || !!busy} onClick={go}>{busy === "tailor" || busy === "rebuild" ? "Tailoring…" : "Redo tailoring"}</button></div>
        <label className="small"><input type="checkbox" checked={pubOk} onChange={(e) => setPubOk(e.target.checked)} /> If this server has no LaTeX compiler, allow a public one (sends the CV to a third party).</label>
        <div className="small muted">Written by {t.model}.</div>
        {autoBox}</details>
    </>}
    {!t && <details className="fold"><summary>Automatic tailoring</summary>{autoBox}</details>}
    {err && <div className="small err">{err}</div>}
  </div>);
}
