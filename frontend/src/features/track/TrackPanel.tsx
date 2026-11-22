import { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/AuthContext";
import { ago, label } from "@/shared/lib/format";
import { useTaskActions, useTasks, useTrack, useTrackActions } from "./api";

const ICON: Record<string, string> = { stage: "→", note: "✎", interview: "📅", email: "✉", follow_up: "⏰", offer: "★" };
const dayInput = (iso?: string | null) => (iso ? iso.slice(0, 10) : "");
const fromDay = (d: string) => (d ? new Date(d + "T09:00:00").toISOString() : null);

/** Application tracking for one job: dates, contact, follow-up, notes and the full timeline. Only for jobs in the user's pipeline. */
export function TrackPanel({ jobId, part = "all" }: { jobId: number; part?: "all" | "notes" | "timeline" }) {
  const { user } = useAuth(); const q = useTrack(jobId, !!user); const act = useTrackActions(jobId);
  const t = q.data?.track; const [notes, setNotes] = useState(""); const [contact, setContact] = useState(""); const [offer, setOffer] = useState(""); const [fnote, setFnote] = useState("");
  const [kind, setKind] = useState("note"); const [title, setTitle] = useState(""); const [body, setBody] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { setNotes(t?.notes ?? ""); setContact(t?.contact ?? ""); setOffer(t?.offer_details ?? ""); setFnote(t?.follow_up_note ?? ""); }, [t?.notes, t?.contact, t?.offer_details, t?.follow_up_note, jobId]);
  if (!user || !t) return null;
  const run = async (p: Promise<unknown>) => { setErr(""); try { await p; } catch (e) { setErr((e as Error).message); } };
  const overdue = !!t.follow_up_at && new Date(t.follow_up_at) <= new Date();
  const N = part !== "timeline", T = part !== "notes";
  return (<div className="track">
    {N && <><h3>Tracking</h3>
    <div className="track-grid">
      <label>Applied on<input type="date" value={dayInput(t.applied_at)} onChange={(e) => run(act.patch.mutateAsync({ applied_at: fromDay(e.target.value) }))} /></label>
      <label>Follow up on<input type="date" className={overdue ? "due" : ""} value={dayInput(t.follow_up_at)} onChange={(e) => e.target.value ? run(act.patch.mutateAsync({ follow_up_at: fromDay(e.target.value) })) : run(act.patch.mutateAsync({ clear_follow_up: true }))} /></label>
      <label>Contact<input type="text" value={contact} placeholder="Recruiter or hiring manager" onChange={(e) => setContact(e.target.value)} onBlur={() => contact !== (t.contact ?? "") && run(act.patch.mutateAsync({ contact }))} /></label>
      <label>Reminder text<input type="text" value={fnote} placeholder="What to do then" onChange={(e) => setFnote(e.target.value)} onBlur={() => fnote !== (t.follow_up_note ?? "") && run(act.patch.mutateAsync({ follow_up_note: fnote }))} /></label>
      {(t.stage === "offer" || t.stage === "accepted") && <label style={{ gridColumn: "1 / -1" }}>Offer details<input type="text" value={offer} placeholder="Salary, leave, start date…" onChange={(e) => setOffer(e.target.value)} onBlur={() => offer !== (t.offer_details ?? "") && run(act.patch.mutateAsync({ offer_details: offer }))} /></label>}
    </div>
    <label>Notes<textarea rows={3} value={notes} placeholder="Prep notes, salary talk, questions to ask…" onChange={(e) => setNotes(e.target.value)} onBlur={() => notes !== (t.notes ?? "") && run(act.patch.mutateAsync({ notes }))} /></label>
    <Tasks jobId={jobId} /></>}
    {T && <>
    <form className="row" onSubmit={(e) => { e.preventDefault(); if (!title.trim()) return; run(act.addEvent.mutateAsync({ kind, title: title.trim(), body: body.trim() || undefined }).then(() => { setTitle(""); setBody(""); })); }}>
      <select value={kind} onChange={(e) => setKind(e.target.value)}><option value="note">Note</option><option value="interview">Interview</option><option value="follow_up">Follow-up sent</option><option value="offer">Offer</option></select>
      <input type="text" style={{ flex: 1, minWidth: 140 }} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Add to the timeline…" />
      <button className="btn ghost small" disabled={!title.trim()}>Add</button>
    </form>
    {err && <div className="small err">{err}</div>}
    <ol className="timeline">{(q.data?.events ?? []).map((e) => (
      <li key={e.id}><span className="tl-i">{ICON[e.kind] ?? "•"}</span>
        <div><div><b>{e.title}</b> <span className="small muted">{ago(e.at)}{e.meta?.source === "email" ? " · from e-mail" : ""}</span></div>{e.body && <div className="small muted">{e.body}</div>}</div>
        {e.kind !== "stage" && <button className="x" title="Remove" onClick={() => run(act.delEvent.mutateAsync(e.id))}>×</button>}</li>))}
      {!q.data?.events.length && <li className="small muted">No history yet. Change the stage or add a note.</li>}</ol>
    <div className="small muted">Stage: {label(t.stage)}</div></>}
  </div>);
}

function Tasks({ jobId }: { jobId: number }) {
  const q = useTasks(jobId); const act = useTaskActions(jobId); const [title, setTitle] = useState(""); const [due, setDue] = useState("");
  return (<div className="tasks stack" style={{ gap: 6 }}><div className="small muted">To-do for this job</div>
    {(q.data ?? []).map((t) => <label key={t.id} className="row task"><input type="checkbox" checked={t.done} onChange={() => act.toggle.mutate(t)} /><span style={{ textDecoration: t.done ? "line-through" : "none", flex: 1 }}>{t.title}</span>
      {t.due_at && <span className={`small ${!t.done && new Date(t.due_at) < new Date() ? "err" : "muted"}`}>{new Date(t.due_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>}
      <button type="button" className="x" title="Remove" onClick={() => act.remove.mutate(t.id)}>×</button></label>)}
    <form className="row" onSubmit={(e) => { e.preventDefault(); if (!title.trim()) return; act.add.mutate({ title: title.trim(), due_at: due ? new Date(due + "T09:00:00").toISOString() : undefined }, { onSuccess: () => { setTitle(""); setDue(""); } }); }}>
      <input type="text" style={{ flex: 1, minWidth: 140 }} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Send portfolio link" aria-label="New task" /><input type="date" value={due} onChange={(e) => setDue(e.target.value)} aria-label="Due date" />
      <button className="btn ghost small" disabled={!title.trim()}>Add task</button></form></div>);
}
