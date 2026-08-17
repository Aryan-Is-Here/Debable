# Debable — Progress Report

**Report date:** 2026-08-15 · **Milestone:** Start of Phase 6 (Chat)
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
| Phase 4 — Matchmaking | ✅ Complete |
| **Phase 5 — Video** | ✅ **Complete** (merged to `main`) |
| Phase 6 — Chat | 🔵 Starting now |
| Phase 7 — AI Fact Check | ⏳ Pending |
| Phase 8 — Ratings | ⏳ Pending |
| Phase 9 — Polish & Deploy | ⏳ Pending |
| Phase 10 — Professional UI/UX Redesign | ⏳ Pending |

**Halfway.** Five of ten phases are merged, and the core loop is real from sign-in through to
a live audio-and-video debate.

---

## Phases 0–4 in brief

**Phase 0** scaffolded the repository and locked the early decisions: Clerk for auth with no
login endpoint of our own, the AI fact-check as an isolated on-demand service, strictly
sequential phases with one branch each.

**Phase 1** built all eight screens against typed mock data. The decision that paid off
repeatedly was writing `lib/types.ts` as the contract first — when the real API arrived, the
screens changed data source rather than being rewritten.

**Phase 2** stood up FastAPI with async SQLAlchemy over psycopg 3, the six-table schema,
Alembic, Clerk JWT verification with a rotating JWKS cache, and a health endpoint that returns
503 when Postgres is unreachable rather than lying about it.

**Phase 3** delivered the first end-to-end slice: topics created and browsed through the real
API with server-side search, filtering and paging. Category was resolved as an indexed varchar
against a shared allowlist rather than a Postgres enum, since the frontend select must know
the list either way.

**Phase 4** paired debaters through a `match_queue` table using
`SELECT … FOR UPDATE SKIP LOCKED`, delivered by polling. It cost three rounds of debugging
after the feature "worked"; the lessons are recorded in
`docs/COMPLETE-PROGRESS-REPORT.md` §7 and are worth reading before Phase 6.

---

## Phase 5 — Video ✅

Real one-to-one WebRTC through LiveKit, replacing the mock tiles.

### What was built

- **`POST /api/v1/rooms/{id}/token`** mints a short-lived LiveKit access token. A POST rather
  than a GET because it creates a credential and must never be cached or prefetched.
- **The grant is the security boundary**, so it is deliberately minimal: join one named room,
  publish and subscribe within it, and nothing else — no create, admin, list, record or
  ingress. Identity is the local user id rather than anything the client claims, so tracks are
  attributable to a known debater.
- Refused for non-participants, unknown rooms and ended debates — a finished debate should not
  hand out fresh media credentials — and it fails closed when LiveKit is unconfigured.
- **Nine tests that decode what was actually signed** rather than trusting the SDK to have
  honoured its arguments, including asserting that administrative powers are absent and that
  both debaters receive distinct identities in the same room.
- The frontend renders both participants' real tracks, and mute and camera now drive the
  actual local track instead of component state.
- Media failure states were designed in rather than discovered: permission denied names the
  fix, a missing device says so, and reconnecting and disconnected are visible. A black
  rectangle is not an error message, and these are the common cases when strangers meet.

### Verified

Two accounts in one debate room see and hear each other, and **muting on one side is visible
on the other** — the check that matters, since a local-only toggle looked identical before
this phase. 109 backend tests pass; lint and build are clean on both sides.

### Why this phase took one round and Phase 4 took three

Two things differed. The LiveKit credentials were validated against the live API *before*
anything was built on them, which would have caught a truncated secret immediately. And the
failure states were treated as the main work rather than as polish, so there was no long tail
of "it just sits there" reports.

---

## What Phase 6 (starting now) will deliver

Real-time text chat between the two debaters, persisted, replacing ChatPanel's fixtures. This
also unblocks Phase 7, since the fact-check verdict is posted *into the chat*.

### Conflict #3 — the last transport question

Doc 05 specifies REST `POST /room/{id}/message`; the structure has always carried a
`websocket/` directory. The resolution to confirm at the start of the phase: **WebSocket for
delivery, the `messages` table for persistence.** REST alone cannot push the other side's
message without polling, and unlike a matchmaking queue — where two seconds of latency is
invisible — chat at two seconds feels broken.

Three things need deciding before code:

1. **Socket authentication.** A browser `WebSocket` cannot set an `Authorization` header.
   Either a token in the query string or an authenticate-first message; the latter avoids
   tokens in access logs. Reuse `ClerkTokenVerifier` rather than writing a second path.
2. **Reconnect behaviour.** History over REST with only new messages streamed, or replay
   through the socket. Either way the client must reconcile by message id, not position, or a
   reconnect duplicates the conversation.
3. **Whether matchmaking migrates onto the same socket.** It can once one exists, but the 2s
   poll is adequate and now well understood — this should not be bundled into Phase 6.

One trap to record while designing: an in-process connection registry does not survive
multiple worker processes. That is the same reasoning that ruled out an in-memory matchmaking
queue in Phase 4, and Phase 9's deployment must either pin to one worker or add a broker.

### The check that will prove it

A message sent in one window appears in the other **without a refresh**, and reloading either
window still shows the full history. Fixtures pass the first half of that test and fail the
second.

---

## Git history (main)

| Commit | Description |
|---|---|
| `4c328c4` | **Merge feature/video — Phase 5 complete** |
| `6457cff` | Handoff note and complete progress report |
| `eebdfc4` | Phase 5: LiveKit tokens and real video |
| `8448a47` | **Merge feature/matchmaking — Phase 4 complete** |
| `fe27248` | **Merge feature/topics — Phase 3 complete** |
| `e690651` | **Merge chore/rename-to-debable** |
| `5b67600` | **Merge feature/backend-foundation — Phase 2 complete** |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `1e24aaf` | Initial scaffold + blueprint docs |
