/** Browser storage that belongs to ONE account. Every key is suffixed with the signed-in user's id (or "anon"),
 *  so a second account on the same computer never sees the first one's CV draft, consent or setup state.
 *  The server is the source of truth for anything that matters (CV, profile); this is only a fast local cache. */
let uid: string | null = null;
const LEGACY = ["cv-draft-v2", "ai-consent", "onboarding-dismissed", "cv-template", "cv-paper"];   // were shared by every account on this browser

export const setStorageUser = (id: string | null) => { uid = id; };
export const ukey = (k: string) => `${k}:${uid ?? "anon"}`;
export function uget(k: string): string | null { try { return localStorage.getItem(ukey(k)); } catch { return null; } }
export function uset(k: string, v: string | null) { try { v == null ? localStorage.removeItem(ukey(k)) : localStorage.setItem(ukey(k), v); } catch { /* private mode / quota */ } }

/** On sign-out: drop this account's cached copies (they live on the server) and anything left from before per-account keys existed. */
export function forgetUser(id: string | null) {
  try {
    const drop = Object.keys(localStorage).filter((k) => LEGACY.includes(k) || (id && k.endsWith(":" + id)) || k.endsWith(":anon"));
    drop.forEach((k) => localStorage.removeItem(k));
  } catch { /* private mode */ }
}
export function dropLegacy() { try { LEGACY.forEach((k) => localStorage.removeItem(k)); } catch { /* private mode */ } }
