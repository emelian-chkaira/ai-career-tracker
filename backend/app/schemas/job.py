import datetime as dt
from pydantic import BaseModel


class CompanyMini(BaseModel):
    id: int
    name: str
    logo: str | None = None
    website: str | None = None
    sponsor_status: str = "unchecked"
    sponsor_match: str | None = None


class JobOut(BaseModel):
    id: int
    title: str
    company: CompanyMini
    location: str | None = None
    city: str | None = None
    country: str | None = None
    countries: list[str] = []
    work_mode: str = "onsite"
    remote_scope: str | None = None
    url: str
    job_type: str
    category: str
    sector: str | None = None
    domain: str | None = None
    language: str
    remote: bool = False
    salary: dict | None = None            # {min,max,period,verdict}
    posted_at: dt.date | None = None
    first_seen: dt.datetime | None = None
    status: str = "open"
    skills: list[str] = []
    snippet: str | None = None
    relevance: int | None = None
    matched: list[str] = []
    fit: int | None = None
    fit_reason: str | None = None
    ai: dict | None = None                # AI assessment against the user's CV: {score, verdict, reason, ...}
    stage: str | None = None              # the signed-in user's pipeline stage
    description: str | None = None        # only on the detail endpoint


class SearchOut(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    limit: int
    facets: dict
    query: dict
    sort: str
