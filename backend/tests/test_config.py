"""Managed Postgres hosts (Render, Heroku, Railway...) hand out `postgres://`
connection strings; SQLAlchemy's async engine needs the driver named
explicitly or it tries to load a sync driver and fails."""

from __future__ import annotations

from app.core.config import Settings


def test_plain_postgres_scheme_gets_asyncpg_appended():
    s = Settings(database_url="postgres://user:pass@host:5432/db")
    assert s.database_url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_postgresql_scheme_gets_asyncpg_appended():
    s = Settings(database_url="postgresql://user:pass@host:5432/db")
    assert s.database_url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_a_url_that_already_names_asyncpg_is_left_alone():
    url = "postgresql+asyncpg://user:pass@host:5432/db"
    assert Settings(database_url=url).database_url == url
