const TEMPLATES: { id: string; name: string; blurb: string }[] = [
  { id: "mine", name: "My CV", blurb: "The look of my own CV: serif type, teal section rules, bold titles with dates on the right, labelled skills." },
  { id: "classic", name: "Classic", blurb: "Centred header, clear rules. The safest choice for applicant-tracking systems." },
  { id: "compact", name: "Compact", blurb: "Dense and tight, fits more on one page." },
  { id: "modern", name: "Modern", blurb: "Accent colour on headings, more air." }];

/** A tiny drawing of each layout, so the choice is visual. */
function Thumb({ id }: { id: string }) {
  const line = (w: number, k: number) => <i key={k} style={{ width: `${w}%` }} />;
  return (<div className={`thumb t-${id}`} aria-hidden><div className="th-head"><b /><i style={{ width: "46%" }} /></div>
    {[0, 1, 2].map((s) => <div key={s} className="th-sec"><b />{[92, 78, 86].map((w, k) => line(w, k))}</div>)}</div>);
}

export function TemplateGallery({ value, onChange }: { value: string; onChange(v: string): void }) {
  return (<div className="gallery" role="radiogroup" aria-label="Layout">{TEMPLATES.map((t) => (
    <button key={t.id} type="button" role="radio" aria-checked={value === t.id} aria-label={`${t.name} layout`} className={"gcard" + (value === t.id ? " on" : "")} onClick={() => onChange(t.id)} title={t.blurb}>
      <Thumb id={t.id} /><span className="gname">{t.name}</span></button>))}
    <div className="small muted" style={{ gridColumn: "1/-1" }}>{TEMPLATES.find((t) => t.id === value)?.blurb}</div></div>);
}
