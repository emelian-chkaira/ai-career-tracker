import { Icon } from "@/shared/ui/Icon";
import { PageHeader } from "@/shared/ui";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { SourceHealth } from "./SourceHealth";
import { WorkerPanel, type WorkerInfo } from "./WorkerPanel";
import { CountriesCard, PauseButton, ScheduleCard, StatusBanner } from "./CrawlerSetup";
import { PipelineExplorer, type CrawlTab } from "./PipelineExplorer";
import { BoardsTab } from "./BoardsTab";
import { RunningNow } from "./RunningNow";
import { CompaniesTab } from "./CompaniesTab";
import { JobsTab } from "./JobsTab";
import { StorageTab } from "./StorageTab";
import { TasksPanel } from "./TasksTab";
import { UsersTab } from "./UsersTab";
import { NotifyProvider, num } from "./ui";

type Stats = { companies: number; companies_scanned: number; companies_with_jobs: number; open_jobs: number; users: number; sponsors: number; scan_outcomes: { note: string; n: number }[] };
const TABS: [CrawlTab, string, string][] = [["overview", "crawler", "How it works"], ["boards", "search", "Job boards"], ["setup", "filter", "Schedule & countries"], ["companies", "company", "Companies"],
  ["jobs", "jobs", "Jobs"], ["storage", "collapse", "Storage & clean-up"], ["tasks", "menu", "Tasks"], ["users", "profile", "Users"]];
const BLURB: Record<CrawlTab, string> = {
  overview: "The crawler in six steps, live numbers for each, and what it is doing this minute.",
  boards: "Optional searches on LinkedIn, Indeed, Glassdoor and Bayt: see exactly which keywords and countries, and how each board is doing.",
  setup: "When the crawler may run on its own, how often it revisits employers, and which countries it collects.",
  companies: "Every employer the crawler watches: search, fix a careers link, re-scan or remove one.",
  jobs: "Every stored posting: browse, filter and delete.",
  storage: "Which fields and how old postings to keep, and clean-ups.",
  tasks: "One-off jobs you can start by hand, and their history.",
  users: "Accounts and roles.",
};

export function CrawlerPage() {
  const isAdmin = useAuth().user?.role === "admin";
  const [sp, setSp] = useSearchParams(); const tab = (TABS.find((t) => t[0] === sp.get("tab"))?.[0] ?? "overview") as CrawlTab;
  const go = (t: CrawlTab) => { setSp(t === "overview" ? {} : { tab: t }, { replace: true }); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const stats = useQuery({ queryKey: ["admin-stats"], refetchInterval: 15000, queryFn: () => api.get<Stats>("/admin/stats") });
  const w = useQuery({ queryKey: ["admin-worker"], refetchInterval: 5000, queryFn: () => api.get<WorkerInfo>("/admin/worker") }).data;
  const s = stats.data;
  const count: Partial<Record<CrawlTab, string>> = s ? { companies: num(s.companies), jobs: num(s.open_jobs), users: num(s.users) } : {};
  return (
    <NotifyProvider>
      <div className="stack crawler">
        <div className="chead">
          <PageHeader eyebrow="System" icon={<Icon name="crawler" size={17} />} title="Crawler" subtitle={<>Finds employers, reads their career pages and keeps the job list fresh, on its own. {BLURB[tab]}</>} />
          <StatusBanner s={w?.status} rate={w?.rate_per_min} control={<PauseButton schedule={w?.schedule} isAdmin={isAdmin} />} />
          <RunningNow />
        </div>
        <nav className="ctabs" role="tablist" aria-label="Crawler sections">{TABS.filter((t) => t[0] !== "users" || isAdmin).map(([k, i, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={`ctab${tab === k ? " on" : ""}`} onClick={() => go(k)}><Icon name={i} size={15} />{l}{count[k] && <span className="count">{count[k]}</span>}{k === "boards" && <span className="exp">beta</span>}</button>))}</nav>
        <div className="fadein" key={tab}>
          {tab === "overview" && <div className="stack">
            <PipelineExplorer go={go} />
            <WorkerPanel />
            <div className="sgrid2" style={{ alignItems: "start" }}>
              {!!s?.scan_outcomes?.length && <div className="card stack"><h2 style={{ margin: 0 }}>How the last visits ended</h2><div className="small muted">What happened on each employer's site the last time it was read.</div>
                {s.scan_outcomes.slice(0, 10).map((o) => <div key={o.note} className="obar"><span className="small">{o.note}</span><span className="small muted">{num(o.n)}</span><i style={{ width: `${Math.min(100, (o.n / Math.max(...s.scan_outcomes.map((x) => x.n))) * 100)}%` }} /></div>)}</div>}
              <div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Start something now</h2><button className="btn ghost small right" onClick={() => go("tasks")}>All tasks →</button></div><TasksPanel compact /></div>
            </div>
            <SourceHealth />
          </div>}
          {tab === "boards" && <BoardsTab />}
          {tab === "setup" && <div className="sgrid2"><ScheduleCard isAdmin={isAdmin} /><CountriesCard isAdmin={isAdmin} /></div>}
          {tab === "companies" && <CompaniesTab isAdmin={isAdmin} />}
          {tab === "jobs" && <JobsTab isAdmin={isAdmin} />}
          {tab === "storage" && <StorageTab isAdmin={isAdmin} />}
          {tab === "tasks" && <TasksPanel />}
          {tab === "users" && isAdmin && <UsersTab />}
        </div>
      </div>
    </NotifyProvider>
  );
}
