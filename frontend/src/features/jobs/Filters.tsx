import type { Facet, SearchParams } from "@/shared/api/types";
import { useState } from "react";
import { label } from "@/shared/lib/format";
import { flag, modeLabel, WORK_MODES } from "@/shared/lib/geo";
import { useSectors } from "@/features/onboarding/SetupWizard";

function Group({ title, facets, selected, onToggle, fmt = (v: string) => v, max = 8 }: { title: string; facets?: Facet[]; selected: string[]; onToggle(v: string): void; fmt?: (v: string) => string; max?: number }) {
  if (!facets?.length) return null;
  return (<div className="facet" style={{ marginBottom: 12 }}><h3>{title}</h3>
    {facets.slice(0, max).map((f) => <label key={f.value}><input type="checkbox" checked={selected.includes(f.value)} onChange={() => onToggle(f.value)} />{fmt(f.value)}<span className="n">{f.count}</span></label>)}</div>);
}
const toggle = (arr: string[] | undefined, v: string) => { const a = arr ?? []; return a.includes(v) ? a.filter((x) => x !== v) : [...a, v]; };

export function Filters({ params, facets, onChange }: { params: SearchParams; facets?: Record<string, Facet[]>; onChange(p: Partial<SearchParams>): void }) {
  const sec = useSectors().data;
  const sectorFacets = sec?.sectors.map((s) => ({ value: s.key, count: s.jobs })) as Facet[] | undefined;
  const countryFacets = sec?.countries.filter((c) => c.jobs).sort((a, b) => b.jobs - a.jobs).map((c) => ({ value: c.code, count: c.jobs })) as Facet[] | undefined;
  const regionFacets = sec?.regions.filter((r) => r.jobs).map((r) => ({ value: r.key, count: r.jobs })) as Facet[] | undefined;
  const modeFacets = sec?.work_modes.map((m) => ({ value: m.key, count: m.jobs })) as Facet[] | undefined;
  const [showAll, setShowAll] = useState(false);
  const name = (k: string) => sec?.sectors.find((s) => s.key === k)?.label ?? sec?.countries.find((c) => c.code === k)?.name ?? label(k);
  return (<div className="card">
    <Group title="Field" facets={sectorFacets} selected={params.sector ?? []} onToggle={(v) => onChange({ sector: toggle(params.sector, v) })} fmt={name} max={20} />
    <Group title="Work mode" facets={modeFacets} selected={params.work_mode ?? []} onToggle={(v) => onChange({ work_mode: toggle(params.work_mode, v) })} fmt={(v) => WORK_MODES.find((m) => m[0] === v)?.slice(2, 3).concat(modeLabel(v)).join(" ") ?? v} />
    <Group title="Region" facets={regionFacets} selected={params.region ?? []} onToggle={(v) => onChange({ region: toggle(params.region, v) })} fmt={(v) => sec?.regions.find((r) => r.key === v)?.label ?? v} max={13} />
    <Group title="Country" facets={countryFacets} selected={params.country ?? []} onToggle={(v) => onChange({ country: toggle(params.country, v) })} fmt={(v) => `${flag(v)} ${name(v)}`} max={showAll ? 80 : 10} />
    {(countryFacets?.length ?? 0) > 10 && <button className="linkbtn small" style={{ marginTop: -8, marginBottom: 12 }} onClick={() => setShowAll(!showAll)}>{showAll ? "Fewer countries" : `All ${countryFacets!.length} countries`}</button>}
    {(params.country?.length || params.region?.length) ? <label className="small" style={{ display: "block", marginBottom: 12 }}><input type="checkbox" checked={params.remote_open !== false} onChange={(e) => onChange({ remote_open: e.target.checked ? undefined : false })} /> Include remote jobs open to these places</label> : null}
    <Group title="Type" facets={facets?.job_type} selected={params.job_type ?? []} onToggle={(v) => onChange({ job_type: toggle(params.job_type, v) })} fmt={label} />
    <Group title="Tech specialty" facets={facets?.domain} selected={params.domain ?? []} onToggle={(v) => onChange({ domain: toggle(params.domain, v) })} fmt={label} />
    <Group title="City" facets={facets?.city} selected={params.city ?? []} onToggle={(v) => onChange({ city: toggle(params.city, v) })} />
    <div className="facet" style={{ marginBottom: 12 }}><h3>Within distance</h3><div className="row">
      <input type="text" list="nlcities" placeholder="City, e.g. Utrecht" value={params.near ?? ""} onChange={(e) => onChange({ near: e.target.value || undefined })} style={{ flex: 1, minWidth: 0 }} aria-label="Near city" />
      <select value={params.radius_km ?? ""} onChange={(e) => onChange({ radius_km: e.target.value ? Number(e.target.value) : undefined })} aria-label="Radius"><option value="">any</option>{[10, 25, 50, 100].map((k) => <option key={k} value={k}>{k} km</option>)}</select>
      <datalist id="nlcities">{["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Groningen", "Delft", "Leiden", "Haarlem", "Breda", "Nijmegen", "Arnhem"].map((c) => <option key={c} value={c} />)}</datalist></div>
      {params.near && !params.radius_km && <div className="small muted">Pick a distance to apply it.</div>}</div>
    <Group title="Language" facets={facets?.language} selected={params.language ?? []} onToggle={(v) => onChange({ language: toggle(params.language, v) })} fmt={label} />
    <Group title="Skills" facets={facets?.skills} selected={params.skills ?? []} onToggle={(v) => onChange({ skills: toggle(params.skills, v) })} />
    <div className="facet">
      <label><input type="checkbox" checked={!!params.remote} onChange={(e) => onChange({ remote: e.target.checked || undefined })} />Remote friendly</label>
      <label><input type="checkbox" checked={!!params.sponsor} onChange={(e) => onChange({ sponsor: e.target.checked || undefined })} />Recognised sponsor only</label>
    </div>
    <div className="row" style={{ marginTop: 10 }}>
      <select value={params.days ?? ""} onChange={(e) => onChange({ days: e.target.value ? +e.target.value : undefined })}>
        <option value="">Any date</option><option value="1">Last 24h</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option></select>
      <select value={params.skills_mode ?? "any"} onChange={(e) => onChange({ skills_mode: e.target.value as "any" | "all" })}><option value="any">any skill</option><option value="all">all skills</option></select>
    </div>
    <div className="row" style={{ marginTop: 10 }}><input type="number" placeholder="Min € / month" style={{ width: 130 }} value={params.min_salary ?? ""} onChange={(e) => onChange({ min_salary: e.target.value ? +e.target.value : undefined })} /></div>
  </div>);
}
