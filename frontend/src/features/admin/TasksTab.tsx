import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { ActionButton, ago, num, useNotify } from "./ui";
import { Housekeeping } from "./StorageTab";

type Task = { id: number; kind: string; status: string; progress?: Record<string, unknown>; error?: string | null; created_at: string; finished_at?: string | null };
type Def = { kind: string; title: string; what: string; note?: string };
/** Every task you can start by hand, in groups. Short lines: the longer explanation sits in the tooltip. */
export const GROUPS: { title: string; items: Def[] }[] = [
  { title: "Read jobs", items: [
    { kind: "scan_due", title: "Scan what is due", what: "Employers whose next visit has come, job-system feeds first", note: "The quick one. The worker already does this on its schedule." },
    { kind: "scan_unscanned", title: "Scan new companies", what: "Only those never visited" },
    { kind: "scan_all", title: "Re-scan everything", what: "Every careers page, slow", note: "Visits every employer, even those just read. Usually not needed." },
    { kind: "board_search", title: "Search job boards", what: "LinkedIn, Indeed, Glassdoor, Bayt", note: "Experimental: via JobSpy, needs CAREERS_BOARD_SITES, and is against those sites' terms. Open the Job boards tab to choose keywords first." }] },
  { title: "Find employers", items: [
    { kind: "discover", title: "Discover companies", what: "From free public sources" },
    { kind: "census", title: "Find job-system boards", what: "Employers on public ATS boards" },
    { kind: "internships", title: "Find internships", what: "Student and graduate pages" }] },
  { title: "Keep tidy", items: [
    { kind: "dedupe_jobs", title: "Merge duplicate jobs", what: "One role, one job", note: "Folds the same role from other cities, links or boards into one and fixes link-label titles. Also runs daily." },
    { kind: "sponsors_refresh", title: "Refresh sponsor list", what: "NL IND register, re-check companies" }] },
];

const ICON: Record<string, string> = { scan_due: "⚡", scan_unscanned: "🆕", scan_all: "🔄", board_search: "🔎", discover: "🧭", census: "🗂", internships: "🎓", dedupe_jobs: "🧩", sponsors_refresh: "🛂", logos: "🖼", embed: "✨" };

function progressText(t: Task) {
  const p = t.progress ?? {}; const done = Number(p.done ?? 0), total = Number(p.total ?? 0);
  if (t.error) return t.error;
  if (total) return `${num(done)} / ${num(total)}${p.new_jobs ? ` · ${num(Number(p.new_jobs))} new jobs` : ""}`;
  const e = Object.entries(p).filter(([, v]) => typeof v === "number" || typeof v === "string").slice(0, 3).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`); return e.join(" · ");
}

/** All the things you can start by hand, in one place, with a search; then the history. */
export function TasksPanel() {
  const qc = useQueryClient(); const notify = useNotify(); const [all, setAll] = useState(false); const [find, setFind] = useState(""); const [group, setGroup] = useState("");
  const isAdmin = useAuth().user?.role === "admin";
  const tasks = useQuery({ queryKey: ["admin-tasks"], refetchInterval: 4000, queryFn: () => api.get<Task[]>("/admin/tasks") });
  const run = async (t: Def) => { const r = await api.post<{ id: number }>("/admin/tasks", { kind: t.kind }); notify(`Queued “${t.title}” (#${r.id}). The worker starts it within seconds.`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); };
  const items = tasks.data ?? []; const shown = all ? items : items.slice(0, 8);
  const active = items.filter((t) => t.status === "queued" || t.status === "running" || t.status === "paused").length;
  const f = find.trim().toLowerCase(); const filtering = !!f || !!group;
  const match = (t: Def) => !f || `${t.title} ${t.what} ${t.note ?? ""}`.toLowerCase().includes(f);
  const groups = GROUPS.filter((g) => !group || g.title === group).map((g) => ({ ...g, items: g.items.filter(match) })).filter((g) => g.items.length);
  const cleanup = (!group || group === "Clean-up") && (!f || "clean-up purge classify clear apply storage policy delete".includes(f));
  return (
    <div className="stack">
      <div className="card stack">
        <div className="row" style={{ gap: 8 }}><h2 style={{ margin: 0 }}>Start a task</h2>{active > 0 && <span className="badge ok">{active} active</span>}
          <input type="search" placeholder="Search tasks…" aria-label="Search tasks" value={find} onChange={(e) => setFind(e.target.value)} style={{ marginLeft: "auto", width: 200 }} /></div>
        <div className="row" style={{ gap: 6 }} role="group" aria-label="Groups">{[...GROUPS.map((g) => g.title), "Clean-up"].map((g) => <button key={g} className={"pill-btn" + (group === g ? " on" : "")} onClick={() => setGroup(group === g ? "" : g)}>{g}</button>)}
          {filtering && <button className="btn ghost small" onClick={() => { setFind(""); setGroup(""); }}>Clear filters</button>}</div>
        <div className="stack" style={{ gap: 18 }}>{groups.map((g) => <section key={g.title}><h3 className="tsec">{g.title}</h3>
          <div className="tcards">{g.items.map((t) => { const busy = items.filter((x) => x.kind === t.kind && (x.status === "running" || x.status === "queued")).length;
            return <div key={t.kind} className={"tcard" + (busy ? " busy" : "")} title={t.note}>
              <div className="tcard-h"><span className="tcard-i" aria-hidden>{ICON[t.kind] ?? "▶"}</span><b>{t.title}</b>{busy > 0 && <span className="badge warn right">running</span>}</div>
              <div className="small muted tcard-d">{t.what}</div>
              <ActionButton className="btn small" disabled={busy > 0} run={() => run(t)}>{busy ? "Already queued" : "Run"}</ActionButton></div>; })}</div></section>)}
          {cleanup && <section><h3 className="tsec">Clean-up</h3><Housekeeping isAdmin={isAdmin} /></section>}</div>
        {!groups.length && !cleanup && <div className="small muted">No task matches. <button className="linkbtn" onClick={() => { setFind(""); setGroup(""); }}>Clear filters</button></div>}
      </div>
      <div className="card stack">
        <div className="row"><h2 style={{ margin: 0 }}>History</h2>
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
