import { useSyncExternalStore } from "react";

/** Which postings you have opened, remembered in this browser (newest 3000). */
const KEY = "jobs:viewed";
const read = (): number[] => { try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; } };
let seen = new Set<number>(read());
const subs = new Set<() => void>();

export function markViewed(id: number) {
  if (seen.has(id)) return;
  seen = new Set([...seen, id].slice(-3000));
  try { localStorage.setItem(KEY, JSON.stringify([...seen])); } catch { /* private window: remembered until reload */ }
  subs.forEach((f) => f());
}

export const useViewed = (id: number) => useSyncExternalStore((f) => { subs.add(f); return () => { subs.delete(f); }; }, () => seen.has(id));
