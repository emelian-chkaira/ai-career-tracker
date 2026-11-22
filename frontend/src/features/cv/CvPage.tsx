import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/shared/api/client";
import { uget, uset } from "@/shared/lib/userStore";
import { useAuth } from "@/features/auth/AuthContext";
import { saveStoredCv } from "@/features/fit/api";
import { Panel, usePane, Splitter } from "@/shared/ui/kit";
import { Studio } from "./Studio";
import { TemplateGallery } from "./Gallery";
import { SectionToggles } from "./SectionsEditor";
import { RrPanel } from "./RrPanel";
import { useAiSettings } from "@/features/ai/AiPanel";
import { useQueryClient } from "@tanstack/react-query";

interface CvData { name: string; email: string; phone: string; location: string; links: string[]; summary: string; skills: string[]; languages: string[]; references?: string[]; skill_groups?: unknown; certifications: string[]; order?: string[]; [k: string]: unknown }
interface Extracted { cv: CvData; latex: string; source?: string }
interface Tailored { text: string; latex?: string; changes?: string[]; matched: string[]; gaps: string[]; match_score: number; keywords: string[] }
interface AiOut { cv: CvData; latex: string; changes: { section: string; title: string; before: string; after: string }[]; gaps: string[]; notes: string; job: { title: string; company: string } }
interface PdfOut { pdf_b64: string; engine: string; bytes: number }
type Mode = "local" | "public";
const KEY = "cv-draft";             // per-account browser cache (shared/lib/userStore); the server copy (/me/cv/draft) is the real one
const load = (): Extracted | null => { try { return JSON.parse(uget(KEY) ?? "null"); } catch { return null; } };
const save = (v: Extracted | null) => uset(KEY, v ? JSON.stringify(v) : null);

/** One studio per account: switching accounts remounts it, so nothing from the previous account stays in memory. */
export function CvPage() {
  const { user, ready } = useAuth();
  if (!ready) return <p className="muted">Loading…</p>;           // know whose studio it is before showing (or caching) any CV
  return <CvStudio key={user?.id ?? "anon"} />;
}

function CvStudio() {
  const [sp] = useSearchParams(); const [jobId, setJobId] = useState(sp.get("job") ?? "");
  const [cv, setCvState] = useState<Extracted | null>(load); const [tailored, setTailored] = useState<Tailored | null>(null); const [letter, setLetter] = useState("");
  const [pdf, setPdf] = useState<{ url: string; engine: string; bytes: number } | null>(null);
  const [busy, setBusy] = useState(""); const [err, setErr] = useState(""); const [tone, setTone] = useState("professional");
  const [mode, setMode] = useState<Mode>("local"); const [consent, setConsent] = useState(false); const [localOk, setLocalOk] = useState<boolean | null>(null);
  const [aiOk, setAiOk] = useState(false); const [aiConsent, setAiConsent] = useState(false); const [ai, setAi] = useState<AiOut | null>(null);
  const [over, setOver] = useState(false); const fileRef = useRef<HTMLInputElement>(null); const [dirty, setDirty] = useState(false);

  useEffect(() => { api.get<{ local: boolean; ai: boolean }>("/cv/compilers").then((r) => { setLocalOk(r.local); setAiOk(r.ai); if (!r.local) setMode("public"); }).catch(() => setLocalOk(false)); }, []);
  const { user } = useAuth(); const qcl = useQueryClient(); const [stored, setStored] = useState("");
  const [template, setTemplate] = useState(() => uget("cv-template") ?? "classic");
  const [paper, setPaper] = useState(() => uget("cv-paper") ?? "a4");
  const [live, setLive] = useState(true); const [prevBusy, setPrevBusy] = useState(false); const [prevErr, setPrevErr] = useState("");
  const pick = (k: string, v: string, set: (x: string) => void) => { set(v); uset(k, v); };
  // The account's own draft lives on the server: load it once, then save every change a second after the last edit.
  const [synced, setSynced] = useState(!user); const [saveErr, setSaveErr] = useState("");
  useEffect(() => {
    if (!user) return;
    api.get<{ draft: Extracted & { template?: string; paper?: string } }>("/me/cv/draft")
      .then((r) => { const { template: t, paper: pp, ...d } = r.draft; setCvState(d.cv ? d : null); save(d.cv ? d : null); if (t) { setTemplate(t); uset("cv-template", t); } if (pp) { setPaper(pp); uset("cv-paper", pp); } })
      .catch(() => { /* 404: nothing saved yet; keep this account's local cache, if any */ })
      .finally(() => setSynced(true));
  }, [user?.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!user || !synced) return;
    const t = setTimeout(() => {
      const req = cv ? api.put("/me/cv/draft", { draft: { ...cv, template, paper } }) : api.del("/me/cv/draft");
      req.then(() => setSaveErr("")).catch((e) => setSaveErr((e as Error).message));
    }, 1000);
    return () => clearTimeout(t);
  }, [cv, template, paper, synced]);   // eslint-disable-line react-hooks/exhaustive-deps
  const showPdf = (r: PdfOut) => { const url = URL.createObjectURL(new Blob([Uint8Array.from(atob(r.pdf_b64), (c) => c.charCodeAt(0))], { type: "application/pdf" })); setPdf((old) => { if (old) URL.revokeObjectURL(old.url); return { url, engine: r.engine, bytes: r.bytes }; }); };
  // Live preview: rebuild the PDF a moment after every edit (local compiler only, so the CV never leaves the server). Not for imported .tex files, which keep their own source.
  const structured = cv && cv.source !== "latex";
  useEffect(() => {
    if (!live || !structured || !localOk) return;
    let stale = false; const t = setTimeout(async () => {
      setPrevBusy(true); setPrevErr("");
      try { const r = await api.post<PdfOut>("/cv/preview", { cv: cv!.cv, template, paper }); if (!stale) showPdf(r); }
      catch (e) { if (!stale) setPrevErr((e as Error).message); } finally { if (!stale) setPrevBusy(false); }
    }, 700);
    return () => { stale = true; clearTimeout(t); };
  }, [cv?.cv, template, paper, live, localOk]);   // eslint-disable-line react-hooks/exhaustive-deps
  const setCv = (v: Extracted | null) => { setCvState(v); save(v); };
  const run = async (name: string, fn: () => Promise<void>) => { setBusy(name); setErr(""); try { await fn(); } catch (e) { setErr((e as Error).message); } finally { setBusy(""); } };
  const edit = (patch: Partial<CvData>) => { if (!cv) return; setCv({ ...cv, cv: { ...cv.cv, ...patch } }); setDirty(true); };

  /** Keep the grouped skills table in sync: removed skills leave their group, new ones go to an "Other" group. */
  const setSkills = (v: string[]) => {
    const old = cv?.cv.skills ?? []; const groups = (cv?.cv.skill_groups as { label: string; items: string[] }[] | undefined) ?? [];
    if (!groups.length) return edit({ skills: v });
    const kept = groups.map((g) => ({ ...g, items: g.items.filter((x) => v.includes(x)) })).filter((g) => g.items.length);
    const added = v.filter((x) => !old.includes(x));
    if (added.length) { const o = kept.find((g) => g.label === "Other"); if (o) o.items.push(...added); else kept.push({ label: "Other", items: added }); }
    edit({ skills: v, skill_groups: kept });
  };
  const upload = (f: File) => run("upload", async () => { const r = await api.upload<Extracted>("/cv/extract", f, { filename: f.name }); setCv(r); setTailored(null); setPdf(null); setDirty(false); });
  const rebuild = () => run("rebuild", async () => { const r = await api.post<{ latex: string }>("/cv/latex", { cv: cv!.cv, template, paper }); setCv({ ...cv!, latex: r.latex }); setDirty(false); });
  const build = (latex: string, name: string) => run("pdf", async () => {
    if (mode === "public" && !consent) throw new Error("Tick the consent box to use a public LaTeX service.");
    const r = await api.post<PdfOut>("/cv/pdf", { latex, mode, allow_public: consent });
    const url = URL.createObjectURL(new Blob([Uint8Array.from(atob(r.pdf_b64), (c) => c.charCodeAt(0))], { type: "application/pdf" }));
    if (pdf) URL.revokeObjectURL(pdf.url); setPdf({ url, engine: r.engine, bytes: r.bytes }); void name;
  });
  const tailor = () => run("tailor", async () => { const t = await api.post<Tailored>("/cv/tailor", { cv: cv!.cv, latex: cv!.latex, job_id: +jobId }); setTailored(t); });
  const aiTailor = () => run("ai", async () => setAi(await api.post<AiOut>("/cv/ai-tailor", { cv: cv!.cv, job_id: +jobId, consent: aiConsent })));
  const applyAi = () => { if (!ai || !cv) return; setCv({ ...cv, cv: ai.cv, latex: ai.latex }); setPdf(null); setAi(null); setDirty(false); };
  const cover = () => run("letter", async () => setLetter((await api.post<{ text: string }>("/cv/cover-letter", { cv: cv!.cv, job_id: +jobId, tone })).text));
  const download = (name: string, data: BlobPart, type: string) => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([data], { type })); a.download = name; a.click(); };
  const step = !cv ? 1 : tailored ? 4 : 2;

  const aiSet = useAiSettings(); const paneL = usePane("cv-left", 500, 340, 760); const paneR = usePane("cv-right", 270, 220, 460, -1);
  const latexNode = cv ? (<Panel id="cv-details" title="LaTeX source"><div className="stack"><div className="row"><h2 style={{ margin: 0 }}>LaTeX</h2><span className="chip plain">{cv.source ?? "text"}</span>
    <button className="btn ghost small right" onClick={() => { setCv(null); setTailored(null); setPdf(null); setLetter(""); }}>Replace CV</button></div>
    <div className="row"><button className="btn" onClick={rebuild} disabled={!!busy}>{busy === "rebuild" ? "Rebuilding…" : dirty ? "Apply edits → LaTeX" : "Rebuild LaTeX"}</button>{dirty && <span className="small muted">You have edits not yet in the LaTeX.</span>}</div>
    <details open={!structured}><summary className="small">LaTeX source ({cv.latex.length.toLocaleString()} chars), editable</summary><textarea rows={14} value={cv.latex} onChange={(e) => setCv({ ...cv, latex: e.target.value })} /></details></div></Panel>) : null;
  const tailorNode = (<>
    <Panel id="cv-tailor" title="Tailor to a job" ><div className="stack"><h2 style={{ margin: 0 }}>Tailor to a job</h2>
          <div className="row"><input type="number" placeholder="Job ID" value={jobId} onChange={(e) => setJobId(e.target.value)} style={{ width: 120 }} />
            <select value={tone} onChange={(e) => setTone(e.target.value)}><option value="professional">Professional</option><option value="warm">Warm</option><option value="concise">Concise</option></select>
            <button className="btn" disabled={!jobId || !!busy} onClick={tailor}>{busy === "tailor" ? "Tailoring…" : "Tailor CV"}</button>
            <button className="btn ghost" disabled={!jobId || !!busy} onClick={cover}>{busy === "letter" ? "Writing…" : "Cover letter"}</button></div>
          <div className="small muted">Open a job and press “Tailor CV & letter” to fill the ID. Tailoring only re-orders what is already in your CV; missing requirements are listed as gaps, never added.</div>
          {tailored && <div className="stack" style={{ gap: 8 }}>
            <div className="row"><strong>Match {tailored.match_score}%</strong><span className="small muted">{tailored.matched.length} of {tailored.keywords.length} keywords</span></div>
            <div>{tailored.matched.map((m) => <span key={m} className="chip ok">{m}</span>)}{tailored.gaps.slice(0, 8).map((m) => <span key={m} className="chip plain" title="Not in your CV">gap: {m}</span>)}</div>
            {tailored.changes?.map((c) => <div key={c} className="small muted">• {c}</div>)}
            <div className="row">{tailored.latex && <button className="btn small" onClick={() => build(tailored.latex!, "tailored")} disabled={!!busy}>Build tailored PDF</button>}
              {tailored.latex && <button className="btn ghost small" onClick={() => download("tailored-cv.tex", tailored.latex!, "text/x-tex")}>.tex</button>}
              <button className="btn ghost small" onClick={() => download("tailored-cv.txt", tailored.text, "text/plain")}>Text</button></div></div>}
        </div></Panel>
        <Panel id="cv-ai" title="AI tailoring (Claude)" ><div className="stack"><div className="row"><h2 style={{ margin: 0 }}>AI tailoring</h2><span className="chip plain">Claude</span></div>
          {!aiOk ? <div className="small muted">Not enabled on this server. Set <code>ANTHROPIC_API_KEY</code> to let Claude rewrite your CV for a job. It only rewords what your CV already says and never adds skills or experience.</div> : <>
            <div className="small muted">Claude rewrites the summary and bullets using the posting's vocabulary, reorders your skills, and lists gaps. You review every change before it is applied.</div>
            <label className="notice row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><input type="checkbox" checked={aiConsent} onChange={(e) => setAiConsent(e.target.checked)} style={{ marginTop: 4 }} /><span>Send my CV and this job posting to Anthropic. Your CV contains personal data and leaves this server.</span></label>
            <div className="row"><button className="btn" disabled={!jobId || !aiConsent || !!busy} onClick={aiTailor}>{busy === "ai" ? "Claude is tailoring…" : "Tailor with AI"}</button>{!jobId && <span className="small muted">Enter a job ID above first.</span>}</div></>}
          {ai && <div className="stack" style={{ gap: 10 }}>
            <strong>{ai.changes.length} suggested change{ai.changes.length === 1 ? "" : "s"} for {ai.job.title} at {ai.job.company}</strong>
            {ai.notes && <div className="small muted">{ai.notes}</div>}
            {ai.changes.map((c, i) => <div key={i} className="card" style={{ padding: 12, boxShadow: "none" }}><div className="small muted">{c.section}{c.title ? ` · ${c.title}` : ""}</div>
              <div className="small" style={{ textDecoration: "line-through", opacity: .6 }}>{c.before || "—"}</div><div className="small">{c.after}</div></div>)}
            {ai.gaps.length > 0 && <div><span className="small muted">Requirements your CV does not show (not added): </span>{ai.gaps.map((g) => <span key={g} className="chip plain">{g}</span>)}</div>}
            <div className="row"><button className="btn" onClick={applyAi}>Apply changes</button><button className="btn ghost" onClick={() => setAi(null)}>Discard</button><span className="small muted">After applying, press “Build PDF”.</span></div></div>}
        </div></Panel>
        {letter && <Panel id="cv-letter" title="Cover letter"><div className="stack"><textarea rows={14} value={letter} onChange={(e) => setLetter(e.target.value)} style={{ fontFamily: "inherit", fontSize: 14 }} />
          <div className="row"><button className="btn ghost small" onClick={() => navigator.clipboard.writeText(letter)}>Copy</button><button className="btn ghost small" onClick={() => download("cover-letter.txt", letter, "text/plain")}>Download</button></div></div></Panel>}
  </>);
  const tools = [{ id: "tailor", label: "Tailor to a job", icon: "🎯", node: tailorNode }, { id: "rr", label: "Reactive Resume", icon: "♻", node: <RrPanel cv={cv?.cv} template={template} paper={paper} onImport={(c) => { setCv({ cv: c as CvData, latex: "", source: "reactive-resume" }); setDirty(true); }} /> }, { id: "latex", label: "LaTeX", icon: "∑", node: latexNode }];

  return (<div className={"stack" + (cv ? " cvfull" : "")}>
    {!cv && <><div><h1>CV Studio</h1><div className="muted">Import your CV (PDF, Word, LaTeX or Reactive Resume JSON), fix what the parser got wrong, watch the PDF update as you edit, and export. {user ? "Your draft is saved, encrypted, to your account only: another account on this computer never sees it." : "Without an account the draft stays in this browser only; sign in to keep it in your account."}</div></div>
    <div className="steps">{["Import", "Review", "Tailor to a job", "Export PDF"].map((s, i) => <div key={s} className={"step" + (step === i + 1 ? " on" : step > i + 1 ? " done" : "")}><b>{step > i + 1 ? "✓" : i + 1}</b>{s}</div>)}</div></>}
    {err && <div className="notice err">{err}</div>}
    {cv && user && <div className="row small">{user && <span className="small muted cvsave" title="Your CV is kept on the server for this account only">{saveErr ? <span className="bad">Not saved: {saveErr}</span> : synced ? "Saved to your account" : "Loading your CV…"}</span>}<button className="btn ghost small" onClick={async () => { try { await saveStoredCv(cv.cv); qcl.invalidateQueries({ queryKey: ["stored-cv"] }); setStored("Saved. Jobs can now be scored against this CV."); } catch (e) { setStored((e as Error).message); } }}>Use for AI scoring</button><span className="muted">{stored || "Stores this CV encrypted on your account so AI can compare it with job postings."}</span></div>}

    {!cv && <div className={"drop" + (over ? " over" : "")} onClick={() => fileRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]); }}>
      <div style={{ fontSize: 34 }}>📄</div><h2>{busy === "upload" ? "Reading your CV…" : "Drop your CV here or click to browse"}</h2><div className="muted">PDF, DOCX, LaTeX (.tex), Reactive Resume JSON or plain text · max 3 MB</div>
      <input ref={fileRef} hidden type="file" accept=".pdf,.docx,.txt,.tex,.md,.json" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} /></div>}

    {cv && <div className="ws" style={{ "--wl": `${paneL.width}px`, "--wr": `${paneR.width}px` } as React.CSSProperties}>
      <div className="ws-left">
        {structured ? <Studio cv={cv.cv} edit={(p) => edit(p as Partial<CvData>)} setSkills={setSkills} aiReady={!!aiSet.data?.provider} tools={tools} /> : <>{latexNode}{tailorNode}</>}
      </div>

      <Splitter props={paneL.props} label="Resize editor" />
      <div className="ws-mid">
{pdf ? <iframe className="pdfview" title="PDF preview" src={pdf.url} /> : <div className="card empty">Your PDF preview appears here{localOk ? " and updates as you type" : ""}.</div>}
      </div>
      <Splitter props={paneR.props} label="Resize settings" />
      <div className="ws-right">
        <div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Layout & PDF</h2>
          <div className="seg right"><button className={mode === "local" ? "on" : ""} disabled={localOk === false} onClick={() => setMode("local")} title={localOk === false ? "No LaTeX compiler on this server" : ""}>This server</button><button className={mode === "public" ? "on" : ""} onClick={() => setMode("public")}>Public LaTeX service</button></div></div>
          {structured && <TemplateGallery value={template} onChange={(v) => pick("cv-template", v, setTemplate)} />}
          {structured && <div className="row"><select value={paper} onChange={(e) => pick("cv-paper", e.target.value, setPaper)} aria-label="Paper size"><option value="a4">A4</option><option value="letter">US Letter</option></select>
            {localOk && <label className="small row" style={{ gap: 6 }}><input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />Live preview</label>}
            {prevBusy && <span className="small muted">updating…</span>}</div>}
          {prevErr && <div className="small err">{prevErr}</div>}
          {mode === "public" && <label className="notice row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 4 }} />
            <span>Send this CV to a third-party compiler (latex.ytotech.com, then texlive.net as fallback). Your CV contains personal data and leaves this server. Leave unticked to keep it private.</span></label>}
          <div className="row"><button className="btn" disabled={!!busy || (mode === "public" && !consent)} onClick={() => structured ? run("pdf", async () => { const l = await api.post<{ latex: string }>("/cv/latex", { cv: cv.cv, template, paper }); await build(l.latex, "cv"); }) : build(cv.latex, "cv")}>{busy === "pdf" ? "Compiling…" : "Build PDF"}</button>
            {pdf && <a className="btn ghost" href={pdf.url} download="cv.pdf">Download PDF</a>}
            <button className="btn ghost small" onClick={() => download("cv.tex", cv.latex, "text/x-tex")}>.tex</button>
            <button className="btn ghost small" title="Open or continue this CV in Reactive Resume" onClick={() => run("rx", async () => { const j = await api.post<object>("/cv/rx/export", { cv: cv.cv, template, paper }); download("resume-reactive-resume.json", JSON.stringify(j, null, 2), "application/json"); })}>Reactive Resume JSON</button>
            <a className="small" href="https://www.overleaf.com/docs" target="_blank" rel="noreferrer noopener">Overleaf ↗</a></div>
          {pdf && <div className="small muted">Built with {pdf.engine} · {(pdf.bytes / 1024).toFixed(0)} KB</div>}
        </div>
        {structured && <SectionToggles cv={cv.cv} edit={(p) => edit(p as Partial<CvData>)} />}
      </div>
    </div>}
  </div>);
}
