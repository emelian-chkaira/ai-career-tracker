import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { Logo } from "@/shared/ui";
import { Icon } from "@/shared/ui/Icon";
import { COMPARE, FEATURES, STATUS } from "./features";
import { REPO, useDemo } from "./useDemo";

const SEEN = "demo:tour-seen";
const seen = () => { try { return localStorage.getItem(SEEN) === "1"; } catch { return false; } };
const remember = () => { try { localStorage.setItem(SEEN, "1"); } catch { /* private window: show it again next time */ } };
const STEPS = ["Welcome", "Features", "Good to know"];
const SKIP_ON = ["/reset", "/verify", "/action"];          // links from e-mails go straight to their page

/** First-visit tour of the online demo: what the app does, what is switched off here, and a one-click guest sign-in. */
export function DemoTour() {
  const { demo, guestDays } = useDemo(); const { user, ready, startDemo } = useAuth(); const nav = useNavigate(); const { pathname } = useLocation();
  const [open, setOpen] = useState(false); const [step, setStep] = useState(0); const [pick, setPick] = useState(FEATURES[0].key);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  useEffect(() => { if (demo && ready && !user && !seen() && !SKIP_ON.includes(pathname)) setOpen(true); }, [demo, ready, user]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const h = () => { setStep(0); setErr(""); setOpen(true); }; window.addEventListener("open-tour", h); return () => window.removeEventListener("open-tour", h); }, []);
  if (!demo) return null;
  const close = () => { remember(); setOpen(false); };
  const start = async () => {
    setBusy(true); setErr("");
    try { await startDemo(); close(); nav("/", { replace: true }); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  const f = FEATURES.find((x) => x.key === pick)!; const last = step === STEPS.length - 1;
  return (<Dialog.Root open={open} onOpenChange={(o) => (o ? setOpen(true) : close())}><Dialog.Portal>
    <Dialog.Overlay className="tour-scrim" />
    <Dialog.Content className="tour" aria-describedby={undefined} onKeyDown={(e) => { if (e.key === "ArrowRight" && !last && !(e.target as HTMLElement).closest(".tour-tabs")) setStep(step + 1); if (e.key === "ArrowLeft" && step && !(e.target as HTMLElement).closest(".tour-tabs")) setStep(step - 1); }}>
      <header className="tour-top"><Logo />
        <ol className="tour-steps">{STEPS.map((s, i) => <li key={s}><button className={i === step ? "on" : i < step ? "done" : ""} aria-current={i === step ? "step" : undefined} onClick={() => setStep(i)}><i>{i + 1}</i><span>{s}</span></button></li>)}</ol>
        <button className="tour-x" onClick={close} aria-label="Close the tour"><Icon name="close" size={18} /></button></header>

      <div className="tour-body" key={step}>
        {step === 0 && <div className="tour-hello">
          <span className="tour-pill">Online demo</span>
          <Dialog.Title>Welcome to AI Career Tracker</Dialog.Title>
          <p>One place to find roles, shape your CV and follow every application. This website is a demo of our work, so take a minute to see what is inside.</p>
          <ul className="tour-flow">{[["search", "Find", "Search and filter roles"], ["cv", "Tailor", "Adapt your CV"], ["jobs", "Apply", "On the employer's site"], ["pipeline", "Track", "From saved to offer"]].map(([icon, t, s], i) =>
            <li key={t} style={{ animationDelay: `${i * 90}ms` }}><span><Icon name={icon} size={20} /></span><b>{t}</b><small>{s}</small></li>)}</ul>
        </div>}

        {step === 1 && <div className="tour-feat">
          <Dialog.Title className="tour-sr">Features</Dialog.Title>
          <div className="tour-tabs" role="tablist" aria-label="Features" aria-orientation="vertical" onKeyDown={(e) => {
            const d = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 0; if (!d) return; e.preventDefault();
            const n = FEATURES[(FEATURES.findIndex((x) => x.key === pick) + d + FEATURES.length) % FEATURES.length].key; setPick(n); document.getElementById("tab-" + n)?.focus(); }}>
            {FEATURES.map((x) => <button key={x.key} id={"tab-" + x.key} role="tab" aria-selected={x.key === pick} tabIndex={x.key === pick ? 0 : -1} className={x.key === pick ? "on" : ""} onClick={() => setPick(x.key)}>
              <Icon name={x.icon} size={17} /><span>{x.name}</span><i className={"dot " + x.status} title={STATUS[x.status]} /></button>)}</div>
          <section className="tour-view" role="tabpanel" aria-labelledby={"tab-" + f.key} key={f.key}>
            <span className={"tour-status " + f.status}>{STATUS[f.status]}</span>
            <h3>{f.headline}</h3><p>{f.text}</p>
            <div className="tour-mock" aria-hidden>{f.rows.map((r, i) => <div key={r.title} style={{ animationDelay: `${i * 80}ms` }}><span className="av">{r.title[0]}</span><div><b>{r.title}</b><small>{r.sub}</small></div><em>{r.tag}</em></div>)}</div>
            <p className="tour-note"><span>Example preview.</span> {f.note}</p>
          </section>
        </div>}

        {step === 2 && <div className="tour-know">
          <Dialog.Title>What is different online</Dialog.Title>
          <p>Free hosting is small, so a few things run only when you install the app on your own computer.</p>
          <table><thead><tr><th scope="col"><span className="tour-sr">Area</span></th><th scope="col">This online demo</th><th scope="col">On your computer</th></tr></thead>
            <tbody>{COMPARE.map(([k, a, b]) => <tr key={k}><th scope="row">{k}</th><td data-l="Online demo">{a.replace("{days}", String(guestDays))}</td><td data-l="Your computer">{b}</td></tr>)}</tbody></table>
          <p className="tour-fine">Please do not add sensitive personal documents here. The first visit after a quiet period can take up to a minute. <a href={REPO} target="_blank" rel="noreferrer">Run it yourself from GitHub</a>.</p>
        </div>}
      </div>

      <footer className="tour-foot">
        {step > 0 ? <button className="btn ghost" onClick={() => setStep(step - 1)}>Back</button> : <button className="btn ghost" onClick={() => setStep(2)}>Skip to the end</button>}
        <span className="err small" role="alert">{err}</span>
        <div className="tour-go">
          {!last ? <button className="btn" onClick={() => setStep(step + 1)}>{step === 0 ? "Show me the features" : "Next"}</button>
            : <>{!user && <button className="btn ghost" onClick={close}>Just look around</button>}
              {user ? <button className="btn" onClick={close}>Back to the app</button> : <button className="btn" onClick={start} disabled={busy}>{busy ? "Opening your demo…" : "Start the demo, no sign-up"}</button>}</>}
        </div>
      </footer>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>);
}
