# Debable — Handoff

**Written:** 2026-08-14 · **Updated:** 2026-08-17 · **Branch:** `main` · **Working tree:** clean

Read this first if you are picking the project up mid-flight. For the full reference see
[`docs/PROJECT-HANDBOOK.md`](docs/PROJECT-HANDBOOK.md); for the narrative and every decision's
reasoning see [`docs/COMPLETE-PROGRESS-REPORT.md`](docs/COMPLETE-PROGRESS-REPORT.md).

---

## 0. Read this before you run anything

**Use `http://localhost:3000`. Nothing else works.** A LAN address or `127.0.0.1` breaks three
things at once: Clerk never loads (the dev instance is bound to specific origins), CORS blocks
the API, and the chat socket's `Origin` check refuses the handshake. This cost real debugging
time — it presented as an eternal spinner, a header with no sign-in button, and a matchmaking
poll that never ran. Three symptoms, one cause. The app now explains itself after ~8 seconds
(`frontend/hooks/use-auth-ready.ts`), but the address is still the fix.

To serve another device, `CORS_ORIGINS`, `NEXT_PUBLIC_API_BASE_URL` and Clerk's allowed
origins must be updated together.

---

## 1. The goal

**Debable** is a random video debate platform that matches strangers by *debate topic* rather
than by random interest. Its differentiator is an **on-demand AI fact-check**: mid-debate,
either participant submits one specific claim, the backend sends only that claim to an
isolated AI service, and the verdict is posted into the debate chat.

Ten phases, built strictly in order, one branch each. **Phases 0–7 are merged to `main`.**
Phase 8 (Ratings) is next and has not been started.

**On "the goal", precisely.** `docs/01-product-vision.md` states the MVP success metric as
*"two strangers can successfully debate and use AI fact-checking during the conversation"* — a
**capability** metric, and Phase 7 met it. The framing used elsewhere, *"can fact-checking
improve debates?"*, is an **outcome** question that nothing currently measures. The decision
taken is to ship the ten phases as specified. That does not foreclose the outcome question:
`ratings.room_id` and `fact_checks.room_id` join on the same room, so "debates with a
fact-check versus without" stays a query rather than a migration. Keep it that way.

---

## 2. Current state of the code

| Phase | State |
|---|---|
| 0 Planning | ✅ merged |
| 1 UI Prototype | ✅ merged |
| 2 Backend Foundation | ✅ merged |
| 3 Topics | ✅ merged |
| 4 Matchmaking | ✅ merged |
| 5 Video | ✅ merged |
| 6 Chat | ✅ merged |
| 7 AI Fact Check | ✅ merged |
| **8 Ratings** | 🔵 **next, not started** |
| 9–10 | ⏳ not started |

**Works end to end today:** sign in → browse or create a topic → queue → get paired → land in
a shared room → see and hear each other over WebRTC → hold a text conversation that survives a
reload → **fact-check a claim and have the verdict appear in both windows with citations that
resolve.**

**Verified by tests:** 216 backend tests. Frontend lint and production build clean.

⚠️ **Most of those tests need Postgres and skip silently without it.** A green run with a high
skip count proves almost nothing — always read the skip line. This has now bitten three times.

**Still mock, by design:** the rating form does not persist, the results page renders the demo
room for any roomId, Profile shows mock stats, and Settings reads a mock user. All Phase 8.

### The fact-check has three configurations

Each degrades to something needing no credentials, so a fresh clone runs the whole flow:

| `backend/.env` | Judgment | Evidence |
|---|---|---|
| no keys | Stub — deterministic fake verdicts | none |
| `GEMINI_API_KEY` | Gemini 3.6 Flash | Wikipedia (no account needed) |
| `+ TAVILY_API_KEY` | Gemini 3.6 Flash | Full trusted-source allowlist, enforced at retrieval |

Currently running: **Gemini + Wikipedia.** Tavily is written and dormant — free at
[app.tavily.com](https://app.tavily.com), 1,000 searches/month, no card. Add the key and
restart; nothing else changes.

### Running it

```bash
docker compose -f docker/docker-compose.yml up -d db
cd backend && uv run alembic upgrade head && uv run python -m app
cd frontend && npm run dev
```

Use `python -m app`, never bare `uvicorn`: on Windows psycopg's async driver cannot run on the
default `ProactorEventLoop`.

Secrets live in `backend/.env` and `frontend/.env.local`, both gitignored. Required:
`DATABASE_URL`, `CLERK_ISSUER`, `LIVEKIT_*`; frontend needs `NEXT_PUBLIC_API_BASE_URL`,
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`. Optional: `GEMINI_API_KEY`,
`TAVILY_API_KEY`.

---

## 3. Where Phase 8 will land

| File | Why it matters |
|---|---|
| `backend/app/models/rating.py` | **The schema already does the work** — a `UniqueConstraint` on `(room_id, reviewer_id)`, a 1–5 `CheckConstraint`, and one forbidding self-review |
| `backend/app/services/chat.py` | The shape to copy: participant guard via `to_room_read()`, reject ended rooms, persist |
| `frontend/app/debate/[roomId]/results/page.tsx` | Uses `mockDebateRoom` for **any** roomId — rating currently "works" while rating nothing |
| `frontend/components/debate-room-loader.tsx` | The pattern for loading a real room client-side with a Clerk token |
| `frontend/app/profile/page.tsx`, `frontend/components/settings-view.tsx` | The last two mock call-sites |

Because the constraints exist, the service translates an `IntegrityError` into a clean 409
rather than re-checking — the same shape `match.join` already uses.

---

## 4. What was tried and failed

### Phase 7 — the documentation was wrong twice, and only a real call showed it

The phase chose Anthropic, then Gemini-with-grounding, and shipped **neither**. The provider
changed twice before a line of the service layer existed.

- `gemini-2.5-flash`, the only model with a free grounding quota on the pricing page, returns
  **404: "no longer available to new users"**.
- `gemini-3.6-flash` with the search tool returns **429 on the first call** — a zero quota,
  not a spent one.
- Plain generation works fine. Only retrieval was closed.

**The lesson (handbook §5.25): verify a third party's free tier with a real call before
designing around it.** One throwaway script cost one request and saved a rewrite. This is the
Phase 5 lesson — validate LiveKit credentials before building on them — generalised, and it
had to be learned twice.

**The forced change improved the design.** Doing retrieval ourselves made the allowlist a
constraint on *what is fetched* rather than a filter on *what is cited*, and removed the tool
from the request, which is what allows structured JSON output.

Two more bugs found by running it: Wikimedia enforces its User-Agent policy (a generic agent
gets a 403), and Wikipedia was missing from the trusted-source allowlist — a test actively
asserted it was untrusted — so every Wikipedia-backed verdict was silently downgraded to
`unverified`.

### Phase 6 — two Phase 5 bugs, both the same mistake

Presence was inferred from whether a camera track existed, and the opponent's mute state from
nothing at all. **Both inferred a fact from a proxy that merely correlates with it**, and both
survived a Phase 5 manual check *that passed*, because that check ran with both cameras on.
Hence handbook §5.24: when verifying by hand, toggle the optional things.

### Phase 4 — three rounds of debugging after the feature "worked"

- Effect cleanups run on **dependency change**, not only unmount. Clerk's `getToken` identity
  changes as the session settles; the page withdrew itself from the queue mid-session.
- **Never gate a poll on a mutation.** Read endpoints are safe to call at any time.
- **Presence is proven by polling, never promised on exit.**
- **Instrument before guessing.** A spinner looks identical whether the client is polling,
  failing silently, or not polling at all. The dev readout that ended it is still in
  `waiting-room.tsx`, and `ChatPanel` carries the equivalent for the socket.

---

## 5. The next step

**Start Phase 8 — Ratings.** Branch `feature/ratings`. Write the progress report to
`docs/progress/` first; that is the routine at every phase start.
`docs/PROJECT-HANDBOOK.md` §7 has the step-by-step.

**The check that will prove it:** a rating submitted after a debate persists, appears on the
rated user's profile, and a second attempt from the same reviewer is refused.

### Then, briefly

- **Phase 9 — Polish & Deploy.** Resolves conflict #1: the Reports feature has no table, so
  `reports` is the **only migration left in the project**. Deployment must be researched at
  the time, not planned now — free tiers moved twice during Phase 7. **Hard constraint:** the
  chat connection registry is per-process, so the API must be pinned to one worker or given a
  broker, or two debaters on different workers see none of each other's messages.
- **Phase 10 — UI/UX redesign.** Deliberately last, so it is done once against a finished
  product. Everything on screen is still Phase 1 prototype styling.
