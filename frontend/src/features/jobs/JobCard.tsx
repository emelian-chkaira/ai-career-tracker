import { flag, SCOPE } from "@/shared/lib/geo";
import { BoardIcon, boardName } from "@/shared/ui/BoardIcon";
import type { Job } from "@/shared/api/types";
import { ago, label, money } from "@/shared/lib/format";
import { FitBadge } from "@/features/fit/FitPanel";

export function Logo({ c, big = false }: { c: Job["company"]; big?: boolean }) {
  const cls = "logo" + (big ? " lg" : "");
  return c.logo ? <img className={cls} src={c.logo.startsWith("http") || c.logo.startsWith("/") ? c.logo : `/logos/${c.logo}`} alt="" loading="lazy" /> : <div className={cls}>{c.name[0]}</div>;
}
export const sponsorChip = (s: string) => (s === "recognised" ? <span className="chip ok">IND sponsor</span> : s === "possible" ? <span className="chip warn">Possible sponsor</span> : null);
const isNew = (d?: string | null) => !!d && Date.now() - new Date(d).getTime() < 3 * 86400000;

export function JobCard({ job, selected, onOpen, picked, onPick }: { job: Job; selected?: boolean; onOpen(id: number): void; picked?: boolean; onPick?(id: number, on: boolean): void }) {
  const when = job.posted_at ?? job.first_seen;
  return (
    <div className={"job" + (selected ? " sel" : "")} onClick={() => onOpen(job.id)} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(job.id)}>
      {onPick && <input className="pick" type="checkbox" checked={!!picked} aria-label={`Select ${job.title}`} onClick={(e) => e.stopPropagation()} onChange={(e) => onPick(job.id, e.target.checked)} />}
      <Logo c={job.company} />
      <div className="grow" style={{ minWidth: 0 }}>
        <div className="t">{job.title}</div>
        <div className="meta">{job.company.name} · <span title={(job.countries ?? []).join(", ")}>{flag(job.country)} {job.city ?? (job.work_mode === "remote" && !job.city ? "Remote" : job.location) ?? ""}{(job.countries?.length ?? 0) > 1 ? ` +${job.countries!.length - 1}` : ""}</span></div>
        {job.snippet && <div className="small muted" style={{ margin: "4px 0", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }} dangerouslySetInnerHTML={{ __html: sanitize(job.snippet) }} />}
        <div className="jchips">
          {isNew(when) && <span className="chip ok">New</span>}
          <span className="chip">{label(job.job_type)}</span>
          {job.source?.startsWith("board:") && <span className="chip plain" title="Found on a job board, not on the employer's own careers page"><BoardIcon board={job.source} size={13} /> via {boardName(job.source)}</span>}
          {!!job.alternates?.length && <AltChip job={job} />}
          {job.work_mode && job.work_mode !== "onsite" && <span className="chip plain" title={job.remote_scope ? `Remote, open to ${SCOPE[job.remote_scope] ?? job.remote_scope}` : undefined}>{job.work_mode === "remote" ? "🏠 Remote" : "🔀 Hybrid"}{job.remote_scope && job.remote_scope !== "world" ? ` · ${SCOPE[job.remote_scope] ?? job.remote_scope}` : job.remote_scope === "world" ? " · anywhere" : ""}</span>}
          {sponsorChip(job.company.sponsor_status)}
          <FitBadge ai={job.ai} />
          {!job.ai && job.fit != null && <span className="chip plain" title={job.fit_reason ?? "Matches your profile preferences"}>{job.fit}% profile match</span>}
          {job.stage && <span className="chip warn">{label(job.stage)}</span>}
          {job.salary?.min != null && <span className="chip plain">{money(job.salary.min)}{job.salary.max ? `–${money(job.salary.max)}` : ""}/{job.salary.period ?? "mo"}</span>}
          
        </div>
      </div>
      <div className="small muted" style={{ whiteSpace: "nowrap" }}>{ago(when)}</div>
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
