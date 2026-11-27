import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { api } from "@/shared/api/client";
import { Modal } from "@/shared/ui/kit";

const SEEN = "guide:seen";
const seen = () => { try { return localStorage.getItem(SEEN) === "1"; } catch { return false; } };
const remember = () => { try { localStorage.setItem(SEEN, "1"); } catch { /* private mode: it shows again, which is fine */ } };

export const GUIDE_STEPS = [
  { title: "Create your account", text: "The first account on this installation becomes the administrator. Your data stays on the machine that runs the app." },
  { title: "Choose what to look for", text: "A short setup opens after you register: your field, countries or remote, job titles and skills." },
  { title: "Keep jobs up to date", text: "The worker reads employers’ career pages. ./setup.sh starts it for you; otherwise run ./run.sh worker in backend/. Control it on the Crawler page." },
  { title: "Optional: AI scoring and CV help", text: "In Settings, pick a local Ollama model or paste your own API key. Your CV is only sent to an outside provider after you agree." },
  { title: "Optional: Google sign-in and Gmail", text: "Both need your own free Google client. Put its ID and secret in .env and restart. Steps: docs/GMAIL_OAUTH.md." },
];

/** Opens by itself on a fresh installation (no account exists yet), once per browser. */
export function FirstRunGuide() {
  const { user, ready } = useAuth(); const go = useNavigate(); const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: () => api.get<{ google_client_id: string | null; first_run?: boolean }>("/auth/config"), staleTime: Infinity, enabled: ready && !user });
  const fresh = ready && !user && cfg.data?.first_run === true;
  useEffect(() => { if (fresh && !seen()) setOpen(true); }, [fresh]);
  const close = () => { remember(); setOpen(false); };
  if (!open || user) return null;
  return (
    <Modal open onOpenChange={(o) => { if (!o) close(); }} width={620} title="Welcome: set up your copy"
      footer={<div className="row" style={{ width: "100%" }}>
        <button className="btn ghost" onClick={close}>Look around first</button>
        <button className="btn right" onClick={() => { close(); if (pathname !== "/register") go("/register"); }}>Create the first account</button></div>}>
      <ol className="guide">{GUIDE_STEPS.map((s, i) => <li key={s.title}><i aria-hidden>{i + 1}</i><div><b>{s.title}</b><p>{s.text}</p></div></li>)}</ol>
    </Modal>
  );
}
