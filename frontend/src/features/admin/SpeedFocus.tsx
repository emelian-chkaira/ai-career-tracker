import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { label } from "@/shared/lib/format";
import { ActionButton, num, useNotify } from "./ui";

const IT = ["mobile", "frontend", "backend", "fullstack", "software", "data", "devops", "security", "qa", "embedded"];
const EXTRA = ["design", "product"];
type Mode = "auto" | "manual" | "all";
type Policy = { keep_domains: string[]; keep_sectors: string[]; saved_domains: string[]; saved_sectors: string[]; fields_mode: Mode; derived: { sectors: string[]; domains: string[]; users: number }; max_job_age_days: number; delete_expired_after_days: number; by_domain: Record<string, number>; by_sector: Record<string, number> };
const MODES: [Mode, string, string][] = [
  ["auto", "Personalised", "Worked out from what each account chose in setup and what its CV says. A mobile developer gets mobile and software jobs, an architect gets architecture jobs."],
  ["manual", "Manual", "Pick the fields yourself."],
  ["all", "Everything", "Collect every field."]];

/** What to collect. Default: personalised from the accounts' profiles and CVs; nothing outside those fields is stored, and employers that only post other kinds of jobs are visited about once a week. */
export function FocusCard({ isAdmin }: { isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  const q = useQuery({ queryKey: ["admin-policy"], queryFn: () => api.get<Policy>("/admin/policy") });
  const [mode, setMode] = useState<Mode | null>(null); const [doms, setDoms] = useState<string[]>([]); const [secs, setSecs] = useState<string[]>([]); const [find, setFind] = useState("");
  useEffect(() => { if (q.data && mode === null) { setMode(q.data.fields_mode); setDoms(q.data.saved_domains); setSecs(q.data.saved_sectors); } }, [q.data, mode]);
  if (!q.data || mode === null) return <div className="card muted">Loading…</div>;
  const p = q.data; const d = p.derived;
  const same = (a: string[], b: string[]) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
  const dirty = mode !== p.fields_mode || (mode === "manual" && (!same(doms, p.saved_domains) || !same(secs, p.saved_sectors)));
  const tog = (l: string[], set: (v: string[]) => void, x: string) => set(l.includes(x) ? l.filter((y) => y !== x) : [...l, x]);
  const save = async () => { await api.put("/admin/policy", { keep_domains: doms, keep_sectors: secs, fields_mode: mode, max_job_age_days: p.max_job_age_days, delete_expired_after_days: p.delete_expired_after_days }); await qc.invalidateQueries({ queryKey: ["admin-policy"] }); await qc.invalidateQueries({ queryKey: ["admin-pipeline"] }); notify(mode === "all" ? "Saved. Every field is stored." : "Saved. From the next scan only your fields are stored.", "ok"); };
  const fit = (x: string) => !find.trim() || label(x).toLowerCase().includes(find.trim().toLowerCase());
  const sectors = Object.keys({ ...p.by_sector, tech: 1, architecture: 1, engineering: 1, design: 1, finance: 1, sales_marketing: 1, operations: 1, healthcare: 1, education: 1, people_legal: 1, hospitality_retail: 1 }).filter((x) => x !== "other");
  const chips = (l: string[]) => l.length ? l.map((x) => <span key={x} className="chip plain">{label(x)}</span>) : <span className="muted small">everything</span>;
  return (<div className="card stack">
    <div className="row"><h2 style={{ margin: 0 }}>What to collect</h2><span className={`chip ${mode === "all" ? "warn" : "ok"} right`}>{MODES.find((m) => m[0] === mode)![1]}</span></div>
    <div className="row" style={{ gap: 6 }}>{MODES.map(([k, t]) => <button key={k} className={"btn small" + (mode === k ? "" : " ghost")} disabled={!isAdmin} onClick={() => setMode(k)}>{t}</button>)}
      {mode === "manual" && <button className="btn ghost small" disabled={!isAdmin || (!doms.length && !secs.length)} onClick={() => { setDoms([]); setSecs([]); }}>Clear filters</button>}</div>
    <div className="small muted">{MODES.find((m) => m[0] === mode)![2]}</div>
    {mode === "auto" && <div className="stack" style={{ gap: 6 }}>
      <div className="small muted">{d.users ? `From ${d.users} account${d.users > 1 ? "s" : ""} with a profile or CV:` : "No account has a profile or CV yet, so everything is collected for now."}</div>
      <div className="row" style={{ gap: 4, flexWrap: "wrap" }}><span className="small muted">Fields</span>{chips(d.sectors)}</div>
      {d.sectors.includes("tech") && <div className="row" style={{ gap: 4, flexWrap: "wrap" }}><span className="small muted">IT areas</span>{chips(d.domains)}</div>}
      <div className="small muted">Update your profile or upload a CV and this follows within a couple of minutes.</div></div>}
    {mode === "manual" && <div className="stack" style={{ gap: 8 }}>
      <input type="search" placeholder="Search fields…" value={find} onChange={(e) => setFind(e.target.value)} aria-label="Search fields" style={{ width: 200 }} />
      <div><div className="small muted" style={{ marginBottom: 4 }}>Fields of work</div><div className="domgrid">{sectors.filter(fit).map((x) => <label key={x} className={secs.includes(x) ? "on" : ""}><input type="checkbox" disabled={!isAdmin} checked={secs.includes(x)} onChange={() => tog(secs, setSecs, x)} />{label(x)}<span className="muted small"> {num(p.by_sector[x] ?? 0)}</span></label>)}</div></div>
      <div><div className="small muted" style={{ marginBottom: 4 }}>IT areas (when “tech” is ticked; none ticked = all)</div><div className="domgrid">{[...IT, ...EXTRA].filter(fit).map((x) => <label key={x} className={doms.includes(x) ? "on" : ""}><input type="checkbox" disabled={!isAdmin} checked={doms.includes(x)} onChange={() => tog(doms, setDoms, x)} />{label(x)}<span className="muted small"> {num(p.by_domain[x] ?? 0)}</span></label>)}</div></div></div>}
    {isAdmin ? <div className="row"><ActionButton className="btn" disabled={!dirty} run={save}>Save</ActionButton>{dirty && <button className="btn ghost" onClick={() => { setMode(p.fields_mode); setDoms(p.saved_domains); setSecs(p.saved_sectors); }}>Undo</button>}{dirty && <span className="small warn">unsaved</span>}</div> : <div className="small muted">Only admins can change this.</div>}
  </div>);
}

type Perf = { browser_slots: number; scan_threads: number; page_wait_ms: number; ats_first: boolean; internship_pass: boolean; parallel: number; defaults: { browser_slots: number; scan_threads: number; page_wait_ms: number } };
type Sched = Record<string, unknown> & { parallel: number };

/** How hard the crawler works. Applied by the running worker within seconds, no restart. */
export function SpeedCard({ isAdmin }: { isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  const q = useQuery({ queryKey: ["admin-perf"], queryFn: () => api.get<Perf>("/admin/perf") });
  const [v, setV] = useState<Perf | null>(null);
  useEffect(() => { if (q.data && !v) setV(q.data); }, [q.data, v]);
  if (!v || !q.data) return <div className="card muted">Loading…</div>;
  const set = (p: Partial<Perf>) => setV({ ...v, ...p });
  const dirty = JSON.stringify(v) !== JSON.stringify(q.data);
  const save = async () => {
    const r = await api.put<Perf>("/admin/perf", v);
    if (v.parallel !== q.data!.parallel) { const s = await api.get<Sched>("/admin/schedule"); await api.put("/admin/schedule", { ...s, parallel: v.parallel }); }
    setV({ ...r, parallel: v.parallel }); await qc.invalidateQueries({ queryKey: ["admin-perf"] }); await qc.invalidateQueries({ queryKey: ["admin-schedule"] }); notify("Saved. The worker uses it within a few seconds.", "ok");
  };
  const row = (text: string, value: number, unit: string, min: number, max: number, on: (n: number) => void, hint: string, step = 1) => (<label className="small"><div className="row" style={{ justifyContent: "space-between" }}><span>{text}</span><b>{value}{unit}</b></div>
    <input type="range" min={min} max={max} step={step} value={value} disabled={!isAdmin} onChange={(e) => on(+e.target.value)} style={{ width: "100%" }} /><span className="muted">{hint}</span></label>);
  return (<div className="card stack">
    <div className="row"><h2 style={{ margin: 0 }}>Speed</h2><span className="small muted right">changes apply without a restart</span></div>
    {row("Browser windows at once", v.browser_slots, "", 1, 12, (n) => set({ browser_slots: n }), "Pages that need a real browser. Each uses roughly 300 MB of memory. More windows, faster scans.")}
    {row("Career sites read at once (automatic)", v.parallel, "", 1, 40, (n) => set({ parallel: n }), "How many employers the worker reads in parallel while it runs on its own.")}
    {row("Threads for manual tasks", v.scan_threads, "", 1, 40, (n) => set({ scan_threads: n }), "Used by “Scan…” tasks you start from the Tasks page.")}
    {row("Wait for a page to settle", v.page_wait_ms / 1000, " s", 0.5, 15, (n) => set({ page_wait_ms: Math.round(n * 1000) }), "Shorter is faster, but slow career pages may be read before their jobs appear.", 0.5)}
    <label className="row small"><input type="checkbox" disabled={!isAdmin} checked={v.ats_first} onChange={(e) => set({ ats_first: e.target.checked })} /> Read employers with a job-system feed first (fast)</label>
    <label className="row small"><input type="checkbox" disabled={!isAdmin} checked={v.internship_pass} onChange={(e) => set({ internship_pass: e.target.checked })} /> Weekly extra pass for internship pages (slow; skipped for employers with no jobs)</label>
    {isAdmin ? <div className="row"><ActionButton className="btn" disabled={!dirty} run={save}>Save speed</ActionButton>{dirty && <button className="btn ghost" onClick={() => setV(q.data!)}>Undo</button>}
      <ActionButton className="btn ghost" run={async () => { await api.del("/admin/perf"); setV(null); await qc.invalidateQueries({ queryKey: ["admin-perf"] }); notify("Back to the defaults.", "ok"); }}>Defaults</ActionButton></div> : <div className="small muted">Only admins can change this.</div>}
  </div>);
}
