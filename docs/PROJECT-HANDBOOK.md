# DebateMatch — Complete Project Handbook

**Generated:** 2026-07-18 · **Project state:** Phase 1 complete, Phase 2 starting
**Repository:** https://github.com/Aryan-Is-Here/Debable
**Local path:** `E:\Projects\Debable`

This is the full project reference: what DebateMatch is, everything built so far, every decision made, and exactly how to continue — written so that anyone (a new developer, a future AI session, or you after a break) can pick the project up from this document alone.

---

## 1. What DebateMatch is

DebateMatch is a **random video debate platform** where strangers are matched by **debate topic** instead of random interests. Its differentiator is an **on-demand AI fact-checking assistant**: during a debate, either participant can submit one specific claim; the backend sends only that claim to an isolated AI service, which verifies it against trusted sources and posts the verdict into the debate chat.

**MVP hypothesis being validated:** *Can AI-assisted fact-checking improve online debates?* Everything else is secondary.

### MVP scope (in)
Authentication · user profiles · topic creation · topic browsing · topic-based matchmaking · 1-to-1 video debates · text chat · on-demand AI fact-check · post-debate rating · basic reporting.

### MVP scope (out — do not build)
AI always-listening · automatic moderation · winner selection · points/ELO/leaderboards/badges · debate summaries · AI coaching · team debates · tournaments · premium features. If a request drifts into these, recommend postponing instead of implementing.

### Source of truth
The blueprint in `docs/` (13 documents: PRD, architecture, database, API spec, UI/UX, roadmap, git workflow, deployment, AI design, coding guidelines, vibe-coding playbook, prompt templates). It is deliberately skeletal. **Follow it; don't rewrite it unless asked.** Known gaps in it are tracked in §6 below — resolve each at its phase, never silently.

---

## 2. Tech stack

| Layer | Choice | Status |
|---|---|---|
| Frontend | Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind v4 | ✅ In use |
| UI kit | shadcn/ui **base-nova** style (built on `@base-ui`, NOT Radix), lucide icons | ✅ In use |
| Theming | next-themes (class strategy), wrapped in own `ThemeProvider` | ✅ In use |
| Forms | react-hook-form + zod v4 + `@hookform/resolvers` | ✅ In use |
| Toasts | sonner | ✅ In use |
| Server state | TanStack Query | ⏳ Planned (when real API exists) |
| Client state | Zustand | ⏳ Planned (only if needed) |
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL | 🔵 Phase 2 |
| Video | LiveKit | ⏳ Phase 5 |
| Auth | **Clerk** (decided; backend verifies Clerk JWTs) | ⏳ Phase 2 |
| AI | RAG + LLM (default: Anthropic Claude), isolated service | ⏳ Phase 7 |
| Local dev | Docker Compose (⚠️ Docker not yet installed — see §7) | 🔵 Phase 2 |
| Deploy | Vercel (frontend), Railway/Fly.io (backend), Neon/Supabase (Postgres), LiveKit Cloud | ⏳ Phase 9 |

**Toolchain on this machine:** Node v24.16, npm 11.13 (no pnpm) · Python 3.11.9, pip 26.1.2, uv 0.11.21 · **no Docker** · git with `gh` CLI absent (plain git + HTTPS remote works).

---

## 3. Repository layout

```
E:\Projects\Debable          (git repo, remote: Aryan-Is-Here/Debable)
├── docs/                    Blueprint (source of truth) + progress reports
│   ├── 01…12-*.md           PRD, architecture, DB, API, UI, roadmap, etc.
│   ├── 13-prompts/          Per-area prompt templates
│   └── progress/            Dated progress reports (one per phase start)
├── frontend/                Next.js app — COMPLETE for Phase 1
│   ├── app/                 Routes (see §4)
│   ├── components/          Feature components + components/ui/ (shadcn)
│   ├── hooks/               (empty — for future custom hooks)
│   ├── lib/                 types.ts, utils.ts, mock/, validation/
│   ├── services/            (empty — future API client layer)
│   └── styles/              (empty — globals live in app/globals.css)
├── backend/                 FastAPI skeleton dirs, all empty (.gitkeep)
│   ├── app/{api,core,models,schemas,services,repositories,db,websocket,ai,auth,utils}
│   ├── tests/
│   └── migrations/
├── docker/                  (empty — compose files land Phase 2)
├── .github/                 (empty — CI lands when useful)
├── shared/                  (empty — cross-cutting contracts if ever needed)
└── scripts/                 (empty)
```

---

## 4. Everything built so far (Phase 0 + Phase 1)

### Phase 0 — Planning ✅
Repo scaffolded to the blueprint structure; blueprint extracted into `docs/`; git + GitHub wired; root `.gitignore` (Node+Python+env) and README. Opinionated configs (linters, CI, Docker) deliberately deferred to their phases.

### Phase 1 — UI Prototype ✅ (merged to `main` via `feature/ui-prototype`)

Every screen renders from **typed mock data** — there is no backend yet. The entire core loop is clickable end-to-end.

| Route | Screen | What it does | Key files |
|---|---|---|---|
| `/` | Home | Hero, how-it-works (3 steps), trending topics grid | `app/page.tsx` |
| `/browse` | Browse | Search (title/description, case-insensitive), category chips incl. "All", most-active sort, empty state | `app/browse/page.tsx`, `components/topic-browser.tsx` |
| `/create` | Create Topic | RHF+zod form (title 10–120, description 20–600, category required), mock submit → toast → `/browse` | `app/create/page.tsx`, `components/create-topic-form.tsx`, `lib/validation/topic.ts` |
| `/waiting` | Waiting Room | 4s simulated matchmaking with elapsed timer → opponent reveal → Enter debate | `app/waiting/page.tsx`, `components/waiting-room.tsx` |
| `/debate/[roomId]` | Debate Room | Mock video tiles (mute/camera toggles, "mock" badge), working chat panel, **fact-check dialog** (claim 10–300 chars → 1.2s mock latency → verdict card in chat: True/False/Misleading/Unverified + explanation + sources) | `app/debate/[roomId]/page.tsx`, `components/debate-room-view.tsx`, `chat-panel.tsx`, `fact-check-dialog.tsx`, `fact-check-card.tsx`, `video-tile.tsx` |
| `/debate/[roomId]/results` | Results/Rating | 1–5 stars (hover states) + optional comment (≤300), mock submit → toast → home | `app/debate/[roomId]/results/page.tsx`, `components/rating-form.tsx` |
| `/profile` | Profile | Identity, stats (debates, avg rating, joined), created topics, debate history with ratings | `app/profile/page.tsx`, `lib/mock/profile.ts` |
| `/settings` | Settings | **Functional** theme selector; read-only account fields ("managed by Clerk"); mock notification switches; mock danger-zone delete w/ confirm dialog | `app/settings/page.tsx`, `components/settings-view.tsx` |
| — | Login | **Intentionally not built** — Clerk replaces it in Phase 2 | header has disabled "Sign in" |

**Shared infrastructure:** `app/layout.tsx` (fonts, ThemeProvider, SiteHeader, Toaster) · `components/site-header.tsx` (nav with active states, theme toggle, user menu) · `components/user-menu.tsx` (avatar dropdown → Profile/Settings; stands in for Clerk's user button) · `components/topic-card.tsx` (reused on Home/Browse/Profile; links into `/waiting?topic=<id>`) · `lib/types.ts` (all view-models: `Topic`, `UserSummary`, `DebateRoom`, `ChatMessage`, `FactCheck`, `UserProfile`, …) · `lib/mock/` (users, topics, debate incl. deterministic `mockFactCheck()`, profile).

**shadcn primitives installed:** button, card, badge, avatar, dropdown-menu, separator, input, field, label, textarea, select, sonner, dialog, scroll-area, switch.

---

## 5. Conventions & gotchas (READ BEFORE CODING)

1. **base-nova ≠ Radix.** Components come from `@base-ui`. Composition uses the **`render` prop**, never `asChild`:
   - `<Button render={<Link href="/x" />}>Label</Button>`
   - `<DialogTrigger render={<Button variant="secondary" />}>…</DialogTrigger>`
   - `asChild` fails the TypeScript build.
2. **Forms:** base-nova has no Radix-style `<Form>` wrapper. Pair react-hook-form (`register`/`Controller`) with the `Field`/`FieldLabel`/`FieldError` primitives; `FieldError` accepts an RHF-shaped `errors` array.
3. **Hydration-safe client state:** don't `setState` in `useEffect` to detect mount (lint error `react-hooks/set-state-in-effect`); use `useSyncExternalStore(() => () => {}, () => true, () => false)` as in `settings-view.tsx`.
4. **Server vs client:** pages stay server components; interactivity lives in dedicated `"use client"` components. Keep it that way.
5. **Mock layer is the contract:** when the backend arrives, replace `lib/mock/*` call-sites with a `services/` API client returning the same `lib/types.ts` shapes. Screens shouldn't need rewrites.
6. **Verification loop for every change:** `npm run lint` → `npm run build` (type-checks) → smoke-test routes (dev server + curl or browser). Nothing merges without all three green.
7. **Git workflow:** one feature per branch (`feature/<name>`), explain plan → files → risks before implementing, commit with conventional messages, push, merge to `main` when the phase/feature is complete. Never force-push `main` — it has received direct edits from Aryan (README) twice; always `git fetch` + merge.
8. **Windows quirks:** LF→CRLF warnings on commit are normal noise. No `.gitattributes` yet (optional improvement). Bash is available (Git Bash paths like `/tmp` work).
9. **Communication style (per project init):** think like a senior engineer; explain plan, list files to change, call out risks before coding; recommend postponing non-MVP features; ask when requirements are ambiguous; don't overengineer.

### How to run the frontend
```bash
cd E:\Projects\Debable\frontend
npm install        # first time only
npm run dev        # http://localhost:3000  (Ctrl+C to stop)
npm run lint       # ESLint
npm run build      # production build + type-check
```
Demo path: Browse → "Debate" on a card → wait ~4s → Enter debate → chat, Fact-check a claim → End debate → rate → Home. Try the theme toggle and mobile width.

---

## 6. Decisions locked & open conflicts

### Locked
| Decision | Detail |
|---|---|
| Auth = Clerk | Client-side login UI from Clerk; backend verifies Clerk-issued JWTs; **drop `POST /auth/login`** from doc 05 in Phase 2 |
| AI service isolation | Backend calls AI over HTTP; AI never listens continuously; LLM default = Anthropic Claude |
| Frontend stack details | See §2/§5 — base-nova, npm, no src/ dir, `@/*` alias |
| Progress reports | A cumulative report is written to `docs/progress/` at the **start of every phase** and committed |

### Open — resolve at the stated phase, never silently
| # | Conflict / gap | Phase | Working proposal |
|---|---|---|---|
| 1 | Reports feature (PRD + `POST /report`) has **no DB table** in doc 04 | 9 | Add `Reports` table (id, room_id, reporter_id, reported_user_id, reason, created_at) |
| 2 | `POST /match` mechanics undefined | 4 | Decide queue model (in-DB queue vs in-memory), delivery (poll vs WS) |
| 3 | Chat transport: doc 05 REST vs `websocket/` dir | 6 | WS for delivery, persist via Messages table |
| 4 | Schema gaps: no timestamps on Users/Topics; no `created_at` on Ratings; `FactChecks.sources` untyped | 2/3 | `created_at`/`updated_at` everywhere; `sources` = **JSONB** |
| 5 | **⚠️ PENDING (blocks Phase 2): local Postgres.** Docker isn't installed. | 2 | Options: (a) install Docker Desktop — matches blueprint exactly; (b) hosted Neon Postgres free tier — no local Docker, compose file still written for CI/later; (c) SQLite — fastest but deviates, not recommended. **Aryan must pick before DB work starts.** |

---

## 7. How to continue — Phase 2 in extreme detail

**Goal:** Backend Foundation. A running FastAPI service with config, DB, migrations, auth verification, health check, and tests — no feature endpoints yet beyond health.

**Branch:** `feature/backend-foundation`

### Step-by-step
1. **Resolve conflict #5** (Postgres hosting — see §6). Everything below assumes a Postgres URL exists.
2. **Python project setup** (`backend/`): use **uv** (installed) — `pyproject.toml` with fastapi, uvicorn, sqlalchemy, alembic, psycopg, pydantic-settings, httpx, pytest, ruff. Pin Python 3.11.
3. **App skeleton** (`backend/app/`):
   - `main.py` — FastAPI factory, CORS (allow `localhost:3000`), router mounting, exception handlers.
   - `core/config.py` — pydantic-settings `Settings` from env (`DATABASE_URL`, `CLERK_*`, `ENV`); `.env.example` committed, `.env` ignored.
   - `core/logging.py` — struct-ish logging setup.
4. **Database layer** (`app/db/`): engine/session factory, `Base`, FastAPI dependency `get_db`.
5. **Models** (`app/models/`) per doc 04 **with agreed fixes** (conflict #4): users, topics, debate_rooms, messages, fact_checks (sources JSONB), ratings — all with timestamps. Users carry `clerk_user_id` unique key (email/username synced from Clerk).
6. **Alembic** (`backend/migrations/`): init, autogenerate initial migration, verify up/down.
7. **Auth** (`app/auth/`): Clerk JWT verification dependency (JWKS fetch + cache, issuer/audience checks) → yields current user; **no login endpoint**.
8. **API** (`app/api/`): versioned router `/api/v1`, `GET /api/v1/health` (checks DB connectivity).
9. **Docker** (`docker/`): `docker-compose.yml` (postgres:16 + backend), `Dockerfile` for backend — written even if Docker isn't installed yet (used by CI/deploy later).
10. **Tests** (`backend/tests/`): pytest + httpx `AsyncClient`; health test; auth-dependency unit test with a fake JWKS.
11. **Verify:** `uv run pytest`, `uv run uvicorn app.main:app --reload` → `curl localhost:8000/api/v1/health`.
12. **Commit → push → merge** when green; write nothing to `frontend/` in this phase.

### Phases 3–9 (summary map)
- **Phase 3 Topics:** CRUD endpoints (`POST/GET /topics`), repository pattern, wire frontend Browse/Create to real API via `services/` + TanStack Query; keep zod schema aligned with backend validation.
- **Phase 4 Matchmaking:** resolve conflict #2; `POST /match` + queue; Waiting Room polls/WS; creates DebateRooms.
- **Phase 5 Video:** LiveKit Cloud; backend mints room tokens; replace `VideoTile` mock with LiveKit React components.
- **Phase 6 Chat:** resolve conflict #3; WS endpoint in `app/websocket/`; persist Messages; swap ChatPanel mock transport.
- **Phase 7 AI Fact Check:** isolated `app/ai/` service client + separate AI service (RAG over trusted sources, Claude); `POST /room/{id}/fact-check`; result broadcast into chat; replace `mockFactCheck`.
- **Phase 8 Ratings:** `POST /room/{id}/rating`; wire RatingForm; enforce one rating per debater per room.
- **Phase 9 Polish & Deploy:** resolve conflict #1 (Reports); `POST /report` + minimal UI; deploy per doc 09; a11y/dark-mode/QA pass.

Each phase: new branch, plan first, progress report at phase start, blueprint-conflict check, tests where appropriate, merge on green.

---

## 8. Git history of `main` (oldest → newest)

| Commit | Description |
|---|---|
| `1e24aaf` | chore: initial scaffold and blueprint docs |
| `03b5607` / `2c8fd99` | Aryan: first commit / README rename |
| `8df97e9` | feat(frontend): Next.js scaffold, app shell, Home |
| `508c781` | feat(frontend): Browse Topics (search + filter) |
| `07e12e3` | feat(frontend): Create Topic (validated form) |
| `86f5459` | feat(frontend): debate flow (Waiting/Debate/Results) |
| `bef71b0` | feat(frontend): Profile + Settings + user menu |
| `52f4a37` | Merge feature/ui-prototype — **Phase 1 complete** |
| `f23bdbf` / `bdf7ad9` | Aryan: README cleanup/enhancement |
| `6799bfb` | Merge remote README updates |
| `2f7f2b1` | docs: Phase 2 start progress report |

---

*This handbook lives at `docs/PROJECT-HANDBOOK.md`. Shorter per-phase progress reports live in `docs/progress/`. Both are updated at each phase start.*
