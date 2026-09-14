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


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
