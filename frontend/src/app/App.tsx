import { Navigate, Outlet, Route, Routes, useLocation, useNavigate, Link } from "react-router-dom";
import { useTheme } from "@/shared/lib/theme";
import { useAuth } from "@/features/auth/AuthContext";
import { AuthPage } from "@/features/auth/AuthPage";
import { ForgotPage, ResetPage, VerifyPage, VerifyBanner, ActionPage } from "@/features/auth/AccountPages";
import { JobsPage } from "@/features/jobs/JobsPage";
import { JobPage } from "@/features/jobs/JobPage";
import { CompaniesPage } from "@/features/companies/CompaniesPage";
import { useNotifications } from "@/features/alerts/api";
import { PipelinePage } from "@/features/pipeline/PipelinePage";
import { CvPage } from "@/features/cv/CvPage";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { CrawlerPage } from "@/features/admin/CrawlerPage";
import { useState } from "react";
import { Drawer, Menu, Splitter, Tip, TipProvider, usePane, usePersisted } from "@/shared/ui/kit";
import { Icon } from "@/shared/ui/Icon";
import { CommandBar } from "@/shared/ui/CommandBar";
import { WatchlistPage } from "@/features/companies/WatchlistPage";
import { Logo } from "@/shared/ui";
import { InboxPage } from "@/features/inbox/InboxPage";
import { SetupWizard } from "@/features/onboarding/SetupWizard";
import { ChangelogPage, useVersion } from "@/features/about/ChangelogPage";

const NAV: { group: string; items: { to: string; text: string; icon: string; auth?: boolean; match?: string[] }[] }[] = [
  { group: "Discover", items: [{ to: "/", text: "Jobs", icon: "jobs", match: ["/internships"] }, { to: "/internships", text: "Internships", icon: "intern" }, { to: "/companies", text: "Companies", icon: "company" }, { to: "/sponsors", text: "Visa sponsors", icon: "company" }] },
  { group: "My search", items: [{ to: "/pipeline", text: "Pipeline", icon: "pipeline", auth: true }, { to: "/inbox", text: "Inbox", icon: "inbox", auth: true }, { to: "/watchlist", text: "Watchlist", icon: "bell", auth: true }, { to: "/cv", text: "CV Studio", icon: "cv" }] },
  { group: "System", items: [{ to: "/crawler", text: "Crawler", icon: "crawler", auth: true }, { to: "/profile", text: "Settings", icon: "profile", auth: true }] }];
const TITLES: Record<string, string> = { "/": "Jobs", "/internships": "Internships", "/companies": "Companies", "/pipeline": "Pipeline", "/inbox": "Inbox", "/cv": "CV Studio", "/crawler": "Crawler", "/profile": "Settings", "/sponsors": "Visa sponsors", "/watchlist": "Watchlist" };

function SideNav({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const { user } = useAuth(); const n = useNotifications(!!user); const loc = useLocation();
  return (<nav className="snav" aria-label="Main">{NAV.map((g) => { const items = g.items.filter((i) => !i.auth || user); if (!items.length) return null; return (
    <div key={g.group} className="sgroup">{!collapsed && <div className="sgroup-t">{g.group}</div>}
      {items.map((i) => { const active = i.to === "/" ? loc.pathname === "/" : loc.pathname.startsWith(i.to); return (
        <Link key={i.to} to={i.to} onClick={onNavigate} className={`sitem${active ? " active" : ""}`} title={collapsed ? i.text : undefined} aria-current={active ? "page" : undefined}>
          <Icon name={i.icon} /><span className="sl">{i.text}</span>{i.to === "/pipeline" && !!n.data?.unread && <span className="sbadge">{n.data.unread}</span>}</Link>); })}</div>); })}</nav>);
}

function Layout() {
  const { user, logout } = useAuth(); const { theme, next } = useTheme(); const loc = useLocation(); const go = useNavigate();
  const ver = useVersion(); const side = usePane("sidebar", 196, 150, 320); const [collapsed, setCollapsed] = usePersisted("sidebar:collapsed", false); const [mobile, setMobile] = useState(false);
  const title = TITLES[loc.pathname] ?? NAV.flatMap((g) => g.items).find((i) => i.to !== "/" && loc.pathname.startsWith(i.to))?.text ?? "";
  const brand = <Logo compact={collapsed} />;
  return (<div className={`app${collapsed ? " collapsed" : ""}`} style={{ "--sw": `${side.width}px` } as React.CSSProperties}>
    <aside className="side">{!collapsed && <Splitter props={side.props} label="Resize sidebar" />}{brand}<SideNav collapsed={collapsed} />
      <div className="side-ft">
        <button className="sitem" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))} aria-label="Search and jump anywhere" title="Search (⌘K)"><Icon name="search" /><span className="sl">Search <kbd>⌘K</kbd></span></button>
        <button className="sitem" onClick={next} aria-label="Change theme" title={`Theme: ${theme}`}><span className="ticon">{theme === "light" ? "☀️" : theme === "dark" ? "🌙" : "🖥️"}</span><span className="sl">Theme: {theme}</span></button>
        {user ? <Menu label="Account menu" trigger={<span className="row" style={{ gap: 8, flexWrap: "nowrap" }}><span className="avatar">{(user.name || user.email)[0].toUpperCase()}</span><span className="small email sl">{user.name || user.email}</span></span>}
          items={[{ label: user.email, onSelect: () => go("/profile") }, { label: "Settings", onSelect: () => go("/profile") }, { label: "CV Studio", onSelect: () => go("/cv") }, { label: "Sign out", onSelect: logout, danger: true }]} />
          : <><Link className="sitem" to="/login"><Icon name="profile" /><span className="sl">Sign in</span></Link><Link className="sitem" to="/register"><Icon name="bell" /><span className="sl">Sign up</span></Link></>}
        <button className="sitem" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}><Icon name={collapsed ? "expand" : "collapse"} /><span className="sl">Collapse</span></button>
        {ver.data && <Link className="small muted sl" to="/changelog" style={{ padding: "2px 10px", textDecoration: "none" }} title="What's new">v{ver.data.version}</Link>}</div></aside>
    <Drawer open={mobile} onOpenChange={setMobile} title="Menu" side="left" size={280}><SideNav collapsed={false} onNavigate={() => setMobile(false)} /></Drawer>
    <div className="body"><header className="bar">
      <button className="kicon only-mobile" onClick={() => setMobile(true)} aria-label="Open menu"><Icon name="menu" /></button>
      <h1 className="bar-title">{title}</h1>
      <div className="bar-r">
        <Tip text="Search and jump anywhere (⌘K)"><button className="cmdbtn" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))} aria-label="Open command bar"><Icon name="search" size={15} /><span>Search…</span><kbd>⌘K</kbd></button></Tip>
        <Tip text={`Theme: ${theme} (click to change)`}><button className="themebtn" onClick={next} aria-label="Change theme">{theme === "light" ? "☀️" : theme === "dark" ? "🌙" : "🖥️"}</button></Tip>
        {user ? <Menu label="Account menu" trigger={<span className="row" style={{ gap: 8, flexWrap: "nowrap" }}><span className="avatar">{(user.name || user.email)[0].toUpperCase()}</span><span className="small email">{user.name || user.email}</span></span>}
          items={[{ label: user.email, onSelect: () => go("/profile") }, { label: "Settings", onSelect: () => go("/profile") }, { label: "CV Studio", onSelect: () => go("/cv") }, { label: "Sign out", onSelect: logout, danger: true }]} />
          : <><Link className="btn ghost small" to="/login">Sign in</Link><Link className="btn small" to="/register">Sign up</Link></>}</div></header>
      <main className="main"><VerifyBanner /><Outlet /></main></div>
    <CommandBar /><SetupWizard /></div>);
}
function Protected({ admin = false }: { admin?: boolean }) {
  const { user, ready } = useAuth(); const loc = useLocation();
  if (!ready) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname + loc.search }} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return <Outlet />;
}
export default function App() {
  return (<TipProvider><Routes>
    <Route path="/login" element={<AuthPage mode="login" />} /><Route path="/register" element={<AuthPage mode="register" />} />
    <Route path="/forgot" element={<ForgotPage />} /><Route path="/reset" element={<ResetPage />} /><Route path="/verify" element={<VerifyPage />} /><Route path="/action" element={<ActionPage />} />
    <Route element={<Layout />}>
      <Route index element={<JobsPage />} /><Route path="internships" element={<JobsPage internships />} /><Route path="jobs/:id" element={<JobPage />} /><Route path="companies" element={<CompaniesPage />} /><Route path="sponsors" element={<CompaniesPage sponsors />} />
      <Route path="changelog" element={<ChangelogPage />} /><Route path="dashboard" element={<Navigate to="/" replace />} /><Route path="cv" element={<CvPage />} />
      <Route element={<Protected />}>
        <Route path="pipeline" element={<PipelinePage />} /><Route path="alerts" element={<Navigate to="/pipeline" replace />} /><Route path="inbox" element={<InboxPage />} /><Route path="watchlist" element={<WatchlistPage />} />
        <Route path="my" element={<Navigate to="/pipeline" replace />} /><Route path="profile" element={<ProfilePage />} /><Route path="crawler" element={<CrawlerPage />} />
      </Route>
      <Route path="admin" element={<Navigate to="/crawler" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route></Routes></TipProvider>);
}
