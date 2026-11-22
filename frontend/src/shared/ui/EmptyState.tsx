import { Icon } from "./Icon";
import type { ReactNode } from "react";

/** What a list shows when it has nothing yet: a picture, one sentence why, and the next step. */
export function EmptyState({ icon = <Icon name="search" size={20} />, title, children, action }: { icon?: ReactNode; title: ReactNode; children?: ReactNode; action?: ReactNode }) {
  return (<div className="emptystate"><div className="es-icon" aria-hidden>{icon}</div><b>{title}</b>{children && <div className="muted small">{children}</div>}{action && <div className="es-action">{action}</div>}</div>);
}
