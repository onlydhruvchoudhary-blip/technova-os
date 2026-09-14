# 🚀 Publish TECHNOVA OS to the internet

The preview you see runs in a **temporary sandbox** — its URL disappears when the sandbox resets.
To give it a **permanent public link** anyone can visit, deploy it to a real host.

TECHNOVA OS is a full-stack app (a web server + a database), so it can't go on a
"static site" host like GitHub Pages. Use a host that runs servers. The steps below use
**Render** because it has a free tier, gives you a public URL, and reads the config already
in this repo (`render.yaml` + `Dockerfile`).

---

## Option A — Render (recommended, free, ~10 minutes)

### 1. Put the code on GitHub
1. Create a free account at https://github.com and make a **new empty repository** (e.g. `technova-os`).
2. On your computer, from inside the `technova-os` folder, run:
   ```bash
   git init
   git add .
   git commit -m "TECHNOVA OS"
   git branch -M main
   git remote add origin https://github.com/<your-username>/technova-os.git
   git push -u origin main
   ```

### 2. Deploy on Render
1. Sign up at https://render.com (you can log in with GitHub).
2. Click **New +** → **Blueprint**.
3. Select your `technova-os` repository.
4. Render reads **`render.yaml`** automatically — it will create:
   - a **web service** (the app), and
   - a **free Postgres database**, with all secrets generated for you.
5. Click **Apply**. First build takes a few minutes (it builds the frontend + backend).
6. When it finishes, Render gives you a public URL like:
   **`https://technova-os.onrender.com`** ← share this with anyone. 🎉

### 3. Log in
On first boot the app seeds demo accounts. Log in as:
- **Email:** `admin@technova.club`
- **Password:** `password123`

> ⚠️ **Change this password immediately** after your first login — the whole world can now reach the site.

> 💡 Render's **free** web service sleeps after ~15 min of no traffic and takes ~30s to wake on the
> next visit. That's normal for free tier. Upgrade to a paid instance for always-on.

---

## Option B — Any Docker host (Railway, Fly.io, a VPS, etc.)
This repo has a self-contained **`Dockerfile`** at the root that builds everything into one image.

```bash
# Build and run locally (or on any server with Docker):
docker build -t technova-os .
docker run -p 8000:8000 \
  -e TECHNOVA_SECRET_KEY=$(openssl rand -hex 32) \
  -e TECHNOVA_QR_SECRET=$(openssl rand -hex 32) \
  technova-os
# then open http://localhost:8000
```

By default (no `TECHNOVA_DATABASE_URL`) it uses a local SQLite file. For production,
set `TECHNOVA_DATABASE_URL` to a Postgres connection string (Render/Railway give you one).

For a full Postgres + backups stack, use the included `docker-compose.yml` (see `docs/DEPLOYMENT.md`).

---

## Which should I pick?
| You want... | Use |
|---|---|
| The simplest free public link | **Option A (Render blueprint)** |
| To run it on your own server / another host | **Option B (Docker)** |
| Local Postgres + nightly backups | `docker-compose.yml` (`docs/DEPLOYMENT.md`) |

---

## Security before you go public
- [ ] Change the `admin@technova.club` password (and the other seeded accounts).
- [ ] Confirm `SECRET_KEY` and `QR_SECRET` are random (Render's blueprint does this automatically).
- [ ] Never commit a real `.env` or `*.db` file (already handled by `.gitignore`).

Full details live in `docs/DEPLOYMENT.md` and `docs/SECURITY.md`.
