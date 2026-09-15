# Deploying TECHNOVA OS

This is the exact, copy-along guide to ship a new version to production. It matches how this repo is
already set up: code lives under a nested `technova-os/` folder, deploys to **Render** (Docker web
service + managed Postgres), and CI runs on **GitHub Actions**.

- **Repo:** `github.com/onlydhruvchoudhary-blip/technova-os`
- **Live service:** Render web service (`srv-...`) + `technova-db` Postgres
- **Health check:** `GET /api/health`

---

## TL;DR (the normal case)

1. Upload the new code to GitHub (drag-and-drop into the `technova-os/` folder — see below).
2. GitHub Actions runs lint + tests + typecheck + build. If green **and** you've set the deploy-hook
   secret, it triggers Render automatically. Otherwise, click **Manual Deploy** in Render.
3. Render rebuilds the image, applies DB migrations **on boot** (`alembic upgrade head`), and goes
   live. No manual database step is ever needed.

That's it. The sections below are the details and the one-time setup.

---

## 0. What NOT to upload

These are generated or local-only and must never be committed (they're already in `.gitignore`):

- `backend/technova.db` and any `*.db` — local SQLite dev data.
- `backend/frontend_dist/` — the built frontend. **Render rebuilds it from source**, so don't ship
  the build output; shipping it can serve a stale UI.
- `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.env`, `backups/`.

> If you're uploading the provided `technova-os-deploy.zip`, it has already been cleaned of all of the
> above. If you're zipping yourself, exclude those paths.

---

## 1. Push the code to GitHub (web uploader)

Because you upload via the browser (no local `git`):

1. Open `github.com/onlydhruvchoudhary-blip/technova-os`.
2. Navigate **into the `technova-os/` folder** in the repo (the project is nested there — the CI and
   `render.yaml` paths depend on this, e.g. `dockerfilePath: ./technova-os/Dockerfile`).
3. Click **Add file → Upload files**, then drag in the contents of the local `technova-os/` folder
   (i.e. `backend/`, `frontend/`, `docs/`, `README.md`, …). GitHub preserves the folder structure.
4. Commit to the **`main`** branch (the message can be anything, e.g. "Cycle 8: activity feed +
   pub/sub broker + live sandbox").

> **Keep the nesting.** The repo layout is `technova-os/technova-os/backend/...`. If you ever upload
> to the repo root instead of into the `technova-os/` folder, the CI `working-directory` and Render's
> `dockerfilePath` will not find anything.

---

## 2. Continuous Integration (automatic)

On every push/PR to `main`, `.github/workflows/ci.yml` runs three jobs:

| Job | What it checks |
|---|---|
| **backend** | `ruff check app`, `alembic upgrade head` on a fresh DB, then `pytest -q` (81 tests). |
| **frontend** | `npm ci`, `tsc -b` (typecheck), `npm run build`. |
| **deploy** | Runs only on `main` **after backend + frontend both pass**; pings the Render deploy hook. |

If any test/lint/build fails, the deploy job does not run — a red build never reaches production.

---

## 3. Deploying to Render

You have two equally-fine options. Pick one.

### Option A — CI-gated deploy hook (recommended)

Deploys automatically, but **only after CI is green**. One-time setup:

1. In **Render → your web service → Settings → Deploy Hook**, copy the hook URL
   (looks like `https://api.render.com/deploy/srv-xxxx?key=yyyy`).
2. In **GitHub → repo → Settings → Secrets and variables → Actions → New repository secret**:
   - **Name:** `RENDER_DEPLOY_HOOK_URL`
   - **Value:** the URL you copied.
3. Done. From now on, a green push to `main` auto-triggers a Render deploy. If the secret is missing,
   the deploy job logs a warning and skips (CI still passes) — so nothing breaks if you forget.

> If you use this, turn **off** Render's own "Auto-Deploy" (Service → Settings) so you don't get two
> deploys per push. This way the *only* path to production is "CI passed".

### Option B — Render native auto-deploy / manual

- Leave Render's **Auto-Deploy: Yes** and it redeploys on every push to `main` (no CI gate).
- Or **Manual Deploy → Deploy latest commit** from the Render dashboard whenever you want.
- In this case you can ignore the `RENDER_DEPLOY_HOOK_URL` secret; the CI deploy job just skips.

### First-time service creation (only if the service doesn't exist yet)

1. Render → **New + → Blueprint**, point it at the GitHub repo. Render reads `render.yaml` and
   provisions the web service + `technova-db` Postgres, and auto-generates `TECHNOVA_SECRET_KEY` /
   `TECHNOVA_QR_SECRET`.
2. Wait for the first build; the service comes up seeded and ready.

---

## 4. Database migrations (automatic, safe)

**You never run a migration command by hand.** On startup the app calls `alembic upgrade head`
(`backend/app/main.py::_init_schema`), which:

- Applies any new migrations to the existing Postgres database.
- Stamps a pre-existing (pre-Alembic) database at baseline first, if needed.
- Falls back to `create_all` if Alembic is somehow unavailable, so the app always boots.

New migrations are **additive and non-destructive** — e.g. the latest, `a1b2c3d4e5f6` (activity
feed), is `create_table` + `create_index` only. Verified locally: upgrading a populated database
preserves all existing rows and adds the new table.

If you ever need to run it manually (e.g. debugging via the Render shell):

```bash
cd technova-os/backend && alembic upgrade head
```

---

## 5. Verify the deploy

Once Render shows **Live**:

```bash
curl -s https://<your-service>.onrender.com/api/health          # -> {"status":"ok",...}
curl -s -o /dev/null -w "%{http_code}\n" https://<your-service>.onrender.com/   # -> 200
```

Then in the browser:

- Log in (seeded admin: `admin@technova.club` / `password123` — **change this** for a real club).
- Open **Live Activity** and redeem something / solve a challenge in another tab → the event should
  appear in real time (SSE).
- Press **⌘K / Ctrl-K** → command palette opens.

Optional load/smoke check against the live URL:

```bash
python scripts/loadtest.py --base https://<your-service>.onrender.com --users 20 --requests 10 --sse 10
```

---

## 6. Rollback

- **Render → your service → Events / Deploys → pick a previous successful deploy → Rollback.**
- Because migrations are additive, rolling the *app* back is safe; the newer table simply goes unused.
  Avoid rolling the *database* back independently.

---

## Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| CI can't find files / "no such directory" | Code wasn't uploaded **into** the `technova-os/` folder. Re-upload preserving the nested path. |
| Deploy job skipped with a warning | `RENDER_DEPLOY_HOOK_URL` secret not set. Add it (§3A) or use Render auto-deploy (§3B). |
| Two deploys per push | Both the CI hook *and* Render auto-deploy are on. Turn off Render Auto-Deploy (§3A). |
| UI looks stale after deploy | A committed `backend/frontend_dist/` shadowed the fresh build. Ensure it's **not** in the repo (§0); Render rebuilds it. |
| 500s right after deploy | Check Render logs. Missing env vars? `render.yaml` auto-generates secrets, but a manually-created service may need `TECHNOVA_SECRET_KEY` / `TECHNOVA_QR_SECRET` / `TECHNOVA_DATABASE_URL` set. |
| Health check failing | The app binds `0.0.0.0` and serves `/api/health`; confirm the service's health-check path is `/api/health`. |
