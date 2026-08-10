"""Shared test fixtures.

The suite runs without Postgres and without network access: ``get_db`` is replaced by an
in-process stub and the Clerk JWKS is served from a locally generated RSA key. That keeps
`uv run pytest` a one-command check on any machine.
"""

from collections.abc import AsyncIterator, Iterator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app

TEST_ISSUER = "https://test-app.clerk.accounts.dev"
TEST_KID = "test-key-1"


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
