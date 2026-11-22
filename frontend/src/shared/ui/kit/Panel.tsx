import * as Collapsible from "@radix-ui/react-collapsible";
import type { ReactNode } from "react";
import { usePersisted } from "./usePersisted";

/** A titled section that can be minimised. The open/closed state is remembered per `id`. */
export function Panel({ id, title, badge, actions, defaultOpen = true, children }: { id: string; title: ReactNode; badge?: ReactNode; actions?: ReactNode; defaultOpen?: boolean; children: ReactNode }) {
  const [open, setOpen] = usePersisted(`panel:${id}`, defaultOpen);
  return (<Collapsible.Root open={open} onOpenChange={setOpen} className="kpanel">
    <div className="kpanel-hd">
      <Collapsible.Trigger className="kpanel-tg" aria-label={`${open ? "Minimise" : "Expand"} ${typeof title === "string" ? title : "section"}`}><span className={`chev${open ? " open" : ""}`} aria-hidden>▸</span><span className="kpanel-title">{title}</span>{badge}</Collapsible.Trigger>
      {actions && <div className="kpanel-actions">{actions}</div>}
    </div>
    <Collapsible.Content className="kpanel-body">{children}</Collapsible.Content>
  </Collapsible.Root>);
}
