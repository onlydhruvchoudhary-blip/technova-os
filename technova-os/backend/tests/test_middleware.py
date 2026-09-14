"""Observability + security-header middleware."""
import pytest
from app.seed import seed
from tests.conftest import auth_header


@pytest.fixture(scope="module", autouse=True)
def _seed():
    seed(reset=True)
    yield


def test_request_id_and_timing_headers(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")
    assert r.headers.get("X-Response-Time-ms")


def test_request_id_is_echoed_when_supplied(client):
    r = client.get("/api/health", headers={"X-Request-ID": "trace-123"})
    assert r.headers.get("X-Request-ID") == "trace-123"


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in r.headers


def test_content_security_policy_present(client):
    r = client.get("/api/health")
    csp = r.headers.get("Content-Security-Policy")
    assert csp and "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    # frame-ancestors is intentionally NOT set here (handled by env-gated X-Frame-Options)
    assert "frame-ancestors" not in csp


def test_unhandled_error_returns_clean_json(client):
    # Hitting an authed endpoint with a totally invalid token surfaces a handled 401, not a 500.
    r = client.get("/api/me/profile", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert "detail" in r.json()


def test_sse_stream_requires_valid_token(client):
    # missing token -> 422 (query param required); bad token -> 401
    assert client.get("/api/notifications/stream").status_code == 422
    r = client.get("/api/notifications/stream?token=not-valid")
    assert r.status_code == 401
