# DebateMatch — Progress Report

**Report date:** 2026-08-10 · **Milestone:** Start of Phase 3 (Topics)
**Repository:** https://github.com/Aryan-Is-Here/Debable

This report is generated at the start of each new phase and covers all progress to date.

---

## Where we are

| Phase | Status |
|---|---|
| Phase 0 — Planning | ✅ Complete |
| Phase 1 — UI Prototype | ✅ Complete (merged to `main`) |
| **Phase 2 — Backend Foundation** | ✅ **Complete** (`feature/backend-foundation`) |
| Phase 3 — Topics | 🔵 Starting now |
| Phase 4 — Matchmaking | ⏳ Pending |
| Phase 5 — Video | ⏳ Pending |
| Phase 6 — Chat | ⏳ Pending |
| Phase 7 — AI Fact Check | ⏳ Pending |
| Phase 8 — Ratings | ⏳ Pending |
| Phase 9 — Polish & Deploy | ⏳ Pending |

---

## Phase 0 — Planning ✅

Repository scaffolded to the blueprint's modular structure; blueprint documents placed in
`docs/` as the source of truth; git and GitHub wired up.

**Key decisions locked:** auth is Clerk (client-side login, backend verifies JWTs, no
`/auth/login` endpoint); the AI fact-check stays an isolated on-demand service; build
strictly sequentially by roadmap phase, one feature per branch.

---

## Phase 1 — UI Prototype ✅

All screens from `docs/06-ui-ux.md` built against mock data only, merged to `main`.

| Screen | Route |
|---|---|
| Home | `/` |
| Browse Topics | `/browse` |
| Create Topic | `/create` |
| Waiting Room | `/waiting` |
| Debate Room | `/debate/[roomId]` |
| Results / Rating | `/debate/[roomId]/results` |
| Profile | `/profile` |
| Settings | `/settings` |

Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind v4, shadcn/ui in the
base-nova style, next-themes, react-hook-form + zod, sonner. Server components for layout
and data, client components only where interactive. The core loop — browse, match, debate,
fact-check, rate — is clickable end to end.

Re-verified at the start of this phase: `npm run lint` is clean and `npm run build` compiles
all 9 routes with no type errors. Phase 1 needed no repairs.

---

## Phase 2 — Backend Foundation ✅

A running FastAPI service. No feature endpoints yet beyond health — that is the point of a
foundation phase.

### What was built

- **Application shell.** `create_app()` factory with CORS driven by settings, a lifespan that
  disposes the connection pool, and exception handlers that give every failure one envelope:
  `{"error": {"code", "message", "details?"}}`. Interactive docs are disabled in production.
- **Configuration and logging.** pydantic-settings `Settings` with `.env.example` committed
  and `.env` ignored; readable log lines in development, one JSON object per record in
  production.
- **Database layer.** Async SQLAlchemy 2 over psycopg 3: memoised engine and session factory,
  and a `get_db` dependency that rolls back on exception while leaving commits to handlers.
- **Schema.** Six tables — users, topics, debate_rooms, messages, fact_checks, ratings — with
  UUID primary keys, `created_at`/`updated_at` on every table, and `fact_checks.sources` as
  JSONB. Check and unique constraints encode the rules that matter: no self-debates, ratings
  scored 1–5, no self-reviews, one rating per reviewer per room.
- **Migrations.** Alembic reading `DATABASE_URL` from the application's own settings, plus the
  initial revision. Verified with `alembic check` (no drift between models and database) and a
  full `downgrade base` → `upgrade head` round trip.
- **Auth.** Clerk JWT verification with an async JWKS cache that refetches on key rotation.
  Signature, expiry, issuer and authorized party are checked; audience too when configured.
  Verification fails closed when Clerk is unconfigured. `get_current_user` provisions the local
  `users` row on first sight, race-safely. There is deliberately no login endpoint.
- **Health.** `GET /api/v1/health` returns `{status, database, env, version}`, and 503 when
  Postgres is unreachable.
- **Docker.** `postgres:16-alpine` with a healthcheck plus an optional containerised API,
  built from a uv-based Dockerfile with dependency layers cached separately.
- **Tests.** 31 pytest tests covering the health endpoint (including the 503 path), settings
  parsing, JWKS caching/rotation/failure handling, and token verification against expired,
  wrong-issuer, wrong-key, wrong-`azp`, wrong-`aud`, subject-less and malformed tokens. The
  suite needs neither a database nor network access.

### Blueprint conflicts resolved

| # | Conflict | Outcome |
|---|---|---|
| 4 | Missing timestamps; `FactChecks.sources` untyped | `created_at`/`updated_at` on every table; `sources` is JSONB defaulting to `[]`. Also added `fact_checks.explanation` (the UI renders it) and `users.clerk_user_id` as the Clerk join key. |
| 5 | No local Postgres — Docker was not installed | Docker Desktop installed; compose runs `postgres:16-alpine` locally. |

### Verified

`alembic upgrade head` against the compose database, then `GET /api/v1/health` returning
`{"status":"ok","database":"ok"}`; stopping the database container turns that into a 503 with
`"database":"error"`, and restarting it recovers without restarting the API. The same check
passes from inside the built API image. `ruff check`, `ruff format --check` and `pytest` are
all green.

### Worth knowing

On Windows, psycopg's async driver cannot run on Python's default `ProactorEventLoop`. The
backend is therefore started with `uv run python -m app`, which selects a compatible policy
before the loop is created; Alembic does the same. Linux, macOS and Docker are unaffected.

---

## What Phase 3 (starting now) will deliver

`POST /api/v1/topics` and `GET /api/v1/topics` behind the repository/service split, and the
frontend's Browse, Create and Home screens reading live data through a `services/` client and
TanStack Query instead of `lib/mock/`.

Three things need deciding before code is written, all tracked in the handbook:

1. **`Topic.category`** exists only in the frontend — Browse filters on it and Create requires
   it, but there is no column. A value set has to be agreed and mirrored on both sides.
2. **Clerk is not configured yet.** `POST /topics` needs an authenticated creator, so the Clerk
   application must exist and a real token must verify first.
3. **`Topic.activeDebaters`** is a queue count with no queue behind it until Phase 4; it stays
   out of the API for now.

---

## Git history (main)

| Commit | Description |
|---|---|
| `32d95f3` | **feat(backend): Phase 2 backend foundation — Phase 2 complete** |
| `1ce336f` | docs: comprehensive project handbook |
| `2f7f2b1` | docs: Phase 2 start progress report |
| `6799bfb` | Merge remote README updates |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `bef71b0` | Profile + Settings screens, header user menu |
| `86f5459` | Debate flow: Waiting Room, Debate Room, Results |
| `07e12e3` | Create Topic screen with validated form |
| `508c781` | Browse Topics screen with search + filter |
| `8df97e9` | Next.js scaffold, app shell, Home screen |
| `1e24aaf` | Initial scaffold + blueprint docs |
