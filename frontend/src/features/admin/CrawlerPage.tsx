import { Icon } from "@/shared/ui/Icon";
import { PageHeader } from "@/shared/ui";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { SourceHealth } from "./SourceHealth";
import { WorkerPanel, type WorkerInfo } from "./WorkerPanel";
import { CountriesCard, PauseButton, RecencyCard, ScheduleCard, StatusBanner, WorkerList } from "./CrawlerSetup";
import { PipelineExplorer, type CrawlTab } from "./PipelineExplorer";
import { BoardsTab } from "./BoardsTab";
import { RunningNow, taskTitle } from "./RunningNow";
import { CompaniesTab } from "./CompaniesTab";
import { JobsTab } from "./JobsTab";
import { StorageTab } from "./StorageTab";
import { FocusCard, SpeedCard } from "./SpeedFocus";
import { TasksPanel } from "./TasksTab";
import { UsersTab } from "./UsersTab";
import { Fold, NotifyProvider, num } from "./ui";

type Stats = { companies: number; companies_scanned: number; companies_with_jobs: number; open_jobs: number; users: number; sponsors: number; scan_outcomes: { note: string; n: number }[] };
type Main = "overview" | "boards" | "settings" | "data" | "tasks" | "users";
const TABS: [Main, string, string][] = [["overview", "crawler", "Overview"], ["boards", "search", "Job boards"], ["settings", "filter", "Settings"], ["data", "company", "Companies & jobs"], ["tasks", "menu", "Tasks"], ["users", "profile", "Users"]];
const BLURB: Record<Main, string> = {
  overview: "The crawler in six steps, with live numbers.",
  boards: "Optional searches on LinkedIn, Indeed, Glassdoor and Bayt.",
  settings: "What to collect, how fast, when it runs, which countries.",
  data: "Every employer it watches and every stored posting.",
  tasks: "Every job you can start by hand, in one place, and their history.",
  users: "Accounts and roles.",
};
/** Older tab names still work (bookmarks, step buttons): they open a section of Settings or Data. */
const ALIAS: Record<string, [Main, string?]> = { setup: ["settings"], storage: ["settings", "storage"], companies: ["data", "companies"], jobs: ["data", "jobs"] };

/** `preview` shows every control (the demo page, which answers all calls itself). */
export function CrawlerPage({ preview = false }: { preview?: boolean }) {
  const isAdmin = useAuth().user?.role === "admin" || preview;
  const [sp, setSp] = useSearchParams(); const raw = sp.get("tab") ?? "overview";
  const [tab, aliasView] = (ALIAS[raw] ?? [TABS.find((t) => t[0] === raw)?.[0] ?? "overview"]) as [Main, string?];
  const view = (sp.get("view") ?? aliasView) === "jobs" ? "jobs" : "companies"; const openStorage = aliasView === "storage";
  const go = (t: CrawlTab, v?: string) => { const [m, av] = ALIAS[t] ?? [t as Main, undefined]; const vv = v ?? av; setSp(m === "overview" ? {} : { tab: m, ...(vv ? { view: vv } : {}) }, { replace: true }); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const stats = useQuery({ queryKey: ["admin-stats"], refetchInterval: 15000, queryFn: () => api.get<Stats>("/admin/stats") });
  const w = useQuery({ queryKey: ["admin-worker"], refetchInterval: 5000, queryFn: () => api.get<WorkerInfo>("/admin/worker") }).data;
  const s = stats.data;
  const count: Partial<Record<Main, string>> = s ? { data: `${num(s.companies)} · ${num(s.open_jobs)}`, users: num(s.users) } : {};
  return (
    <NotifyProvider>
      <div className="stack crawler">
        <div className="chead">
          <PageHeader eyebrow="System" icon={<Icon name="crawler" size={17} />} title="Crawler" subtitle={<>Finds employers, reads their career pages and keeps the job list fresh, on its own. {BLURB[tab]}</>} />
          <StatusBanner s={w?.status} rate={w?.rate_per_min} control={<PauseButton schedule={w?.schedule} isAdmin={isAdmin} />} />
          <WorkerList s={w?.status} title={taskTitle} />
          <RunningNow />
        </div>
        <nav className="ctabs" role="tablist" aria-label="Crawler sections">{TABS.filter((t) => t[0] !== "users" || isAdmin).map(([k, i, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={`ctab${tab === k ? " on" : ""}`} onClick={() => go(k)}><Icon name={i} size={15} />{l}{count[k] && <span className="count">{count[k]}</span>}{k === "boards" && <span className="exp">beta</span>}</button>))}</nav>
        <div className="fadein" key={tab}>
          {tab === "overview" && <div className="stack">
            <PipelineExplorer />
            <Fold title="Live activity" hint="visits per minute, what is waiting, the latest scans"><WorkerPanel bare /></Fold>
            {!!s?.scan_outcomes?.length && <Fold title="How the last visits ended" hint="what happened on each employer's site"><Outcomes rows={s.scan_outcomes} /></Fold>}
            <Fold title="Source health" hint="failing and stale employers, coverage per job system"><SourceHealth bare /></Fold>
          </div>}
          {tab === "boards" && <BoardsTab />}
          {tab === "settings" && <div className="stack">
            <div className="sgrid2"><div className="stack"><FocusCard isAdmin={isAdmin} /><CountriesCard isAdmin={isAdmin} /></div><div className="stack"><SpeedCard isAdmin={isAdmin} /><RecencyCard isAdmin={isAdmin} /><ScheduleCard isAdmin={isAdmin} /></div></div>
            <Fold title="Storage & clean-up" hint="which fields to keep, old jobs, housekeeping" open={openStorage}><StorageTab isAdmin={isAdmin} /></Fold>
          </div>}
          {tab === "data" && <div className="stack">
            <div className="seg" role="tablist" aria-label="Show"><button role="tab" aria-selected={view === "companies"} className={view === "companies" ? "on" : ""} onClick={() => go("data", "companies")}>Companies {s && <span className="count">{num(s.companies)}</span>}</button>
              <button role="tab" aria-selected={view === "jobs"} className={view === "jobs" ? "on" : ""} onClick={() => go("data", "jobs")}>Jobs {s && <span className="count">{num(s.open_jobs)}</span>}</button></div>
            {view === "companies" ? <CompaniesTab isAdmin={isAdmin} /> : <JobsTab isAdmin={isAdmin} />}
          </div>}
          {tab === "tasks" && <TasksPanel preview={preview} />}
          {tab === "users" && isAdmin && <UsersTab />}
        </div>
      </div>
    </NotifyProvider>
  );
}

function Outcomes({ rows }: { rows: { note: string; n: number }[] }) {
  const max = Math.max(...rows.map((x) => x.n));
  return <div className="stack" style={{ gap: 6 }}>{rows.slice(0, 10).map((o) => <div key={o.note} className="obar"><span className="small">{o.note}</span><span className="small muted">{num(o.n)}</span><i style={{ width: `${Math.min(100, (o.n / max) * 100)}%` }} /></div>)}</div>;
}
