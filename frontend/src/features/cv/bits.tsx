import { useState } from "react";

export function Tags({ items, onChange, placeholder }: { items: string[]; onChange(v: string[]): void; placeholder: string }) {
  const [v, setV] = useState("");
  const add = () => { const t = v.trim(); if (t) onChange([...items, t]); setV(""); };
  return (<div className="stack" style={{ gap: 8 }}>
    <div className="tags">{items.map((t, i) => <span className="tag" key={i}>{t}<button aria-label="remove" onClick={() => onChange(items.filter((_, j) => j !== i))}>×</button></span>)}</div>
    <input type="text" value={v} placeholder={placeholder} onChange={(e) => setV(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} onBlur={add} />
  </div>);
}
export const Field = ({ label, children }: { label: string; children: React.ReactNode }) => <label className="field"><span className="flabel">{label}</span>{children}</label>;
