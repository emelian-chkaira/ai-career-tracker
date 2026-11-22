# NL Career Tracker vs JobOps: a deep comparison and how to close the gap

*Written 21 Nov 2026. JobOps = `DaKheera47/job-ops` (the copy you cloned and the prebuilt image you ran at http://localhost:3005).*

## How this was checked, and what it does not cover

| Source | What I did |
|---|---|
| JobOps source code | Read the server (AI providers, scorer, ghostwriter, resume renderer, tracking, auth, pipeline), the React client (pages, components, dependencies) and the shared package. |
| JobOps docs and screenshots | Read the feature docs and looked at the screenshots shipped in `docs-site/static/img/features/`. |
| JobOps running app | The container is up and healthy, but it opens on a **sign-in page** and I did not have an account. I cannot create one or type a password for you. So the live UI was judged from the shipped screenshots and the client code, **not clicked through**. If you sign in at http://localhost:3005 and tell me, I can walk through it live and correct anything below. |
| Our app | I know it first-hand (I built most of it). Figures come from our database and test suite. |

**Licence note.** JobOps is AGPLv3 with the Commons Clause (no selling). We are MIT. We can study ideas and behaviour. All code we write must be our own. Nothing in the roadmap below needs their code.

---

## 1. The one-paragraph verdict

They are a **mature, general-purpose, multi-country job-hunting workstation** (about 120,000 lines of TypeScript, 300 test files, 16 AI providers, a full resume editor, a per-job AI chat, a polished component-library UI). We are a **focused Netherlands product with better data and a better mobile story, but a thinner AI and CV layer and no UI component system or front-end tests**. After the work done this week (fit score, timeline, follow-ups, tailored CV with fact guard) we are close on *features* and still clearly behind on **AI flexibility, resume editing depth, the per-job assistant, UI craft and test coverage**. For a CV project, the honest pitch is: *employer-direct Dutch data you cannot get from them, plus a safer AI layer*, and the roadmap below closes the rest.

---

## 2. What each product is

| | **JobOps** | **NL Career Tracker** |
|---|---|---|
| Goal | Find jobs anywhere, auto-rank, tailor, apply, track | Find jobs in the Netherlands straight from employers, track, tailor |
| Stack | Node 22, Express, **SQLite** (Drizzle), React 18 + Tailwind 4 + Radix, Vitest, Biome | Python, FastAPI, **Postgres 16 + pgvector**, React 18 + TanStack Query, plain CSS, pytest, **Flutter mobile app** |
| Size | ~120k lines TS, 300 test files | ~6.7k lines Python backend, 102 backend tests, 0 front-end tests |
| Where jobs come from | Scrapes **job boards** (LinkedIn, Indeed, Glassdoor via JobSpy, Adzuna, Seek, Naukri, StartupJobs, …, 15 extractors) plus a company **watchlist** | Crawls **employers' own career pages** (Greenhouse, Lever, Ashby, Recruitee, BambooHR, Teamtailor, SmartRecruiters, Workable, plus HTML and browser-rendered pages): 3,200 companies, 4,118 open jobs, 13,089 IND sponsor records |
| Deploy | `docker compose up` (one container, SQLite file) | Docker / `setup.sh` / Render + Neon free |
| Licence | AGPLv3 + Commons Clause | MIT |

Their model is wide (many boards, many countries). Ours is deep (one country, direct from the source, deduplicated, sponsor-aware). That is a real product difference, not a gap.

---

## 3. Feature-by-feature judgement

Verdict key: **Them** = they are clearly better, **Us** = we are clearly better, **Even** = comparable.

| Area | JobOps | Us | Verdict |
|---|---|---|---|
| Job sources | 15 board extractors, global, fragile by nature (scraping LinkedIn/Indeed breaks and is against their terms) | Direct ATS APIs + career pages, NL-only, stable, deduped, no ToS risk | **Us** for NL reliability. **Them** for breadth |
| Search | Keyword + AI-generated search plan + saved searches, location radius map | Full-text + semantic (pgvector) + hybrid, operators, typo tolerance, synonyms | **Us** |
| Visa sponsors | UK, Canada, NL, US registers | NL IND register, matched to employers, shown on every job | **Even** (they have more countries, we have it tighter in NL) |
| AI fit scoring | 0-100 score + reason per job, per-task model, auto-skip threshold, salary penalty, editable prompt | 0-100 score + strengths/gaps/deal-breakers, cached, server-side Dutch cap, batch scoring | **Even**, they have more knobs, we have more evidence and code-level guards |
| AI provider support | 16 providers incl. CLI ones | 11 presets + custom | **Them** (see §4) |
| Per-job AI assistant | **Ghostwriter**: chat per job with notes, emails, documents as context | None (cover letter only) | **Them** |
| CV editing | Resume Studio: structured editor, rich text, per-field AI, live PDF preview | Import + parse + edit in CV Studio | **Them** (see §5) |
| CV tailoring | Per-job summary/headline/skills + project selection, auto-regenerated PDF | Per-job rewrite of summary and bullets, diff view, **fact guard**, keyword coverage, 2 layouts | **Even**, ours is safer, theirs is more automated |
| PDF output | Typst themes (classic, clean-print, compact) + Jake LaTeX + optional Reactive Resume | 2 LaTeX layouts (tectonic locally, public service with consent) | **Them** (more themes, paper size) |
| Cover letter | Via Ghostwriter | One-shot AI letter, editable | **Them** |
| Tracking | 8 stages, kanban, stage events with metadata, tasks, email review queue | Timeline, follow-ups, drag board, funnel stats, mail → timeline | **Even** now, they still have tasks and analytics over time |
| Inbox / email | Gmail OAuth + IMAP, confidence tiers (auto ≥95%, review 50-94%) | Gmail OAuth, AI classification, review and accept | **Even**, they have IMAP and auto-processing |
| Analytics | Applications per day, response conversion, funnel, 7/14/30/90 d | Market dashboard + your funnel stats | **Them** for personal analytics. **Us** for market data |
| Alerts | Watchlist alerts | Saved-search alerts + follow-up reminders | **Even** |
| Mobile | Responsive web only | **Native Flutter app** (iOS/Android) | **Us** |
| Login | Username/password, SSO (Google, GitHub, any OIDC), multi-tenant hosted mode | Firebase email + Google, verification and reset mail, admin role | **Them** for options. **Even** for what a user needs |
| Privacy controls | Local instance | Encrypted keys, CV and Gmail token, explicit consent before data leaves for an AI provider | **Us** |
| UI quality | Component library (Radix), ⌘K command bar, keyboard shortcuts, virtualised lists, bulk actions, onboarding wizard | Custom flat CSS, light/dark/system | **Them** |
| Testing | 300 test files, Storybook | 102 backend tests, none on the front end | **Them** |
| Ops | Backups, webhooks, extractor health, demo mode, billing hooks | Crawler admin page, retention, health endpoint | **Them** |

---

## 4. AI: connection and use of models

### What they do
- **16 providers** behind one interface: OpenAI, Anthropic, Gemini, OpenRouter, GLM, Ollama, LM Studio, LiteLLM, Requesty, OrcaRouter, AtlasCloud, any OpenAI-compatible URL, and three **CLI providers** (Codex, Claude CLI, Gemini CLI) so a person can use a subscription they already pay for instead of an API key.
- **Structured output with a fallback ladder**: ask for `json_schema`, fall back to `json_object`, then to plain text with tolerant parsing. A `capability-fallback` policy remembers what each model supports.
- **Retry and error policy**: separate "configuration problem" (tell the user to fix settings) from "transient problem" (just try again later, never blame the user).
- **Per-task models**: one default model plus overrides for scoring, tailoring and project selection. A settings screen shows the "resolved config" (what is really used and why).
- **Everything editable**: the prompt templates are settings (with `{{tokens}}`), plus a **writing style** (tone, formality, constraints, banned words) and an **output language**.
- **Usage metering** for their hosted mode (reserve, settle, refund per call).

### What we do
- One chosen model per user, 11 presets (Ollama, Groq free tier, Grok, DeepSeek, Qwen, Moonshot, Zhipu, OpenRouter, Anthropic, OpenAI, custom). Keys are encrypted at rest.
- **Consent gate**: nothing is sent to an outside provider until the user agrees, per action. They run locally so they do not need this; for us it is a real privacy feature.
- **Server-side guards the model cannot override**: Dutch-required cap on the score, and the CV fact guard (an edit that adds a number or a skill the CV lacks is rejected and listed).
- Cached scores keyed by hash of CV, posting, language, sponsor and model.

### Gap and how to close it (our own code)
1. **Structured-output ladder + a small per-model capability memory** in `llm_service.py` (JSON schema → JSON object → text). Removes the "unexpected response" class of errors we hit with Groq.
2. **Split errors into "configuration" vs "transient"** with different messages and retry behaviour. Cheap, and visible quality.
3. **Per-task model overrides** (scoring, tailoring, inbox, letter) with a "resolved settings" panel. Lets someone use a cheap model for the inbox and a strong one for tailoring.
4. **Editable prompts, writing style, output language** (tone, formality, banned words). Stored per user, with the safe defaults and the fact guard still applied on top.
5. **LM Studio and LiteLLM presets** (trivial, both OpenAI-compatible).
6. **CLI providers are optional and skippable.** They are nice on a laptop, not safe on a shared server, so I would add them behind an env flag and never on the public demo.

---

## 5. CV Studio and the "reactive" resume

### What they do
- **Resume Studio** keeps one canonical, structured resume (the Reactive Resume v5 JSON schema) and edits it in place: rich-text fields (TipTap), item dialogs, a list editor per section, a side rail, a **live PDF preview** while you edit.
- **Import by LLM**: upload a PDF/DOCX and the model produces the structured resume (with Claude/Gemini CLI paths).
- **Per-field AI assistant** (select a field, ask for a rewrite, review, apply). It is ephemeral, so nothing changes until you accept.
- **Project catalog**: your projects are listed once, and each job picks the relevant ones automatically (and you can override). Output stays tidy, one page.
- **Renderers**: Typst themes (classic, clean-print-cv, compact), Jake LaTeX template, or Reactive Resume's own export. Paper size (A4/Letter).
- **Auto PDF regeneration** when the source or the job changes, **tracer links** (rewrite resume links so you can see if a recruiter clicked), PDFs stored per job.
- Round-trips to Reactive Resume.

### What we do
- Import PDF/DOCX/text/LaTeX with a rules-based parser that keeps links, then a form editor with tag inputs and LaTeX output.
- Per-job tailoring that **only rewords** and proves it (fact guard, diff, keyword coverage before/after), two layouts, PDF via local tectonic.
- Cover letter generation and editing.

### Where they are ahead
- A **real editor with live preview** (ours is "edit, then build").
- **LLM-assisted import** (more robust on odd layouts than our rules parser).
- **Project selection per job** and **more themes**.
- **PDF stored per job and kept fresh** automatically.

### Plan (in order of value for effort)
1. **Live PDF preview** beside the editor (debounced build, we already compile in about a second locally). Biggest "feels pro" jump.
2. **LLM-assisted import as a second pass** over our parser output (fix headings, dates, bullets), still behind consent.
3. **Per-field AI assist** reusing the fact guard: "improve this bullet", apply or discard.
4. **Project/experience selection per job** using the fit score's keyword evidence; show "included / left out" toggles.
5. **Two more layouts** (a modern single-column and a two-column) and **paper size**.
6. **Auto-rebuild + store the PDF per job**, and optional **link tracking** (a short redirect that counts opens, self-hosted, off by default for privacy).
7. Export/import the structured resume as JSON so users can leave with their data.

---

## 6. Login, sessions and accounts

| | JobOps | Us |
|---|---|---|
| Methods | Username + password (JWT with a token blacklist), **SSO: Google, GitHub, any OIDC** (allow-lists by email domain, per-provider signup switch), optional HTTP basic auth | Email + password and Google through Firebase; verification and password-reset emails; Firebase REST, no SDK on the server |
| Model | Single user by default; **hosted multi-tenant mode** with tenant ids, signups switch, usage limits and billing hooks | Multi-user, per-user data and keys, admin role, rate limits |
| Fit | Self-host first | Portfolio/public-demo first |

**Judgement:** for a demo that recruiters click, ours is **easier** (Google in one click, real email verification). Theirs is **more flexible** for self-hosters (any OIDC provider, no third party). Neither is ahead in security basics.

**Improve:** add a generic **OIDC option** (Keycloak, Pocket ID, Authentik) next to Firebase; add **session management** (list and revoke sessions) and **account deletion/export**. Keep Firebase as the default, since it is what makes the hosted demo work without running a mail server.

---

## 7. UI design and flexibility

### What they do well (from the screenshots and client code)
- **Component system**: shadcn-style Radix primitives (dialogs, popovers, tabs, selects, switches, tooltips) with Tailwind 4 and `cva` variants, so every control behaves the same and is keyboard- and screen-reader-friendly.
- **Master-detail Jobs workspace**: list on the left with score, status dot and salary, detail on the right with a *Fit assessment* block, a *Tailored summary*, *Ghostwriter*, *Download PDF* and one big *Mark applied* action. The primary action is obvious.
- **Speed tools**: ⌘K command bar, `j/k` navigation, multi-select with bulk actions, virtualised long lists (`@tanstack/react-virtual`), floating action bar, mobile job drawer.
- **Onboarding wizard** (model, profile, resume, search), **offline page**, **error boundary**, toasts with progress for long actions.
- **Settings as a product**: collapsible sections for model, scoring, ghostwriter, display, backup, webhooks, danger zone, each showing *effective vs default* values.
- **Dashboards** with a 7/14/30/90-day switch (applications per day, funnel, conversion).
- A **warm dark theme** (terracotta accent on charcoal) used consistently, plus Storybook for components.

### Where we are good
- A **calmer, more humane** look (warm paper, serif headings), light/dark/system, a clean mobile layout, plain CSS that is easy to read.
- **Native mobile app** with the same design language.

### Honest gaps
No component library, no keyboard shortcuts or command bar, no bulk actions or list virtualisation, no onboarding flow, no toast/progress system for long jobs (we use inline text), no front-end tests, no Storybook, limited accessibility auditing.

### Plan
1. **Adopt Radix primitives** for dialog, select, tabs, tooltip, switch (keep our CSS tokens so the look stays ours). Replace the hand-made drawer and selects.
2. **Command bar (⌘K)** over jobs, companies and pages, plus `j/k`, `/`, `a` (apply) shortcuts.
3. **Master-detail Jobs layout** on wide screens (we have the drawer; make it a pinned right pane with the fit block first).
4. **Bulk select**: score selected, add to pipeline, skip.
5. **Onboarding wizard** (3 steps: AI model, CV, preferences) that ends on a scored result so the first minute shows the value.
6. **Toast + progress** component for batch scoring, mail sync and PDF builds.
7. **Virtualise** the job list.
8. **A settings page with "effective vs default"** for AI, scoring and alerts.
9. Add **Vitest + Testing Library** for the shared components and **Playwright** smoke tests for sign-in → search → score → track. This is the single highest-value credibility item for a CV project.

---

## 8. Tracking and email

| | JobOps | Us |
|---|---|---|
| Stages | Applied → Recruiter screen → Assessment → Team match → Technical interview → Final round → Offer → Closed | Shortlisted → Applied → Screening → Interview → Offer → Accepted / Rejected / Withdrawn / Skipped |
| History | Stage events with metadata, editable, plus a **tasks** list | Timeline (stage, note, interview, e-mail, follow-up) with applied date, contact, offer details |
| Reminders | Tasks | Follow-up date with one in-app notification when due |
| Board | In-progress kanban, sortable | Drag-and-drop board with fit chip and follow-up badge |
| Analytics | Applications/day, funnel, conversion, 7/14/30/90 d | Active, heard-back rate, average reply time, funnel (no time series yet) |
| Email | Gmail OAuth **and IMAP**, confidence tiers: ≥95% auto-applied, 50-94% review with a suggestion, <50% orphan; every sync run is logged | Gmail OAuth, AI classifies, you accept or dismiss each, accept writes the timeline |

**Improve:** add (a) **tasks per job** (generic to-dos with due dates, "send portfolio", "prepare for system design"), (b) **applications-per-day chart and conversion over time**, (c) **confidence tiers** so high-confidence mails are applied automatically with an undo, (d) **sync-run history** on the Inbox page, (e) **IMAP** as a second provider so non-Gmail users work, (f) a **finer stage list** for the interview phase.

---

## 9. Data, crawling and "how they fetch from LinkedIn"

They use **JobSpy** (a Python scraper that logs into nothing but queries LinkedIn/Indeed/Glassdoor public search pages) and a set of per-site extractors, run in a browser with stealth (**Camoufox**, a patched Firefox) to get past bot detection. That gives breadth and the largest postings pool, but:
- it is **fragile** (the sites change and block), and
- scraping LinkedIn is **against its terms**, which matters for a public portfolio.

We deliberately do not do this. We read the **employer's own ATS** (public JSON APIs) and career pages: stable, legal, deduplicated, and every job has a real apply link at the employer.

**Where to go further without scraping boards:**
1. More ATS adapters (Personio, Workday public endpoints, Join, Homerun, Comeet).
2. A **watchlist** UX like theirs: follow a company, get an alert for new roles (we have saved searches; add "follow company").
3. **Location radius search** (city + km) using a Dutch city table, since distance matters in NL.
4. An **extractor health** panel: per-source last success, failures, jobs gained/lost (we have the data, expose it).
5. **Optional, opt-in board connectors** only where an official API exists (Adzuna has one).

---

## 10. Engineering quality and operations

| | JobOps | Us |
|---|---|---|
| Tests | 300 files across server, client, shared | 102 backend tests on real Postgres; **no front-end or end-to-end tests** |
| Tooling | Biome (lint+format), Storybook, knip (dead code), docs site (Docusaurus) | GitHub Actions per part (backend, frontend) |
| Ops | Backup/restore, webhooks, extractor health, demo mode, activation funnel | Seed data, one-click setup, Render demo, Oracle guide |
| Docs | Full docs site, workflows | READMEs and four deploy/setup docs |

**Improve (cheap, high signal):** front-end Vitest, a Playwright smoke test in CI, a typed API client generated from FastAPI's OpenAPI schema, a linter/formatter for the front end, a `docs/` site (MkDocs or Docusaurus) generated from the existing markdown, **backup/export** (JSON of the user's data), and **webhooks** (notify a URL on a stage change).

---

## 11. Where we are already better (keep and advertise)

1. **Employer-direct, deduplicated Dutch data** with IND sponsor matching on every job. They cannot offer this.
2. **Postgres + pgvector hybrid search** with operators and typo tolerance.
3. **Privacy-first AI**: encrypted keys/CV/token, consent before any text leaves, local Ollama as a first-class option.
4. **Code-level AI guards**: Dutch-required cap, **CV fact guard**, cached scores. Models can be wrong; the server does not take their word.
5. **A native mobile app** sharing the same API contract.
6. **MIT licence**, free hosted demo path, and a simple one-click setup.

---

## 12. Prioritised roadmap (to reach "same level or better")

Effort: S ≤ 1 day, M = 2-4 days, L = 1-2 weeks.

| # | Item | Why it matters | Effort |
|---|---|---|---|
| 1 | **Front-end tests + Playwright smoke in CI** | Biggest credibility gap; shows engineering discipline | M |
| 2 | **Live PDF preview in CV Studio** | The most visible "pro" feature of their resume editor | S-M |
| 3 | **Structured-output ladder + config/transient error split + per-task models** | Reliability and flexibility of AI, fewer user-facing errors | M |
| 4 | **Per-job assistant (chat)** with the job, your CV, notes and mail as context, streaming, cancel | Their signature feature; reuses our AI settings and consent | M-L |
| 5 | **Master-detail Jobs layout + ⌘K + shortcuts + bulk actions** | Speed and feel | M |
| 6 | **Radix-based component layer** (dialog, select, tabs, tooltip, toast) | Consistency and accessibility | M |
| 7 | **Onboarding wizard** | First-minute value | S-M |
| 8 | **Tasks per job + applications-per-day chart + conversion over time** | Closes the tracking gap | M |
| 9 | **Editable prompts, writing style, output language** | Flexibility they advertise | S-M |
| 10 | **LLM-assisted CV import + per-field AI assist + project selection per job** | Closes the CV gap | M-L |
| 11 | **More themes + paper size + stored PDF per job** | Output quality | M |
| 12 | **Mail confidence tiers + IMAP + sync history** | Inbox parity | M |
| 13 | **OIDC option, sessions list, data export/delete, backup** | Account and ops completeness | M |
| 14 | **More ATS adapters, follow-a-company, radius search, source health panel** | Data lead | M-L |
| 15 | **Mobile sync of fit score, timeline, follow-ups, tailored CV; push reminders** | Our unique advantage over them | L |

Suggested order for the best CV impact: **1 → 2 → 3 → 4 → 5/6 → 8 → 15**, then the rest.

---

### 12b. Status after the implementation round

Done: front-end tests (Vitest, 16) + Playwright e2e (4) + CI; live CV preview, Reactive Resume v5 import/export, 3 layouts, A4/Letter; AI error split, JSON-mode fallback, per-task models, writing style; per-job assistant; ⌘K command bar, shortcuts, bulk actions, toasts, onboarding checklist; per-job tasks, applications-per-day chart; inbox confidence auto-apply with undo and sync history; data export/delete and sessions; follow-a-company, radius search, source health.

Not done (honest list): Radix select/tabs component layer (only dialog-style cmdk and sonner were added), list virtualisation (pages are 20 rows, so not needed), IMAP and OIDC, new ATS adapters, per-field AI assist and LLM-assisted CV import, project selection per job, stored PDF per job, editable prompt templates, mobile sync and push reminders, scheduled backup.

## 13. Bottom line

- **Feature coverage:** after this week's work we are roughly **70-75% of their surface** for a Dutch-focused user, and ahead on search, sponsor data, privacy and mobile.
- **The visible gaps** a reviewer will notice first are the **CV editor with live preview, the per-job assistant, UI polish (command bar, shortcuts, component system) and test coverage**.
- Closing items 1-8 in the roadmap gets us to parity in how it *feels*; items 9-14 reach parity in *flexibility*; item 15 keeps a lead they cannot match.

---

## 14. Live check of the running app (21 Nov 2026)

Signed in and looked at the running container at http://localhost:3005. Only partly, because the app **gates everything behind onboarding** until the last step is confirmed, and I did not press "Use this resume" for you. What I saw:

- **Onboarding is a 3-step gate**: *Your search*, *AI connection*, *Your resume*. Until step 3 is confirmed, every other page (jobs, board, resume studio) redirects back to it. Good first-run guidance, but a user cannot look around before committing.
- **Resume review step**: the uploaded CV was parsed into a name, headline and three experience entries with dates, with a "Parsed successfully / 3 experience entries" badge and an "Edit in Resume Studio" link. It also showed **"No location detected"**, so their LLM-assisted import misses details too. Our rules parser does the same on odd layouts; neither is perfect, and both need a review step.
- **Settings** (briefly readable before the redirect): sections *AI*, *Scoring*, *Integrations*, *Workspaces & Security*, *Display*, *Backups*, *Danger zone*. The *Models* page has a provider selector, an API key field, a default model, **purpose-specific overrides** (Scoring, Tailoring, Project selection) and a **"Resolved config"** table showing exactly what will be used. It said "Using defaults", and the API key showed *Not set* while onboarding already counted the AI connection as complete, so the connection must come from the server environment or a CLI provider. That is a small inconsistency a user could find confusing.
- **Look and feel**: warm dark charcoal with a terracotta accent, generous spacing, a hamburger menu and a mobile-style layout at the pane's narrow width.

Nothing here changes the verdicts above. It confirms the three things worth copying: the **first-run wizard**, the **resolved-config panel**, and **per-purpose model overrides**.


### 14b. After onboarding was finished (second look)

I only browsed. I did not run any search, scoring or AI action. The browser pane is narrow, so I saw JobOps's **phone layout**, not the wide two-pane desktop one from its screenshots.

- **Onboarding had already discovered 108 Dutch jobs.** The tabs are *Ready* (0), *Discovered* (108), *All jobs* (108). *Ready* stays empty until you press **"Tailor discovered jobs"**, so scoring is an explicit, LLM-costing step. In our app a score is one click per job or per page.
- **Result quality, from the discovered list.** Mostly relevant (React, Java, DevOps, Android roles with salary ranges), but also visible noise: *UX Writer II* at Booking.com, a *UI/UX designer for a skincare clinic* at $55/hour, an employer shown as **"Unknown Employer"**, a *Jobgether* aggregator posting with an empty location, and a JetBrains role listing **11 cities in 8 countries** as one location. This is the cost of scraping boards: wide, but dirty. Our employer-direct data has a real company, a single location and an apply link on the employer's own site.
- **List tools**: "Select all filtered" with a selected counter (bulk actions), Filters, a **⌘K search**, status dots, and a bottom-sheet job detail on small screens. Opening a job showed a loading spinner for the whole time I looked, so I could not judge the detail view itself.
- **Resume Studio**: *Edit* and *Preview* tabs, a "Choose section" picker, a **renderer selector** (the default was "RxResume export") and a PDF preview with zoom (it was still "Rendering PDF preview" when I looked). The split between editing and previewing is by tab on a phone and side by side on a wide screen, which matches the docs.

The first three roadmap items in section 12 stay the same. This check adds one more argument for our direction: **clean, employer-direct data is a genuine lead**, and the thing to copy from them is the *experience around the data* (bulk select, command bar, onboarding, live preview), not the scraping.

## 15. Re-comparison after the redesign: CV builder and UI

Sources: JobOps public docs (v0.10.0: Resume Studio, Reactive Resume, Ghostwriter, Settings, Keyboard shortcuts). The live JobOps UI was behind its sign-in at the time of writing, so everything about JobOps here comes from the docs, not from clicking through it. Our side is from the running app and its tests.

### 15.1 CV builder

| Area | JobOps (docs) | Ours now | Verdict |
|---|---|---|---|
| Document model | Stores an exact Reactive Resume v5 document natively | Own structured CV; converts to and from RR v5 JSON | They are RR-native, we are RR-compatible |
| Editing | Left-panel field editing, save indicator | Basics, skills, tags, and full entry editor for experience, education, projects (add, drag, move, duplicate, delete, reorder and hide sections) | Roughly even on structure; they add a save indicator, we have none |
| Live preview | PDF with a "stale" marker, old PDF stays viewable | Debounced live PDF rebuild on every edit (local compiler) | Ours is more interactive |
| Templates | LaTeX (Jake-style) and Typst Classic/Compact, themes as folders | LaTeX classic, compact, modern; A4 and Letter | Even; they have a theme-folder extension point |
| AI per field | Sparkle button on headline, summary, item titles, descriptions, skill keywords; fills empty fields, Apply on filled ones | Missing | Gap |
| Per-job tailoring | Changes summary, headline, skills, project visibility; keeps headline and titles exact for ATS | Rewords summary and bullets with a fact guard that rejects new numbers and skills, keyword coverage before and after, diff view, stored encrypted per job | Ours is stricter and more transparent; they also toggle project visibility |
| Project selection | Must-include, AI-selectable pool, max projects | Missing | Gap |
| PDF per job | Generated per job, auto-regenerates when settings change, tracer links | Built on demand from the stored tailored CV; no stored PDF, no tracer links | Gap |
| Import | RR import and re-import, picture upload, DOCX and PDF via Gemini CLI | PDF, DOCX, LaTeX, RR JSON, text through a local parser | Even; they use an LLM for messy PDFs, we do not |
| Cover letter and chat | Ghostwriter drawer, one chat per job, pop-up mode, notes as context, stop and regenerate, copy | Assistant dock (minimise, close), one chat per job, CV, notes and linked e-mails as context, quick prompts, copy, clear | Even; they have stop and regenerate and Markdown rendering |
| Prompts and style | Editable prompt templates with Reset, style modes (Manual, match resume, match job language) | Writing style (tone and rules) and per-task models; prompts are not editable | Gap: prompt editing, language matching |
| Photo, rich text | Picture upload, rich descriptions | Neither | Gap |
| Undo and history | Not documented | None | Gap on both |

### 15.2 UI

| Area | JobOps (docs) | Ours now | Verdict |
|---|---|---|---|
| Navigation | Main navigation, Jobs organised by status tabs | Collapsible sidebar, top bar with command bar, theme and account menu | Ours is clearer; their status tabs on the job list are missing from ours |
| Job detail | Right-side drawers, Ghostwriter pop-up | Master-detail on wide screens, drawer on narrow ones, collapsible panels, docked assistant | Even |
| Shortcuts | `?` help overlay, j/k, 1-4 tabs, Cmd+K or `/`, p and d for PDF, Control hint bar | j/k, `/`, s, x, Cmd+K; no help overlay, no tab keys | Gap: help overlay |
| Theming | Not documented | Light, dark, system | Ours documented |
| Tests | Not assessed | 125 backend, 16 unit, 5 browser tests | Ours known |

### 15.3 What would close the gap, in order of value

1. AI sparkle per field in the editor, behind the same fact guard as tailoring.
2. Project selection per job (must-include, AI pool, max) and project visibility in tailoring.
3. Stored PDF per job with a "stale" indicator and regenerate.
4. Editable prompt templates with Reset, and language matching (resume or job language).
5. Assistant: stop and regenerate, Markdown rendering.
6. Save indicator, undo and redo, and autosave of the CV draft to the account.
7. Typst renderer option (needs the `typst` binary; not installed here).
8. `?` shortcut help overlay and status tabs on the job list.
9. LLM-assisted import for messy PDFs.
10. Photo support.

### 15.4 Live walkthrough of JobOps v0.14.0 (signed in by the user, every tab opened)

Navigation: Overview, Jobs, In Progress, Resume Studio, Tracking Inbox, Tracer Links, Visa Sponsors, Watchlist, Settings, Account. The account entry has no page of its own (the route renders blank), so it is probably a menu action.

| Tab | What it does | Notes versus ours |
|---|---|---|
| Overview | Applications per day, application to response conversion with funnel (Applied, Screening, Interview, Offer, Rejected), rolling 7-day conversion chart, response rate by source, pipeline run history; 7, 14, 30, 90 day switch | We have per-day chart and funnel; missing: conversion over time, response rate by source, run history, day-range switch |
| Jobs | Tabs Ready, Discovered, All Jobs with counts; Filters; search with Cmd+K; two-pane list and detail; Find jobs and Add a job buttons | Our list has no status tabs; no manual "add a job" |
| Job page | A full "application dossier": score, source, location, posted, outcome, projects chosen; sub-tabs Overview, Notes, Documents, Timeline, Emails, Ghostwriter; actions Start Tailoring, Upload PDF, Skip, Open listing | Ours has the same pieces as panels in one drawer; no per-job document store (upload your own PDF), no job-level notes and transcripts area |
| In Progress | Kanban with 8 stages: Applied, Recruiter screen, Assessment, Team match, Technical interview, Final round, Offer, Closed | Ours has 9 coarser stages (shortlisted to skipped); theirs is finer for interviews |
| Resume Studio | Icon rail: Live preview, Contact, Summary, Picture, Custom Fields, Education, Experience, Languages, Profiles, Projects, Skills; each section is its own route; list items have drag handle, Visible badge, edit, hide, delete, Add; edit opens a modal with Company, Location, Position, Period, Website and a rich text description (H1 to H3, bold, italic, lists, links) with an AI assistant button on Position and Description; header actions Import File, Re-import RxResume, Download PDF, Export; renderer picker and PDF zoom | See 15.5 |
| Tracking Inbox | Gmail OAuth, max messages, search days, Sync, pending review queue with approve or deny, recent sync runs | We match this and add auto-apply with undo and confidence |
| Tracer Links | Per-application tracking links: total views, unique jobs reached, human clicks, daily activity | We have nothing like it |
| Visa Sponsors | Look up a company across sponsor sources | We flag sponsors on jobs and companies but have no lookup page |
| Watchlist | Pick company boards to monitor or add a supported careers URL | We crawl everything; "follow a company" is the closest |
| Settings | AI (model per task: scoring, tailoring, project selection), Scoring, Integrations, Workspaces and Security, Display, Backups, Danger Zone | We have per-task models, style, data export and delete; no backups, no workspaces |

Resume Studio in this install showed "Preview unavailable" because the Reactive Resume API key configured there is read-only (HTTP 403). That is a JobOps setup issue, not a design flaw, but it shows the preview depends on an external renderer, while ours renders locally.

### 15.5 Resume Studio against our CV Studio

What they do better in the editor:
1. One screen area per section with an icon rail, so a long CV never becomes one long form.
2. Rich text descriptions (headings, bold, italic, lists, links) instead of plain lines.
3. An AI assistant button on individual fields.
4. Per-project use rule (exclude, let AI include, always include) edited right on the project.
5. Sections for Picture, Custom Fields, Profiles and Languages as first-class lists.
6. Re-import from Reactive Resume to replace the local copy, and PDF zoom.

What we do better:
1. The PDF preview is live and local, with no external key needed.
2. Tailoring is checked: invented numbers and skills are rejected, keyword coverage is shown, every change is a visible diff.
3. Three layouts and two paper sizes are one click apart; they pick one renderer for everything.
4. Sections can be reordered and hidden in the PDF with a single toggle.

Build list (new, from this walkthrough): icon rail with one section per view; rich text editor for descriptions; per-field AI button behind the fact guard; project use rule (exclude, AI, always); Picture, Profiles and Custom Fields sections; Overview extras (conversion over time, response by source, day-range switch); Jobs status tabs; finer interview stages; Visa lookup page; backups.


### 15.6 Status after the Resume Studio round (22 Nov 2026)

Built (own code, ideas only): icon-rail CV editor with item list and edit dialog, rich text (bold, links), per-field AI assist behind the fact guard, per-project AI rule (exclude, AI may choose, always include), per-item show/hide that reaches the PDF, custom sections, Reactive Resume connect/import/push/PDF (`/me/rr`), job page with six tabs, finer pipeline stages (recruiter screen, assessment, team match, technical interview, final round), quick-view tabs, day-range analytics, visa sponsor lookup, watchlist, Settings with integrations and display.

Not done or not verified: Reactive Resume calls follow the public v6 docs and were only tested against a fake server, so push and import may need small adjustments on a real instance; no profile picture (the layouts are text-only on purpose); no Tracer links; no "response by source" chart; Typst export; the theme button in the top bar does not follow a change made in Settings until reload.
