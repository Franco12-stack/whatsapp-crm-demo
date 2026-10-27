"""App-wide settings, read from the environment.

Everything here has a safe default so the demo runs out of the box with just
`docker compose up`. In a real deployment you'd pin every one of these in
`.env` and never ship a default secret — see the production project this
demo is distilled from.
"""

from __future__ import annotations

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


settings = Settings()
