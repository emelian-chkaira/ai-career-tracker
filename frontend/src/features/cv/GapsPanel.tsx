import { useState } from "react";
import { api } from "@/shared/api/client";

type Block = { title?: string; bullets?: string[]; [k: string]: any };
type Cv = { summary?: string; skills?: string[]; experience?: Block[]; [k: string]: any };
interface Proposal { id: string; kind: "skill" | "experience" | "summary"; section: string; term: string; text: string; why: string; index?: number; role?: string }
interface Result { target: string; label: string; covered: string[]; proposals: Proposal[]; tips: { id: string; text: string }[] }
const TARGETS: [string, string][] = [["mobile", "Mobile / Flutter"], ["software", "Software engineer"], ["internship", "Internship"]];

/** Missing keywords and missing experience for a target role, as pre-filled editable proposals. Nothing changes until you accept it. */
export function GapsPanel({ cv, jobId, edit }: { cv: Cv; jobId: string; edit(p: Record<string, unknown>): void }) {
  const [target, setTarget] = useState("mobile"); const [useJob, setUseJob] = useState(false);
  const [res, setRes] = useState<Result | null>(null); const [text, setText] = useState<Record<string, string>>({}); const [done, setDone] = useState<Record<string, "yes" | "no">>({});
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const find = async () => {
    setBusy(true); setErr("");
    try { const r = await api.post<Result>("/cv/gaps", { cv, target, job_id: useJob && jobId ? +jobId : null }); setRes(r); setText(Object.fromEntries(r.proposals.map((p) => [p.id, p.text]))); setDone({}); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  /** Applies the accepted proposals to a working copy and sends ONE patch, so several accepts never overwrite each other. */
  const acceptSome = (ps: Proposal[]) => {
    let skills = [...(cv.skills ?? [])], summary = cv.summary ?? "", exp = [...(cv.experience ?? [])]; let touchedExp = false, touchedSummary = false;
    for (const p of ps) {
      const v = (text[p.id] ?? "").trim(); if (!v) continue;
      if (p.kind === "skill") { if (!skills.some((s) => s.toLowerCase() === v.toLowerCase())) skills.push(v); }
      else if (p.kind === "summary") { summary = [summary, v].filter(Boolean).join(" "); touchedSummary = true; }
      else { const i = p.index ?? -1; touchedExp = true;
        if (i < 0 || !exp[i]) exp.unshift({ heading: "Experience", title: "Role", place: "Company", date: "", desc: "", bullets: [v] }); else exp[i] = { ...exp[i], bullets: [...(exp[i].bullets ?? []), v] }; }
    }
    const patch: Record<string, unknown> = {};
    const added = skills.slice((cv.skills ?? []).length);
    if (added.length) {
      patch.skills = skills; const groups = (cv.skill_groups as { label: string; items: string[] }[] | undefined) ?? [];
      if (groups.length) { const g = groups.map((x) => ({ ...x, items: [...x.items] })); const o = g.find((x) => x.label === "Other"); if (o) o.items.push(...added); else g.push({ label: "Other", items: added }); patch.skill_groups = g; }
    }
    if (touchedSummary) patch.summary = summary;
    if (touchedExp) { patch.experience = exp; patch.order = [...new Set([...(cv.order ?? []), "experience"])]; }
    if (Object.keys(patch).length) edit(patch);
    setDone((d) => ({ ...d, ...Object.fromEntries(ps.map((p) => [p.id, "yes" as const])) }));
  };
  const accept = (p: Proposal) => acceptSome([p]);
  const open = res?.proposals.filter((p) => !done[p.id]) ?? [];
  return (<div className="stack"><h2 style={{ margin: 0 }}>Missing keywords & experience</h2>
    <div className="small muted">Finds what recruiters and applicant-tracking systems look for in a target role and your CV does not say. Each suggestion is pre-filled so you can edit it, then accept or skip it.</div>
    <div className="row"><select value={target} onChange={(e) => setTarget(e.target.value)} aria-label="Target role" disabled={useJob}>{TARGETS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      <label className="small row" style={{ gap: 6 }}><input type="checkbox" checked={useJob} disabled={!jobId} onChange={(e) => setUseJob(e.target.checked)} />Use job #{jobId || "…"} instead</label>
      <button className="btn" onClick={find} disabled={busy}>{busy ? "Checking…" : "Find gaps"}</button></div>
    {err && <div className="small err">{err}</div>}
    {res && <>
      <div className="notice small"><b>Accept only what is true.</b> These are common expectations for {res.label}, not facts about you. Once accepted they become part of your CV, so a recruiter may ask about them.</div>
      {res.covered.length > 0 && <div className="small"><span className="muted">Already covered: </span>{res.covered.map((c) => <span key={c} className="chip ok">{c}</span>)}</div>}
      {!open.length && <div className="card empty small">{res.proposals.length ? "All suggestions reviewed." : "Nothing missing for this target."}</div>}
      {open.length > 1 && <div className="row"><button className="btn small" onClick={() => acceptSome(open)}>Accept all {open.length}</button><span className="small muted">Review the wording first.</span></div>}
      {open.map((p) => <div key={p.id} className="card stack" style={{ padding: 12, boxShadow: "none", gap: 8 }}>
        <div className="row small"><span className="chip plain" style={{ margin: 0 }}>{p.kind === "skill" ? "Skill" : p.kind === "summary" ? "Summary" : `Bullet${p.role ? ` · ${p.role}` : ""}`}</span><b>{p.term}</b></div>
        <div className="small muted">{p.why}</div>
        {p.kind === "skill" ? <input type="text" value={text[p.id] ?? ""} onChange={(e) => setText({ ...text, [p.id]: e.target.value })} aria-label={`Edit ${p.term}`} />
          : <textarea rows={2} value={text[p.id] ?? ""} onChange={(e) => setText({ ...text, [p.id]: e.target.value })} aria-label={`Edit ${p.term}`} />}
        <div className="row"><button className="btn small" onClick={() => accept(p)}>Accept</button><button className="btn ghost small" onClick={() => setDone({ ...done, [p.id]: "no" })}>Skip</button></div></div>)}
      {Object.values(done).includes("yes") && <div className="small okc">Added to your CV. The preview updates, and tailoring may now use these facts.</div>}
      {res.tips.length > 0 && <div className="stack" style={{ gap: 4 }}><b className="small">Also worth fixing</b>{res.tips.map((t) => <div key={t.id} className="small muted">• {t.text}</div>)}</div>}
    </>}
  </div>);
}
