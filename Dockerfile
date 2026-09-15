# TECHNOVA OS — all-in-one production image.
# Builds the React frontend, then runs the FastAPI backend which also serves the SPA.
# One container, one public port (8000). Ideal for Render / Railway / Fly / any Docker host.

# ---------- Stage 1: build the frontend ----------
FROM node:20-slim AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # -> /web/dist

# ---------- Stage 2: backend + built SPA ----------
FROM python:3.13-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# system deps for psycopg2 + pillow (qrcode)
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc libpq-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Alembic migrations + config (schema is migration-managed).
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
# Bake the freshly built SPA into the location the API serves from.
COPY --from=frontend /web/dist ./frontend_dist

EXPOSE 8000
# Render/most hosts inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:${PORT:-8000} --access-logfile - --error-logfile -"]
