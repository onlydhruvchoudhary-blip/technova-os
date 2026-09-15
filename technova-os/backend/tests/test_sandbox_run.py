"""Live sandbox /run: executes sample tests only — no points, no persistence, no hidden tests."""
from app.database import SessionLocal
from app.models import Submission, User
from app.seed import seed
from tests.conftest import auth_header, register


def _setup(client, email="sandbox@t.io"):
    seed(reset=True)  # provides the 'sum-two' challenge + demo data
    register(client, email)
    return auth_header(client, email)


def test_run_passes_samples_without_persisting_or_awarding(client):
    h = _setup(client)
    prof_before = client.get("/api/me/profile", headers=h).json()

    r = client.post("/api/challenges/sum-two/run", headers=h,
                    json={"code": "def add(a, b):\n    return a + b\n"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sandbox"] is True
    assert body["passed"] is True
    assert body["sample_results"]  # visible samples are returned

    # No points awarded, no submission row, no solved-count change.
    prof_after = client.get("/api/me/profile", headers=h).json()
    assert prof_after["points"] == prof_before["points"]
    assert prof_after["stats"]["challenges_solved"] == 0

    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email="sandbox@t.io").first().id
        assert db.query(Submission).filter_by(user_id=uid).count() == 0
    finally:
        db.close()


def test_run_reports_failures_on_wrong_code(client):
    h = _setup(client, "sandbox2@t.io")
    r = client.post("/api/challenges/sum-two/run", headers=h,
                    json={"code": "def add(a, b):\n    return a - b\n"})
    assert r.status_code == 200
    assert r.json()["passed"] is False


def test_run_never_exposes_hidden_tests(client):
    h = _setup(client, "sandbox3@t.io")
    ch = client.get("/api/challenges/sum-two", headers=h).json()
    r = client.post("/api/challenges/sum-two/run", headers=h,
                    json={"code": "def add(a, b):\n    return a + b\n"}).json()
    # sandbox only ever runs the visible sample count, never the hidden set
    assert r["tests_total"] == len(ch["sample_tests"])


def test_run_requires_auth(client):
    assert client.post("/api/challenges/sum-two/run",
                       json={"code": "x"}).status_code == 401
