# Debable — Progress Report

**Report date:** 2026-09-06 · **Milestone:** Start of Phase 8 (Ratings)
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
| Phase 6 — Chat | ✅ Complete |
| **Phase 7 — AI Fact Check** | ✅ **Complete** (merged to `main`) |
| **Phase 8 — Ratings** | ✅ **Complete** |
| Phase 9 — Polish & Deploy | ⏳ Pending |
| Phase 10 — Professional UI/UX Redesign | ⏳ Pending |

**Seven of ten phases merged.** The differentiator works: two strangers can be matched by
topic, see and hear each other, hold a conversation that survives a reload, and fact-check a
claim mid-debate with the verdict appearing in both windows.

**The MVP success metric in `docs/01-product-vision.md` — "two strangers can successfully
debate and use AI fact-checking during the conversation" — has been met.** What remains is
finishing the product around it.

---

## Phases 0–6 in brief

**Phase 0** scaffolded the repository and locked the early decisions: Clerk for auth with no
login endpoint of our own, the fact-check as an isolated on-demand service, strictly
sequential phases.

**Phase 1** built all eight screens against typed mock data. Writing `lib/types.ts` as the
contract first paid off in every later phase — screens changed data source rather than being
rewritten, and it is still true: `FactCheckCard` renders Phase 7's real verdicts through the
same type it was given in Phase 1.

**Phase 2** brought up FastAPI, async SQLAlchemy over psycopg 3, Alembic, Clerk JWT
verification, and a health endpoint that fails honestly.

**Phase 3** made topics real and settled the category conflict with an indexed `varchar` and
one shared allowlist rather than a Postgres enum.

**Phase 4** built matchmaking on `SELECT … FOR UPDATE SKIP LOCKED`. Three rounds of debugging
after it "worked" produced the lessons the project still runs on.

**Phase 5** added LiveKit video with a deliberately minimal token grant, tested by decoding
what was signed rather than trusting the SDK.

**Phase 6** resolved the last transport conflict: history over REST, delivery over a
WebSocket, authenticated by a first frame rather than a query-string token.

---

## Phase 7 — AI Fact Check ✅

The phase where **the published documentation was wrong twice**, and only a real API call
showed it. That is the most transferable thing it produced.

The plan chose Anthropic for server-side web search, then Gemini for free Google Search
grounding. Neither shipped. `gemini-2.5-flash`, the only model the pricing page grants a free
grounding quota, returns *404: no longer available to new users*. Every 3.x model returns
*429 RESOURCE_EXHAUSTED on the first call* — a zero quota, not a spent one. Plain generation
works fine, so the key was healthy and only retrieval was closed.

The provider therefore changed twice before a line of the service layer existed. The
`FactCheckProvider` protocol written first is why that cost nothing: the guards, the rate
limits and the persistence never changed at all.

**Being forced to retrieve evidence ourselves improved the design.** The allowlist became a
constraint on what is *fetched* rather than a filter on what is *cited*, so an untrusted page
is never read. And with no tool in the request, structured JSON output works, so the verdict
is parsed rather than scraped out of prose. Citations became impossible to invent: the model
selects from numbered sources by index, and out-of-range indices are discarded.

Two more bugs found by running it rather than reading about it: Wikimedia enforces its
User-Agent policy, and Wikipedia was missing from the trusted-source allowlist — a test
actively asserted it was untrusted — so every Wikipedia-backed verdict was silently
downgraded to `unverified`.

A third, in the frontend: **Clerk never loads on a non-`localhost` origin**, and `useAuth`
has no way to report that, so the app spun forever with no sign-in button and a matchmaking
poll that never ran. Three symptoms, one cause, nothing on screen connecting them.
`useAuthReady` now explains it after eight seconds.

**216 backend tests pass, 0 skipped, and none of them touch a network.**

---

## Phase 8 — Ratings (starting now)

The last mock data in the product, and the record of whether a debate went well.

### The schema already does most of the work

`app/models/rating.py` carries a `UniqueConstraint` on `(room_id, reviewer_id)`, a
`CheckConstraint` for the 1–5 range, and another forbidding self-review. So the service
translates an `IntegrityError` into a clean 409 rather than re-checking — the same shape
`match.join` already uses, and one fewer race to reason about.

`RatingForm` has existed since Phase 1 and needs no redesign, only a real submit.

### The three remaining mock call-sites

- `app/debate/[roomId]/results/page.tsx` uses `mockDebateRoom` for **any** roomId. Rating
  currently "works" while rating nobody — the most misleading remaining mock, because it
  looks correct.
- `app/profile/page.tsx` uses `mockProfile`: debates count, average rating and history.
- `components/settings-view.tsx` uses `currentUser`.

### Decisions to make

1. **Whether a rating is required.** The results screen has a Skip button. Keep it — a forced
   rating produces compliance, not signal.
2. **What the profile shows before anyone has rated you.** `averageRating` is nullable in the
   type for exactly this. An empty state is honest; a default of 5 is a lie and a 0 is worse.
3. **Whether ratings are visible to the person rated.** The schema stores a comment. Showing
   it attributed changes what people write. The MVP has no moderation, so aggregate-only is
   the safer default.

### Risks

- **The results page is reachable after any debate**, including one the caller was not in.
  It needs the same `to_room_read()` participant guard as chat and fact-check.
- **Rating an unfinished debate** should be refused — the room must have `ended_at` set.
- Profile history joins rooms, topics and ratings. Worth watching the query count; the
  existing `selectinload` pattern in `app/repositories/match.py` is the one to copy.

### The check that will prove it

A rating submitted after a debate persists, appears on the rated user's profile, and a second
attempt from the same reviewer is refused rather than silently overwriting the first.

---

## Phase 8 outcome

All three decisions were taken as proposed: rating stays skippable, `averageRating` is null
rather than a number before anyone has rated you, and comments are stored but not shown
attributed.

### The results page was rating nobody

The plan called this "the most misleading remaining mock, because it looks correct" and that
was accurate. `app/debate/[roomId]/results/page.tsx` rendered `mockDebateRoom` for **any**
roomId: the form submitted, a toast appeared, and nothing was written. It survived seven
phases precisely because it never looked broken.

Loading the real room also brought the participant guard with it — a debate you were not in
is now a 403 rather than a form you can fill in.

### The schema did the work, and that shaped the service

`ratings` already carried a `UniqueConstraint` on `(room_id, reviewer_id)`, a 1–5
`CheckConstraint` and a no-self-review check. So uniqueness is enforced by letting the insert
fail and translating `IntegrityError` into a 409, rather than querying first. That is not
laziness: a "have they rated?" read followed by an insert is a *longer* race than the insert
alone — two submissions milliseconds apart would both read "no" and both proceed.

A second attempt is refused rather than allowed to overwrite. An overwrite would let someone
revise a score after seeing the reply, and would destroy the original silently.

### A gap found in use, not in tests

The results page was reachable only by the one-time redirect after ending a debate. Every test
passed, because tests address the URL directly. But through the UI, a rating you had given —
and, worse, a finished debate you had *not yet* rated — could afterwards be found only by
assembling the URL by hand. Hitting Skip, or closing the tab, stranded that debate
permanently.

Profile history rows are now links to their results page. **This is the second time this
project has shipped something that worked and could not be reached** — the first was Phase 5's
mute indicator, which was rendered but never wired. Both were invisible to tests for the same
reason: a test that calls the thing directly cannot tell you whether anything calls it.

### Every mock is gone

`frontend/lib/mock/` has no remaining references and was deleted. Every screen in the product
now renders server data.

`lib/types.ts`, written in Phase 1 as the contract before any backend existed, **never
changed**. The screens changed data source. That was the bet made in Phase 1, and it paid off
in every phase since.

**242 backend tests pass, 0 skipped.** No migration: the `ratings` table has existed since the
initial schema. Confirmed by hand: rate a real opponent, see it on the profile, revisit and
get the already-rated screen, and reach it from profile history.

---

## Verification status

| Area | Evidence |
|---|---|
| Backend suite | 216 tests pass, 0 skipped. None touch a network |
| Lint/format | `ruff check`, `ruff format --check`, `eslint` all clean |
| Build | `npm run build` compiles all 9 routes, no type errors |
| Migrations | `alembic check` reports no drift |
| Topics | Confirmed by hand: a created topic survives a reload |
| Matchmaking | Confirmed by hand: two accounts, two windows, both flip to matched |
| Video | Confirmed by hand: audio, video, camera-off and mute all cross correctly |
| Chat | Confirmed by hand: messages cross without a refresh and survive a reload |
| Fact-check | Confirmed by hand: a verdict appears in both windows with citations that resolve |
| Ratings | 26 automated tests. **Confirmed by hand:** a rating persists, shows on the profile, and a second attempt is refused rather than overwriting |

---

## Note on dates

Earlier reports in this directory carried dates inherited from a previous session's numbering
rather than the day the work happened. The Phase 7 report has been renamed to its real date
(2026-09-05) and this one uses today's. Nothing else changed.

---

## Git history (main)

| Commit | Description |
|---|---|
| `23b030e` | **Merge feature/fact-check — Phase 7 complete** |
| `47fdec5` | **Merge feature/chat — Phase 6 complete** |
| `4c328c4` | **Merge feature/video — Phase 5 complete** |
| `8448a47` | **Merge feature/matchmaking — Phase 4 complete** |
| `fe27248` | **Merge feature/topics — Phase 3 complete** |
| `5b67600` | **Merge feature/backend-foundation — Phase 2 complete** |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `1e24aaf` | Initial scaffold + blueprint docs |
