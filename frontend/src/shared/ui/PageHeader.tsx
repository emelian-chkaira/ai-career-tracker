import type { ReactNode } from "react";

/** The top of a page: a small eyebrow, the title (optionally with an icon), one line of explanation, and actions on the right. */
export function PageHeader({ title, eyebrow, subtitle, icon, actions, children }: { title: ReactNode; eyebrow?: ReactNode; subtitle?: ReactNode; icon?: ReactNode; actions?: ReactNode; children?: ReactNode }) {
  return (<header className="pagehead">
    <div className="ph-main">
      {eyebrow && <div className="ph-eyebrow">{eyebrow}</div>}
      <h1 className="ph-title">{icon && <span className="ph-icon" aria-hidden>{icon}</span>}{title}</h1>
      {subtitle && <div className="ph-sub">{subtitle}</div>}
    </div>
    {actions && <div className="ph-actions">{actions}</div>}
    {children}
  </header>);
}
