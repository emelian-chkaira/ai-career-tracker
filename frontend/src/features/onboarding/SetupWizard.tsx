import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { Modal, Switch } from "@/shared/ui/kit";
import { useSectors } from "@/shared/api/meta";
import type { Profile } from "@/shared/api/types";
import { flag, modeLabel, WORK_MODES } from "@/shared/lib/geo";
import { announceCrawl } from "@/features/jobs/CrawlNotice";

export { useSectors } from "@/shared/api/meta";
export const openSetup = () => window.dispatchEvent(new Event("open-setup"));

const CITIES = ["Amsterdam", "Rotterdam", "Utrecht", "Eindhoven", "Den Haag", "Delft", "Leiden", "Groningen", "Nijmegen", "Arnhem", "Tilburg", "Breda", "Haarlem", "Amersfoort", "Enschede", "Zwolle", "Maastricht"];
const LEVELS: [string, string][] = [["internship", "Internship"], ["traineeship", "Traineeship"], ["junior", "Junior"], ["job", "Medior"], ["senior", "Senior / lead"]];
const MAX_SECTORS = 3;

/** Toggle chips from suggestions, plus free text (Enter or comma adds). */
export function ChipPicker({ label, value, onChange, options = [], placeholder, max = 30 }: { label: string; value: string[]; onChange(v: string[]): void; options?: string[]; placeholder?: string; max?: number }) {
  const [txt, setTxt] = useState(""); const low = value.map((v) => v.toLowerCase());
  const add = (raw: string) => { const v = raw.trim().replace(/,$/, ""); if (v && !low.includes(v.toLowerCase()) && value.length < max) onChange([...value, v]); setTxt(""); };
  const toggle = (o: string) => onChange(low.includes(o.toLowerCase()) ? value.filter((v) => v.toLowerCase() !== o.toLowerCase()) : value.length < max ? [...value, o] : value);
  const extra = value.filter((v) => !options.some((o) => o.toLowerCase() === v.toLowerCase()));
  return (<div className="cpick"><div className="cpick-l">{label}</div>
    <div className="cpick-row" role="group" aria-label={label}>
      {[...options, ...extra].map((o) => { const on = low.includes(o.toLowerCase()); return <button type="button" key={o} className={`cchip${on ? " on" : ""}`} aria-pressed={on} onClick={() => toggle(o)}>{on ? "✓ " : "+ "}{o}</button>; })}
      <input type="text" className="cpick-in" value={txt} placeholder={placeholder ?? "Add your own…"} aria-label={`Add to ${label}`}
        onChange={(e) => { const v = e.target.value; if (v.endsWith(",")) add(v); else setTxt(v); }}
        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(txt); } else if (e.key === "Backspace" && !txt && value.length) onChange(value.slice(0, -1)); }} onBlur={() => txt && add(txt)} />
    </div></div>);
}

type P = Profile; type Set = (patch: Partial<P>) => void;

export function SectorStep({ p, set }: { p: P; set: Set }) {
  const { data } = useSectors(); const sel = p.sectors ?? [];
  const toggle = (k: string) => set({ sectors: sel.includes(k) ? sel.filter((x) => x !== k) : sel.length < MAX_SECTORS ? [...sel, k] : sel });
  return (<div className="stack"><div className="muted small">Pick up to {MAX_SECTORS}. Your feed, match score and alerts follow these. The catalogue is strongest in tech; other fields grow as more employers are crawled.</div>
    <div className="seccards">{(data?.sectors ?? []).map((s) => { const on = sel.includes(s.key); return (
      <button type="button" key={s.key} className={`seccard${on ? " on" : ""}`} aria-pressed={on} onClick={() => toggle(s.key)}>
        <b>{s.label}</b><span className="small muted">{s.blurb}</span><span className="small seccount">{s.jobs ? `${s.jobs.toLocaleString()} open jobs` : "no jobs yet"}</span></button>); })}
      {!data && <div className="muted">Loading sectors…</div>}</div></div>);
}

/** Countries of the user's profile: the legacy single `country` counts when the list is empty. */
export const myCountries = (p: P) => p.countries ?? (p.country ? [p.country] : []);

/** Regions as one-click groups, countries grouped by region with a search box, and a summary of what is picked. */
export function PlacePicker({ countries, regions, onChange }: { countries: string[]; regions: string[]; onChange(c: string[], r: string[]): void }) {
  const { data } = useSectors(); const [q, setQ] = useState(""); const [open, setOpen] = useState(false);
  const all = data?.countries ?? []; const name = (c: string) => all.find((x) => x.code === c)?.name ?? c;
  const toggleC = (c: string) => onChange(countries.includes(c) ? countries.filter((x) => x !== c) : [...countries, c], regions);
  const toggleR = (r: string) => onChange(countries, regions.includes(r) ? regions.filter((x) => x !== r) : [...regions, r]);
  const groups: [string, string][] = [["benelux", "Benelux"], ["dach", "DACH"], ["uk_ie", "UK & Ireland"], ["nordics", "Nordics & Baltics"], ["south", "Southern Europe"], ["cee", "Central & Eastern Europe"], ["gcc", "Gulf (GCC)"], ["middle_east", "Middle East"], ["africa", "Africa"]];
  const shown = all.filter((c) => !q || c.name.toLowerCase().includes(q.toLowerCase()) || c.code.toLowerCase() === q.toLowerCase());
  return (<div className="stack" style={{ gap: 10 }}>
    <div className="cpick"><div className="cpick-l">Whole regions</div><div className="cpick-row">{(data?.regions ?? []).map((r) => { const on = regions.includes(r.key); return (
      <button type="button" key={r.key} className={`cchip${on ? " on" : ""}`} aria-pressed={on} title={r.countries.map(name).join(", ")} onClick={() => toggleR(r.key)}>{on ? "✓ " : ""}{r.label}{r.jobs ? <span className="cn">{r.jobs.toLocaleString()}</span> : null}</button>); })}</div></div>
    <div className="cpick"><div className="cpick-l">Countries</div>
      <div className="cpick-row">{countries.map((c) => <button type="button" key={c} className="cchip on" onClick={() => toggleC(c)} aria-label={`Remove ${name(c)}`}>{flag(c)} {name(c)} ✕</button>)}
        <button type="button" className="cchip" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Done" : countries.length ? "+ Add country" : "+ Choose countries"}</button></div>
      {open && <div className="cbox"><input type="search" className="cpick-in" placeholder="Search a country…" value={q} onChange={(e) => setQ(e.target.value)} autoFocus aria-label="Search countries" />
        {groups.map(([rk, rl]) => { const list = shown.filter((c) => c.regions.includes(rk) && (rk !== "middle_east" || !c.regions.includes("gcc")) && (rk !== "cee" || !c.regions.includes("nordics"))); if (!list.length) return null; return (
          <div key={rk} className="cgroup"><div className="small muted">{rl}</div><div className="cpick-row">{list.map((c) => { const on = countries.includes(c.code); return (
            <button type="button" key={c.code} className={`cchip${on ? " on" : ""}`} aria-pressed={on} onClick={() => toggleC(c.code)}>{flag(c.code)} {c.name}{c.jobs ? <span className="cn">{c.jobs.toLocaleString()}</span> : null}</button>); })}</div></div>); })}</div>}</div>
    <div className="small muted">{!countries.length && !regions.length ? "Nothing picked: jobs from every country we crawl." : `Covers ${[...new Set([...countries, ...regions.flatMap((r) => data?.regions.find((x) => x.key === r)?.countries ?? [])])].length} countries.`} Jobs are only there for countries the crawler collects (Crawler → Countries).</div>
  </div>);
}

export function WorkModePicker({ value, onChange }: { value: string[]; onChange(v: string[]): void }) {
  return (<div className="cpick"><div className="cpick-l">How do you want to work? <span className="muted small">(none = any)</span></div><div className="cpick-row">{WORK_MODES.map(([k, l, i]) => { const on = value.includes(k); return (
    <button type="button" key={k} className={`cchip${on ? " on" : ""}`} aria-pressed={on} onClick={() => onChange(on ? value.filter((x) => x !== k) : [...value, k])}>{i} {l}</button>); })}</div></div>);
}

export function PlaceStep({ p, set }: { p: P; set: Set }) {
  return (<div className="stack">
    <PlacePicker countries={myCountries(p)} regions={p.regions ?? []} onChange={(c, r) => set({ countries: c, regions: r })} />
    <ChipPicker label="Cities (optional: leave empty for whole countries)" value={p.cities ?? []} onChange={(v) => set({ cities: v })} options={CITIES.slice(0, 8)} placeholder="Any city, e.g. Berlin, Dubai…" />
    <WorkModePicker value={p.work_modes ?? []} onChange={(v) => set({ work_modes: v })} />
    <Switch checked={p.remote_ok !== false} onChange={(v) => set({ remote_ok: v })} label="Remote jobs open to my countries count as near me" />
    <Switch checked={!!p.sponsor_needed} onChange={(v) => set({ sponsor_needed: v })} label="I need visa sponsorship (show NL IND-recognised sponsors only)" />
  </div>);
}

export function RoleStep({ p, set }: { p: P; set: Set }) {
  const { data } = useSectors(); const sel = p.sectors ?? [];
  const sugg = useMemo(() => [...new Set((data?.sectors ?? []).filter((s) => sel.includes(s.key)).flatMap((s) => s.titles))].slice(0, 14), [data, sel]);
  const lv = p.job_types ?? [];
  return (<div className="stack">
    <ChipPicker label="Job titles you are looking for" value={p.titles ?? []} onChange={(v) => set({ titles: v })} options={sugg} placeholder="e.g. Junior Architect" />
    <div className="cpick"><div className="cpick-l">Level <span className="muted small">(none = any; postings that do not state a level are always included)</span></div><div className="cpick-row">{LEVELS.map(([k, l]) => { const on = lv.includes(k); return <button type="button" key={k} className={`cchip${on ? " on" : ""}`} aria-pressed={on} onClick={() => set({ job_types: on ? lv.filter((x) => x !== k) : [...lv, k] })}>{l}</button>; })}</div></div>
    <Switch checked={!!p.english_only} onChange={(v) => set({ english_only: v })} label="Only jobs where English is enough (hide “Dutch required”)" />
  </div>);
}

export function SkillsStep({ p, set, withCv = true }: { p: P; set: Set; withCv?: boolean }) {
  const { data } = useSectors(); const sel = p.sectors ?? []; const qc = useQueryClient();
  const sugg = useMemo(() => [...new Set((data?.sectors ?? []).filter((s) => sel.includes(s.key)).flatMap((s) => s.skills))].slice(0, 16), [data, sel]);
  const [cvMsg, setCvMsg] = useState(""); const [busy, setBusy] = useState(false); const file = useRef<HTMLInputElement>(null);
  const upload = async (f: File) => {
    setBusy(true); setCvMsg("");
    try {
      const r = await api.upload<{ cv: { skills?: string[]; skill_groups?: { items: string[] }[]; experience?: unknown[] }; latex: string; source?: string }>("/cv/extract", f, { filename: f.name });
      await api.put("/me/cv/draft", { draft: r });
      const found = [...new Set([...(r.cv.skills ?? []), ...(r.cv.skill_groups ?? []).flatMap((g) => g.items)])];
      set({ skills: [...new Set([...(p.skills ?? []), ...found.slice(0, 12)])] });
      qc.invalidateQueries({ queryKey: ["stored-cv"] });
      setCvMsg(`Read your CV: ${found.length} skills found, ${(r.cv.experience ?? []).length} experience entries. It is saved to your account and open in CV Studio.`);
    } catch (e) { setCvMsg((e as Error).message); } finally { setBusy(false); }
  };
  return (<div className="stack">
    {withCv && <div className="cvdrop"><div><b>Upload your CV</b> <span className="small muted">(PDF, DOCX or .tex, optional)</span><div className="small muted">We read your skills from it to rank jobs. It stays in your account only.</div></div>
      <button type="button" className="btn ghost" disabled={busy} onClick={() => file.current?.click()}>{busy ? "Reading…" : "Choose file"}</button>
      <input ref={file} type="file" hidden accept=".pdf,.docx,.tex,.txt" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
      {cvMsg && <div className="small" role="status">{cvMsg}</div>}</div>}
    <ChipPicker label="Skills and tools" value={p.skills ?? []} onChange={(v) => set({ skills: v })} options={sugg} placeholder="e.g. Revit" max={60} />
    <ChipPicker label="Other words that make a job interesting (optional)" value={p.keywords ?? []} onChange={(v) => set({ keywords: v })} placeholder="e.g. sustainability, timber, healthcare" />
  </div>);
}

const STEPS = [
  { title: "What field do you work in?", node: SectorStep, ok: (p: P) => !!p.sectors?.length },
  { title: "Where do you want to work?", node: PlaceStep, ok: () => true },
  { title: "What are you looking for?", node: RoleStep, ok: () => true },
  { title: "Your skills and CV", node: SkillsStep, ok: () => true },
];

/** Opens once after sign-up (until finished or skipped) and again from Settings. Each Next saves, so it can be resumed. */
export function SetupWizard() {
  const { user, saveProfile } = useAuth(); const qc = useQueryClient(); const go = useNavigate();
  const [open, setOpen] = useState(false); const [i, setI] = useState(0); const [p, setP] = useState<P>({}); const [alert, setAlert] = useState(true); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const later = useRef(false);
  useEffect(() => { if (user && user.profile?.onboarded !== true && !later.current) { setP(user.profile ?? {}); setOpen(true); } }, [user?.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const h = () => { if (user) { setP(user.profile ?? {}); setI(0); setOpen(true); } }; window.addEventListener("open-setup", h); return () => window.removeEventListener("open-setup", h); }, [user]);
  const sectors = useSectorsLabel(p.sectors);
  const sec = useSectors().data; const cname = (c: string) => sec?.countries.find((x) => x.code === c)?.name ?? c;
  if (!user) return null;
  const set: Set = (patch) => setP((x) => ({ ...x, ...patch }));
  const pick = (x: P): P => ({ sectors: x.sectors, countries: myCountries(x), regions: x.regions ?? [], work_modes: x.work_modes ?? [], cities: x.cities ?? [], remote_ok: x.remote_ok !== false, sponsor_needed: !!x.sponsor_needed, titles: x.titles ?? [], job_types: x.job_types ?? [], english_only: !!x.english_only, skills: x.skills ?? [], keywords: x.keywords ?? [] });
  const step = async (n: number) => { setErr(""); try { const u = await saveProfile(pick(p)); if (i === 1) announceCrawl(u.crawl, cname); setI(n); } catch (e) { setErr((e as Error).message); } };
  const finish = async () => {
    setBusy(true); setErr("");
    try {
      announceCrawl((await saveProfile({ ...pick(p), onboarded: true })).crawl, cname);
      if (alert) await api.post("/me/searches", { name: "My feed", params: { scope: "mine" }, alert_frequency: "daily" }).catch(() => undefined);
      qc.invalidateQueries({ queryKey: ["jobs"] }); qc.invalidateQueries({ queryKey: ["searches"] }); setOpen(false); go("/");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  const skip = async () => { try { await saveProfile({ onboarded: true }); } catch { /* still close */ } setOpen(false); };
  const done = i >= STEPS.length; const S = STEPS[Math.min(i, STEPS.length - 1)];
  return (<Modal open={open} onOpenChange={(o) => { if (!o) { later.current = true; setOpen(false); } }} width={900} title={done ? "Your feed is ready" : `Set up your search · ${i + 1} of ${STEPS.length}`}
    footer={<div className="row" style={{ width: "100%" }}>
      <button className="btn ghost small" onClick={skip}>Skip setup</button>
      <span className="small bad">{err}</span>
      <div className="row right">{i > 0 && <button className="btn ghost" onClick={() => setI(i - 1)}>Back</button>}
        {done ? <button className="btn" disabled={busy} onClick={finish}>{busy ? "Saving…" : "Show my jobs"}</button>
          : <button className="btn" disabled={!S.ok(p)} title={S.ok(p) ? undefined : "Pick at least one field"} onClick={() => step(i + 1)}>Next</button>}</div></div>}>
    <div className="wiz">
      <ol className="wiz-steps" aria-label="Progress">{STEPS.map((s, n) => <li key={s.title} className={n === i ? "on" : n < i ? "done" : ""}><span>{n < i ? "✓" : n + 1}</span>{s.title}</li>)}<li className={done ? "on" : ""}><span>★</span>Done</li></ol>
      <div className="wiz-body" key={i}>
        {!done ? <><h2>{S.title}</h2><S.node p={p} set={set} /></> : (<div className="stack">
          <div className="wiz-sum">
            <div><span className="muted small">Field</span><b>{sectors || "Any"}</b></div>
            <div><span className="muted small">Where</span><b>{[...myCountries(p).map((c) => `${flag(c)} ${c}`), ...(p.regions ?? [])].join(", ") || "Every country"}{p.cities?.length ? ` · ${p.cities.join(", ")}` : ""}{p.work_modes?.length ? ` · ${p.work_modes.map(modeLabel).join("/")}` : ""}</b></div>
            <div><span className="muted small">Titles</span><b>{p.titles?.join(", ") || "Any title"}</b></div>
            <div><span className="muted small">Skills</span><b>{p.skills?.slice(0, 8).join(", ") || "None yet"}</b></div>
          </div>
          <div className="small muted">Jobs, internships and alerts now start from this profile (“My feed”). Switch to “All jobs” any time, and change everything in Settings → Preferences.</div>
          <label className="row small"><input type="checkbox" checked={alert} onChange={(e) => setAlert(e.target.checked)} /> E-mail and notify me daily about new jobs in my feed</label>
          <div className="small muted">Optional next steps: choose an AI model in Settings for fit scores and tailored CVs.</div></div>)}
      </div></div></Modal>);
}

function useSectorsLabel(keys?: string[]) { const { data } = useSectors(); return (keys ?? []).map((k) => data?.sectors.find((s) => s.key === k)?.label ?? k).join(", "); }
