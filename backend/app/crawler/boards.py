"""Job boards (LinkedIn, Indeed, Glassdoor, Google Jobs, Bayt) through the open-source JobSpy library (MIT, `pip install python-jobspy`).

EXPERIMENTAL and OFF by default (CAREERS_BOARD_SITES is empty). Unlike the rest of the crawler this does not read employers' own career
pages: it queries the boards' public search pages, which their terms of use do not allow and which they rate-limit or block. Turn it on
only for personal use, keep the volume low, and expect it to break when a board changes its pages. Robots.txt is not consulted here.

Each posting is stored like any other (dedupe, sector, country, work mode), under the employer's name, with source "board:<site>".
When the board gives the employer's own apply link (job_url_direct), that link is stored instead of the board's."""
import datetime as dt, logging, math, re

log = logging.getLogger("boards")
SITES = ("linkedin", "indeed", "glassdoor", "google", "bayt")

# JobSpy's country names for Indeed / Glassdoor (its `country_indeed` argument). Countries missing here are searched by location text only.
INDEED_COUNTRY = {"NL": "netherlands", "BE": "belgium", "DE": "germany", "AT": "austria", "CH": "switzerland", "GB": "uk", "IE": "ireland", "FR": "france",
                  "ES": "spain", "PT": "portugal", "IT": "italy", "PL": "poland", "CZ": "czech republic", "DK": "denmark", "SE": "sweden", "NO": "norway",
                  "FI": "finland", "GR": "greece", "HU": "hungary", "RO": "romania", "LU": "luxembourg", "TR": "turkey", "AE": "united arab emirates",
                  "SA": "saudi arabia", "QA": "qatar", "KW": "kuwait", "BH": "bahrain", "OM": "oman", "EG": "egypt", "MA": "morocco", "ZA": "south africa",
                  "NG": "nigeria", "IL": "israel", "UA": "ukraine"}
GULF = {"AE", "SA", "QA", "KW", "BH", "OM", "EG", "JO", "LB"}          # where Bayt has listings


class BoardsUnavailable(RuntimeError):
    pass


def _jobspy():
    try:
        from jobspy import scrape_jobs                                         # optional dependency, imported only when boards are switched on
    except ImportError as e:
        raise BoardsUnavailable("job boards need the JobSpy library: pip install python-jobspy") from e
    return scrape_jobs


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


def to_job(row: dict, site: str) -> tuple[str, dict] | None:
    """One JobSpy row -> (employer name, our job dict). None when it has no title, company or link."""
    title, company = _val(row.get("title")), _val(row.get("company"))
    url = _val(row.get("job_url_direct")) or _val(row.get("job_url"))
    if not title or not company or not url: return None
    loc = _val(row.get("location")) or ""
    if _val(row.get("is_remote")) is True and "remote" not in str(loc).lower(): loc = f"{loc}; Remote".strip("; ")
    desc = str(_val(row.get("description")) or "")[:20000] + _salary(row)
    return str(company).strip(), dict(title=str(title).strip(), location=str(loc), url=str(url), description=desc.strip(), posted_at=_date(row.get("date_posted")),
                                      board=site, board_url=_val(row.get("job_url")), company_site=_val(row.get("company_url_direct")))


def search(sites: list[str], term: str, country: str, location: str = "", results: int = 30, hours_old: int = 168) -> list[tuple[str, dict]]:
    """Search the boards for one term in one country. -> [(employer, job), ...]. A board that fails is logged and skipped."""
    scrape_jobs = _jobspy()
    sites = [s for s in sites if s in SITES and (s != "bayt" or country in GULF)]
    if not sites: return []
    from . import places
    where = location or places.COUNTRIES.get(country, (country,))[0]
    out: list[tuple[str, dict]] = []
    for site in sites:                                                         # one site at a time: a block on one board must not lose the others
        kw = dict(site_name=[site], search_term=term, location=where, results_wanted=results, hours_old=hours_old, description_format="markdown", verbose=0)
        if site in ("indeed", "glassdoor"):
            if country not in INDEED_COUNTRY: continue
            kw["country_indeed"] = INDEED_COUNTRY[country]
        if site == "linkedin": kw["linkedin_fetch_description"] = True     # slower, but without it LinkedIn rows have no description
        if site == "google": kw["google_search_term"] = f"{term} jobs in {where} since last week"
        try:
            df = scrape_jobs(**kw)
        except Exception as e:                                                  # blocked (429/403), page changed, network ...
            log.warning("board %s failed for %r in %s: %s", site, term, where, str(e)[:200]); continue
        rows = df.to_dict("records") if hasattr(df, "to_dict") else list(df or [])
        for r in rows:
            j = to_job(r, site)
            if j: out.append(j)
    return out
