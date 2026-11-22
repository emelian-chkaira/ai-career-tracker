import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";

type H = { totals: { companies: number; never_scanned: number; failing: number; stale: number }; by_ats: { ats: string; companies: number; failing: number; open_jobs: number }[];
  failing: { id: number; name: string; ats: string | null; fail_count: number; last_scan: string | null; scan_note: string | null }[] };

/** Which sources are healthy: coverage per ATS, companies that keep failing, and ones nobody has scanned for two weeks. */
export function SourceHealth({ bare = false }: { bare?: boolean }) {
  const q = useQuery({ queryKey: ["source-health"], queryFn: () => api.get<H>("/admin/source-health"), staleTime: 60_000 }); const h = q.data;
  if (!h) return null;
  return (<div className={bare ? "stack" : "card stack"}>{!bare && <h2 style={{ margin: 0 }}>Source health</h2>}
    <div className="row small" style={{ gap: 18 }}><span><b>{h.totals.companies}</b> companies</span><span className={h.totals.failing ? "err" : ""}><b>{h.totals.failing}</b> failing (3+ misses)</span><span><b>{h.totals.stale}</b> not scanned for 14 days</span><span><b>{h.totals.never_scanned}</b> never scanned</span></div>
    <table className="table"><thead><tr><th>ATS</th><th>Companies</th><th>Failing</th><th>Open jobs</th></tr></thead><tbody>{h.by_ats.map((r) => <tr key={r.ats}><td>{r.ats}</td><td>{r.companies}</td><td className={r.failing ? "err" : ""}>{r.failing}</td><td>{r.open_jobs}</td></tr>)}</tbody></table>
    {!!h.failing.length && <><h3>Failing companies</h3>{h.failing.slice(0, 10).map((c) => <div key={c.id} className="small row"><b>{c.name}</b><span className="muted">{c.ats ?? "no ATS"} · {c.fail_count} misses · {c.scan_note ?? ""}</span></div>)}</>}</div>);
}
