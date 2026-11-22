import { useCallback, useState } from "react";

/** useState that remembers its value in this browser (never throws: private mode just forgets). */
export function usePersisted<T>(key: string, initial: T): [T, (v: T | ((p: T) => T)) => void] {
  const [v, setV] = useState<T>(() => { try { const s = localStorage.getItem("ui:" + key); return s == null ? initial : (JSON.parse(s) as T); } catch { return initial; } });
  const set = useCallback((n: T | ((p: T) => T)) => setV((p) => { const x = typeof n === "function" ? (n as (p: T) => T)(p) : n; try { localStorage.setItem("ui:" + key, JSON.stringify(x)); } catch { /* ignore */ } return x; }), [key]);
  return [v, set];
}
