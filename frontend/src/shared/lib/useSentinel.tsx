import { useEffect, useRef } from "react";

/** Infinite scroll trigger: put the returned ref on an element at the end of a list; `load` runs each time it comes into view (inside any scrolling parent). */
export function useSentinel(load: () => void, enabled: boolean) {
  const ref = useRef<HTMLDivElement>(null); const fn = useRef(load); fn.current = load;
  useEffect(() => {
    const el = ref.current; if (!el || !enabled) return;
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) fn.current(); }, { rootMargin: "300px" });
    io.observe(el); return () => io.disconnect();
  }, [enabled]);
  return ref;
}

/** The footer of an endless list. */
export function ListEnd({ sentinel, more, loading, count, total }: { sentinel: React.RefObject<HTMLDivElement>; more: boolean; loading: boolean; count: number; total: number }) {
  return (<div ref={sentinel} className="lend small muted" aria-live="polite">{loading ? "Loading more…" : more ? "" : count > 0 ? `That's all ${total.toLocaleString()}.` : ""}</div>);
}
