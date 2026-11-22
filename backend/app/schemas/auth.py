import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field("", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str | None = None          # web uses the httpOnly cookie; mobile sends it in the body


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    name: str
    role: str
    profile: dict
    email_verified: bool = False
    crawl: dict | None = None             # only after a profile save: countries the crawler started collecting for you


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProfileIn(BaseModel):
    """What the user looks for. Every field is optional: only the fields sent are changed (the rest of the profile is kept)."""
    skills: list[str] | None = Field(None, max_length=60)
    titles: list[str] | None = Field(None, max_length=30)
    cities: list[str] | None = Field(None, max_length=30)          # optional: empty = anywhere in the country
    job_types: list[str] | None = None
    english_only: bool | None = None
    salary_category: str | None = None
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")                # legacy single country (still read)
    countries: list[str] | None = Field(None, max_length=60)                # where you want to work (ISO codes)
    regions: list[str] | None = Field(None, max_length=14)                  # or whole regions: europe, dach, gcc ...
    work_modes: list[str] | None = None                                     # onsite | hybrid | remote (none = any)
    sectors: list[str] | None = Field(None, max_length=6)        # tech | architecture | engineering ... (GET /meta/sectors)
    keywords: list[str] | None = Field(None, max_length=40)      # extra words that should count as a match
    remote_ok: bool | None = None
    sponsor_needed: bool | None = None                            # only show employers that can sponsor a work visa
    onboarded: bool | None = None                                 # finished (or skipped) the setup dialog
    prefs: dict | None = None                                     # per-user UI choices (CV template, AI consent, ...), never device-wide


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class EmailIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResetIn(TokenIn):
    new_password: str = Field(min_length=8, max_length=128)


class GoogleIn(BaseModel):
    credential: str = Field(min_length=20, max_length=4000)
