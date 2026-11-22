import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { label, ago } from "@/shared/lib/format";
import { useJob, useSetStage } from "./api";
import { Tabs } from "@/shared/ui/kit";
import { Logo, sponsorChip } from "./JobCard";
import { Description } from "./JobDrawer";
import { FitPanel } from "@/features/fit/FitPanel";
import { TrackPanel } from "@/features/track/TrackPanel";
import { AssistantPanel } from "@/features/assistant/AssistantPanel";
import { TailorPanel } from "@/features/cv/TailorPanel";
import { FollowButton } from "@/features/companies/FollowButton";

const STAGES = ["shortlisted", "applied", "screening", "assessment", "team_match", "interview", "final_round", "offer", "accepted", "rejected", "withdrawn", "skipped"];
interface MailEv { id: number; subject: string | null; sender: string | null; category: string; summary: string | null; received_at: string | null; status: string }

function Emails({ jobId }: { jobId: number }) {
  const q = useQuery({ queryKey: ["job-mail", jobId], queryFn: () => api.get<{ items: MailEv[] }>(`/mail/events?job_id=${jobId}`) });
  if (q.isLoading) return <div className="skel" style={{ height: 80 }} />;
  const items = q.data?.items ?? [];
  if (!items.length) return <div className="card empty small">No e-mails linked to this job yet. Connect Gmail in <Link to="/inbox">Inbox</Link> and sync; replies from this company show up here.</div>;
  return (<ul className="plain stack" style={{ gap: 8 }}>{items.map((e) => <li key={e.id} className="irow"><div className="irow-main"><b>{e.subject ?? "(no subject)"}</b><div className="small muted">{e.sender} · {ago(e.received_at)}</div>{e.summary && <div className="small">{e.summary}</div>}</div><span className="chip plain" style={{ margin: 0 }}>{label(e.category)}</span></li>)}</ul>);
}

/** The full-page "dossier" for one job: everything you need while applying, split into tabs. */
export function JobPage() {
  const { id } = useParams(); const jid = Number(id); const go = useNavigate(); const { user } = useAuth(); const { data: j, isLoading, error } = useJob(jid); const setStage = useSetStage();
  if (isLoading) return <div className="stack"><div className="skel" style={{ height: 90 }} /><div className="skel" style={{ height: 300 }} /></div>;
  if (error || !j) return <div className="notice err">{(error as Error)?.message ?? "Job not found"} <button className="btn ghost small" onClick={() => go("/")}>Back to jobs</button></div>;
  const tracked = !!j.stage;
  return (<div className="stack">
    <div className="small"><Link to="/">← Jobs</Link></div>
    <div className="card stack"><div className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><Logo c={j.company} big />
      <div className="grow" style={{ minWidth: 0 }}><h1 style={{ fontSize: 24 }}>{j.title}</h1><div className="muted">{[j.company.name, j.location || (j.work_mode === "remote" ? "Remote" : ""), ago(j.posted_at ?? j.first_seen)].filter(Boolean).join(" · ")}</div></div>
      {j.ai && <span className="chip plain" title="AI fit score">Fit {j.ai.score}</span>}</div>
      {j.status === "expired" && <div className="notice warn" role="status">This posting is no longer online: the employer removed it. It stays here only for your history.</div>}
      <div>{sponsorChip(j.company.sponsor_status)}<span className="chip">{label(j.job_type)}</span>{j.language !== "unknown" && <span className="chip">{label(j.language)}</span>}{j.remote && <span className="chip">Remote friendly</span>}</div>
      <div className="row"><a className="btn" href={j.url} target="_blank" rel="noreferrer noopener">Apply on company site ↗</a>
        {user && <select value={j.stage ?? ""} onChange={(e) => setStage.mutate({ id: j.id, stage: e.target.value })} aria-label="Pipeline stage"><option value="" disabled>Track…</option>{STAGES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>}
        {user && <FollowButton companyId={j.company.id} name={j.company.name} />}{!user && <span className="small muted"><Link to="/login">Sign in</Link> to track this job</span>}</div></div>
    <Tabs tabs={[
      { value: "overview", label: "Overview", content: <div className="stack">{user && <FitPanel jobId={j.id} ai={j.ai} />}
        {j.skills.length > 0 && <div><h3>Skills mentioned</h3>{j.skills.map((s) => <span className="chip" key={s}>{s}</span>)}</div>}
        <div><h3>About the role</h3>{j.description ? <Description text={j.description} /> : <p className="muted">No description captured. Open the posting on the company site.</p>}</div></div> },
      ...(user ? [
        { value: "notes", label: "Notes & to-dos", content: tracked ? <TrackPanel jobId={j.id} part="notes" /> : <div className="card empty small">Choose a stage above to start tracking this job; notes, dates and to-dos appear here.</div> },
        { value: "docs", label: "Documents", content: <TailorPanel jobId={j.id} title={j.title} /> },
        { value: "timeline", label: "Timeline", content: tracked ? <TrackPanel jobId={j.id} part="timeline" /> : <div className="card empty small">The timeline starts when you change the stage.</div> },
        { value: "emails", label: "Emails", content: <Emails jobId={j.id} /> },
        { value: "assistant", label: "Assistant", content: <AssistantPanel jobId={j.id} embedded /> }] : [])]} />
  </div>);
}
