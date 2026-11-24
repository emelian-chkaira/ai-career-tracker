import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/shared/api/client";
import { uget, uset } from "@/shared/lib/userStore";
import { useAuth } from "@/features/auth/AuthContext";
import { useDocs, useRefreshDocs, foldersOf, type DocMeta } from "@/features/fit/api";
import { DocBar } from "./DocBar";
import { LettersWorkspace } from "./LettersWorkspace";
import { ChatPanel } from "./ChatPanel";
import { Panel, usePane, Splitter } from "@/shared/ui/kit";
import { Studio } from "./Studio";
import { TemplateGallery } from "./Gallery";
import { SectionToggles } from "./SectionsEditor";
import { RrPanel } from "./RrPanel";
import { GapsPanel } from "./GapsPanel";
import { useAiSettings } from "@/features/ai/AiPanel";

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
  const [cv, setCvState] = useState<Extracted | null>(load); const [docId, setDocId] = useState<number | null>(null); const [focus] = useState<{ tab: string; n: number }>({ tab: "experience", n: 0 }); const [tailored, setTailored] = useState<Tailored | null>(null);
  const [pdf, setPdf] = useState<{ url: string; engine: string; bytes: number } | null>(null);
  const [busy, setBusy] = useState(""); const [err, setErr] = useState(""); const [tone, setTone] = useState("professional");
  const [mode, setMode] = useState<Mode>("local"); const [consent, setConsent] = useState(false); const [localOk, setLocalOk] = useState<boolean | null>(null);
  const [aiOk, setAiOk] = useState(false); const [aiConsent, setAiConsent] = useState(false); const [ai, setAi] = useState<AiOut | null>(null);
  const [section, setSection] = useState<"cv" | "cover">("cv"); const [rtab, setRtab] = useState<"ai" | "layout">("ai"); const [incoming, setIncoming] = useState({ text: "", n: 0 });
  const [over, setOver] = useState(false); const fileRef = useRef<HTMLInputElement>(null); const [dirty, setDirty] = useState(false);

  useEffect(() => { api.get<{ local: boolean; ai: boolean }>("/cv/compilers").then((r) => { setLocalOk(r.local); setAiOk(r.ai); if (!r.local) setMode("public"); }).catch(() => setLocalOk(false)); }, []);
  const { user } = useAuth(); const docsQ = useDocs("cv", !!user); const refreshDocs = useRefreshDocs();
  const [template, setTemplate] = useState(() => uget("cv-template") ?? "mine");
  const [paper, setPaper] = useState(() => uget("cv-paper") ?? "a4");
  const [live, setLive] = useState(true); const [prevBusy, setPrevBusy] = useState(false); const [prevErr, setPrevErr] = useState("");
  const pick = (k: string, v: string, set: (x: string) => void) => { set(v); uset(k, v); };
  // The account's CVs live on the server (CV Studio library): open the one used last, then save every change a second after the last edit.
  const [synced, setSynced] = useState(!user); const [saveErr, setSaveErr] = useState("");
  const openData = (id: number, d: Extracted & { template?: string; paper?: string }) => { const { template: t, paper: pp, ...rest } = d; setDocId(id); uset("cv-active", String(id)); setCvState(rest.cv ? rest : null); save(rest.cv ? rest : null); setTailored(null); setPdf(null); setAi(null); setDirty(false); if (t) { setTemplate(t); uset("cv-template", t); } if (pp) { setPaper(pp); uset("cv-paper", pp); } };
  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const { docs } = await api.get<{ docs: DocMeta[] }>("/me/docs", { kind: "cv" }); const want = +(uget("cv-active") ?? 0);
        const d = docs.find((x) => x.id === want) ?? docs.find((x) => x.is_default) ?? docs[0];
        if (d) { const r = await api.get<{ data: Extracted & { template?: string; paper?: string } }>(`/me/docs/${d.id}`); openData(d.id, r.data); }
      } catch (e) { setSaveErr(`CV library unavailable (${(e as Error).message.slice(0, 80)}). Restart the backend so it has the latest version.`); } finally { setSynced(true); }
    })();
  }, [user?.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const payload = () => ({ ...cv!, template, paper });
  const saveNow = async () => { if (!user || !cv || !synced) return; if (docId) await api.put(`/me/docs/${docId}`, { data: payload() }); };
  useEffect(() => {
    if (!user || !synced || !cv) return;
    const t = setTimeout(() => {
      const req = docId ? api.put(`/me/docs/${docId}`, { data: payload() }) : api.post<{ id: number }>("/me/docs", { kind: "cv", name: cv.cv.name ? `${cv.cv.name} CV` : "My CV", data: payload() }).then((r) => { setDocId(r.id); uset("cv-active", String(r.id)); refreshDocs(); });
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
  const upload = (files: File[]) => run("upload", async () => {
    await saveNow().catch(() => undefined);                      // the CV you are leaving is saved first
    let last: { id: number; r: Extracted } | null = null; const bad: string[] = [];
    for (const f of files) {
      try {
        const r = await api.upload<Extracted>("/cv/extract", f, { filename: f.name });
        if (user) { const d = await api.post<{ id: number }>("/me/docs", { kind: "cv", name: f.name.replace(/\.[^.]+$/, "").slice(0, 80) || "Uploaded CV", folder: cur?.folder ?? "", data: { ...r, template, paper } }); last = { id: d.id, r }; }
        else last = { id: 0, r };
      } catch (e) { bad.push(`${f.name}: ${(e as Error).message}`); }
    }
    if (last) { if (last.id) { openData(last.id, { ...last.r, template, paper }); refreshDocs(); } else { setCv(last.r); setTailored(null); setPdf(null); setAi(null); setDirty(false); } }
    if (bad.length) throw new Error(`Could not read ${bad.join("; ")}`);
  });
  const openDoc = (id: number) => run("open", async () => { await saveNow().catch(() => undefined); const r = await api.get<{ data: Extracted & { template?: string; paper?: string } }>(`/me/docs/${id}`); openData(id, r.data); refreshDocs(); });
  const cur = (docsQ.data ?? []).find((d) => d.id === docId);
  const renameDoc = () => run("doc", async () => { const n = window.prompt("New name for this CV", cur?.name ?? ""); if (docId && n?.trim()) { await api.put(`/me/docs/${docId}`, { name: n }); refreshDocs(); } });
  const dupDoc = () => run("doc", async () => { const n = window.prompt("Name for the copy", `${cur?.name ?? "CV"} copy`); if (!cv || !n?.trim()) return; const d = await api.post<{ id: number }>("/me/docs", { kind: "cv", name: n, data: payload() }); setDocId(d.id); uset("cv-active", String(d.id)); refreshDocs(); });
  const delDoc = () => run("doc", async () => {
    if (!docId || !window.confirm(`Delete “${cur?.name}”? This cannot be undone.`)) return;
    await api.del(`/me/docs/${docId}`); const left = (docsQ.data ?? []).filter((d) => d.id !== docId); refreshDocs();
    if (left.length) { const next = left.find((d) => d.is_default) ?? left[0]; const r = await api.get<{ data: Extracted & { template?: string; paper?: string } }>(`/me/docs/${next.id}`); openData(next.id, r.data); }
    else { setDocId(null); uset("cv-active", null); setCv(null); }
  });
  const defDoc = () => run("doc", async () => { if (!docId) return; await saveNow(); await api.post(`/me/docs/${docId}/default`); refreshDocs(); });
  const moveDoc = (f: string) => run("doc", async () => { if (docId) { await api.put(`/me/docs/${docId}`, { folder: f }); refreshDocs(); } });
  const saveAs = (name: string, href: string) => { const a = document.createElement("a"); a.href = href; a.download = name; a.click(); };
  const cvPdf = () => run("pdf", async () => { if (pdf) return saveAs(`${cur?.name ?? "cv"}.pdf`, pdf.url); const r = await api.post<PdfOut>("/cv/preview", { cv: cv!.cv, template, paper }); saveAs(`${cur?.name ?? "cv"}.pdf`, URL.createObjectURL(new Blob([Uint8Array.from(atob(r.pdf_b64), (c) => c.charCodeAt(0))], { type: "application/pdf" }))); });
  const copyCv = (n: Record<string, unknown>, fold: string) => run("doc", async () => { await saveNow().catch(() => undefined); const d = await api.post<{ id: number }>("/me/docs", { kind: "cv", name: `${cur?.name ?? "CV"} (AI)`, folder: fold, data: { ...cv!, cv: n, template, paper } }); refreshDocs(); openData(d.id, { ...cv!, cv: n as CvData, template, paper }); });
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
  const cover = () => run("letter", async () => { const t = (await api.post<{ text: string }>("/cv/cover-letter", { cv: cv!.cv, job_id: +jobId, tone })).text; setIncoming((x) => ({ text: t, n: x.n + 1 })); setSection("cover"); });
  const download = (name: string, data: BlobPart, type: string) => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([data], { type })); a.download = name; a.click(); };
  const step = !cv ? 1 : tailored ? 4 : 2;

  const aiSet = useAiSettings(); const paneL = usePane("cv-left", 500, 340, 760); const paneR = usePane("cv-right2", 360, 280, 520, -1);
  const latexNode = cv ? (<Panel id="cv-details" title="LaTeX source"><div className="stack"><div className="row"><h2 style={{ margin: 0 }}>LaTeX</h2><span className="chip plain">{cv.source ?? "text"}</span></div>
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
  </>);
  const chatNode = <ChatPanel target="cv" docName={cur?.name ?? ""} cv={(cv?.cv ?? {}) as Record<string, unknown>} letter="" jobId={jobId} folders={foldersOf(docsQ.data ?? [])}
    applyCv={(n) => { if (cv) { setCv({ ...cv, cv: n as CvData }); setDirty(true); } }} copyCv={copyCv} applyLetter={() => {}} copyLetter={() => {}} />;
  const tools = [{ id: "gaps", label: "Missing keywords", icon: "🧭", node: <GapsPanel cv={cv?.cv ?? {}} jobId={jobId} edit={(p) => edit(p as Partial<CvData>)} /> }, { id: "tailor", label: "Tailor to a job", icon: "🎯", node: tailorNode }, { id: "rr", label: "Reactive Resume", icon: "♻", node: <RrPanel cv={cv?.cv} template={template} paper={paper} onImport={(c) => { setCv({ cv: c as CvData, latex: "", source: "reactive-resume" }); setDirty(true); }} /> }, { id: "latex", label: "LaTeX", icon: "∑", node: latexNode }];

  const segNode = <div className="seg" role="tablist" aria-label="Section"><button role="tab" aria-selected={section === "cv"} className={section === "cv" ? "on" : ""} onClick={() => setSection("cv")}>CVs</button>
        <button role="tab" aria-selected={section === "cover"} className={section === "cover" ? "on" : ""} onClick={() => setSection("cover")}>Cover letters</button></div>;
  const noCv = section === "cv" && !cv;
  const saveText = saveErr ? <span className="bad">Not saved: {saveErr}</span> : synced ? "Saved to your account" : "Loading your CVs…";
  return (<div className={"stack" + (cv && section === "cv" ? " cvfull" : "")}>
    {!user && <div className="docbar">{segNode}</div>}
    {noCv && <><div className="muted">Import your CV (PDF, Word, LaTeX or Reactive Resume JSON), fix what the parser got wrong, watch the PDF update as you edit, and export. {user ? "Your CVs are saved, encrypted, to your account only: another account on this computer never sees them." : "Without an account the draft stays in this browser only; sign in to keep it in your account."}</div>
    <div className="steps">{["Import", "Review", "Tailor to a job", "Export PDF"].map((s, i) => <div key={s} className={"step" + (step === i + 1 ? " on" : step > i + 1 ? " done" : "")}><b>{step > i + 1 ? "✓" : i + 1}</b>{s}</div>)}</div></>}
    {err && <div className="notice err">{err}</div>}
    {section === "cover" && <LettersWorkspace lead={segNode} cv={(cv?.cv ?? {}) as Record<string, unknown>} jobId={jobId} tone={tone} setTone={setTone} generating={busy === "letter"} onGenerate={cover} incoming={incoming} onErr={setErr} />}
    {section === "cv" && user && <DocBar lead={segNode} kind="cv" docs={docsQ.data ?? []} selectedId={docId} busy={!!busy} status={saveText} onSelect={openDoc} onFiles={upload}
      onRename={renameDoc} onDuplicate={dupDoc} onMove={moveDoc} onDelete={delDoc} onDefault={defDoc} onPdf={cvPdf} />}
    {noCv && <div className={"drop" + (over ? " over" : "")} onClick={() => fileRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = [...e.dataTransfer.files]; if (f.length) upload(f); }}>
      <div style={{ fontSize: 34 }}>📄</div><h2>{busy === "upload" ? "Reading your CV…" : "Drop your CVs here or click to browse"}</h2><div className="muted">PDF, DOCX, LaTeX (.tex), Reactive Resume JSON or plain text · max 3 MB each · several files at once</div>
      <input ref={fileRef} hidden multiple type="file" accept=".pdf,.docx,.txt,.tex,.md,.json" onChange={(e) => { const f = [...(e.target.files ?? [])]; e.target.value = ""; if (f.length) upload(f); }} /></div>}
    {cv && section === "cv" && <div className="ws" style={{ "--wl": `${paneL.width}px`, "--wr": `${paneR.width}px` } as React.CSSProperties}>
      <div className="ws-left">
        {structured ? <Studio key={docId ?? "new"} cv={cv.cv} edit={(p) => edit(p as Partial<CvData>)} setSkills={setSkills} aiReady={!!aiSet.data?.provider} tools={tools} focus={focus} /> : <>{latexNode}{tailorNode}</>}
      </div>

      <Splitter props={paneL.props} label="Resize editor" />
      <div className="ws-mid">
{pdf ? <iframe className="pdfview" title="PDF preview" src={pdf.url + "#view=FitH&toolbar=1"} /> : <div className="card empty">Your PDF preview appears here{localOk ? " and updates as you type" : ""}.</div>}
      </div>
      <Splitter props={paneR.props} label="Resize settings" />
      <div className="ws-right">
        <div className="seg rtabs" role="tablist" aria-label="Side panel"><button role="tab" aria-selected={rtab === "ai"} className={rtab === "ai" ? "on" : ""} onClick={() => setRtab("ai")}>✨ AI</button><button role="tab" aria-selected={rtab === "layout"} className={rtab === "layout" ? "on" : ""} onClick={() => setRtab("layout")}>Layout & PDF</button></div>
        {rtab === "ai" && <div className="card">{chatNode}</div>}
        {rtab === "layout" && <><div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Layout & PDF</h2>
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
        {structured && <SectionToggles cv={cv.cv} edit={(p) => edit(p as Partial<CvData>)} />}</>}
      </div>
    </div>}
  </div>);
}
