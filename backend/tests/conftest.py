"""Test database setup.

Earlier version of this file shared a single AsyncSession between the test
body and the FastAPI app (via a dependency override), so uncommitted fixture
data was visible to HTTP requests without a commit. That's the "textbook"
pattern, but it hit asyncpg's "another operation is in progress" whenever a
test both touched the session directly and drove it through the app -
likely a task-boundary issue where httpx's ASGI transport and the test body
weren't strictly sequential at the connection level.

Simpler and just as correct for this project: each side gets its own
session, both pointed at the same real database, and fixtures commit their
setup data instead of just flushing it. No session sharing, no dependency
override, nothing to race. Isolation comes from unique UUIDs per fixture
rather than a rollback - fine for a project this size.

Requires a local Postgres reachable at TEST_DATABASE_URL (defaults to the
same demo/demo database used by docker-compose, on localhost).
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://demo:demo@localhost:5432/demo"),
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("SIMULATE_CUSTOMER_REPLIES", "false")

from app.core.security import hash_password  # noqa: E402
from app.db.models import Base, Contact, Conversation, User, WhatsAppLine, utcnow  # noqa: E402
from app.main import app  # noqa: E402

engine = create_async_engine(os.environ["DATABASE_URL"])
TestSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db():
    """A session for setting up fixture data. Fixtures and helpers commit
    as they go (not just flush) so the app's own, separate session - used
    whenever a test drives things through `client` - can see the data
    immediately. Two sessions on two connections, never shared."""
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def agent(db) -> User:
    user = User(
        id=uuid.uuid4(), full_name="Test Agent", email=f"agent-{uuid.uuid4()}@demo.com",
        password_hash=hash_password("secret123"), role="agent",
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def admin(db) -> User:
    user = User(
        id=uuid.uuid4(), full_name="Test Admin", email=f"admin-{uuid.uuid4()}@demo.com",
        password_hash=hash_password("secret123"), role="admin",
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def line(db, agent) -> WhatsAppLine:
    wa_line = WhatsAppLine(
        id=uuid.uuid4(), phone_number=f"+1555{uuid.uuid4().int % 10_000_000:07d}",
        label="Test line", agent_id=agent.id,
        policy_daily=250, policy_hourly=30, policy_new_chats_daily=30,
        warmup_started_at=utcnow() - timedelta(days=45),  # fully warmed by default
    )
    db.add(wa_line)
    await db.commit()
    return wa_line


async def make_conversation(db: AsyncSession, line: WhatsAppLine, *, warm: bool) -> Conversation:
    contact = Contact(id=uuid.uuid4(), name="Test Contact", phone_number="+1 555 000 0000")
    db.add(contact)
    await db.commit()
    convo = Conversation(
        id=uuid.uuid4(), contact_id=contact.id, line_id=line.id,
        first_inbound_at=utcnow() if warm else None,
    )
    db.add(convo)
    await db.commit()
    return convo


async def token_for(client: AsyncClient, user: User) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", data={"username": user.email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
