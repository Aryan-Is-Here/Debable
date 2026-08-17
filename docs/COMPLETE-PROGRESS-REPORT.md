# Debable — Complete Progress Report

**Written:** 2026-08-14 · **Updated:** 2026-08-15 · **Repository:** https://github.com/Aryan-Is-Here/Debable
**State:** Phases 0–5 merged to `main`. Phase 6 (Chat) is next.

This is the full narrative: what the product is, how it has been built, why every tool was
chosen over its alternatives, what remains, and what will bite you. Companion documents:
[`HANDOFF.md`](../HANDOFF.md) for picking up mid-flight, [`PROJECT-HANDBOOK.md`](PROJECT-HANDBOOK.md)
for the working reference, [`DEMO-GUIDE.md`](DEMO-GUIDE.md) for checking each phase by hand.

---

## 1. The product

Debable matches strangers for one-to-one video debates **by topic** rather than by random
interest. Mid-debate either participant can submit a single claim for an **on-demand AI
fact-check**; only that claim goes to an isolated AI service, and the verdict lands in the
debate chat.

**The MVP tests one hypothesis: can AI-assisted fact-checking improve online debates?** That
sentence settles scope arguments. Everything that does not serve it waits.

**In scope:** auth, profiles, topic creation and browsing, topic-based matchmaking, 1:1 video,
text chat, on-demand fact-check, post-debate rating, basic reporting.

**Explicitly out:** always-listening AI, automated moderation, winner selection, points, ELO,
leaderboards, badges, debate summaries, AI coaching, team debates, tournaments, premium tiers.
If a request drifts here, the correct answer is to recommend postponing it.

The blueprint in `docs/01`–`docs/12` is the source of truth. It is deliberately skeletal; its
gaps are tracked as numbered conflicts (§6) and resolved at the phase that needs them, never
silently.

---

## 2. Tech stack, and why not the alternative

Every row below was a real choice. The rejected option matters as much as the chosen one.

### Frontend

| Choice | Why | Why not the alternative |
|---|---|---|
| **Next.js 16** (App Router, Turbopack) | Server components keep data fetching off the client; one framework covers routing, SSR and bundling | Plain React + Vite would need a separate router and no SSR story; the marketing surface (Home, Browse) benefits from server rendering |
| **React 19** | Required by Next 16 | — |
| **TypeScript** | `lib/types.ts` is the contract between frontend and API; drift becomes a compile error rather than a runtime surprise | JavaScript would have let the camelCase/snake_case mismatch reach production silently |
| **Tailwind v4** | Utility CSS with no naming overhead; dark mode via a class strategy | CSS Modules mean inventing names for one-off layouts; styled-components adds runtime cost |
| **shadcn/ui, base-nova style** | Components are copied into the repo, so they can be edited rather than fought | A packaged library (MUI, Chakra) means overriding someone else's opinions at every turn |
| **TanStack Query** | Server cache, retries and invalidation without hand-rolled loading state | Plain `useEffect` + `useState` per screen; redux-toolkit-query would drag in a store the app does not need |
| **Zustand** | Planned, not installed | Deliberately deferred — no client state has yet justified it. Adding a store "for later" is how apps get one they do not need |

Note on base-nova: it is built on **`@base-ui`, not Radix**. Composition uses the `render`
prop, never `asChild`. Getting this wrong fails the TypeScript build.

### Backend

| Choice | Why | Why not the alternative |
|---|---|---|
| **FastAPI** | Async-native, Pydantic validation and OpenAPI docs generated from the code, so `/docs` can never drift | Django REST Framework brings an ORM, admin and migration stack we would fight against a Clerk-owned user model; Flask would need the async and validation story assembled by hand |
| **SQLAlchemy 2 (async)** | Typed models, real relationships, and Alembic for migrations | Raw SQL means hand-writing every join and migration; Tortoise/Piccolo have far smaller ecosystems when something goes wrong |
| **psycopg 3** | Current Postgres driver with first-class async | asyncpg is faster but has a different SQL dialect surface with SQLAlchemy, and speed is not the constraint here. **Cost of this choice:** psycopg's async driver cannot run on Windows' default `ProactorEventLoop` (see §7) |
| **PostgreSQL 16** | JSONB for fact-check sources, and `FOR UPDATE SKIP LOCKED` — which is what makes matchmaking correct | SQLite has no JSONB, no `ILIKE`, and no row locking; MySQL's `SKIP LOCKED` exists but JSONB support is weaker |
| **Alembic** | Versioned, reversible schema changes; `alembic check` proves models and database agree | `create_all()` cannot evolve a schema that already holds data |
| **uv** | Fast, lockfile-based, single tool for envs and deps | pip + venv + requirements.txt has no real lockfile; Poetry is slower and heavier |
| **ruff** | Lint and format in one fast tool | black + isort + flake8 is three tools and three configs |
| **pytest** | Fixtures compose cleanly, which the transactional database fixture depends on | unittest is more ceremony for less power |

### Services

| Choice | Why | Why not the alternative |
|---|---|---|
| **Clerk** (auth) | Sign-in UI, sessions, OAuth and account management for free; the backend only verifies JWTs against public JWKS and never stores a password | Rolling our own means owning password hashing, reset flows, email verification and breach risk — weeks of work orthogonal to the hypothesis. Auth0 is comparable but has a heavier free-tier footprint |
| **LiveKit Cloud** (video) | Managed SFU; peer-to-peer WebRTC does not survive NAT without TURN, and running our own SFU is a project in itself | Raw WebRTC needs signalling, STUN/TURN and renegotiation written by hand; Daily/Agora are similar but LiveKit's self-host path keeps an exit route open |
| **Anthropic Claude** (AI, Phase 7) | Strong instruction-following for a structured verdict; the fact-check must return a verdict, an explanation and real sources | Decided at Phase 0; revisit only if the RAG design demands it |
| **Docker Compose** (local Postgres) | One command for a real Postgres that matches production | A native install is machine-specific and hard to reset; a hosted database makes offline work impossible |

---

## 3. How the code is organised

```
frontend/
  app/            Routes. Server components by default.
  components/     Feature components; components/ui/ is shadcn.
  lib/            types.ts (the contract), validation/, constants/, mock/
  services/       API clients — the only place that knows the API exists
backend/
  app/api/v1/     HTTP layer only: routing, status codes, dependencies
  app/services/   Business rules; owns transactions; raises AppError
  app/repositories/  Queries and persistence; imports no web framework
  app/models/     SQLAlchemy models
  app/schemas/    Pydantic request/response models (camelCase out)
  app/auth/       Clerk verification
  app/core/       config, logging, errors, platform shims
  migrations/     Alembic
docker/           compose (Postgres + optional API) and the backend Dockerfile
docs/             Blueprint, handbook, demo guide, progress reports
```

The layering rule: **repositories never import FastAPI, services never raise
`HTTPException`.** Services raise `AppError` subclasses that the edge translates into one
error envelope, `{"error": {"code", "message", "details?"}}`. This keeps the domain testable
without a web server and gives the frontend one error shape to handle.

---

## 4. Phase-by-phase, with the decisions made

### Phase 0 — Planning ✅

Repo scaffolded to the blueprint structure. Locked: Clerk for auth (so `POST /auth/login` from
doc 05 is dropped), the AI fact-check as an isolated on-demand service, strictly sequential
phases with one branch each, and a progress report at every phase start.

### Phase 1 — UI Prototype ✅

All eight screens built against typed mock data, no backend. Home, Browse, Create, Waiting
Room, Debate Room, Results, Profile, Settings.

**The decision that paid off repeatedly:** `lib/types.ts` was written as the contract, and the
mock layer produced exactly those shapes. When the real API arrived in Phase 3, screens did
not need rewriting — only their data source changed. The backend serialises camelCase
specifically to preserve that.

### Phase 2 — Backend Foundation ✅

FastAPI app factory, pydantic-settings configuration, logging that switches to JSON in
production, async SQLAlchemy, the six-table schema, Alembic, Clerk JWT verification with a
rotating JWKS cache, and a health endpoint that returns **503 when Postgres is unreachable**
rather than lying.

Schema decisions beyond the blueprint's column lists:

- `created_at`/`updated_at` on every table; `fact_checks.sources` as JSONB (conflict #4).
- `users.clerk_user_id` unique — the join key to Clerk. Local rows are provisioned on the
  first authenticated request, race-safely. A webhook can replace that later without touching
  call sites.
- `fact_checks.explanation` added; doc 04 omits it but the UI renders it.
- Constraints encode the rules: no self-debates, ratings 1–5, no self-reviews, one rating per
  reviewer per room — the Phase 8 rule, in the schema from the start.
- Delete rules: `CASCADE` from a room to its messages, fact-checks and ratings; `RESTRICT` on
  author links so a user cannot vanish from under a debate transcript.

### Phase 3 — Topics ✅

First end-to-end slice. Repository/service/schema split, `GET /topics` with **server-side**
search, category filter and paging (filtering the current page client-side would silently hide
matches), `POST /topics` behind a verified session, duplicate titles rejected because two
identically named topics split debaters across separate matchmaking pools.

**Conflict #6 — `category`.** Resolved as an indexed `varchar` validated against a shared
allowlist, not a Postgres enum. The frontend's `<Select>` must know the list either way, so an
enum would add a migration to every change without adding protection. No `CHECK` constraint,
for the same reason. Ten values, mirrored in `backend/app/core/categories.py` and
`frontend/lib/constants/categories.ts` — **change both together.**

Three bugs found here, all pre-existing:

1. The Phase 2 error handler could not serialise its own 422 — a validator raising `ValueError`
   puts the exception object in Pydantic's `ctx`, which `json.dumps` rejects.
2. The category list was derived from existing topics, so an empty database offered no
   categories and the first topic could never have been created.
3. Button-styled links warned on every render. Base UI's `Button` expects a native `<button>`;
   the documented escape hatch applies `role="button"`, which makes screen readers announce a
   link as a button. Fixed with a `ButtonLink` that styles a real link.

### Phase 4 — Matchmaking ✅

**Conflict #2 — mechanics.** A `match_queue` table in Postgres, paired inside one transaction
using `SELECT … FOR UPDATE SKIP LOCKED`, delivered by polling every 2s.

- *Not in-memory*, because a deployed backend runs several worker processes: per-process
  queues would leave two people waiting on the same topic in separate queues, never to meet.
  It also loses the queue on every dev reload.
- *Not Redis*, which adds a service to run for a queue holding a handful of rows.
- *Not WebSocket*, because the WS layer does not exist until Phase 6; building one here means
  building it twice. A queue is somewhere people expect to wait, so 2s costs nothing.

`SKIP LOCKED` is the load-bearing part: when two people arrive at once, neither may claim the
same opponent. That is tested with genuinely concurrent connections, because row locking is
invisible inside a single transaction.

**Conflict #7** closed as a side effect: `activeDebaters` is now the live queue count.

This phase cost three rounds of debugging after it "worked". See §7 — those lessons are the
most valuable output of the phase.

### Phase 5 — Video ✅

`POST /api/v1/rooms/{id}/token` mints a short-lived LiveKit token. A POST because it creates a
credential and must never be cached.

The grant is the security boundary, so it is minimal: join one named room, publish and
subscribe, nothing else — no create, admin, list, record or ingress. Identity is the local
user id, not anything the client claims. Refused for non-participants, unknown rooms, and
ended debates; fails closed when unconfigured. The tests **decode what was signed** rather
than trusting the SDK to have honoured the arguments.

The frontend renders real tracks and wires mute/camera to the actual local track. Media
failure states — permission denied, no device, reconnecting, disconnected — get as much
attention as the happy path, because they are the common cases when strangers meet.

**Verified live:** two accounts in one debate room see and hear each other, and muting on one
side is visible on the other. That last part is the check that matters — a local-only toggle
looked identical before this phase.

Notably this phase took one round, against Phase 4's three. The difference was having the
failure states designed in from the start rather than discovered, and validating the LiveKit
credentials against the API *before* building on them.

---

## 5. What remains

### Phase 6 — Chat
Resolves **conflict #3** (doc 05 says REST, the structure has `websocket/`). Plan: WebSocket in
`app/websocket/` for delivery, persisted to the existing `messages` table, replacing
ChatPanel's fixtures. Matchmaking can move onto the same socket afterwards if the poll ever
feels slow. Watch for: authenticating the socket handshake with a Clerk token, and reconnect
without duplicating messages.

### Phase 7 — AI Fact Check
The differentiator. Isolated `app/ai/` client plus a separate AI service doing RAG over trusted
sources with Claude. `POST /room/{id}/fact-check`, result broadcast into chat, replacing
`mockFactCheck`. Watch for: latency (the user is mid-conversation), hallucinated sources —
citations must be real and load — and cost per call. The verdict vocabulary
(`true`/`false`/`misleading`/`unverified`) is already fixed in the schema and the frontend.

### Phase 8 — Ratings
`POST /room/{id}/rating`, wire `RatingForm`. The one-rating-per-reviewer-per-room rule already
exists as a unique constraint, so the service only needs to translate the violation into a
clean error.

### Phase 9 — Polish & Deploy
Resolves **conflict #1**: the Reports feature has no table in doc 04 — add
`reports(id, room_id, reporter_id, reported_user_id, reason, created_at)`. Then deploy per doc
09: Vercel (frontend), Railway or Fly.io (backend), Neon or Supabase (Postgres), LiveKit Cloud.
Create **production** Clerk and LiveKit instances — the current ones are development
instances with usage limits and a browser warning.

### Phase 10 — Professional UI/UX Redesign
Full visual and interaction overhaul, at Aryan's request, deliberately **last**. Redesigning
screens whose behaviour is still moving means paying twice — the debate room alone changes
shape in Phases 5, 6 and 7. Until then, judge work on whether it functions, not how it looks.

---

## 6. Open conflicts

| # | Gap | Phase |
|---|---|---|
| 1 | Reports feature has no DB table in doc 04 | 9 |
| 3 | Chat transport: doc 05 says REST, structure has `websocket/` | 6 |

Resolved: #2 and #7 (Phase 4), #4 and #5 (Phase 2), #6 and #8 (Phase 3).

---

## 7. Things to be careful about

**Windows + psycopg.** The async driver cannot run on the default `ProactorEventLoop`. Start
the backend with `uv run python -m app`, never bare `uvicorn`; `app/core/platform.py` sets the
policy before the loop is created, and Alembic does the same. Linux, macOS and Docker are
unaffected.

**The test suite skips silently without Docker.** 63 of 109 tests need Postgres and skip when
it is unreachable, so a "green" run can be nearly meaningless. Check the skip count.

**Clock skew breaks auth intermittently.** This machine measured 13.3s behind Clerk, and Clerk
stamps `nbf`, so fresh tokens were rejected as not-yet-valid. Verification now allows 60s of
skew, but keep the system clock synchronised.

**Never gate a poll on a mutation.** The waiting room's poll was `enabled` only once the join
mutation succeeded; when the mutation did not resolve, nothing polled while cached data kept
the screen looking alive. Read endpoints are safe to call at any time.

**Effect cleanups run on dependency change, not only unmount.** Clerk's `getToken` identity
changes as the session settles; an effect depending on it withdrew the user from the queue
mid-session. Mirror such values into a ref and give the cleanup an empty dependency array.

**Presence must be proven, never promised.** A closed tab cannot reliably withdraw itself.
`match_queue.last_seen_at` is refreshed by every poll; entries that stop being refreshed are
excluded and swept. Use the same shape for any future "who is here" state.

**Rooms do not end themselves.** Only the End debate button sets `ended_at`. Joining a new
debate now closes any abandoned room; without that, both participants were trapped forever.

**Instrument before guessing.** A spinner looks identical whether the client is polling,
failing silently, or not polling at all. The dev-only readout in `waiting-room.tsx` exists
because that ambiguity cost three debugging rounds. Keep it, and reach for that kind of
evidence first.

**base-nova is not Radix.** Compose with the `render` prop, never `asChild`. Use `ButtonLink`
for navigation and `Button` for actions.

**Two known lint rules bite repeatedly.** No `setState` synchronously in an effect body, and
no reading `ref.current` during render. Both have caught real bugs here.

**Category lists live in two languages.** `backend/app/core/categories.py` and
`frontend/lib/constants/categories.ts` must match, or Create fails with a 422.

**Secrets.** `backend/.env` and `frontend/.env.local` are gitignored and must stay that way.
The Clerk secret key is needed by `@clerk/nextjs` server-side but never by the Python backend.
The LiveKit secret is a signing key — the browser only ever receives a minted token.

---

## 8. Verification status

| Area | Evidence |
|---|---|
| Backend suite | 109 tests pass, including concurrent pairing, queue liveness and token grants |
| Lint/format | `ruff check`, `ruff format --check`, `eslint` all clean |
| Build | `npm run build` compiles all 9 routes, no type errors |
| Migrations | `alembic check` reports no drift; up/down round trip verified |
| Health | 200 with the database up, 503 with it stopped, recovers without restart |
| Topics | Confirmed by hand: a topic created in the UI survives a reload |
| Matchmaking | Confirmed by hand: two accounts, two windows, both flip to matched, same room |
| Video | Confirmed by hand: two accounts see and hear each other; mute crosses between them |
