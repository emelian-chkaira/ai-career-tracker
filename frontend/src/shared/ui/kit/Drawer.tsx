import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

/** A side sheet with focus trap, Esc to close and a scrim. `side` left or right; `size` is the width. */
export function Drawer({ open, onOpenChange, title, side = "right", size = 560, children, footer }: { open: boolean; onOpenChange(o: boolean): void; title: string; side?: "left" | "right"; size?: number; children: ReactNode; footer?: ReactNode }) {
  return (<Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal>
    <Dialog.Overlay className="kscrim" />
    <Dialog.Content className={`kdrawer ${side}`} style={{ width: `min(${size}px, 100vw)` }} aria-describedby={undefined}>
      <div className="kdrawer-hd"><Dialog.Title>{title}</Dialog.Title><Dialog.Close className="kicon" aria-label="Close">✕</Dialog.Close></div>
      <div className="kdrawer-bd">{children}</div>
      {footer && <div className="kdrawer-ft">{footer}</div>}
    </Dialog.Content></Dialog.Portal></Dialog.Root>);
}
