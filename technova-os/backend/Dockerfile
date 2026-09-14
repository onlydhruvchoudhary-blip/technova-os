# TECHNOVA OS — backend (also serves the built frontend in production)
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# system deps for psycopg2 + pillow (qrcode)
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc libpq-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Built frontend (produced by `npm run build`) is expected at ../frontend/dist and
# is copied into the image by docker-compose build context. In this Dockerfile we
# copy it if present so the API can serve the SPA.
COPY frontend_dist ./frontend/dist

EXPOSE 8000
# Gunicorn with uvicorn workers for production.
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
