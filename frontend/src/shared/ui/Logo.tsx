import { Link } from "react-router-dom";

/** The AI Career Tracker mark: a blue tile with a rising path (the job hunt, moving forward), plus the wordmark. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (<svg className="logomark" width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="AI Career Tracker">
    <rect width="32" height="32" rx="8" fill="#2563eb" />
    <path d="M7 22.5 13 16l4 3.5 7.5-8.5" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="24.5" cy="11" r="2.2" fill="#fff" />
  </svg>);
}

export function Logo({ to = "/", compact = false, light = false }: { to?: string; compact?: boolean; light?: boolean }) {
  return (<Link to={to} className={`logo-lockup${light ? " light" : ""}`} aria-label="AI Career Tracker, home">
    <LogoMark />{!compact && <span className="wordmark sl"><b className="grad-text">AI</b> Career Tracker</span>}</Link>);
}
