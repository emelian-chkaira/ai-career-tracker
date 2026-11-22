import { useEffect } from "react";

const typing = (t: EventTarget | null) => { const e = t as HTMLElement | null; return !!e && (e.tagName === "INPUT" || e.tagName === "TEXTAREA" || e.tagName === "SELECT" || e.isContentEditable); };

/** Single-key shortcuts that never fire while typing or with a modifier held. Keys: j k / s Escape ... */
export function useShortcuts(map: Record<string, () => void>) {
  useEffect(() => {
    const f = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || typing(e.target)) return;
      const fn = map[e.key]; if (fn) { e.preventDefault(); fn(); }
    };
    window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f);
  });
}
