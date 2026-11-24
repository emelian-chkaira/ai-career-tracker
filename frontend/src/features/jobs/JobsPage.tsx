import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { api, ApiError } from "@/shared/api/client";
import type { SearchParams, SearchResult } from "@/shared/api/types";
import { label, parseQs, qs } from "@/shared/lib/format";
import { SaveSearchButton } from "@/features/alerts/SaveSearchButton";
import { getConsent, getScoringCv, runBatch, useDocs, useStoredCv } from "@/features/fit/api";
import { CvPicker } from "@/features/cv/CvPicker";
import { isExternalAi, useAiSettings } from "@/features/ai/AiPanel";
import { toast } from "sonner";
import { useShortcuts } from "@/shared/lib/useShortcuts";
import { liveSearch, taskStatus, useJobFeed, useSetStage, useSuggest } from "./api";
import { Filters } from "./Filters";
import { useSentinel, ListEnd } from "@/shared/lib/useSentinel";
import { Drawer, Splitter, usePane } from "@/shared/ui/kit";
import { Icon } from "@/shared/ui/Icon";
import { Menu } from "./Menu";
import { FilterPills } from "./FilterPills";
import { JobCard } from "./JobCard";
import { JobDetail, JobDrawer } from "./JobDrawer";
import { useQueryClient } from "@tanstack/react-query";
import { openSetup } from "@/features/onboarding/SetupWizard";
import { useSectors } from "@/shared/api/meta";
import { flag, modeLabel } from "@/shared/lib/geo";
import { EmptyState } from "@/shared/ui";
import { CrawlNotice } from "./CrawlNotice";

const ARR = ["job_type", "domain", "language", "city", "skills", "sector", "country", "region", "work_mode"] as const;
function fromUrl(search: string, internships: boolean): SearchParams {
  const raw = parseQs(search); const p: Record<string, unknown> = { ...raw };
  for (const k of ARR) p[k] = raw[k] === undefined ? [] : ([] as string[]).concat(raw[k]);
  for (const k of ["remote", "sponsor", "remote_open"]) if (raw[k] !== undefined) p[k] = raw[k] === "true";
  for (const k of ["min_salary", "days", "page", "radius_km"]) if (raw[k] !== undefined) p[k] = Number(raw[k]);
  if (internships) p.kind = "internship";
  return { limit: 20, ...p } as SearchParams;
}

function useWide() {
  const [w, setW] = useState(() => window.matchMedia("(min-width:1101px)").matches);
  useEffect(() => { const m = window.matchMedia("(min-width:1101px)"); const f = () => setW(m.matches); m.addEventListener("change", f); return () => m.removeEventListener("change", f); }, []);
  return w;
}
const LEVEL: Record<string, string> = { internship: "Internship", traineeship: "Traineeship", junior: "Junior", job: "Medior", senior: "Senior" };

export function JobsPage({ internships = false }: { internships?: boolean }) {
  const [sp, setSp] = useSearchParams();
  const params = useMemo(() => fromUrl(sp.toString(), internships), [sp, internships]);
  const [q, setQ] = useState(params.q ?? ""); const [open, setOpen] = useState<number | null>(null);
  const { user } = useAuth(); const qc = useQueryClient(); const sec = useSectors().data;
  // Signed in: "My feed" (the profile fills every empty filter on the server) unless the URL says scope=all.
  const mine = !!user && params.scope !== "all";
  const feed = useMemo(() => ({ ...params, scope: user ? (mine ? "mine" : "all") : undefined } as SearchParams), [params, user, mine]);
  const { data, isFetching, error, more, loadingMore, next } = useJobFeed(feed);
  const prof = (data?.query?.profile ?? {}) as { sector?: string[]; country?: string[]; region?: string[]; work_mode?: string[]; cities?: string[]; job_type?: string[]; language?: string[]; sponsor?: boolean };
  const secName = (k: string) => sec?.sectors.find((s) => s.key === k)?.label ?? label(k); const sentinel = useSentinel(next, more);
  const sug = useSuggest(q.split(/\s+/).pop() ?? "");
  useEffect(() => setQ(params.q ?? ""), [params.q]);

  const update = (patch: Partial<SearchParams>, keepPage = false) => {
    const next = { ...params, ...patch, ...(keepPage ? {} : { page: 1 }) } as Record<string, unknown>; delete next.limit; delete next.kind;
    setSp(qs(next), { replace: true });
  };
  const [live, setLive] = useState(""); const [filtersOpen, setFiltersOpen] = useState(false);
  const active: { key: string; text: string; clear(): void }[] = [
    ...(["sector", "region", "country", "work_mode", "job_type", "domain", "language", "city", "skills"] as const).flatMap((f) => ((params[f] as string[] | undefined) ?? []).map((v) => ({ key: `${f}:${v}`,
      text: f === "sector" ? secName(v) : f === "country" ? `${flag(v)} ${sec?.countries.find((c) => c.code === v)?.name ?? v}` : f === "region" ? (sec?.regions.find((r) => r.key === v)?.label ?? v) : f === "work_mode" ? modeLabel(v) : label(v), clear: () => update({ [f]: ((params[f] as string[]) ?? []).filter((x) => x !== v) } as Partial<SearchParams>) }))),
    ...(params.remote ? [{ key: "remote", text: "Remote", clear: () => update({ remote: undefined }) }] : []), ...(params.sponsor ? [{ key: "sponsor", text: "Visa sponsor", clear: () => update({ sponsor: undefined }) }] : []),
    ...(params.days ? [{ key: "days", text: `Last ${params.days}d`, clear: () => update({ days: undefined }) }] : []), ...(params.min_salary ? [{ key: "sal", text: `≥ €${params.min_salary}`, clear: () => update({ min_salary: undefined }) }] : []),
    ...(params.near && params.radius_km ? [{ key: "near", text: `${params.radius_km} km of ${params.near}`, clear: () => update({ near: undefined, radius_km: undefined }) }] : [])];
  const cvSaved = useStoredCv(!!user); const aiSet = useAiSettings(); const [batch, setBatch] = useState(""); const [scoreCv, setScoreCv] = useState<number | null>(getScoringCv()); const cvDocs = useDocs("cv", !!user);
  const canScore = !!user && !!cvSaved.data && !!aiSet.data?.provider;
  /** Only when asked: the AI reads your CV against the 60 most promising jobs of the current view (the whole filtered feed, best guess first). */
  async function scoreTop() {
    if (isExternalAi(aiSet.data) && !getConsent()) { setBatch("Open any job and tick the AI consent box first (your CV is sent to the provider)."); return; }
    try {
      setBatch("Choosing the best 60 jobs in this view…");
      const r0 = await api.get<SearchResult>("/jobs", { ...feed, sort: "fit", limit: 60, page: 1 } as Record<string, unknown>);
      const want = (cvDocs.data ?? []).find((d) => (scoreCv !== null ? d.id === scoreCv : d.is_default))?.name;   // jobs scored with another CV are scored again with the chosen one
      const ids = r0.items.filter((j) => !j.ai || (!!want && !!j.ai.cv_name && j.ai.cv_name !== want)).map((j) => j.id);
      if (!ids.length) { setBatch("The best 60 jobs in this view are already scored."); return; }
      setBatch(`AI scoring ${ids.length} jobs…`);
      const r = await runBatch(ids, getConsent(), (t) => setBatch(`AI scoring ${t.progress?.done ?? 0} / ${t.progress?.total ?? ids.length}`), scoreCv);
      setBatch(r.status === "done" ? `Scored ${r.progress?.scored ?? 0}${r.progress?.failed ? `, ${r.progress.failed} failed` : ""}. Sort by AI score to see them first.` : `Stopped: ${r.error ?? r.progress?.error ?? "unknown error"}`);
      qc.invalidateQueries({ queryKey: ["jobs"] });
    } catch (e) { setBatch(e instanceof ApiError ? e.message : (e as Error).message); }
  }
  async function runLive() {
    if (!q.trim()) return;
    try {
      setLive("Re-reading career pages…"); const { task_id } = await liveSearch(q);
      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 3000)); const t = await taskStatus(task_id);
        if (t.status === "done" || t.status === "failed") { setLive(t.status === "done" ? "Live search finished — results refreshed." : "Live search failed."); qc.invalidateQueries({ queryKey: ["jobs"] }); return; }
        setLive(`Re-reading career pages… ${JSON.stringify(t.progress ?? {})}`);
      }
      setLive("Still running in the background; refresh in a minute.");
    } catch (e) { setLive(e instanceof ApiError ? e.message : "Live search unavailable"); }
  }
  const wide = useWide(); const pane = usePane("jobs-list", 420, 300, 720); const setStage = useSetStage(); const [picked, setPicked] = useState<Set<number>>(new Set());
  const items = data?.items ?? []; const idx = items.findIndex((j) => j.id === open);
  const pick = (id: number, on: boolean) => setPicked((p) => { const n = new Set(p); on ? n.add(id) : n.delete(id); return n; });
  const bulk = async (stage: string) => {
    const ids = [...picked]; const results = await Promise.allSettled(ids.map((id) => setStage.mutateAsync({ id, stage }))); const bad = results.filter((r) => r.status === "rejected").length;
    setPicked(new Set()); bad ? toast.error(`${ids.length - bad} updated, ${bad} failed`) : toast.success(`${ids.length} job${ids.length > 1 ? "s" : ""} marked ${stage}`);
  };
  useShortcuts({
    j: () => { if (items.length) { setOpen(items[Math.min(items.length - 1, idx + 1)].id); if (idx >= items.length - 3) next(); } }, k: () => items.length && setOpen(items[Math.max(0, idx - 1)].id),
    "/": () => document.querySelector<HTMLInputElement>(".sbar input[type=search]")?.focus(),
    s: () => { if (user && open != null) setStage.mutate({ id: open, stage: "shortlisted" }, { onSuccess: () => toast.success("Shortlisted") }); },
    x: () => { if (open != null) pick(open, !picked.has(open)); },
  });
  useEffect(() => { if (wide && data?.items.length && (open == null || !data.items.some((j) => j.id === open))) setOpen(data.items[0].id); }, [wide, data]);   // eslint-disable-line react-hooks/exhaustive-deps
  const sorts: [string, string][] = [...(params.q ? [["", "Relevance"], ["newest", "Newest"]] : [["", "Newest"]]), ...(user ? [["ai_fit", "AI score"]] : [])] as [string, string][];
  const where = mine ? [(prof.sector ?? []).map(secName).join(", "), [...(prof.country ?? []).map((c) => `${flag(c)} ${c}`), ...(prof.region ?? []).map((r) => sec?.regions.find((x) => x.key === r)?.label ?? r)].join(", "), (prof.work_mode ?? []).map(modeLabel).join("/"), (prof.job_type ?? []).map((x) => LEVEL[x] ?? x).join(", ")].filter(Boolean).join(" · ") : "";
  return (<div className={wide ? "jfull" : ""}>
    <div className="jb">
      <div className="jb1">
        <div className="seg"><Link to="/" className={internships ? "" : "on"}>Jobs</Link><Link to="/internships" className={internships ? "on" : ""}>Internships</Link></div>
        {user ? <div className="seg" aria-label="Whose jobs"><button className={mine ? "on" : ""} aria-pressed={mine} onClick={() => update({ scope: undefined })}>My feed</button><button className={!mine ? "on" : ""} aria-pressed={!mine} onClick={() => update({ scope: "all" })}>All jobs</button></div>
          : <select className="jfield" value={(params.sector ?? [])[0] ?? "tech"} onChange={(e) => update({ sector: [e.target.value] })} aria-label="Field">{(sec?.sectors ?? []).map((s) => <option key={s.key} value={s.key}>{s.label} ({s.jobs})</option>)}</select>}
        <form className="sbar" onSubmit={(e) => { e.preventDefault(); update({ q }); }}>
          <Icon name="search" size={18} />
          <input type="search" list="sug" placeholder={internships ? "Search internships: title, skill or company" : "Search title, skill or company"} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search jobs" />
          <datalist id="sug">{[...(sug.data?.skills ?? []), ...(sug.data?.titles ?? [])].slice(0, 8).map((s2) => <option key={s2} value={q.replace(/\S*$/, "") + s2} />)}</datalist>
          <button className="btn">Search</button>
        </form>
        <Menu label="More ▾">
          <button type="button" onClick={runLive} disabled={!q.trim()} title={q.trim() ? "" : "Type a search first"}>Re-read employers live{!q.trim() ? " (type a search)" : ""}</button>
          {user && <div className="menu-item"><SaveSearchButton params={feed} /></div>}
          {user && <button type="button" onClick={openSetup}>Edit my preferences</button>}
          <div className="menu-note">Keys: j / k move, / search, s shortlist, x select</div>
        </Menu>
      </div>
      <div className="jb2">
        <FilterPills params={params} onChange={(p) => update(p)} onAll={() => setFiltersOpen(true)} count={active.length} />
        <div className="jb2r">
          <span className="jcount"><strong>{data ? `${data.total.toLocaleString()} ${internships ? "internship" : "job"}${data.total === 1 ? "" : "s"}` : "…"}</strong>{isFetching && <em>updating…</em>}{batch && <em>{batch}</em>}{live && <em>{live}</em>}</span>
          <select className="jsort" value={params.sort ?? ""} onChange={(e) => update({ sort: e.target.value || undefined })} aria-label="Order">{sorts.map(([v, name]) => <option key={v || "default"} value={v}>{name}</option>)}</select>
          {canScore && <CvPicker value={scoreCv} onChange={setScoreCv} label="with CV" />}
          {canScore && <button type="button" className="btn small" onClick={scoreTop} disabled={batch.startsWith("AI scoring") || batch.startsWith("Choosing")} title="The AI reads your CV against the 60 most promising jobs in this view">✦ AI score best 60</button>}
        </div>
      </div>
      {user && params.q?.trim() && <div className="alertbar"><span>🔔 Get notified about new <b>“{params.q}”</b> jobs</span><SaveSearchButton params={feed} /></div>}
      {(active.length > 0 || where) && <div className="chips-row">
        {active.map((c) => <button key={c.key} className="achip" onClick={c.clear} aria-label={`Remove filter ${c.text}`}>{c.text}<span aria-hidden>✕</span></button>)}
        {active.length > 0 && <button className="linkbtn" onClick={() => setSp(qs({ q: params.q, mode: params.mode, sort: params.sort }), { replace: true })}>Clear all</button>}
        {!active.length && where && <span className="fact">Showing jobs for your profile: {where}</span>}
      </div>}
    </div>
    <Drawer open={filtersOpen} onOpenChange={setFiltersOpen} title="Filters" side="left" size={360}><Filters params={params} facets={data?.facets} onChange={(p) => update(p)} /></Drawer>
    <div className={"layout" + (wide ? "" : " noDetail")} style={{ "--wl": `${pane.width}px` } as React.CSSProperties}>
      <div className="card list">
        {(params.country?.length || params.region?.length) ? <CrawlNotice country={params.country} region={params.region} /> : mine ? <CrawlNotice /> : null}
        {!data && !error && Array.from({ length: 6 }, (_, i) => <div key={i} className="job"><div className="skel logo" /><div className="grow stack" style={{ gap: 8 }}><div className="skel" style={{ height: 16, width: "70%" }} /><div className="skel" style={{ height: 12, width: "45%" }} /></div></div>)}
        {error && <div className="empty err">{(error as Error).message}</div>}
        {data && !data.items.length && (mine && Object.keys(prof).length
          ? <EmptyState icon={<Icon name="filter" size={20} />} title="No jobs match your profile yet" action={<div className="row"><button className="btn small" onClick={() => update({ scope: "all" })}>Show all jobs</button><button className="btn ghost small" onClick={openSetup}>Edit preferences</button></div>}>Fields outside tech are still small: more employers are added as they are crawled.</EmptyState>
          : <EmptyState icon={<Icon name="search" size={20} />} title="Nothing matches just yet">Try fewer filters, or ask us to re-read the employers live.</EmptyState>)}
        {data?.items.map((j) => <JobCard key={j.id} job={j} selected={wide && open === j.id} onOpen={setOpen} picked={picked.has(j.id)} onPick={user ? pick : undefined} />)}
        {picked.size > 0 && <div className="bulkbar"><b>{picked.size} selected</b><button className="btn small" onClick={() => bulk("shortlisted")}>Shortlist</button><button className="btn ghost small" onClick={() => bulk("applied")}>Mark applied</button><button className="btn ghost small" onClick={() => bulk("skipped")}>Skip</button><button className="btn ghost small right" onClick={() => setPicked(new Set())}>Clear</button></div>}
        {data && <ListEnd sentinel={sentinel} more={more} loading={loadingMore} count={data.items.length} total={data.total} />}
      </div>
      {wide && <Splitter props={pane.props} label="Resize job list" />}
      {wide && <div className="card detail inline">{open != null ? <JobDetail id={open} /> : <div className="empty">Pick a job on the left and the details will show up here.</div>}</div>}
    </div>
    {!wide && open != null && <JobDrawer id={open} onClose={() => setOpen(null)} />}
  </div>);
}
