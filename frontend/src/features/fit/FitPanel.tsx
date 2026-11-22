import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { isExternalAi, useAiSettings } from "@/features/ai/AiPanel";
import type { AiFit } from "@/shared/api/types";
import { ago } from "@/shared/lib/format";
import { getConsent, scoreJob, setConsentStored, useRefreshJobs, useStoredCv } from "./api";

export const VERDICT: Record<AiFit["verdict"], string> = { strong: "Strong match", good: "Good match", stretch: "A stretch", weak: "Weak match" };
export const tone = (v: AiFit["verdict"]) => (v === "strong" || v === "good" ? "ok" : v === "stretch" ? "warn" : "bad");

export function FitBadge({ ai }: { ai?: AiFit | null }) {
  return ai ? <span className={`chip ${tone(ai.verdict)}`} title={ai.reason}>AI {ai.score} · {VERDICT[ai.verdict]}</span> : null;
}

/** AI assessment of this posting against the saved CV: score, evidence, gaps and deal-breakers. */
export function FitPanel({ jobId, ai }: { jobId: number; ai?: AiFit | null }) {
  const { user } = useAuth(); const cv = useStoredCv(!!user); const settings = useAiSettings(); const refresh = useRefreshJobs();
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [consent, setConsent] = useState(getConsent());
  if (!user) return <div className="fit"><h3>AI fit</h3><div className="small muted"><Link to="/login">Sign in</Link> to see how well this role matches your CV.</div></div>;
  const needAi = !!settings.data && !settings.data.provider; const external = isExternalAi(settings.data); const noCv = cv.data === null;
  const run = async (force: boolean) => {
    setBusy(true); setErr("");
    try { await scoreJob(jobId, consent, force); refresh(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  return (<div className="fit">
    <h3>AI fit</h3>
    {ai ? <>
      <div className="fit-head"><div className={`fit-score ${tone(ai.verdict)}`}><b>{ai.score}</b><span>/100</span></div>
        <div><div className="fit-verdict">{VERDICT[ai.verdict]}</div><div className="small">{ai.reason}</div></div></div>
      {!!ai.flags.length && <div className="fit-flags">{ai.flags.map((f) => <span key={f} className="chip warn">⚠ {f}</span>)}</div>}
      <div className="fit-cols">
        {!!ai.strengths.length && <div><div className="fit-h">Why it fits</div><ul>{ai.strengths.map((x) => <li key={x}>{x}</li>)}</ul></div>}
        {!!ai.gaps.length && <div><div className="fit-h">Not shown in your CV</div><ul>{ai.gaps.map((x) => <li key={x}>{x}</li>)}</ul></div>}
      </div>
      {ai.summary && <div className="small muted">In this role: {ai.summary}</div>}
      <div className="row small muted"><span>Scored by {ai.model} {ago(ai.at)}</span>
        <button className="btn ghost small right" disabled={busy || (external && !consent)} onClick={() => run(true)}>{busy ? "Scoring…" : "Score again"}</button></div>
    </> : <>
      <div className="small muted">How well does this role match your CV? An AI model reads the posting and your CV and tells you why.</div>
      {noCv && <div className="small">First <Link to="/cv">save your CV for AI scoring</Link> (CV Studio).</div>}
      {needAi && <div className="small">Then <Link to="/profile">choose an AI model</Link> in your profile.</div>}
      {external && !noCv && <label className="small"><input type="checkbox" checked={consent} onChange={(e) => { setConsent(e.target.checked); setConsentStored(e.target.checked); }} /> I agree that my CV and this posting are sent to <b>{settings.data?.provider}</b>.</label>}
      <div className="row"><button className="btn" disabled={busy || noCv || needAi || (external && !consent)} onClick={() => run(false)}>{busy ? "Reading the posting…" : "Score with AI"}</button></div>
    </>}
    {err && <div className="small err">{err}</div>}
  </div>);
}
