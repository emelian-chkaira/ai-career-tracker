/** Made-up data for the demo's Crawler page. Every employer, job and account here is invented; nothing is fetched or changed. */
import { ApiError } from "@/shared/api/client";

export const BLOCKED = "This is a demo: nothing here runs, saves or deletes. Run the project on your computer to use it.";
export class DemoBlocked extends ApiError { constructor() { super(409, BLOCKED); } }

const ago = (min: number) => new Date(Date.now() - min * 60_000).toISOString();
const EMPLOYERS: [string, string, string, number][] = [["Aster Robotics", "Eindhoven", "greenhouse", 14], ["Bluepeak Energy", "Utrecht", "lever", 9], ["Canal Data Labs", "Amsterdam", "recruitee", 12], ["Delta Freight Systems", "Rotterdam", "workday", 21],
  ["Elm Health", "Leiden", "personio", 7], ["Fjord Payments", "Amsterdam", "greenhouse", 18], ["Gable Architects", "Delft", "html", 3], ["Harbor Security", "Den Haag", "html", 0], ["Ivy Learning", "Groningen", "recruitee", 5], ["Juniper Foods", "Nijmegen", "html", 0]];
const slug = (s: string) => s.toLowerCase().replace(/[^a-z]+/g, "-");
const companies = () => EMPLOYERS.map(([name, city, ats, n], i) => ({ id: i + 1, name, city, country: "NL", ats, source: i % 3 ? "European Tech Map" : "OpenStreetMap offices", website: `https://${slug(name)}.example`, careers_url: i === 9 ? null : `https://${slug(name)}.example/careers`,
  last_scan: ago(3 + i * 11), next_scan: ago(-600 + i * 30), scan_note: n ? `${n} postings read` : i === 7 ? "careers page did not answer" : "no open roles listed", fail_count: i === 7 ? 3 : 0, notes: null, open_jobs: n }));
const TITLES = ["Backend Developer", "Data Engineer", "Mobile Developer (Flutter)", "Frontend Developer", "DevOps Engineer", "QA Engineer", "Product Designer", "Software Engineering Intern", "Machine Learning Engineer", "Support Engineer", "Security Analyst", "Platform Engineer"];
const jobs = () => TITLES.map((title, i) => { const [company, city] = EMPLOYERS[i % 7]; return { id: 100 + i, title, url: `https://${slug(company)}.example/careers/${slug(title)}`, location: city, city, country: "NL", countries: ["NL"], work_mode: ["onsite", "hybrid", "remote"][i % 3], sector: "tech",
  domain: ["software", "data", "mobile", "software", "devops", "software"][i % 6], job_type: title.includes("Intern") ? "internship" : "job", source: i % 5 === 4 ? "board:indeed" : "company-site", status: "open", posted_at: ago(i * 700).slice(0, 10), first_seen: ago(i * 650), last_seen: ago(20), company, company_id: (i % 7) + 1, saved_by: i % 4 === 0 ? 1 : 0 }; });
const search = <T,>(rows: T[], q: unknown) => { const s = String(q ?? "").toLowerCase(); const items = s ? rows.filter((r) => JSON.stringify(r).toLowerCase().includes(s)) : rows; return { items, total: items.length, page: 1, limit: 25 }; };

const schedule = { enabled: true, days: [0, 1, 2, 3, 4, 5, 6], start: "00:00", end: "24:00", tz: "Europe/Amsterdam", revisit_hours: 12, parallel: 20 };
const status = () => ({ state: "running", seen_seconds: 2, pid: 4821, host: "your-computer", inflight: 20, task: null, allowed: true, why: "", next_start: null, note: "" });
const tasks = () => [
  { id: 42, kind: "scan_unscanned", status: "running", created_at: ago(6), finished_at: null, progress: { done: 318, total: 640, found: 97, new_jobs: 54, log: ["Reading Canal Data Labs: 12 postings"] } },
  { id: 41, kind: "discover", status: "done", created_at: ago(190), finished_at: ago(172), progress: { done: 4, total: 4, new_jobs: 0, found: 126 } },
  { id: 40, kind: "dedupe_jobs", status: "done", created_at: ago(1500), finished_at: ago(1497), progress: { merged: 38 } },
  { id: 39, kind: "sponsors_refresh", status: "done", created_at: ago(2900), finished_at: ago(2895), progress: { sponsors: 12480 } }];
const worker = () => ({ running: true, idle_seconds: 0, status: status(), schedule, tasks: [], total: 6240, due: 1180, rate_per_min: 34, eta_minutes: 35, open_jobs: 10870, new_jobs_hour: 163, saved_careers_pages: 3410,
  per_min: Array.from({ length: 30 }, (_, i) => ({ t: ago(29 - i), n: 22 + ((i * 7) % 17) })), recent: EMPLOYERS.slice(0, 8).map(([name, , ats, n], i) => ({ name, ats, note: n ? `${n} postings read` : "no open roles listed", at: ago(i * 0.4 + 0.1) })) });
const bySector = { tech: 2840, sales_marketing: 910, operations: 640, healthcare: 520, engineering: 480, people_legal: 330, finance: 260, architecture: 210, other: 4680 };
const byDomain = { software: 910, data: 640, devops: 350, mobile: 210, security: 180, other: 550 };
const pipeline = () => ({ discover: { companies: 6240, by_source: [{ source: "seed list", n: 2420 }, { source: "European Tech Map", n: 2148 }, { source: "OpenStreetMap offices", n: 1672 }], last: { kind: "discover", status: "done", at: ago(172) } },
  locate: { with_careers_page: 3410, with_job_system: 3290, not_found: 420, never_visited: 640 }, read: { visited_hour: 2040, visited_day: 5890, due: 1180, revisit_hours: 12, parallel: 20 },
  understand: { open_jobs: 10870, embedded: 9985, by_sector: Object.entries(bySector).map(([key, n]) => ({ key, n })), by_mode: [{ key: "onsite", n: 7410 }, { key: "hybrid", n: 2570 }, { key: "remote", n: 890 }] },
  keep: { countries: ["NL"], keep_remote: true, max_job_age_days: 0, delete_expired_after_days: 60, new_day: 412, expired_day: 188 }, notify: { saved_searches: 14, alerts_day: 31, emails_pending: 0 },
  boards: { enabled: true, jobs: 264, last: { kind: "board_search", status: "done", at: ago(300) }, every_hours: 12 } });
const policy = () => ({ countries: ["NL"], keep_remote: true, keep_domains: [], keep_sectors: ["tech"], saved_domains: [], saved_sectors: [], fields_mode: "auto", max_job_age_days: 0, delete_expired_after_days: 60,
  defaults: { countries: ["NL"], keep_remote: true, keep_domains: [], keep_sectors: [], fields_mode: "auto", max_job_age_days: 0, delete_expired_after_days: 60 },
  places: { countries: [["NL", "Netherlands", "benelux"], ["BE", "Belgium", "benelux"], ["DE", "Germany", "dach"], ["AT", "Austria", "dach"]].map(([code, name, r]) => ({ code, name, regions: [r, "eu"] })),
    regions: [{ key: "benelux", label: "Benelux", countries: ["NL", "BE"] }, { key: "dach", label: "DACH (Germany, Austria, Switzerland)", countries: ["DE", "AT"] }] },
  derived: { sectors: ["tech"], domains: ["software", "data"], users: 3 }, by_sector: bySector, by_domain: byDomain, by_country: { NL: 10870 }, by_age: { open: 10870, older_10: 4120, older_30: 1630, older_90: 240 } });
const SITES: [string, string, string][] = [["linkedin", "LinkedIn", "Blocks bursts of requests for about a minute; the strictest board."], ["indeed", "Indeed", "The most reliable board, rarely blocks."], ["glassdoor", "Glassdoor", "Works for some countries only."], ["bayt", "Bayt", "Jobs in the Middle East."]];
const plan = () => { const terms = ["Backend Developer", "Data Engineer"], sites = ["linkedin", "indeed"]; return { sites, terms: terms.map((term) => ({ term, from: "job title in a user's preferences" })), countries: ["NL"], dropped: 0, cap: 24, results_per_board: 30, requests: 4,
  searches: terms.map((term) => ({ term, country: "NL", boards: sites.map((site) => ({ site, where: "Netherlands", skip: null })) })) }; };
const boards = () => ({ enabled: true, installed: true, every_hours: 12, plan: plan(), health: SITES.map(([site, label, note], i) => ({ site, label, note, enabled: i < 2, resting_until: null, last_ok: i < 2 ? ago(300 + i * 4) : undefined, found_total: i < 2 ? [88, 176][i] : 0 })) });
const filters = () => { const opt = (a: [string, number][]) => a.map(([value, n]) => ({ value, n })); const places = { country: opt([["NL", 6240]]), city: opt([["Amsterdam", 1420], ["Rotterdam", 610], ["Utrecht", 540]]), source: opt([["site", 6100], ["board:indeed", 140]]) };
  return { companies: places, jobs: { ...places, sector: opt(Object.entries(bySector)), work_mode: opt([["onsite", 7410], ["hybrid", 2570], ["remote", 890]]) } }; };

const GET: Record<string, (q?: Record<string, unknown>) => unknown> = {
  "/admin/stats": () => ({ users: 3, companies: 6240, companies_scanned: 5600, companies_with_jobs: 1740, open_jobs: 10870, embedded_jobs: 9985, sponsors: 12480, saved_searches: 14, emails_pending: 0,
    scan_outcomes: [{ note: "postings read", n: 3290 }, { note: "no open roles listed", n: 1760 }, { note: "no careers page found", n: 420 }, { note: "website did not answer", n: 130 }] }),
  "/admin/worker": worker, "/admin/tasks": tasks, "/admin/pipeline": pipeline, "/admin/policy": policy, "/admin/boards": boards, "/admin/filters": filters,
  "/admin/schedule": () => ({ ...schedule, allowed_now: true, why: "", next_start: null }),
  "/admin/perf": () => ({ browser_slots: 5, scan_threads: 16, page_wait_ms: 3000, ats_first: true, internship_pass: true, parallel: 20, defaults: { browser_slots: 5, scan_threads: 16, page_wait_ms: 3000, ats_first: true, internship_pass: true }, limits: { browser_slots: [1, 12], scan_threads: [1, 40], page_wait_ms: [500, 15000], parallel: [1, 40] } }),
  "/admin/source-health": () => ({ totals: { companies: 6240, never_scanned: 640, failing: 37, stale: 112 }, by_ats: [["greenhouse", 410, 2, 2600], ["recruitee", 620, 4, 2100], ["lever", 190, 1, 940], ["workday", 140, 6, 1730], ["personio", 480, 3, 1100], ["html", 1450, 21, 2400]].map(([ats, c, f, o]) => ({ ats, companies: c, failing: f, open_jobs: o })),
    failing: [{ id: 8, name: "Harbor Security", ats: "html", fail_count: 3, last_scan: ago(80), scan_note: "careers page did not answer" }] }),
  "/admin/users": () => [["admin", "admin"], ["sam", "user"], ["noor", "user"]].map(([n, role], i) => ({ id: `demo-${i}`, email: `${n}@example.com`, role, active: true, created_at: ago((30 - i * 7) * 1440) })),
  "/admin/companies": (q) => search(companies(), q?.q), "/admin/jobs": (q) => search(jobs(), q?.q),
};

/** Answers the Crawler page's admin calls. Returns undefined for everything else, so the rest of the demo keeps working. */
export function crawlerSample(method: string, path: string, query: Record<string, unknown> | undefined, blocked: () => void): unknown {
  if (!path.startsWith("/admin/")) return undefined;
  if (method === "POST" && path === "/admin/boards/plan") return plan();
  if (method === "GET") {
    if (GET[path]) return GET[path](query);
    if (/^\/admin\/maintenance\/\w+\/preview$/.test(path)) return path.includes("purge") ? { too_old_deleted: 240 } : { jobs: 120 };
  }
  blocked(); throw new DemoBlocked();
}
