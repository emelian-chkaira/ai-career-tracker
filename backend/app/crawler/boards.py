"""Job boards (LinkedIn, Indeed, Glassdoor, Google Jobs, Bayt) through the open-source JobSpy library (MIT, `pip install python-jobspy`).

EXPERIMENTAL and OFF by default (CAREERS_BOARD_SITES is empty). Unlike the rest of the crawler this does not read employers' own career
pages: it queries the boards' public search pages, which their terms of use do not allow and which they rate-limit or block. Turn it on
only for personal use, keep the volume low, and expect it to break when a board changes its pages. Robots.txt is not consulted here.

Being a good guest instead of fighting blocks (no proxies, no challenge solving):
  * JobSpy does not raise when a board blocks it; it lists the failure in `df.attrs["errors"]`. We read that, so a 429 counts as a failure.
  * A blocked board rests (cool-down) before it is asked again; repeated blocks double the rest (services/boards_service.py keeps that state).
  * Glassdoor gets a city instead of a country (it handles country-wide searches badly) and requests to it are spaced out.
Each posting is stored like any other (dedupe, sector, country, work mode), under the employer's name, with source "board:<site>".
When the board gives the employer's own apply link (job_url_direct), that link is stored instead of the board's."""
import datetime as dt, logging, math, re, time

log = logging.getLogger("boards")
SITES = ("linkedin", "indeed", "glassdoor", "google", "bayt")
INFO = {   # what each board is like, from JobSpy's README; shown on the Crawler page
    "linkedin": dict(label="LinkedIn", note="Blocks bursts of requests (HTTP 429) for about a minute; the strictest board.", spacing=4.0),
    "indeed": dict(label="Indeed", note="The most reliable board, rarely blocks.", spacing=1.0),
    "glassdoor": dict(label="Glassdoor", note="Limits above about 2 requests a second; searched by city, not country.", spacing=2.0),
    "google": dict(label="Google Jobs", note="JobSpy reports Google Jobs as currently unavailable; expect empty results.", spacing=2.0),
    "bayt": dict(label="Bayt", note="Gulf and Middle East board; only searched for those countries.", spacing=2.0),
}

# JobSpy's country names for Indeed / Glassdoor (its `country_indeed` argument). Countries missing here are searched by location text only.
INDEED_COUNTRY = {"NL": "netherlands", "BE": "belgium", "DE": "germany", "AT": "austria", "CH": "switzerland", "GB": "uk", "IE": "ireland", "FR": "france",
                  "ES": "spain", "PT": "portugal", "IT": "italy", "PL": "poland", "CZ": "czech republic", "DK": "denmark", "SE": "sweden", "NO": "norway",
                  "FI": "finland", "GR": "greece", "HU": "hungary", "RO": "romania", "LU": "luxembourg", "TR": "turkey", "AE": "united arab emirates",
                  "SA": "saudi arabia", "QA": "qatar", "KW": "kuwait", "BH": "bahrain", "OM": "oman", "EG": "egypt", "MA": "morocco", "ZA": "south africa",
                  "NG": "nigeria", "IL": "israel", "UA": "ukraine"}
GULF = {"AE", "SA", "QA", "KW", "BH", "OM", "EG", "JO", "LB"}          # where Bayt has listings
_last_call: dict[str, float] = {}


class BoardsUnavailable(RuntimeError):
    pass


def _jobspy():
    try:
        from jobspy import scrape_jobs                                         # optional dependency, imported only when boards are switched on
    except ImportError as e:
        raise BoardsUnavailable("job boards need the JobSpy library: pip install -r requirements-boards.txt") from e
    return scrape_jobs


def available() -> bool:
    try: _jobspy(); return True
    except BoardsUnavailable: return False


def _val(v):
    """pandas gives NaN / NaT for missing values; turn every kind of 'missing' into None."""
    if v is None: return None
    if isinstance(v, float) and math.isnan(v): return None
    s = str(v)
    return None if s in ("nan", "NaT", "None", "") else v


def _date(v) -> str | None:
    v = _val(v)
    if v is None: return None
    if isinstance(v, (dt.date, dt.datetime)): return v.isoformat()[:10]
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(v)); return m.group(0) if m else None


def _salary(row) -> str:
    lo, hi, cur, per = (_val(row.get(k)) for k in ("min_amount", "max_amount", "currency", "interval"))
    if lo is None and hi is None: return ""
    sym = {"EUR": "€", "GBP": "£", "USD": "$"}.get(str(cur or "").upper(), f"{cur} " if cur else "€")
    f = lambda x: f"{sym}{int(float(x)):,}".replace(",", ".")
    return f"\n\nSalary: {f(lo) if lo is not None else ''}{' - ' + f(hi) if hi is not None else ''} per {per or 'year'}"


def plain(md: str) -> str:
    """JobSpy returns markdown; the app shows plain text: drop emphasis, headings, escapes and link syntax, keep paragraphs and bullets."""
    t = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", md or "")
    t = re.sub(r"^\s*[-+*]\s+", "• ", t, flags=re.M)                        # bullets first, before '*' emphasis is dropped
    t = re.sub(r"(\*\*|__|\*|`)", "", t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"\\([\\`*_{}\[\]()#+\-.!&])", r"\1", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def to_job(row: dict, site: str) -> tuple[str, dict] | None:
    """One JobSpy row -> (employer name, our job dict). None when it has no title, company or link."""
    title, company = _val(row.get("title")), _val(row.get("company"))
    url = _val(row.get("job_url_direct")) or _val(row.get("job_url"))
    if not title or not company or not url: return None
    loc = _val(row.get("location")) or ""
    if _val(row.get("is_remote")) is True and "remote" not in str(loc).lower(): loc = f"{loc}; Remote".strip("; ")
    desc = plain(str(_val(row.get("description")) or ""))[:20000] + _salary(row)
    return str(company).strip(), dict(title=str(title).strip(), location=str(loc), url=str(url), description=desc.strip(), posted_at=_date(row.get("date_posted")),
                                      board=site, board_url=_val(row.get("job_url")), company_site=_val(row.get("company_url_direct")))


def where_for(site: str, country: str, location: str = "") -> str:
    """The location text a board understands best: Glassdoor wants a city, the others take the country name."""
    from . import places
    name, _alts, cities = places.COUNTRIES.get(country, (country, [], []))
    if location: return location
    if site == "glassdoor" and cities: return " ".join(w.capitalize() for w in cities[0].split(" "))
    return name


def applies(site: str, country: str) -> str | None:
    """None when this board can be searched for this country, else the reason it is skipped."""
    if site == "bayt" and country not in GULF: return "Bayt only lists Gulf and Middle East jobs"
    if site in ("indeed", "glassdoor") and country not in INDEED_COUNTRY: return f"{INFO[site]['label']} does not cover this country"
    return None


def search_site(site: str, term: str, country: str, location: str = "", results: int = 30, hours_old: int = 168) -> tuple[list[tuple[str, dict]], str | None]:
    """One board, one term, one country. -> (rows, error). error is the board's own message (e.g. '429 ... blocked') or None."""
    scrape_jobs = _jobspy()
    where = where_for(site, country, location)
    kw = dict(site_name=[site], search_term=term, location=where, results_wanted=results, hours_old=hours_old, description_format="markdown", verbose=0)
    if site in ("indeed", "glassdoor"): kw["country_indeed"] = INDEED_COUNTRY[country]
    if site == "linkedin": kw["fetch_description"] = True                     # without it LinkedIn rows have no description
    if site == "google": kw["google_search_term"] = f"{term} jobs in {where} since last week"
    wait = INFO[site]["spacing"] - (time.monotonic() - _last_call.get(site, 0))
    if wait > 0: time.sleep(wait)                                             # space requests to the same board out
    try:
        df = scrape_jobs(**kw)
    except Exception as e:                                                    # network down, page changed ...
        return [], str(e)[:300] or e.__class__.__name__
    finally:
        _last_call[site] = time.monotonic()
    err = ((getattr(df, "attrs", None) or {}).get("errors") or {}).get(site)    # JobSpy logs blocks instead of raising
    rows = df.to_dict("records") if hasattr(df, "to_dict") else []
    out = [j for j in (to_job(r, site) for r in rows) if j]
    return out, (str(err)[:300] if err else None)
