import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { Switch } from "@/shared/ui/kit";
import { flag } from "@/shared/lib/geo";
import { PlacePicker } from "@/features/onboarding/SetupWizard";
import { ActionButton, num, useNotify } from "./ui";

export type WorkerStatus = { state: "running" | "idle" | "paused" | "stopped"; seen_seconds: number | null; pid?: number; host?: string; inflight: number; task?: string | null; allowed: boolean; why: string; next_start: string | null; note: string };
type Schedule = { enabled: boolean; days: number[]; start: string; end: string; tz: string; revisit_hours: number; parallel: number; allowed_now: boolean; why: string; next_start: string | null };
type Policy = { countries: string[]; keep_remote: boolean; by_country: Record<string, number>; places: { countries: { code: string; name: string; regions: string[] }[]; regions: { key: string; label: string; countries: string[] }[] } };

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

/** One line that says plainly what the crawler is doing, with a live dot. */
export function StatusBanner({ s, rate, control }: { s?: WorkerStatus; rate?: number; control?: React.ReactNode }) {
  if (!s) return <div className="cstatus"><span className="cdot" /> Checking the worker…</div>;
  const text = {
    running: <>Running · <b>{s.inflight}</b> career site{s.inflight === 1 ? "" : "s"} being read{s.task ? <> · task <b>{s.task.replace(/_/g, " ")}</b></> : null}{rate ? <> · {rate}/min</> : null}</>,
    idle: <>Running · nothing due right now, it checks again every few seconds</>,
    paused: <>Paused · {s.why}{s.next_start ? <> · starts again <b>{at(s.next_start)}</b></> : null}{s.inflight ? <> · finishing <b>{s.inflight}</b> site{s.inflight === 1 ? "" : "s"} it had already started</> : null}. Tasks you start still run.</>,
    stopped: <>Stopped · {s.note}</>,
  }[s.state];
  return (<div className={`cstatus ${s.state}`} role="status"><span className="cdot" aria-hidden />{text}
    {s.state !== "stopped" && s.seen_seconds != null && <span className="small muted right">worker {s.pid ? `#${s.pid}` : ""} · heartbeat {s.seen_seconds}s ago</span>}
    {control && <span className={s.state !== "stopped" && s.seen_seconds != null ? "" : "right"}>{control}</span>}</div>);
}

const STEPS: [string, string, string][] = [
  ["🔎", "Discover", "Finds employers in free public sources: European Tech Map, OpenStreetMap, Wikipedia/Wikidata, public ATS boards."],
  ["🧭", "Locate the careers page", "Visits each website, follows the 'jobs/careers/werken bij' link and recognises the job system (Greenhouse, Lever, Workday, Personio…)."],
  ["📥", "Read postings", "Reads every posting through that system's public feed, or from the page itself. Polite: robots.txt and rate limits."],
  ["🏷️", "Understand them", "Country, city, remote/hybrid, field, level, language, salary and skills, from the posting text."],
  ["🗂️", "Keep what you want", "Stores only the countries and fields set below; removes duplicates; marks postings that disappeared as expired."],
  ["🔔", "Tell people", "Each user's feed, match score and alerts pick up new jobs within minutes."],
];

export function HowItWorks() {
  return (<div className="card stack"><h2 style={{ margin: 0 }}>How the crawler works</h2>
    <ol className="hiw">{STEPS.map(([i, t, d], n) => <li key={t} style={{ animationDelay: `${n * 70}ms` }}><span className="hiw-i" aria-hidden>{i}</span><b>{t}</b><span className="small muted">{d}</span></li>)}</ol>
    <div className="small muted">Each company is visited again after the revisit interval (or later when its site keeps failing). The schedule decides when this happens on its own.</div></div>);
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
  const save = async () => { const r = await api.put<Schedule>("/admin/schedule", v); setV(r); await qc.invalidateQueries({ queryKey: ["admin-schedule"] }); await qc.invalidateQueries({ queryKey: ["admin-worker"] }); notify(r.allowed_now ? "Saved. The crawler is allowed to run now." : `Saved. Paused: ${r.why}${r.next_start ? `, starts ${at(r.next_start)}` : ""}.`, "ok"); };
  return (<div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Schedule</h2><span className={`chip ${q.data?.allowed_now ? "ok" : "warn"} right`}>{q.data?.allowed_now ? "Allowed now" : `Paused${q.data?.next_start ? ` until ${at(q.data.next_start)}` : ""}`}</span></div>
    <fieldset disabled={!isAdmin} className="sched">
      <Switch checked={v.enabled} onChange={(e) => set({ enabled: e })} label="Crawl automatically" />
      <div className="cpick"><div className="cpick-l">Days</div><div className="cpick-row">{DAYS.map((d, i) => { const on = v.days.includes(i); return <button type="button" key={d} className={`cchip${on ? " on" : ""}`} aria-pressed={on} onClick={() => set({ days: on ? v.days.filter((x) => x !== i) : [...v.days, i].sort() })}>{d}</button>; })}</div></div>
      <div className="row"><label className="row small"><input type="checkbox" checked={allDay} onChange={(e) => set(e.target.checked ? { start: "00:00", end: "24:00" } : { start: "08:00", end: "20:00" })} /> All day</label>
        {!allDay && <><label className="small">From <input type="time" value={v.start} onChange={(e) => set({ start: e.target.value })} /></label><label className="small">to <input type="time" value={v.end === "24:00" ? "23:59" : v.end} onChange={(e) => set({ end: e.target.value })} /></label></>}
        <select value={v.tz} onChange={(e) => set({ tz: e.target.value })} aria-label="Time zone">{[...new Set([v.tz, ...TZ])].map((t) => <option key={t}>{t}</option>)}</select></div>
      <label className="small">Revisit each company every <b>{v.revisit_hours} h</b><input type="range" min={1} max={72} value={Math.min(72, v.revisit_hours)} onChange={(e) => set({ revisit_hours: +e.target.value })} style={{ width: "100%" }} /></label>
      <label className="small">Read up to <b>{v.parallel}</b> career sites at once<input type="range" min={1} max={40} value={v.parallel} onChange={(e) => set({ parallel: +e.target.value })} style={{ width: "100%" }} /></label>
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
  const save = async () => { const p = q.data!; await api.put("/admin/policy", { countries: cs, keep_remote: remote, keep_domains: (p as unknown as { keep_domains: string[] }).keep_domains, max_job_age_days: (p as unknown as { max_job_age_days: number }).max_job_age_days, delete_expired_after_days: (p as unknown as { delete_expired_after_days: number }).delete_expired_after_days }); await qc.invalidateQueries({ queryKey: ["admin-policy"] }); qc.invalidateQueries({ queryKey: ["sectors"] }); notify("Saved. New postings from these countries are kept from now on.", "ok"); };
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
