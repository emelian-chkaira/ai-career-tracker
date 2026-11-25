import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/shared/api/client";
import { useAuth } from "@/features/auth/AuthContext";
import { Section } from "./Section";

type Sess = { id: string; started: string; last_active: string; expires_at: string };

/** Your data: download everything, see signed-in devices, delete the account. */
export function DataPanel() {
  const { user, logout } = useAuth(); const qc = useQueryClient(); const [confirm, setConfirm] = useState(""); const [busy, setBusy] = useState(false); const [all, setAll] = useState(false);
  const sess = useQuery({ queryKey: ["sessions"], queryFn: () => api.get<Sess[]>("/me/sessions") });
  const exportData = async () => {
    const d = await api.get<unknown>("/me/export"); const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" })); a.download = "career-tracker-export.json"; a.click(); toast.success("Export downloaded");
  };
  const end = async (id?: string) => { await api.del(id ? `/me/sessions/${id}` : "/me/sessions"); if (!id) { logout(); return; } qc.invalidateQueries({ queryKey: ["sessions"] }); toast.success("Session ended"); };
  const del = async () => { setBusy(true); try { await api.post("/me/account/delete", { confirm_email: confirm }); toast.success("Account deleted"); logout(); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); } };
  return (<>
    <Section title="Your data" hint="Profile, CV, pipeline, timeline, tasks, searches, AI scores, assistant chats and e-mail events. Never passwords, tokens or API keys.">
      <div><button className="btn ghost" onClick={exportData}>Download my data (JSON)</button></div></Section>
    <Section title="Signed-in devices" action={sess.data?.length ? <button className="btn ghost small" onClick={() => end()}>Sign out everywhere</button> : undefined}>
      <ul className="plain">{(sess.data ?? []).slice(0, all ? undefined : 5).map((s) => <li key={s.id} className="sess"><span className="small">Started {new Date(s.started).toLocaleString()} · last active {new Date(s.last_active).toLocaleString()}</span><button className="btn ghost small" onClick={() => end(s.id)}>End</button></li>)}</ul>
      {(sess.data?.length ?? 0) > 5 && <div><button className="btn ghost small" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show all ${sess.data!.length}`}</button></div>}</Section>
    <Section title="Delete account" tone="danger" hint={<>Removes your profile, CV, pipeline and everything above, permanently. Type <b>{user?.email}</b> to confirm. (If you use Firebase sign-in, the sign-in record itself is removed from the Firebase console.)</>}>
      <div className="row delrow"><input type="text" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="your e-mail" aria-label="Confirm e-mail" style={{ flex: 1 }} /><button className="btn danger" disabled={busy || confirm.trim().toLowerCase() !== user?.email.toLowerCase()} onClick={del}>Delete everything</button></div></Section>
  </>);
}
