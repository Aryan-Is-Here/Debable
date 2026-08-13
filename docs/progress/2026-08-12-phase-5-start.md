# Debable — Progress Report

**Report date:** 2026-08-12 · **Milestone:** Start of Phase 5 (Video)
**Repository:** https://github.com/Aryan-Is-Here/Debable

This report is generated at the start of each new phase and covers all progress to date.

---

## Where we are

| Phase | Status |
|---|---|
| Phase 0 — Planning | ✅ Complete |
| Phase 1 — UI Prototype | ✅ Complete |
| Phase 2 — Backend Foundation | ✅ Complete |
| Phase 3 — Topics | ✅ Complete |
| **Phase 4 — Matchmaking** | ✅ **Complete** (merged to `main`) |
| Phase 5 — Video | 🔵 Starting now |
| Phase 6 — Chat | ⏳ Pending |
| Phase 7 — AI Fact Check | ⏳ Pending |
| Phase 8 — Ratings | ⏳ Pending |
| Phase 9 — Polish & Deploy | ⏳ Pending |
| Phase 10 — Professional UI/UX Redesign | ⏳ Pending |

---

## Phases 0–3 in brief

**Phase 0** scaffolded the repository and locked the early decisions: Clerk for auth with no
login endpoint of our own, the AI fact-check as an isolated on-demand service, strictly
sequential phases with one branch each.

**Phase 1** built all eight screens against typed mock data on Next.js 16, React 19,
Tailwind v4 and shadcn/ui in the base-nova style.

**Phase 2** stood up the FastAPI service: settings, structured logging, async SQLAlchemy over
psycopg 3, the six-table schema, Alembic, Clerk JWT verification with a rotating JWKS cache,
and a health endpoint that reports database connectivity honestly.

**Phase 3** delivered the first end-to-end slice — topics created and browsed through the real
API, with server-side search, filtering and paging, and the frontend reading live data through
a typed client. Category was resolved as an indexed varchar validated against a shared
allowlist rather than a Postgres enum.

---

## Phase 4 — Matchmaking ✅

Two people who pick the same topic are paired into a real, persisted debate room. The Waiting
Room's four-second simulation is gone.

### Conflict #2 resolved

A `match_queue` table in Postgres, paired inside one transaction using
`SELECT … FOR UPDATE SKIP LOCKED`, with the Waiting Room polling for the result.

An in-memory queue was rejected on a specific ground: a deployed backend runs several worker
processes, so per-process queues would leave two people waiting on the same topic in separate
queues, never to meet. Polling rather than WebSocket because the WS layer does not exist until
Phase 6, and building one here means building it twice.

This also closed conflict #7 — `Topic.activeDebaters` is now the live count of queue rows.

### What was built

- `POST`/`GET`/`DELETE /api/v1/match`, `GET /api/v1/rooms/{id}`, `POST /api/v1/rooms/{id}/end`.
- Rooms resolve `you`/`opponent` per caller, so the UI never works out which side it is on;
  non-participants get a 403 rather than a peek.
- Concurrency correctness tested with genuinely concurrent connections rather than the shared
  test transaction, since row locking is invisible inside one.
- Waiting Room joins, polls every two seconds, shows elapsed time and how many others wait,
  and withdraws on cancel or navigate-away.

### Four bugs, and what each one teaches

This phase took three rounds of debugging after the feature "worked". All four causes are
worth carrying forward:

1. **The page withdrew itself from the queue.** The withdraw-on-leave effect depended on
   Clerk's `getToken`, whose identity changes as the session settles — and React runs an
   effect's cleanup whenever its dependencies change, not only on unmount.
2. **Abandoned rooms trapped both debaters.** Rooms only end via the End debate button, so
   closing a tab left one open; joining used to *return* an open room, so both participants
   stayed permanently "already debating" with a partner who had left. Joining now ends it.
3. **The poll was gated on a mutation.** The query was enabled only once the join mutation
   succeeded; when it did not resolve, nothing polled while cached data kept the screen
   looking alive. Read endpoints are safe to call at any time — the poll is now the source of
   truth and the join is merely an action.
4. **The machine's clock ran 13 seconds behind Clerk's.** Clerk stamps `nbf`, so freshly
   minted tokens were intermittently rejected as not-yet-valid. Verification now allows sixty
   seconds of skew.

A methodological note: two of these were diagnosed from the wrong evidence first — a log file
belonging to a different backend process, and an assumption about background windows that an
isolated harness later disproved. What finally settled it was a development-only readout under
the spinner showing the poll's actual state. A spinner looks identical whether the client is
polling, failing silently, or not polling at all; that ambiguity cost more time than any of
the bugs. The readout stays.

### Verified

100 backend tests including concurrent pairing and queue liveness; lint, format and build
green on both sides. Aryan confirmed the end-to-end check by hand: two accounts, two windows,
same topic — each sees the other's waiting count, both flip to matched, and both land in the
same room.

---

## What Phase 5 (starting now) will deliver

Real one-to-one video and audio between matched debaters, replacing the mock `VideoTile`
placeholders with LiveKit.

The backend mints short-lived LiveKit access tokens scoped to a single room and identity,
issued only to that room's two participants and refused once the debate has ended. The
frontend joins the room and renders real tracks, with the existing mute and camera controls
wired to the local track instead of component state.

**Needs before live verification:** a LiveKit Cloud project. Its URL, API key and API secret
go into `backend/.env`; the secret is a signing key and belongs nowhere else. Most of the
phase can be built before those exist — only the call itself needs them.

The work that usually matters most here is not the happy path but the failure states: camera
or microphone denied, no device attached, connection dropped. A black rectangle is not an
error message.

---

## Git history (main)

| Commit | Description |
|---|---|
| `8448a47` | **Merge feature/matchmaking — Phase 4 complete** |
| `53facc6` | Decouple the waiting-room poll from the join mutation |
| `26737c1` | Stop abandoned rooms trapping both debaters |
| `336ebd3` | Stop the waiting room withdrawing itself from the queue |
| `faf5a98` | Phase 4 matchmaking: queue, pairing, rooms |
| `fe27248` | **Merge feature/topics — Phase 3 complete** |
| `e690651` | **Merge chore/rename-to-debable** |
| `5b67600` | **Merge feature/backend-foundation — Phase 2 complete** |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `1e24aaf` | Initial scaffold + blueprint docs |
