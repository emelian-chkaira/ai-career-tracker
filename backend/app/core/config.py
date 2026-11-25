"""Typed settings from environment variables / .env (12-factor). Nothing deployment-specific is hard-coded elsewhere."""
from functools import lru_cache
from pydantic import Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAREERS_", env_file=(".env", "../.env"), extra="ignore", populate_by_name=True)

    # --- infrastructure
    # Neon gives a pooled DATABASE_URL and a direct DATABASE_URL_UNPOOLED. The direct one wins: each connection runs a session-level SET (core/db.py),
    # which a transaction-mode pooler would lose, Alembic needs it too, and this long-running server already pools connections itself.
    database_url: str = Field("postgresql+psycopg://careers:careers@localhost:5433/careers", validation_alias=AliasChoices("DATABASE_URL_UNPOOLED", "DATABASE_URL", "CAREERS_DATABASE_URL"))
    db_pool_size: int = 30
    data_dir: str = "./data"                      # logos, uploads
    env: str = "dev"                              # dev | prod
    # --- security
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    access_ttl_min: int = 30
    refresh_ttl_days: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8787"
    rate_limit_per_min: int = 240
    auth_rate_limit_per_min: int = 20
    allow_registration: bool = True
    demo_mode: bool = False                       # true on the public demo only: feature tour, one-click guest accounts, no crawler-backed actions
    demo_guest_days: int = 7                      # demo guest accounts are deleted after this many days
    firebase_api_key: str | None = None            # Firebase project Web API key: when set, Firebase Authentication is the identity provider
    google_client_id: str | None = None           # OAuth client ID(s) from Google Cloud Console, comma separated (web, iOS, Android)
    google_client_secret: str | None = None       # secret of the web OAuth client: enables "Connect Gmail" (see docs/GMAIL_OAUTH.md)
    gmail_client_id: str | None = None            # optional: a separate OAuth client for Gmail; defaults to the first google_client_id
    api_url: str = "http://localhost:8787"        # public address of this API, used for the Google OAuth redirect
    require_verified_email: bool = False          # true: sign-in is refused until the address is confirmed
    verify_ttl_hours: int = 48
    reset_ttl_min: int = 60
    # --- what to store (apply on ingest, and via the Prune action to existing data) ---
    crawl_countries: str = "NL"                   # comma list of ISO codes to store jobs for (NL, BE, DE, AE ...), or region keys (benelux, dach, europe, gcc, emea). Empty = everywhere
    keep_remote: bool = True
    # EXPERIMENTAL job boards through JobSpy (crawler/boards.py). Off unless sites are listed. Against those sites' terms: personal use only.
    board_sites: str = ""                         # comma list of: linkedin, indeed, glassdoor, bayt
    board_every_hours: int = 12                   # automatic board search interval (inside the crawl schedule); 0 = only when started by hand
    board_results: int = 30                       # postings per site per search
    board_max_searches: int = 24                  # term x country searches per run (keeps the volume low)                      # also store remote jobs that are open to those countries ("Remote - Europe", "Anywhere")
    keep_domains: str = ""                        # manual mode only: comma list of: mobile, frontend, backend, fullstack, software, data, devops, security, qa, embedded, design, product, other. Empty = store every domain
    fields_mode: str = "auto"                     # auto = collect what the accounts' profiles and CVs ask for (default) | manual = the lists in the Crawler page | all = every field
    max_job_age_days: int = 0                     # 0 = no limit. Otherwise skip jobs posted longer ago than this, and delete stored ones that got older
    delete_expired_after_days: int = 60           # jobs no longer on the employer's page are deleted after this many days (0 = keep forever). Saved/pipeline jobs are never deleted
    allow_private_hosts: bool = True              # True: users may point AI/mail connections at localhost / LAN (Ollama, local mail bridge). Set False on a public server (SSRF protection)
    open_crawler: bool = True                     # True: any signed-in user can use the Crawler page (self-hosted default). False: admins only (set this for a public deployment)
    first_user_admin: bool = True                 # the first account created on a fresh install becomes admin (so a self-hosted copy needs no setup)
    admin_emails: str = ""                        # comma separated: these accounts get the admin role on sign-up
    cookie_secure: bool = False
    trust_proxy: bool = False
    # --- crawler identity
    contact: str = "https://github.com/your-org/ai-career-tracker"
    brave_api_key: str | None = None
    browser_slots: int = 5
    scan_threads: int = 16
    # --- search / semantic
    embedding_model: str = "BAAI/bge-small-en-v1.5"   # 384-d, local ONNX via fastembed
    embedding_dim: int = 384
    semantic_enabled: bool = True
    # --- alerts / email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_security: str = "starttls"                # starttls (587) | ssl (465) | none (local test servers such as Mailpit)
    mail_from: str = "AI Career Tracker <no-reply@localhost>"
    public_url: str = "http://localhost:5173"        # used in email links
    # --- optional
    anthropic_api_key: str | None = None
    latex_compile: bool = True

    @field_validator("database_url")
    @classmethod
    def _driver(cls, v: str) -> str:
        """Hosted databases (Neon, Supabase, Render ...) hand out plain postgres:// URLs: use the psycopg 3 driver."""
        for pre in ("postgres://", "postgresql://"):
            if v.startswith(pre): return "postgresql+psycopg://" + v[len(pre):]
        return v

    @property
    def user_agent(self) -> str: return f"ai-career-tracker/0.4 (+{self.contact})"
    @property
    def firebase_on(self) -> bool: return bool(self.firebase_api_key)
    @property
    def google_ids(self) -> list[str]: return [c.strip() for c in (self.google_client_id or "").split(",") if c.strip()]
    @property
    def cors_list(self) -> list[str]: return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    @property
    def admin_list(self) -> set[str]: return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}
    @property
    def domain_set(self) -> set[str]:
        from app.crawler.domains import parse
        return parse(self.keep_domains)


@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
