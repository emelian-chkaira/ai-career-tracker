import { useEffect, useRef } from "react";

/** A small "More" dropdown: one button instead of a row of rarely used ones. Closes on outside click, Escape and after choosing an item. */
export function Menu({ label, children, align = "right", className = "" }: { label: React.ReactNode; children: React.ReactNode; align?: "left" | "right"; className?: string }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const down = (e: MouseEvent) => { if (ref.current?.open && !ref.current.contains(e.target as Node)) ref.current.open = false; };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape" && ref.current?.open) ref.current.open = false; };
    document.addEventListener("mousedown", down); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", down); document.removeEventListener("keydown", key); };
  }, []);
  return (<details ref={ref} className={`menu ${align} ${className}`}>
    <summary className="btn ghost small" aria-haspopup="menu">{label}</summary>
    <div className="menu-pop" role="menu" onClick={(e) => { if ((e.target as HTMLElement).closest("button,a")) ref.current!.open = false; }}>{children}</div>
  </details>);
}
