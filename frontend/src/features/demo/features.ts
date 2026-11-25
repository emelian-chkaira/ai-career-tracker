export type Availability = "here" | "partly" | "local";
export interface Feature { key: string; icon: string; name: string; headline: string; text: string; status: Availability; note: string; rows: { title: string; sub: string; tag: string }[] }

export const STATUS: Record<Availability, string> = { here: "Works in this demo", partly: "Partly in this demo", local: "Only on your own computer" };

export const FEATURES: Feature[] = [
  { key: "search", icon: "search", name: "Job search", headline: "Find the right roles fast", status: "here",
    text: "Filter by field, country, level, language, work mode and salary. Small typos are forgiven.", note: "Searches the saved snapshot of jobs.",
    rows: [{ title: "Backend Engineer", sub: "Amsterdam · Hybrid", tag: "Junior" }, { title: "Mobile Developer", sub: "Berlin · Remote", tag: "English" }, { title: "Data Analyst", sub: "Utrecht · On-site", tag: "New" }] },
  { key: "sponsors", icon: "company", name: "Companies and sponsors", headline: "Know who can sponsor you", status: "here",
    text: "Browse employers and see which are on the Netherlands' IND register of recognised sponsors.", note: "A signal from a public register, not immigration advice.",
    rows: [{ title: "Example Tech B.V.", sub: "14 open roles", tag: "IND sponsor" }, { title: "Sample Labs", sub: "3 open roles", tag: "IND sponsor" }, { title: "Demo Studio", sub: "6 open roles", tag: "Not listed" }] },
  { key: "pipeline", icon: "pipeline", name: "Pipeline", headline: "Every application in one board", status: "here",
    text: "Move roles from saved to offer, with notes, contacts, follow-up dates and a timeline.", note: "A guest account starts with three sample applications.",
    rows: [{ title: "Frontend Engineer", sub: "Follow up on Friday", tag: "Applied" }, { title: "QA Engineer", sub: "Tuesday, 10:00", tag: "Interview" }, { title: "Platform Engineer", sub: "Reply by Monday", tag: "Offer" }] },
  { key: "cv", icon: "cv", name: "CV Studio", headline: "A CV you can shape per role", status: "partly",
    text: "Import a PDF or Word CV, edit it section by section and keep several versions.", note: "PDF typesetting is switched off online.",
    rows: [{ title: "Experience", sub: "3 entries", tag: "Edited" }, { title: "Projects", sub: "4 entries", tag: "AI may choose" }, { title: "Skills", sub: "18 skills", tag: "Ready" }] },
  { key: "ai", icon: "market", name: "AI fit and tailoring", headline: "Honest AI help, no invented facts", status: "partly",
    text: "Fit scores, tailored summaries and cover letters. A fact guard rejects claims your CV does not contain.", note: "Needs your own AI provider key, added in Settings.",
    rows: [{ title: "Fit score", sub: "Dutch required, not on your CV", tag: "Explained" }, { title: "Tailored bullets", sub: "Rewritten for one role", tag: "Checked" }, { title: "Cover letter", sub: "Draft you can edit", tag: "Draft" }] },
  { key: "alerts", icon: "bell", name: "Alerts and watchlist", headline: "Follow searches and employers", status: "partly",
    text: "Save a search or follow a company and get told when something new appears.", note: "No new jobs arrive online, so no new alerts will fire.",
    rows: [{ title: "My feed", sub: "Daily summary", tag: "Saved search" }, { title: "Example Tech B.V.", sub: "Watching", tag: "Company" }, { title: "Internships, NL", sub: "Weekly", tag: "Saved search" }] },
  { key: "inbox", icon: "inbox", name: "Inbox assistant", headline: "Your pipeline updates itself", status: "local",
    text: "Reads Gmail with read-only access and moves a role when a test, interview, offer or rejection arrives.", note: "Needs your own Google setup. Not connected online.",
    rows: [{ title: "Interview invitation", sub: "Moved to Interview", tag: "Detected" }, { title: "Online assessment", sub: "Moved to Assessment", tag: "Detected" }, { title: "Application received", sub: "Added to Applied", tag: "Detected" }] },
  { key: "crawler", icon: "crawler", name: "Crawler", headline: "Fresh jobs from the source", status: "local",
    text: "Reads company career pages and job boards on a schedule, following your fields and countries.", note: "Needs a lot of storage and memory. Online it would need paid hosting.",
    rows: [{ title: "Career pages", sub: "Read on a schedule", tag: "Worker" }, { title: "Job boards", sub: "Searched with your titles", tag: "Worker" }, { title: "Old postings", sub: "Removed automatically", tag: "Worker" }] },
];

export const COMPARE: [string, string, string][] = [
  ["Job data", "A saved snapshot, not updated in real time", "Updated as your crawler runs"],
  ["Crawler", "Off: needs more storage and RAM, so paid hosting", "Runs on your machine"],
  ["Gmail inbox", "Not connected", "Connect with your Google setup"],
  ["Semantic search and PDF export", "Switched off to fit free hosting", "Available"],
  ["Your account", "A guest account, removed after about {days} days", "Yours to keep"],
];
