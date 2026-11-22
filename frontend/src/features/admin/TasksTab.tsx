import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { ActionButton, ago, num, useNotify } from "./ui";

type Task = { id: number; kind: string; status: string; progress?: Record<string, unknown>; error?: string | null; created_at: string; finished_at?: string | null };
type Def = { kind: string; title: string; what: string; note?: string };
/** Every task you can start by hand, in three groups. Short lines: the longer explanation sits in the tooltip. */
export const GROUPS: { title: string; items: Def[] }[] = [
  { title: "Find employers", items: [
    { kind: "discover", title: "Discover companies", what: "From free public sources" },
    { kind: "census", title: "Find job-system boards", what: "Employers on public ATS boards" },
    { kind: "internships", title: "Find internships", what: "Student and graduate pages" }] },
  { title: "Read jobs", items: [
    { kind: "scan_unscanned", title: "Scan new companies", what: "Only those never visited" },
    { kind: "scan_all", title: "Re-scan everything", what: "Every careers page, slow", note: "The worker already does this continuously on its schedule." },
    { kind: "board_search", title: "Search job boards", what: "LinkedIn, Indeed, Glassdoor, Bayt…", note: "Experimental: via JobSpy, needs CAREERS_BOARD_SITES, and is against those sites' terms. Open the Job boards tab to choose keywords first." }] },
  { title: "Keep tidy", items: [
    { kind: "dedupe_jobs", title: "Merge duplicate jobs", what: "One role, one job", note: "Folds the same role from other cities, links or boards into one and fixes link-label titles. Also runs daily." },
    { kind: "sponsors_refresh", title: "Refresh sponsor list", what: "IND register, re-check companies" },
    { kind: "logos", title: "Fetch logos", what: "For the job cards" },
    { kind: "embed", title: "Build search vectors", what: "For smart search" }] },
];

function progressText(t: Task) {
  const p = t.progress ?? {}; const done = Number(p.done ?? 0), total = Number(p.total ?? 0);
  if (t.error) return t.error;
  if (total) return `${num(done)} / ${num(total)}${p.new_jobs ? ` · ${num(Number(p.new_jobs))} new jobs` : ""}`;
  const e = Object.entries(p).filter(([, v]) => typeof v === "number" || typeof v === "string").slice(0, 3).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`); return e.join(" · ");
}

export function TasksPanel() {
  const qc = useQueryClient(); const notify = useNotify(); const [all, setAll] = useState(false);
  const tasks = useQuery({ queryKey: ["admin-tasks"], refetchInterval: 4000, queryFn: () => api.get<Task[]>("/admin/tasks") });
  const run = async (t: Def) => { const r = await api.post<{ id: number }>("/admin/tasks", { kind: t.kind }); notify(`Queued “${t.title}” (#${r.id}). The worker starts it within seconds.`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); };
  const items = tasks.data ?? []; const shown = all ? items : items.slice(0, 8);
  const active = items.filter((t) => t.status === "queued" || t.status === "running" || t.status === "paused").length;
  return (
    <div className="stack">
      <div className="card tgroups">{GROUPS.map((g) => <section key={g.title}><h3>{g.title}</h3>
        {g.items.map((t) => <div key={t.kind} className="trow" title={t.note}><div><b>{t.title}</b><span className="small muted">{t.what}</span></div><ActionButton className="btn ghost small" run={() => run(t)}>Run</ActionButton></div>)}</section>)}</div>
      <div className="card stack">
        <div className="row"><h2 style={{ margin: 0 }}>History</h2>{active > 0 && <span className="badge ok">{active} active</span>}
          <ActionButton className="btn ghost small right" run={async () => { const r = await api.del<{ removed: number }>("/admin/tasks"); notify(`Removed ${r.removed} finished task(s).`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); }}>Clear finished</ActionButton></div>
        <div className="tablewrap"><table className="dtable"><thead><tr><th>#</th><th>Task</th><th>Status</th><th>Progress</th><th>Started</th><th /></tr></thead>
          <tbody>{shown.map((t) => <tr key={t.id}><td>{t.id}</td><td>{t.kind.replace(/_/g, " ")}</td>
            <td><span className={`badge ${t.status === "done" ? "ok" : t.status === "failed" ? "bad" : t.status === "running" ? "warn" : ""}`}>{t.status}</span></td>
            <td className="clip small muted" title={progressText(t)}>{progressText(t)}</td><td className="small muted">{ago(t.created_at)}</td>
            <td><div className="actions">{(t.status === "queued" || t.status === "running") && <ActionButton className="iconbtn" run={async () => { await api.post(`/admin/tasks/${t.id}/cancel`); notify(`Task #${t.id} stopped.`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); }}>Stop</ActionButton>}</div></td></tr>)}
            {!items.length && <tr><td colSpan={6} className="empty">No tasks yet. Run one above.</td></tr>}</tbody></table></div>
        {items.length > 8 && <button className="linkbtn small" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show all ${items.length}`}</button>}
      </div>
    </div>
  );
}
