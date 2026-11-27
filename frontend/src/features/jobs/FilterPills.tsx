import { useEffect, useRef } from "react";
import type { SearchParams } from "@/shared/api/types";
import { SEARCH_MODES } from "./Filters";

/** One pill that opens a small popover (LinkedIn / Indeed style). The pill shows the current choice and turns blue when a filter is on. */
function Pill({ name, value, on, children }: { name: string; value?: string; on: boolean; children: React.ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const down = (e: MouseEvent) => { if (ref.current?.open && !ref.current.contains(e.target as Node)) ref.current.open = false; };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape" && ref.current?.open) ref.current.open = false; };
    document.addEventListener("mousedown", down); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", down); document.removeEventListener("keydown", key); };
  }, []);
  return (<details ref={ref} className={"pill" + (on ? " on" : "")}><summary aria-haspopup="true"><span>{name}</span>{value && <b>{value}</b>}<i aria-hidden>▾</i></summary>
    <div className="pill-pop" onClick={(e) => { if ((e.target as HTMLElement).closest("[data-close]")) ref.current!.open = false; }}>{children}</div></details>);
}
function Choice({ checked, onChange, children, type = "radio", hint }: { checked: boolean; onChange(): void; children: React.ReactNode; type?: "radio" | "checkbox"; hint?: string }) {
  return (<label className="pill-opt" data-close={type === "radio" ? "" : undefined}><input type={type} checked={checked} onChange={onChange} /><span>{children}{hint && <small>{hint}</small>}</span></label>);
}

const DAYS: [number | undefined, string][] = [[undefined, "Any time"], [1, "Past 24 hours"], [7, "Past week"], [30, "Past month"]];
const MODES: [string, string][] = [["remote", "Remote"], ["hybrid", "Hybrid"], ["onsite", "On-site"]];
const LEVELS: [string, string][] = [["internship", "Internship"], ["traineeship", "Traineeship"], ["junior", "Junior"], ["job", "Medior"], ["senior", "Senior"]];
const LANGS: [string, string][] = [["english_ok", "English is enough"], ["dutch_plus", "Dutch is a plus"], ["dutch_required", "Dutch required"]];
const SALARY: [number | undefined, string][] = [[undefined, "Any"], [2500, "€2,500+ / month"], [3500, "€3,500+ / month"], [4500, "€4,500+ / month"], [6000, "€6,000+ / month"]];
const toggle = (a: string[] | undefined, v: string) => (a?.includes(v) ? a.filter((x) => x !== v) : [...(a ?? []), v]);
const short = (list: string[] | undefined, all: [string, string][]) => { const n = (list ?? []).map((v) => all.find((x) => x[0] === v)?.[1] ?? v); return n.length > 1 ? `${n[0]} +${n.length - 1}` : n[0]; };

export function FilterPills({ params, onChange, onAll, count }: { params: SearchParams; onChange(p: Partial<SearchParams>): void; onAll(): void; count: number }) {
  const mode = SEARCH_MODES.find((m) => m.key === (params.mode ?? "hybrid"))!;
  return (<div className="pills" role="group" aria-label="Quick filters">
    {params.q?.trim() && <Pill name="Match" value={mode.label} on={!!params.mode && params.mode !== "hybrid"}>
      {SEARCH_MODES.map((m) => <Choice key={m.key} checked={(params.mode ?? "hybrid") === m.key} onChange={() => onChange({ mode: m.key })} hint={m.hint}>{m.label}</Choice>)}</Pill>}
    <Pill name="Date posted" value={DAYS.find((d) => d[0] === params.days)?.[0] ? DAYS.find((d) => d[0] === params.days)![1].replace("Past ", "") : undefined} on={!!params.days}>
      {DAYS.map(([v, n]) => <Choice key={n} checked={params.days === v} onChange={() => onChange({ days: v })}>{n}</Choice>)}
      <p className="small muted" style={{ margin: "6px 4px 0" }}>A time range leaves out jobs with an unknown date.</p></Pill>
    <Pill name="Work mode" value={short(params.work_mode, MODES)} on={!!params.work_mode?.length}>
      {MODES.map(([v, n]) => <Choice key={v} type="checkbox" checked={!!params.work_mode?.includes(v)} onChange={() => onChange({ work_mode: toggle(params.work_mode, v) })}>{n}</Choice>)}</Pill>
    <Pill name="Level" value={short(params.job_type, LEVELS)} on={!!params.job_type?.length}>
      {LEVELS.map(([v, n]) => <Choice key={v} type="checkbox" checked={!!params.job_type?.includes(v)} onChange={() => onChange({ job_type: toggle(params.job_type, v) })}>{n}</Choice>)}</Pill>
    <Pill name="Language" value={short(params.language, LANGS)} on={!!params.language?.length}>
      {LANGS.map(([v, n]) => <Choice key={v} type="checkbox" checked={!!params.language?.includes(v)} onChange={() => onChange({ language: toggle(params.language, v) })}>{n}</Choice>)}</Pill>
    <Pill name="Salary" value={params.min_salary ? `€${params.min_salary.toLocaleString("nl-NL")}+` : undefined} on={!!params.min_salary}>
      {SALARY.map(([v, n]) => <Choice key={n} checked={params.min_salary === v} onChange={() => onChange({ min_salary: v })}>{n}</Choice>)}</Pill>
    <button type="button" className={"pill pill-btn" + (params.sponsor ? " on" : "")} aria-pressed={!!params.sponsor} onClick={() => onChange({ sponsor: params.sponsor ? undefined : true })}>Visa sponsor</button>
    <button type="button" className="pill pill-btn all" onClick={onAll}>All filters{count > 0 && <span className="fcount">{count}</span>}</button>
  </div>);
}
