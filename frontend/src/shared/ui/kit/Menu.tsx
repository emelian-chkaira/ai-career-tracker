import * as M from "@radix-ui/react-dropdown-menu";
import type { ReactNode } from "react";

export type MenuItem = { label: ReactNode; onSelect(): void; danger?: boolean; disabled?: boolean };
/** A button that opens a small action menu. */
export function Menu({ trigger, items, label = "More actions" }: { trigger: ReactNode; items: MenuItem[]; label?: string }) {
  return (<M.Root><M.Trigger className="btn ghost small" aria-label={label}>{trigger}</M.Trigger><M.Portal>
    <M.Content className="kmenu" align="end" sideOffset={6}>{items.map((i, n) => <M.Item key={n} className={`kmenu-i${i.danger ? " danger" : ""}`} disabled={i.disabled} onSelect={i.onSelect}>{i.label}</M.Item>)}</M.Content></M.Portal></M.Root>);
}
