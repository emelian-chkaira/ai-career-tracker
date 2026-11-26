import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { Switch } from "@/shared/ui/kit";
import { flag } from "@/shared/lib/geo";
import { PlacePicker } from "@/features/onboarding/SetupWizard";
import { ActionButton, num, useNotify } from "./ui";

export type WorkerRow = { id: string; pid?: number; host?: string; state: string; task?: string | null; task_id?: number | null; inflight: number; lead: boolean; old: boolean; seen_seconds: number };
export type WorkerStatus = { workers?: WorkerRow[]; state: "running" | "idle" | "paused" | "stopped"; seen_seconds: number | null; pid?: number; host?: string; inflight: number; task?: string | null; allowed: boolean; why: string; next_start: string | null; note: string };
type Schedule = { enabled: boolean; days: number[]; start: string; end: string; tz: string; revisit_hours: number; parallel: number; allowed_now: boolean; why: string; next_start: string | null };
type Policy = { countries: string[]; keep_remote: boolean; keep_domains: string[]; saved_domains?: string[]; max_job_age_days: number; delete_expired_after_days: number; by_age: Record<string, number>; by_country: Record<string, number>; places: { countries: { code: string; name: string; regions: string[] }[]; regions: { key: string; label: string; countries: string[] }[] } };

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const TZ = ["Europe/Amsterdam", "Europe/London", "Europe/Berlin", "Europe/Warsaw", "Europe/Athens", "Asia/Dubai", "Asia/Riyadh", "Asia/Qatar", "Africa/Cairo", "UTC"];
const at = (iso: string | null) => (iso ? new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "");

type Sched = { enabled: boolean; days: number[]; start: string; end: string; tz: string; revisit_hours: number; parallel: number };

/** Pause / resume automatic crawling in one click (switches the schedule off or on). Admins only; others see why it is disabled. */
export function PauseButton({ schedule, isAdmin }: { schedule?: Sched; isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  if (!schedule) return null;
  const on = schedule.enabled;
  const flip = async () => {
    await api.put("/admin/schedule", { ...schedule, enabled: !on });
    await Promise.all([qc.invalidateQueries({ queryKey: ["admin-worker"] }), qc.invalidateQueries({ queryKey: ["admin-schedule"] })]);
    notify(on ? "Paused. No new career sites are started; the ones already open finish in a minute or two." : "Resumed. The crawler starts reading career sites again within seconds.", "ok");
  };
  return (<ActionButton className={`btn small ${on ? "danger" : ""}`} run={flip} disabled={!isAdmin} title={isAdmin ? undefined : "Only admins can pause the crawler"}>{on ? "⏸ Pause crawler" : "▶ Resume crawler"}</ActionButton>);
}

/** What the crawler is doing right now: a status light, one headline, one detail line, the worker's pulse and the pause control, in one tidy row. */
export function StatusBanner({ s, rate, control }: { s?: WorkerStatus; rate?: number; control?: React.ReactNode }) {
  if (!s) return <div className="cstatus"><span className="cdot" /><div className="cs-main"><b className="cs-title">Checking the worker…</b></div></div>;
  const sites = <><b>{s.inflight}</b> career site{s.inflight === 1 ? "" : "s"} being read</>;
  const head = { running: "Crawler running", idle: "Crawler running", paused: "Crawler paused", stopped: "Crawler stopped" }[s.state];
  const detail = {
    running: <>{sites}{s.task ? <> · task <b>{s.task.replace(/_/g, " ")}</b></> : null}{rate ? <> · {rate}/min</> : null}</>,
    idle: <>Nothing due right now. It checks again every few seconds.</>,
    paused: <>{s.why}{s.next_start ? <> · starts again <b>{at(s.next_start)}</b></> : null}{s.inflight ? <> · finishing <b>{s.inflight}</b> site{s.inflight === 1 ? "" : "s"} already started</> : null}. Tasks you start still run.</>,
    stopped: <>{s.note}</>,
  }[s.state];
  const pulse = s.state !== "stopped" && s.seen_seconds != null;
  return (<div className={`cstatus ${s.state}`} role="status"><span className="cdot" aria-hidden />
    <div className="cs-main"><b className="cs-title">{head}</b><span className="cs-sub">{detail}</span></div>
    {pulse && <div className="cs-meta"><span>{(s.workers?.length ?? 0) > 1 ? `${s.workers!.length} workers` : `Worker ${s.pid ? `#${s.pid}` : ""}`}</span><span>heartbeat {s.seen_seconds}s ago</span></div>}
    {control && <div className="cs-ctl">{control}</div>}</div>);
}

/** Every running worker: what it is on, and which one leads. Shown under the status bar while at least one worker reports. */
export function WorkerList({ s, title }: { s?: WorkerStatus; title: (kind: string) => string }) {
  const list = s?.workers ?? [];
  if (!list.length) return null;
  const old = list.some((w) => w.old);
  return (<section className="wlist" aria-label="Workers">
    <div className="wl-head"><b>Workers</b><span className="wl-count">{list.length}</span><span className="small muted">Each takes one task at a time. Add one by running <code>./run.sh worker</code> in another terminal.</span></div>
    <ul>{list.map((w) => <li key={w.id} className={w.task ? "busy" : ""}>
      <span className="wl-dot" aria-hidden />
      <div className="wl-main"><b>{w.task ? title(w.task) : w.state === "paused" ? "Waiting for tasks (crawling paused)" : w.lead ? "Running the automatic work" : "Ready for a task"}</b>
        <span className="small muted">#{w.pid} on {w.host}{w.task_id ? ` · task #${w.task_id}` : ""}{w.inflight ? ` · ${w.inflight} site${w.inflight === 1 ? "" : "s"} being read` : ""} · seen {w.seen_seconds}s ago</span></div>
      {w.lead && <span className="wl-tag" title="This worker alone starts automatic scans, alerts and e-mails">Lead</span>}
      {w.old && <span className="wl-tag old">Restart to update</span>}</li>)}</ul>
    {old && <p className="small muted">A worker marked &ldquo;Restart to update&rdquo; still runs the previous version. Restart it before running several.</p>}
  </section>);
}

export function ScheduleCard({ isAdmin }: { isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  const q = useQuery({ queryKey: ["admin-schedule"], refetchInterval: 30000, queryFn: () => api.get<Schedule>("/admin/schedule") });
  const [v, setV] = useState<Schedule | null>(null);
  useEffect(() => { if (q.data && !v) setV(q.data); }, [q.data, v]);
  if (!v) return <div className="card muted">Loading schedule…</div>;
  const set = (p: Partial<Schedule>) => setV({ ...v, ...p });
  const dirty = JSON.stringify({ ...v, allowed_now: 0, why: 0, next_start: 0 }) !== JSON.stringify({ ...q.data, allowed_now: 0, why: 0, next_start: 0 });
  const allDay = v.start === "00:00" && v.end === "24:00";
  const save = async () => { const cur = await api.get<Schedule>("/admin/schedule"); const r = await api.put<Schedule>("/admin/schedule", { ...v, parallel: cur.parallel }); setV(r); await qc.invalidateQueries({ queryKey: ["admin-schedule"] }); await qc.invalidateQueries({ queryKey: ["admin-worker"] }); notify(r.allowed_now ? "Saved. The crawler is allowed to run now." : `Saved. Paused: ${r.why}${r.next_start ? `, starts ${at(r.next_start)}` : ""}.`, "ok"); };
  return (<div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Schedule</h2><span className={`chip ${q.data?.allowed_now ? "ok" : "warn"} right`}>{q.data?.allowed_now ? "Allowed now" : `Paused${q.data?.next_start ? ` until ${at(q.data.next_start)}` : ""}`}</span></div>
    <fieldset disabled={!isAdmin} className="sched">
      <Switch checked={v.enabled} onChange={(e) => set({ enabled: e })} label="Crawl automatically" />
      <div className="cpick"><div className="cpick-l">Days</div><div className="cpick-row">{DAYS.map((d, i) => { const on = v.days.includes(i); return <button type="button" key={d} className={`cchip${on ? " on" : ""}`} aria-pressed={on} onClick={() => set({ days: on ? v.days.filter((x) => x !== i) : [...v.days, i].sort() })}>{d}</button>; })}</div></div>
      <div className="row"><label className="row small"><input type="checkbox" checked={allDay} onChange={(e) => set(e.target.checked ? { start: "00:00", end: "24:00" } : { start: "08:00", end: "20:00" })} /> All day</label>
        {!allDay && <><label className="small">From <input type="time" value={v.start} onChange={(e) => set({ start: e.target.value })} /></label><label className="small">to <input type="time" value={v.end === "24:00" ? "23:59" : v.end} onChange={(e) => set({ end: e.target.value })} /></label></>}
        <select value={v.tz} onChange={(e) => set({ tz: e.target.value })} aria-label="Time zone">{[...new Set([v.tz, ...TZ])].map((t) => <option key={t}>{t}</option>)}</select></div>
      <label className="small">Revisit each company every <b>{v.revisit_hours} h</b><input type="range" min={1} max={72} value={Math.min(72, v.revisit_hours)} onChange={(e) => set({ revisit_hours: +e.target.value })} style={{ width: "100%" }} /></label>
    </fieldset>
    {isAdmin ? <div className="row"><ActionButton className="btn" disabled={!dirty} run={save}>Save schedule</ActionButton>{dirty && <button className="btn ghost" onClick={() => setV(q.data!)}>Undo</button>}</div> : <div className="small muted">Only admins can change the schedule.</div>}
  </div>);
}

export function CountriesCard({ isAdmin }: { isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  const q = useQuery({ queryKey: ["admin-policy"], queryFn: () => api.get<Policy>("/admin/policy") });
  const [cs, setCs] = useState<string[] | null>(null); const [remote, setRemote] = useState(true);
  useEffect(() => { if (q.data && cs === null) { setCs(q.data.countries); setRemote(q.data.keep_remote); } }, [q.data, cs]);
  if (!q.data || cs === null) return <div className="card muted">Loading countries…</div>;
  const name = (c: string) => q.data!.places.countries.find((x) => x.code === c)?.name ?? c;
  const dirty = JSON.stringify(cs) !== JSON.stringify(q.data.countries) || remote !== q.data.keep_remote;
  const save = async () => { const p = q.data!; await api.put("/admin/policy", { countries: cs, keep_remote: remote, keep_domains: (p as unknown as { saved_domains?: string[]; keep_domains: string[] }).saved_domains ?? p.keep_domains, max_job_age_days: (p as unknown as { max_job_age_days: number }).max_job_age_days, delete_expired_after_days: (p as unknown as { delete_expired_after_days: number }).delete_expired_after_days }); await qc.invalidateQueries({ queryKey: ["admin-policy"] }); qc.invalidateQueries({ queryKey: ["sectors"] }); notify("Saved. New postings from these countries are kept from now on.", "ok"); };
  const discover = async (c: string) => { const r = await api.post<{ id: number }>("/admin/tasks", { kind: "discover_country", payload: { country: c } }); notify(`Looking for employers in ${name(c)} (task #${r.id}). Their jobs follow on the next scans.`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); };
  return (<div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Countries to collect</h2><span className="small muted right">{cs.length ? `${cs.length} countries` : "every country"}</span></div>
    <div className="small muted">The crawler keeps postings located in these countries{remote ? ", plus remote jobs open to them" : ""}. Users then pick any of them in their own feed.</div>
    {isAdmin ? <PlacePicker countries={cs} regions={[]} onChange={(c, r) => setCs([...new Set([...c, ...r.flatMap((k) => q.data!.places.regions.find((x) => x.key === k)?.countries ?? [])])])} />
      : <div className="cpick-row">{cs.map((c) => <span key={c} className="cchip on">{flag(c)} {name(c)}</span>)}</div>}
    {isAdmin && <Switch checked={remote} onChange={setRemote} label="Also keep remote jobs open to these countries (“Remote - Europe”, “Anywhere”)" />}
    {isAdmin && <div className="row"><ActionButton className="btn" disabled={!dirty} run={save}>Save countries</ActionButton>{dirty && <button className="btn ghost" onClick={() => { setCs(q.data!.countries); setRemote(q.data!.keep_remote); }}>Undo</button>}</div>}
    <div className="ctable">{(cs.length ? cs : Object.keys(q.data.by_country)).map((c) => <div key={c} className="crow"><span>{flag(c)} {name(c)}</span><span className="small muted">{num(q.data!.by_country[c] ?? 0)} open jobs</span>
      <ActionButton className="btn ghost small" run={() => discover(c)} title={`Find employers based in ${name(c)} from free public sources`}>Find employers</ActionButton></div>)}</div>
    <div className="small muted">Most employers come from Dutch sources so far. “Find employers” searches European Tech Map, OpenStreetMap and Wikipedia for that country; their career pages are then read like any other.</div>
  </div>);
}

const RECENT: [number, string][] = [[10, "Last 10 days"], [30, "Last month"], [90, "Last 3 months"], [180, "Last 6 months"], [0, "Any date"]];

/** How recent a posting must be to be collected: applies to career pages and job boards, and old stored jobs can be removed in one click. */
export function RecencyCard({ isAdmin }: { isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  const q = useQuery({ queryKey: ["admin-policy"], queryFn: () => api.get<Policy>("/admin/policy") });
  if (!q.data) return <div className="card muted">Loading…</div>;
  const p = q.data; const cur = p.max_job_age_days; const age = p.by_age ?? {};
  const older = (d: number) => (d ? age[`older_${d}`] ?? 0 : 0);
  const pick = async (d: number) => {
    await api.put("/admin/policy", { countries: p.countries, keep_remote: p.keep_remote, keep_domains: p.saved_domains ?? p.keep_domains, max_job_age_days: d, delete_expired_after_days: p.delete_expired_after_days });
    await qc.invalidateQueries({ queryKey: ["admin-policy"] });
    notify(d ? `Saved. From now on only postings from the last ${d} days are collected, from career pages and job boards.` : "Saved. Postings of any date are collected.", "ok");
  };
  const purge = async () => {
    if (!window.confirm(`Delete ${num(older(cur))} stored jobs older than ${cur} days? Jobs saved in someone's pipeline stay. This cannot be undone.`)) return;
    const r = await api.post<Record<string, number>>("/admin/maintenance/purge", {}); await qc.invalidateQueries({ queryKey: ["admin-policy"] });
    notify(`Removed ${num(r.too_old_deleted ?? 0)} old jobs.`, "ok");
  };
  return (<div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>How recent</h2><span className="small muted right">{num(age.open ?? 0)} open jobs stored</span></div>
    <div className="small muted">Collect only postings published in this period. Job boards are asked for this window directly; career-page postings older than it are skipped.</div>
    <div className="cpick-row" role="radiogroup" aria-label="How recent">{RECENT.map(([d, l]) => <button type="button" key={d} role="radio" aria-checked={cur === d} disabled={!isAdmin} className={`cchip${cur === d ? " on" : ""}`} onClick={() => cur !== d && pick(d)}
      title={d ? `${num(older(d))} stored jobs are older than this` : undefined}>{l}{d > 0 && <span className="small muted"> · {num(older(d))} older</span>}</button>)}</div>
    {cur > 0 && older(cur) > 0 && isAdmin && <div className="row"><span className="small">{num(older(cur))} stored jobs are older than {cur} days. They are removed in the daily clean-up, or now:</span><ActionButton className="btn ghost small" run={purge}>Remove them now</ActionButton></div>}
    <div className="small muted">{num(age.undated ?? 0)} postings give no publish date; for those the day the crawler first saw them counts.</div>
  </div>);
}
