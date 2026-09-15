"""Extra security/anti-exploit tests: cert revocation, QR expiry, daily caps, RBAC matrix."""
import time
import pytest
from app.seed import seed
from app.security import make_qr_token, verify_qr_token
from app.config import get_settings
from tests.conftest import register, auth_header


@pytest.fixture(scope="module", autouse=True)
def _seed():
    seed(reset=True)
    yield


# ---------------------------------------------------------------- QR expiry (unit)
def test_qr_token_valid_now_and_expired_later():
    s = get_settings()
    now_w = int(time.time()) // s.qr_window_seconds
    token = make_qr_token(1, now_w)
    assert verify_qr_token(token, 1) is True
    # a token from far in the past must NOT verify
    old = make_qr_token(1, now_w - 5)
    assert verify_qr_token(old, 1) is False
    # token for a different event must not verify
    assert verify_qr_token(token, 2) is False


# ---------------------------------------------------------------- certificate revocation (API)
def test_certificate_revocation_flow(client):
    # give a member a certificate via course completion
    register(client, "revtest@technova.club", "Rev Test")
    h = auth_header(client, "revtest@technova.club")
    # complete the whole AI course (2 lessons) -> course completion cert
    course = client.get("/api/academy/courses/ai-fundamentals", headers=h).json()
    for l in course["lessons"]:
        client.post(f"/api/academy/lessons/{l['id']}/complete", headers=h, json={})
    certs = client.get("/api/certificates/me", headers=h).json()
    assert len(certs) >= 1
    uid = certs[0]["cert_uid"]

    # valid before revoke
    assert client.get(f"/api/verify/{uid}").json()["valid"] is True
    # a member cannot revoke
    assert client.post(f"/api/certificates/{uid}/revoke", headers=h).status_code == 403
    # club head can revoke
    h_head = auth_header(client, "head@technova.club")
    assert client.post(f"/api/certificates/{uid}/revoke", headers=h_head).status_code == 200
    # verification now reports invalid
    v = client.get(f"/api/verify/{uid}").json()
    assert v["valid"] is False
    assert "revoked" in v["reason"].lower()


# ---------------------------------------------------------------- daily cap via API
def test_learning_cap_blocks_farming_via_api(client, monkeypatch):
    """A member cannot exceed the daily learning cap even by completing many lessons."""
    from app import engine
    register(client, "farmer@technova.club", "Farmer")
    h = auth_header(client, "farmer@technova.club")
    # complete both web + python + ai lessons; learning points are capped at 200/day
    for slug in ["python-foundations", "web-dev-starter", "ai-fundamentals"]:
        course = client.get(f"/api/academy/courses/{slug}", headers=h).json()
        for l in course["lessons"]:
            # unlock sequentially; quiz lesson needs answers
            det = client.get(f"/api/academy/lessons/{l['id']}", headers=h)
            if det.status_code != 200:
                continue
            body = {}
            dj = det.json()
            if dj.get("quiz"):
                # answer all correctly is unknown; skip quiz (not needed to test cap)
                continue
            client.post(f"/api/academy/lessons/{l['id']}/complete", headers=h, json=body)
    lb = client.get("/api/leaderboard", headers=h).json()
    learning_pts = lb["me"]["breakdown"].get("learning", 0)
    assert learning_pts <= 200  # cap enforced


# ---------------------------------------------------------------- RBAC matrix
@pytest.mark.parametrize("email,role,can_event,can_comp,can_audit", [
    ("isha@technova.club", "MEMBER", False, False, False),
    ("nisha@technova.club", "COMMITTEE", True, False, False),
    ("mentor@technova.club", "MENTOR", True, False, False),
    ("head@technova.club", "CLUB_HEAD", True, True, True),
    ("admin@technova.club", "SUPER_ADMIN", True, True, True),
])
def test_rbac_matrix(client, email, role, can_event, can_comp, can_audit):
    h = auth_header(client, email)
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role"] == role
    ev = client.post("/api/events", headers=h, json={"title": "T", "starts_at": "2030-01-01T10:00:00Z"})
    assert (ev.status_code == 201) == can_event
    cp = client.post("/api/competitions", headers=h, json={"title": "T"})
    assert (cp.status_code == 201) == can_comp
    au = client.get("/api/admin/audit", headers=h)
    assert (au.status_code == 200) == can_audit
