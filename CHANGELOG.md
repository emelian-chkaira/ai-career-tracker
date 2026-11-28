# Changelog

All notable changes to AI Career Tracker. Versions follow [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.
The current version is also shown in the app (sidebar, "What's new") and by `GET /api/v1/version`.

To release: add an entry here, then set the same number in `backend/app/version.py` and `frontend/package.json` (a test checks all three agree).

## [1.2.0] - 2026-11-28

### Added
- A Country filter directly on the Jobs and Internships filter bar, with a search box. In My feed it replaces your preferred places until you clear it.

## [1.1.0] - 2026-11-26

### Added
- A welcome guide that opens by itself on a fresh installation.
- Several crawler workers can run side by side, with a worker list and the reason a task is waiting.
- Posting dates are read from the employer's own page.

### Changed
- Jobs show the employer's posting date or "Unknown date". The date filter leaves unknown dates out and date ordering puts them last.
- New sign-in page: worldwide search, a dark job preview and a gently moving background.
- Clearer setup instructions; stopping the app now stops the crawler too.

### Fixed
- Google sign-in now removes the password and sessions of an account whose e-mail address was never confirmed.

## [1.0.2] - 2026-11-24

### Added
- CV Studio library: keep several CVs and several cover letters per account, with folders, rename, duplicate, delete and one default scoring CV.
- Upload several CVs at once; each CV and each letter has its own PDF.
- Score a job with a CV you choose (job panel and "AI score best 60"); the score shows which CV it used.
- AI assistant in CV Studio: give it a prompt and it edits the selected CV or cover letter, shows every change, and saves in place or as a copy in a folder. Opening CV Studio from a job suggests changes for that posting.
- AI cover letters are written from your prompt, your CV and your own saved letters, in your voice.
- "My CV" layout that matches the author's own CV, and cover letters as PDF in the same look.
- Version number and this changelog inside the app.

### Changed
- One button system across the app: same height, padding and corner radius everywhere.
- CV Studio side bar has more room.
- Jobs page redesign: search modes, cleaner list, AI-score-only matches, NL IND labels.

### Fixed
- PDF import: skill groups with bold labels are read correctly and duplicate header links are folded.

## [1.0.1] - 2026-11-22

### Added
- Crawler page with live status, pause and resume, six tabs and grouped tasks.
- Job boards (LinkedIn, Indeed, Glassdoor, Google Jobs) through JobSpy; one role, one job.
- Crawl memory per employer, dead-link removal and a recency window.
- CV Studio workspace, AI fit scoring, per-job CV tailoring, application tracking and the assistant.
- Per-user feed with sectors, countries and regions; one-click setup dialog; command bar and shortcuts.

### Changed
- Renamed to AI Career Tracker with a standard dark theme and shared components.
- README rebuilt with architecture and technical infographics.

## [1.0.0] - 2026-11-18

### Added
- First release: employer career-page crawler, hybrid search (PostgreSQL full text plus pgvector), accounts with Firebase sign-in, Gmail inbox classification, production deployment (Docker, Render, Oracle) and Firebase guide.
