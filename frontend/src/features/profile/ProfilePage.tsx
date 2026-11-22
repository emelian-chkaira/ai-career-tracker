import { useState } from "react";
import { api } from "@/shared/api/client";
import { myCountries, openSetup, PlaceStep, RoleStep, SectorStep, SkillsStep } from "@/features/onboarding/SetupWizard";
import type { Profile } from "@/shared/api/types";
import { announceCrawl } from "@/features/jobs/CrawlNotice";
import { useAuth } from "@/features/auth/AuthContext";
import { useQueryClient } from "@tanstack/react-query";
import { Tabs } from "@/shared/ui/kit";
import { DataPanel } from "./DataPanel";
import { AiPanel } from "@/features/ai/AiPanel";
import { deleteStoredCv, useStoredCv } from "@/features/fit/api";
import { Link } from "react-router-dom";
import { RrPanel } from "@/features/cv/RrPanel";
import { useTheme } from "@/shared/lib/theme";

export function ProfilePage() {
  const { user, saveProfile } = useAuth(); const p = user!.profile;
  const [cur, setCur] = useState(""); const [next, setNext] = useState(""); const [pmsg, setPmsg] = useState("");
  const { theme, setTheme } = useTheme(); const cvq = useStoredCv(); const qc = useQueryClient();
  return (<div className="stack"><div><h1>Settings</h1><div className="muted">{user!.email} · {user!.role}. Your field, places, titles and skills shape “My feed”, the match score and your alerts.</div></div>
    <Tabs vertical tabs={[
      { value: "prefs", label: "Preferences", content: <PrefsForm /> },
      { value: "ai", label: "AI model & CV", content: (<div className="stack">
    <div className="card stack"><h2>AI scoring</h2>
      <div className="small muted">{cvq.data ? <>Your CV is stored encrypted for AI scoring (saved {new Date(cvq.data.updated_at).toLocaleDateString()}). </> : <>No CV saved yet. Import one in <Link to="/cv">CV Studio</Link> and press “Use for AI scoring”. </>}
        {cvq.data && <button type="button" className="btn ghost small" onClick={async () => { await deleteStoredCv(); qc.invalidateQueries({ queryKey: ["stored-cv"] }); }}>Delete stored CV</button>}</div>
      <AiPanel onSaved={() => qc.invalidateQueries({ queryKey: ["ai-settings"] })} /></div>
</div>) },
      { value: "integrations", label: "Integrations", content: (<div className="sgrid2">
        <div className="card stack"><h2>Gmail</h2><div className="small muted">Read job e-mails (applications, interviews, offers) and move your pipeline automatically. Read-only access.</div><div><Link className="btn ghost" to="/inbox">Open Inbox settings</Link></div></div>
        <div className="card"><RrPanel connectOnly /></div></div>) },
      { value: "display", label: "Display", content: (<div className="card stack"><h2>Appearance</h2><div className="seg" role="group" aria-label="Theme">{(["system", "light", "dark"] as const).map((t) => <button key={t} className={theme === t ? "on" : ""} aria-pressed={theme === t} onClick={() => setTheme(t)}>{t[0].toUpperCase() + t.slice(1)}</button>)}</div>
        <div className="small muted">“System” follows your device. The sidebar can be collapsed from its bottom button.</div></div>) },
      { value: "account", label: "Account & data", content: (<div className="sgrid2">
    <form className="card stack" onSubmit={async (e) => { e.preventDefault(); try { await api.post("/auth/password", { current_password: cur, new_password: next }); setPmsg("Password changed"); setCur(""); setNext(""); } catch (x) { setPmsg((x as Error).message); } }}>
      <h2>Change password</h2><input type="password" placeholder="Current password" value={cur} onChange={(e) => setCur(e.target.value)} required autoComplete="current-password" />
      <input type="password" placeholder="New password (min 8)" minLength={8} value={next} onChange={(e) => setNext(e.target.value)} required autoComplete="new-password" />
      <div className="row"><button className="btn ghost">Change</button><span className="muted small">{pmsg}</span></div></form>
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
  return (<div className="stack">
    <div className="card stack"><div className="row"><h2 style={{ margin: 0 }}>Field</h2><button type="button" className="btn ghost small right" onClick={openSetup}>Run the setup again</button></div><SectorStep p={p} set={set} /></div>
    <div className="sgrid2"><div className="card stack"><h2>Where</h2><PlaceStep p={p} set={set} /></div><div className="card stack"><h2>What</h2><RoleStep p={p} set={set} /></div></div>
    <div className="card stack"><h2>Skills</h2>{cvn > 0 && <div className="small muted">Also using {cvn} skills from your CV.</div>}<SkillsStep p={p} set={set} withCv={false} /></div>
    <div className="row prefs-save"><button className="btn" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save preferences"}</button><span className="small muted" role="status">{msg}</span></div>
  </div>);
}
