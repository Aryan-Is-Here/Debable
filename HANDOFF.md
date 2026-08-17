# Debable — Handoff

**Written:** 2026-08-14 · **Branch:** `feature/video` (commit `eebdfc4`) · **Working tree:** clean

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

Ten phases, built strictly in order, one branch each. Phases 0–4 are merged to `main`.
Phase 5 is built and awaiting a live check.

---

## 2. Current state of the code

| Phase | State |
|---|---|
| 0 Planning | ✅ merged |
| 1 UI Prototype | ✅ merged — 8 screens, then mock data |
| 2 Backend Foundation | ✅ merged — FastAPI, Postgres, Alembic, Clerk verification, health |
| 3 Topics | ✅ merged — real topic CRUD, frontend on live data |
| 4 Matchmaking | ✅ merged — queue, pairing, debate rooms |
| **5 Video** | 🟡 **built, committed, not yet verified live** |
| 6–10 | ⏳ not started |

**Works end to end today:** sign in with Clerk → browse and search real topics → create a
topic that survives a reload → queue for a topic → get paired with a second account → land in
a shared debate room. Aryan has confirmed all of that by hand.

**Verified by tests:** 109 backend tests pass (`cd backend && uv run pytest`). Frontend lint
and production build are clean. 63 of those tests need Postgres and *skip silently* if Docker
is not running — check the skip count before trusting a green run.

**Still mock, by design:** chat messages are fixtures and do not cross between windows
(Phase 6), the fact-check verdict is deterministic mock output (Phase 7), the rating form does
not persist (Phase 8), and Profile shows mock stats.

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

## 3. Files most recently touched

Nothing is mid-edit — the tree is clean and Phase 5 is committed. These are the files that
Phase 5 changed, i.e. where attention should go if the live check fails:

| File | Role |
|---|---|
| `backend/app/services/video.py` | Mints the LiveKit token; owns the grant, which is the security boundary |
| `backend/app/schemas/video.py` | `RoomToken` response shape |
| `backend/app/api/v1/match.py` | Added `POST /rooms/{id}/token` |
| `backend/app/core/config.py` | `LIVEKIT_*` settings and `livekit_configured` |
| `backend/tests/test_video.py` | 9 tests that decode the signed token rather than trust the SDK |
| `frontend/components/debate-video.tsx` | **New.** Connects to LiveKit, renders both tiles, owns every media failure state |
| `frontend/services/video.ts` | Token client |
| `frontend/components/debate-room-view.tsx` | Mock tiles swapped for `DebateVideo`; local mute/camera state deleted |
| `frontend/components/video-tile.tsx` | **Deleted** — the Phase 1 mock, now unused |

---

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

**Live-verify Phase 5, then merge.** Nothing else should start first.

Two browser windows, two different Clerk accounts, same topic → match → Enter debate:

1. Both tiles show live video, correctly labelled, with "(you)" on the local one.
2. **Mute in one window shows as muted in the other.** This is the real check — a local-only
   toggle looked identical before this phase.
3. Camera off falls back to the avatar, not a black rectangle.
4. Deny permission deliberately once: it must produce the explanatory message.

Two testing artefacts that will otherwise look like bugs: use **headphones** (two windows on
one machine feed back within seconds), and Chrome may refuse to hand the **same webcam** to
two tabs — if the second tile stays on its avatar, turn one camera off and confirm the other
side renders the "camera off" state instead.

If it passes: merge `feature/video` into `main`, push, then start Phase 6 (Chat) — which
resolves the last transport conflict (`docs/PROJECT-HANDBOOK.md` §6, conflict #3) by putting a
WebSocket in `app/websocket/` and persisting to the existing `messages` table.

If it fails: the browser console plus *whether the opposite window sees your track* isolates
which side broke. Do not guess — instrument first. That lesson cost three rounds.
