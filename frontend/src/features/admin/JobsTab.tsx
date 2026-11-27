import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { label } from "@/shared/lib/format";
import { ActionButton, Modal, ListFoot, useAdminList, download, num, useDebounced, useNotify } from "./ui";
import { PlaceFilters, type PlaceF } from "./PlaceFilters";
import { flag, modeLabel } from "@/shared/lib/geo";
import { BoardIcon, boardName } from "@/shared/ui/BoardIcon";

type Job = { id: number; title: string; url: string; location?: string | null; city?: string | null; country?: string | null; countries?: string[]; work_mode?: string; sector?: string; source?: string | null; status: string; domain?: string | null; job_type: string; posted_at?: string | null; first_seen: string; company: string; company_id: number; saved_by: number };
const DOMAINS = ["mobile", "frontend", "backend", "fullstack", "software", "data", "devops", "security", "qa", "embedded", "design", "product", "other"];

export function JobsTab({ isAdmin }: { isAdmin: boolean }) {
  const qc = useQueryClient(); const notify = useNotify();
  const [q, setQ] = useState(""); const [status, setStatus] = useState("open"); const [domain, setDomain] = useState(""); const [older, setOlder] = useState(""); const [sort, setSort] = useState("newest"); const [pf, setPf] = useState<PlaceF>({});
  const [sel, setSel] = useState<Set<number>>(new Set()); const [confirm, setConfirm] = useState<null | { action: string; all: boolean }>(null);
  const dq = useDebounced(q); const dcity = useDebounced(pf.city ?? "");
  const place = { country: pf.country, city: dcity || undefined, sector: pf.sector, work_mode: pf.work_mode, source: pf.source };
  const params = { q: dq, status, domain, older_than_days: older, sort, ...place };
  const list = useAdminList<Job>("jobs-admin", "/admin/jobs", params);
  const items = list.items; const total = list.total;
  const refresh = () => { setSel(new Set()); qc.invalidateQueries({ queryKey: ["jobs-admin"] }); qc.invalidateQueries({ queryKey: ["admin-policy"] }); qc.invalidateQueries({ queryKey: ["admin-stats"] }); };
  const reset = (fn: () => void) => { fn(); setSel(new Set()); };
  const all = items.length > 0 && items.every((j) => sel.has(j.id));
  const run = async (action: string, allMatching: boolean) => {
    const body = allMatching ? { action, all_matching: true, confirm: true, q: dq || undefined, status: status === "all" ? undefined : status, domain: domain || undefined, older_than_days: older ? +older : undefined, ...place } : { action, ids: [...sel] };
    const r = await api.post<{ changed: number }>("/admin/jobs/bulk", body);
    notify(`${num(r.changed)} job(s) ${action === "delete" ? "deleted" : action === "expire" ? "marked expired" : "re-opened"}.`, r.changed ? "ok" : "info"); setConfirm(null); refresh();
  };
  const btn = (action: string, text: string, danger = false) => <button className={`btn small ${danger ? "danger" : "ghost"}`} disabled={!sel.size} onClick={() => (action === "delete" ? setConfirm({ action, all: false }) : run(action, false))}>{text} ({sel.size})</button>;
  return (
    <div className="stack">
      <div className="toolbar">
        <input type="search" placeholder="Search title or company" value={q} onChange={(e) => reset(() => setQ(e.target.value))} />
        <select value={status} onChange={(e) => reset(() => setStatus(e.target.value))}><option value="open">Open</option><option value="expired">Expired</option><option value="all">All</option></select>
        <select value={domain} onChange={(e) => reset(() => setDomain(e.target.value))}><option value="">Any domain</option>{DOMAINS.map((d) => <option key={d} value={d}>{label(d)}</option>)}</select>
        <select value={older} onChange={(e) => reset(() => setOlder(e.target.value))}><option value="">Any age</option><option value="7">Older than 7 days</option><option value="30">Older than 30 days</option><option value="60">Older than 60 days</option><option value="90">Older than 90 days</option><option value="180">Older than 180 days</option></select>
        <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="company">Company</option><option value="title">Title</option></select>
        <ActionButton className="btn ghost small" run={async () => { await download("/admin/export/jobs.csv", "jobs.csv"); notify("Downloaded jobs.csv", "ok"); }}>⬇ CSV</ActionButton>
      </div>
      <PlaceFilters kind="jobs" value={pf} onChange={(v) => reset(() => setPf(v))} />
      <div className="toolbar">
        {btn("expire", "Mark expired")}{btn("reopen", "Re-open")}{isAdmin && btn("delete", "Delete", true)}
        {isAdmin && total > 0 && <button className="btn ghost small" onClick={() => setConfirm({ action: "delete", all: true })}>Delete all {num(total)} matching…</button>}
        <span className="muted small right">{sel.size ? `${sel.size} selected` : "Tick rows to act on them"}</span>
      </div>
      <div className="tablewrap"><table className="dtable">
        <thead><tr><th style={{ width: 30 }}><input type="checkbox" checked={all} onChange={() => setSel(all ? new Set() : new Set(items.map((j) => j.id)))} aria-label="Select all loaded rows" /></th><th>Title</th><th>Company</th><th>Domain</th><th>Type</th><th>Posted</th><th>Seen</th><th>Status</th></tr></thead>
        <tbody>{items.map((j) => <tr key={j.id}>
          <td><input type="checkbox" checked={sel.has(j.id)} onChange={() => setSel((s) => { const n = new Set(s); n.has(j.id) ? n.delete(j.id) : n.add(j.id); return n; })} /></td>
          <td className="clip" title={j.title}><span title={j.source?.startsWith("board:") ? `Found on ${boardName(j.source)}` : "From the employer's own site"}><BoardIcon board={j.source?.startsWith("board:") ? j.source : "site"} size={15} /></span> <a href={j.url} target="_blank" rel="noreferrer">{j.title}</a>{j.saved_by > 0 && <span className="badge" title="Saved in someone's pipeline" style={{ marginLeft: 6 }}>saved ×{j.saved_by}</span>}</td>
          <td className="clip">{j.company}<div className="muted small">{flag(j.country)} {j.city ?? j.country ?? ""}{(j.countries?.length ?? 0) > 1 ? ` +${j.countries!.length - 1}` : ""}{j.work_mode && j.work_mode !== "onsite" ? ` · ${modeLabel(j.work_mode)}` : ""}</div></td><td><span className="badge">{j.domain ?? "—"}</span></td><td className="small">{label(j.job_type)}</td>
          <td className="small muted">{j.posted_at ?? "Unknown date"}</td><td className="small muted">{new Date(j.first_seen).toLocaleDateString()}</td>
          <td><span className={`badge ${j.status === "open" ? "ok" : "warn"}`}>{j.status}</span></td></tr>)}
          {!items.length && <tr><td colSpan={8} className="empty">{list.isLoading ? "Loading…" : "No jobs match these filters."}</td></tr>}</tbody>
      </table></div>
      <ListFoot shown={items.length} total={total} more={list.more} loading={list.loadingMore} sentinel={list.sentinel} />
      {confirm && <Modal title={confirm.all ? `Delete all ${num(total)} matching jobs?` : `Delete ${sel.size} job(s)?`} onClose={() => setConfirm(null)}>
        <p>{confirm.all ? <>Every job matching the current filters will be removed — not only the {items.length} loaded so far.</> : <>The selected jobs will be removed.</>} Jobs saved in a pipeline disappear from it too. This cannot be undone.</p>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={() => setConfirm(null)}>Cancel</button><ActionButton className="btn danger" run={() => run("delete", confirm.all)}>Delete</ActionButton></div></Modal>}
    </div>
  );
}
