# Deploying Debable — free tier runbook

**Written:** 2026-09-06 · Supersedes the platform choices in
[`09-deployment.md`](09-deployment.md), which is nine lines and half stale.

> **This produces a demo deployment, not a production system.** It runs on Clerk
> **development** keys, because Clerk will not issue production keys for a `*.vercel.app`
> domain — production requires DNS records on a domain you own, and there is a dedicated
> error for it (`feature_requires_custom_domain`). Clerk's own documentation gives dev keys on
> a host-provided domain as the supported alternative. The cost is a Clerk dev banner in the
> corner, a lower user cap, and development keys in a public app. Say so wherever you share
> the link.
>
> To make it a real production deployment, buy a domain (~$5–15/year), point it at Vercel, and
> create a Clerk production instance. Nothing else in this guide changes.

## What doc 09 got wrong

It names Railway/Fly.io for the backend and Cloudflare R2 for storage.

- **Fly.io's free tier is gone**, and **Railway's has been gone since 2023.**
- **Render** is a fallback for the API, but its free Postgres is **deleted after 90 days**.
- **Cloudflare R2 is not needed at all.** Nothing in Debable stores objects — avatars are
  Clerk-hosted URLs, there are no uploads and no recordings. Skipped deliberately.

## The stack

| Layer | Service | Free tier | Card? |
|---|---|---|---|
| Frontend | **Vercel** Hobby | Non-commercial projects | No |
| Backend | **Koyeb** | 1 instance, 512 MB / 0.1 vCPU, 100 GB egress. WebSockets supported | Usually not |
| Database | **Neon** | 0.5 GB, 100 CU-hours/mo | No |
| Video | **LiveKit** Build | 5,000 WebRTC min/mo, 100 concurrent | No |
| Auth | **Clerk** free | Development keys (see above) | No |
| AI | **Gemini** free | Optional — without it, fact-checks return stub verdicts | No |

**Both Koyeb and Neon scale to zero.** After roughly an hour idle the first request is slow
and any open WebSocket has dropped. `frontend/hooks/use-debate-chat.ts` reconnects with
backoff, so this recovers — but it is the deployment's real failure mode and the easiest to
skip testing.

**Koyeb's free tier allows exactly one instance, which is what this application requires.**
See the comment on `CMD` in `docker/Dockerfile.backend`: the chat registry is per-process, so
a second worker silently breaks chat. Here the free tier enforces the correct deployment.

---

## 1. Database — Neon

1. Sign up at [neon.tech](https://neon.tech), create a project.
2. Copy the connection string and **rewrite the driver prefix**: Neon gives you
   `postgresql://…`, and this application needs `postgresql+psycopg://…`. Everything else in
   the string, including `?sslmode=require`, stays.
3. From your machine, run the migrations against it:

```bash
cd backend
DATABASE_URL="postgresql+psycopg://…neon…/debable?sslmode=require" uv run alembic upgrade head
```

Confirm with `alembic current` that it reports `0005`.

## 2. Backend — Koyeb

Create a Web Service from this GitHub repository, Docker build,
`docker/Dockerfile.backend`, build context the repository **root** (the Dockerfile copies
`backend/`), port **8000**, health check path `/api/v1/health`.

Environment variables:

```
ENV=production
DATABASE_URL=postgresql+psycopg://…neon…?sslmode=require
CORS_ORIGINS=https://<your-app>.vercel.app
CLERK_ISSUER=https://<your-instance>.clerk.accounts.dev
CLERK_AUTHORIZED_PARTIES=https://<your-app>.vercel.app
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=…
LIVEKIT_API_SECRET=…
GEMINI_API_KEY=…            # optional; omit for stub verdicts
TAVILY_API_KEY=…            # optional; omit and evidence comes from Wikipedia
```

`ENV=production` disables `/docs` and `/openapi.json` — see `app/main.py`.

⚠️ **`CORS_ORIGINS` is also read by the chat socket's `Origin` check**
(`app/websocket/auth.py`). Getting CORS right for REST but forgetting the socket produces a
working app with silently broken chat. It is one variable; just do not omit the Vercel URL.

You will not know the Vercel URL until step 3, so set these two after, or set them now if you
have already reserved the project name.

## 3. Frontend — Vercel

Import the repository, root directory `frontend`.

```
NEXT_PUBLIC_API_BASE_URL=https://<your-service>.koyeb.app/api/v1
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_…
CLERK_SECRET_KEY=sk_test_…
```

Note `pk_test_`/`sk_test_` — **development** keys, deliberately. Production keys will not work
on a `vercel.app` domain.

## 4. Clerk

Add `https://<your-app>.vercel.app` to the development instance's allowed origins. Nothing
else changes; the dev instance keeps working.

## 5. LiveKit

Reuse the existing project — LiveKit has no development/production split, only projects. Check
Settings → Project for your current limits.

---

## Verification

Two people, two machines, against the deployed URL:

1. Both sign in, queue the same topic, get matched.
2. Video and audio connect both ways.
3. Chat crosses both ways **without a refresh**, and survives a reload.
4. A fact-check verdict appears in **both** windows, with citations that resolve.
5. A report submits and confirms honestly.
6. Both rate; each rating shows on the other's profile.
7. **Leave it idle for over an hour and come back.** Koyeb and Neon have both scaled to zero.
   The first load is slow and chat reconnects — it should recover, not appear broken. This is
   the step most likely to be skipped and the most likely to be wrong.

## If something is broken

| Symptom | Cause |
|---|---|
| Eternal spinner, no sign-in button | The Vercel URL is not in Clerk's allowed origins |
| REST works, chat silently dead | The Vercel URL is missing from `CORS_ORIGINS` — the socket checks `Origin` against it |
| Both debaters see only their own messages | More than one worker. See `CMD` in `docker/Dockerfile.backend` |
| First request after idle times out | Koyeb and Neon cold start. Retry once; if it persists, check the Neon project is not suspended |
| Fact-check returns 503 | No `GEMINI_API_KEY`, or its free quota is spent. Stub verdicts still work with no key at all |
| `/docs` returns 404 | Correct — `ENV=production` disables it |
