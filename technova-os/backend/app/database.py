"""Database engine + session management. SQLite (dev) / PostgreSQL (prod) parity."""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()


def normalize_db_url(url: str) -> str:
    """Normalize database URLs. Managed hosts (Render, Heroku, Railway) hand out
    "postgres://..." but SQLAlchemy + psycopg2 need "postgresql+psycopg2://...".
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


_db_url = normalize_db_url(settings.database_url)

connect_args = {}
if _db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    _db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)


# Enforce foreign keys on SQLite (off by default) — important for a real relational model.
if _db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_con, con_record):  # pragma: no cover - trivial
        cur = dbapi_con.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Real-time fan-out: drain messages that engine helpers stashed on the session, but ONLY after the
# transaction actually commits (so rolled-back writes are never broadcast). Registered once on the
# Session class — the correct pattern; per-call listeners leak and fire in a committed state.
@event.listens_for(Session, "after_commit")
def _drain_pending_publishes(session):  # pragma: no cover - exercised via integration
    pending = session.info.pop("_pending_publishes", None)
    if not pending:
        return
    from .broker import broker
    for topic, data, target in pending:
        broker.publish(topic, data, target)


@event.listens_for(Session, "after_rollback")
def _discard_pending_publishes(session):  # pragma: no cover - trivial
    session.info.pop("_pending_publishes", None)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
