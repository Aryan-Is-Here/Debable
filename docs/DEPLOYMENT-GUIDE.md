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

## Step 0 — Decide names and push the branch

Koyeb needs the Vercel URL and Vercel needs the Koyeb URL. Choosing both names up front
removes the circularity; otherwise you will deploy twice.

1. Go to [vercel.com/new](https://vercel.com/new) and check the project name `debable` is
   available. If it is taken, pick another and substitute it everywhere below.
2. Write down the two URLs you are committing to:
   - Frontend: `https://debable.vercel.app`
   - Backend: `https://debable-api-<your-org-slug>.koyeb.app` (Koyeb appends your org slug;
     you will see the exact URL after creating the service in Step 2)
3. Push the branch so the platforms can see it:

   ```bash
   git push -u origin feature/polish
   ```

Deploy from `feature/polish` first, and switch both platforms to `main` after it merges. That
keeps the merge gated on the deployment actually working.

---

## Step 1 — Neon (database)

1. Go to [neon.tech](https://neon.tech) and sign up with GitHub.
2. Create a project: name it `debable`, Postgres 16 or later, region nearest you.
3. On the project dashboard find the connection string. It looks like:
   `postgresql://user:pass@ep-xxx-123.aws.neon.tech/neondb?sslmode=require`
4. **Change the scheme from `postgresql://` to `postgresql+psycopg://`.** Change nothing
   else — keep the credentials, the host and `?sslmode=require`. This application uses the
   async psycopg driver and will not connect without it. This is the single most common way
   to get stuck here.
5. Apply the schema from your own machine (Neon has no shell):

   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require" uv run alembic upgrade head
   ```

6. **Verify before moving on.** This must print `0005`:

   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require" uv run alembic current
   ```

   If it prints nothing, the migrations did not run. If it errors on the driver, revisit 4.

---

## Step 2 — Koyeb (backend)

1. Go to [koyeb.com](https://www.koyeb.com) and sign up with GitHub. A card is usually not
   required; if it asks, that is its human-verification path.
2. **Create Web Service** → source **GitHub** → authorise Koyeb for
   `Aryan-Is-Here/Debable` → branch **`feature/polish`**.
3. Builder: choose **Dockerfile** (not Buildpack).
   - Dockerfile location: `docker/Dockerfile.backend`
   - Work directory: **leave empty.** The Dockerfile copies `backend/` relative to the
     repository root, so setting this breaks the build.
4. Instance: **Free** (512 MB / 0.1 vCPU). Region: Washington DC or Frankfurt — the free tier
   allows no others.
5. Exposed port: **8000**. Health check: HTTP on `/api/v1/health`.
6. Scaling: leave at **1 instance**. ⚠️ Not a default worth raising — see the `CMD` comment in
   `docker/Dockerfile.backend`. More than one process silently breaks chat.
7. Service name: `debable-api`.
8. Add the environment variables (values marked `<copy>` come from your `backend/.env`):

   ```
   ENV=production
   DATABASE_URL=postgresql+psycopg://…your Neon string…?sslmode=require
   CORS_ORIGINS=https://debable.vercel.app
   CLERK_ISSUER=https://distinct-kitten-15.clerk.accounts.dev
   CLERK_AUTHORIZED_PARTIES=https://debable.vercel.app
   LIVEKIT_URL=wss://debable-zm0l0fu7.livekit.cloud
   LIVEKIT_API_KEY=<copy>
   LIVEKIT_API_SECRET=<copy>
   GEMINI_API_KEY=<copy>
   ```

   Mark `DATABASE_URL`, `LIVEKIT_API_SECRET` and `GEMINI_API_KEY` as secrets if Koyeb offers
   the choice.
9. Deploy, and watch the build log. First build takes a few minutes.
10. **Verify before moving on.** Note your real URL from the dashboard, then:

    ```bash
    curl https://debable-api-YOURORG.koyeb.app/api/v1/health
    ```

    Expect `{"status":"ok","database":"ok","env":"production",...}`.
    - `database` not `ok` → the Neon URL is wrong, usually the missing `+psycopg`.
    - No response at all → check the build log and that the exposed port is 8000.

---

## Step 3 — Vercel (frontend)

1. Go to [vercel.com/new](https://vercel.com/new), sign in with GitHub, import
   `Aryan-Is-Here/Debable`.
2. **Root Directory: `frontend`.** ⚠️ The most-missed setting here — the repository root has
   no `package.json`, so the build fails immediately without it.
3. Framework preset should auto-detect as Next.js. Leave the build and output settings alone.
4. Project name: `debable`, matching what you reserved in Step 0.
5. Environment variables (copy the two Clerk values from your `frontend/.env.local`, where
   they already exist):

   ```
   NEXT_PUBLIC_API_BASE_URL=https://debable-api-YOURORG.koyeb.app/api/v1
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_…
   CLERK_SECRET_KEY=sk_test_…
   ```

   Note the `/api/v1` suffix on the API URL, and note `pk_test_`/`sk_test_` — **development**
   keys, deliberately. Production keys are rejected on a `vercel.app` domain.
6. Deploy. If the branch is not `feature/polish`, set it under Settings → Git and redeploy.
7. **Verify before moving on:** the site loads and renders the header. Sign-in will not work
   yet — that is Step 4.

---

## Step 4 — Clerk

1. Go to [dashboard.clerk.com](https://dashboard.clerk.com) and select the
   `distinct-kitten-15` development instance.
2. Find where allowed origins/domains are configured (**Configure → Domains**, or Paths; the
   label moves between Clerk releases).
3. Add `https://debable.vercel.app`.
4. **Verify:** reload the deployed site. The **Sign in** button should now appear in the
   header. If it does not within ~8 seconds you will see "Sign-in isn't loading" instead —
   that message exists precisely for this misconfiguration.

---

## Step 5 — LiveKit

Nothing to change. LiveKit has no development/production split, so the existing project works
as-is. Check Settings → Project for your current limits if you want to see the Build plan
allowances.

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
