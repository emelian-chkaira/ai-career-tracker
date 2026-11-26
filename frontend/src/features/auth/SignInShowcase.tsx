import type { CSSProperties } from "react";
import { Logo } from "@/shared/ui";

/** The sign-in story column: the README banner as a page. Employers and rows are made-up examples. */
const ATS = ["Greenhouse", "Lever", "Workday", "Personio", "Ashby", "Recruitee"];
const BOARDS = [["LinkedIn", "#0a66c2"], ["Indeed", "#2557d6"], ["Glassdoor", "#0c8f37"], ["Bayt", "#d9480f"]] as const;
const ROWS = [
  { initial: "N", color: "#0d9488", title: "Backend Developer", from: "Northwind Labs · from its careers page", score: "92%", tag: "IND sponsor", kind: "ind" },
  { initial: "T", color: "#7c3aed", title: "Data Engineer", from: "Tulip Energy · from its job system", score: "87%", tag: "", kind: "" },
  { initial: "C", color: "#0a66c2", title: "Data Science Intern", from: "Canal Pay · found on a job board", score: "81%", tag: "Internship", kind: "intern" },
];
const at = (s: number) => ({ "--d": `${s}s` }) as CSSProperties;

export function SignInShowcase() {
  return (
    <aside className="si-story">
      <Logo />
      <div className="si-body">
        <header className="si-head si-rise">
          <h2>Jobs <em>straight from the source.</em></h2>
          <ul className="si-pills">
            <li className="intern"><span aria-hidden>🎓</span> Jobs and internships</li>
            <li className="ind"><span className="si-flag" aria-hidden /> Netherlands: IND recognised sponsors</li>
          </ul>
        </header>
        <div className="si-show">
          <section className="si-sources si-rise" style={at(0.12)}>
            <p className="si-kicker">Fetched from original sources</p>
            <h3>Employers&rsquo; own career pages</h3>
            <ul className="si-ats">{ATS.map((n, i) => <li key={n} className="si-rise" style={at(0.25 + i * 0.05)}>{n}</li>)}</ul>
            <p className="si-kicker boards">+ Optional job-board searches</p>
            <ul className="si-boards">{BOARDS.map(([n, c], i) => <li key={n} className="si-rise" style={{ ...at(0.55 + i * 0.06), background: c }}>{n}</li>)}</ul>
          </section>
          <div className="si-flow" aria-hidden>
            <svg viewBox="0 0 400 44" preserveAspectRatio="none">
              <path d="M70 0 C70 30 200 14 200 44" stroke="#34d399" />
              <path d="M200 0 V44" stroke="#38bdf8" />
              <path d="M330 0 C330 30 200 14 200 44" stroke="#fbbf24" />
            </svg>
            <span>one role · one card</span>
          </div>
          <section className="si-list si-rise" style={at(0.3)} aria-label="Example job list">
            <p className="si-list-head"><b>Your one list</b><span>ranked against your CV</span></p>
            <ul>{ROWS.map((r, i) => <li key={r.title} className="si-rise" style={at(0.7 + i * 0.14)}>
              <i style={{ background: r.color }} aria-hidden>{r.initial}</i>
              <div><p><b>{r.title}</b>{r.tag && <em className={r.kind}>{r.tag}</em>}</p><span>{r.from}</span></div>
              <strong>{r.score}</strong></li>)}</ul>
            <p className="si-next">&rarr; tailor your CV · apply · track replies from your inbox</p>
          </section>
        </div>
      </div>
      <p className="si-note"><span className="si-flag" role="img" aria-label="Netherlands flag" />
        <span>Example employers shown. Job boards stay off until you switch them on. Sponsor flags come from the Netherlands&rsquo; IND register (Immigration and Naturalisation Service): a signal, not immigration advice.</span></p>
    </aside>
  );
}
