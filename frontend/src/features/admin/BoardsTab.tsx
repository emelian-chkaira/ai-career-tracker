import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { flag } from "@/shared/lib/geo";
import { ChipPicker } from "@/features/onboarding/SetupWizard";
import { useSectors } from "@/shared/api/meta";
import { ActionButton, ago, num, useNotify } from "./ui";
import { BoardIcon } from "@/shared/ui/BoardIcon";
import { TaskCard } from "./RunningNow";

type Health = { site: string; label: string; note: string; enabled: boolean; resting_until: string | null; last_ok?: string; last_run?: string; last_error?: string; error_at?: string; kind?: string; found_total?: number; found_last?: number; blocks_in_row?: number };
type Plan = { sites: string[]; terms: { term: string; from: string }[]; countries: string[]; searches: { term: string; country: string; boards: { site: string; where: string; skip: string | null }[] }[]; dropped: number; cap: number; results_per_board: number; requests: number };
type Overview = { enabled: boolean; installed: boolean; every_hours: number; health: Health[]; plan: Plan };
type Task = { id: number; kind: string; status: string; error?: string | null; created_at: string; finished_at?: string | null;
  progress?: { done?: number; total?: number; current?: string; found?: number; new_jobs?: number; blocked?: number; errors?: number; skipped?: number; log?: string[]; per_site?: Record<string, { found: number; new: number; errors: number; skipped: number }>; plan?: { terms: string[]; countries: string[]; sites: string[] } } };
const time = (iso?: string | null) => (iso ? new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "");

function BoardCard({ h, on, toggle }: { h: Health; on: boolean; toggle(): void }) {
  const state = !h.enabled ? ["off", "Off in settings"] : h.resting_until ? ["rest", `Resting until ${time(h.resting_until)}`] : h.kind && h.error_at && (!h.last_ok || h.error_at > h.last_ok) ? ["bad", "Last run failed"] : h.last_ok ? ["ok", "Working"] : ["new", "Not run yet"];
  return (<div className={`bcard ${state[0]}${on ? " on" : ""}`}>
    <div className="row" style={{ gap: 8 }}><label className="row" style={{ gap: 6 }}><input type="checkbox" checked={on} disabled={!h.enabled} onChange={toggle} /><BoardIcon board={h.site} size={22} /><b>{h.label}</b></label><span className={`bstate ${state[0]}`}>{state[1]}</span></div>
    <div className="small muted">{h.note}</div>
    <div className="bfacts small">
      <span>Last success: <b>{h.last_ok ? ago(h.last_ok) : "never"}</b></span>
      <span>Found in total: <b>{num(h.found_total ?? 0)}</b></span>
      {h.last_error && <span className="berr" title={h.last_error}>{h.kind === "blocked" ? "Blocked" : "Error"} {h.error_at ? ago(h.error_at) : ""}: {h.last_error.slice(0, 90)}</span>}
    </div></div>);
}

/** EXPERIMENTAL job boards: health per board, exactly what the next search looks for (and why), a live preview, and the run as it happens. */
export function BoardsTab() {
  const qc = useQueryClient(); const notify = useNotify(); const sec = useSectors().data;
  const ov = useQuery({ queryKey: ["admin-boards"], refetchInterval: 20000, queryFn: () => api.get<Overview>("/admin/boards") });
  const tasks = useQuery({ queryKey: ["admin-tasks"], refetchInterval: 3000, queryFn: () => api.get<Task[]>("/admin/tasks") });
  const [terms, setTerms] = useState<string[] | null>(null); const [countries, setCountries] = useState<string[] | null>(null); const [sites, setSites] = useState<string[] | null>(null);
  const d = ov.data;
  useEffect(() => { if (d && terms === null) { setTerms(d.plan.terms.map((t) => t.term)); setCountries(d.plan.countries); setSites(d.plan.sites); } }, [d, terms]);
  const origin = useMemo(() => Object.fromEntries((d?.plan.terms ?? []).map((t) => [t.term, t.from])), [d]);
  const key = JSON.stringify([terms, countries, sites]);
  const preview = useQuery({ queryKey: ["board-plan", key], enabled: terms !== null, placeholderData: (x) => x,
    queryFn: () => api.post<Plan>("/admin/boards/plan", { terms, countries, sites }) });
  const run = tasks.data?.find((t) => t.kind === "board_search");
  const live = run && (run.status === "running" || run.status === "queued");
  if (!d) return <div className="card muted">Loading job boards…</div>;
  const p = preview.data ?? d.plan; const cname = (c: string) => sec?.countries.find((x) => x.code === c)?.name ?? c;
  const start = async () => { const r = await api.post<{ id: number }>("/admin/tasks", { kind: "board_search", payload: { terms, countries, sites } }); notify(`Board search started (task #${r.id}): ${p.searches.length} searches.`, "ok"); qc.invalidateQueries({ queryKey: ["admin-tasks"] }); };
  const pr = run?.progress ?? {};
  return (<div className="stack fadein">
    <div className="notice">⚠️ <b>Experimental.</b> These boards' terms do not allow automated searching and they block busy visitors. The crawler stays polite: one board at a time, requests spaced out, and a board that blocks it <b>rests</b> (10 min for LinkedIn, doubling if it happens again) instead of being pushed. Use it for personal job hunting.</div>
    {!d.enabled && <div className="card stack"><h2 style={{ margin: 0 }}>Switched off</h2><div className="small">Add <code>CAREERS_BOARD_SITES=linkedin,indeed,glassdoor,bayt</code> to <code>backend/.env.local</code>, run <code>pip install -r requirements-boards.txt</code> and restart the API and worker.</div></div>}
    {d.enabled && !d.installed && <div className="notice err">JobSpy is not installed in this API's Python: <code>pip install -r requirements-boards.txt</code>, then restart.</div>}

    <div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Boards</h2><span className="small muted right">{d.every_hours ? `Runs by itself every ${d.every_hours} h while the crawler is allowed to run` : "Runs only when you start it"}</span></div>
      <div className="bgrid">{d.health.map((h) => <BoardCard key={h.site} h={h} on={(sites ?? []).includes(h.site)} toggle={() => setSites((s) => (s ?? []).includes(h.site) ? (s ?? []).filter((x) => x !== h.site) : [...(s ?? []), h.site])} />)}</div></div>

    <div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>What the next search looks for</h2><span className="small muted right">Changes here apply to “Search now”; the automatic run uses users' preferences.</span></div>
      <div className="sgrid2" style={{ alignItems: "start" }}>
        <div className="stack" style={{ gap: 6 }}>
          <ChipPicker label="Keywords (job titles)" value={terms ?? []} onChange={setTerms} placeholder="Add a keyword, e.g. Data Analyst" max={12} />
          <ul className="origins small">{(terms ?? []).map((t) => <li key={t}><b>{t}</b> <span className="muted">— {origin[t] ?? "added by you for this run"}</span></li>)}</ul>
          <button className="linkbtn small" onClick={() => { setTerms(d.plan.terms.map((t) => t.term)); setCountries(d.plan.countries); setSites(d.plan.sites); }}>Reset to users' preferences</button>
        </div>
        <div className="stack" style={{ gap: 6 }}>
          <div className="cpick"><div className="cpick-l">Countries</div><div className="cpick-row">{(countries ?? []).map((c) => <button key={c} type="button" className="cchip on" onClick={() => setCountries((x) => (x ?? []).filter((y) => y !== c))}>{flag(c)} {cname(c)} ✕</button>)}
            <select className="cpick-in" value="" onChange={(e) => e.target.value && setCountries((x) => [...new Set([...(x ?? []), e.target.value])])} aria-label="Add a country"><option value="">+ Add a country</option>{sec?.countries.filter((c) => !(countries ?? []).includes(c.code)).map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}</select></div></div>
          <div className="bsum"><div><b>{p.searches.length}</b><span>searches</span></div><div><b>{p.requests}</b><span>board requests</span></div><div><b>~{num(p.requests * p.results_per_board)}</b><span>postings at most</span></div></div>
          {p.dropped > 0 && <div className="small warn">{p.dropped} more keyword × country combinations are left out: one run does at most {p.cap} searches (CAREERS_BOARD_MAX_SEARCHES). Remove keywords or countries to choose which.</div>}
        </div></div>
      <div className="tablewrap"><table className="dtable splan"><thead><tr><th>#</th><th>Keyword</th><th>Country</th>{(p.sites ?? []).map((s) => <th key={s}><span className="row" style={{ gap: 5, flexWrap: "nowrap" }}><BoardIcon board={s} size={15} />{d.health.find((h) => h.site === s)?.label ?? s}</span></th>)}</tr></thead>
        <tbody>{p.searches.map((s, i) => <tr key={`${s.term}-${s.country}`}><td className="muted">{i + 1}</td><td><b>{s.term}</b></td><td>{flag(s.country)} {s.country}</td>
          {s.boards.map((b) => <td key={b.site} className="small">{b.skip ? <span className="muted" title={b.skip}>skipped · {b.skip.length > 28 ? b.skip.slice(0, 28) + "…" : b.skip}</span> : <span>searches “{b.where}”</span>}</td>)}</tr>)}</tbody></table></div>
      <div className="row"><ActionButton className="btn" disabled={!d.enabled || !d.installed || !!live || !p.requests} run={start} title={!p.requests ? "Nothing to search: every board is skipped" : undefined}>{live ? "Running…" : `▶ Search now (${p.searches.length} searches)`}</ActionButton>
        <span className="small muted">Each finished search is saved right away, so stopping early keeps what was found.</span></div></div>

    {run && <div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>{live ? "Searching now" : "Last run"}</h2><span className={`chip ${run.status === "done" ? "ok" : run.status === "failed" ? "bad" : "warn"} right`}>{run.status}{run.finished_at ? ` · ${ago(run.finished_at)}` : ""}</span></div>
      {run.error && <div className="notice err">{run.error}</div>}
      {pr.total ? <div><div className="row small muted" style={{ justifyContent: "space-between" }}><span>{live && pr.current ? <>Now: <b>{pr.current}</b></> : `${pr.done} of ${pr.total} searches`}</span><span>{pr.done}/{pr.total}</span></div>
        <div className="pbar"><div style={{ width: `${Math.round(((pr.done ?? 0) / pr.total) * 100)}%` }} /></div></div> : null}
      <div className="bsum"><div><b>{num(pr.found ?? 0)}</b><span>postings found</span></div><div><b>{num(pr.new_jobs ?? 0)}</b><span>new jobs saved</span></div><div><b>{pr.blocked ?? 0}</b><span>blocked</span></div><div><b>{pr.skipped ?? 0}</b><span>skipped</span></div></div>
      {live && <TaskCard t={run as never} compact />}
      {pr.per_site && <div className="cpick-row">{Object.entries(pr.per_site).map(([s, v]) => <span key={s} className={`cchip ${v.errors ? "" : "on"}`}><BoardIcon board={s} size={14} /> {d.health.find((h) => h.site === s)?.label ?? s}: {v.found} found, {v.new} new{v.errors ? `, ${v.errors} failed` : ""}{v.skipped ? `, ${v.skipped} skipped` : ""}</span>)}</div>}
      {!!pr.log?.length && <ol className="blog small">{[...pr.log].reverse().map((l, i) => <li key={i}>{l}</li>)}</ol>}
    </div>}
  </div>);
}
