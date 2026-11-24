"""Gap suggestions for CV Studio: what a recruiter or an ATS looks for in a target role that your CV does not say yet.

Nothing here is applied by itself. Every proposal is pre-filled and editable, the user reads it and accepts or skips it, and only then
does it become part of the CV (and so a fact the tailoring guard allows). Proposals describe common practice, not the user's history:
the UI tells them to accept only what is true."""
import re
from . import cv as cvmod

# (term shown, regex that proves it is already in the CV, kind, bullet to add when it is experience, regex of the role it fits best)
Row = tuple[str, str, str, str, str]
MOBILE: list[Row] = [
    ("Flutter", r"\bflutter\b", "skill", "", ""), ("Dart", r"\bdart\b", "skill", "", ""),
    ("State management (BLoC, Riverpod, Provider)", r"\b(bloc|riverpod|provider|getx|redux|mobx)\b", "skill", "", ""),
    ("Unit and widget testing", r"\b(unit|widget|integration|golden)\s+test|\btest(ing|s)?\b", "experience", "Wrote unit and widget tests for business logic and key screens.", r"mobile|app|flutter"),
    ("CI/CD", r"ci\s*/\s*cd|\bjenkins\b|github actions|codemagic|fastlane|bitrise|gitlab ci", "experience", "Automated builds and releases to TestFlight and Google Play with a CI/CD pipeline.", r"mobile|app|flutter"),
    ("REST APIs", r"\brest(ful)?\b|\bapis?\b|graphql", "skill", "", ""),
    ("Clean architecture", r"clean architecture|feature[- ]driven|\bmvvm\b|\bmvc\b|\bmvi\b", "skill", "", ""),
    ("Git and code review", r"\bgit\b|code review|pull request", "experience", "Worked in Git feature branches with pull requests and code reviews.", r"mobile|app|flutter|engineer|developer"),
    ("App Store and Google Play releases", r"app store|google play|testflight|play store", "skill", "", ""),
    ("Firebase", r"\bfirebase\b", "skill", "", ""),
    ("Performance and crash monitoring", r"crashlytics|sentry|performance|profil(e|ing)|monitoring", "experience", "Monitored crashes and performance with Crashlytics or Sentry and fixed the top issues.", r"mobile|app|flutter"),
    ("Agile / Scrum", r"\bagile\b|\bscrum\b|\bkanban\b|sprint", "skill", "", ""),
    ("Accessibility and localisation", r"accessib|localis|localiz|\bi18n\b|\brtl\b", "experience", "Built bilingual, right-to-left aware screens with accessible, localised text.", r"mobile|app|flutter"),
]
SOFTWARE: list[Row] = [
    ("Python", r"\bpython\b", "skill", "", ""), ("TypeScript", r"\btypescript\b", "skill", "", ""), ("SQL / PostgreSQL", r"\b(sql|postgres(ql)?|mysql)\b", "skill", "", ""),
    ("REST API design", r"\brest(ful)?\b|\bapis?\b|graphql", "skill", "", ""),
    ("Automated testing", r"\btest(ing|s)?\b|pytest|jest|vitest|junit", "experience", "Covered services and components with automated unit and integration tests.", r"engineer|developer"),
    ("CI/CD", r"ci\s*/\s*cd|\bjenkins\b|github actions|gitlab ci", "experience", "Ran builds, tests and deployments through a CI/CD pipeline.", r"engineer|developer"),
    ("Docker", r"\bdocker\b|container", "skill", "", ""), ("Cloud (AWS / Azure / GCP)", r"\b(aws|azure|gcp|google cloud)\b", "skill", "", ""),
    ("Git and code review", r"\bgit\b|code review|pull request", "experience", "Worked in Git feature branches with pull requests and code reviews.", r"engineer|developer"),
    ("System design", r"system design|architecture|microservice", "skill", "", ""),
    ("Agile / Scrum", r"\bagile\b|\bscrum\b|\bkanban\b|sprint", "skill", "", ""),
    ("Data structures and algorithms", r"data structures|algorithms", "skill", "", ""),
]
INTERN: list[Row] = [
    ("Availability and duration", r"intern(ship)?|stage|stagiair|thesis|afstudeer", "tip", "", ""),
    ("Python", r"\bpython\b", "skill", "", ""), ("Git", r"\bgit\b", "skill", "", ""), ("SQL", r"\bsql\b", "skill", "", ""),
    ("Teamwork in a student or project team", r"team(work)?|collaborat|hackathon", "experience", "Collaborated in a small team, splitting tasks and reviewing each other's code.", r"hackathon|project|engineer|developer"),
    ("Unit testing", r"\btest(ing|s)?\b", "experience", "Wrote unit tests for the features I built.", r"engineer|developer|project"),
    ("Learning agility", r"learn(ed|ing)|self[- ]taught|course|certif|specializ", "skill", "", ""),
]
PROFILES = {"mobile": MOBILE, "software": SOFTWARE, "internship": INTERN}
LABELS = {"mobile": "Mobile / Flutter engineer", "software": "Software engineer", "internship": "Internship"}


def _slug(s: str) -> str: return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _best_role(cv: dict, hint: str) -> int:
    """The experience entry a new bullet fits best: the one mentioning the hint most, else the first (newest)."""
    exp = cv.get("experience") or []; best, score = 0, -1
    for i, b in enumerate(exp):
        s = len(re.findall(hint, " ".join([b.get("title", ""), b.get("desc", ""), " ".join(b.get("bullets", []))]), re.I)) if hint else 0
        if s > score: best, score = i, s
    return best


def _tips(cv: dict, text: str) -> list[dict]:
    t, links = [], " ".join(cv.get("links") or []).lower()
    def tip(i, msg): t.append({"id": "tip-" + i, "kind": "tip", "text": msg})
    if not (cv.get("summary") or "").strip(): tip("summary", "Add a 2-3 line summary with your target title and strongest stack: ATS and recruiters read it first.")
    if "github" not in links: tip("github", "Add your GitHub link under Profiles: code is the proof for developer roles.")
    if "linkedin" not in links: tip("linkedin", "Add your LinkedIn link under Profiles.")
    bullets = [x for b in (cv.get("experience") or []) for x in b.get("bullets", [])]
    if bullets and sum(bool(re.search(r"\d", x)) for x in bullets) < max(1, len(bullets) // 4): tip("metrics", "Few bullets contain a number. Add real figures (users, downloads, % faster, team size) where you know them.")
    dates = [b.get("date", "") for b in cv.get("experience") or []]
    if any(re.search(r"[-–—]\s*$|[-–—]\s*(20\d{2})?\s*$", d) and not re.search(r"(present|20\d{2}\s*[-–—]\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?[a-z]*\.?\s*20\d{2})", d, re.I) for d in dates if d): tip("dates", "One role has an unclear end date. Use month and year, or 'Present'.")
    if not (cv.get("location") or "").strip(): tip("location", "Add your city and country: recruiters filter by location.")
    return t


def analyse(cv: dict, target: str = "", job: dict | None = None) -> dict:
    """-> {target, label, covered, proposals, tips}. Proposals are skills to add or bullets to write; each carries an editable `text`."""
    text = cvmod.cv_text_for_gaps(cv); have = {x.lower() for x in cv.get("skills") or []}
    proposals, covered = [], []
    if job:
        for k in cvmod.job_keywords(job):
            if k.lower() in {t.lower() for t in cvmod.find_terms(text)} or k.lower() in have: covered.append(cvmod.pretty(k)); continue
            proposals.append({"id": "job-" + _slug(k), "kind": "skill", "section": "skills", "term": cvmod.pretty(k), "text": cvmod.pretty(k), "why": f"The posting asks for {cvmod.pretty(k)}; your CV does not mention it."})
        label = f"{job.get('title', 'this job')} at {job.get('company', '')}".strip()
    else:
        target = target if target in PROFILES else "software"; label = LABELS[target]
        for term, rx, kind, bullet, hint in PROFILES[target]:
            if re.search(rx, text, re.I): covered.append(term); continue
            if kind == "tip": proposals.append({"id": f"{target}-{_slug(term)}", "kind": "summary", "section": "summary", "term": term, "text": "Open to internships and graduate roles; available [from month year] for [duration] months.", "why": "Internship postings screen for availability and duration; yours says neither."}); continue
            if kind == "experience":
                i = _best_role(cv, hint); role = (cv.get("experience") or [{}])[i] if cv.get("experience") else {}
                proposals.append({"id": f"{target}-{_slug(term)}", "kind": "experience", "section": "experience", "index": i if cv.get("experience") else -1, "role": role.get("title", ""), "term": term, "text": bullet,
                                  "why": f"{LABELS[target]} postings expect {term}; your CV does not mention it."})
            else:
                proposals.append({"id": f"{target}-{_slug(term)}", "kind": "skill", "section": "skills", "term": term, "text": term, "why": f"{LABELS[target]} postings expect {term}; your CV does not mention it."})
    return {"target": target or "job", "label": label, "covered": covered, "proposals": proposals, "tips": _tips(cv, text)}
