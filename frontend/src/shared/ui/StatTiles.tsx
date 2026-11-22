import type { ReactNode } from "react";
import { CountUp } from "./CountUp";

export type Stat = { label: ReactNode; value: number | null | undefined; icon?: ReactNode; hint?: string; onClick?: () => void; format?: (n: number) => string };

/** A row of figures that count up when they appear. Clickable tiles act like buttons. */
export function StatTiles({ stats, compact = false }: { stats: Stat[]; compact?: boolean }) {
  return (<div className={`stiles${compact ? " compact" : ""}`}>{stats.map((s, i) => {
    const body = <>{s.icon && <span className="st-icon" aria-hidden>{s.icon}</span>}<b>{s.value == null ? "–" : <CountUp value={s.value} format={s.format} />}</b><span>{s.label}</span></>;
    return s.onClick ? <button key={i} className="stile" title={s.hint} onClick={s.onClick} style={{ animationDelay: `${i * 60}ms` }}>{body}</button>
      : <div key={i} className="stile" title={s.hint} style={{ animationDelay: `${i * 60}ms` }}>{body}</div>;
  })}</div>);
}
