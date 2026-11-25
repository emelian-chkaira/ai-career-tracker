import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { flag } from "@/shared/lib/geo";
import { useDemo } from "@/features/demo/useDemo";

type Country = { code: string; name: string; collected: boolean; jobs: number; employers: number; to_read: number; finding: string | null; phase: "off" | "finding_employers" | "reading" | "ready" };
export type Coverage = { countries: Country[]; worker: { state: string; next_start: string | null; why: string }; active: boolean };
export type CrawlResult = { added: string[]; discovering: string[]; requested: string[] };

const names = (cs: Country[]) => cs.map((c) => `${flag(c.code)} ${c.name}`).join(", ");
const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "");

/** After saving places: say what the crawler started doing, so an empty list is not a surprise. */
export function announceCrawl(r?: CrawlResult | null, nameOf: (c: string) => string = (c) => c) {
  if (!r) return;
  if (r.added.length || r.discovering.length) toast.success(`The crawler now collects ${[...new Set([...r.added, ...r.discovering])].map((c) => `${flag(c)} ${nameOf(c)}`).join(", ")}`, { description: r.discovering.length ? "It is finding employers there; their jobs appear in your feed as they are read (minutes to a few hours)." : "New postings from there are kept from now on." });
  else if (r.requested.length) toast(`${r.requested.map(nameOf).join(", ")} ${r.requested.length > 1 ? "are" : "is"} not collected yet`, { description: "An admin can turn it on in Crawler → Schedule & countries." });
}

/** Above the job list: which of the searched countries the crawler is still filling, and what it is doing right now. Refreshes itself. */
export function CrawlNotice({ country, region }: { country?: string[]; region?: string[] }) {
  const { user } = useAuth(); const qc = useQueryClient(); const { demo } = useDemo();
  const key = ["coverage", country ?? [], region ?? [], user?.id ?? "anon"];
  const q = useQuery({ queryKey: key, enabled: !!user || !!country?.length || !!region?.length, staleTime: 10_000,
    queryFn: () => api.get<Coverage>("/jobs/coverage", { country, region } as Record<string, unknown>), refetchInterval: (s) => (s.state.data?.active ? 20_000 : 120_000) });
  const cov = q.data; const active = !!cov?.active;
  useEffect(() => {                                                       // while the crawler is filling these countries, pull new jobs in by itself
    if (!active) return;
    const t = setInterval(() => qc.invalidateQueries({ queryKey: ["jobs"] }), 30_000); return () => clearInterval(t);
  }, [active, qc]);
  if (!cov || demo) return null;          // the demo has no crawler, and its banner already says so
  const finding = cov.countries.filter((c) => c.phase === "finding_employers"), reading = cov.countries.filter((c) => c.phase === "reading"), off = cov.countries.filter((c) => c.phase === "off");
  const w = cov.worker.state; const busy = finding.length + reading.length > 0;
  const collect = async () => { try { const r = await api.post<CrawlResult>("/jobs/coverage/collect", { country: off.map((c) => c.code) }); announceCrawl(r, (c) => cov.countries.find((x) => x.code === c)?.name ?? c); qc.invalidateQueries({ queryKey: ["coverage"] }); } catch (e) { toast.error((e as Error).message); } };
  if (!busy && !off.length) return null;
  return (<div className={`crawlnote ${busy && (w === "running" || w === "idle") ? "live" : busy ? "wait" : "off"}`} role="status">
    {busy && (w === "running" || w === "idle") && <><span className="cdot" aria-hidden /><div>
      <b>Collecting jobs in {names([...finding, ...reading])}</b>
      <div className="small">{[...finding.map((c) => `${c.name}: finding employers${c.employers ? ` (${c.employers.toLocaleString()} so far)` : ""}`), ...reading.map((c) => `${c.name}: reading ${c.to_read.toLocaleString()} career site${c.to_read === 1 ? "" : "s"} · ${c.jobs.toLocaleString()} jobs so far`)].join(" · ")}</div>
      <div className="small muted">New jobs appear here as they are read; this list refreshes by itself.</div></div></>}
    {busy && w === "paused" && <div><b>Jobs in {names([...finding, ...reading])} are waiting for the crawler</b><div className="small muted">It is paused ({cov.worker.why}){cov.worker.next_start ? ` and starts again ${when(cov.worker.next_start)}` : ""}.</div></div>}
    {busy && w === "stopped" && <div><b>Jobs in {names([...finding, ...reading])} are waiting for the crawler</b><div className="small muted">The crawler is not running right now, so nothing new arrives until it is started again.</div></div>}
    {off.length > 0 && <div className="row" style={{ gap: 8 }}><span className="small">{names(off)} {off.length > 1 ? "are" : "is"} not collected yet.</span>{user && <button className="btn small" onClick={collect}>Start collecting</button>}</div>}
  </div>);
}
