import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";

type Sess = { id: string; started: string; last_active: string; expires_at: string };

/** Your data: download everything, see signed-in devices, delete the account. */
export function DataPanel() {
  const { user, logout } = useAuth(); const qc = useQueryClient(); const [confirm, setConfirm] = useState(""); const [busy, setBusy] = useState(false);
  const sess = useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Sess[]>("/me/sessions") });
  const exportData = async () => {
    const d = await api.get<unknown>("/me/export"); const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" })); a.download = "career-tracker-export.json"; a.click(); toast.success("Export downloaded");
  };
  const end = async (id?: string) => { await api.del(id ? `/me/sessions/${id}` : "/me/sessions"); if (!id) { logout(); return; } qc.invalidateQueries({ queryKey: ["sessions"] }); toast.success("Session ended"); };
  const del = async () => { setBusy(true); try { await api.post("/me/account/delete", { confirm_email: confirm }); toast.success("Account deleted"); logout(); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); } };
  return (<div className="card stack"><h2>Your data</h2>
    <div className="row"><button className="btn ghost" onClick={exportData}>Download my data (JSON)</button><span className="small muted">Profile, CV, pipeline, timeline, tasks, searches, AI scores, assistant chats, e-mail events. Never passwords, tokens or API keys.</span></div>
    <h3>Signed-in devices</h3>
    <ul className="plain">{(sess.data ?? []).map((s) => <li key={s.id} className="row"><span className="small">Started {new Date(s.started).toLocaleString()} · last active {new Date(s.last_active).toLocaleString()}</span><button className="btn ghost small right" onClick={() => end(s.id)}>End</button></li>)}</ul>
    {!!sess.data?.length && <div><button className="btn ghost small" onClick={() => end()}>Sign out everywhere</button></div>}
    <h3>Delete account</h3>
    <div className="small muted">Removes your profile, CV, pipeline and everything above, permanently. Type <b>{user?.email}</b> to confirm. (If you use Firebase sign-in, the sign-in record itself is removed from the Firebase console.)</div>
    <div className="row"><input type="text" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="your e-mail" aria-label="Confirm e-mail" style={{ flex: 1 }} /><button className="btn danger" disabled={busy || confirm.trim().toLowerCase() !== user?.email.toLowerCase()} onClick={del}>Delete everything</button></div>
  </div>);
}
