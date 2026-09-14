"""TECHNOVA OS — FastAPI application entrypoint."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import get_settings
from .database import Base, engine
from . import models  # noqa: F401  (register models)
from .routers import auth, profile, academy, challenges, projects, events, competitions, general, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("technova")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Seed demo data + login accounts on first boot (idempotent: no-op if already seeded).
    # Lets a fresh production database (e.g. Render Postgres) come up ready to use.
    try:
        from .seed import seed
        seed()
    except Exception as exc:  # pragma: no cover - never block startup on seed issues
        logger.warning("Seed skipped: %s", exc)
    logger.info("TECHNOVA OS started in %s mode", settings.environment)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0",
              description="The digital operating system of a technology club.",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Reflect any origin AND allow credentials (cookies). allow_origins=["*"] is invalid with
    # credentials, so we use a regex to echo the caller's origin. Same-origin (prod) needs no CORS;
    # this keeps cross-origin dev/preview working with the auth cookie.
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, profile, academy, challenges, projects, events, competitions, general, admin):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@app.get("/api/meta")
def meta():
    """Public metadata for the landing/command center."""
    return {
        "app": settings.app_name,
        "flow": ["Discover", "Learn", "Practice", "Collaborate", "Build",
                 "Compete", "Showcase", "Earn", "Lead"],
    }


# ---- Serve built frontend (production). In dev, Vite serves it separately.
# Prefer the persistent copy under backend/frontend_dist (it survives snapshots;
# the sibling frontend/dist is excluded from snapshots and can disappear on reset).
_candidates = [
    os.path.join(os.path.dirname(__file__), "..", "frontend_dist"),
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"),
]
_frontend_dist = next((p for p in _candidates if os.path.isdir(p)), _candidates[0])
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        index = os.path.join(_frontend_dist, "index.html")
        return FileResponse(index)
