# DebateMatch

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
├── docker/       # Docker / docker-compose (added at its phase)
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

Scaffold only — modular folder skeleton in place. Feature work proceeds **strictly sequentially by
roadmap phase**, one feature per branch, with a plan reviewed before each module is implemented.
