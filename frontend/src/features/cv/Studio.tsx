import { useEffect, useState } from "react";
import { Modal, Switch } from "@/shared/ui/kit";
import { Field, Tags } from "./bits";
import { RichField, Rich } from "./RichField";
import { withHeading, move, titleOf, type Block } from "./SectionsEditor";

type Cv = { [k: string]: any };
export interface ToolTab { id: string; label: string; icon: string; node: React.ReactNode }
const RAIL: { id: string; label: string; icon: string }[] = [
  { id: "basics", label: "Basics", icon: "👤" }, { id: "summary", label: "Summary", icon: "📝" }, { id: "experience", label: "Experience", icon: "💼" }, { id: "education", label: "Education", icon: "🎓" },
  { id: "projects", label: "Projects", icon: "🧩" }, { id: "skills", label: "Skills", icon: "🛠" }, { id: "languages", label: "Languages", icon: "🌐" }, { id: "profiles", label: "Profiles", icon: "🔗" },
  { id: "certifications", label: "Certificates", icon: "🏅" }, { id: "references", label: "References", icon: "💬" }, { id: "custom", label: "Custom", icon: "➕" }];
const USE: Record<string, string> = { ai: "AI may choose", always: "Always include", exclude: "Never include" };

function ItemModal({ kind, item, onSave, onClose, aiReady }: { kind: string; item: Block; onSave(b: Block): void; onClose(): void; aiReady: boolean }) {
  const [b, setB] = useState<Block>({ ...item, title: item.title ?? titleOf(item) }); const set = (p: Partial<Block>) => setB((x) => ({ ...x, ...p }));
  const L = kind === "projects" ? ["Project name", "Link or stack"] : kind === "education" ? ["Degree / programme", "School"] : ["Role", "Company"];
  return (<Modal open onOpenChange={(o) => !o && onClose()} title={item.title || item.heading ? "Edit item" : "New item"} width={680}
    footer={<><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn" onClick={() => onSave(withHeading({ ...b, bullets: (b.bullets ?? []).map((x) => x.trim()).filter(Boolean) }))}>Save</button></>}>
    <div className="stack">
      <div className="grid two" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Field label={L[0]}><input type="text" value={b.title ?? ""} onChange={(e) => set({ title: e.target.value })} autoFocus /></Field>
        <Field label={L[1]}><input type="text" value={b.place ?? ""} onChange={(e) => set({ place: e.target.value })} /></Field>
        <Field label="Dates"><input type="text" value={b.date ?? ""} placeholder="2021 – 2024" onChange={(e) => set({ date: e.target.value })} /></Field>
        {kind === "projects" && <Field label="Tech"><input type="text" value={b.tech ?? ""} onChange={(e) => set({ tech: e.target.value })} /></Field>}</div>
      {kind !== "education" && <RichField label="Description" value={b.desc ?? ""} rows={3} kind="description" aiReady={aiReady} onChange={(v) => set({ desc: v })} help="Use B for bold and the link button for links; both show in the PDF." />}
      <RichField label="Bullets (one per line)" value={(b.bullets ?? []).join("\n")} rows={5} kind="bullet list" aiReady={aiReady} onChange={(v) => set({ bullets: v.split("\n") })} />
      {kind === "projects" && <Field label="When AI tailors this CV to a job"><select value={b.use ?? "ai"} onChange={(e) => set({ use: e.target.value as Block["use"] })}>{Object.entries(USE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>}
      <Switch checked={!b.hidden} onChange={(v) => set({ hidden: !v })} label="Visible in the PDF" />
    </div></Modal>);
}

function ItemList({ kind, list, onChange, aiReady, label }: { kind: string; list: Block[]; onChange(l: Block[]): void; aiReady: boolean; label: string }) {
  const [editing, setEditing] = useState<number | null>(null); const [drag, setDrag] = useState<number | null>(null);
  const blank = withHeading({ title: "", place: "", date: "", bullets: [] });
  return (<div className="stack" style={{ gap: 10 }}>
    <div className="row"><h2 style={{ margin: 0 }}>{label}</h2><span className="chip plain">{list.length}</span><button className="btn small right" onClick={() => setEditing(list.length)}>+ Add</button></div>
    {!list.length && <div className="card empty small">Nothing here yet. Press Add to create your first entry.</div>}
    <ul className="plain stack" style={{ gap: 8 }}>{list.map((b, i) => <li key={i} className={"irow" + (b.hidden ? " off" : "")} draggable onDragStart={() => setDrag(i)} onDragOver={(e) => drag !== null && e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); if (drag !== null && drag !== i) onChange(move(list, drag, i)); setDrag(null); }}>
      <span className="grip" aria-hidden title="Drag to reorder">⋮⋮</span>
      <div className="irow-main"><b>{titleOf(b) || `New ${label.toLowerCase()} entry`}</b><div className="small muted">{[b.place?.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1"), b.date].filter(Boolean).join(" · ") || "No details yet"}</div>
        {b.desc && <div className="small irow-d"><Rich text={b.desc} /></div>}</div>
      {b.hidden ? <span className="chip plain" style={{ margin: 0 }}>Hidden in PDF</span> : null}
      {kind === "projects" && b.use && b.use !== "ai" && <span className="chip plain" style={{ margin: 0 }}>{USE[b.use]}</span>}
      <span className="eblock-acts"><button className="kicon" onClick={() => setEditing(i)} aria-label="Edit" title="Edit">✎</button>
        <button className="kicon" onClick={() => onChange(list.map((x, j) => (j === i ? { ...x, hidden: !x.hidden } : x)))} aria-label={b.hidden ? "Show" : "Hide"} title={b.hidden ? "Show in PDF" : "Hide from PDF"}>{b.hidden ? "🙈" : "👁"}</button>
        <button className="kicon" onClick={() => onChange([...list.slice(0, i + 1), { ...b }, ...list.slice(i + 1)])} aria-label="Duplicate" title="Duplicate">⧉</button>
        <button className="kicon" onClick={() => onChange(list.filter((_, j) => j !== i))} aria-label="Delete" title="Delete">🗑</button></span></li>)}</ul>
    {editing !== null && <ItemModal kind={kind} item={list[editing] ?? blank} aiReady={aiReady} onClose={() => setEditing(null)} onSave={(nb) => { onChange(editing >= list.length ? [...list, nb] : list.map((x, j) => (j === editing ? nb : x))); setEditing(null); }} />}
  </div>);
}

/** One section at a time, picked from an icon rail. Entries are edited in a dialog with rich text and per-field AI. */
export function Studio({ cv, edit, setSkills, aiReady, tools, startTab, focus }: { cv: Cv; edit(p: Record<string, unknown>): void; setSkills(v: string[]): void; aiReady: boolean; tools: ToolTab[]; startTab?: string; focus?: { tab: string; n: number } }) {
  const [tab, setTab] = useState(startTab ?? "experience"); useEffect(() => { if (focus && focus.n > 0) setTab(focus.tab); }, [focus?.n]);   // eslint-disable-line react-hooks/exhaustive-deps
   const all = [...RAIL, ...tools.map((t) => ({ id: "t:" + t.id, label: t.label, icon: t.icon }))];
  const ensure = (k: string) => ({ order: [...new Set([...(cv.order ?? []), k])] });
  const list = (k: string) => (cv[k] as Block[] | undefined) ?? [];
  const extras: { title: string; blocks: Block[] }[] = cv.extras ?? [];
  const view = (() => {
    switch (tab) {
      case "basics": return (<div className="stack"><h2 style={{ margin: 0 }}>Basics</h2><div className="grid two" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {(["name", "email", "phone", "location"] as const).map((k) => <Field key={k} label={k[0].toUpperCase() + k.slice(1)}><input type="text" value={cv[k] ?? ""} onChange={(e) => edit({ [k]: e.target.value })} /></Field>)}</div>
        <div className="small muted">A profile picture is not supported yet: the PDF layouts are text-only so they pass applicant-tracking systems.</div></div>);
      case "summary": return <div className="stack"><h2 style={{ margin: 0 }}>Summary</h2><RichField label="Summary" value={cv.summary ?? ""} rows={6} kind="summary" aiReady={aiReady} onChange={(v) => edit({ summary: v })} /></div>;
      case "experience": case "education": case "projects": return <ItemList kind={tab} label={RAIL.find((r) => r.id === tab)!.label} list={list(tab)} aiReady={aiReady} onChange={(l) => edit({ [tab]: l, ...ensure(tab) })} />;
      case "skills": return <div className="stack"><h2 style={{ margin: 0 }}>Skills</h2><Tags items={cv.skills ?? []} onChange={setSkills} placeholder="Add a skill, press Enter" /></div>;
      case "languages": return <div className="stack"><h2 style={{ margin: 0 }}>Languages</h2><Tags items={cv.languages ?? []} onChange={(v) => edit({ languages: v })} placeholder="e.g. Arabic: native, press Enter" /></div>;
      case "certifications": return <div className="stack"><h2 style={{ margin: 0 }}>Certificates</h2><Tags items={cv.certifications ?? []} onChange={(v) => edit({ certifications: v })} placeholder="Add a certificate" /></div>;
      case "references": return <div className="stack"><h2 style={{ margin: 0 }}>References</h2><Tags items={cv.references ?? []} onChange={(v) => edit({ references: v, ...ensure("references") })} placeholder="Name, role, organisation" /></div>;
      case "profiles": return <div className="stack"><h2 style={{ margin: 0 }}>Profiles & links</h2><Tags items={cv.links ?? []} onChange={(v) => edit({ links: v })} placeholder="https://github.com/you, press Enter" /><div className="small muted">LinkedIn, GitHub, portfolio. They appear in the header of the PDF.</div></div>;
      case "custom": return (<div className="stack"><div className="row"><h2 style={{ margin: 0 }}>Custom sections</h2><button className="btn small right" onClick={() => { const t = window.prompt("Name of the new section (e.g. Volunteering)"); if (t?.trim()) edit({ extras: [...extras, { title: t.trim(), blocks: [] }], order: [...(cv.order ?? []), "x:" + t.trim()] }); }}>+ Add section</button></div>
        {!extras.length && <div className="card empty small">Add sections such as Volunteering, Publications or Awards.</div>}
        {extras.map((x, i) => <div key={x.title} className="card" style={{ boxShadow: "none" }}><ItemList kind="custom" label={x.title} list={x.blocks} aiReady={aiReady} onChange={(l) => edit({ extras: extras.map((e, j) => (j === i ? { ...e, blocks: l } : e)) })} />
          <button className="btn ghost small" style={{ marginTop: 8 }} onClick={() => edit({ extras: extras.filter((_, j) => j !== i), order: (cv.order ?? []).filter((o: string) => o !== "x:" + x.title) })}>Remove section</button></div>)}</div>);
      default: return tools.find((t) => "t:" + t.id === tab)?.node ?? null;
    }
  })();
  return (<div className="rstudio"><nav className="rail" aria-label="CV sections">{all.map((r) => <button key={r.id} className={"rail-i" + (tab === r.id ? " on" : "")} onClick={() => setTab(r.id)} title={r.label} aria-label={r.label} aria-current={tab === r.id}><span aria-hidden>{r.icon}</span><em>{r.label}</em></button>)}</nav>
    <div className="rview"><div key={tab} className="rpane">{view}</div></div></div>);
}
