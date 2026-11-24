import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";

export interface Release { version: string; date: string; sections: Record<string, string[]> }
export const useVersion = () => useQuery({ queryKey: ["version"], staleTime: 600_000, queryFn: () => api.get<{ version: string; released: string; changelog: Release[] }>("/version") });

/** What changed in each version. The running version is marked "current". */
export function ChangelogPage() {
  const v = useVersion();
  if (v.isLoading) return <p className="muted">Loading…</p>;
  if (!v.data) return <div className="notice err">Could not load the changelog.</div>;
  return (<div className="stack" style={{ maxWidth: 780 }}>
    <div><h1>What's new</h1><div className="muted">You are on version <b>{v.data.version}</b>{v.data.released ? `, released ${v.data.released}` : ""}.</div></div>
    {v.data.changelog.map((r) => (<section key={r.version} className="card stack" style={{ gap: 10 }}>
      <div className="row"><h2 style={{ margin: 0 }}>{r.version}</h2>{r.version === v.data.version && <span className="chip ok" style={{ margin: 0 }}>Current</span>}<span className="small muted right">{r.date}</span></div>
      {Object.entries(r.sections).map(([name, items]) => (<div key={name}><h3>{name}</h3><ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>{items.map((x) => <li key={x} className="small" style={{ margin: "3px 0" }}>{x}</li>)}</ul></div>))}
    </section>))}
  </div>);
}
