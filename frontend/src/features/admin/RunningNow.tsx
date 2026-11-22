import { Icon } from "@/shared/ui/Icon";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { flag } from "@/shared/lib/geo";
import { BoardIcon, boardName } from "@/shared/ui/BoardIcon";
import { ActionButton, ago, num } from "./ui";

export type TaskRow = { id: number; kind: string; status: string; error?: string | null; created_at: string; finished_at?: string | null; progress?: Record<string, unknown> | null };

/** Plain-language names for every task the worker can run. */
export const TASK_INFO: Record<string, { icon: string; title: string; what: string }> = {
  scan_all: { icon: "crawler", title: "Re-scan every company", what: "Reading every employer's careers page again" },
  scan_unscanned: { icon: "company", title: "Scan new companies", what: "Reading the careers pages of employers never visited" },
  scan_company: { icon: "company", title: "Scan one company", what: "Reading one employer's careers page" },
  discover: { icon: "search", title: "Discover companies", what: "Collecting employers from free public sources" },
  discover_country: { icon: "search", title: "Find employers in a country", what: "Searching maps and directories for employers" },
  board_search: { icon: "search", title: "Search job boards", what: "Asking LinkedIn, Indeed and others for matching jobs" },
  census: { icon: "filter", title: "Find job-system boards", what: "Looking up public job boards of known job systems" },
  internships: { icon: "intern", title: "Find internships", what: "Reading student and graduate pages" },
  broad_sources: { icon: "search", title: "Wide discovery", what: "Sweeping bigger open-data sources for employers" },
  logos: { icon: "company", title: "Fetch logos", what: "Downloading company logos" },
  dedupe_jobs: { icon: "jobs", title: "Merge duplicate jobs", what: "Folding the same role from other cities, links and boards into one job" },
  sponsors_refresh: { icon: "company", title: "Refresh visa sponsors", what: "Downloading the IND sponsor register" },
  embed: { icon: "cv", title: "Build search vectors", what: "Preparing jobs for smart search" },
  live_search: { icon: "crawler", title: "Live re-read", what: "Re-reading the employers related to a search" },
  mail_sync: { icon: "inbox", title: "Sync inbox", what: "Reading job e-mails" },
};
const info = (k: string) => TASK_INFO[k] ?? { icon: "crawler", title: k.replace(/_/g, " "), what: "" };

/** One sentence: what this task is doing at this moment. */
function doingNow(t: TaskRow): React.ReactNode {
  const p = (t.progress ?? {}) as Record<string, unknown>;
  if (t.status === "queued") return <>Waiting for the worker to pick it up…</>;
  if (t.kind === "board_search" && p.current) {
    const [term, , country] = String(p.current).split(/ (in) /);
    const site = p.current_site as string | undefined;
    return site ? <><BoardIcon board={site} size={16} /> Asking <b>{boardName(site)}</b> for <b>“{term}”</b> in {flag(country)} <b>{String(p.current_where ?? country)}</b></>
      : <>Just finished <b>“{term}”</b> in {flag(country)} {country}</>;
  }
  if (t.kind === "discover_country" && p.country) return <>{flag(String(p.country))} {(p.log as string[] | undefined)?.slice(-1)[0] ?? `Finding employers in ${p.country}`}</>;
  const log = p.log as string[] | undefined;
  if (log?.length) return <>{log[log.length - 1]}</>;
  if (p.total) return <>{num(Number(p.done ?? 0))} of {num(Number(p.total))} done{p.new_jobs ? ` · ${num(Number(p.new_jobs))} new jobs` : ""}</>;
  return <>{info(t.kind).what}…</>;
}

export function TaskCard({ t, compact = false }: { t: TaskRow; compact?: boolean }) {
  const qc = useQueryClient(); const i = info(t.kind); const p = (t.progress ?? {}) as Record<string, unknown>;
  const total = Number(p.total ?? 0), done = Number(p.done ?? 0), pct = total ? Math.round((done / total) * 100) : null;
  const act = async (a: "pause" | "resume" | "cancel") => { await api.post(`/admin/tasks/${t.id}/${a}`); await qc.invalidateQueries({ queryKey: ["admin-tasks"] }); };
  const st = t.status === "paused" ? "paused" : t.status === "queued" ? "queued" : "running";
  const plan = p.plan as { terms?: string[]; countries?: string[]; sites?: string[] } | undefined;
  return (<div className={`tcard ${st}`}>
    <div className="tc-top"><span className="tc-icon ph-icon" aria-hidden><Icon name={i.icon} size={17} /></span>
      <div className="tc-main"><div className="row" style={{ gap: 8 }}><b>{i.title}</b><span className={`tc-pill ${st}`}><i />{st === "running" ? "Running" : st === "paused" ? "Paused" : "Queued"}</span><span className="small muted">#{t.id} · started {ago(t.created_at)}</span></div>
        <div className="tc-now small">{t.status === "paused" ? <>Paused. It stopped between two steps and keeps everything found so far. Press Resume to carry on.</> : doingNow(t)}</div></div>
      <div className="tc-act">
        {t.status === "running" && <ActionButton className="btn ghost small" run={() => act("pause")} title="Pause at the next step; nothing is lost">⏸ Pause</ActionButton>}
        {t.status === "paused" && <ActionButton className="btn small" run={() => act("resume")}>▶ Resume</ActionButton>}
        <ActionButton className="btn ghost small danger-text" run={() => act("cancel")} title="Stop at the next step; what was found so far is kept">■ Stop</ActionButton></div></div>
    {pct !== null && <div className={`tc-bar ${st}`} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}><div style={{ width: `${Math.max(2, pct)}%` }} /><span>{num(done)} / {num(total)}</span></div>}
    {!compact && t.kind === "board_search" && plan && <div className="tc-plan small"><span className="muted">Searching for</span> {(plan.terms ?? []).map((x) => <span key={x} className="cchip on">{x}</span>)}
      <span className="muted">in</span> {(plan.countries ?? []).map((c) => <span key={c} className="cchip">{flag(c)} {c}</span>)}<span className="muted">on</span> {(plan.sites ?? []).map((s) => <BoardIcon key={s} board={s} size={18} />)}</div>}
    {!compact && (p.found !== undefined || p.new_jobs !== undefined) && <div className="tc-stats small">{p.found !== undefined && <span><b>{num(Number(p.found))}</b> found</span>}{p.new_jobs !== undefined && <span><b>{num(Number(p.new_jobs))}</b> new jobs</span>}{Number(p.blocked ?? 0) > 0 && <span className="berr"><b>{String(p.blocked)}</b> blocked</span>}{Number(p.skipped ?? 0) > 0 && <span><b>{String(p.skipped)}</b> skipped</span>}</div>}
  </div>);
}

/** Under the status bar on every Crawler tab: everything started by hand that is queued, running or paused, and the last one that finished. */
export function RunningNow() {
  const q = useQuery({ queryKey: ["admin-tasks"], refetchInterval: 3000, queryFn: () => api.get<TaskRow[]>("/admin/tasks") });
  const all = q.data ?? []; const active = all.filter((t) => ["queued", "running", "paused"].includes(t.status));
  const last = all.find((t) => t.status === "done" || t.status === "failed");
  if (!q.data) return null;
  return (<div className="running">
    {active.length ? active.map((t) => <TaskCard key={t.id} t={t} />)
      : <div className="tc-idle small"><Icon name="crawler" size={15} /> No task started by hand is running. The crawler's own reading of career pages (step 3) runs by itself and is shown in the bar above.
        {last && <span className="muted"> Last task: {info(last.kind).title} {last.error === "stopped by operator" ? "stopped" : last.status}{last.finished_at ? ` ${ago(last.finished_at)}` : ""}{(last.progress as Record<string, unknown> | null)?.new_jobs !== undefined ? `, ${num(Number((last.progress as Record<string, unknown>).new_jobs))} new jobs` : ""}.</span>}</div>}
  </div>);
}
