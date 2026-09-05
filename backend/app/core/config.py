"""Application settings loaded from the environment.

Every tunable lives here so that no module reads ``os.environ`` directly. Values come from
the process environment first and ``backend/.env`` second; see ``.env.example`` for the
full list.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "production"]

# pydantic-settings JSON-decodes list-typed fields before validators run, so a plain
# `a,b` in .env would blow up. NoDecode hands the raw string to our `_split_csv` instead.
CsvList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    """Typed view of the runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Runtime ---
    env: Environment = "development"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "postgresql+psycopg://debable:debable@localhost:5432/debable"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # --- CORS ---
    cors_origins: CsvList = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- LiveKit (video) ---
    # The URL is public — the browser needs it. The key and especially the secret are
    # signing credentials and must never reach the frontend: the browser only ever receives
    # a short-lived token minted here.
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    # How long a room token stays valid. Long enough to cover a debate, short enough that a
    # leaked one expires on its own.
    livekit_token_ttl_minutes: int = 120

    @property
    def livekit_configured(self) -> bool:
        return bool(self.livekit_url and self.livekit_api_key and self.livekit_api_secret)

    # --- Gemini (AI fact-check) ---
    # The key is optional by design: with none set the application falls back to a stub
    # provider, so a fresh clone runs the whole debate flow without any credentials.
    #
    # Gemini rather than Claude because this project has no budget, and Gemini 2.5 Flash is
    # the only model whose Google Search grounding is free of charge. That amends a Phase 0
    # decision — see `docs/PROJECT-HANDBOOK.md` §6.
    gemini_api_key: str = ""
    # 2.5-flash returns 404 "no longer available to new users"; 3.6-flash is verified working
    # on a free key for plain generation, which is all this needs — search is ours.
    gemini_model: str = "gemini-3.6-flash"
    # Optional. Without it the fact-check searches Wikipedia, which needs no credentials.
    # With it, evidence comes from the whole trusted-source allowlist, enforced at retrieval.
    tavily_api_key: str = ""
    fact_check_timeout_seconds: float = 45.0
    # Per room, per hour. Stops one debate spamming the button.
    fact_check_rate_limit_per_hour: int = 10
    # Across the whole deployment, per day. The per-room limit cannot protect a *shared*
    # quota — thirty rooms doing ten checks each is 300 requests, and on a 250/day free tier
    # every fact-check after that fails for everyone. Set below the real quota so the
    # service refuses with its own clear message instead of hitting Google's 429.
    fact_check_daily_budget: int = 200

    @property
    def fact_check_configured(self) -> bool:
        """Whether a real provider can be built. False means the stub answers."""
        return bool(self.gemini_api_key)

    # --- Clerk ---
    # Sign-in is owned by Clerk on the client; the backend only verifies its JWTs.
    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    clerk_audience: str = ""
    clerk_authorized_parties: CsvList = Field(default_factory=list)
    clerk_jwks_cache_seconds: int = 3600

    @field_validator("cors_origins", "clerk_authorized_parties", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept both a comma-separated string and a real list from the environment."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def resolved_clerk_jwks_url(self) -> str:
        """Explicit JWKS URL if configured, otherwise the issuer's well-known location."""
        if self.clerk_jwks_url:
            return self.clerk_jwks_url
        if self.clerk_issuer:
            return f"{self.clerk_issuer.rstrip('/')}/.well-known/jwks.json"
        return ""


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
