# Deployment guide

TECHNOVA OS is designed to travel from **internal club platform → public showcase → hosted product**.

## Environments

| | Dev | Production |
|---|---|---|
| DB | SQLite file (`technova.db`) | PostgreSQL 16 |
| Server | `uvicorn --reload` + `vite dev` | `gunicorn` (uvicorn workers) serving API + built SPA |
| Config | defaults in `app/config.py` | `.env` (see `.env.example`) |
| Frontend | Vite dev server, proxies `/api` | Pre-built static files served by the API |

## Environment variables

All backend settings read the `TECHNOVA_` prefix (see `.env.example`). The critical production ones:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret. **Must** be random & secret. |
| `QR_SECRET` | HMAC key for QR tokens & certificate signatures. |
| `DB_PASSWORD` | Postgres password (compose). |
| `TECHNOVA_DATABASE_URL` | Set automatically by compose to the Postgres DSN. |
| `TECHNOVA_ENVIRONMENT` | `production` disables dev conveniences. |

Generate secrets: `openssl rand -hex 32`.

## Production with Docker

```bash
cp .env.example .env                # fill in real secrets
cd frontend && npm ci && npm run build
cp -r dist ../backend/frontend_dist # bake the SPA into the API image build context
cd ..
docker compose up --build -d
```

Services:
- **db** — Postgres 16 with a persistent named volume `pgdata`.
- **api** — gunicorn + 4 uvicorn workers; serves both `/api/*` and the SPA (single origin).
- **backup** — runs `pg_dump` nightly into `./backups`, pruning dumps older than 7 days.

### First run
The API auto-creates tables on startup. To seed an initial dataset (optional, for a demo):
```bash
docker compose exec api python -m app.seed
```
Otherwise the **first user to register becomes SUPER_ADMIN**, then invites/promotes others.

## Migrations
Schema is created via SQLAlchemy `create_all`. For evolving a live Postgres DB in production,
add **Alembic** (`alembic init`, autogenerate revisions). The models are Alembic-ready.

## Reverse proxy / TLS
Put nginx or Caddy in front of the API for TLS termination and gzip. Example Caddy:
```
technova.school.edu {
    reverse_proxy localhost:8000
}
```

## Backups & restore
- Automated: the `backup` service writes `./backups/technova-YYYYmmdd-HHMMSS.sql` nightly.
- Manual backup: `docker compose exec db pg_dump -U technova technova > backup.sql`
- Restore: `cat backup.sql | docker compose exec -T db psql -U technova technova`

## Logging & monitoring
- Structured logs to stdout (captured by Docker / your platform).
- Health check: `GET /api/health` → use for uptime monitors & load-balancer probes.
- Add Sentry (backend) and a uptime monitor hitting `/api/health` for production.

## Update strategy
1. `git pull` → rebuild frontend → `docker compose up --build -d`.
2. Zero-ish downtime: run behind the reverse proxy; gunicorn reloads workers.
3. Run DB migrations (Alembic) before switching traffic if the schema changed.
