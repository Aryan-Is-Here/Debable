# DebateMatch — Complete Project Handbook

**Generated:** 2026-07-18 · **Last updated:** 2026-08-10 · **Project state:** Phases 1–2 complete, Phase 3 next
**Repository:** https://github.com/Aryan-Is-Here/Debable
**Local path:** `E:\Projects\Debable`

This is the full project reference: what DebateMatch is, everything built so far, every decision made, and exactly how to continue — written so that anyone (a new developer, a future AI session, or you after a break) can pick the project up from this document alone.

---

## 1. What DebateMatch is

DebateMatch is a **random video debate platform** where strangers are matched by **debate topic** instead of random interests. Its differentiator is an **on-demand AI fact-checking assistant**: during a debate, either participant can submit one specific claim; the backend sends only that claim to an isolated AI service, which verifies it against trusted sources and posts the verdict into the debate chat.

**MVP hypothesis being validated:** *Can AI-assisted fact-checking improve online debates?* Everything else is secondary.

### MVP scope (in)
Authentication · user profiles · topic creation · topic browsing · topic-based matchmaking · 1-to-1 video debates · text chat · on-demand AI fact-check · post-debate rating · basic reporting.

### MVP scope (out — do not build)
AI always-listening · automatic moderation · winner selection · points/ELO/leaderboards/badges · debate summaries · AI coaching · team debates · tournaments · premium features. If a request drifts into these, recommend postponing instead of implementing.

### Source of truth
The blueprint in `docs/` (13 documents: PRD, architecture, database, API spec, UI/UX, roadmap, git workflow, deployment, AI design, coding guidelines, vibe-coding playbook, prompt templates). It is deliberately skeletal. **Follow it; don't rewrite it unless asked.** Known gaps in it are tracked in §6 below — resolve each at its phase, never silently.

---

## 2. Tech stack

| Layer | Choice | Status |
|---|---|---|
| Frontend | Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind v4 | ✅ In use |
| UI kit | shadcn/ui **base-nova** style (built on `@base-ui`, NOT Radix), lucide icons | ✅ In use |
| Theming | next-themes (class strategy), wrapped in own `ThemeProvider` | ✅ In use |
| Forms | react-hook-form + zod v4 + `@hookform/resolvers` | ✅ In use |
| Toasts | sonner | ✅ In use |
| Server state | TanStack Query | ⏳ Planned (when real API exists) |
| Client state | Zustand | ⏳ Planned (only if needed) |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16, uv | ✅ In use |
| Video | LiveKit | ⏳ Phase 5 |
| Auth | **Clerk** (backend verifies Clerk JWTs; no login endpoint) | ✅ Backend side done |
| AI | RAG + LLM (default: Anthropic Claude), isolated service | ⏳ Phase 7 |
| Local dev | Docker Compose (postgres:16 + api) | ✅ In use |
| Deploy | Vercel (frontend), Railway/Fly.io (backend), Neon/Supabase (Postgres), LiveKit Cloud | ⏳ Phase 9 |

**Toolchain on this machine:** Node v24.16, npm 12.0.2 (no pnpm) · Python 3.11.9, uv 0.11.21 · Docker 29.6.2 + Compose v5.3.1 (Docker Desktop, installed on `E:`) · git with `gh` CLI absent (plain git + HTTPS remote works).

---

## 3. Repository layout

```
E:\Projects\Debable          (git repo, remote: Aryan-Is-Here/Debable)
├── docs/                    Blueprint (source of truth) + progress reports
│   ├── 01…12-*.md           PRD, architecture, DB, API, UI, roadmap, etc.
│   ├── 13-prompts/          Per-area prompt templates
│   └── progress/            Dated progress reports (one per phase start)
├── frontend/                Next.js app — COMPLETE for Phase 1
│   ├── app/                 Routes (see §4)
│   ├── components/          Feature components + components/ui/ (shadcn)
│   ├── hooks/               (empty — for future custom hooks)
│   ├── lib/                 types.ts, utils.ts, mock/, validation/
│   ├── services/            (empty — future API client layer)
│   └── styles/              (empty — globals live in app/globals.css)
├── backend/                 FastAPI service — COMPLETE for Phase 2
│   ├── app/
│   │   ├── main.py          App factory: CORS, lifespan, exception handlers
│   │   ├── __main__.py      Dev entrypoint (`python -m app`) — see §5.11
│   │   ├── core/            config.py, logging.py, errors.py, platform.py
│   │   ├── db/              base.py (Base + mixins), session.py (engine, get_db)
│   │   ├── models/          user, topic, debate_room, message, fact_check, rating
│   │   ├── schemas/         health.py (Pydantic I/O models)
│   │   ├── auth/            clerk.py, jwks.py, dependencies.py
│   │   ├── api/v1/          router.py, health.py
│   │   └── {services,repositories,websocket,ai,utils}/   (empty — later phases)
│   ├── tests/               conftest + health/auth/jwks/config suites (31 tests)
│   ├── migrations/          Alembic env + versions/0001_initial_schema.py
│   ├── pyproject.toml       uv-managed deps, ruff + pytest config
│   ├── alembic.ini
│   └── .env.example
├── docker/                  docker-compose.yml (db + api), Dockerfile.backend
├── .github/                 (empty — CI lands when useful)
├── shared/                  (empty — cross-cutting contracts if ever needed)
└── scripts/                 (empty)
```

---

## 4. Everything built so far (Phases 0–2)

### Phase 0 — Planning ✅
Repo scaffolded to the blueprint structure; blueprint extracted into `docs/`; git + GitHub wired; root `.gitignore` (Node+Python+env) and README. Opinionated configs (linters, CI, Docker) deliberately deferred to their phases.

### Phase 1 — UI Prototype ✅ (merged to `main` via `feature/ui-prototype`)

Every screen renders from **typed mock data** — there is no backend yet. The entire core loop is clickable end-to-end.

| Route | Screen | What it does | Key files |
|---|---|---|---|
| `/` | Home | Hero, how-it-works (3 steps), trending topics grid | `app/page.tsx` |
| `/browse` | Browse | Search (title/description, case-insensitive), category chips incl. "All", most-active sort, empty state | `app/browse/page.tsx`, `components/topic-browser.tsx` |
| `/create` | Create Topic | RHF+zod form (title 10–120, description 20–600, category required), mock submit → toast → `/browse` | `app/create/page.tsx`, `components/create-topic-form.tsx`, `lib/validation/topic.ts` |
| `/waiting` | Waiting Room | 4s simulated matchmaking with elapsed timer → opponent reveal → Enter debate | `app/waiting/page.tsx`, `components/waiting-room.tsx` |
| `/debate/[roomId]` | Debate Room | Mock video tiles (mute/camera toggles, "mock" badge), working chat panel, **fact-check dialog** (claim 10–300 chars → 1.2s mock latency → verdict card in chat: True/False/Misleading/Unverified + explanation + sources) | `app/debate/[roomId]/page.tsx`, `components/debate-room-view.tsx`, `chat-panel.tsx`, `fact-check-dialog.tsx`, `fact-check-card.tsx`, `video-tile.tsx` |
| `/debate/[roomId]/results` | Results/Rating | 1–5 stars (hover states) + optional comment (≤300), mock submit → toast → home | `app/debate/[roomId]/results/page.tsx`, `components/rating-form.tsx` |
| `/profile` | Profile | Identity, stats (debates, avg rating, joined), created topics, debate history with ratings | `app/profile/page.tsx`, `lib/mock/profile.ts` |
| `/settings` | Settings | **Functional** theme selector; read-only account fields ("managed by Clerk"); mock notification switches; mock danger-zone delete w/ confirm dialog | `app/settings/page.tsx`, `components/settings-view.tsx` |
| — | Login | **Intentionally not built** — Clerk replaces it in Phase 2 | header has disabled "Sign in" |

**Shared infrastructure:** `app/layout.tsx` (fonts, ThemeProvider, SiteHeader, Toaster) · `components/site-header.tsx` (nav with active states, theme toggle, user menu) · `components/user-menu.tsx` (avatar dropdown → Profile/Settings; stands in for Clerk's user button) · `components/topic-card.tsx` (reused on Home/Browse/Profile; links into `/waiting?topic=<id>`) · `lib/types.ts` (all view-models: `Topic`, `UserSummary`, `DebateRoom`, `ChatMessage`, `FactCheck`, `UserProfile`, …) · `lib/mock/` (users, topics, debate incl. deterministic `mockFactCheck()`, profile).

**shadcn primitives installed:** button, card, badge, avatar, dropdown-menu, separator, input, field, label, textarea, select, sonner, dialog, scroll-area, switch.

### Phase 2 — Backend Foundation ✅ (branch `feature/backend-foundation`)

A running FastAPI service with configuration, database, migrations, auth verification and
health checks. No feature endpoints yet — those start in Phase 3.

| Area | What exists | Key files |
|---|---|---|
| App shell | `create_app()` factory; CORS from settings; lifespan disposes the pool; docs/OpenAPI disabled in production | `app/main.py` |
| Errors | `AppError` hierarchy (404/409/401/403/503) + handlers giving every failure one envelope: `{"error": {"code", "message", "details?"}}` | `app/core/errors.py`, `app/main.py` |
| Config | pydantic-settings `Settings`; comma-separated env lists via `NoDecode` + a `before` validator; `.env.example` committed, `.env` ignored | `app/core/config.py` |
| Logging | Readable lines in dev, one JSON object per record in production; uvicorn loggers re-parented onto ours | `app/core/logging.py` |
| Database | Async engine (psycopg 3), memoised session factory, `get_db` that rolls back on exception and leaves commits to handlers | `app/db/session.py` |
| Schema | 6 tables, UUID PKs (`gen_random_uuid()`), `created_at`/`updated_at` everywhere, `fact_checks.sources` JSONB, deterministic constraint naming convention | `app/db/base.py`, `app/models/*` |
| Migrations | Alembic reading `DATABASE_URL` from the app's own settings; `0001_initial_schema`; verified with `alembic check` (no drift) and a `downgrade base` → `upgrade head` round trip | `migrations/`, `alembic.ini` |
| Auth | Clerk JWT verification: async JWKS cache with TTL + rotation refetch; checks signature, expiry, issuer, `azp`, and `aud` when configured; **fails closed** if `CLERK_ISSUER` is unset. `get_current_user` lazily provisions the local `users` row (race-safe) | `app/auth/*` |
| API | `/api/v1` router; `GET /api/v1/health` returns `{status, database, env, version}` and **503** when Postgres is unreachable | `app/api/v1/*` |
| Docker | `postgres:16-alpine` with a healthcheck + an `api` service built from `Dockerfile.backend` (uv, layer-cached deps) | `docker/*`, `.dockerignore` |
| Tests | 31 pytest tests — health (incl. the 503 path), config parsing, JWKS caching/rotation/failures, token verification (expired, wrong issuer, wrong key, wrong `azp`, wrong `aud`, no subject, garbage). No DB and no network needed | `tests/*` |

**Schema decisions made here** (beyond the bare doc 04 column lists):

- `users.clerk_user_id` unique — the join key to Clerk. Local rows are created on the first
  authenticated request; a Clerk webhook can replace that later without touching call sites.
- `fact_checks.explanation` added — doc 04 omits it but the UI renders it beside every verdict.
- `topics.status` and `fact_checks.verdict` are native Postgres enums whose values mirror the
  frontend's `lib/types.ts` unions exactly.
- Constraints: `debate_rooms` rejects self-debates; `ratings` enforces score 1–5, no
  self-review, and one rating per reviewer per room (the Phase 8 rule, in the schema already).
- Delete rules: `CASCADE` from a room to its messages/fact-checks/ratings; `RESTRICT` on the
  author/participant links so a user row cannot vanish out from under a debate transcript.

**Verified end to end:** `alembic upgrade head` against the compose Postgres → `python -m app`
→ `GET /api/v1/health` = 200 `{"status":"ok","database":"ok"}`; container stopped → 503 with
`"database":"error"`; container restarted → 200 again; the same health check also passes from
inside the built `api` image.

---

## 5. Conventions & gotchas (READ BEFORE CODING)

1. **base-nova ≠ Radix.** Components come from `@base-ui`. Composition uses the **`render` prop**, never `asChild`:
   - `<Button render={<Link href="/x" />}>Label</Button>`
   - `<DialogTrigger render={<Button variant="secondary" />}>…</DialogTrigger>`
   - `asChild` fails the TypeScript build.
2. **Forms:** base-nova has no Radix-style `<Form>` wrapper. Pair react-hook-form (`register`/`Controller`) with the `Field`/`FieldLabel`/`FieldError` primitives; `FieldError` accepts an RHF-shaped `errors` array.
3. **Hydration-safe client state:** don't `setState` in `useEffect` to detect mount (lint error `react-hooks/set-state-in-effect`); use `useSyncExternalStore(() => () => {}, () => true, () => false)` as in `settings-view.tsx`.
4. **Server vs client:** pages stay server components; interactivity lives in dedicated `"use client"` components. Keep it that way.
5. **Mock layer is the contract:** when the backend arrives, replace `lib/mock/*` call-sites with a `services/` API client returning the same `lib/types.ts` shapes. Screens shouldn't need rewrites.
6. **Verification loop for every change:** `npm run lint` → `npm run build` (type-checks) → smoke-test routes (dev server + curl or browser). Nothing merges without all three green.
7. **Git workflow:** one feature per branch (`feature/<name>`), explain plan → files → risks before implementing, commit with conventional messages, push, merge to `main` when the phase/feature is complete. Never force-push `main` — it has received direct edits from Aryan (README) twice; always `git fetch` + merge.
8. **Windows quirks:** LF→CRLF warnings on commit are normal noise. No `.gitattributes` yet (optional improvement). Bash is available (Git Bash paths like `/tmp` work).
9. **Communication style (per project init):** think like a senior engineer; explain plan, list files to change, call out risks before coding; recommend postponing non-MVP features; ask when requirements are ambiguous; don't overengineer.
10. **Backend verification loop:** `uv run ruff check .` → `uv run ruff format --check .` → `uv run pytest` → for schema changes also `uv run alembic upgrade head` and `uv run alembic check` (must report no new operations). Nothing merges without all of them green.
11. **⚠️ Windows + psycopg:** the async driver cannot run on Python's default `ProactorEventLoop`. Start the API with `uv run python -m app` (not bare `uvicorn`) — `app/core/platform.py` selects the selector policy before the loop is created, and `migrations/env.py` does the same. Linux/macOS/Docker are unaffected.
12. **Config lists from env:** pydantic-settings JSON-decodes `list[str]` fields before validators run. Any new comma-separated setting must use the `CsvList` alias in `app/core/config.py`, otherwise `A,B` in `.env` raises a parse error at startup.
13. **Errors:** raise `AppError` subclasses from services/repositories rather than `HTTPException`, so those layers stay framework-free and every response keeps the same envelope.
14. **Migrations are hand-checkable:** after editing models, autogenerate or hand-write the revision, then prove equivalence with `alembic check`. Constraint names come from the naming convention in `app/db/base.py` — name new `CheckConstraint`s with the short form (`score_range`), not the full `ck_…` string, or the convention will double the prefix.

### How to run the frontend
```bash
cd E:\Projects\Debable\frontend
npm install        # first time only
npm run dev        # http://localhost:3000  (Ctrl+C to stop)
npm run lint       # ESLint
npm run build      # production build + type-check
```
Demo path: Browse → "Debate" on a card → wait ~4s → Enter debate → chat, Fact-check a claim → End debate → rate → Home. Try the theme toggle and mobile width.

### How to run the backend
```bash
docker compose -f docker/docker-compose.yml up -d db     # Postgres 16 on :5432
cd E:\Projects\Debable\backend
cp .env.example .env      # first time only
uv sync                   # first time only
uv run alembic upgrade head
uv run python -m app      # http://localhost:8000 — docs at /docs
uv run pytest             # 31 tests, no DB or network required
```
Whole stack in containers instead: `docker compose -f docker/docker-compose.yml up -d --build`.

---

## 6. Decisions locked & open conflicts

### Locked
| Decision | Detail |
|---|---|
| Auth = Clerk | Client-side login UI from Clerk; backend verifies Clerk-issued JWTs; `POST /auth/login` from doc 05 is **dropped** (done — no such endpoint exists) |
| AI service isolation | Backend calls AI over HTTP; AI never listens continuously; LLM default = Anthropic Claude |
| Frontend stack details | See §2/§5 — base-nova, npm, no src/ dir, `@/*` alias |
| Backend stack details | uv + Python 3.11, async SQLAlchemy 2 over psycopg 3, ruff, pytest; API versioned under `/api/v1` |
| Progress reports | A cumulative report is written to `docs/progress/` at the **start of every phase** and committed |

### Resolved
| # | Conflict / gap | Resolved in | Outcome |
|---|---|---|---|
| 4 | Schema gaps: no timestamps on Users/Topics; no `created_at` on Ratings; `FactChecks.sources` untyped | Phase 2 | `created_at`/`updated_at` on **every** table via `TimestampMixin`; `sources` is **JSONB** defaulting to `[]`. Also added `fact_checks.explanation` (the UI needs it) and `users.clerk_user_id`. |
| 5 | Local Postgres — Docker wasn't installed | Phase 2 | **Docker Desktop installed** (on `E:`). `docker/docker-compose.yml` runs `postgres:16-alpine` with a healthcheck, plus an optional `api` service. |

### Open — resolve at the stated phase, never silently
| # | Conflict / gap | Phase | Working proposal |
|---|---|---|---|
| 1 | Reports feature (PRD + `POST /report`) has **no DB table** in doc 04 | 9 | Add `Reports` table (id, room_id, reporter_id, reported_user_id, reason, created_at) |
| 2 | `POST /match` mechanics undefined | 4 | Decide queue model (in-DB queue vs in-memory), delivery (poll vs WS) |
| 3 | Chat transport: doc 05 REST vs `websocket/` dir | 6 | WS for delivery, persist via Messages table |
| 6 | **`Topic.category` exists only in the frontend.** `lib/types.ts` marks it UI-only and Browse filters on it, but doc 04 has no such column — so category survives no round trip through the API. | 3 | Add a `category` column to `topics` (short enum or free text?) and mirror the allowed values in the zod schema. **Decide the value set before writing the Phase 3 migration.** |
| 7 | **`Topic.activeDebaters` is a computed count**, not a stored column. | 3/4 | Derive it (count of waiting users per topic) once matchmaking exists; until then Browse shows a placeholder. Do not add a denormalised column without a reason. |
| 8 | **Clerk is not configured yet.** `CLERK_ISSUER` is blank, so token verification correctly fails closed and no authenticated route can be exercised end to end. | 3 | Create the Clerk application, put the issuer in `backend/.env`, add the frontend keys, and confirm a real token verifies before building authenticated endpoints. |

---

## 7. How to continue — Phase 3 in extreme detail

**Goal:** Topics. The first real feature slice, end to end: create and list topics through the
API, and replace the frontend's topic mocks with live data. This is also the phase where the
frontend stops being self-contained, so the seams matter more than the endpoints do.

**Branch:** `feature/topics`

### Decide before writing code
1. **Conflict #6 — `category`.** Browse filters by it and Create requires it, but no column
   exists. Pick a fixed set (enum, migration needed whenever it changes) or free text with a
   curated list in the UI. Whatever you pick, the zod schema in
   `frontend/lib/validation/topic.ts` and the backend validator must agree exactly.
2. **Conflict #8 — Clerk.** `POST /topics` needs an authenticated creator, so the Clerk app has
   to exist first: create it, set `CLERK_ISSUER` in `backend/.env`, add the publishable key to
   the frontend, and verify one real token against `get_current_claims` before building on it.
3. **Conflict #7 — `activeDebaters`.** Leave it out of the API for now, or return `0`. It is a
   matchmaking-queue count and there is no queue until Phase 4.

### Step-by-step
4. **Migration** for the `category` decision (plus any index Browse's filter needs).
5. **Repository** (`app/repositories/topic.py`): query/persist functions taking an
   `AsyncSession`. No FastAPI imports here.
6. **Service** (`app/services/topic.py`): business rules — ownership, validation beyond field
   shape, raising `AppError` subclasses.
7. **Schemas** (`app/schemas/topic.py`): `TopicCreate`, `TopicRead`, `UserSummary`. Match
   `frontend/lib/types.ts` field-for-field; that file *is* the contract.
8. **Endpoints** (`app/api/v1/topics.py`): `POST /api/v1/topics` (auth required, creator from
   `get_current_user`) and `GET /api/v1/topics` (public; search + category filter + pagination
   server-side, since Browse currently filters client-side over mocks).
9. **Tests:** repository/service tests against a real Postgres (a throwaway compose database or
   a per-test transaction), plus endpoint tests with the auth dependency overridden.
10. **Frontend wiring:** add TanStack Query + a `services/topics.ts` client returning existing
    `lib/types.ts` shapes; swap `lib/mock/topics.ts` call-sites in Browse/Create/Home. Screens
    should not need rewrites — if one does, the API shape drifted from the view-model.
11. **Verify both sides:** backend loop from §5.10; frontend `npm run lint` + `npm run build`;
    then click Browse → Create → Browse and confirm the new topic is really persisted.
12. **Commit → push → merge** when green.

### Phases 4–9 (summary map)
- **Phase 4 Matchmaking:** resolve conflict #2; `POST /match` + queue; Waiting Room polls/WS; creates DebateRooms.
- **Phase 5 Video:** LiveKit Cloud; backend mints room tokens; replace `VideoTile` mock with LiveKit React components.
- **Phase 6 Chat:** resolve conflict #3; WS endpoint in `app/websocket/`; persist Messages; swap ChatPanel mock transport.
- **Phase 7 AI Fact Check:** isolated `app/ai/` service client + separate AI service (RAG over trusted sources, Claude); `POST /room/{id}/fact-check`; result broadcast into chat; replace `mockFactCheck`.
- **Phase 8 Ratings:** `POST /room/{id}/rating`; wire RatingForm; enforce one rating per debater per room.
- **Phase 9 Polish & Deploy:** resolve conflict #1 (Reports); `POST /report` + minimal UI; deploy per doc 09; a11y/dark-mode/QA pass.

Each phase: new branch, plan first, progress report at phase start, blueprint-conflict check, tests where appropriate, merge on green.

---

## 8. Git history of `main` (oldest → newest)

| Commit | Description |
|---|---|
| `1e24aaf` | chore: initial scaffold and blueprint docs |
| `03b5607` / `2c8fd99` | Aryan: first commit / README rename |
| `8df97e9` | feat(frontend): Next.js scaffold, app shell, Home |
| `508c781` | feat(frontend): Browse Topics (search + filter) |
| `07e12e3` | feat(frontend): Create Topic (validated form) |
| `86f5459` | feat(frontend): debate flow (Waiting/Debate/Results) |
| `bef71b0` | feat(frontend): Profile + Settings + user menu |
| `52f4a37` | Merge feature/ui-prototype — **Phase 1 complete** |
| `f23bdbf` / `bdf7ad9` | Aryan: README cleanup/enhancement |
| `6799bfb` | Merge remote README updates |
| `2f7f2b1` | docs: Phase 2 start progress report |
| `1ce336f` | docs: comprehensive project handbook |
| `32d95f3` | feat(backend): Phase 2 backend foundation — **Phase 2 complete** (on `feature/backend-foundation`) |

---

*This handbook lives at `docs/PROJECT-HANDBOOK.md`. Shorter per-phase progress reports live in `docs/progress/`. Both are updated at each phase start.*
