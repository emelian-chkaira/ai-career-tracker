"""One role, one job.

Employers publish the same role many times: once per city ("Projektleiter (m/w/d)" in Mainz, Munich and Mannheim), once per store
("Winkelmedewerker Amsterdam (24 uur)", "Winkelmedewerker Utrecht (32 uur)"), and job boards repeat it again. Generic career-page
readers also pick up navigation links ("Skip to main content", "mehr Informationen ›") as if they were titles.

  role_key(company, title)  the identity of a role: the title without places, gender tags, hours/FTE, prefixes, case or punctuation.
                            Postings with the same key at the same employer are ONE job with several locations / links.
  nav_label(title)          True for link texts that are not job titles.
  title_from_url(url)       recovers a real title from the link ('/jobs/bauleiter-hochbau' -> 'Bauleiter Hochbau') when the label was junk.
"""
import hashlib, html, re, unicodedata
from urllib.parse import unquote, urlparse

_R = lambda p: re.compile(p, re.I)
GENDER = _R(r"\(\s*(?:[mwfdxhvai*]\s*[/|,]\s*){1,3}[mwfdxhvai*]\s*\)|\b(?:m|w|f|h)\s*/\s*(?:w|f|m|v|h)\s*/\s*(?:d|x|v|i|div)\b|\(\s*(?:all genders?|alle geschlechter|gn\*?|genderneutral|any gender)\s*\)|\bm/f/x\b")
HOURS = _R(r"\(?\b\d{1,2}(?:[.,]\d)?\s*(?:[-–]\s*\d{1,2}(?:[.,]\d)?\s*)?(?:uur|hours?|hrs|std\.?|stunden|h)\b(?:\s*(?:per|p/?)\s*(?:week|wk|w))?\)?|\(?\b[01](?:[.,]\d{1,2})?\s*(?:[-–]\s*[01](?:[.,]\d{1,2})?\s*)?fte\b\)?|\b(?:full|part)[- ]?time\b|\bparttime\b|\bfulltime\b|\bvoltijd\b|\bdeeltijd\b|\bteilzeit\b|\bvollzeit\b|\bminijob\b")
PREFIX = _R(r"^\s*(?:vacature|vacancy|job|stellenangebot|stelle|offre d'emploi|we are hiring|we're hiring|hiring)\s*[:\-–|]\s*")
WORKMODE = _R(r"\b(?:remote|hybrid|hybride|on[- ]?site|thuiswerk|homeoffice|home office|anywhere|worldwide|emea|europe)\b")
NAV = _R(r"^\W*(?:skip to (?:main )?content|skip navigation|read more|lees (?:meer|verder)|meer (?:info|informatie|lezen|weten)|mehr(?: informationen| erfahren| infos?)?|weiterlesen|"
         r"learn more|more (?:info|information|details)|view (?:job|vacancy|details|position|all(?: jobs| vacancies)?)|see (?:job|details|all jobs)|bekijk(?: de| alle)? vacatures?|"
         r"alle vacatures|overige vacatures|onze vacatures|vacatures|solliciteer(?: nu| direct| hier)?|apply(?: now| here| online)?|jetzt bewerben|zur stelle|zum job|stellenangebote|"
         r"details|open (?:positions|vacancies|roles)|jobs|careers?|werken bij|search jobs|job alert|job alerts|home|menu|contact|back|terug|zurück|next|previous|volgende|vorige|"
         r"en savoir plus|postuler|ver oferta|saiba mais|leggi (?:di più|tutto)|scopri di più|bewerben|stelle ansehen|job ansehen|cookies?|privacy(?: policy| statement)?|"
         r"click here|klik hier|hier klicken|show more|toon meer|load more|(?:view|see) job (?:&|and) apply|(?:job ?)?details? ansehen|job details|stellendetails|"
         r"zur stellenanzeige|stellenanzeige|jetzt ansehen|ansehen|mehr details|more|meer|vacature bekijken|bekijk|view|apply for this job|apply for job)\W*$")
JOB_NOUN = _R(r"(engineer|developer|ontwikkelaar|entwickler|manager|specialist|consultant|adviseur|berater|analyst|analist|architect|designer|planner|coordinator|co[öo]rdinator|"
              r"assistant|assistent|medewerker|mitarbeiter|technicus|techniker|monteur|meister|leiter|leider|lead|director|officer|scientist|researcher|onderzoeker|"
              r"\bintern(?!ation)|internship|\bstage\b|stagiair|trainee|werkstudent|ausbildung|apprentice|nurse|verpleeg|docent|teacher|lehrer|accountant|controller|recruiter|"
              r"maurer|zimmer|polier|bauleiter|elektriker|mechani|chauffeur|driver|operator|verkoper|verkäufer|sales|support|administrat|secretar|tester|programmer|"
              r"owner|master|expert|head of|chef|kok|koch|cook|barista|schilder|lasser|timmerman|installateur|electricien|werkvoorbereider|uitvoerder|calculator|"
              r"technician|worker|staff|clerk|agent|representative|associate|executive|buyer|inkoper|cashier|therapist|physician|pharmacist|doctor|arts\b|surgeon|"
              r"welder|electrician|carpenter|plumber|painter|cleaner|receptionist|writer|editor|producer|artist|photographer|translator|tutor|coach|trainer|"
              r"advisor|auditor|actuary|economist|lawyer|counsel|paralegal|supervisor|foreman|inspector|surveyor|draftsman|drafter|steward|hostess|host\b|"
              r"fachkraft|kaufmann|kauffrau|referent|sachbearbeiter|bediener|helfer|pfleger|erzieher|verkäufer|disponent|pilot|crew)")
NOT_JOB_SLUG = _R(r"\b(life|culture|diversity|women|benefits|why|about|story|stories|team|teams|students?|graduates?|apprentices|interns|events?|faq|blog|news|locations?|"
                  r"departments?|working|work|join|us|our|people|values|process|hiring|how)\b")
_place_rx = None


def _places():
    """One pattern for every place name we know (countries, their other names, cities, Dutch towns)."""
    global _place_rx
    if _place_rx is None:
        from . import nl, places
        words = {w.lower() for code, (name, alts, cities) in places.COUNTRIES.items() for w in [name, *alts, *cities] if len(w) >= 3}
        words |= {c.replace("-", " ") for c in nl.CITIES if len(c) >= 4}
        alt = "|".join(re.escape(w).replace(r"\ ", r"[ -]") for w in sorted(words, key=len, reverse=True))
        _place_rx = re.compile(r"(?<![\w])(?:" + alt + r")(?![\w])", re.I)
    return _place_rx


def clean(title: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(title or "").replace("\xa0", " ")).strip()


def canonical(title: str) -> str:
    """The role a title names, without where, when or for whom: 'Senior Terminplaner Industry (m/w/d) - Munich' -> 'senior terminplaner industry'."""
    t = PREFIX.sub("", clean(title))
    t = GENDER.sub(" ", t); t = HOURS.sub(" ", t); t = WORKMODE.sub(" ", t); t = _places().sub(" ", t)
    t = re.sub(r"[^\w+#]+", " ", t.lower().replace("&", " and "))
    t = re.sub(r"\b(?:the|in|at|bei|bij|in de|voor|for|und|and|en)\s*$", "", t.strip())   # dangling words left by a removed place: 'Store Manager in'
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))   # Industriële = Industriele
    return " ".join(t.split())


def similar(a: str, b: str) -> bool:
    """Do two titles name the same role? Same canonical words, or nearly (most words shared)."""
    x, y = set(canonical(a).split()), set(canonical(b).split())
    if not x or not y: return False
    return x == y or len(x & y) / len(x | y) >= 0.7


def role_key(company_id: int, title: str) -> str:
    return hashlib.sha1(f"{company_id}|{canonical(title) or clean(title).lower()}".encode()).hexdigest()[:16]


def nav_label(title: str) -> bool:
    t = clean(title)
    return not t or len(t) < 3 or not re.search(r"[A-Za-zÀ-ž]{2}", t) or bool(NAV.match(t))


def title_from_url(url: str) -> str | None:
    """'/jobs/bauleiter-hochbau' -> 'Bauleiter Hochbau'. Only when the link clearly names a job (a job noun, not 'life-at-airbus')."""
    segs = [s for s in unquote(urlparse(url or "").path).split("/") if s]
    if not segs: return None
    seg = re.sub(r"\.(html?|php|aspx?)$", "", segs[-1], flags=re.I)                     # only the last part: the folders above are categories
    words = [w for w in re.split(r"[-_+.\s]+", seg) if w and not re.fullmatch(r"\d+|[0-9a-f]{8,}|[a-z]?\d+[a-z]?|id|job|jobs|vacature|vacancy|stelle|en|nl|de|fr", w, re.I)]
    while len(words) > 1 and len(words[-1]) == 1: words.pop()                    # 'servicemonteur-industrie-v': a cut-off id, not part of the title
    if not words or len(" ".join(words)) < 4: return None
    cand = " ".join(w if w.isupper() else w.capitalize() for w in words)
    if len(words) == 1 and re.fullmatch(r"(?i)(apprentices|interns|internships|students|graduates|trainees|vacancies|vacatures|careers|openings|positions|stellen|jobs)", words[0]): return None
    if NOT_JOB_SLUG.search(cand) and not JOB_NOUN.search(cand): return None
    return cand[:200] if JOB_NOUN.search(cand) else None


def sane_location(loc: str | None) -> str:
    """Some sites put salary or description text in the location field ('39576, Stendal 15.15 - 15.15 STUNDE Die Gehaltsspanne ...').
    Keep the parts that name a place; short clean locations are returned as they are."""
    s = clean(loc or "")
    if len(s) <= 80 and not re.search(r"[✔•·]|\b(?:stunde|gehalt|salary|werken aan)\b", s, re.I): return s
    from . import places
    keep = []
    for part in re.split(r"[,;|\n]", s):
        m = re.match(r"^[\W\d_]*([A-Za-zÀ-ž][A-Za-zÀ-ž .'()/-]{1,40}?)(?=\s+\d|\s{2}|$|\s+[a-zäöü]+\s)", part.strip() + " ")
        cand = (m.group(1) if m else "").strip(" .-")
        if cand and (places.parse(cand).countries or places.city_of(cand)): keep.append(cand)
        if len(keep) == 2: break
    return ", ".join(keep)
