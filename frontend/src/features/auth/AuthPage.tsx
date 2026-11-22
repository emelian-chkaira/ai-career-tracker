import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { Icon } from "@/shared/ui/Icon";
import { GoogleButton } from "./GoogleButton";

/** 0-4: length, mixed case, digit, symbol. Display only; the server enforces the real rule. */
function strength(p: string) {
  let s = 0; if (p.length >= 8) s++; if (p.length >= 12) s++; if (/[a-z]/.test(p) && /[A-Z]/.test(p)) s++; if (/\d/.test(p) && /[^A-Za-z0-9]/.test(p)) s++;
  return Math.min(s, 4);
}
const LABELS = ["Too short", "Weak", "Okay", "Good", "Strong"];

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { user, login, register, google } = useAuth();
  const nav = useNavigate(); const loc = useLocation(); const reg = mode === "register";
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [name, setName] = useState("");
  const [show, setShow] = useState(false); const [agree, setAgree] = useState(false); const [touched, setTouched] = useState(false);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const from = (loc.state as { from?: string } | null)?.from ?? "/";
  if (user) return <Navigate to={from} replace />;
  const st = strength(password); const emailOk = /^\S+@\S+\.\S+$/.test(email); const pwOk = reg ? password.length >= 8 : password.length > 0;
  async function submit(e: FormEvent) {
    e.preventDefault(); setTouched(true); setErr("");
    if (!emailOk || !pwOk || (reg && !agree)) return;
    setBusy(true);
    try { reg ? await register(email, password, name) : await login(email, password); nav(from, { replace: true }); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="authwrap">
      <aside className="authside">
        <Link to="/" className="brand" style={{ color: "#fff" }}><i style={{ background: "#ffffff30" }}>NL</i><span>Career Tracker</span></Link>
        <div>
          <h2>Your job search in the Netherlands, in one place.</h2>
          <ul>
            <li><span className="fi"><Icon name="company" /></span><div><b>Straight from employers</b><span>Every role comes from the company's own career page.</span></div></li>
            <li><span className="fi"><Icon name="bell" /></span><div><b>Alerts that matter</b><span>Save a search or follow a company and hear about new roles the day they appear.</span></div></li>
            <li><span className="fi"><Icon name="cv" /></span><div><b>A CV that fits the job</b><span>Import once, edit live, tailor with AI and export a clean PDF.</span></div></li>
            <li><span className="fi"><Icon name="inbox" /></span><div><b>Your inbox, sorted</b><span>Interviews, tests, offers and rejections tracked from Gmail.</span></div></li>
          </ul>
        </div>
        <div className="small" style={{ opacity: .75 }}>IND sponsor status is shown as a flag, never as advice.</div>
      </aside>
      <main className="authmain">
        <form className="authform authcard stack" onSubmit={submit} noValidate>
          <div><h1>{reg ? "Create your account" : "Welcome back"}</h1>
            <div className="muted">{reg ? "Free. Takes less than a minute." : "Sign in to your saved searches, alerts and pipeline."}</div></div>
          <GoogleButton onError={setErr} onCredential={async (c) => { setErr(""); try { await google(c); nav(from, { replace: true }); } catch (x) { setErr((x as Error).message); } }} />
          {reg && <div className="field"><label htmlFor="n">Name</label><input id="n" type="text" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></div>}
          <div className="field"><label htmlFor="e">Email</label>
            <input id="e" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" aria-invalid={touched && !emailOk} />
            {touched && !emailOk && <span className="small err">Enter a valid email address.</span>}</div>
          <div className="field"><label htmlFor="p">Password</label>
            <div className="pw"><input id="p" type={show ? "text" : "password"} placeholder={reg ? "At least 8 characters" : "Your password"} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={reg ? "new-password" : "current-password"} aria-invalid={touched && !pwOk} />
              <button type="button" className="eye" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>{show ? "Hide" : "Show"}</button></div>
            {reg && password && <div className="meter" aria-live="polite"><div className="bars">{[1, 2, 3, 4].map((i) => <i key={i} className={i <= st ? `on s${st}` : ""} />)}</div><span className="small muted">{LABELS[st]}</span></div>}
            {!reg && <Link to="/forgot" className="small" style={{ alignSelf: "flex-end" }}>Forgot password?</Link>}
            {touched && !pwOk && <span className="small err">{reg ? "Use at least 8 characters." : "Enter your password."}</span>}</div>
          {reg && <label className="small row" style={{ alignItems: "flex-start", flexWrap: "nowrap", gap: 8 }}><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} style={{ marginTop: 3 }} />
            <span>I understand my saved searches and tracked jobs are stored on this server, and that my CV is stored (encrypted) only if I choose to save it for AI features.</span></label>}
          {touched && reg && !agree && <span className="small err">Please confirm to continue.</span>}
          {err && <div className="notice err" role="alert">{err}</div>}
          <button className="btn lg" style={{ justifyContent: "center" }} disabled={busy}>{busy ? "Please wait…" : reg ? "Create account" : "Sign in"}</button>
          <div className="small muted" style={{ textAlign: "center" }}>{reg ? <>Already have an account? <Link to="/login" state={loc.state}>Sign in</Link></> : <>New here? <Link to="/register" state={loc.state}>Create an account</Link></>}
            <br /><Link to="/">Continue without an account</Link></div>
        </form>
      </main>
    </div>
  );
}
