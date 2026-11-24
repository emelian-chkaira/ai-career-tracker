import { Link } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { label, ago, money } from "@/shared/lib/format";
import { useJob, useSetStage } from "./api";
import { Panel, Drawer, Dock, Tabs } from "@/shared/ui/kit";
import { CoachDock } from "@/features/cv/CoachDock";
import { useState } from "react";
import { FollowButton } from "@/features/companies/FollowButton";
import { Menu } from "./Menu";
import { Match, matchOf } from "./JobCard";
import { Logo, sponsorChip } from "./JobCard";
import { FitPanel } from "@/features/fit/FitPanel";
import { TrackPanel } from "@/features/track/TrackPanel";
import { AssistantPanel } from "@/features/assistant/AssistantPanel";
import { TailorPanel } from "@/features/cv/TailorPanel";
import { BoardIcon, boardName } from "@/shared/ui/BoardIcon";
import { flag, modeLabel } from "@/shared/lib/geo";
import type { Job } from "@/shared/api/types";

const STAGES = ["shortlisted", "applied", "screening", "assessment", "team_match", "interview", "final_round", "offer", "accepted", "rejected", "withdrawn", "skipped"];

/** Plain-text description -> paragraphs, bullet lists and sub-headings (no HTML injection: everything is rendered as React text). */
function Description({ text }: { text: string }) {
  const blocks: JSX.Element[] = []; let list: string[] = [];
  const flush = () => { if (list.length) { blocks.push(<ul key={"u" + blocks.length}>{list.map((x, i) => <li key={i}>{x}</li>)}</ul>); list = []; } };
  text.split(/\n+/).map((l) => l.trim()).filter(Boolean).forEach((l) => {
    if (/^[-*•·]\s+/.test(l)) list.push(l.replace(/^[-*•·]\s+/, ""));
    else { flush(); blocks.push(/^[^.!?]{3,60}:$/.test(l) && l.split(" ").length <= 7 ? <h4 key={blocks.length}>{l.replace(/:$/, "")}</h4> : <p key={blocks.length}>{l}</p>); }
  });
  flush();
  return <div className="desc">{blocks}</div>;
}

export { Description };
export function JobDetail({ id, onClose }: { id: number; onClose?: () => void }) {
  const { data: j, isLoading, error } = useJob(id);
  const { user } = useAuth(); const setStage = useSetStage(); const [chat, setChat] = useState(false); const [coach, setCoach] = useState(false);
  if (isLoading) return <div className="bd stack"><div className="skel" style={{ height: 64 }} /><div className="skel" style={{ height: 14 }} /><div className="skel" style={{ height: 240 }} /></div>;
  if (error || !j) return <div className="bd err">{(error as Error)?.message ?? "Not found"}</div>;
  const sal = j.salary?.min != null ? `${money(j.salary.min)}${j.salary.max ? `–${money(j.salary.max)}` : ""} / ${j.salary.period ?? "month"}` : "";
  const facts: [string, string][] = ([["Salary", sal], ["Work mode", j.work_mode ? modeLabel(j.work_mode) : ""], ["Level", label(j.job_type)], ["Language", j.language !== "unknown" ? label(j.language) : ""], ["Location", j.city || j.location || ""], ["Posted", ago(j.posted_at ?? j.first_seen)]] as [string, string][]).filter((x) => x[1]);
  const overview = (<div className="stack">
          {facts.length > 0 && <div className="facts" aria-label="Job highlights">{facts.map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}</div>}
          <Panel id="job-fit" title="How well you match"><FitPanel jobId={j.id} ai={j.ai} /></Panel>
          <div><h3>About the role</h3>{j.description ? <Description text={j.description} /> : <p className="muted">No description captured — open the posting on the company site.</p>}</div>
          {j.skills.length > 0 && <div><h3>Skills mentioned</h3>{j.skills.map((s) => <span className="chip" key={s}>{s}</span>)}</div>}
          {!!j.alternates?.length && <AlsoListed job={j} />}
          {j.company.sponsor_match && <div className="small muted">NL IND register match: {j.company.sponsor_match}. A flag only; confirm with the employer.</div>}
        </div>);
  return (<>
    <div className="hd jdhead">
      <div className="jdtop">
        <Logo c={j.company} big />
        <div className="jdtitle">
          <h1>{j.title}</h1>
          <div className="jdsub"><b>{j.company.name}</b>{(j.location || j.work_mode === "remote") && <span>{flag(j.country)} {j.location || "Remote"}</span>}<span>{ago(j.posted_at ?? j.first_seen)}</span></div>
        </div>
        {matchOf(j) != null && <Match job={j} />}
        {onClose && <button className="btn ghost small jdclose" onClick={onClose} aria-label="Close">✕</button>}
      </div>
      {j.status === "expired" && <div className="notice warn" role="status">This posting is no longer online: the employer removed it. It stays here only for your history.</div>}
      <div className="jchips">{sponsorChip(j.company.sponsor_status)}</div>
      <div className="jdact">
        <a className="btn" href={j.url} target="_blank" rel="noreferrer noopener">Apply ↗</a>
        {user && <button className="btn ghost" disabled={!!j.stage} onClick={() => setStage.mutate({ id: j.id, stage: "shortlisted" })}>{j.stage ? "★ Saved" : "☆ Save"}</button>}
        {user && <select value={j.stage ?? ""} onChange={(e) => setStage.mutate({ id: j.id, stage: e.target.value })} title="Pipeline stage">
          <option value="" disabled>Track…</option>{STAGES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>}
        {!user && <span className="small muted"><Link to="/login">Sign in</Link> to track</span>}
        <span className="grow" />
        <Menu label="More ▾" className="right">
          <Link className="menu-item" to={`/jobs/${j.id}`}>Open full page ↗</Link>
          {user && <FollowButton companyId={j.company.id} name={j.company.name} />}
          {user && <button className="menu-item" onClick={() => setChat(true)}>💬 Ask the assistant</button>}
        </Menu>
      </div>
    </div>
    <div className="bd stack">
      {!user ? overview : <Tabs tabs={[
        { value: "overview", label: "Overview", content: overview },
        ...(user ? [{ value: "cv", label: "My CV", content: (<div className="stack">
          <div className="coach-cta"><div><b>Missing something you have done?</b><div className="small muted">Tell the CV coach in a chat and it adds skills, bullets or projects to your CV.</div></div><button className="btn" onClick={() => setCoach(true)}>✦ Open CV coach</button></div>
          <Panel id="job-tailor" title="Tune my CV for this job"><TailorPanel jobId={j.id} title={j.title} /></Panel>
        </div>) }] : []),
        ...(user && j.stage ? [{ value: "track", label: "Tracking", content: <TrackPanel jobId={j.id} /> }] : []),
      ]} />}
      {user && !coach && <button className="coachfab" onClick={() => setCoach(true)} aria-label="Open the CV coach"><span>✦</span> CV coach</button>}
      {coach && <CoachDock jobId={j.id} title={j.title} onClose={() => setCoach(false)} />}
      {chat && <Dock id="assistant" title={`Assistant · ${j.title}`} onClose={() => setChat(false)} width={400} offset={coach ? 416 : 0}><AssistantPanel jobId={j.id} embedded /></Dock>}
    </div>
  </>);
}

export function JobDrawer({ id, onClose }: { id: number; onClose(): void }) {
  return (<Drawer open onOpenChange={(o) => !o && onClose()} title="Job details" size={680}><div className="jd"><JobDetail id={id} /></div></Drawer>);
}


/** Every other place and site this role is listed on: one role, one job, all its links. */
function AlsoListed({ job }: { job: Job }) {
  const [open, setOpen] = useState(false);
  const alts = job.alternates ?? []; const shown = open ? alts : alts.slice(0, 6);
  return (<div className="alsolisted"><h3>Also listed <span className="muted small">· the same role in {alts.length} more {alts.length === 1 ? "place" : "places"}, shown once</span></h3>
    <ul>{shown.map((a) => <li key={a.url}><BoardIcon board={a.source?.startsWith("board:") ? a.source : "site"} size={15} />
      <a href={a.url} target="_blank" rel="noreferrer">{a.city || a.location || (a.source?.startsWith("board:") ? boardName(a.source) : "Employer site")}</a>
      {a.countries?.[0] && <span className="muted small">{flag(a.countries[0])}</span>}{a.source?.startsWith("board:") && <span className="muted small">on {boardName(a.source)}</span>}</li>)}</ul>
    {alts.length > 6 && <button className="linkbtn small" onClick={() => setOpen(!open)}>{open ? "Show fewer" : `Show all ${alts.length}`}</button>}</div>);
}
