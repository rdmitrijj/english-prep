# Deploying English-prep (Render + Neon, both free)

What you end up with: one Render web service at `https://<name>.onrender.com` that serves the app, the API and the audio,
and a Neon Postgres database. Content and users are put into Neon **from your machine** (Render's free plan has no shell).

## 0. Before you start
- The repo is pushed to GitHub (`git push origin main`). Render builds from GitHub.
- Docker is running locally (the seed and user commands below run in the dev `backend` image).

## 1. Neon: create the database
1. Sign in at <https://console.neon.tech> → **New project**. Name: `english-prep`. Region: **AWS Europe Central 1 (Frankfurt)**,
   the same region as the Render service, so every query is a short hop.
2. On the project dashboard click **Connect**. Turn **Connection pooling off**. You want the *direct* URL: its host has no
   `-pooler` in it.
3. Copy the string. It looks like
   `postgresql://neondb_owner:PASSWORD@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.
4. Rewrite it for our driver (asyncpg):
   - `postgresql://` → `postgresql+asyncpg://`
   - `?sslmode=require&channel_binding=require` → `?ssl=require`

   Result: `postgresql+asyncpg://neondb_owner:PASSWORD@ep-xxx.eu-central-1.aws.neon.tech/neondb?ssl=require`.
   This is your **NEON_URL** for the rest of this guide. Keep it secret: it contains the password.

## 2. Render: create the service from the blueprint
1. Sign in at <https://dashboard.render.com> with GitHub → **New** → **Blueprint**.
2. Pick the `english-prep` repo. Render reads `render.yaml` and shows one web service, `english-prep`.
3. It asks for `DATABASE_URL`: paste **NEON_URL**. (`JWT_SECRET` is generated for you; `COOKIE_SECURE` is preset.)
4. **Apply**. The first build takes ~5 min (it builds the frontend, then the Python image with the audio baked in).
   On start the container runs `alembic upgrade head`, so the tables are created in Neon automatically.
5. When the service shows **Live**, open `https://<name>.onrender.com/api/health` → `{"status":"ok"}`.

If the name `english-prep` is taken, Render adds a suffix; the URL is shown at the top of the service page.

## 3. Load the content into Neon
From the repo root on your machine:

```bash
export NEON_URL='postgresql+asyncpg://...?ssl=require'   # single quotes: the password may contain $ or &
docker compose run --rm --no-deps -e DATABASE_URL="$NEON_URL" backend python -m scripts.content.seed
```

It prints one line per test (`mock-01: created`, ...). It is idempotent (safe to run again), so after adding new content
later you run the same command.

`--no-deps` stops Compose from starting the local Postgres, and `-e DATABASE_URL=...` overrides the local database URL.

## 4. Create your user
Easiest: set `ADMIN_EMAIL` and `ADMIN_PASSWORD` (min 10 chars) in the service's **Environment** tab. The user is
created on the next start. Changing them later does not change an existing user's password.

Or from your machine:
```bash
docker compose run --rm --no-deps -e DATABASE_URL="$NEON_URL" backend \
  python -m app.cli create-user --email you@example.com --name "Your Name"
```
It asks for the password twice (at least 10 characters). There is no public sign-up.

## 5. Log in
Open `https://<name>.onrender.com` → log in → start a mock.

## Day to day
- **Deploy a change:** `git push origin main`. Render rebuilds and restarts by itself (`autoDeploy`), running new migrations on start.
- **Score essays:** the same loop as locally (PLAN.md M6), with the database pointed at Neon:
  ```bash
  docker compose run --rm --no-deps --user 1000:1000 -e DATABASE_URL="$NEON_URL" backend \
    python -m scripts.essays pending --out /srv/content/drafts/pending.json
  # ...two blind examiner runs write content/drafts/run-a.json and run-b.json, then for each:
  docker compose run --rm --no-deps --user 1000:1000 -e DATABASE_URL="$NEON_URL" backend \
    python -m scripts.essays apply /srv/content/drafts/run-a.json
  ```
- **Score Speaking:** the same, with `scripts.speaking pending --out /srv/content/drafts/speaking.json` and
  `scripts.speaking apply …` (it transcribes the recordings on your machine first; see PLAN.md M10).
- **Logs:** Render dashboard → the service → **Logs**.

## Free-plan behaviour to expect
- **Cold start.** The Render service sleeps after 15 min with no visits; the next visit takes ~1 min to wake it.
  A running exam is not affected: deadlines live in the database and an attempt past its deadline is submitted
  on the next request.
- **Neon suspends** its compute after 5 min idle; the first query after that takes a second or two. The app re-checks
  connections before using them (`pool_pre_ping`), so this shows up only as a slightly slower first page.
- Audio is inside the image (~70 MB), so it survives restarts. Re-rendered audio needs a commit and push to go live.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Deploy fails, log shows `sslmode` / `channel_binding` error | The URL wasn't rewritten: it must end in `?ssl=require` and start with `postgresql+asyncpg://`. |
| `/api/health` → 503 | Render can't reach Neon: check `DATABASE_URL` in the service's **Environment** tab. |
| Login works locally but not on Render | You created the user in the local DB: re-run step 4 with `-e DATABASE_URL="$NEON_URL"`. |
| Mock list is empty | Step 3 wasn't run against Neon. |
| "Too many login attempts" | Behind Render's proxy the limit (5 per minute) is shared by everyone; wait a minute. |
