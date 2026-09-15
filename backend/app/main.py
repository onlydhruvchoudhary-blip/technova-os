"""TECHNOVA OS — FastAPI application entrypoint."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (register models)
from .config import get_settings
from .database import Base, engine
from .routers import (
    academy,
    admin,
    auth,
    challenges,
    competitions,
    events,
    general,
    governance,
    grading,
    profile,
    projects,
    store,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("technova")

settings = get_settings()


def _init_schema() -> None:
    """Bring the database schema up to date.

    Prefers Alembic migrations (production-grade, versioned). Falls back to
    create_all if Alembic isn't available. Handles the case of a pre-existing
    database created before migrations by stamping it at the base revision.
    """
    from sqlalchemy import inspect
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext

        cfg_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        if not os.path.exists(cfg_path):
            raise FileNotFoundError("alembic.ini not found")
        cfg = Config(cfg_path)
        cfg.set_main_option("script_location",
                            os.path.join(os.path.dirname(__file__), "..", "migrations"))

        insp = inspect(engine)
        tables = set(insp.get_table_names())
        # An existing DB from before migrations: has app tables but no alembic_version.
        if tables and "alembic_version" not in tables:
            with engine.connect() as conn:
                if MigrationContext.configure(conn).get_current_revision() is None:
                    command.stamp(cfg, "head")  # adopt current schema as the baseline
                    logger.info("Stamped existing database at head revision")
        command.upgrade(cfg, "head")
        logger.info("Database migrations applied")
    except Exception as exc:  # pragma: no cover - fall back so the app still boots
        logger.warning("Alembic unavailable (%s); using create_all fallback", exc)
        Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_schema()
    # Bind the running event loop to the pub/sub broker so sync write paths (in the threadpool)
    # can fan out real-time messages to SSE subscribers on the loop.
    import asyncio

    from .broker import broker
    broker.bind_loop(asyncio.get_running_loop())
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

# Observability + security hardening middleware.
from .middleware import RequestContextMiddleware, SecurityHeadersMiddleware  # noqa: E402

app.add_middleware(SecurityHeadersMiddleware, is_production=(settings.environment == "production"))
app.add_middleware(RequestContextMiddleware)

for r in (auth, profile, academy, challenges, projects, events, competitions, general, governance, store, grading, admin):
    app.include_router(r.router)


# ---- Global error boundary: unhandled exceptions return clean JSON, never a stack trace.
from fastapi import Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the full trace server-side for debugging, but never leak internals to clients.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Our team has been notified.",
                 "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Consistent, human-readable 422 envelope instead of FastAPI's raw error array.
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    msg = first.get("msg", "Invalid request")
    detail = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "errors": errors,
                 "request_id": getattr(request.state, "request_id", None)},
    )


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
