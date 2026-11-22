import { Icon } from "@/shared/ui/Icon";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { flag } from "@/shared/lib/geo";
import { useSectors } from "@/shared/api/meta";
import { ActionButton, ago, num, useNotify } from "./ui";

export type CrawlTab = "overview" | "boards" | "setup" | "companies" | "jobs" | "storage" | "tasks" | "users";
type Last = { kind: string; status: string; at: string | null } | null;
export type Pipeline = {
  discover: { companies: number; by_source: { source: string; n: number }[]; last: Last };
  locate: { with_careers_page: number; with_job_system: number; not_found: number; never_visited: number };
  read: { visited_hour: number; visited_day: number; due: number; revisit_hours: number; parallel: number };
  understand: { open_jobs: number; embedded: number; by_sector: { key: string; n: number }[]; by_mode: { key: string; n: number }[] };
  keep: { countries: string[]; keep_remote: boolean; max_job_age_days: number; delete_expired_after_days: number; new_day: number; expired_day: number };
  notify: { saved_searches: number; alerts_day: number; emails_pending: number };
  boards: { enabled: boolean; jobs: number; last: Last; every_hours: number };
};
type Step = { id: keyof Pipeline; icon: string; title: string; short: string; metric: (p: Pipeline) => string; what: string; when: (p: Pipeline) => string;
  now: (p: Pipeline, name: (k: string) => string) => [string, string][]; actions: { label: string; task?: string; tab?: CrawlTab; hint: string }[] };

const lastText = (l: Last) => (l ? `${l.kind.replace(/_/g, " ")} ${l.status}${l.at ? `, ${ago(l.at)}` : ""}` : "never run");
const pct = (a: number, b: number) => (b ? `${Math.round((a / b) * 100)}%` : "–");

const STEPS: Step[] = [
  { id: "discover", icon: "🔎", title: "Find employers", short: "who to watch", metric: (p) => `${num(p.discover.companies)} employers`,
    what: "Builds the list of companies to watch from free public sources: European Tech Map, OpenStreetMap offices, Wikipedia/Wikidata, public job-system boards and the seed list. Users' countries add more.",
    when: () => "When you run “Discover companies” or “Find employers” for a country, and automatically when someone picks a country the crawler knows few employers in.",
    now: (p) => [["Employers known", num(p.discover.companies)], ...p.discover.by_source.map((s): [string, string] => [`from ${s.source}`, num(s.n)]), ["Last discovery", lastText(p.discover.last)]],
    actions: [{ label: "Discover companies", task: "discover", hint: "All free sources, the Netherlands first. Takes a while." }, { label: "Find employers per country", tab: "setup", hint: "Schedule & countries → Find employers" }] },
  { id: "locate", icon: "🧭", title: "Find careers pages", short: "where jobs live", metric: (p) => `${pct(p.locate.with_careers_page, p.discover.companies)} located`,
    what: "Visits each company's website, follows the “jobs / careers / werken bij” link and recognises the job system behind it (Greenhouse, Lever, Workday, Personio, Recruitee…), so it can read postings from the source.",
    when: () => "The first time a company is visited, and again whenever its careers page stops answering.",
    now: (p) => [["Careers page found", num(p.locate.with_careers_page)], ["Job system recognised", num(p.locate.with_job_system)], ["Website or page not found", num(p.locate.not_found)], ["Never visited yet", num(p.locate.never_visited)]],
    actions: [{ label: "Scan new companies", task: "scan_unscanned", hint: "Visit only the companies never visited." }, { label: "See companies", tab: "companies", hint: "Search, fix a careers link, re-scan one company." }] },
  { id: "read", icon: "📥", title: "Read postings", short: "all day, politely", metric: (p) => `${num(p.read.visited_hour)}/hour`,
    what: "Reads every posting from the job system's public feed, or from the page itself when there is none. Polite: robots.txt honoured, one request per second per site, never-visited employers first.",
    when: (p) => `Continuously while the schedule allows: up to ${p.read.parallel} career sites at once, each employer again every ${p.read.revisit_hours} h (less often when its site keeps failing).`,
    now: (p) => [["Visited in the last hour", num(p.read.visited_hour)], ["Visited in the last day", num(p.read.visited_day)], ["Waiting for a visit", num(p.read.due)]],
    actions: [{ label: "Re-scan everything", task: "scan_all", hint: "Visit every company now (slow)." }, { label: "Change schedule", tab: "setup", hint: "Days, hours, revisit interval, parallel sites." }] },
  { id: "understand", icon: "🏷️", title: "Understand postings", short: "field, place, level", metric: (p) => `${num(p.understand.open_jobs)} open jobs`,
    what: "Works out each posting's field, country and city, on-site / hybrid / remote, level, language, salary and skills, and builds a meaning vector for smart search.",
    when: () => "Right after a posting is read. Search vectors are added every two minutes.",
    now: (p, name) => [["Open jobs", num(p.understand.open_jobs)], ["Ready for smart search", `${num(p.understand.embedded)} (${pct(p.understand.embedded, p.understand.open_jobs)})`],
      ...p.understand.by_sector.map((s): [string, string] => [name(s.key), num(s.n)]), ...p.understand.by_mode.map((m): [string, string] => [m.key === "onsite" ? "On-site" : m.key[0].toUpperCase() + m.key.slice(1), num(m.n)])],
    actions: [{ label: "Build search vectors", task: "embed", hint: "Catch up on smart-search vectors now." }, { label: "See jobs", tab: "jobs", hint: "Browse, filter and delete stored jobs." }] },
  { id: "keep", icon: "🗂️", title: "Keep what matters", short: "countries & rules", metric: (p) => `${p.keep.countries.length || "all"} countries`,
    what: "Stores only postings in the countries you collect (plus remote jobs open to them). One role, one job: the same role in another city, on another link or on a job board is folded into one job with all its places. Postings that disappeared expire; old ones are deleted by your storage rules.",
    when: (p) => `On every read. Expired postings are deleted after ${p.keep.delete_expired_after_days || "never"}${p.keep.delete_expired_after_days ? " days" : ""}, checked daily.`,
    now: (p) => [["Countries collected", p.keep.countries.map((c) => `${flag(c)} ${c}`).join(" ") || "every country"], ["Remote jobs open to them", p.keep.keep_remote ? "kept" : "skipped"], ["New in the last day", num(p.keep.new_day)], ["Expired in the last day", num(p.keep.expired_day)]],
    actions: [{ label: "Merge duplicate jobs", task: "dedupe_jobs", hint: "Fold duplicates now (it also runs daily)." }, { label: "Countries to collect", tab: "setup", hint: "Add or remove countries." }, { label: "Storage rules", tab: "storage", hint: "Fields to keep, maximum age, clean-up." }] },
  { id: "notify", icon: "🔔", title: "Tell people", short: "feeds & alerts", metric: (p) => `${num(p.notify.alerts_day)} alerts today`,
    what: "New jobs reach each user's feed at once. Saved searches and followed companies send in-app alerts and e-mail digests.",
    when: () => "Alerts are checked every five minutes; each saved search sends instantly, daily or weekly, as its owner chose.",
    now: (p) => [["Saved searches and follows", num(p.notify.saved_searches)], ["Alerts in the last day", num(p.notify.alerts_day)], ["E-mails waiting to be sent", num(p.notify.emails_pending)]],
    actions: [] },
];

/** The crawler as six steps. Click one to see what it does, when it runs, what it did lately and what you can do about it. */
export function PipelineExplorer({ go }: { go(t: CrawlTab): void }) {
  const q = useQuery({ queryKey: ["admin-pipeline"], refetchInterval: 15000, queryFn: () => api.get<Pipeline>("/admin/pipeline") });
  const sec = useSectors().data; const name = (k: string) => sec?.sectors.find((s) => s.key === k)?.label ?? k;
  const [sel, setSel] = useState<Step["id"]>("read"); const qc = useQueryClient(); const notify = useNotify();
  const p = q.data;
  if (!p) return <div className="card muted">Loading the crawler's steps…</div>;
  const st = STEPS.find((s) => s.id === sel) ?? STEPS[2];
  const run = async (task: string, label: string) => { const r = await api.post<{ id: number }>("/admin/tasks", { kind: task }); notify(`Started “${label}” (task #${r.id}). Follow it in Tasks.`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); };
  return (<div className="card stack pipe">
    <div className="row"><h2 style={{ margin: 0 }}>How the crawler works</h2><span className="small muted">Click a step to see what it does, when, and what it did lately.</span></div>
    <ol className="psteps" role="tablist" aria-label="Crawler steps">{STEPS.map((s, i) => (
      <li key={s.id}><button role="tab" aria-selected={sel === s.id} className={`pstep${sel === s.id ? " on" : ""}`} onClick={() => setSel(s.id)} style={{ animationDelay: `${i * 50}ms` }}>
        <span className="pnum">{i + 1}</span><span className="picon" aria-hidden>{s.icon}</span><b>{s.title}</b><span className="small muted">{s.short}</span><span className="pmetric">{s.metric(p)}</span></button></li>))}</ol>
    <div className="pdetail" key={st.id}>
      <div className="stack" style={{ gap: 10 }}>
        <div><div className="plabel">What it does</div><div>{st.what}</div></div>
        <div><div className="plabel">When it happens</div><div>{st.when(p)}</div></div>
        {st.actions.length > 0 && <div><div className="plabel">What you can do</div><div className="row">{st.actions.map((a) => a.task
          ? <ActionButton key={a.label} className="btn small" title={a.hint} run={() => run(a.task!, a.label)}>▶ {a.label}</ActionButton>
          : <button key={a.label} className="btn ghost small" title={a.hint} onClick={() => go(a.tab!)}>{a.label} →</button>)}</div></div>}
      </div>
      <div><div className="plabel">Right now</div><dl className="pnow">{st.now(p, name).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl></div>
    </div>
    <button className={`pboards${p.boards.enabled ? " on" : ""}`} onClick={() => go("boards")}>
      <span aria-hidden className="ph-icon"><Icon name="search" size={16} /></span><span><b>Side road: job boards</b> <span className="chip warn" style={{ margin: 0 }}>experimental</span><br /><span className="small muted">
        {p.boards.enabled ? `LinkedIn, Indeed and others every ${p.boards.every_hours} h · ${num(p.boards.jobs)} open jobs found there · last run: ${lastText(p.boards.last)}` : "Switched off. Searches LinkedIn, Indeed, Glassdoor and Bayt for users' job titles when turned on."}</span></span><span className="right">Open →</span></button>
  </div>);
}
