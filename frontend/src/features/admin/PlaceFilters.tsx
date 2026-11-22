import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { flag, modeLabel } from "@/shared/lib/geo";
import { useSectors } from "@/shared/api/meta";
import { BoardIcon, boardName } from "@/shared/ui/BoardIcon";

type Opt = { value: string; n: number };
type Filters = { companies: Record<string, Opt[]>; jobs: Record<string, Opt[]> };
export type PlaceF = { country?: string; city?: string; source?: string; sector?: string; work_mode?: string };

/** Country, city and source (employer site or a job board) filters for the Companies and Jobs lists; Jobs also by field and work mode. */
export function PlaceFilters({ kind, value, onChange }: { kind: "companies" | "jobs"; value: PlaceF; onChange(v: PlaceF): void }) {
  const f = useQuery({ queryKey: ["admin-filters"], staleTime: 60_000, queryFn: () => api.get<Filters>("/admin/filters") }).data?.[kind];
  const sec = useSectors().data; const cname = (c: string) => sec?.countries.find((x) => x.code === c)?.name ?? c;
  const set = (k: keyof PlaceF, v: string) => onChange({ ...value, [k]: v || undefined });
  const boards = (f?.source ?? []).filter((s) => s.value.startsWith("board:"));
  const active = Object.values(value).filter(Boolean).length;
  return (<div className="pfilters">
    <select value={value.country ?? ""} onChange={(e) => set("country", e.target.value)} aria-label="Country"><option value="">🌍 All countries</option>
      {(f?.country ?? []).map((o) => <option key={o.value} value={o.value}>{flag(o.value)} {cname(o.value)} ({o.n.toLocaleString()})</option>)}</select>
    <input type="search" list={`cities-${kind}`} placeholder="City" value={value.city ?? ""} onChange={(e) => set("city", e.target.value)} aria-label="City" style={{ width: 130 }} />
    <datalist id={`cities-${kind}`}>{(f?.city ?? []).map((o) => <option key={o.value} value={o.value}>{o.n} {kind}</option>)}</datalist>
    {kind === "jobs" && <select value={value.sector ?? ""} onChange={(e) => set("sector", e.target.value)} aria-label="Field"><option value="">Any field</option>
      {(f?.sector ?? []).map((o) => <option key={o.value} value={o.value}>{sec?.sectors.find((s) => s.key === o.value)?.label ?? o.value} ({o.n.toLocaleString()})</option>)}</select>}
    {kind === "jobs" && <select value={value.work_mode ?? ""} onChange={(e) => set("work_mode", e.target.value)} aria-label="Work mode"><option value="">Any work mode</option>
      {(f?.work_mode ?? []).map((o) => <option key={o.value} value={o.value}>{modeLabel(o.value)} ({o.n.toLocaleString()})</option>)}</select>}
    <div className="srcseg" role="group" aria-label="Found on">
      <button className={!value.source ? "on" : ""} onClick={() => set("source", "")}>All sources</button>
      <button className={value.source === "site" ? "on" : ""} onClick={() => set("source", "site")} title="Read from the employer's own careers page"><BoardIcon board="site" size={16} /> Employer sites</button>
      {boards.map((b) => <button key={b.value} className={value.source === b.value ? "on" : ""} onClick={() => set("source", b.value)} title={`Found on ${boardName(b.value)}`}><BoardIcon board={b.value} size={16} /> {boardName(b.value)} <span className="muted">{b.n}</span></button>)}
    </div>
    {active > 0 && <button className="linkbtn small" onClick={() => onChange({})}>Clear {active} filter{active > 1 ? "s" : ""}</button>}
  </div>);
}
