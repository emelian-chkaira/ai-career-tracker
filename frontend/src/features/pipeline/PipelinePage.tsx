import { Menu, usePersisted } from "@/shared/ui/kit";
import { Logo } from "@/features/jobs/JobCard";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/shared/api/client";
import type { Job } from "@/shared/api/types";
import { label, ago } from "@/shared/lib/format";
import { useSetStage } from "@/features/jobs/api";
import { JobDrawer } from "@/features/jobs/JobDrawer";
import { FitBadge } from "@/features/fit/FitPanel";
import { useStats } from "@/features/track/api";
import { AlertsPage } from "@/features/alerts/AlertsPage";

const day = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "");
const FUNNEL: [string, string][] = [["applied", "Applied"], ["screening", "Recruiter screen"], ["assessment", "Assessment"], ["team_match", "Team match"], ["interview", "Technical interview"], ["final_round", "Final round"], ["offer", "Offer"]];

function Spark({ data }: { data: { day: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count)); const w = 100 / data.length;
  return (<svg viewBox="0 0 100 24" preserveAspectRatio="none" role="img" aria-label="Applications per day" className="spark">
    {data.map((d, i) => <rect key={d.day} x={i * w + 0.2} width={w - 0.4} y={24 - Math.max(0.6, (d.count / max) * 22)} height={Math.max(0.6, (d.count / max) * 22)} rx="0.4" fill="var(--brand)"><title>{`${d.day}: ${d.count}`}</title></rect>)}</svg>);
}

/** One slim strip: the numbers that matter, the day range, a sparkline and how far applications get. */
function Stats() {
  const [days, setDays] = usePersisted("stats:days", 30); const { data: s } = useStats(days); if (!s || !s.total) return null;
  const top = Math.max(1, s.funnel.applied);
  return (<div className="card pstats">
    <div className="kpi"><b>{s.active}</b><span>active</span></div>
    <div className="kpi"><b>{s.response_rate == null ? "–" : `${Math.round(s.response_rate * 100)}%`}</b><span>heard back</span></div>
    <div className="kpi"><b>{s.avg_days_to_response == null ? "–" : `${s.avg_days_to_response}d`}</b><span>avg. reply</span></div>
    <div className={`kpi${s.follow_ups_due ? " due" : ""}`}><b>{s.follow_ups_due}</b><span>follow-ups due</span></div>
    {!!s.applications_per_day && <div className="spark-w"><Spark data={s.applications_per_day} /><span className="small muted">applications, last {days} days</span></div>}
    {s.funnel.applied > 0 && <div className="fchips" aria-label="How far applications get">{FUNNEL.map(([k, name]) => <span key={k} className="fchip" title={`${s.funnel[k]} of ${top} applications reached ${name}`}>{name} <b>{s.funnel[k]}</b></span>)}</div>}
    <div className="seg right" role="group" aria-label="Day range">{[7, 14, 30, 90].map((d) => <button key={d} className={days === d ? "on" : ""} aria-pressed={days === d} onClick={() => setDays(d)}>{d}d</button>)}</div></div>);
}

export function PipelinePage() {
  const { data } = useQuery({ queryKey: ["pipeline"], queryFn: () => api.get<{ stages: string[]; items: Job[] }>("/me/pipeline") });
  const set = useSetStage(); const [mins, setMins] = usePersisted<Record<string, boolean>>("pipeline:min", {}); const [view, setView] = useState<"board" | "alerts">("board"); const [open, setOpen] = useState<number | null>(null); const [over, setOver] = useState<string | null>(null);
  if (!data) return <p className="muted">Loading…</p>;
  const stages = data.stages.filter((s) => s !== "skipped");
  const drop = (s: string, e: React.DragEvent) => { e.preventDefault(); setOver(null); const id = Number(e.dataTransfer.getData("text/plain")); const j = data.items.find((x) => x.id === id); if (j && j.stage !== s) set.mutate({ id, stage: s }); };
  return (<div className="pfull"><div className="row" style={{ alignItems: "center" }}><h1 style={{ margin: 0 }}>Pipeline</h1><span className="muted small">Drag a card to move it. Every change is kept in that job's timeline.</span>
      <div className="seg right" role="tablist" aria-label="Pipeline view"><button role="tab" aria-selected={view === "board"} className={view === "board" ? "on" : ""} onClick={() => setView("board")}>Board</button><button role="tab" aria-selected={view === "alerts"} className={view === "alerts" ? "on" : ""} onClick={() => setView("alerts")}>Saved searches & alerts</button></div></div>
    {view === "alerts" ? <div className="pscroll"><AlertsPage /></div> : <>
    <Stats />
    {!data.items.length && <div className="card empty">Open a job and choose a pipeline stage to start tracking.</div>}
    <div className="board">{stages.map((s) => { const items = data.items.filter((j) => j.stage === s); const isMin = !!mins[s]; return (
      <div key={s} className={`col kcol st-${s}${over === s ? " over" : ""}${isMin ? " min" : ""}`} onDragOver={(e) => { e.preventDefault(); setOver(s); }} onDragLeave={() => setOver((o) => (o === s ? null : o))} onDrop={(e) => drop(s, e)}>
        <button className="kcol-hd" onClick={() => setMins({ ...mins, [s]: !isMin })} aria-expanded={!isMin} aria-label={`${isMin ? "Expand" : "Minimise"} ${label(s)}`}><i className="dot" /><b>{label(s)}</b><span className="n">{items.length}</span><span className="chev" aria-hidden>{isMin ? "▸" : "▾"}</span></button>
        {!isMin && <div className="kcol-bd">{!items.length && <div className="small muted kcol-empty">Drop a job here</div>}
        {items.map((j) => { const due = !!j.follow_up_at && new Date(j.follow_up_at) <= new Date(); return (
          <div key={j.id} className="pcard" draggable onDragStart={(e) => e.dataTransfer.setData("text/plain", String(j.id))}>
            <div className="row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}><Logo c={j.company} />
              <div className="grow" style={{ minWidth: 0 }}><a href="#" className="pt" onClick={(e) => { e.preventDefault(); setOpen(j.id); }}>{j.title}</a><div className="small muted">{j.company.name} · {ago((j as { updated_at?: string }).updated_at)}</div></div>
              <Menu label={`Actions for ${j.title}`} trigger="⋯" items={[{ label: "Open details", onSelect: () => setOpen(j.id) }, ...data.stages.filter((x) => x !== j.stage).map((x) => ({ label: `Move to ${label(x)}`, onSelect: () => set.mutate({ id: j.id, stage: x }) }))]} /></div>
            <div className="pchips"><FitBadge ai={j.ai} />{j.follow_up_at && <span className={`chip ${due ? "bad" : "plain"}`} title={j.follow_up_note ?? ""}>⏰ {due ? "due " : ""}{day(j.follow_up_at)}</span>}</div></div>); })}</div>}</div>); })}</div>
    </>}
    {open != null && <JobDrawer id={open} onClose={() => setOpen(null)} />}
  </div>);
}
