import { Icon } from "@/shared/ui/Icon";
import { PageHeader } from "@/shared/ui";
import { useState } from "react";
import { api } from "@/shared/api/client";
import { myCountries, openSetup, PlaceStep, RoleStep, SectorStep, SkillsStep } from "@/features/onboarding/SetupWizard";
import type { Profile } from "@/shared/api/types";
import { announceCrawl } from "@/features/jobs/CrawlNotice";
import { useAuth } from "@/features/auth/AuthContext";
import { useQueryClient } from "@tanstack/react-query";
import { Tabs } from "@/shared/ui/kit";
import { DataPanel } from "./DataPanel";
import { Section } from "./Section";
import { AiPanel } from "@/features/ai/AiPanel";
import { deleteStoredCv, useStoredCv } from "@/features/fit/api";
import { Link } from "react-router-dom";
import { RrPanel } from "@/features/cv/RrPanel";
import { useTheme } from "@/shared/lib/theme";

export function ProfilePage() {
  const { user } = useAuth();
  const [cur, setCur] = useState(""); const [next, setNext] = useState(""); const [pmsg, setPmsg] = useState("");
  const { theme, setTheme } = useTheme(); const cvq = useStoredCv(); const qc = useQueryClient();
  return (<div className="stack settings"><PageHeader eyebrow="Your account" icon={<Icon name="profile" size={17} />} title="Settings" subtitle={<>{user!.email} · {user!.role}. Your field, places, titles and skills shape “My feed”, the match score and your alerts.</>} />
    <Tabs vertical tabs={[
      { value: "prefs", label: "Preferences", content: <PrefsForm /> },
      { value: "ai", label: "AI model & CV", content: (<div className="set-col">
        <Section title="Your CV for AI scoring" hint={cvq.data ? <>Stored encrypted, saved {new Date(cvq.data.updated_at).toLocaleDateString()}.</> : <>No CV saved yet. Import one in <Link to="/cv">CV Studio</Link> and press “Use for AI scoring”.</>}
          action={cvq.data ? <button type="button" className="btn ghost small" onClick={async () => { await deleteStoredCv(); qc.invalidateQueries({ queryKey: ["stored-cv"] }); }}>Delete stored CV</button> : undefined} />
        <div className="set-wrap"><AiPanel onSaved={() => qc.invalidateQueries({ queryKey: ["ai-settings"] })} /></div></div>) },
      { value: "integrations", label: "Integrations", content: (<div className="set-col">
        <Section title="Gmail" hint="Read job e-mails (applications, interviews, offers) and move your pipeline automatically. Read-only access." action={<Link className="btn ghost small" to="/inbox">Open Inbox settings</Link>} />
        <div className="card set-card"><RrPanel connectOnly /></div></div>) },
      { value: "display", label: "Display", content: (<div className="set-col">
        <Section title="Appearance" hint="“System” follows your device. The sidebar can be collapsed from its bottom button.">
          <div className="seg" role="group" aria-label="Theme">{(["system", "light", "dark"] as const).map((x) => <button key={x} className={theme === x ? "on" : ""} aria-pressed={theme === x} onClick={() => setTheme(x)}>{x[0].toUpperCase() + x.slice(1)}</button>)}</div></Section></div>) },
      { value: "account", label: "Account & data", content: (<div className="set-col">
        <Section title="Change password" hint="At least 8 characters.">
          <form className="set-form" onSubmit={async (e) => { e.preventDefault(); try { await api.post("/auth/password", { current_password: cur, new_password: next }); setPmsg("Password changed"); setCur(""); setNext(""); } catch (x) { setPmsg((x as Error).message); } }}>
            <input type="password" placeholder="Current password" aria-label="Current password" value={cur} onChange={(e) => setCur(e.target.value)} required autoComplete="current-password" />
            <input type="password" placeholder="New password (min 8)" aria-label="New password" minLength={8} value={next} onChange={(e) => setNext(e.target.value)} required autoComplete="new-password" />
            <button className="btn ghost">Change</button></form>
          {pmsg && <span className="muted small" role="status">{pmsg}</span>}</Section>
        <DataPanel /></div>) }]} />
  </div>);
}

/** The same questions as the setup dialog, all on one page. Only what you change is sent; the rest of the profile is kept. */
function PrefsForm() {
  const { user, saveProfile } = useAuth(); const [p, setP] = useState<Profile>(user!.profile ?? {}); const [msg, setMsg] = useState(""); const [busy, setBusy] = useState(false);
  const set = (patch: Partial<Profile>) => { setP((x) => ({ ...x, ...patch })); setMsg(""); };
  const save = async () => {
    setBusy(true);
    try { const u = await saveProfile({ sectors: p.sectors ?? [], countries: myCountries(p), regions: p.regions ?? [], work_modes: p.work_modes ?? [], cities: p.cities ?? [], remote_ok: p.remote_ok !== false, sponsor_needed: !!p.sponsor_needed, titles: p.titles ?? [], job_types: p.job_types ?? [], english_only: !!p.english_only, skills: p.skills ?? [], keywords: p.keywords ?? [] }); announceCrawl(u.crawl); setMsg("Saved. My feed and alerts use it now."); }
    catch (x) { setMsg((x as Error).message); } finally { setBusy(false); }
  };
  const cvn = user!.profile?.cv_skills?.length ?? 0;
  return (<div className="set-col">
    <Section title="Field" hint="Pick up to three. Your feed, match score and alerts follow these." action={<button type="button" className="btn ghost small" onClick={openSetup}>Run the setup again</button>}><SectorStep p={p} set={set} /></Section>
    <Section title="Where" hint="The places you want to work in."><PlaceStep p={p} set={set} /></Section>
    <Section title="What" hint="The roles and levels you are looking for."><RoleStep p={p} set={set} /></Section>
    <Section title="Skills" hint={cvn > 0 ? `Also using ${cvn} skills from your CV.` : "Used to rank jobs by how well they fit."}><SkillsStep p={p} set={set} withCv={false} /></Section>
    <div className="set-save"><span className="small muted" role="status">{msg || "Changes apply to your feed and alerts."}</span><button className="btn" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save preferences"}</button></div>
  </div>);
}
