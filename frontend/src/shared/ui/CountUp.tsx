import { useEffect, useRef, useState } from "react";

const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** A number that counts up to its value (and eases to new values). Plain text for screen readers and reduced motion. */
export function CountUp({ value, duration = 900, format = (n: number) => Math.round(n).toLocaleString() }: { value: number; duration?: number; format?: (n: number) => string }) {
  const [shown, setShown] = useState(reduced() ? value : 0); const from = useRef(reduced() ? value : 0);
  useEffect(() => {
    if (reduced()) { setShown(value); return; }
    const start = performance.now(), a = from.current, b = value; let raf = 0;
    const tick = (t: number) => { const k = Math.min(1, (t - start) / duration), e = 1 - Math.pow(1 - k, 3); setShown(a + (b - a) * e); if (k < 1) raf = requestAnimationFrame(tick); else from.current = b; };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <span className="countup" aria-label={format(value)}>{format(shown)}</span>;
}
