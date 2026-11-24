import { useRef, useState } from "react";
import { folderLabel, foldersOf, type DocMeta } from "@/features/fit/api";
import { Menu } from "@/features/jobs/Menu";

/** One compact row for a section: pick the document (grouped by folder), upload, and a menu with everything else. Leaves the room to the work area. */
export function DocBar({ lead, kind, docs, selectedId, busy, status, onSelect, onFiles, onNew, onRename, onDuplicate, onMove, onDelete, onDefault, onPdf }: {
  lead?: React.ReactNode; kind: "cv" | "cover"; docs: DocMeta[]; selectedId: number | null; busy: boolean; status: React.ReactNode; onSelect(id: number): void; onFiles?(files: File[]): void; onNew?(): void;
  onRename(): void; onDuplicate(): void; onMove(folder: string): void; onDelete(): void; onDefault?(): void; onPdf(): void;
}) {
  const file = useRef<HTMLInputElement>(null); const [extra, setExtra] = useState<string[]>([]);
  const folders = [...new Set([...foldersOf(docs), ...extra])].sort((a, b) => a.localeCompare(b)); const cur = docs.find((d) => d.id === selectedId); const word = kind === "cv" ? "CV" : "letter";
  const newFolder = () => { const n = window.prompt("Folder name")?.trim(); if (n) { setExtra((x) => [...x, n]); if (cur) onMove(n); } };
  const group = (f: string) => docs.filter((d) => d.folder === f).map((d) => <option key={d.id} value={d.id}>{d.is_default ? "★ " : ""}{d.name}</option>);
  return (<div className="docbar" role="group" aria-label={kind === "cv" ? "Your CVs" : "Your cover letters"}>
    {lead}{lead && <span className="docbar-sep" aria-hidden />}
    <select className="docsel" aria-label={kind === "cv" ? "Your CVs" : "Your cover letters"} value={selectedId ?? ""} disabled={busy || !docs.length} onChange={(e) => onSelect(+e.target.value)}>
      {!docs.length && <option value="">{kind === "cv" ? "No CV yet" : "No letters yet"}</option>}
      {folders.length ? <><optgroup label="Default">{group("")}</optgroup>{folders.map((f) => <optgroup key={f} label={f}>{group(f)}</optgroup>)}</> : group("")}
    </select>
    {cur && <span className="chip plain" style={{ margin: 0 }} title="Folder">{folderLabel(cur.folder)}</span>}
    {kind === "cv" && cur?.is_default && <span className="chip ok" style={{ margin: 0 }} title="AI scoring uses this CV unless you pick another for a job">★ Scoring CV</span>}
    <button className="btn small" disabled={busy} onClick={() => file.current?.click()} title={kind === "cv" ? "Add one or more CVs (PDF, Word, LaTeX, Reactive Resume JSON)" : "Add one or more cover letters (PDF, Word or text)"}>⬆ Upload</button>
    {kind === "cover" && <button className="btn small" disabled={busy} onClick={onNew}>+ New</button>}
    <input ref={file} hidden multiple type="file" accept={kind === "cv" ? ".pdf,.docx,.txt,.tex,.md,.json" : ".pdf,.docx,.txt,.md"} onChange={(e) => { const f = [...(e.target.files ?? [])]; e.target.value = ""; if (f.length) onFiles?.(f); }} />
    {cur && <Menu label="More ▾" className="dmenu">
      <button onClick={onRename}>Rename</button><button onClick={onDuplicate}>Duplicate</button>
      {kind === "cv" && !cur.is_default && <button onClick={onDefault}>★ Use for AI scoring</button>}
      <button onClick={onPdf}>⬇ Download PDF</button>
      <div className="menu-sep">Move to folder</div>
      {["", ...folders].filter((f) => f !== cur.folder).map((f) => <button key={f || "d"} onClick={() => onMove(f)}>{folderLabel(f)}</button>)}
      <button onClick={newFolder}>+ New folder…</button>
      <button className="danger" onClick={onDelete}>Delete {word}</button></Menu>}
    <span className="small muted right">{status}</span>
  </div>);
}
