import type { Facet, SearchParams } from "@/shared/api/types";
import { useState } from "react";
import { label } from "@/shared/lib/format";
import { flag, modeLabel, WORK_MODES } from "@/shared/lib/geo";
import { useSectors } from "@/shared/api/meta";

function Group({ title, facets, selected, onToggle, fmt = (v: string) => v, max = 8, open = false }: { title: string; facets?: Facet[]; selected: string[]; onToggle(v: string): void; fmt?: (v: string) => string; max?: number; open?: boolean }) {
  if (!facets?.length) return null;
  return (<details className="fgroup" open={open || selected.length > 0}><summary><span>{title}</span>{selected.length > 0 && <b className="fcount">{selected.length}</b>}</summary>
    <div className="fbody">{facets.slice(0, max).map((f) => <label key={f.value}><input type="checkbox" checked={selected.includes(f.value)} onChange={() => onToggle(f.value)} />{fmt(f.value)}<span className="n">{f.count}</span></label>)}</div></details>);
}
function Section({ title, children, open = false }: { title: string; children: React.ReactNode; open?: boolean }) {
  return (<details className="fgroup" open={open}><summary><span>{title}</span></summary><div className="fbody">{children}</div></details>);
}
const toggle = (arr: string[] | undefined, v: string) => { const a = arr ?? []; return a.includes(v) ? a.filter((x) => x !== v) : [...a, v]; };

export const SEARCH_MODES: { key: NonNullable<SearchParams["mode"]>; label: string; hint: string; eg: string }[] = [
  { key: "hybrid", label: "Smart", hint: "Words, related roles and meaning together. Best for exploring.", eg: "“flutter” also finds iOS, Android and mobile roles." },
  { key: "exact", label: "Exact", hint: "Only jobs whose title or text contains your words. Like LinkedIn.", eg: "“flutter” finds only jobs that say Flutter." },
  { key: "keyword", label: "Related words", hint: "Your words plus close terms (Dart, mobile, Swift…), no AI.", eg: "Wider than Exact, more predictable than Smart." },
  { key: "semantic", label: "By meaning", hint: "Finds jobs that describe the same work in other words.", eg: "“smartphone app programmer” finds Flutter jobs." },
];

export function Filters({ params, facets, onChange }: { params: SearchParams; facets?: Record<string, Facet[]>; onChange(p: Partial<SearchParams>): void }) {
  const sec = useSectors().data;
  const sectorFacets = sec?.sectors.map((s) => ({ value: s.key, count: s.jobs })) as Facet[] | undefined;
  const countryFacets = sec?.countries.filter((c) => c.jobs).sort((a, b) => b.jobs - a.jobs).map((c) => ({ value: c.code, count: c.jobs })) as Facet[] | undefined;
  const regionFacets = sec?.regions.filter((r) => r.jobs).map((r) => ({ value: r.key, count: r.jobs })) as Facet[] | undefined;
  const modeFacets = sec?.work_modes.map((m) => ({ value: m.key, count: m.jobs })) as Facet[] | undefined;
  const [showAll, setShowAll] = useState(false);
  const name = (k: string) => sec?.sectors.find((s) => s.key === k)?.label ?? sec?.countries.find((c) => c.code === k)?.name ?? label(k);
  return (<div className="filters">
    <Section title="Search & order" open>
      <div className="frow">How to search
        <div className="modes" role="radiogroup" aria-label="How to search">{SEARCH_MODES.map((m) => <label key={m.key} className={`mode ${(params.mode ?? "hybrid") === m.key ? "on" : ""}`}>
          <input type="radio" name="search-mode" checked={(params.mode ?? "hybrid") === m.key} onChange={() => onChange({ mode: m.key })} />
          <span><b>{m.label}</b><small>{m.hint}</small><small className="eg">{m.eg}</small></span></label>)}</div></div>
      <label className="frow">Order<select value={params.sort ?? ""} onChange={(e) => onChange({ sort: e.target.value || undefined })}><option value="">{params.q ? "Relevance" : "Newest first"}</option>{params.q && <option value="newest">Newest first</option>}<option value="ai_fit">AI score (highest first)</option><option value="oldest">Oldest first</option><option value="salary">Highest salary</option></select></label>
      <label className="frow">Posted<select value={params.days ?? ""} onChange={(e) => onChange({ days: e.target.value ? +e.target.value : undefined })}><option value="">Any time</option><option value="1">Last 24 hours</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option></select></label>
    </Section>
    <Group title="Field" facets={sectorFacets} selected={params.sector ?? []} onToggle={(v) => onChange({ sector: toggle(params.sector, v) })} fmt={name} max={20} open />
    <Group title="Work mode" facets={modeFacets} selected={params.work_mode ?? []} onToggle={(v) => onChange({ work_mode: toggle(params.work_mode, v) })} fmt={(v) => WORK_MODES.find((m) => m[0] === v)?.slice(2, 3).concat(modeLabel(v)).join(" ") ?? v} />
    <Group title="Region" facets={regionFacets} selected={params.region ?? []} onToggle={(v) => onChange({ region: toggle(params.region, v) })} fmt={(v) => sec?.regions.find((r) => r.key === v)?.label ?? v} max={13} />
    <Group title="Country" facets={countryFacets} selected={params.country ?? []} onToggle={(v) => onChange({ country: toggle(params.country, v) })} fmt={(v) => `${flag(v)} ${name(v)}`} max={showAll ? 80 : 10} />
    {(countryFacets?.length ?? 0) > 10 && <button className="linkbtn small" style={{ margin: "-4px 0 10px 4px" }} onClick={() => setShowAll(!showAll)}>{showAll ? "Fewer countries" : `All ${countryFacets!.length} countries`}</button>}
    {(params.country?.length || params.region?.length) ? <label className="small fnote"><input type="checkbox" checked={params.remote_open !== false} onChange={(e) => onChange({ remote_open: e.target.checked ? undefined : false })} /> Include remote jobs open to these places</label> : null}
    <Group title="Level" facets={facets?.job_type} selected={params.job_type ?? []} onToggle={(v) => onChange({ job_type: toggle(params.job_type, v) })} fmt={label} />
    <Group title="Tech specialty" facets={facets?.domain} selected={params.domain ?? []} onToggle={(v) => onChange({ domain: toggle(params.domain, v) })} fmt={label} />
    <Group title="City" facets={facets?.city} selected={params.city ?? []} onToggle={(v) => onChange({ city: toggle(params.city, v) })} />
    <Section title="Distance from a city"><div className="row">
      <input type="text" list="nlcities" placeholder="City, e.g. Utrecht" value={params.near ?? ""} onChange={(e) => onChange({ near: e.target.value || undefined })} style={{ flex: 1, minWidth: 0 }} aria-label="Near city" />
      <select value={params.radius_km ?? ""} onChange={(e) => onChange({ radius_km: e.target.value ? Number(e.target.value) : undefined })} aria-label="Radius"><option value="">any</option>{[10, 25, 50, 100].map((k) => <option key={k} value={k}>{k} km</option>)}</select>
      <datalist id="nlcities">{["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Groningen", "Delft", "Leiden", "Haarlem", "Breda", "Nijmegen", "Arnhem"].map((c) => <option key={c} value={c} />)}</datalist></div>
      {params.near && !params.radius_km && <div className="small muted">Pick a distance to apply it.</div>}</Section>
    <Group title="Language" facets={facets?.language} selected={params.language ?? []} onToggle={(v) => onChange({ language: toggle(params.language, v) })} fmt={label} />
    <Group title="Skills" facets={facets?.skills} selected={params.skills ?? []} onToggle={(v) => onChange({ skills: toggle(params.skills, v) })} />
    <Section title="More">
      <label><input type="checkbox" checked={!!params.remote} onChange={(e) => onChange({ remote: e.target.checked || undefined })} />Remote friendly</label>
      <label><input type="checkbox" checked={!!params.sponsor} onChange={(e) => onChange({ sponsor: e.target.checked || undefined })} />Recognised visa sponsor only</label>
      <label className="frow">Skills must match<select value={params.skills_mode ?? "any"} onChange={(e) => onChange({ skills_mode: e.target.value as "any" | "all" })}><option value="any">any of them</option><option value="all">all of them</option></select></label>
      <label className="frow">Minimum salary<input type="number" placeholder="€ per month" value={params.min_salary ?? ""} onChange={(e) => onChange({ min_salary: e.target.value ? +e.target.value : undefined })} /></label>
    </Section>
  </div>);
}
