import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

/** A centred dialog with focus trap and Esc to close. Put the action buttons in `footer`. */
export function Modal({ open, onOpenChange, title, children, footer, width = 640 }: { open: boolean; onOpenChange(o: boolean): void; title: string; children: ReactNode; footer?: ReactNode; width?: number }) {
  return (<Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal>
    <Dialog.Overlay className="kscrim" />
    <Dialog.Content className="kmodal" style={{ width: `min(${width}px, 96vw)` }} aria-describedby={undefined}>
      <div className="kdrawer-hd"><Dialog.Title>{title}</Dialog.Title><Dialog.Close className="kicon" aria-label="Close">✕</Dialog.Close></div>
      <div className="kdrawer-bd">{children}</div>
      {footer && <div className="kdrawer-ft">{footer}</div>}
    </Dialog.Content></Dialog.Portal></Dialog.Root>);
}
