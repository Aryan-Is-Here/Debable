# DebateMatch Backend

FastAPI service backing the DebateMatch platform. Phase 2 delivers the foundation only:
configuration, logging, database layer, models, migrations, Clerk JWT verification and a
health endpoint. Feature endpoints arrive from Phase 3 onward.

## Requirements

- Python 3.11
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker Desktop (runs local PostgreSQL 16)

## Setup

```bash
cd backend
cp .env.example .env      # then edit if needed
uv sync
```

Start PostgreSQL:

```bash
docker compose -f ../docker/docker-compose.yml up -d db
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Run the API:

```bash
uv run python -m app
```

Use `python -m app` rather than calling `uvicorn` directly: on Windows psycopg's async
driver cannot run on the default `ProactorEventLoop`, and the entrypoint selects a
compatible policy before the loop is created (see `app/core/platform.py`). On Linux and
macOS, and inside the Docker image, `uvicorn app.main:app` works unchanged.

Then `GET http://localhost:8000/api/v1/health` should report `{"status": "ok", "database": "ok"}`
— and 503 with `"database": "error"` when Postgres is unreachable. Interactive docs live at
`http://localhost:8000/docs` in development.

To run the API in a container instead of on the host:

```bash
docker compose -f ../docker/docker-compose.yml up -d --build
```

## Tests

```bash
uv run pytest
```

Tests do not require a database or network: the `get_db` dependency and the Clerk JWKS
fetcher are both overridden with fakes.

## Lint

```bash
uv run ruff check .
uv run ruff format --check .
```

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | Application factory, middleware, exception handlers |
| `app/__main__.py` | Development entrypoint (`python -m app`) |
| `app/core/` | Settings, logging, error types, platform shims |
| `app/db/` | Engine, session factory, `get_db` dependency, declarative `Base` |
| `app/models/` | SQLAlchemy models (doc 04 schema) |
| `app/schemas/` | Pydantic request/response models |
| `app/auth/` | Clerk JWT verification (no login endpoint — Clerk owns sign-in) |
| `app/api/v1/` | Versioned routers |
| `migrations/` | Alembic environment and revisions |
| `tests/` | pytest suite |
