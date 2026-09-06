# Debable — Progress Report

**Report date:** 2026-08-17 · **Milestone:** Start of Phase 7 (AI Fact Check)
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
| Phase 5 — Video | ✅ Complete |
| **Phase 6 — Chat** | ✅ **Complete** (merged to `main`) |
| **Phase 7 — AI Fact Check** | ✅ **Complete** |
| Phase 8 — Ratings | ⏳ Pending |
| Phase 9 — Polish & Deploy | ⏳ Pending |
| Phase 10 — Professional UI/UX Redesign | ⏳ Pending |

**Six of ten phases merged.** The core loop is real end to end: sign in, browse or create a
topic, queue, get paired, land in a shared room, see and hear each other over WebRTC, and
hold a text conversation that survives a reload.

**This is the phase the project exists for.** Every prior phase built the room; this one puts
the thing being tested inside it.

---

## Phases 0–5 in brief

**Phase 0** scaffolded the repository and locked the early decisions: Clerk for auth with no
login endpoint of our own, the AI fact-check as an isolated on-demand service, strictly
sequential phases with one branch each.

**Phase 1** built all eight screens against typed mock data. Writing `lib/types.ts` as the
contract first paid off repeatedly — when the real API arrived, screens changed data source
rather than being rewritten.

**Phase 2** brought up FastAPI, Postgres, Alembic and Clerk JWT verification, with every
model carrying `created_at`/`updated_at` and a health endpoint that fails honestly.

**Phase 3** made topics real and settled the category conflict: an indexed `varchar` plus one
shared allowlist constant validated on both sides, rather than a Postgres enum.

**Phase 4** built matchmaking on a `match_queue` table paired with `FOR UPDATE SKIP LOCKED`.
It cost three rounds of debugging after it "worked", and produced the lessons the project
still runs on: instrument before guessing, never gate a poll on a mutation, and presence must
be proven rather than promised.

**Phase 5** added real LiveKit video with a deliberately minimal token grant, tested by
decoding what was signed rather than trusting the SDK. Two bugs in it survived until Phase 6
— see below.

---

## Phase 6 — Chat ✅

Resolved **conflict #3**, the last open transport question, by using both transports for the
halves each is good at: **history is REST, delivery is a WebSocket.** A REST-only chat cannot
push the other side's message without polling, and two seconds of latency that is invisible in
a matchmaking queue makes a conversation feel broken. Doc 05's `POST /room/{id}/message` was
dropped outright — a send that succeeds while the socket is dead leaves the sender staring at
nothing.

Decisions worth carrying forward:

- **Authenticate-first frame, not a query-string token.** A browser `WebSocket` cannot set an
  `Authorization` header, and a token in the URL would land in access logs, proxy logs and
  browser history. `ClerkTokenVerifier` and the provisioning logic are reused — the shared
  half of `get_current_user` became `resolve_user` — so HTTP and socket paths cannot disagree
  about who a caller is.
- **The handshake checks `Origin` itself,** because CORS does not apply to WebSockets.
- **The wire carries `senderId`,** not the frontend's viewer-relative `author`. One broadcast
  frame reaches both debaters, and "you" would mean the opposite thing on each side.
- **Refusals before `ready` close the socket; refusals after it do not.** A mistyped empty
  message should not cost someone their connection.

**Verified by hand:** messages cross both ways without a refresh, and the full history
survives a reload of either window. 136 backend tests pass, 0 skipped.

### Two bugs found in Phase 5, during Phase 6's manual check

Both in the video tile, and they are the same mistake twice: **a fact inferred from a proxy
that merely correlates with it.**

1. Participant *presence* was read off whether a camera track existed. Turning a camera off
   unpublishes the track, so "camera off" and "never joined" were indistinguishable — one side
   showed "Waiting for them to join…" over someone who had been there the whole time. Only the
   person with their camera off saw the room correctly, which is why it read as one window
   working and one broken rather than as a rendering bug.
2. The opponent's *mute state* was read off nothing at all — the tile never passed the prop,
   so an opponent always rendered as unmuted. The handbook's claim that Phase 5 was "verified
   live: mute crosses between windows" was true of video only, and has been corrected in
   place.

**How they were missed matters more than what they were.** Both survived a Phase 5 manual
check *that passed*, because that check ran with both cameras on. They surfaced in Phase 6
only because someone happened to have a camera off. New convention (handbook §5.24): when
verifying by hand, toggle the optional things — camera, mic, one tab closed — not just the
happy path.

A second correction: both documents had been repeating "63 of 109 tests need Postgres". That
figure was never measured and was wrong. Measured by running with the database unreachable,
the real split is **99 of 136**.

---

## Phase 7 — AI Fact Check (starting now)

The differentiator, and the question the MVP exists to answer: **can AI-assisted fact-checking
improve online debates?**

### The blueprint is thinnest exactly here

Worth stating plainly, because it is the opposite of every prior phase.
`docs/10-ai-fact-check-design.md` is **22 lines** — a seven-box flow ending in "AI is NOT
always listening in the MVP". `docs/03-system-architecture.md` contributes one ASCII box
labelled `AI Service`. The PRD contributes one bullet.

"RAG retrieves trusted sources" is a phrase, not a specification. Every other phase had a
document telling it what to build; this one has to decide first.

### Decisions taken before code

| Question | Decision |
|---|---|
| Retrieval | **Claude with server-side web search, restricted by a domain allowlist.** The allowlist *is* the trust boundary — a citation can only come from a source on it. Retrieval is real and the URLs load, but there is no corpus to ingest, embed or maintain |
| Model | `claude-opus-5` |
| Service boundary | **`app/ai/` is a client, not a second deployable.** Doc 03 draws the AI as its own box; the property that box exists to guarantee is that the AI never listens continuously and only the submitted claim crosses the boundary. An API call satisfies that. A separate service would add operational work without adding isolation |
| Credentials | `ANTHROPIC_API_KEY` in `backend/.env`, gitignored, as with the LiveKit signing secret. Aryan adds it; the code is written and tested against a stubbed client |

**Why not a vector store.** It is the literal reading of "RAG", and it is weeks of ingestion
pipeline and embedding infrastructure before anything is testable — during which the corpus
choice quietly becomes the product. The allowlist gets the same property (a citation cannot
come from an untrusted source) for a fraction of the work, and can be replaced later without
touching the endpoint, the persistence or the UI.

**Why not model knowledge alone.** It is by far the cheapest option and it is disqualified:
citations would be generated rather than retrieved, and a plausible URL that 404s is precisely
the failure that would invalidate the experiment.

### Things the current API makes true, that intuition gets wrong

- **Server-tool failures return HTTP 200.** A failed search arrives as a result block
  containing an error object, not as a raised exception. The "AI is unavailable" path must
  inspect content, not catch.
- **`allowed_domains` is enforced server-side by the search tool**, which is what makes the
  allowlist a real boundary rather than a prompt instruction the model may ignore.
- Web search runs code internally; `code_execution` must not be declared alongside it.

### Open question for this phase

A fact-check is **not** a `messages` row. `messages.sender_id` is `NOT NULL` and references
`users`, so a system-authored message has no author to point at. Two options:

1. Broadcast fact-checks as their own frame type, with a `GET /rooms/{id}/fact-checks` for
   reloads. No migration; keeps two genuinely different things apart.
2. Add a nullable `sender_id` and a kind discriminator to `messages`. One list, one read, but
   a migration and a nullable foreign key on a table that currently has neither.

**Recommendation: option 1.** Recorded here rather than settled silently.

### Risks specific to this phase

- **Latency.** The user is mid-conversation. A fact-check must not block the socket's receive
  loop, and "slow" must be visibly distinct from "broken" — the same ambiguity that cost three
  rounds in Phase 4.
- **Cost.** This is the first endpoint that spends money per call. It needs a rate limit before
  it is exposed, not after.
- **Hallucinated citations.** The allowlist constrains the domain; it does not guarantee the
  page says what the model claims. Worth checking by hand that cited URLs load and support the
  verdict.

### The check that will prove it

A claim submitted in one window produces the same verdict card in **both** windows, with
citations that resolve, and it is still there after a reload.

---

## Phase 7 outcome — what the plan above got wrong

The plan opened by saying this phase had the thinnest blueprint in the project. That turned
out to matter less than something it did not anticipate: **the documentation for the paid
services was wrong twice, and only a real API call revealed it.**

### Google Search grounding is unobtainable on a free account

The plan chose Gemini specifically because its pricing page lists free Google Search
grounding. Both halves of that turned out to be closed:

- `gemini-2.5-flash` — the only model with a free grounding quota — returns
  **404: "no longer available to new users"**.
- `gemini-3.6-flash` with the `google_search` tool returns **429 RESOURCE_EXHAUSTED on the
  first call**, before any successful generation. A zero quota, not a spent one, matching the
  "Grounding: Not available" on every 3.x Free Tier row.
- Plain generation on those models works fine. The key was healthy; only retrieval was shut.

Before that, the phase had already moved off Anthropic for cost. So the provider changed
twice before a line of the service layer existed — which is the strongest possible argument
for the `FactCheckProvider` protocol the plan happened to specify first. The service layer,
the guards, the rate limits and the persistence never changed at all.

### Being forced to retrieve separately made the design better

Doing the search ourselves beat both grounding designs on the axes that matter:

| | Grounding (planned) | Shipped |
|---|---|---|
| Allowlist | Post-filter — the model could *read* untrusted pages, we only dropped citations | **Enforced at retrieval** — untrusted pages are never fetched |
| Output | Text parsing, since schemas and grounding conflict on Gemini 2.5 | **Structured JSON** — no tool in the request, no conflict |
| Citations | Opaque `vertexaisearch` redirect URLs | Real publisher URLs from the search we ran |

Citations also became impossible to invent rather than merely unlikely: the model selects
from numbered sources by index, and an index outside the supplied range is discarded.

### Three bugs found by running it, not reading about it

1. **Wikimedia enforces its User-Agent policy.** A generic agent gets a `403` linking to the
   policy. The agent now names the application and a contact.
2. **Wikipedia was missing from the trusted-source allowlist** — a test actively asserted it
   was untrusted. Since it is the retrieval backend when no Tavily key is set, *every*
   Wikipedia-backed verdict had its citations stripped and was silently downgraded to
   `unverified`. The original exclusion applied the wrong test: what matters is whether a
   debater can check a citation in one click.
3. **Clerk never loads on a non-`localhost` origin**, which produced an eternal spinner, a
   header with no sign-in button, and a matchmaking poll that never ran — three symptoms, one
   cause, nothing on screen connecting them. Fixed by `useAuthReady`.

### What shipped

Three configurations, each degrading to something needing no credentials:

| `.env` | Judgment | Evidence |
|---|---|---|
| no keys | Stub | none — fake verdicts, whole flow works |
| `GEMINI_API_KEY` | Gemini 3.6 Flash | Wikipedia |
| `+ TAVILY_API_KEY` | Gemini 3.6 Flash | Full trusted-source allowlist, enforced at retrieval |

**Verified live:** *"The Great Depression began with a stock market crash in 1929"* returns
`true`, citing the Wall Street crash of 1929 and Great Depression articles. Confirmed by hand
in two windows: the card appears in both without a refresh and survives a reload.

216 backend tests pass, 0 skipped. **None of them touch a network** — that is load-bearing
rather than tidy: a suite spending one Tavily credit per run would exhaust a 1,000-a-month
allowance in a fortnight of ordinary development.

The rule the phase was built around held: `UNVERIFIED` is a verdict, `FactCheckUnavailable`
is an error, and the two never collapse. A failed check persists nothing.

---

## Verification status

| Area | Evidence |
|---|---|
| Backend suite | 136 tests pass, 0 skipped (99 require Postgres and skip without it) |
| Lint/format | `ruff check`, `ruff format --check`, `eslint` all clean |
| Build | `npm run build` compiles all 9 routes, no type errors |
| Migrations | `alembic check` reports no drift |
| Topics | Confirmed by hand: a created topic survives a reload |
| Matchmaking | Confirmed by hand: two accounts, two windows, both flip to matched |
| Video | Confirmed by hand: audio, video, camera-off and mute all cross correctly |
| Chat | Confirmed by hand: messages cross without a refresh and survive a reload |
| Fact-check | 216 tests, none touching a network. **Confirmed by hand:** a verdict card appears in both windows without a refresh, with citations that resolve, and survives a reload |

---

## Git history (main)

| Commit | Description |
|---|---|
| `47fdec5` | **Merge feature/chat — Phase 6 complete** |
| `9310ef3` | Correct two false claims about Phase 5 video |
| `85f1dd0` | Fix a camera-off debater looking like they never joined |
| `4c328c4` | **Merge feature/video — Phase 5 complete** |
| `8448a47` | **Merge feature/matchmaking — Phase 4 complete** |
| `fe27248` | **Merge feature/topics — Phase 3 complete** |
| `e690651` | **Merge chore/rename-to-debable** |
| `5b67600` | **Merge feature/backend-foundation — Phase 2 complete** |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `1e24aaf` | Initial scaffold + blueprint docs |
