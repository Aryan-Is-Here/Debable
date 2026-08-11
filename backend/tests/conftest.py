"""Shared test fixtures.

Two tiers:

* **Unit tests** run with no database and no network — ``get_db`` is replaced by an
  in-process stub and the Clerk JWKS is served from a locally generated RSA key.
* **Integration tests** (anything requesting ``db_session`` or ``api_client``) need the
  compose Postgres. If it is not reachable they *skip* rather than fail, so
  ``uv run pytest`` stays green on a machine with Docker stopped.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.platform import configure_event_loop_policy
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Topic, User

configure_event_loop_policy()

TEST_ISSUER = "https://test-app.clerk.accounts.dev"
TEST_KID = "test-key-1"

# ---------------------------------------------------------------------------
# Unit-test fixtures (no database)
# ---------------------------------------------------------------------------


class StubSession:
    """Minimal stand-in for ``AsyncSession`` covering what the health check touches."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.executed: list[str] = []

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        self.executed.append(str(statement))
        if self.fail:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def settings() -> Settings:
    """Settings that never read a developer's local ``.env``."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        env="test",
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        cors_origins=["http://localhost:3000"],
        clerk_issuer=TEST_ISSUER,
        clerk_authorized_parties=["http://localhost:3000"],
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def db_stub() -> StubSession:
    return StubSession()


@pytest.fixture
def failing_db_stub() -> StubSession:
    return StubSession(fail=True)


@pytest.fixture
async def client(app: FastAPI, db_stub: StubSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[StubSession]:
        yield db_stub

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture(scope="session")
def rsa_key_pair() -> tuple[rsa.RSAPrivateKey, dict[str, Any]]:
    """An RSA key plus its public JWK, standing in for Clerk's signing key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(  # type: ignore[assignment]
        private_key.public_key(), as_dict=True
    )
    jwk.update({"kid": TEST_KID, "alg": "RS256", "use": "sig"})
    return private_key, jwk


# ---------------------------------------------------------------------------
# Integration fixtures (real Postgres)
# ---------------------------------------------------------------------------


def _with_database(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


def test_database_url() -> str:
    """A sibling of the configured database, suffixed ``_test``.

    Never the development database: these tests create and drop tables.
    """
    url = Settings(_env_file=None).database_url  # type: ignore[call-arg]
    name = urlsplit(url).path.lstrip("/") or "debable"
    return _with_database(url, f"{name}_test")


async def _prepare_test_database() -> str | None:
    """Create the test database and its schema. Returns None if Postgres is unreachable."""
    url = test_database_url()
    parts = urlsplit(url)
    target = parts.path.lstrip("/")
    admin_url = _with_database(url, "postgres")

    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target}
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{target}"'))
    except OperationalError:
        return None
    finally:
        await admin_engine.dispose()

    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()
    return url


@pytest.fixture(scope="session")
def database_url() -> str:
    """URL of a freshly created test database, or skip the whole integration tier."""
    url = asyncio.run(_prepare_test_database())
    if url is None:
        pytest.skip(
            "Postgres is not reachable — start it with "
            "`docker compose -f docker/docker-compose.yml up -d db`",
            allow_module_level=True,
        )
    return url


@pytest_asyncio.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    """A session whose writes are rolled back after the test.

    The outer transaction is never committed; ``join_transaction_mode="create_savepoint"``
    turns the service layer's own ``commit()`` into a savepoint release, so code under test
    can commit normally without leaking rows into the next test.
    """
    engine = create_async_engine(database_url)
    connection = await engine.connect()
    transaction = await connection.begin()
    factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    """A persisted user to own topics."""
    record = User(
        clerk_user_id="user_test_primary",
        username="debater",
        email="debater@example.com",
        avatar_url=None,
    )
    db_session.add(record)
    await db_session.flush()
    return record


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    record = User(
        clerk_user_id="user_test_secondary",
        username="opponent",
        email="opponent@example.com",
        avatar_url=None,
    )
    db_session.add(record)
    await db_session.flush()
    return record


@pytest_asyncio.fixture
async def api_client(
    app: FastAPI, db_session: AsyncSession, user: User
) -> AsyncIterator[AsyncClient]:
    """Client wired to the transactional session, signed in as ``user``.

    Authentication is overridden rather than mocked at the HTTP layer: token verification
    has its own tests, and re-proving it on every endpoint test would only couple them.
    """

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def anonymous_api_client(
    app: FastAPI, db_session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    """Client with no signed-in user, for checking that writes are refused."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def make_topic(user: User, **overrides: Any) -> Topic:
    """A valid topic owned by ``user``, with fields overridable per test."""
    values: dict[str, Any] = {
        "title": "Should artificial intelligence be regulated",
        "description": "A debate about whether governments should regulate AI development.",
        "category": "Technology",
        "creator_id": user.id,
    }
    values.update(overrides)
    return Topic(**values)
