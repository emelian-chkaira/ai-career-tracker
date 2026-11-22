"""Sectors: which field of work a posting belongs to, plus the presets a user picks during setup.

The catalogue grew from tech employers, so `tech` is the richest sector (it keeps its finer `domain`: mobile, backend, data, ...).
Every other posting the crawler already stores gets a sector too, so an architect, a nurse or an accountant sees postings of their own field.

classify() looks at the TITLE only (descriptions mention everything). Rules run in order; the first match wins.
A rule marked `guard` is skipped when the title is clearly a software role ("Sales Engineer" is sales, "Sales Platform Developer" is tech)."""
import re
from . import nl

_R = lambda p: re.compile(p, re.I)
SOFTWARE = _R(r"\b(it|ict|data|developer|software|devops|programmer|programmeur|ontwikkelaar|data engineer|data scientist|machine learning|frontend|front-end|backend|back-end|full[- ]?stack|sre|cloud engineer)\b")
IT_ARCHITECT = _R(r"\b(software|solutions?|cloud|data|enterprise|it|ict|security|technical|application|integration|domain|platform|systems?|network|infrastructure|salesforce|sap|erp|crm|azure|aws|customer|klant|iam|workplace|automation|api|business|technology|digital)\b[\w /&-]{0,25}architect")

# key: (label, short description, title rule, guarded?, suggested titles, suggested skills / keywords)
PRESETS: dict[str, dict] = {
    "tech": dict(label="Software, IT & data", blurb="Developers, data, DevOps, security, IT support, product and UX.",
                 titles=["Software Engineer", "Backend Developer", "Frontend Developer", "Mobile Developer", "Data Engineer", "Data Scientist", "DevOps Engineer", "QA Engineer", "Product Manager", "UX Designer"],
                 skills=["Python", "Java", "TypeScript", "React", "Kotlin", "SQL", "AWS", "Docker", "Kubernetes", "Machine learning"]),
    "architecture": dict(label="Architecture & construction", blurb="Architects, urban and landscape design, BIM, construction and site management.",
                         titles=["Architect", "Junior Architect", "Landscape Architect", "Interior Architect", "Urban Designer", "BIM Modeller", "Project Architect", "Construction Manager", "Werkvoorbereider", "Uitvoerder"],
                         skills=["Revit", "ArchiCAD", "AutoCAD", "Rhino", "Grasshopper", "SketchUp", "BIM", "Building codes", "Sustainable design", "Bouwbesluit"]),
    "engineering": dict(label="Engineering & manufacturing", blurb="Mechanical, electrical, civil, process and mechatronics; production and maintenance.",
                        titles=["Mechanical Engineer", "Electrical Engineer", "Civil Engineer", "Process Engineer", "Mechatronics Engineer", "Structural Engineer", "Quality Engineer", "Maintenance Engineer", "Test Engineer", "Field Service Engineer"],
                        skills=["SolidWorks", "CATIA", "Siemens NX", "MATLAB", "PLC", "FEA", "Lean", "Six Sigma", "GD&T", "Root cause analysis"]),
    "design": dict(label="Design & creative", blurb="Graphic, visual, motion and brand design, video, photography, copy.",
                   titles=["Graphic Designer", "Visual Designer", "Motion Designer", "Art Director", "Brand Designer", "Illustrator", "Video Editor", "Copywriter"],
                   skills=["Figma", "Adobe Illustrator", "Photoshop", "InDesign", "After Effects", "Premiere Pro", "Typography", "Branding"]),
    "finance": dict(label="Finance & accounting", blurb="Accounting, control, audit, tax, treasury and financial analysis.",
                    titles=["Accountant", "Financial Controller", "Financial Analyst", "Auditor", "Tax Advisor", "Treasury Analyst", "Credit Risk Analyst", "Payroll Specialist"],
                    skills=["Excel", "IFRS", "SAP FI", "Exact", "AFAS", "Power BI", "Financial modelling", "Audit"]),
    "sales_marketing": dict(label="Sales & marketing", blurb="Sales, account and business development, marketing, content and communication.",
                            titles=["Account Manager", "Business Developer", "Sales Engineer", "Marketing Manager", "Content Marketer", "SEO Specialist", "Communication Advisor", "Customer Success Manager"],
                            skills=["CRM", "Salesforce", "HubSpot", "Google Ads", "SEO", "Negotiation", "Content strategy", "B2B sales"]),
    "operations": dict(label="Operations, logistics & supply chain", blurb="Supply chain, planning, purchasing, warehouse and production operations.",
                       titles=["Supply Chain Planner", "Logistics Coordinator", "Buyer", "Procurement Specialist", "Operations Manager", "Production Planner", "Warehouse Supervisor"],
                       skills=["SAP MM", "ERP", "S&OP", "Inventory management", "Lean", "Excel", "Procurement", "Forecasting"]),
    "healthcare": dict(label="Healthcare & life sciences", blurb="Care, nursing, medical, pharmacy, lab and clinical research.",
                       titles=["Nurse", "Verpleegkundige", "Physiotherapist", "Doctor", "Pharmacist", "Lab Technician", "Clinical Research Associate", "Psychologist"],
                       skills=["Patient care", "BIG registration", "GCP", "Laboratory", "Clinical trials", "Medical devices"]),
    "education": dict(label="Education & research", blurb="Teaching, lecturing, PhD and postdoc positions, research staff.",
                      titles=["Teacher", "Docent", "Lecturer", "PhD Candidate", "Postdoc", "Researcher", "Teaching Assistant"],
                      skills=["Teaching", "Curriculum design", "Research", "Academic writing", "Statistics"]),
    "people_legal": dict(label="HR, legal & office", blurb="HR, recruitment, legal, compliance, office and administration.",
                         titles=["HR Advisor", "Recruiter", "Talent Acquisition Specialist", "Legal Counsel", "Compliance Officer", "Office Manager", "Management Assistant"],
                         skills=["Recruitment", "Employment law", "AFAS", "Workday", "GDPR", "Contract law"]),
    "hospitality_retail": dict(label="Hospitality, retail & services", blurb="Hotels, restaurants, shops, customer service and facility work.",
                               titles=["Store Manager", "Chef", "Hotel Receptionist", "Customer Service Agent", "Facility Coordinator"],
                               skills=["Customer service", "Retail", "Hospitality", "Food safety"]),
    "other": dict(label="Other", blurb="Everything else.", titles=[], skills=[]),
}
SECTORS = tuple(PRESETS)

# (sector, title rule, guard: skip when the title is clearly software). Order matters.
RULES: list[tuple[str, re.Pattern, bool]] = [
    ("architecture", _R(r"\b(architect|architecte|architectuur|landschapsarchitect|interieurarchitect|stedenbouw\w*|urban (design|planner)|urbanist|bim[- ]?(modell?er|coordinator|manager|engineer|specialist)?|revit|bouwkund\w*|werkvoorbereid\w*|uitvoerder|calculator bouw|projectleider bouw|construction (manager|engineer|site)|infra|gww|wegenbouw|grondwerk\w*|riool\w*|betonbouw|bouw\w*|site manager|quantity surveyor|aannem\w*|tekenaar|draftsman|draughtsman|interior design\w*)\b"), True),
    ("healthcare", _R(r"\b(nurse|nursing|verpleeg\w*|verzorgende|zorg\w*|ggz|arts|doctor|physician|huisarts|fysio\w*|physiotherap\w*|pharmac\w*|apothe\w*|psycholo\w*|therapeut|therapist|clinical|klinisch|medical (doctor|specialist|advisor)|lab(oratory)? (technician|analyst|analist)|analist laboratorium|dental|tandarts|verloskund\w*|care (worker|assistant)|caregiver)\b"), True),
    ("people_legal", _R(r"\b(recruit\w*|talent acquisition|hr\b|hrm|human resources|people (partner|advisor|operations)|payroll|salarisadministr\w*|legal|lawyer|jurist|advocaat|counsel|paralegal|compliance|privacy officer|notar\w*|office manager|management assistant|executive assistant|secreta\w*|receptionist|receptioniste|administratief|administrative)\b"), True),
    ("finance", _R(r"\b(accountant|accounting|controller|controlling|finance|financial|fiscal\w*|tax\b|belasting\w*|audit\w*|treasur\w*|boekhoud\w*|bookkeep\w*|credit|crediteuren|debiteuren|accounts (payable|receivable)|fp&a|actuar\w*|fixed assets|intercompany)\b"), True),
    ("sales_marketing", _R(r"\b(sales|sdr|bdr|account (executive|director)|rvp|account manager|accountmanager|business develop\w*|key account|commercial|commercieel|verkoop\w*|vertrieb|marketing|marketeer|content|copywriter|seo|sea\b|social media|communicat\w*|pr\b|public relations|brand manager|customer success|partnerships?)\b"), True),
    ("operations", _R(r"\b(supply chain|logisti\w*|warehouse|magazijn\w*|planner|planning|inkoop\w*|inkoper|buyer|procurement|purchas\w*|operations (manager|coordinator|specialist|lead)|production (operator|planner|lead|manager)|productiemedewerker|operator|chauffeur|driver|fahrer|auslieferung\w*|entlader|koerier|courier|bezorg\w*|voorraad\w*|lager\w*|expedit\w*|transport|hse|ehs|safety officer)\b"), True),
    ("engineering", _R(r"\b(mechanical|electrical|civil|civie\w*|lasser|welder|beveiligingstechniek|structural|process engineer|chemical engineer|mechatronic\w*|werktuigbouw\w*|elektrotechn\w*|installatietechn\w*|maintenance|onderhoud\w*|monteur|technician|technicus|service engineer|field service|calibration|manufacturing|optical engineer|optics|physicist|hydraulic|hvac|energy engineer|high voltage|hoogspanning|quality engineer|manufacturing engineer|product engineer|r&d engineer)\b"), True),
    ("hospitality_retail", _R(r"\b(chef|kok|cook|barista|waiter|waitress|bediening|horeca|hotel|retail|store|winkel\w*|cashier|kassa\w*|customer service|klantenservice|call ?center|facilit\w*|schoonmaak\w*|cleaner|host(ess)?)\b"), True),
    ("tech", None, False),                                                                       # nl.category(title) == "tech"
    ("education", _R(r"\b(teacher|docent|leraar|lerares|lecturer|professor|onderwijs\w*|tutor|phd|ph\.d|postdoc|post-doc|promovendus|research (assistant|associate|fellow)|onderzoeker|researcher)\b"), False),
    ("design", _R(r"\b(graphic|grafisch|visual designer|motion designer|art director|illustrat\w*|brand designer|video editor|videograph\w*|photograph\w*|fotograaf|animator|3d artist)\b"), False),
]


def classify(title: str) -> str:
    t = (title or "").strip()
    if not t: return "other"
    software = bool(SOFTWARE.search(t)) or bool(IT_ARCHITECT.search(t))
    for sector, rx, guard in RULES:
        if rx is None:
            if nl.category(t) == "tech": return "tech"
            continue
        if guard and software: continue
        if rx.search(t): return sector
    return "other"


def category_of(sector: str) -> str: return "tech" if sector == "tech" else "other"


def keywords(sectors: list[str]) -> list[str]:
    """Words that mark a posting as belonging to the user's chosen sectors (used by the profile match score)."""
    out: list[str] = []
    for s in sectors or []:
        p = PRESETS.get(s)
        if p: out += [x.lower() for x in p["titles"] + p["skills"]]
    return list(dict.fromkeys(out))


def public() -> list[dict]:
    return [dict(key=k, label=v["label"], blurb=v["blurb"], titles=v["titles"], skills=v["skills"]) for k, v in PRESETS.items() if k != "other"]


# ------------------------------------------------------------------ country of a posting (kept for migration 0012; places.py is the real parser)
def country_of(location: str | None) -> str:
    from . import places
    return places.parse(location).country or "NL"
