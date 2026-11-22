import { Icon } from "@/shared/ui/Icon";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { label } from "@/shared/lib/format";
import { Drawer, Splitter, usePane } from "@/shared/ui/kit";
import { useShortcuts } from "@/shared/lib/useShortcuts";
import { AiPanel, type AiSettings, errText } from "@/features/ai/AiPanel";

type Account = { id: number; provider?: string; label: string; username: string; days_back: number; last_sync_at?: string | null; last_error?: string | null };
type Ev = { id: number; category: string; company?: string | null; role?: string | null; location?: string | null; event_date?: string | null; summary?: string | null; subject?: string | null; sender?: string | null;
  received_at?: string | null; confidence: number; classifier: string; status: string; company_known?: string | null; job?: { id: number; title: string } | null; suggested_stage?: string | null };
type Events = { items: Ev[]; counts: { category: Record<string, number>; status: Record<string, number> } };
type Prog = { phase?: string; scanned?: number; total?: number; found?: number; skipped?: number; duplicate?: number; ai_failed?: number; ai_error?: string };

const CATS = ["application_received", "interview_invite", "assessment", "offer", "rejection", "recruiter_outreach"];
const COLOR: Record<string, string> = { application_received: "#3b82f6", interview_invite: "#8b5cf6", assessment: "#f59e0b", offer: "#10b981", rejection: "#ef4444", recruiter_outreach: "#06b6d4" };
const hue = (t: string) => { let h = 0; for (const ch of t) h = (h * 31 + ch.charCodeAt(0)) % 360; return h; };
const when = (iso?: string | null) => { if (!iso) return "never"; const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000); return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };

export function InboxPage() {
  const events = useQuery({ queryKey: ["mail-events"], queryFn: () => api.get<Events>("/mail/events") });
  const ai = useQuery({ queryKey: ["ai-settings"], queryFn: () => api.get<AiSettings>("/ai/settings") });
  const [showAi, setShowAi] = useState(false);
  const c = events.data?.counts; const tracked = (c?.status.new ?? 0) + (c?.status.accepted ?? 0);
  const needAi = !!ai.data && !ai.data.provider;
  return (
    <div className="ifull">
      <div className="inbox-banner">
        <div><h1 className="ph-title"><span className="ph-icon" aria-hidden><Icon name="inbox" size={17} /></span>Inbox assistant</h1>
          <p>Your job-search mail, sorted for you. We read your Gmail <b>read-only</b> and pick out the replies that matter: interviews, tests, offers and, yes, the rejections too.</p></div>
        <div className="inbox-banner-n"><b>{c?.status.new ?? 0}</b><span>to review</span></div><div className="inbox-banner-n"><b>{tracked}</b><span>tracked</span></div>
      </div>
      <div className="itop"><Connection ai={ai.data} needAi={needAi} showAi={showAi} toggleAi={() => setShowAi(!showAi)} /></div>
      <Drawer open={showAi} onOpenChange={setShowAi} title="AI model for your e-mails" size={520}><AiPanel onSaved={() => setShowAi(false)} /></Drawer>
      <Review />
    </div>
  );
}

/* ------------------------------------------------------------------ Gmail connection + sync */
function Connection({ ai, needAi, showAi, toggleAi }: { ai?: AiSettings; needAi: boolean; showAi: boolean; toggleAi: () => void }) {
  const qc = useQueryClient();
  const accs = useQuery({ queryKey: ["mail-accounts"], queryFn: () => api.get<Account[]>("/mail/accounts") });
  const gm = useQuery({ queryKey: ["gmail-status"], queryFn: () => api.get<{ configured: boolean; redirect_uri: string }>("/mail/gmail/status"), staleTime: Infinity });
  const [msg, setMsg] = useState(""); const [prog, setProg] = useState<Prog | null>(null); const [state, setState] = useState<"idle" | "running" | "done" | "failed">("idle");
  const [days, setDays] = useState(60); const [consent, setConsent] = useState(false); const [auto, setAuto] = useState(false);
  const a = accs.data?.[0];
  const usesExternalAi = !!ai?.provider && ai.provider !== "ollama";
  const refresh = () => { qc.invalidateQueries({ queryKey: ["mail-accounts"] }); qc.invalidateQueries({ queryKey: ["mail-events"] }); };
  useEffect(() => {
    const q = new URLSearchParams(window.location.search), g = q.get("gmail"); if (!g) return;
    setMsg(g === "connected" ? "✓ Gmail connected. Press “Sync now” to read your recent e-mails." : g === "denied" ? "✗ Google sign-in was cancelled." : "✗ Gmail sign-in failed" + (q.get("reason") ? `: ${q.get("reason")}` : "."));
    window.history.replaceState({}, "", window.location.pathname); refresh();
  }, []);
  const connect = async () => { setMsg(""); try { const { url } = await api.post<{ url: string }>("/mail/gmail/start", {}); window.location.href = url; } catch (e) { setMsg("✗ " + errText(e)); } };
  const run = async () => {
    if (!a) return; setState("running"); setMsg(""); setProg({ phase: "starting" });
    try {
      const { task_id } = await api.post<{ task_id: number }>("/mail/sync", { account_id: a.id, days, consent, auto_apply: auto });
      for (let i = 0; i < 1200; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        const t = await api.get<{ status: string; progress: Prog; error?: string }>(`/mail/sync/${task_id}`);
        setProg(t.progress ?? {}); if (i % 3 === 0) qc.invalidateQueries({ queryKey: ["mail-events"] });
        if (t.status === "failed") { setState("failed"); setMsg("✗ " + (t.error ?? "Sync failed")); break; }
        if (t.status === "done") { setState("done"); break; }
      }
    } catch (e) { setState("failed"); setMsg("✗ " + errText(e)); }
    refresh();
  };
  const disconnect = async () => { if (window.confirm("Disconnect Gmail? The saved Google access is deleted. Events already extracted stay until you delete them.")) { await api.del(`/mail/accounts/${a!.id}`); setState("idle"); setProg(null); refresh(); } };
  const pct = prog?.total ? Math.min(100, Math.round(((prog.scanned ?? 0) / prog.total) * 100)) : 0;
  if (!a) return (
    <div className="card inbox-hero fancy">
      <div style={{ flex: 1, minWidth: 260 }}>
        <h2 style={{ margin: "0 0 6px" }}>Connect your Gmail</h2>
        <ul className="small muted" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
          <li>You sign in on <b>Google's own page</b>. No password is shared.</li>
          <li><b>Read-only</b>: nothing is deleted, moved or marked as read.</li>
          <li>Only extracted facts (company, role, status) are kept, <b>never the e-mail text</b>.</li>
          <li>Revoke any time at myaccount.google.com/permissions.</li>
        </ul>
        {msg && <div className={`small ${msg.startsWith("✗") ? "err" : "ok"}`} style={{ marginTop: 8 }}>{msg}</div>}
      </div>
      <div className="stack" style={{ alignItems: "flex-start", gap: 8 }}>
        <div className="stack" style={{ gap: 8, alignItems: "stretch" }}><button className="btn" disabled={!gm.data?.configured} onClick={connect}>Connect Gmail</button><button className="btn ghost small" onClick={toggleAi}>{needAi ? "Choose AI model" : `AI: ${ai?.provider}`}</button></div>
        {gm.data && !gm.data.configured && <span className="small muted" style={{ maxWidth: 320 }}>Not set up on this server yet. Add <code>CAREERS_GOOGLE_CLIENT_SECRET</code> and the redirect URI <code>{gm.data.redirect_uri}</code>, see docs/GMAIL_OAUTH.md.</span>}
      </div>
    </div>);
  return (
    <div className="card stack fancy">
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <span className="avatar" style={{ flex: "none" }}>{a.username[0]?.toUpperCase()}</span>
        <div style={{ flex: 1, minWidth: 200 }}><b>{a.username}</b> <span className="chip ok" style={{ margin: 0 }}>● connected</span>
          <div className="small muted">{a.last_error ? <span className="err">{a.last_error}</span> : `last read ${when(a.last_sync_at)}`}</div></div>
        <select value={days} onChange={(e) => setDays(+e.target.value)} aria-label="How far back to read" disabled={state === "running"}>{[[14, "Last 2 weeks"], [30, "Last 30 days"], [60, "Last 60 days"], [90, "Last 90 days"], [180, "Last 6 months"], [365, "Last year"]].map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
        <button className="btn" disabled={state === "running" || needAi || (usesExternalAi && !consent)} onClick={run}>{state === "running" ? "Reading…" : "Sync now"}</button>
        <button className="btn ghost small" onClick={disconnect}>Disconnect</button>
      </div>
      <label className="small"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> Move my pipeline automatically when the AI is very confident (90%+) and the job is known. You can undo each one.</label>
      <SyncHistory />
      {usesExternalAi && <label className="small"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> I agree that the text of my job e-mails is sent to <b>{ai?.provider}</b> to be analysed.</label>}
      <div className="small muted">{needAi ? <span className="err">Choose the AI model that will read your e-mails before syncing.</span> : <>AI model: <b>{ai?.provider}{ai?.model ? ` · ${ai.model}` : ""}</b></>} <button className="btn ghost small" onClick={toggleAi}>{needAi ? "Choose" : showAi ? "Close" : "Change"}</button></div>
      {state === "running" && prog && <div className="stack" style={{ gap: 4 }}>
        <div className="progress"><div style={{ width: `${prog.phase === "analysing" ? pct : 6}%` }} /></div>
        <div className="small muted">{prog.phase === "analysing" ? `Analysing ${prog.scanned ?? 0} / ${prog.total ?? 0} e-mails · ${prog.found ?? 0} job e-mails found` : "Reading your mailbox from Gmail… this can take a minute or two."}</div></div>}
      {state === "done" && prog && <div className="small">
        <span className="ok">✓ Read {prog.scanned ?? 0} e-mails</span> · <b>{prog.found ?? 0}</b> job e-mails added to Review{prog.duplicate ? ` · ${prog.duplicate} already known` : ""} · {prog.skipped ?? 0} not job related.
        {!!prog.ai_failed && <div className="err">The AI model failed on {prog.ai_failed} e-mails{prog.ai_error ? `: ${prog.ai_error}` : ""}. Press “Sync now” again to retry them.</div>}
        {!prog.found && !prog.ai_failed && !prog.duplicate && <div className="muted">Nothing job-related in this period. Try a longer period.</div>}
      </div>}
      {msg && <div className={`small ${msg.startsWith("✗") ? "err" : "ok"}`}>{msg}</div>}
    </div>);
}

/* ------------------------------------------------------------------ Review */
function Review() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("new"); const [cat, setCat] = useState(""); const [q, setQ] = useState(""); const [note, setNote] = useState("");
  const all = useQuery({ queryKey: ["mail-events"], queryFn: () => api.get<Events>("/mail/events") });
  const list = useQuery({ queryKey: ["mail-events", status, cat, q], queryFn: () => api.get<Events>("/mail/events", { status, category: cat, q }) });
  const act = async (id: number, a: "accept" | "dismiss") => {
    const r = await api.post<{ stage?: string | null }>(`/mail/events/${id}/${a}`); if (a === "accept") setNote(r.stage ? `Moved your pipeline job to “${label(r.stage)}”.` : "Kept. No pipeline job was linked, so nothing moved."); qc.invalidateQueries({ queryKey: ["mail-events"] });
  };
  const edit = async (id: number, body: object) => { await api.patch(`/mail/events/${id}`, body); qc.invalidateQueries({ queryKey: ["mail-events"] }); };
  const bulk = async (ids: number[], action: string) => { await api.post("/mail/events/bulk", { ids, action }); qc.invalidateQueries({ queryKey: ["mail-events"] }); };
  const counts = all.data?.counts; const items = list.data?.items ?? [];
  const pane = usePane("inbox-list", 420, 280, 720); const [sel, setSel] = useState<number | null>(null); const cur = items.find((e) => e.id === sel) ?? items[0];
  const move = (d: number) => { if (!items.length) return; const i = Math.max(0, Math.min(items.length - 1, items.findIndex((e) => e.id === cur?.id) + d)); setSel(items[i].id); requestAnimationFrame(() => document.querySelector(".irow1.sel")?.scrollIntoView({ block: "nearest" })); };
  useShortcuts({ j: () => move(1), ArrowDown: () => move(1), k: () => move(-1), ArrowUp: () => move(-1),
    a: () => { if (cur && cur.status === "new") act(cur.id, "accept"); }, d: () => { if (cur && cur.status === "new") act(cur.id, "dismiss"); } });
  const sure = items.filter((e) => e.confidence >= 0.75 && e.status === "new").map((e) => e.id);
  return (
    <div className="stack ireview">
      <div className="inbox-bar">
        <div className="seg">{([["new", "To review", counts?.status.new ?? 0], ["auto", "Auto-applied", counts?.status.auto ?? 0], ["accepted", "Kept", counts?.status.accepted ?? 0], ["dismissed", "Dismissed", counts?.status.dismissed ?? 0], ["", "All", 0]] as const).map(([k, t, v]) =>
          <button key={k} className={status === k ? "on" : ""} onClick={() => setStatus(k)}>{t}{k ? <i>{v}</i> : null}</button>)}</div>
        <select value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Filter by type"><option value="">All types</option>{CATS.map((c) => <option key={c} value={c}>{label(c)}{counts?.category[c] ? ` (${counts.category[c]})` : ""}</option>)}</select>
        <div className="searchwrap"><input type="search" placeholder="Search company, role or subject" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        {!!sure.length && <button className="btn small" onClick={() => bulk(sure, "accept")}>Accept {sure.length} confident</button>}
        {!!items.length && <button className="btn ghost small" onClick={async () => { if (window.confirm("Delete everything extracted from your e-mails?")) { await api.del("/mail/events"); qc.invalidateQueries({ queryKey: ["mail-events"] }); } }}>Delete all</button>}
      </div>
      {note && <div className="small ok">{note}</div>}
      <div className="isplit" style={{ "--wl": `${pane.width}px` } as React.CSSProperties}>
      <div className="ilist">
        {list.isLoading && [0, 1, 2, 3, 4].map((i) => <div key={i} className="skel" style={{ height: 38, marginBottom: 6 }} />)}
        {!list.isLoading && !items.length && <div className="card empty">{counts && Object.keys(counts.status).length ? "Nothing here with these filters." : "It's quiet in here. Press “Sync now” and we'll look through your Gmail."}</div>}
        {items.map((e) => (
          <button key={e.id} className={"irow1" + (cur?.id === e.id ? " sel" : "")} style={{ ["--c" as string]: COLOR[e.category] ?? "var(--brand)", opacity: e.status === "dismissed" ? 0.55 : 1 }} onClick={() => setSel(e.id)}>
            <span className="idot" /><b className="ico">{e.company ?? "Unknown company"}</b><span className="irole">{e.role ?? e.subject}</span>
            <span className="pill">{label(e.category)}</span><span className="meta">{e.received_at ? new Date(e.received_at).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : ""}</span></button>))}
      </div>
      <Splitter props={pane.props} label="Resize e-mail list" />
      <div className="card idetail">{!cur ? <div className="muted small">Pick an e-mail on the left to see what was found and what will happen.</div> : (() => { const e = cur; return (<div className="inbox-ev" style={{ ["--c" as string]: COLOR[e.category] ?? "var(--brand)" }}>
          <div className="logo" style={{ background: `hsl(${hue(e.company ?? e.sender ?? "?")} 70% 45%)` }}>{(e.company ?? e.sender ?? "?").trim()[0]?.toUpperCase()}</div>
          <div className="body">
            <div className="evtop">
              <b>{e.company ?? "Unknown company"}</b>{e.role && <span className="role">{e.role}</span>}
              <span className="pill">{label(e.category)}</span>
              <span className="meta">{e.received_at ? new Date(e.received_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : ""}</span>
            </div>
            {e.summary && <div className="sum">{e.summary}</div>}
            <div className="sub">{e.subject}{e.event_date ? ` · ${e.event_date}` : ""}</div>
            <div className="link">{e.job ? <>Linked to your pipeline job <b>{e.job.title}</b>{e.suggested_stage && <> → will move to <b>{label(e.suggested_stage)}</b></>}</> : <span className="muted">{e.company_known ? `“${e.company_known}” is in the tracker, but none of your pipeline jobs matches.` : "Not linked to a job."}</span>}</div>
            <div className="foot">
              <span className="conf" title={`${Math.round(e.confidence * 100)}% confident · ${e.classifier}`}><i style={{ width: `${Math.round(e.confidence * 100)}%` }} /></span><span className="muted small">{Math.round(e.confidence * 100)}% · {e.classifier}</span>
              {e.status === "auto" && <span className="acts"><span className="chip ok">Applied automatically</span><button className="btn ghost small" onClick={async () => { const r = await api.post<{ stage?: string | null }>(`/mail/events/${e.id}/undo`); setNote(r.stage ? `Undone. The job is back in “${label(r.stage)}”.` : "Undone."); qc.invalidateQueries({ queryKey: ["mail-events"] }); qc.invalidateQueries({ queryKey: ["pipeline"] }); }}>Undo</button></span>}
              {e.status === "new" && <span className="acts">
                <select value={e.category} onChange={(x) => edit(e.id, { category: x.target.value })} aria-label="Change category">{CATS.map((c) => <option key={c} value={c}>{label(c)}</option>)}</select>
                <button className="btn ghost small" onClick={() => act(e.id, "dismiss")}>Dismiss</button>
                <button className="btn small" onClick={() => act(e.id, "accept")}>{e.job ? "Accept & update pipeline" : "Keep"}</button>
              </span>}
            </div>
          </div>
        </div>); })()}</div>
      </div>
    </div>
  );
}


type Run = { id: number; status: string; at: string; error?: string | null; stats: Record<string, number> };
/** The last few mailbox syncs, so a failed or empty run is never a mystery. */
function SyncHistory() {
  const q = useQuery({ queryKey: ["mail-history"], queryFn: () => api.get<Run[]>("/mail/sync-history") }); const [open, setOpen] = useState(false);
  if (!q.data?.length) return null;
  return (<div className="small"><button className="btn ghost small" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"} sync history</button>
    {open && <table className="table"><thead><tr><th>When</th><th>Status</th><th>Read</th><th>Found</th><th>Auto</th><th>AI failed</th></tr></thead><tbody>{q.data.map((r) => <tr key={r.id}><td>{new Date(r.at).toLocaleString()}</td><td className={r.status === "failed" ? "err" : ""} title={r.error ?? ""}>{r.status}</td><td>{r.stats.scanned ?? "–"}</td><td>{r.stats.found ?? "–"}</td><td>{r.stats.auto_applied ?? 0}</td><td>{r.stats.ai_failed ?? 0}</td></tr>)}</tbody></table>}</div>);
}
