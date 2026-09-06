# Debable — Progress Report

**Report date:** 2026-09-06 · **Milestone:** Start of Phase 9 (Polish & Deploy)
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
| Phase 7 — AI Fact Check | ✅ Complete |
| **Phase 8 — Ratings** | ✅ **Complete** (merged to `main`) |
| Phase 9 — Polish & Deploy | 🔵 Starting now |
| Phase 10 — Professional UI/UX Redesign | ⏳ Pending |

**Eight of ten phases merged, and the product is feature-complete.** Two strangers can be
matched by topic, see and hear each other, hold a persisted conversation, fact-check a claim
mid-debate with the verdict reaching both windows, and rate each other afterwards. Every
screen renders server data — `frontend/lib/mock/` was deleted in Phase 8.

**242 backend tests pass, 0 skipped.** None of them touch a network.

---

## Phases 0–6 in brief

**Phase 0** locked the early decisions: Clerk for auth with no login endpoint of our own, the
fact-check as an isolated on-demand service, strictly sequential phases.

**Phase 1** built all eight screens against typed mock data. `lib/types.ts` was written as the
contract *before* any backend existed — and never changed once. Every later phase swapped a
data source rather than rewriting a screen. It is the single decision that paid off most.

**Phase 2** brought up FastAPI, async SQLAlchemy over psycopg 3, Alembic, Clerk JWT
verification, and a health endpoint that fails honestly.

**Phase 3** made topics real and settled the category conflict with an indexed `varchar` and
one shared allowlist rather than a Postgres enum.

**Phase 4** built matchmaking on `SELECT … FOR UPDATE SKIP LOCKED`, and cost three rounds of
debugging after it "worked". Its lessons still govern the project.

**Phase 5** added LiveKit video with a deliberately minimal token grant.

**Phase 6** resolved the last transport conflict: history over REST, delivery over a
WebSocket, authenticated by a first frame rather than a query-string token.

**Phase 7** shipped the differentiator — and neither of the two designs it was planned with.
Free Google Search grounding turned out to be unobtainable, which only a real API call
revealed. Retrieving evidence ourselves made the design *better*: the trusted-source allowlist
became a constraint on what is fetched rather than a filter on what is cited.

---

## Phase 8 — Ratings ✅

The last mock data, and two findings worth more than the feature.

**The results page was rating nobody.** It rendered the demo room for *any* roomId: the form
submitted, a toast appeared, nothing was written. It survived seven phases because it never
looked broken.

**And nothing led to it.** The page was reachable only by the one-time redirect after ending a
debate, so a debate you skipped rating was stranded permanently. Every test passed, because
tests address the URL directly.

That was the **second** time this project shipped working, tested code that nothing reached —
Phase 5's opponent mute indicator was the first. Both were found by a person using the
product. Recorded as handbook §5.28, and it is the trap Phase 9 is most likely to repeat.

---

## Phase 9 — Polish & Deploy (starting now)

The last substantive phase. Two halves: close the final blueprint gap, and put the product on
a public URL.

### Conflict #1 — the last open gap, and the last migration

The PRD lists a Reports feature and `docs/05-api-specification.md` has `POST /report`, but
`docs/04-database-design.md` has no table for it. Closing it needs revision `0005` — **the only
migration left in the project.** Everything built since Phase 2 has fitted the original schema.

Decided: `reports(id, room_id, reporter_id, reported_user_id, category, detail, created_at)`,
with `category` an indexed `varchar` against a shared allowlist constant rather than a Postgres
enum — the same reasoning that settled conflict #6, since the frontend needs the list anyway.

The endpoint will be `POST /rooms/{room_id}/report` rather than doc 05's bare `POST /report`,
for the reason ratings hang off a room: what is being reported is conduct in a specific
debate, and the room is what proves the reporter was there. A deliberate, recorded deviation.

**Explicitly not built:** a moderation queue, an admin surface, or any `GET /reports`. Handbook
§1 lists automatic moderation as out of scope. A report is a *record*, not a workflow — and the
confirmation message must say so rather than implying a review that will not happen.

### Deployment: what the research actually found

`docs/09-deployment.md` is **nine lines** and half of it is already wrong. Verified rather than
assumed, because that exact mistake cost Phase 7 two redesigns:

| Layer | Decision |
|---|---|
| Frontend | Vercel Hobby — free, no card |
| Backend | **Koyeb** — 512 MB, WebSockets supported, scales to zero after 1h idle |
| Database | **Neon** — 0.5 GB, scale-to-zero |
| Video | LiveKit **Build** — 5,000 WebRTC min/mo, no card; the existing project works |
| Auth | Clerk **development** keys on the `vercel.app` URL |

**Doc 09 is stale:** Fly.io's free tier is dead and Railway's has been gone since 2023. Render
is the fallback but deletes its free Postgres after 90 days.

**Clerk cannot issue production keys for a `*.vercel.app` domain.** Production requires DNS
records on a domain you own; there is a dedicated error code for it. Clerk's own docs give
development keys on a host-provided domain as the supported alternative, and that is the
decision — the project has no budget for a domain. **The consequence must be stated plainly
wherever this deployment is described: it is a demo, not a production system.** Dev keys, a
Clerk warning banner, and a lower user cap.

**Cloudflare R2 appears in doc 09 and is not needed.** Nothing in the product stores objects.
Skipped deliberately.

**One happy accident:** Koyeb's free tier allows exactly one instance, which is precisely what
the per-process chat registry requires. The free tier enforces the correct deployment — the
constraint that was most likely to be got wrong is now impossible to get wrong.

### Risks

- **Scale-to-zero on both the API and the database.** After an hour idle, the first request is
  slow and open WebSockets have dropped. `use-debate-chat.ts` already reconnects with backoff,
  but that path has never been exercised against a real cold start.
- **The chat socket's `Origin` check reads `CORS_ORIGINS`.** Configuring CORS for the Vercel
  URL but forgetting the socket would give working REST and silently broken chat.
- **A report action with no button.** §5.28, for the third time. The entry point is part of the
  feature, not a follow-up.

### The check that will prove it

Two people, different machines, against the deployed URL: match, video, chat, fact-check,
report, rate. Then leave it idle for an hour and return — the app should recover rather than
appear broken.

---

## Verification status

| Area | Evidence |
|---|---|
| Backend suite | 242 tests pass, 0 skipped. None touch a network |
| Lint/format | `ruff check`, `ruff format --check`, `eslint` all clean |
| Build | `npm run build` compiles all 9 routes |
| Migrations | `alembic check` reports no drift |
| Topics / Matchmaking / Video / Chat / Fact-check / Ratings | All confirmed by hand |
| Reports | ⏳ Not started |
| Deployment | ⏳ Not started |

---

## Git history (main)

| Commit | Description |
|---|---|
| `9e2edaf` | **Merge feature/ratings — Phase 8 complete** |
| `23b030e` | **Merge feature/fact-check — Phase 7 complete** |
| `47fdec5` | **Merge feature/chat — Phase 6 complete** |
| `4c328c4` | **Merge feature/video — Phase 5 complete** |
| `8448a47` | **Merge feature/matchmaking — Phase 4 complete** |
| `fe27248` | **Merge feature/topics — Phase 3 complete** |
| `5b67600` | **Merge feature/backend-foundation — Phase 2 complete** |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `1e24aaf` | Initial scaffold + blueprint docs |
