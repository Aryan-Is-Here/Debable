# Debable — Handoff

**Written:** 2026-08-14 · **Updated:** 2026-08-17 · **Branch:** `main` · **Working tree:** clean

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

Ten phases, built strictly in order, one branch each. **Phases 0–6 are merged to `main`.**
Phase 7 (AI Fact Check) is next and has not been started.

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
| 6 Chat | ✅ merged — real-time text over a WebSocket, persisted |
| **7 AI Fact Check** | 🔵 **next, not started** |
| 8–10 | ⏳ not started |

**Works end to end today:** sign in with Clerk → browse and search real topics → create a
topic that survives a reload → queue for a topic → get paired with a second account → land in
a shared debate room → see and hear each other over real WebRTC → **type to each other, with
the transcript surviving a reload.**

**Verified by tests:** 136 backend tests pass (`cd backend && uv run pytest`). Frontend lint
and production build are clean.

⚠️ **99 of those 136 tests need Postgres and skip silently if Docker is not running.** A green
run with a high skip count proves almost nothing — always read the skip line. (An earlier
version of these docs claimed "63 of 109"; that figure was never measured and was wrong. 99 is
measured.)

**Still mock, by design:** the fact-check verdict is deterministic mock output generated in
the browser (Phase 7), the rating form does not persist (Phase 8), and Profile shows mock
stats.

The core loop is now real from sign-in through to a live debate with a working conversation.
What remains is the fact-check the whole product exists to test.

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

## 3. Where Phase 7 will land

Nothing is mid-edit — the tree is clean and Phase 6 is merged. These are the files Phase 7
(AI Fact Check) will touch, and the ones worth reading first:

| File | Why it matters to Phase 7 |
|---|---|
| `backend/app/ai/` | **Empty.** Scaffolded in Phase 0 for exactly this; the AI service client goes here |
| `backend/app/models/fact_check.py` | The table already exists — claim, verdict enum, explanation, JSONB sources |
| `backend/app/services/chat.py` | The shape to copy: participant guard via `to_room_read()`, reject ended rooms, persist, then broadcast |
| `backend/app/websocket/registry.py` | `chat_registry.broadcast()` is how a verdict reaches both windows |
| `backend/app/api/v1/chat.py` | Where `POST /rooms/{id}/fact-check` belongs, and the pattern for its refusals |
| `frontend/components/debate-room-view.tsx` | Holds `mockFactCheck` and the local fact-check array to replace |
| `frontend/components/fact-check-dialog.tsx` | Already collects the claim; only its submit handler changes |
| `docs/10-ai-fact-check-design.md` | The RAG design and the verdict vocabulary |

**One design question to settle first:** a fact-check is not a `messages` row —
`messages.sender_id` is `NOT NULL` and references `users`, so a "system" message has no author
to point at. See `docs/PROJECT-HANDBOOK.md` §7 for the two options and the recommendation.

## 4. What was tried and failed

### Phase 6 (chat) — two real bugs, both found by tests rather than guessed at

1. **Postgres `now()` is the transaction start time.** Three messages written inside one
   transaction shared a `created_at` down to the byte, so the ordered read fell through to its
   random-UUID tiebreak and returned them *shuffled*. Fixed by setting `created_at` to
   `clock_timestamp()` at insert. No migration was needed.
2. **`httpx-ws`'s transport holds an anyio cancel scope**, and pytest-asyncio finalises async
   fixtures in a *different task* than it sets them up in — so a fixture yielding an entered
   client blew up in teardown. Socket tests open their client inside the test body instead.

### Phase 4 (matchmaking) — three rounds of debugging after the feature "worked"

The failures are more instructive than the fixes, and two of them were wrong diagnoses.

**Fixes that were correct but were not the reported bug**

1. **`refetchIntervalInBackground`.** Diagnosed the stalled waiting room as TanStack Query
   skipping fetches while `document.visibilityState === "hidden"`. That behaviour is real, but
   it was **not** the cause. Kept because it is correct for genuinely hidden windows.
2. **The 60-second clock-skew allowance in Clerk verification.** Real and measured (this
   machine ran 13.3s behind Clerk, and Clerk stamps `nbf`). Worth keeping, but it explained
   scattered 401s, not the stall.

**The methodological failures worth remembering**

3. **Read the wrong log file.** Counted "zero `GET /match` requests" from a log belonging to a
   different backend process. A whole diagnosis was built on it. *(This bit again in Phase 6:
   port 8000 can be owned by someone else's server. Confirm the log you are reading is the one
   your traffic went to before drawing a conclusion from it.)*
4. **Four isolation harnesses that all failed to reproduce.** Every added difference was
   exonerated. Reverse-engineering the observer's internals was abandoned after three attempts.
5. **Guessing instead of instrumenting.** What finally resolved it was a development-only
   readout under the spinner. It showed `join=false` with `status=queued` — the query was
   disabled while stale cache kept the screen looking alive. That line should have been the
   *first* move, not the fourth. It is still in `waiting-room.tsx`, and `ChatPanel` now
   carries the same kind of readout for the socket.

**The actual root causes, once found**

- The withdraw-on-leave effect depended on Clerk's `getToken`, whose identity changes as the
  session settles — and React runs an effect's cleanup when dependencies change, not only on
  unmount. The page was withdrawing itself from the queue while the user watched. *(The chat
  hook mirrors `getToken` into a ref for exactly this reason.)*
- Rooms only end via the End debate button, so closing a tab left one open — and joining used
  to *return* an open room, trapping both participants with a partner who had left.
- The poll was gated on the join mutation succeeding. **Never gate a poll on a mutation.**
- A closed tab cannot reliably withdraw itself, so queue presence is proven by continued
  polling rather than promised on exit.

---

## 5. The next step

**Start Phase 7 — AI Fact Check.** Branch `feature/fact-check`. Write the progress report to
`docs/progress/` first; that is the routine at every phase start.

This is the feature the entire project exists to evaluate, and the first one that depends on a
third party with real latency and real cost. `docs/PROJECT-HANDBOOK.md` §7 has the step-by-step
plan. Decide before writing code:

1. **How the verdict reaches the chat** — its own frame type and endpoint, or a new kind of
   `messages` row (which needs a migration, because `sender_id` is `NOT NULL`). The handbook
   recommends the former, and notes the consequence: reloads then need a
   `GET /rooms/{id}/fact-checks`.
2. **What happens when the AI is slow or down.** It must not block the socket's receive loop,
   and a failure needs a visible outcome rather than silence.
3. **Rate limiting.** This is the endpoint that costs money.

**The check that will prove it:** a claim submitted in one window produces the same verdict
card in *both* windows, and it is still there after a reload.

Before starting, read §5.14–5.22 of `docs/PROJECT-HANDBOOK.md` and §7 of
`docs/COMPLETE-PROGRESS-REPORT.md`. Two apply immediately: the connection registry is
per-worker, so a broadcast verdict inherits chat's deployment constraint; and an AI call that
is merely slow looks exactly like one that is broken, so instrument it before guessing.

---

## 6. Outstanding manual check

Phase 6's automated coverage is good — 27 tests, including two sockets exchanging a message in
one room, and the refusal paths confirmed against a running server. **The two-window check by
hand has not been done yet.** Worth ten minutes before building Phase 7 on top:

1. Sign in as two different accounts in two windows, queue the same topic, land in one room.
2. Type in window A — it should appear in window B with no refresh. Type in B, appears in A.
3. **Reload either window — the full history should still be there.** This is the half that
   fixtures used to fail.
4. Stop the backend: both panels should show "Reconnecting to chat…" and disable the composer.
   Restart it: they reconnect and the conversation is **not** duplicated.
5. End the debate, then try to send: refused with a message, socket stays open.

The dev-only line under the composer (`dev · ws=… · msgs=… · you=… · last=…`) tells you which
state the socket is actually in — use it rather than inferring from a quiet panel.
