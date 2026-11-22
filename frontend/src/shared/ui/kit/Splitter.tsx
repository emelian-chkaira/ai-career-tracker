import { usePersisted } from "./usePersisted";

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/** A pane width the user can change by dragging a divider. Remembered in this browser. `dir` is 1 when the pane is left of the divider, -1 when it is right of it. */
export function usePane(key: string, def: number, min: number, max: number, dir: 1 | -1 = 1) {
  const [w, setW] = usePersisted<number>("pane:" + key, def);
  const width = clamp(w, min, max);
  const props = {
    onMouseDown: (e: React.MouseEvent) => e.preventDefault(),
    onPointerDown: (e: React.PointerEvent) => {
      e.preventDefault(); const x0 = e.clientX, w0 = width; document.body.classList.add("resizing");
      const mv = (ev: PointerEvent) => setW(clamp(w0 + dir * (ev.clientX - x0), min, max));
      const up = () => { document.body.classList.remove("resizing"); (document.activeElement as HTMLElement | null)?.blur?.(); window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
      window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
    },
    onDoubleClick: () => setW(def),
    onKeyDown: (e: React.KeyboardEvent) => { if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); setW(clamp(width + dir * (e.key === "ArrowRight" ? 24 : -24), min, max)); } },
  };
  return { width, props };
}

/** The draggable divider itself. Double-click resets the width; arrow keys nudge it. */
export function Splitter({ props, label = "Resize panel" }: { props: ReturnType<typeof usePane>["props"]; label?: string }) {
  return <div className="split" role="separator" aria-orientation="vertical" aria-label={label} tabIndex={0} title="Drag to resize, double-click to reset" {...props}><i /></div>;
}
