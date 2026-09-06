# Debable — Complete Project Handbook

**Generated:** 2026-07-18 · **Last updated:** 2026-09-06 · **Project state:** Phases 1–7 complete, Phase 8 next
**Repository:** https://github.com/Aryan-Is-Here/Debable
**Local path:** `E:\Projects\Debable`

This is the full project reference: what Debable is, everything built so far, every decision made, and exactly how to continue — written so that anyone (a new developer, a future AI session, or you after a break) can pick the project up from this document alone.

---

## 1. What Debable is

Debable is a **random video debate platform** where strangers are matched by **debate topic** instead of random interests. Its differentiator is an **on-demand AI fact-checking assistant**: during a debate, either participant can submit one specific claim; the backend sends only that claim to an isolated AI service, which verifies it against trusted sources and posts the verdict into the debate chat.

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
| Video | LiveKit Cloud | ✅ In use |
| Auth | **Clerk** (backend verifies Clerk JWTs; no login endpoint) | ✅ Backend side done |
| AI | Gemini 3.6 Flash for judgment + our own retrieval (Tavily or Wikipedia) | ✅ In use |
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
├── frontend/                Next.js app — live against the API (no mock data left in the debate loop)
│   ├── app/                 Routes (see §4)
│   ├── components/          Feature components + components/ui/ (shadcn)
│   ├── hooks/               use-debate-chat, use-auth-ready
│   ├── lib/                 types.ts, utils.ts, mock/, validation/
│   ├── services/            API clients: api-client, topics, match, video, chat, fact-check
│   └── styles/              (empty — globals live in app/globals.css)
├── backend/                 FastAPI service — Phases 2-7 complete
│   ├── app/
│   │   ├── main.py          App factory: CORS, lifespan, exception handlers
│   │   ├── __main__.py      Dev entrypoint (`python -m app`) — see §5.11
│   │   ├── core/            config.py, logging.py, errors.py, platform.py
│   │   ├── db/              base.py (Base + mixins), session.py (engine, get_db)
│   │   ├── models/          user, topic, debate_room, message, fact_check, rating
│   │   ├── schemas/         health, topic, match, video, user, common (camelCase out)
│   │   ├── auth/            clerk.py, jwks.py, dependencies.py
│   │   ├── api/v1/          router, health, topics, match (incl. video token)
│   │   ├── services/        topic, match, video, chat, fact_check
│   │   ├── repositories/    topic, match, message, fact_check
│   │   ├── websocket/       registry, auth, protocol (Phase 6)
│   │   ├── ai/              base, gemini, stub, factory (Phase 7)
│   │   └── search/          base, tavily, wikipedia (Phase 7)
│   ├── tests/               216 tests; most need Postgres and SKIP without it
│   ├── migrations/          Alembic env + 4 revisions (0001-0004)
│   ├── pyproject.toml       uv-managed deps, ruff + pytest config
│   ├── alembic.ini
│   └── .env.example
├── docker/                  docker-compose.yml (db + api), Dockerfile.backend
├── .github/                 (empty — CI lands when useful)
├── shared/                  (empty — cross-cutting contracts if ever needed)
└── scripts/                 (empty)
```

---

## 4. Everything built so far (Phases 0–7)

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
14. **Presence is proven by polling, never promised on exit.** A closed tab cannot reliably withdraw itself — unload handlers are unreliable and the request needs a token there is no time to fetch. `match_queue.last_seen_at` is refreshed by every status poll; entries that stop being refreshed are excluded from matching and swept. Apply the same shape to any future "who is here" state.
15. **Never gate a poll on a mutation.** The waiting room's poll was `enabled` only once the join mutation succeeded; when the mutation didn't resolve, nothing polled while cached data kept the screen looking alive. Read endpoints are safe to call at any time — let the poll be the source of truth and the mutation merely an action. The waiting room also owns its interval explicitly rather than using `refetchInterval`, whose behaviour depends on the interaction of `enabled`, `staleTime` and window focus.
16. **The waiting room carries a dev-only diagnostic line** (`dev · join=… · status=… · fetch=… · last poll …`), hidden in production. It exists because a spinner looks identical whether the client is polling, failing silently, or not polling at all — three rounds of debugging were spent on that ambiguity. Keep it.
17. **Migrations are hand-checkable:** after editing models, autogenerate or hand-write the revision, then prove equivalence with `alembic check`. Constraint names come from the naming convention in `app/db/base.py` — name new `CheckConstraint`s with the short form (`score_range`), not the full `ck_…` string, or the convention will double the prefix.
18. **⚠️ The chat connection registry is per-process.** `app/websocket/registry.py` holds
    `room_id -> sockets` in memory, so two debaters served by *different* uvicorn workers
    would each broadcast into an empty set and see none of the other's messages. This is the
    same trap that ruled out an in-memory matchmaking queue in Phase 4; the difference is
    that a queue could move into Postgres while a broadcast needs a channel. **Phase 9 must
    either pin the API to one worker or put a broker behind `broadcast()`.** Persistence is
    unaffected — messages are committed before they are broadcast, so the worst case is a
    message that needs a reload to appear, not one that is lost.
19. **CORS does not apply to WebSockets.** `CORSMiddleware` never sees a handshake, so
    `cors_origins` constrains the REST API and nothing else. The chat socket checks `Origin`
    itself in `app/websocket/auth.py`; any future socket must do the same.
20. **`now()` is the transaction start time in Postgres.** Rows inserted in one transaction
    share a `created_at` down to the byte, so anything ordered by it needs either a tiebreak
    that means something or `clock_timestamp()`. Chat messages hit this exactly: with a
    random-UUID tiebreak, three messages in one transaction came back shuffled. See
    `app/repositories/message.py`.
21. **A browser `WebSocket` cannot set an `Authorization` header**, which is why chat
    authenticates from its first frame rather than a header or a query string. Reuse
    `resolve_user` in `app/auth/dependencies.py` — it is the shared half of `get_current_user`
    and exists so HTTP and socket paths cannot disagree about who a caller is.
22. **Socket tests open their client inside the test body, not a fixture.** `httpx-ws`'s
    transport holds an anyio cancel scope, and anyio requires the task that entered one to
    exit it — but pytest-asyncio finalises async fixtures in a different task. A fixture
    yielding an entered client fails in teardown with "attempted to exit cancel scope in a
    different task". `open_ws_client` in `tests/conftest.py` is a helper for this reason.
    Related: httpx-ws wraps handler exceptions in nested `ExceptionGroup`s, so asserting on a
    close code needs unwrapping (`close_code` in `tests/test_chat_socket.py`).
23. **Never infer a fact from a proxy that merely correlates with it.** Two Phase 5 bugs were
    the same mistake: participant *presence* was read off whether a camera track existed
    (turning a camera off unpublishes the track, so "camera off" and "never joined" became
    indistinguishable), and the opponent's *mute state* was read off nothing at all — the tile
    never passed the prop. Ask the source of truth: `useRemoteParticipants()` for presence,
    `useIsMuted()` for mute. This is the same lesson as §5.14 (presence is proven, never
    promised) and it was re-learned anyway, which is why it is written twice.
24. **Test the configuration you do not expect.** Both bugs above survived a Phase 5 manual
    check that passed, because that check ran with both cameras on. They surfaced in Phase 6
    only because someone happened to have a camera off. When verifying by hand, toggle the
    optional things — camera, mic, one tab closed — not just the happy path.
25. **⚠️ Verify a third party's free tier with a real call before designing around it.** In
    Phase 7 the published documentation was wrong twice, in ways that would each have broken
    the design at integration time: `gemini-2.5-flash` is listed with a free grounding quota
    but returns `404 no longer available to new users`, and every 3.x model lists grounding as
    unavailable *and* 429s on the first call. One throwaway script cost one request and saved
    a rewrite. This is the Phase 5 lesson (validate LiveKit credentials before building on
    them) generalised, and Phase 7 had to learn it twice.
26. **Development only works on `http://localhost:3000`.** A LAN address or `127.0.0.1`
    breaks three things at once: Clerk never loads (the dev instance is bound to specific
    origins), CORS blocks the API, and the chat socket's `Origin` check refuses the
    handshake. `useAuthReady` now explains the first one rather than spinning forever, but
    the address is still the fix. To serve another device, update `CORS_ORIGINS`,
    `NEXT_PUBLIC_API_BASE_URL` and Clerk's allowed origins together.
27. **Clerk cannot say "I will never load".** `useAuth` has only *loading* and
    *loaded-with-an-answer*, so `!isLoaded ? spinner : …` spins forever when anything upstream
    is wrong. Use `useAuthReady` from `frontend/hooks/use-auth-ready.ts`, which adds
    `stalled`. Its `stalled` is **derived** (`!isLoaded && timedOut`) rather than reset in an
    effect — clearing it there is a synchronous setState in an effect body (§5.3).

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
uv run pytest             # 216 tests; most SKIP without Postgres — always check the skip count
```
Whole stack in containers instead: `docker compose -f docker/docker-compose.yml up -d --build`.

---

## 6. Decisions locked & open conflicts

### Locked
| Decision | Detail |
|---|---|
| Auth = Clerk | Client-side login UI from Clerk; backend verifies Clerk-issued JWTs; `POST /auth/login` from doc 05 is **dropped** (done — no such endpoint exists) |
| AI service isolation | Backend calls AI over HTTP; AI never listens continuously. **LLM default was Anthropic Claude; superseded in Phase 7 by Google Gemini** — the project has no budget, and Claude has no free tier. The isolation property is unchanged: `app/ai/` is a client, only the submitted claim crosses the boundary, and everything sits behind a `FactCheckProvider` protocol so the provider is a one-file swap (it has already changed twice) |
| Frontend stack details | See §2/§5 — base-nova, npm, no src/ dir, `@/*` alias |
| Backend stack details | uv + Python 3.11, async SQLAlchemy 2 over psycopg 3, ruff, pytest; API versioned under `/api/v1` |
| Progress reports | A cumulative report is written to `docs/progress/` at the **start of every phase** and committed |

### Resolved
| # | Conflict / gap | Resolved in | Outcome |
|---|---|---|---|
| 4 | Schema gaps: no timestamps on Users/Topics; no `created_at` on Ratings; `FactChecks.sources` untyped | Phase 2 | `created_at`/`updated_at` on **every** table via `TimestampMixin`; `sources` is **JSONB** defaulting to `[]`. Also added `fact_checks.explanation` (the UI needs it) and `users.clerk_user_id`. |
| 5 | Local Postgres — Docker wasn't installed | Phase 2 | **Docker Desktop installed** (on `E:`). `docker/docker-compose.yml` runs `postgres:16-alpine` with a healthcheck, plus an optional `api` service. |
| 2 | `POST /match` mechanics undefined | Phase 4 | **A `match_queue` table in Postgres**, paired inside one transaction with `SELECT … FOR UPDATE SKIP LOCKED`, delivered by the waiting room **polling** every 2s. In-memory was rejected because a deployed backend runs several workers, so per-process queues would leave two people waiting on the same topic in separate queues. Polling rather than WebSocket because the WS layer does not exist until Phase 6. |
| 7 | `Topic.activeDebaters` was a computed count with nothing behind it | Phase 4 | Now the live count of queue rows per topic, resolved with one grouped query per page. Stale entries are excluded. |
| 3 | Chat transport: doc 05 REST vs `websocket/` dir | Phase 6 | **Both, for the halves each is good at.** History is REST (`GET /rooms/{id}/messages`) so it stays readable when the socket is down and testable without one; delivery is `WS /rooms/{id}/chat`. Persistence is the `messages` table either way, and a message is committed *before* it is broadcast. Doc 05's `POST /room/{id}/message` is **dropped** — a send that succeeded while the socket was dead would leave the sender staring at nothing. |

### Open — resolve at the stated phase, never silently
| # | Conflict / gap | Phase | Working proposal |
|---|---|---|---|
| 1 | Reports feature (PRD + `POST /report`) has **no DB table** in doc 04 | 9 | Add `Reports` table (id, room_id, reporter_id, reported_user_id, reason, created_at) |
| 6 | **`Topic.category` exists only in the frontend.** `lib/types.ts` marks it UI-only and Browse filters on it, but doc 04 has no such column. Worse, `getCategories()` derives the list from *existing topics*, so against an empty database the Create form's select is empty and no topic can ever be created. | 3 | **Decided (2026-08-10):** indexed `varchar` column plus a single shared allowlist constant validated by both the zod schema and the backend. No Postgres enum and no `CHECK` constraint — the frontend select must know the list anyway, so a migration would add cost without adding protection. Values: Technology, Science, Politics, Economics, Society, Ethics, Health, Environment, Education, Culture (`Work` folds into Economics; remap the mock topic using it). |
| 8 | Clerk configuration | 3 | **Resolved (2026-08-10).** Development instance `distinct-kitten-15.clerk.accounts.dev`; `CLERK_ISSUER` set in `backend/.env`, JWKS verified live through `ClerkTokenVerifier` (one RS256 key). Remaining Phase 3 work: add the publishable key to the frontend, mount `<ClerkProvider>`, replace the disabled "Sign in" button, and confirm a real session token verifies end to end. The session token must carry `email`, `username` and `image_url` claims (configured in the Clerk dashboard) — `get_current_user` reads exactly those. |

---

### Phase 4 — Matchmaking ✅ (branch `feature/matchmaking`)

Two people who pick the same topic are paired into a real, persisted debate room.

| Area | What exists |
|---|---|
| Queue | `match_queue`, one row per waiting user, deleted the instant a pair forms |
| Pairing | `SELECT … FOR UPDATE SKIP LOCKED` — two simultaneous joins cannot claim the same opponent. Tested with genuinely concurrent connections, since row locking is invisible inside one transaction |
| Liveness | `last_seen_at` heartbeat refreshed by every poll; stale entries are excluded and swept |
| Endpoints | `POST`/`GET`/`DELETE /api/v1/match`, `GET /api/v1/rooms/{id}`, `POST /api/v1/rooms/{id}/end` |
| Rooms | `you`/`opponent` resolved per caller; non-participants get 403; ending is idempotent and frees both sides |
| Frontend | Waiting room joins, polls every 2s, shows elapsed time and how many others wait, withdraws on cancel or navigate-away; debate room loads the real room by id |

**Bugs this phase cost three rounds to find — all worth remembering:**

1. The withdraw-on-leave effect depended on Clerk's `getToken`, whose identity changes as the session settles. React runs an effect's cleanup when dependencies change, not only on unmount, so the page withdrew itself from the queue while the user watched.
2. Rooms only end via the End debate button, so closing the tab left one open — and joining used to *return* an open room, trapping both participants forever with a partner who had left. Joining now ends it.
3. The poll was gated on the join mutation succeeding (see §5.15).
4. The machine's clock ran 13s behind Clerk's; Clerk stamps `nbf`, so freshly minted tokens were intermittently rejected. Verification now allows 60s of skew.

---

### Phase 5 — Video ✅ (branch `feature/video`)

Real one-to-one WebRTC through LiveKit, replacing the mock tiles.

| Area | What exists |
|---|---|
| Token | `POST /api/v1/rooms/{id}/token` mints a short-lived LiveKit token. A POST because it creates a credential and must never be cached |
| Grant | Minimal by design — join one named room, publish and subscribe, nothing else. No create, admin, list, record or ingress. Identity is the local user id, not a client claim |
| Refusals | Non-participants (403), unknown rooms (404), ended debates (409), unconfigured server (503, fails closed) |
| Tests | 9 tests that **decode the signed token** rather than trusting the SDK, including asserting administrative powers are absent |
| Frontend | `components/debate-video.tsx` connects and renders both tracks; mute and camera drive the real local track; permission-denied, no-device, reconnecting and disconnected all have explicit states |

**Verified live:** both accounts see and hear each other.

⚠️ **This section used to claim "mute crosses between windows". It did not.** Two bugs in
`ParticipantFrame` survived until they were found by hand during Phase 6 (fixed in `85f1dd0`):
the opponent's tile never passed the `muted` prop, so an opponent always rendered as unmuted;
and presence was inferred from whether a camera track existed, so a debater who turned their
camera off appeared — to the other side only — never to have joined. Presence now comes from
`useRemoteParticipants()`. See §5.23.

Testing note that is not a bug: two windows on one machine feed back through the speakers
(use headphones), and Chrome may refuse to hand the same webcam to two tabs.

---

### Phase 6 — Chat ✅ (branch `feature/chat`)

Real-time text between the two debaters, persisted, replacing `ChatPanel`'s fixtures. This
resolves conflict #3 and is what makes the Phase 7 fact-check deliverable — the verdict is
posted *into* the chat.

| Area | What exists |
|---|---|
| Transport | `WS /api/v1/rooms/{id}/chat` for delivery, `GET /api/v1/rooms/{id}/messages` for history. Persist first, broadcast second |
| Auth | An authenticate-first frame (`{"type":"auth","token":…}`), not a query-string token, which would put a Clerk JWT in access logs. Reuses `ClerkTokenVerifier` and the new `resolve_user` — one verification path, not two. A silent socket is closed after 5s |
| Origin | Checked at the handshake, because **CORS does not apply to WebSockets** |
| Guard | The same `to_room_read()` participant check as `GET /rooms/{id}`, so the two cannot drift apart. Ended rooms stay readable but refuse new messages |
| Refusals | Before `ready`: close with 4401/4403/4404/4409, mirroring the HTTP status. After `ready`: an error frame, socket stays open — a mistyped empty message should not cost the connection |
| Echo | The sender is echoed rather than rendering its own copy, so both windows show the row the server stored instead of optimistic state that can disagree with it |
| Registry | In-process, `room_id -> sockets`. **Does not survive multiple workers** — see §5.18 |
| Frontend | `hooks/use-debate-chat.ts` owns the socket: auth frame, history on `ready`, live frames buffered during the fetch, reconciliation by id, backoff to 15s. `ChatPanel` gained a connection notice and a dev-only readout |
| Tests | 27 new (136 total, 0 skipped), including two sockets in one room, ordering, registry cleanup, and that a broadcast message is in the REST history afterwards |

**Two bugs found while testing, both real:**

1. **Postgres `now()` is the transaction start time**, so messages written inside one
   transaction shared a timestamp and the ordered read fell through to its random-UUID
   tiebreak and returned them *shuffled*. `add_message` now sets `created_at` to
   `clock_timestamp()` explicitly. No migration — the column default remains the fallback.
2. **httpx-ws's transport holds an anyio cancel scope**, and pytest-asyncio finalises async
   fixtures in a different task than it sets them up in, so a fixture yielding an entered
   client died in teardown. The client is opened inside each test body instead.

---

### Phase 7 — AI Fact Check ✅ (branch `feature/fact-check`)

The differentiator: either debater submits one claim, it is checked against trusted sources,
and the verdict is pushed into the chat both people are already reading.

| Area | What exists |
|---|---|
| Retrieval | **Ours, not the model's.** `app/search/` — Tavily when `TAVILY_API_KEY` is set (1,000/month free, no card), Wikipedia when it is not (no account at all) |
| Judgment | `app/ai/gemini.py` — Gemini 3.6 Flash, structured JSON output, `temperature=0` |
| Trust boundary | `app/core/sources.py`. With Tavily it is enforced **at retrieval** via `include_domains` + `include_domains_mode="filter"`; the service-layer filter then runs as defence in depth |
| Citations | Cannot be invented — the model picks from numbered sources by index, and out-of-range indices are discarded |
| Endpoints | `POST /rooms/{id}/fact-check`, `GET /rooms/{id}/fact-checks`, plus a `fact_check` socket frame broadcast to both debaters |
| Limits | Per-room hourly **and** a global daily budget, both counted from the `fact_checks` table so they survive restarts and multiple workers |
| Tests | 27 new (216 total, 0 skipped). **None touch a network** |

**Three configurations, each degrading to something needing no credentials:** no keys → stub
verdicts (the whole flow still works on a fresh clone); `GEMINI_API_KEY` → real verdicts from
Wikipedia; `+ TAVILY_API_KEY` → the full allowlist. Nothing downstream changes at any step.

**The rule the phase is built around:** `UNVERIFIED` is a *verdict* — checked, nothing
settles it. `FactCheckUnavailable` is an *error* — never checked. They must never collapse
into one another: recording failures as `unverified` would fill the dataset with claims
nobody examined, persisted and indistinguishable from real results. A failed check stores
nothing.

**What the plan got wrong, and how.** The phase chose Anthropic, then Gemini-with-grounding,
and shipped neither — the provider changed twice before a line of the service layer existed.
Free Google Search grounding is unobtainable: `gemini-2.5-flash` is 404 for new users, and
3.x grounding is a zero quota that 429s on the first call. Only a real API call showed this;
the pricing page said otherwise. See §5.25.

Being forced to retrieve separately **improved** the design: the allowlist became a retrieval
constraint rather than a citation filter, and with no tool in the request, structured output
works.

**Two more bugs found by running it:** Wikimedia enforces its User-Agent policy (a generic
agent gets a 403), and Wikipedia was missing from the trusted-source allowlist — a test
actively asserted it was untrusted — so every Wikipedia-backed verdict was silently
downgraded to `unverified`.

**Verified live:** *"The Great Depression began with a stock market crash in 1929"* → `true`,
citing real articles. Confirmed by hand in two windows.

---

## 7. How to continue — Phase 8 in extreme detail

**Goal:** Ratings. The last mock data in the product, and the instrument that records
whether a debate went well.

**Branch:** `feature/ratings`

### What is already in place
The schema does most of the work. `app/models/rating.py` already carries a `UniqueConstraint`
on `(room_id, reviewer_id)`, a `CheckConstraint` for the 1–5 range, and another forbidding
self-review. So the service translates an `IntegrityError` into a clean 409 rather than
re-checking — the same shape `match.join` already uses. `RatingForm` exists and has been
rendering since Phase 1.

### The three remaining mock call-sites
- `app/debate/[roomId]/results/page.tsx` — uses `mockDebateRoom` for **any** roomId, so
  rating currently "works" while rating nothing. Load the real room via `getRoom`, exactly as
  `components/debate-room-loader.tsx` does.
- `app/profile/page.tsx` — `mockProfile`. Debates count and average rating become real.
- `components/settings-view.tsx` — `currentUser`. Read from Clerk instead.

### Step-by-step
1. `app/repositories/rating.py` and `app/services/rating.py`. Guard with `to_room_read()`
   from `app/services/match.py`, as chat and fact-check both do.
2. `POST /rooms/{id}/rating`.
3. Wire `RatingForm`; load the real room on the results page.
4. Real profile stats.
5. Tests: a participant may rate once; a second attempt is 409; a non-participant is 403;
   self-rating is refused; a score outside 1–5 is 422.

### A note on the project's goal
`docs/01-product-vision.md` states the MVP success metric as *"two strangers can successfully
debate and use AI fact-checking during the conversation"* — a **capability** metric, met by
Phase 7. The handoff framing, *"can fact-checking improve debates?"*, is an **outcome**
question that nothing currently measures.

Phase 8 does not have to answer it, and by decision it does not. But it should not foreclose
it either: `ratings.room_id` and `fact_checks.room_id` join on the same room, so "debates
with a fact-check versus without" stays a query rather than a migration. Keep it that way.

### Phases 9–10 (summary map)
- **Phase 9 Polish & Deploy:** resolve conflict #1 (Reports); `POST /report` + minimal UI; deploy per doc 09; a11y/dark-mode/QA pass.
- **Phase 10 Professional UI/UX Redesign:** the full visual overhaul, deliberately last.

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

*This handbook lives at `docs/PROJECT-HANDBOOK.md`. Shorter per-phase progress reports live in `docs/progress/`. Both are updated at each phase start. For running the project and checking each phase's output by hand, see `docs/DEMO-GUIDE.md`.*
