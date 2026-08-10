# Debable — How to Inspect the Project

A companion to `PROJECT-HANDBOOK.md`, written for the person checking the work rather than
writing it. It answers two questions: **how do I run what exists right now**, and **at the end
of each phase, what should I actually look at to know it works?**

Rule of thumb: after every phase you get something you can see or hit yourself. If a phase ends
and there is nothing here for you to check, the phase is not finished.

---

## Running it

Two processes. The frontend can run alone; the backend needs Docker for Postgres.

```bash
# 1. Database — leave this running
docker compose -f docker/docker-compose.yml up -d db

# 2. Backend — http://localhost:8000
cd backend
uv run alembic upgrade head        # only after a schema change
uv run python -m app

# 3. Frontend — http://localhost:3000
cd frontend
npm run dev
```

Stop everything with `Ctrl+C` in each terminal, plus:

```bash
docker compose -f docker/docker-compose.yml down
```

**Windows:** start the backend with `python -m app`, not `uvicorn` — see handbook §5.11.

### Two views that are always worth a look

- **`http://localhost:8000/docs`** — auto-generated, interactive API documentation. Every
  endpoint the backend exposes is listed with its request and response shape, and there is a
  "Try it out" button that issues the real call. This is the fastest way to see what a phase
  actually added, and it cannot drift from the code because it is generated from it.
- **`http://localhost:8000/api/v1/health`** — one line telling you the service is up and can
  reach the database.

---

## What to check, phase by phase

### Phase 1 — UI Prototype ✅ *(done)*

Everything is mock data; nothing persists. You are judging look, flow and responsiveness.

Walk the loop: **Home → Browse → "Debate" on a card → Waiting Room (~4s) → Enter debate → send
a chat message → Fact-check a claim → End debate → rate → Home.**

- Browse: type in the search box, click category chips, and clear them to an empty result.
- Debate room: the video tiles are placeholders with a "mock" badge — that is expected until
  Phase 5. Mute and camera buttons should toggle visibly.
- Fact-check: submit a claim, wait ~1.2s, confirm a verdict card appears **inside the chat**
  with an explanation and sources.
- Toggle light/dark in the header, and narrow the window to phone width on each screen.

**Expected to be broken:** "Sign in" is disabled, refreshing loses everything, and two browser
windows do not see each other. None of that is a bug yet.

### Phase 2 — Backend Foundation ✅ *(done)*

Nothing visible changed in the UI — this phase built the engine, not the bodywork. Check it
directly:

1. Open `http://localhost:8000/docs`. You should see one endpoint, `GET /api/v1/health`.
2. Hit `http://localhost:8000/api/v1/health` → `{"status":"ok","database":"ok",...}`.
3. Now prove the database check is real, not hardcoded:
   ```bash
   docker compose -f docker/docker-compose.yml stop db
   curl -i http://localhost:8000/api/v1/health     # 503, "database":"error"
   docker compose -f docker/docker-compose.yml start db
   curl -i http://localhost:8000/api/v1/health     # 200 again
   ```
4. Look at the tables that were created:
   ```bash
   docker exec -it debable-db psql -U debable -d debable -c "\dt"
   ```
   Six tables plus `alembic_version`. They are all empty — nothing writes to them until Phase 3.
5. Run the test suite: `cd backend && uv run pytest` → 31 passing.

### Phase 3 — Topics *(next)*

The first phase where the frontend and backend actually talk. **The thing to verify is
persistence.**

- Create a topic in the UI, then **refresh the page** — it must still be there. Phase 1 topics
  vanished on refresh; these must not.
- Stop and restart the backend, reload Browse — still there.
- Confirm it reached the database, not just memory:
  ```bash
  docker exec -it debable-db psql -U debable -d debable -c "select title, status, created_at from topics;"
  ```
- In `/docs`, try `GET /api/v1/topics` directly and check the JSON matches what Browse renders.
- Try `POST /api/v1/topics` from `/docs` **without signing in** — it must be rejected with 401,
  not accepted.
- Submit the Create form with a 3-character title: the frontend should block it, and the API
  should also reject it if called directly. Validation on only one side is a bug.

### Phase 4 — Matchmaking

- Open two browser windows, one normal and one private/incognito, signed in as different users.
- Both pick the same topic and hit Debate. They should be matched **to each other**, and both
  should land in a room with the same room ID in the URL.
- One user alone should keep waiting rather than being matched with a phantom.
- Cancel from the waiting room and confirm the user leaves the queue (the other window should
  not then match with them).

### Phase 5 — Video

- The two windows should show **real webcam video** of each other; the "mock" badge is gone.
- Mute yourself and confirm the other window shows you muted. Same for camera off.
- Check that permission prompts appear the first time, and that denying them fails gracefully
  instead of showing a blank screen.

### Phase 6 — Chat

- Send a message in one window; it appears in the other **without a refresh**.
- Refresh one window: the conversation history is still there (it is coming from the database
  now, not memory).
- Close and reopen a window mid-debate and confirm it reconnects.

### Phase 7 — AI Fact Check

The core hypothesis of the product. Judge quality, not just plumbing.

- Submit a claim that is clearly true, one clearly false, and one genuinely ambiguous. The
  verdicts should differ sensibly and the ambiguous one should come back *misleading* or
  *unverified* rather than a confident wrong answer.
- Click the cited sources — they must be real, working links that actually support the verdict.
- The verdict must appear in **both** participants' chats, not just the requester's.
- Try a nonsense or empty claim and confirm it is rejected cleanly.

### Phase 8 — Ratings

- End a debate, rate the opponent, then check the rating shows on their profile.
- Try to rate the same debate twice — the second attempt must be refused.
- Confirm the average rating on the profile updates correctly.

### Phase 9 — Polish & Deploy

- Report a user and confirm the report is stored.
- Full pass on a real phone, in both light and dark mode.
- Tab through every screen using only the keyboard; nothing should be unreachable.
- Then the same walkthrough against the deployed URLs rather than localhost.

---

## When something looks wrong

Useful things to capture before reporting it — they usually identify the cause immediately:

- What you clicked, and what you expected instead.
- The browser console (F12 → Console) and the Network tab entry for the failing request.
- The backend terminal output at the moment it happened.
- Whether `http://localhost:8000/api/v1/health` was healthy at the time.
