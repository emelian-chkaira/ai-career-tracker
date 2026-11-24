import { useEffect, useRef, useState } from "react";
import { api } from "@/shared/api/client";
import { uget, uset } from "@/shared/lib/userStore";
import { useDocs, useRefreshDocs, foldersOf } from "@/features/fit/api";
import { DocBar } from "./DocBar";
import { ChatPanel } from "./ChatPanel";

const blobUrl = (b64: string) => URL.createObjectURL(new Blob([Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))], { type: "application/pdf" }));
const save = (name: string, href: string) => { const a = document.createElement("a"); a.href = href; a.download = name; a.click(); };

/** The cover-letter section: your letters in folders, an editor, a PDF preview in the look of your CV, and the AI assistant beside them. */
export function LettersWorkspace({ lead, cv, jobId, tone, setTone, generating, onGenerate, incoming, onErr }: {
  lead?: React.ReactNode; cv: Record<string, unknown>; jobId: string; tone: string; setTone(t: string): void; generating: boolean; onGenerate(): void;
  incoming: { text: string; n: number }; onErr(m: string): void;
}) {
  const docs = useDocs("cover"); const refresh = useRefreshDocs(); const list = docs.data ?? [];
  const [id, setId] = useState<number | null>(null); const [text, setText] = useState("");
  const [pdf, setPdf] = useState<{ url: string; kb: number } | null>(null); const [pdfErr, setPdfErr] = useState(""); const [busy, setBusy] = useState(false); const [state, setState] = useState("");
  const [tab, setTab] = useState<"text" | "pdf">("text"); const [copied, setCopied] = useState(false); const dirty = useRef(false); const cur = list.find((d) => d.id === id); const jobNo = jobId ? +jobId : null;
  const guard = async (fn: () => Promise<void>) => { setBusy(true); try { await fn(); } catch (e) { onErr((e as Error).message); } finally { setBusy(false); } };
  const create = async (name: string, body: string, fold: string) => { const d = await api.post<{ id: number }>("/me/docs", { kind: "cover", name, data: { text: body }, folder: fold, job_id: jobNo }); refresh(); return d.id; };
  const open = (n: number) => guard(async () => { const d = await api.get<{ data: { text: string } }>(`/me/docs/${n}`); dirty.current = false; setId(n); setText(d.data.text ?? ""); uset("letter-active", String(n)); });
  // open the letter used last (or the first one) once the list arrives
  useEffect(() => { if (id === null && list.length) { const want = +(uget("letter-active") ?? 0); open((list.find((d) => d.id === want) ?? list[0]).id); } }, [list.length]);   // eslint-disable-line react-hooks/exhaustive-deps
  // a letter generated from "Tailor to a job" arrives as a new document
  useEffect(() => { if (incoming.n > 0 && incoming.text) guard(async () => { const n = await create(`Letter for job ${jobId || "?"}`, incoming.text, cur?.folder ?? ""); dirty.current = false; setId(n); setText(incoming.text); uset("letter-active", String(n)); }); }, [incoming.n]);   // eslint-disable-line react-hooks/exhaustive-deps
  // autosave a second after the last keystroke
  useEffect(() => {
    if (!id || !dirty.current) return; setState("Saving…");
    const t = setTimeout(() => { api.put(`/me/docs/${id}`, { data: { text } }).then(() => { dirty.current = false; setState("Saved"); refresh(); }).catch((e) => setState(`Not saved: ${(e as Error).message}`)); }, 1000);
    return () => clearTimeout(t);
  }, [text, id]);   // eslint-disable-line react-hooks/exhaustive-deps
  // PDF preview in the same look as the CV
  useEffect(() => {
    if (!text.trim()) { setPdf(null); return; }
    let stale = false; const t = setTimeout(async () => {
      try { const r = await api.post<{ pdf_b64: string; bytes: number }>("/cv/letter-pdf", { text, cv, job_id: jobNo }); if (stale) return; setPdfErr(""); setPdf((o) => { if (o) URL.revokeObjectURL(o.url); return { url: blobUrl(r.pdf_b64), kb: Math.round(r.bytes / 1024) }; }); }
      catch (e) { if (!stale) setPdfErr((e as Error).message); }
    }, 900);
    return () => { stale = true; clearTimeout(t); };
  }, [text, jobNo]);   // eslint-disable-line react-hooks/exhaustive-deps
  const edit = (v: string) => { dirty.current = true; setText(v); };
  const newLetter = () => guard(async () => { const n = window.prompt("Name this cover letter", "Cover letter"); if (!n?.trim()) return; const nid = await create(n.trim(), "", cur?.folder ?? ""); dirty.current = false; setId(nid); setText(""); });
  const upload = (files: File[]) => guard(async () => {
    let last = 0; const bad: string[] = [];
    for (const f of files) {
      try { const r = await api.upload<{ text: string }>("/cv/extract-text", f, { filename: f.name }); last = await create(f.name.replace(/\.[^.]+$/, "").slice(0, 80) || "Uploaded letter", r.text, cur?.folder ?? ""); }
      catch (e) { bad.push(`${f.name}: ${(e as Error).message}`); }
    }
    if (last) await open(last); if (bad.length) throw new Error(`Could not read ${bad.join("; ")}`);
  });
  const rename = () => guard(async () => { const n = window.prompt("New name", cur?.name ?? ""); if (cur && n?.trim()) { await api.put(`/me/docs/${cur.id}`, { name: n }); refresh(); } });
  const dup = () => guard(async () => { const n = window.prompt("Name for the copy", `${cur?.name ?? "Letter"} copy`); if (!n?.trim()) return; const nid = await create(n.trim(), text, cur?.folder ?? ""); dirty.current = false; setId(nid); });
  const move = (f: string) => guard(async () => { if (cur) { await api.put(`/me/docs/${cur.id}`, { folder: f }); refresh(); } });
  const del = () => guard(async () => {
    if (!cur || !window.confirm(`Delete “${cur.name}”? This cannot be undone.`)) return; await api.del(`/me/docs/${cur.id}`); refresh();
    const left = list.filter((d) => d.id !== cur.id); if (left.length) await open(left[0].id); else { setId(null); setText(""); uset("letter-active", null); }
  });
  const copyLetter = (body: string, fold: string) => guard(async () => { const nid = await create(`${cur?.name ?? "Letter"} (AI)`, body, fold); dirty.current = false; setId(nid); setText(body); });
  const copy = () => { navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); }).catch(() => onErr("Could not copy: allow clipboard access")); };
  const download = () => { if (pdf) save(`${cur?.name ?? "cover-letter"}.pdf`, pdf.url); };

  return (<div className="stack">
    <DocBar lead={lead} kind="cover" docs={list} selectedId={id} busy={busy} status={state} onSelect={open} onFiles={upload} onNew={newLetter} onRename={rename} onDuplicate={dup} onMove={move} onDelete={del} onPdf={download} />
    <div className="lw">
      <div className="card stack lw-edit">
        <div className="row" style={{ gap: 8 }}>
          <div className="seg" role="tablist" aria-label="Letter view"><button role="tab" aria-selected={tab === "text"} className={tab === "text" ? "on" : ""} onClick={() => setTab("text")}>Text</button>
            <button role="tab" aria-selected={tab === "pdf"} className={tab === "pdf" ? "on" : ""} onClick={() => setTab("pdf")}>PDF</button></div>
          <h2 style={{ margin: 0, fontSize: 16, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={cur?.name}>{cur?.name ?? "Cover letter"}</h2>
          <span className="small muted right">{state}</span></div>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn small" disabled={!text} onClick={copy}>{copied ? "✓ Copied" : "Copy text"}</button>
          <button className="btn ghost small" disabled={!pdf} onClick={download}>⬇ PDF{pdf ? ` (${pdf.kb} KB)` : ""}</button>
          <select value={tone} onChange={(e) => setTone(e.target.value)} aria-label="Tone" className="right"><option value="professional">Professional</option><option value="warm">Warm</option><option value="concise">Concise</option></select>
          <button className="btn ghost small" disabled={!jobId || generating} onClick={onGenerate} title={jobId ? "Write a new letter for the job you opened" : "Open a job first (Tailor to a job)"}>{generating ? "Writing…" : "Generate for job"}</button></div>
        {id === null ? <div className="card empty small">No cover letter yet. Press “+ New”, upload one, or ask the assistant to write it.</div>
          : tab === "text"
            ? <textarea className="lw-text" value={text} onChange={(e) => edit(e.target.value)} aria-label="Cover letter text" placeholder="Write the letter, or tell the assistant what to write." />
            : pdf ? <iframe className="pdfview lw-pdf" title="Cover letter PDF" src={pdf.url + "#view=FitH"} />
              : <div className="card empty small">{pdfErr ? <span className="err">{pdfErr}</span> : text.trim() ? "Building the PDF…" : "Write the letter first; the PDF appears here."}</div>}
        {tab === "text" && pdfErr && <div className="small err">{pdfErr}</div>}
      </div>
      <div className="card"><ChatPanel target="cover" docName={cur?.name ?? ""} cv={cv} letter={text} jobId={jobId} folders={foldersOf(list)}
        applyCv={() => {}} copyCv={() => {}} applyLetter={(t) => { if (id) { dirty.current = true; setText(t); } else guard(async () => { const nid = await create("Cover letter", t, cur?.folder ?? ""); setId(nid); setText(t); }); }} copyLetter={copyLetter} /></div>
    </div></div>);
}
