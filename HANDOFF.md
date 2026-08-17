# Debable — Handoff

**Written:** 2026-08-14 · **Updated:** 2026-08-15 · **Branch:** `main` (commit `4c328c4`) · **Working tree:** clean

Read this first if you are picking the project up mid-flight. For the full reference see
[`docs/PROJECT-HANDBOOK.md`](docs/PROJECT-HANDBOOK.md); for the narrative and every decision's
reasoning see [`docs/COMPLETE-PROGRESS-REPORT.md`](docs/COMPLETE-PROGRESS-REPORT.md).

---

## 1. The goal

**Debable** is a random video debate platform that matches strangers by *debate topic* rather
than by random interest. Its differentiator is an **on-demand AI fact-check**: mid-debate,
either participant submits one specific claim, the backend sends only that claim to an
isolated AI service, and the verdict is posted into the debate chat.

The MVP exists to answer one question: **can AI-assisted fact-checking improve online
debates?** Every scope decision defers to that. Leaderboards, ELO, always-listening AI,
moderation, tournaments and premium tiers are explicitly out.

Ten phases, built strictly in order, one branch each. **Phases 0–5 are merged to `main`.**
Phase 6 (Chat) is next and has not been started.

---

## 2. Current state of the code

| Phase | State |
|---|---|
| 0 Planning | ✅ merged |
| 1 UI Prototype | ✅ merged — 8 screens, then mock data |
| 2 Backend Foundation | ✅ merged — FastAPI, Postgres, Alembic, Clerk verification, health |
| 3 Topics | ✅ merged — real topic CRUD, frontend on live data |
| 4 Matchmaking | ✅ merged — queue, pairing, debate rooms |
| 5 Video | ✅ merged — real LiveKit audio and video, verified live |
| **6 Chat** | 🔵 **next, not started** |
| 7–10 | ⏳ not started |

**Works end to end today:** sign in with Clerk → browse and search real topics → create a
topic that survives a reload → queue for a topic → get paired with a second account → land in
a shared debate room → **see and hear each other over real WebRTC**, with mute and camera
state visible to the other side. Aryan has confirmed all of that by hand.

**Verified by tests:** 109 backend tests pass (`cd backend && uv run pytest`). Frontend lint
and production build are clean. 63 of those tests need Postgres and *skip silently* if Docker
is not running — check the skip count before trusting a green run.

**Still mock, by design:** chat messages are fixtures and do not cross between windows
(Phase 6), the fact-check verdict is deterministic mock output (Phase 7), the rating form does
not persist (Phase 8), and Profile shows mock stats.

The core loop is now real from sign-in through to a live debate. What remains is making the
*conversation* real — chat, then the fact-check that the whole product exists to test.

### Running it

```bash
docker compose -f docker/docker-compose.yml up -d db
cd backend && uv run alembic upgrade head && uv run python -m app
cd frontend && npm run dev
```

Use `python -m app`, never bare `uvicorn`: on Windows psycopg's async driver cannot run on the
default `ProactorEventLoop`, and that entrypoint fixes the policy before the loop is created.

Secrets live in `backend/.env` and `frontend/.env.local`, both gitignored. Required:
`DATABASE_URL`, `CLERK_ISSUER`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`;
frontend needs `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and
`CLERK_SECRET_KEY`.

---

## 3. Where Phase 6 will land

Nothing is mid-edit — the tree is clean and Phase 5 is merged. These are the files Phase 6
(Chat) will touch, and the ones worth reading first:

| File | Why it matters to Phase 6 |
|---|---|
| `backend/app/websocket/` | **Empty.** Scaffolded in Phase 0 for exactly this; the WS endpoint goes here |
| `backend/app/models/message.py` | The `messages` table already exists — room, sender, content, timestamps, and an index on `(room_id, created_at)` for "this room, oldest first" |
| `backend/app/auth/dependencies.py` | HTTP auth. A socket handshake cannot send an `Authorization` header the same way, so this needs a companion path |
| `backend/app/services/match.py` | `to_room_read()` holds the participant check that must also guard the socket |
| `frontend/components/chat-panel.tsx` | Currently renders `initialMessages` fixtures |
| `frontend/components/debate-room-view.tsx` | Owns `messages` state and `handleSend`; `mockFactCheck` still lives here until Phase 7 |
| `frontend/lib/mock/debate.ts` | The fixtures to replace |

## 4. What was tried and failed

Phase 4 took **three rounds of debugging after the feature "worked"**. The failures are more
instructive than the fixes, and two of them were wrong diagnoses of mine.

### Fixes that were correct but were not the reported bug

1. **`refetchIntervalInBackground`.** Diagnosed the stalled waiting room as TanStack Query
   skipping fetches while `document.visibilityState === "hidden"`. That behaviour is real —
   the source confirms the interval fires and skips the request — but it was **not** the
   cause here. The setting was kept because it is correct for genuinely hidden windows.
2. **The 60-second clock-skew allowance in Clerk verification.** Real and measured (this
   machine ran 13.3s behind Clerk, and Clerk stamps `nbf`, so fresh tokens were intermittently
   rejected). Worth keeping, but it explained scattered 401s, not the stall.

### The methodological failures worth remembering

3. **Read the wrong log file.** Counted "zero `GET /match` requests" from `/tmp/api7.log`,
   which belonged to a backend process of mine. Port 8000 was owned by Aryan's own backend in
   his terminal, so that log could never have contained his traffic. A whole diagnosis was
   built on it.
4. **Four isolation harnesses that all failed to reproduce.** A throwaway page replicating the
   waiting room's hook structure — `enabled` gate flipped by a mutation, cache seeded by that
   mutation's `onSuccess`, function-form `refetchInterval`, one-second re-render tick, Clerk's
   `getToken` inside `queryFn` — **polled correctly every time.** Each added difference was
   exonerated. Reverse-engineering the observer's internals was abandoned as a poor use of
   time after three attempts.
5. **Guessing instead of instrumenting.** What finally resolved it was a development-only
   readout under the spinner (`dev · join=… · status=… · fetch=… · last poll …`). It showed
   `join=false` with `status=queued` — the query was disabled while stale cache kept the
   screen looking alive. That line should have been the *first* move, not the fourth. It is
   still in `waiting-room.tsx` and should stay.

### The actual root causes, once found

- The withdraw-on-leave effect depended on Clerk's `getToken`, whose identity changes as the
  session settles — and React runs an effect's cleanup when dependencies change, not only on
  unmount. The page was withdrawing itself from the queue while the user watched.
- Rooms only end via the End debate button, so closing a tab left one open — and joining used
  to *return* an open room, trapping both participants with a partner who had left.
- The poll was gated on the join mutation succeeding. When the mutation did not resolve,
  nothing polled. **Never gate a poll on a mutation**; read endpoints are safe to call at any
  time.
- A closed tab cannot reliably withdraw itself, so queue presence is now proven by continued
  polling (`match_queue.last_seen_at`) rather than promised on exit.

---

## 5. The next step

**Start Phase 6 — Chat.** Branch `feature/chat`. Write the progress report to
`docs/progress/` first; that is the routine at every phase start.

This resolves the last transport conflict (`PROJECT-HANDBOOK.md` §6, conflict #3): doc 05
specifies REST `POST /room/{id}/message`, but the structure has always had a `websocket/`
directory. The resolution to propose: **WebSocket for delivery, the `messages` table for
persistence** — REST alone cannot push the other side's message without the polling that chat,
unlike a matchmaking queue, would feel.

Decide before writing code:

1. **How the socket authenticates.** A browser `WebSocket` cannot set an `Authorization`
   header. The usual options are a token in the query string (simple, but tokens end up in
   logs) or a first message that authenticates before anything else is accepted. Prefer the
   latter, and reuse `ClerkTokenVerifier` rather than inventing a second verification path.
2. **What happens on reconnect.** Fetch history over REST and stream new messages over the
   socket, or replay through the socket? Whichever, messages must not duplicate — the client
   should reconcile by message id, not by position.
3. **Whether matchmaking moves onto the same socket.** It can, once one exists. Not required;
   the 2s poll is adequate and now well understood. Do not bundle it into Phase 6.

Then: persist on receive, broadcast to both participants, guard the socket with the same
participant check as `GET /rooms/{id}`, and swap `ChatPanel`'s fixtures for the live
transport.

**The check that will prove it:** a message sent in one window appears in the other without a
refresh, and reloading either window still shows the full history. Fixtures would pass the
first half of that test and fail the second.

Before starting, read §7 of `docs/COMPLETE-PROGRESS-REPORT.md`. The Phase 4 lessons —
instrument before guessing, never gate a read on a mutation, presence must be proven rather
than promised — all apply directly to a socket, and one of them cost three rounds last time.
