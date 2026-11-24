import { flag, SCOPE } from "@/shared/lib/geo";
import { BoardIcon, boardName } from "@/shared/ui/BoardIcon";
import type { Job } from "@/shared/api/types";
import { ago, label, money } from "@/shared/lib/format";

export function Logo({ c, big = false }: { c: Job["company"]; big?: boolean }) {
  const cls = "logo" + (big ? " lg" : "");
  return c.logo ? <img className={cls} src={c.logo.startsWith("http") || c.logo.startsWith("/") ? c.logo : `/logos/${c.logo}`} alt="" loading="lazy" /> : <div className={cls}>{c.name[0]}</div>;
}
export const sponsorChip = (s: string) => (s === "recognised" ? <span className="chip ok">NL IND sponsor</span> : s === "possible" ? <span className="chip warn">Possible sponsor</span> : null);
const isNew = (d?: string | null) => !!d && Date.now() - new Date(d).getTime() < 3 * 86400000;

/** Only the AI score is shown. No profile estimate: scores appear when you press "AI score" (or score a job in the detail panel). */
export const matchOf = (j: Job): { pct: number; why: string; ai: boolean } | null =>
  j.ai ? { pct: j.ai.score, why: j.ai.reason || "AI fit score", ai: true } : null;

export function Match({ job, pending = false }: { job: Job; pending?: boolean }) {
  if (pending && !job.ai) return <div className="match pend" title="The AI is reading your CV against this posting"><b>…</b><em>AI scoring</em></div>;
  const m = matchOf(job); if (!m) return null;
  return <div className={"match " + (m.pct >= 75 ? "hi" : m.pct >= 50 ? "mid" : "lo") + (m.ai ? "" : " est")} title={`${m.ai ? "AI" : "Profile"} match: ${m.why}`}><i className="mv"><b>{m.ai ? "" : "~"}{Math.round(m.pct)}</b><span>%</span></i><em>{m.ai ? "AI match" : "estimate"}</em>{m.ai && job.fit != null && Math.abs(job.fit - m.pct) >= 10 && <small title="Instant estimate from your CV. The AI score is more thorough and replaces it.">CV {Math.round(job.fit)}%</small>}</div>;
}

export function JobCard({ job, selected, onOpen, picked, onPick, pending }: { job: Job; selected?: boolean; onOpen(id: number): void; picked?: boolean; onPick?(id: number, on: boolean): void; pending?: boolean }) {
  const when = job.posted_at ?? job.first_seen; const place = job.city ?? (job.work_mode === "remote" && !job.city ? "Remote" : job.location) ?? "";
  const extra = (job.countries?.length ?? 0) > 1 ? ` +${job.countries!.length - 1}` : "";
  const alts = job.alternates?.length ? `${new Set([job.city, ...job.alternates.map((a) => a.city)].filter(Boolean)).size > 1 ? "several locations" : `${job.alternates.length + 1} listings`}` : "";
  // at most three chips: what the person needs to decide quickly
  const chips: React.ReactNode[] = [];
  if (job.stage) chips.push(<span key="st" className="chip warn">{label(job.stage)}</span>);
  const sp = sponsorChip(job.company.sponsor_status); if (sp) chips.push(<span key="sp">{sp}</span>);
  if (job.work_mode && job.work_mode !== "onsite") chips.push(<span key="wm" className="chip plain" title={job.remote_scope ? `Remote, open to ${SCOPE[job.remote_scope] ?? job.remote_scope}` : undefined}>{job.work_mode === "remote" ? "Remote" : "Hybrid"}</span>);
  if (job.job_type && job.job_type !== "job") chips.push(<span key="ty" className="chip plain">{label(job.job_type)}</span>);
  return (
    <div className={"job" + (selected ? " sel" : "")} onClick={() => onOpen(job.id)} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(job.id)}>
      <div className="jlogo">{onPick && <input className="pick" type="checkbox" checked={!!picked} aria-label={`Select ${job.title}`} onClick={(e) => e.stopPropagation()} onChange={(e) => onPick(job.id, e.target.checked)} />}<Logo c={job.company} /></div>
      <div className="jmain">
        <div className="t"><span className="tt">{job.title}</span>{isNew(when) && <span className="newdot" title="New in the last 3 days" />}</div>
        <div className="meta"><span className="co">{job.company.name}</span>{place && <span>{flag(job.country)} {place}{extra}</span>}
          {job.salary?.min != null && <span>{money(job.salary.min)}{job.salary.max ? `–${money(job.salary.max)}` : ""}/{job.salary.period ?? "mo"}</span>}
          {job.source?.startsWith("board:") && <span title="Found on a job board, not on the employer's own careers page"><BoardIcon board={job.source} size={12} /> {boardName(job.source)}</span>}
          {alts && <span title={`The same role is listed in ${alts}`}>{alts}</span>}
          <span className="when">{ago(when)}</span></div>
        {job.snippet && <div className="snip" dangerouslySetInnerHTML={{ __html: sanitize(job.snippet) }} />}
        {(chips.length > 0 || !!job.skills?.length) && <div className="jchips">{chips.slice(0, 3)}{job.skills?.slice(0, 4).map((k) => <span key={k} className="skill">{k}</span>)}</div>}
      </div>
      <Match job={job} pending={pending} />
    </div>
  );
}
/** Snippets come from ts_headline and may only contain <mark>; strip everything else. */
function sanitize(html: string) { return html.replace(/<(?!\/?mark>)[^>]*>/gi, ""); }


/** "4 locations" / "also on Indeed": the same role folded from several cities, links or sites (one role, one card). */
export function AltChip({ job }: { job: Job }) {
  const alts = job.alternates ?? [];
  const cities = [...new Set([job.city, ...alts.map((a) => a.city)].filter(Boolean))] as string[];
  const boards = [...new Set(alts.map((a) => a.source).filter((s) => s?.startsWith("board:")))] as string[];
  const tip = [cities.length > 1 ? `In ${cities.join(", ")}` : "", boards.length ? `Also on ${boards.map(boardName).join(", ")}` : "", `${alts.length + 1} links to this role`].filter(Boolean).join(" · ");
  return (<span className="chip plain altchip" title={tip}>{cities.length > 1 ? <>📍 {cities.length} locations</> : <>🔗 {alts.length + 1} listings</>}{boards.map((b) => <BoardIcon key={b} board={b} size={12} />)}</span>);
}
