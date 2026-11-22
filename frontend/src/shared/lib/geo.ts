/** Small helpers for places: flag emoji from an ISO code, and labels for work modes and remote scopes. */
export const flag = (code?: string | null) => (code && /^[A-Z]{2}$/.test(code) ? String.fromCodePoint(...[...code].map((c) => 0x1f1a5 + c.charCodeAt(0))) : "🌍");
export const WORK_MODES: [string, string, string][] = [["onsite", "On-site", "🏢"], ["hybrid", "Hybrid", "🔀"], ["remote", "Remote", "🏠"]];
export const modeLabel = (m?: string | null) => WORK_MODES.find((x) => x[0] === m)?.[1] ?? "On-site";
export const SCOPE: Record<string, string> = { europe: "Europe", eu: "EU", emea: "EMEA", gcc: "Gulf", middle_east: "Middle East", mena: "MENA", africa: "Africa", world: "anywhere" };
