import { useState } from "react";
import { flag } from "@/shared/lib/geo";

export type CountryOption = { code: string; name: string; jobs: number };

/** Countries with jobs, the chosen ones first, then the busiest. Typing narrows the list by name or ISO code. */
export function orderCountries(all: CountryOption[], selected: string[], find: string): CountryOption[] {
  const q = find.trim().toLowerCase();
  return all.filter((c) => (c.jobs > 0 || selected.includes(c.code)) && (!q || c.name.toLowerCase().includes(q) || c.code.toLowerCase() === q))
    .sort((a, b) => Number(selected.includes(b.code)) - Number(selected.includes(a.code)) || b.jobs - a.jobs);
}

export function CountryPicker({ countries, selected, onChange, clearLabel }: { countries: CountryOption[]; selected: string[]; onChange(next: string[]): void; clearLabel: string }) {
  const [find, setFind] = useState("");
  const shown = orderCountries(countries, selected, find);
  return (<>
    <input type="search" className="pill-find" value={find} onChange={(e) => setFind(e.target.value)} placeholder="Find a country" aria-label="Find a country" />
    <div className="pill-scroll">
      {shown.map((c) => <label key={c.code} className="pill-opt"><input type="checkbox" checked={selected.includes(c.code)} onChange={() => onChange(selected.includes(c.code) ? selected.filter((x) => x !== c.code) : [...selected, c.code])} /><span>{flag(c.code)} {c.name}</span></label>)}
      {!shown.length && <p className="small muted" style={{ margin: "6px 10px" }}>No country with jobs matches.</p>}
    </div>
    {selected.length > 0 && <button type="button" className="linkbtn small" data-close="" onClick={() => onChange([])}>{clearLabel}</button>}
  </>);
}
