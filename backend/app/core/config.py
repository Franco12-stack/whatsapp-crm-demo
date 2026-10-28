"""App-wide settings, read from the environment.

Everything here has a safe default so the demo runs out of the box with just
`docker compose up`. In a real deployment you'd pin every one of these in
`.env` and never ship a default secret — see the production project this
demo is distilled from.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://demo:demo@postgres:5432/demo"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 12

    # How fast the simulated customers reply, so the demo feels alive without
    # a real WhatsApp number behind it. See app/services/simulator.py.
    simulate_customer_replies: bool = True
    simulator_tick_seconds: int = 12

    # Seeds demo data on first boot if the database is empty. Exists for
    # hosts like Render's free tier, which don't give you a shell to run
    # `python -m scripts.seed_demo` by hand - see scripts/seed_demo.py.
    auto_seed: bool = True

    @field_validator("database_url")
    @classmethod
    def _asyncpg_scheme(cls, value: str) -> str:
        """Managed Postgres hosts (Render, Heroku, Railway...) hand out
        `postgres://` or `postgresql://` connection strings. SQLAlchemy's
        async engine needs the driver named explicitly, or it tries (and
        fails) to load a sync driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix) and "+asyncpg" not in value:
                return "postgresql+asyncpg://" + value[len(prefix):]
        return value


settings = Settings()
