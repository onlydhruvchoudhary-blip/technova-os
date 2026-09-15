import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# fresh temp DB per test session
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["TECHNOVA_DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["TECHNOVA_SECRET_KEY"] = "test-secret-key-abcdefghijklmnop"
os.environ["TECHNOVA_QR_SECRET"] = "test-qr-secret-abcdef"

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    try:
        os.close(_db_fd)
        os.unlink(_db_path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear in-memory rate-limit / throttle state so tests don't trip 429s on each other."""
    from app.routers import auth as auth_router
    from app.routers import challenges as ch_router
    auth_router._hits.clear()
    ch_router._subs.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def register(client, email, name="Test User", password="password123"):
    r = client.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    return r


def auth_header(client, email, password="password123"):
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
