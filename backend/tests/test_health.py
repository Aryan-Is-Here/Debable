"""Health endpoint behaviour."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import __version__
from app.db.session import get_db
from tests.conftest import StubSession


async def test_health_reports_ok_when_database_responds(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "env": "test",
        "version": __version__,
    }


async def test_health_queries_the_database(client: AsyncClient, db_stub: StubSession) -> None:
    await client.get("/api/v1/health")

    assert db_stub.executed == ["SELECT 1"]


async def test_health_returns_503_when_database_is_down(
    app: FastAPI, failing_db_stub: StubSession
) -> None:
    async def override_get_db():
        yield failing_db_stub

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "error"


async def test_unknown_route_uses_the_shared_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
