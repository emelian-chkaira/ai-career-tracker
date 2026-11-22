import { Switch } from "@/shared/ui/kit";

export type Block = { title?: string; heading?: string; place?: string; date?: string; desc?: string; tech?: string; bullets?: string[]; use?: "ai" | "always" | "exclude"; [k: string]: unknown };
export type CvLike = { order?: string[]; hidden?: string[]; [k: string]: unknown };
export const SECTIONS: [string, string][] = [["summary", "Summary"], ["experience", "Experience"], ["education", "Education"], ["projects", "Projects"], ["skills", "Skills"], ["languages", "Languages"], ["certifications", "Certifications"], ["references", "References"]];

/** The classic template reads one "heading" string; the others read title/place/date. Keep both in step. */
export const withHeading = (b: Block): Block => ({ ...b, heading: [b.title, b.place].filter(Boolean).join(" | ") + (b.date ? `  ${b.date}` : "") });
export const move = <T,>(a: T[], from: number, to: number) => { if (to < 0 || to >= a.length) return a; const c = [...a]; const [x] = c.splice(from, 1); c.splice(to, 0, x); return c; };
export const titleOf = (b: Block) => b.title ?? (b.heading ?? "").split(/\s*\|\s*|\s{2,}/)[0] ?? "";

/** Section toggles: switch a whole section on or off in the PDF and move it up or down. Hidden sections stay in your data. */
export function SectionToggles({ cv, edit }: { cv: CvLike; edit(p: Record<string, unknown>): void }) {
  const hidden = cv.hidden ?? [];
  const present = SECTIONS.filter(([k]) => { const v = cv[k]; return Array.isArray(v) ? v.length > 0 : !!v; }).map(([k]) => k);
  const order = [...new Set([...(cv.order ?? []).filter((k) => SECTIONS.some(([s]) => s === k)), ...present])];
  const label = (k: string) => SECTIONS.find(([s]) => s === k)?.[1] ?? k;
  const toggle = (k: string) => edit({ hidden: hidden.includes(k) ? hidden.filter((x) => x !== k) : [...hidden, k] });
  return (<div className="card stack" style={{ gap: 8 }}><h2 style={{ margin: 0 }}>Sections</h2>
    <ul className="plain stack" style={{ gap: 6 }}>{order.map((k, i) => <li key={k} className={`osec${hidden.includes(k) ? " off" : ""}`}><Switch checked={!hidden.includes(k)} onChange={() => toggle(k)} label={label(k)} /><span className="eblock-acts">
      <button className="kicon" disabled={i === 0} onClick={() => edit({ order: move(order, i, i - 1) })} aria-label={`Move ${label(k)} up`}>↑</button><button className="kicon" disabled={i === order.length - 1} onClick={() => edit({ order: move(order, i, i + 1) })} aria-label={`Move ${label(k)} down`}>↓</button></span></li>)}</ul></div>);
}
