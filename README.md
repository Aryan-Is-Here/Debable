[Debablereadme.txt](https://github.com/user-attachments/files/29934435/Debablereadme.txt)

# Debable

A random video debate platform that matches strangers by **debate topic** instead of random
interest — with an **on-demand AI fact-checking** assistant. During a debate, either participant
can submit a specific claim; the backend forwards only that claim to an isolated AI service, which
verifies it against trusted sources and returns the result into the debate chat.

**MVP hypothesis:** _Can AI-assisted fact-checking improve online debates?_

> The blueprint in [`docs/`](./docs) (PRD, roadmap, architecture, database design, development
> phases, coding standards) is the **source of truth**. This README is a short pointer only.

## Repository structure

```
debate-match/
├── docs/         # Blueprint — source of truth
├── frontend/     # Next.js + React + TypeScript + Tailwind + shadcn/ui
├── backend/      # FastAPI + SQLAlchemy + Alembic + PostgreSQL
├── docker/       # docker-compose (Postgres 16 + API) and the backend Dockerfile
├── shared/       # Cross-cutting shared types/contracts
├── scripts/      # Dev & ops scripts
└── .github/      # CI workflows (added at its phase)
```

## Tech stack (per blueprint)

| Area   | Choice |
| ------ | ------ |
| Frontend | Next.js, React, TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand |
| Backend  | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Video    | LiveKit |
| Auth     | Clerk (client login; backend verifies Clerk JWTs) |
| AI       | RAG + LLM, exposed as an isolated backend service |
| Deploy   | Vercel (frontend), Railway/Fly.io (backend) |

## Status

**Phase 1 (UI prototype) and Phase 2 (backend foundation) are complete; Phase 3 (Topics) is next.**
The frontend renders every screen from typed mock data, and the backend runs with configuration,
migrations, Clerk JWT verification and a health endpoint — but the two are not wired together yet.
Feature work proceeds **strictly sequentially by roadmap phase**, one feature per branch, with a
plan reviewed before each module is implemented.

See [`docs/PROJECT-HANDBOOK.md`](./docs/PROJECT-HANDBOOK.md) for the full picture and
[`docs/progress/`](./docs/progress) for per-phase reports.

## Running it locally

```bash
# Frontend — http://localhost:3000
cd frontend && npm install && npm run dev

# Backend — http://localhost:8000 (needs Docker for Postgres)
docker compose -f docker/docker-compose.yml up -d db
cd backend && cp .env.example .env && uv sync
uv run alembic upgrade head
uv run python -m app
```
#
