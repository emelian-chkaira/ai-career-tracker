import type { ReactNode } from "react";
import { usePersisted } from "./usePersisted";

/** A floating window pinned to a corner: minimise it to a title bar, expand it, or close it. Great for chat that should stay out of the way. */
export function Dock({ id, title, onClose, children, width = 380, offset = 0 }: { id: string; title: ReactNode; onClose?(): void; children: ReactNode; width?: number; offset?: number }) {
  const [min, setMin] = usePersisted(`dock:${id}`, false);
  return (<section className={`kdock${min ? " min" : ""}`} style={{ width: `min(${width}px, calc(100vw - 24px))`, right: 16 + offset }} aria-label={typeof title === "string" ? title : "Window"}>
    <header className="kdock-hd" onDoubleClick={() => setMin(!min)}><b className="kdock-title">{title}</b>
      <button className="kicon" onClick={() => setMin(!min)} aria-label={min ? "Expand" : "Minimise"} aria-expanded={!min}>{min ? "▴" : "–"}</button>
      {onClose && <button className="kicon" onClick={onClose} aria-label="Close">✕</button>}</header>
    {!min && <div className="kdock-bd">{children}</div>}
  </section>);
}
