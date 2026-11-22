import re
NL_REQ = re.compile(r"\b(dutch (is )?required|fluent (in )?dutch|nederlands(e)? (taal )?(vereist|spreken)|vloeiend nederlands|goede beheersing van de nederlandse|native dutch)\b", re.I)
NL_PLUS = re.compile(r"\b(dutch (is )?a plus|dutch (is )?an advantage|nederlands is een pre)\b", re.I)
def language(title, desc):
    t = f"{title} {desc}"
    if NL_REQ.search(t): return "dutch_required"
    if NL_PLUS.search(t): return "dutch_plus"
    # Dutch-language posting text implies Dutch needed
    if len(re.findall(r"\b(wij|jij|je|bij|een|het|voor|met|onze)\b", (desc or "")[:1500].lower())) > 12: return "dutch_required"
    return "english_ok"
INTERN_RE = re.compile(r"\b(intern|interns|internship|internships|stage|stagiair|stagiaire|stages|werkstudent|working student|thesis|afstudeer\w*|praktikum|co-?op|apprentice\w*|summer student|student assistant|studentassistent|bijbaan|meewerkstage|praktijkopdracht|studentenbaan|student job|graduation (project|internship|assignment|thesis)|master'?s? thesis|bachelor'?s? thesis|research intern|summer (internship|school)|afstudeeropdracht|afstudeerstage|stage ?plek|stageplaats)\b", re.I)
TRAINEE_RE = re.compile(r"\b(trainee|traineeship|graduate (programme|program|scheme)|management trainee|graduate programme|young professional|starters? programma|leerwerk|early[- ]careers?|graduate (trainee|job)|starterfunctie|young talent)\b", re.I)
def job_type(title, desc=""):
    t = title or ""
    if INTERN_RE.search(t) or re.search(r"interns? and trainees?|graduate programme", desc or "", re.I): return "internship"
    if TRAINEE_RE.search(t): return "traineeship"
    low = t.lower()
    if re.search(r"junior|entry|associate\b", low): return "junior"
    if re.search(r"senior|lead|principal|staff|head of|manager|director", low): return "senior"
    return "job"
DEFAULT_PROFILE = {"skills": [], "titles": [], "cities": [], "job_types": [], "english_only": False, "salary_category": "hsm_under30",
                   "country": "NL", "sectors": [], "keywords": [], "remote_ok": True, "sponsor_needed": False, "onboarded": False}


def has_signal(p: dict | None) -> bool:
    p = p or {}
    return any(p.get(k) for k in ("skills", "titles", "cities", "keywords", "sectors", "cv_skills"))


def _hits(words, hay: str) -> list[str]:
    out = []
    for w in words:
        w = w.strip().lower()
        if len(w) >= 2 and re.search(r"(?<![\w+#])" + re.escape(w) + r"(?![\w+#])", hay): out.append(w)
    return list(dict.fromkeys(out))


def fit(title, desc, location, jtype, lang, p, sector: str | None = None):
    """0-100 match of one posting against ONE user's profile: titles 30, skills (own + from the CV) 35, sector 15, place 10, keywords 10.
    Penalties for the wrong level and for Dutch when the user wants English. Returns (score, why)."""
    from . import sectors as sx
    p = p or {}
    t = (title or "").lower(); hay = f"{t} {(desc or '')[:6000].lower()}"
    titles = [x.lower() for x in p.get("titles", []) if x.strip()]
    skills = list(dict.fromkeys([x for x in p.get("skills", []) if x.strip()] + [x for x in p.get("cv_skills", []) if x.strip()]))[:60]
    words = [x for x in p.get("keywords", []) if x.strip()]
    want = p.get("sectors") or []
    score, why = 0.0, []
    th = [x for x in titles if x in t] or [x for x in titles if len(set(x.split()) & set(re.findall(r"[a-z0-9+#]+", t))) >= max(1, len(x.split()) - 1)]
    score += 30 if th else (0 if titles else 12)
    if th: why.append("title: " + th[0])
    hit = _hits(skills, hay)
    if skills: score += 35 * min(1.0, len(hit) / max(3, min(len(skills), 10)))
    else: score += 10
    if hit: why.append("skills: " + ", ".join(hit[:6]))
    if want:
        if sector in want: score += 15
        elif sector and sector != "other": score -= 20
        else:
            pk = _hits(sx.keywords(want)[:80], t)
            if pk: score += 8
    else: score += 6
    cities = [c.lower() for c in p.get("cities", []) if c.strip()]
    if cities and any(c in (location or "").lower() for c in cities): score += 10; why.append("in " + next(c for c in cities if c in (location or "").lower()).title())
    elif not cities: score += 6
    kh = _hits(words, hay)
    if words: score += 10 * min(1.0, len(kh) / max(1, min(len(words), 3)))
    if kh: why.append("keywords: " + ", ".join(kh[:4]))
    if p.get("job_types") and jtype not in p["job_types"] and jtype != "job": score -= 25            # "job" = level not stated: no penalty
    if p.get("english_only") and lang == "dutch_required": score -= 40; why.append("Dutch required")
    elif lang == "dutch_required": why.append("Dutch required")
    return max(0, min(100, round(score))), "; ".join(why) or "no profile signal yet"
