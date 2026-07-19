# DebateMatch — Progress Report

**Report date:** 2026-07-18 · **Milestone:** Start of Phase 2 (Backend Foundation)
**Repository:** https://github.com/Aryan-Is-Here/Debable

This report is generated at the start of each new phase and covers all progress to date.

---

## Where we are

| Phase | Status |
|---|---|
| Phase 0 — Planning | ✅ Complete |
| **Phase 1 — UI Prototype** | ✅ **Complete** (merged to `main`) |
| Phase 2 — Backend Foundation | 🔵 Starting now |
| Phase 3 — Topics | ⏳ Pending |
| Phase 4 — Matchmaking | ⏳ Pending |
| Phase 5 — Video | ⏳ Pending |
| Phase 6 — Chat | ⏳ Pending |
| Phase 7 — AI Fact Check | ⏳ Pending |
| Phase 8 — Ratings | ⏳ Pending |
| Phase 9 — Polish & Deploy | ⏳ Pending |

---

## Phase 0 — Planning ✅

- Repository scaffolded to the blueprint's modular structure (`frontend/`, `backend/app/*`, `docs/`, `docker/`, `.github/`, `shared/`, `scripts/`).
- Blueprint documents (PRD, architecture, database, API, roadmap, guidelines) placed in `docs/` — treated as **source of truth**.
- Git initialized, connected to GitHub, baseline committed.

**Key decisions locked:**
- **Auth = Clerk** — client-side login; backend verifies Clerk JWTs. `POST /auth/login` (doc 05) is dropped in Phase 2.
- **AI fact-check** stays an isolated service the backend calls over HTTP; on-demand only (never always-listening).
- Build strictly sequential by roadmap phase; one feature per branch; plan → files → risks explained before each module.

**Open blueprint conflicts (deliberately deferred to their phase):**
| Conflict | Resolve at |
|---|---|
| Reports feature has no DB table in doc 04 | Phase 9 |
| `POST /match` matchmaking mechanics undefined (queue/poll/WS) | Phase 4 |
| Chat: doc 05 says REST `POST /room/{id}/message`, structure has `websocket/` | Phase 6 |
| Schema gaps: missing timestamps on Users/Topics/Ratings; `FactChecks.sources` type | Phase 2/3 (JSONB planned) |

---

## Phase 1 — UI Prototype ✅

All screens from `docs/06-ui-ux.md` built **mock-data only** (no backend), merged to `main` via `feature/ui-prototype`.

### Screens delivered

| Screen | Route | Highlights |
|---|---|---|
| Home | `/` | Hero, how-it-works, trending topics grid |
| Browse Topics | `/browse` | Case-insensitive search, category filter chips, empty state |
| Create Topic | `/create` | react-hook-form + zod validation, mock submit → toast |
| Waiting Room | `/waiting` | Simulated matchmaking (timer), opponent reveal, cancel |
| Debate Room | `/debate/[roomId]` | Mock video tiles (mute/camera toggles), live chat panel, **on-demand fact-check dialog** → verdict card posts into chat |
| Results / Rating | `/debate/[roomId]/results` | 1–5 stars + optional comment, mock submit |
| Profile | `/profile` | Stats (debates, avg rating, joined), created topics, debate history |
| Settings | `/settings` | **Functional** theme selector, read-only account (until Clerk), mock notifications + danger zone |
| Login | — | **Intentionally not built** — replaced by Clerk in Phase 2 |

### Technical foundation

- **Stack:** Next.js 16 (App Router, Turbopack) · React 19 · TypeScript · Tailwind v4 · shadcn/ui (base-nova style) · next-themes (dark mode) · react-hook-form + zod · sonner (toasts) · lucide icons.
- **Architecture:** server components for data/layout, client components only where interactive; typed view-models (`lib/types.ts`) + mock fixtures (`lib/mock/`) stand in for the API; `lib/validation/topic.ts` zod schema will be reused against the real backend.
- **Conventions:** base-nova uses `@base-ui` primitives — composition via `render` prop (not Radix's `asChild`). Theme dependency wrapped in our own `ThemeProvider` for replaceability.
- **Verification:** every screen passed ESLint + production build (type-checked); all 8 routes smoke-tested returning 200.

### The core loop works end-to-end (mocked)

Browse → pick topic → Waiting Room finds opponent → Debate Room (chat + fact-check a claim → AI verdict card in chat) → End debate → rate opponent → Home.

### How to run it

```bash
cd frontend
npm install
npm run dev     # → http://localhost:3000
```

---

## What Phase 2 (starting now) will deliver

- FastAPI application skeleton (`backend/app/`) with config, logging, error handling.
- PostgreSQL via Docker Compose; SQLAlchemy models + Alembic migrations for the doc 04 schema (with agreed fixes: timestamps everywhere, `FactChecks.sources` as JSONB).
- Clerk JWT verification dependency (no `/auth/login` endpoint).
- Health endpoint + test harness (pytest).

---

## Git history (main)

| Commit | Description |
|---|---|
| `6799bfb` | Merge remote README updates |
| `52f4a37` | **Merge feature/ui-prototype — Phase 1 complete** |
| `bef71b0` | Profile + Settings screens, header user menu |
| `86f5459` | Debate flow: Waiting Room, Debate Room, Results |
| `07e12e3` | Create Topic screen with validated form |
| `508c781` | Browse Topics screen with search + filter |
| `8df97e9` | Next.js scaffold, app shell, Home screen |
| `1e24aaf` | Initial scaffold + blueprint docs |
