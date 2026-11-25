import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { GUEST_DOMAIN, openTour, useDemo } from "./useDemo";

/** A slim, always-honest line above every page of the online demo. */
export function DemoBar() {
  const { demo, guestDays } = useDemo(); const { user, startDemo } = useAuth(); const nav = useNavigate(); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  if (!demo) return null;
  const guest = !!user?.email.endsWith(GUEST_DOMAIN);
  return (<div className="demobar" role="note">
    <span className="demobar-tag">Demo</span>
    <span className="demobar-text">Jobs are a saved snapshot, not live. The crawler runs only on your own computer.{guest && ` Your guest account is removed after about ${guestDays} days.`}</span>
    {err && <span className="err small" role="alert">{err}</span>}
    <span className="demobar-acts"><button onClick={openTour}>Feature tour</button>
      {!user && <button className="main" disabled={busy} onClick={async () => { setBusy(true); setErr(""); try { await startDemo(); nav("/"); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } }}>{busy ? "Opening…" : "Try as guest"}</button>}</span>
  </div>);
}
