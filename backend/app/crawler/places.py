"""Where is a job? Countries, regions, work mode (on-site / hybrid / remote) and who a remote job is open to.

Locations from career sites look like "Berlin, de", "DE-Germany-Remote", "Amsterdam, Netherlands; Prague, Czech Republic; Remote - Europe",
"Remote in the US", "Dubai - United Arab Emirates" or just "Riyadh". parse() turns any of these into:
    countries    every country the posting names, in order (ISO 3166 alpha-2)
    work_mode    "remote" | "hybrid" | "onsite"
    remote_scope who may work remotely: a REGION key ("europe", "emea", "world", ...) or None (= the countries listed)
Countries we do not cover (US, India, ...) are still recognised, so their postings can be told apart and skipped."""
import re
from dataclasses import dataclass, field

# code: (English name, [other names, demonym-ish words, native spellings], [main cities])
COUNTRIES: dict[str, tuple[str, list[str], list[str]]] = {
    # ---- Benelux
    "NL": ("Netherlands", ["nederland", "holland", "the netherlands", "nld"], []),                       # NL cities come from nl.py (hundreds)
    "BE": ("Belgium", ["belgie", "belgië", "belgique", "belgien"], ["brussels", "brussel", "bruxelles", "antwerp", "antwerpen", "anvers", "ghent", "gent", "gand", "leuven", "louvain", "liege", "liège", "mechelen", "bruges", "brugge", "namur", "charleroi", "hasselt", "kortrijk", "mons", "wavre", "zaventem", "diegem"]),
    "LU": ("Luxembourg", ["luxemburg", "lëtzebuerg"], ["luxembourg city", "esch-sur-alzette", "kirchberg"]),
    # ---- DACH
    "DE": ("Germany", ["deutschland", "allemagne", "duitsland", "germania", "niemcy"], ["berlin", "munich", "münchen", "muenchen", "hamburg", "frankfurt", "cologne", "köln", "koeln", "düsseldorf", "dusseldorf", "duesseldorf", "stuttgart", "leipzig", "dresden", "hannover", "hanover", "nuremberg", "nürnberg", "nuernberg", "bremen", "essen", "dortmund", "bonn", "karlsruhe", "mannheim", "heidelberg", "aachen", "münster", "freiburg", "augsburg", "wiesbaden", "mainz", "darmstadt", "potsdam", "kiel", "regensburg", "ingolstadt", "wolfsburg", "erlangen", "jena", "kelsterbach", "schönefeld", "walldorf", "garching", "eschborn", "ulm", "bochum", "duisburg", "kassel", "braunschweig", "rostock", "magdeburg", "saarbrücken", "tamm"]),
    "AT": ("Austria", ["österreich", "osterreich", "oesterreich", "autriche"], ["vienna", "wien", "graz", "linz", "salzburg", "innsbruck", "klagenfurt"]),
    "CH": ("Switzerland", ["schweiz", "suisse", "svizzera", "zwitserland"], ["zurich", "zürich", "zuerich", "geneva", "genève", "geneve", "genf", "basel", "bern", "lausanne", "lucerne", "luzern", "zug", "lugano", "winterthur", "st. gallen", "baar", "schaffhausen"]),
    # ---- UK & Ireland
    "GB": ("United Kingdom", ["uk", "u.k.", "great britain", "britain", "england", "scotland", "wales", "northern ireland",
                           "west midlands", "east midlands", "greater london", "greater manchester", "merseyside", "west yorkshire", "south yorkshire", "north yorkshire", "east yorkshire", "tyne and wear",
                           "surrey", "kent", "essex", "sussex", "east sussex", "west sussex", "hampshire", "hertfordshire", "berkshire", "buckinghamshire", "oxfordshire", "cambridgeshire", "bedfordshire",
                           "lancashire", "cheshire", "staffordshire", "derbyshire", "nottinghamshire", "leicestershire", "lincolnshire", "northamptonshire", "warwickshire", "worcestershire", "gloucestershire",
                           "wiltshire", "somerset", "dorset", "devon", "cornwall", "norfolk", "suffolk", "cumbria", "northumberland", "county durham", "shropshire", "herefordshire", "middlesex", "gloucester"], ["london", "manchester", "edinburgh", "glasgow", "birmingham", "bristol", "leeds", "cambridge", "oxford", "belfast", "cardiff", "liverpool", "newcastle", "nottingham", "sheffield", "reading", "brighton", "milton keynes", "aberdeen", "southampton", "york"]),
    "IE": ("Ireland", ["éire", "eire", "republic of ireland"], ["dublin", "cork", "galway", "limerick", "waterford"]),
    # ---- Nordics & Baltics
    "DK": ("Denmark", ["danmark", "denemarken"], ["copenhagen", "københavn", "kobenhavn", "aarhus", "odense", "aalborg"]),
    "SE": ("Sweden", ["sverige", "zweden", "schweden"], ["stockholm", "gothenburg", "göteborg", "goteborg", "malmö", "malmo", "uppsala", "linköping", "lund"]),
    "NO": ("Norway", ["norge", "noorwegen", "norwegen"], ["oslo", "bergen, norway", "trondheim", "stavanger"]),
    "FI": ("Finland", ["suomi", "finnland"], ["helsinki", "espoo", "tampere", "oulu", "turku", "vantaa"]),
    "IS": ("Iceland", ["ísland"], ["reykjavik", "reykjavík"]),
    "EE": ("Estonia", ["eesti"], ["tallinn", "tartu"]),
    "LV": ("Latvia", ["latvija"], ["riga", "rīga"]),
    "LT": ("Lithuania", ["lietuva"], ["vilnius", "kaunas"]),
    # ---- Southern Europe
    "FR": ("France", ["frankrijk", "frankreich", "francia"], ["paris", "lyon", "marseille", "toulouse", "nice", "nantes", "lille", "bordeaux", "strasbourg", "montpellier", "rennes", "grenoble", "sophia antipolis", "la défense", "la defense", "nanterre", "boulogne-billancourt", "issy-les-moulineaux"]),
    "ES": ("Spain", ["españa", "espana", "spanje", "spanien", "espagne"], ["madrid", "barcelona", "valencia", "seville", "sevilla", "malaga", "málaga", "bilbao", "zaragoza", "alicante", "palma", "las palmas"]),
    "PT": ("Portugal", [], ["lisbon", "lisboa", "porto", "braga", "coimbra", "aveiro", "faro"]),
    "IT": ("Italy", ["italia", "italië", "italien", "italie"], ["milan", "milano", "rome", "roma", "turin", "torino", "naples", "napoli", "bologna", "florence", "firenze", "genoa", "genova", "venice", "venezia", "verona", "padua", "padova", "bari", "catania", "palermo", "trieste", "pisa", "brescia", "bergamo", "modena", "parma"]),
    "GR": ("Greece", ["hellas", "ελλάδα", "griekenland"], ["athens", "athína", "thessaloniki", "patras", "heraklion"]),
    "MT": ("Malta", [], ["valletta", "sliema", "st julian's", "st. julian's", "gzira", "birkirkara"]),
    "CY": ("Cyprus", ["kypros", "cyprus"], ["nicosia", "limassol", "larnaca", "paphos"]),
    # ---- Central & Eastern Europe
    "PL": ("Poland", ["polska", "polen", "pologne"], ["warsaw", "warszawa", "krakow", "kraków", "cracow", "wroclaw", "wrocław", "gdansk", "gdańsk", "poznan", "poznań", "lodz", "łódź", "katowice", "gdynia", "lublin", "szczecin", "bydgoszcz"]),
    "CZ": ("Czech Republic", ["czechia", "česko", "cesko", "tsjechië"], ["prague", "praha", "brno", "ostrava", "plzen", "plzeň"]),
    "SK": ("Slovakia", ["slovensko"], ["bratislava", "kosice", "košice", "zilina", "žilina"]),
    "HU": ("Hungary", ["magyarország", "magyarorszag", "hongarije"], ["budapest", "debrecen", "szeged", "pécs", "gyor", "győr"]),
    "RO": ("Romania", ["românia", "roemenië"], ["bucharest", "bucurești", "bucuresti", "cluj-napoca", "cluj", "iasi", "iași", "timisoara", "timișoara", "brasov", "brașov"]),
    "BG": ("Bulgaria", ["българия"], ["sofia", "plovdiv", "varna", "burgas"]),
    "SI": ("Slovenia", ["slovenija"], ["ljubljana", "maribor"]),
    "HR": ("Croatia", ["hrvatska", "kroatië"], ["zagreb", "split", "rijeka", "osijek"]),
    "RS": ("Serbia", ["srbija"], ["belgrade", "beograd", "novi sad", "nis", "niš"]),
    "BA": ("Bosnia and Herzegovina", ["bosnia"], ["sarajevo", "banja luka"]),
    "ME": ("Montenegro", ["crna gora"], ["podgorica"]),
    "MK": ("North Macedonia", ["macedonia"], ["skopje"]),
    "AL": ("Albania", ["shqipëria"], ["tirana", "tiranë"]),
    "XK": ("Kosovo", [], ["pristina", "prishtina"]),
    "UA": ("Ukraine", ["україна", "ukraina"], ["kyiv", "kiev", "lviv", "kharkiv", "odesa", "odessa", "dnipro"]),
    "MD": ("Moldova", [], ["chisinau", "chișinău"]),
    "TR": ("Turkey", ["türkiye", "turkiye", "turkije"], ["istanbul", "ankara", "izmir", "i̇zmir", "bursa", "antalya"]),
    # ---- Middle East (GCC first)
    "AE": ("United Arab Emirates", ["uae", "u.a.e.", "emirates", "الإمارات"], ["dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah", "al ain"]),
    "SA": ("Saudi Arabia", ["ksa", "kingdom of saudi arabia", "saudi", "السعودية"], ["riyadh", "jeddah", "dammam", "khobar", "al khobar", "dhahran", "mecca", "makkah", "medina", "madinah", "neom", "jubail", "tabuk"]),
    "QA": ("Qatar", ["قطر"], ["doha", "lusail", "al rayyan", "al wakrah"]),
    "KW": ("Kuwait", ["الكويت"], ["kuwait city"]),
    "BH": ("Bahrain", ["البحرين"], ["manama"]),
    "OM": ("Oman", ["sultanate of oman", "عمان"], ["muscat", "salalah", "sohar"]),
    "JO": ("Jordan", ["الأردن"], ["amman", "irbid", "aqaba"]),
    "LB": ("Lebanon", ["لبنان"], ["beirut"]),
    "IL": ("Israel", [], ["tel aviv", "tel-aviv", "jerusalem", "haifa", "herzliya", "ramat gan", "petah tikva", "beersheba"]),
    "IQ": ("Iraq", [], ["baghdad", "erbil", "basra"]),
    # ---- Africa
    "EG": ("Egypt", ["مصر"], ["cairo", "alexandria", "giza", "new cairo", "6th of october"]),
    "MA": ("Morocco", ["maroc", "المغرب"], ["casablanca", "rabat", "marrakech", "tangier", "tanger", "fes", "fès"]),
    "TN": ("Tunisia", ["tunisie"], ["tunis", "sfax", "sousse"]),
    "DZ": ("Algeria", ["algérie"], ["algiers", "alger", "oran"]),
    "ZA": ("South Africa", ["rsa"], ["johannesburg", "cape town", "durban", "pretoria", "sandton", "stellenbosch"]),
    "NG": ("Nigeria", [], ["lagos", "abuja", "ibadan"]),
    "KE": ("Kenya", [], ["nairobi", "mombasa"]),
    "GH": ("Ghana", [], ["accra", "kumasi"]),
    "RW": ("Rwanda", [], ["kigali"]),
    # ---- recognised so they can be told apart (not offered as a place to search)
    "US": ("United States", ["usa", "u.s.", "u.s.a.", "united states of america", "us-remote", "california", "texas", "new york state", "florida", "illinois", "massachusetts", "washington state", "georgia, us", "ohio", "pennsylvania", "colorado", "virginia", "north carolina", "michigan", "arizona", "minnesota", "oregon", "new jersey", "utah", "tennessee", "maryland", "wisconsin", "missouri", "indiana"], ["cincinnati", "cleveland", "columbus", "st. louis", "kansas city", "indianapolis", "charlotte", "baltimore", "orlando", "tampa", "sacramento", "las vegas", "new orleans", "irvine", "oakland", "cambridge, ma", "princeton", "ann arbor", "boulder", "new york", "san francisco", "seattle", "chicago", "boston", "austin", "los angeles", "atlanta", "denver", "washington, dc", "miami", "dallas", "houston", "san jose", "palo alto", "mountain view", "menlo park", "sunnyvale", "redmond", "portland", "philadelphia", "pittsburgh", "san diego", "salt lake city", "raleigh", "nashville", "minneapolis", "detroit", "phoenix"]),
    "CA": ("Canada", [], ["toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "waterloo"]),
    "IN": ("India", ["bharat"], ["bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "chennai", "gurgaon", "gurugram", "noida", "new delhi", "delhi", "kolkata", "ahmedabad", "kochi"]),
    "SG": ("Singapore", [], []), "JP": ("Japan", [], ["tokyo", "osaka"]), "AU": ("Australia", [], ["sydney", "melbourne", "brisbane", "perth"]),
    "BR": ("Brazil", ["brasil"], ["são paulo", "sao paulo", "rio de janeiro"]), "MX": ("Mexico", ["méxico"], ["mexico city", "guadalajara", "monterrey"]),
    "CN": ("China", [], ["shanghai", "beijing", "shenzhen"]), "HK": ("Hong Kong", [], []), "PH": ("Philippines", [], ["manila"]), "AR": ("Argentina", [], ["buenos aires"]),
    "PK": ("Pakistan", [], ["karachi", "lahore", "islamabad"]), "VN": ("Vietnam", [], ["ho chi minh", "hanoi"]), "KR": ("South Korea", ["korea"], ["seoul"]), "NZ": ("New Zealand", [], ["auckland"]),
    "CO": ("Colombia", [], ["bogota", "bogotá", "medellin"]), "CL": ("Chile", [], ["santiago"]),
}

# Regions: a key, a label, and the countries in it. A region can contain other regions' countries (overlap is fine).
_EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]
_EUROPE = _EU27 + ["GB", "CH", "NO", "IS", "RS", "BA", "ME", "MK", "AL", "XK", "UA", "MD", "TR"]
_GCC = ["AE", "SA", "QA", "KW", "BH", "OM"]
_ME = _GCC + ["JO", "LB", "IL", "IQ", "TR", "EG"]
_AFRICA = ["EG", "MA", "TN", "DZ", "ZA", "NG", "KE", "GH", "RW"]
REGIONS: dict[str, tuple[str, list[str]]] = {
    "benelux": ("Benelux", ["NL", "BE", "LU"]),
    "dach": ("DACH (Germany, Austria, Switzerland)", ["DE", "AT", "CH"]),
    "nordics": ("Nordics & Baltics", ["DK", "SE", "NO", "FI", "IS", "EE", "LV", "LT"]),
    "uk_ie": ("UK & Ireland", ["GB", "IE"]),
    "south": ("Southern Europe", ["FR", "ES", "PT", "IT", "GR", "MT", "CY"]),
    "cee": ("Central & Eastern Europe", ["PL", "CZ", "SK", "HU", "RO", "BG", "SI", "HR", "RS", "BA", "ME", "MK", "AL", "XK", "UA", "MD", "EE", "LV", "LT"]),
    "eu": ("European Union", _EU27),
    "europe": ("Europe", _EUROPE),
    "gcc": ("Gulf (GCC)", _GCC),
    "middle_east": ("Middle East", _ME),
    "mena": ("Middle East & North Africa", _ME + ["MA", "TN", "DZ"]),
    "africa": ("Africa", _AFRICA),
    "emea": ("EMEA", list(dict.fromkeys(_EUROPE + _ME + _AFRICA))),
    "world": ("Anywhere", []),
}
COVERED = list(dict.fromkeys(REGIONS["emea"][1]))                       # countries offered as search places (Europe, Middle East, Africa)

# words in a location that mean "remote, open to this region"
_REMOTE_SCOPE = [
    ("emea", r"emea"), ("europe", r"europe|european|\beu\b|cet|cest|european union"), ("eu", r"eu only|eu-based|within the eu"),
    ("gcc", r"gcc|gulf"), ("middle_east", r"middle east|\bme\b region"), ("mena", r"mena"), ("africa", r"africa"),
    ("world", r"anywhere|worldwide|global|world ?wide|any location|fully distributed"),
]
REMOTE_RX = re.compile(r"\b(remote|remotely|work from home|wfh|home[- ]?based|thuiswerk|telework|télétravail|teletrabajo|homeoffice|home office|distributed)\b", re.I)
HYBRID_RX = re.compile(r"\b(hybrid|hybride|hybrid working|partly remote|flexible location)\b", re.I)


def _rx(words: list[str]) -> str: return "|".join(re.escape(w).replace(r"\ ", r"[ -]") for w in sorted(set(words), key=len, reverse=True))


def _build():
    from . import nl
    pats = []
    for code, (name, alts, cities) in COUNTRIES.items():
        words = [name.lower()] + alts + cities + (list(nl.CITIES) if code == "NL" else [])
        pats.append((code, re.compile(r"(?<![\w-])(" + _rx([w for w in words if len(w) >= 3]) + r")(?![\w])", re.I)))
    return pats


_PATS = None
# bare ISO codes only where they are unambiguous: "Berlin, de", "US-DE-Remote", "Remote (UK)"; never inside words
_CODE_RX = re.compile(r"(?:^|[\s,;(/|-])([A-Za-z]{2})(?=$|[\s,;)/|-])")
_CODE_OK = {"NL", "BE", "DE", "AT", "CH", "GB", "UK", "IE", "FR", "ES", "PT", "IT", "PL", "CZ", "SE", "DK", "FI", "NO", "AE", "SA", "QA", "US", "RO", "HU", "GR", "LU", "EE", "LV", "LT", "SK", "SI", "HR", "BG", "TR", "EG", "ZA", "IN", "CA"}


_US_STATE = re.compile(r",\s*(AL|AK|AZ|AR|CA|CO|CT|DC|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA|VT|WA|WI|WV|WY)\b(?!\s*-)(?=\s*(,|$|\d|;|\)|\s+(US|USA|United States)))")


@dataclass
class Place:
    countries: list[str] = field(default_factory=list)
    work_mode: str = "onsite"
    remote_scope: str | None = None

    @property
    def country(self) -> str | None: return self.countries[0] if self.countries else None


def parse(location: str | None, text: str = "") -> Place:
    """location: the posting's location string. text: optional title/first lines (only used to spot 'hybrid'/'remote')."""
    global _PATS
    if _PATS is None: _PATS = _build()
    loc = (location or "").strip(); low = loc.lower()
    found: dict[str, int] = {}
    for code, rx in _PATS:
        m = rx.search(loc)
        if m: found[code] = m.start()
    for m in _CODE_RX.finditer(loc):
        c = m.group(1)
        if re.search(r"\d{4}\s?$", loc[:m.start(1)]): continue                    # Dutch postcode "5151 AE", not a country
        if c.isupper() or m.start() > 0 and loc[m.start()] in ",;-" or low.rstrip().endswith(c.lower()):
            c = c.upper(); c = "GB" if c == "UK" else c
            if c in _CODE_OK and c not in found: found[c] = m.start(1)
    m = _US_STATE.search(loc)
    if m and "US" not in found and (m.group(1) not in COUNTRIES or m.group(3)): found["US"] = m.start()      # "Berlin, DE" is Germany, "Dover, DE, USA" is Delaware
    countries = [c for c, _ in sorted(found.items(), key=lambda x: x[1])]
    hay = f"{loc} {text[:400]}"
    mode = "remote" if REMOTE_RX.search(loc) else "hybrid" if HYBRID_RX.search(hay) else "remote" if REMOTE_RX.search(text[:200]) else "onsite"
    if mode == "remote" and HYBRID_RX.search(hay): mode = "hybrid"
    scope = None
    if mode == "remote":
        for key, pat in _REMOTE_SCOPE:
            if re.search(pat, low): scope = key; break
        if scope is None and not countries: scope = "world"
    return Place(countries, mode, scope)


def regions_of(country: str) -> list[str]: return [k for k, (_, cs) in REGIONS.items() if country in cs] + ["world"]


def expand(countries: list[str] | None = None, regions: list[str] | None = None) -> list[str]:
    out = [c.upper() for c in countries or []]
    for r in regions or []: out += REGIONS.get(r, ("", []))[1]
    return list(dict.fromkeys(out))


def scopes_for(countries: list[str]) -> list[str]:
    """Remote scopes that include at least one of these countries ("europe" includes NL, "world" includes everyone)."""
    return sorted({r for c in countries for r in regions_of(c)})


def wanted(p: Place, keep: list[str], keep_remote: bool = True) -> bool:
    """Storage rule: keep the posting when it is in one of the countries we crawl for, or remote and open to them."""
    if not keep: return True
    if any(c in keep for c in p.countries): return True
    if keep_remote and p.work_mode == "remote" and p.remote_scope and p.remote_scope != "world" and any(c in keep for c in REGIONS.get(p.remote_scope, ("", []))[1]): return True
    if keep_remote and p.work_mode == "remote" and p.remote_scope == "world": return True
    return False


def public() -> dict:
    return {"countries": [{"code": c, "name": COUNTRIES[c][0], "regions": [r for r in regions_of(c) if r != "world"]} for c in COVERED],
            "regions": [{"key": k, "label": v[0], "countries": v[1]} for k, v in REGIONS.items() if k != "world"]}


_CITY_NAMES = {"münchen": "Munich", "muenchen": "Munich", "köln": "Cologne", "koeln": "Cologne", "wien": "Vienna", "zürich": "Zurich", "zuerich": "Zurich", "genève": "Geneva", "geneve": "Geneva", "genf": "Geneva",
               "warszawa": "Warsaw", "kraków": "Krakow", "cracow": "Krakow", "praha": "Prague", "milano": "Milan", "roma": "Rome", "torino": "Turin", "napoli": "Naples", "firenze": "Florence", "lisboa": "Lisbon",
               "brussel": "Brussels", "bruxelles": "Brussels", "antwerpen": "Antwerp", "gent": "Ghent", "københavn": "Copenhagen", "göteborg": "Gothenburg", "beograd": "Belgrade", "bucurești": "Bucharest", "bucuresti": "Bucharest"}
_CITY_RX = None


def city_of(location: str | None) -> str | None:
    """First big city named in a location outside the Netherlands, in its English spelling."""
    global _CITY_RX
    if _CITY_RX is None:
        cities = [c for code, (_, _, cs) in COUNTRIES.items() if code != "NL" for c in cs if len(c) >= 4]
        _CITY_RX = re.compile(r"(?<![\w-])(" + _rx(cities) + r")(?![\w])", re.I)
    m = _CITY_RX.search(location or "")
    if not m: return None
    c = m.group(1).lower()
    return _CITY_NAMES.get(c) or " ".join(w.capitalize() for w in c.split(" "))
