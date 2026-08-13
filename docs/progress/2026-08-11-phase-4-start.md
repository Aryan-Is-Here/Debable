# Debable — Progress Report

**Report date:** 2026-08-11 · **Milestone:** Start of Phase 4 (Matchmaking)
**Repository:** https://github.com/Aryan-Is-Here/Debable

This report is generated at the start of each new phase and covers all progress to date.

---

## Where we are

| Phase | Status |
|---|---|
| Phase 0 — Planning | ✅ Complete |
| Phase 1 — UI Prototype | ✅ Complete |
| Phase 2 — Backend Foundation | ✅ Complete |
| **Phase 3 — Topics** | ✅ **Complete** (merged to `main`) |
| Phase 4 — Matchmaking | 🔵 Starting now |
| Phase 5 — Video | ⏳ Pending |
| Phase 6 — Chat | ⏳ Pending |
| Phase 7 — AI Fact Check | ⏳ Pending |
| Phase 8 — Ratings | ⏳ Pending |
| Phase 9 — Polish & Deploy | ⏳ Pending |
| Phase 10 — Professional UI/UX Redesign | ⏳ Pending |

---

## Phases 0–2 in brief

**Phase 0** scaffolded the repository to the blueprint structure and locked the early
decisions: Clerk for auth with no login endpoint of our own, the AI fact-check as an
isolated on-demand service, and strictly sequential phases with one branch each.

**Phase 1** built all eight screens against typed mock data — Home, Browse, Create,
Waiting Room, Debate Room, Results, Profile, Settings — on Next.js 16, React 19,
Tailwind v4 and shadcn/ui in the base-nova style.

**Phase 2** stood up the FastAPI service: settings, structured logging, async SQLAlchemy
over psycopg 3, the six-table schema with timestamps everywhere and `fact_checks.sources`
as JSONB, Alembic, Clerk JWT verification with a rotating JWKS cache, and a health
endpoint that reports database connectivity honestly (503 when Postgres is down).

---

## Phase 3 — Topics ✅

The first slice that runs end to end. Browse, Home and Create now read and write real rows.

### Backend

- Repository, service and schema layers separated: repositories hold queries and import no
  web framework, services own transaction boundaries and raise `AppError` subclasses that
  the edge translates into the shared error envelope.
- `GET /api/v1/topics` with server-side search, category filter, paging and a total count.
  Filtering client-side would have quietly hidden matches beyond the first page.
- `GET /api/v1/topics/{id}`, `GET /api/v1/topics/categories`, and `POST /api/v1/topics`
  behind a verified Clerk session.
- Migration `0002` adds `topics.category` as an indexed varchar validated against an
  allowlist in `app/core/categories.py`, deliberately not a Postgres enum — the frontend
  select has to know the list anyway, so an enum would add a migration to every change
  without adding protection.
- Duplicate titles are rejected. Two identically named topics would split debaters across
  separate matchmaking pools, which defeats the point of matching by topic.
- Responses serialise to camelCase to match `frontend/lib/types.ts` exactly, and never
  include the creator's email.

### Frontend

- Clerk wired in: provider, proxy, real sign-in and sign-up, and a user button carrying
  links to our own Profile and Settings screens.
- TanStack Query with the client created per render tree, so a server render never shares
  a cache between users.
- A `services/` API client that turns the backend's error envelope into a typed `ApiError`.
- Browse queries the API with debounced search, category chips, paging, loading skeletons
  and a retryable error state.
- Create submits for real, maps a 409 onto the title field, and shows a sign-in prompt to
  signed-out visitors.

### Bugs found and fixed along the way

1. **The Phase 2 error handler could not serialise its own 422.** A field validator raising
   `ValueError` puts the exception object into Pydantic's error `ctx`, which `json.dumps`
   rejects. Every endpoint with a custom validator would have hit this.
2. **The category list was derived from existing topics**, so an empty database offered no
   categories and the very first topic could never have been created.
3. **Button-styled links warned on every render.** Base UI's `Button` expects a native
   `<button>`; the documented escape hatch applies `role="button"`, which would have screen
   readers announce a link as a button. Replaced with a `ButtonLink` that styles a real
   link, and added the `aria-current` the nav had always lacked visually.

### Conflicts resolved

| # | Conflict | Outcome |
|---|---|---|
| 6 | `Topic.category` had no column | Indexed varchar plus a shared allowlist; ten agreed values |
| 8 | Clerk unconfigured | Development instance live; issuer verified against real JWKS |

### Verified

60 backend tests, ruff clean, frontend lint and build clean. Against live Postgres:
search and category filters return the right rows, unauthenticated `POST` is refused with
401, and the response shape matches the frontend view-models. Aryan confirmed the
persistence check by hand — a topic created in the UI survives a page reload.

---

## What Phase 4 (starting now) will deliver

Topic-based matchmaking: two people who pick the same topic get paired into a real debate
room, replacing the Waiting Room's four-second simulation.

### Conflict #2 resolved — matchmaking mechanics

The blueprint specified `POST /match` and nothing about how it works. The decision:

**A `match_queue` table in Postgres, paired inside one transaction using
`SELECT ... FOR UPDATE SKIP LOCKED`, with the Waiting Room polling for its result.**

An in-memory queue was rejected on a specific ground rather than taste: a deployed backend
runs more than one worker process, and per-process dictionaries mean two users waiting on
the same topic would sit in separate queues and never meet. It also loses the queue on
every reload during development. Redis would work but adds a service to run for a queue
that will hold a handful of rows.

Polling rather than WebSocket because the WS layer does not exist until Phase 6. Building
one here means building it twice. A queue is somewhere people expect to wait, so a couple
of seconds of latency costs nothing, and Phase 6 can push match events down the real
socket later without changing the queue model.

This also closes conflict #7: `Topic.activeDebaters` becomes a count of queue rows per
topic, which is what the field always meant.

---

## Git history (main)

| Commit | Description |
|---|---|
| `fe27248` | **Merge feature/topics — Phase 3 complete** |
| `ba11818` | Render button-styled links as real links |
| `5187acd` | Topic API and live frontend data |
| `c6af3e5` | Settle Clerk and category decisions, add Phase 10 |
| `abace45` | Per-phase inspection guide |
| `e690651` | **Merge chore/rename-to-debable** |
| `5b67600` | **Merge feature/backend-foundation — Phase 2 complete** |
| `1ce336f` | Comprehensive project handbook |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `1e24aaf` | Initial scaffold + blueprint docs |
