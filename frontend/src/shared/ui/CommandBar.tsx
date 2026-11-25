import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { useTheme } from "@/shared/lib/theme";

const PAGES: [string, string, boolean][] = [["Jobs", "/", false], ["Internships", "/internships", false], ["Companies", "/companies", false], ["CV Studio", "/cv", false],
  ["Pipeline & alerts", "/pipeline", true], ["Inbox", "/inbox", true], ["Crawler", "/crawler", true], ["Settings (AI, integrations, data)", "/profile", true], ["Visa sponsor lookup", "/sponsors", false], ["Watchlist", "/watchlist", true]];

/** ⌘K / Ctrl+K: jump anywhere, change theme, start a search. Opens with the keyboard or the "/" key is for the job search box. */
export function CommandBar() {
  const [open, setOpen] = useState(false); const nav = useNavigate(); const { user, logout } = useAuth(); const { next } = useTheme(); const [q, setQ] = useState("");
  useEffect(() => {
    const f = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); } };
    window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f);
  }, []);
  const go = (to: string) => { setOpen(false); setQ(""); nav(to); };
  return (<Command.Dialog open={open} onOpenChange={setOpen} label="Command bar" className="cmdk" shouldFilter>
    <Command.Input value={q} onValueChange={setQ} placeholder="Go to a page, or search jobs…" />
    <Command.List>
      <Command.Empty>No match. Press Enter to search jobs for “{q}”.</Command.Empty>
      <Command.Group heading="Go to">{PAGES.filter(([, to, auth]) => !auth || user).map(([n, to]) => <Command.Item key={to} value={n} onSelect={() => go(to)}>{n}</Command.Item>)}</Command.Group>
      <Command.Group heading="Actions">
        {q.trim() && <Command.Item value={`search ${q}`} onSelect={() => go(`/?q=${encodeURIComponent(q.trim())}`)}>Search jobs for “{q.trim()}”</Command.Item>}
        <Command.Item value="change theme" onSelect={() => { next(); setOpen(false); }}>Change theme</Command.Item>
        {user && <Command.Item value="sign out" onSelect={() => { setOpen(false); logout(); }}>Sign out</Command.Item>}
      </Command.Group>
    </Command.List>
    <div className="cmdk-hint">↑↓ to move · Enter to choose · Esc to close</div>
  </Command.Dialog>);
}
