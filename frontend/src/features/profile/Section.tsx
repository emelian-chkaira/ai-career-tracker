import type { ReactNode } from "react";

/** One settings block. Every section has the same width, padding and heading layout. */
export function Section({ title, hint, action, children, tone }: { title: string; hint?: ReactNode; action?: ReactNode; children?: ReactNode; tone?: "danger" }) {
  return (<section className={`card set-card${tone ? " " + tone : ""}`} aria-label={title}>
    <header className="set-head"><div><h2>{title}</h2>{hint && <p>{hint}</p>}</div>{action}</header>
    {children && <div className="set-body">{children}</div>}
  </section>);
}
