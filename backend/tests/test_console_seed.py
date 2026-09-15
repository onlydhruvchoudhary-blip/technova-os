"""Admin console seed commands (projects / competitions / events) + global error boundary."""
import pytest
from app.seed import seed
from tests.conftest import auth_header


@pytest.fixture(scope="module", autouse=True)
def _seed():
    seed(reset=True)
    yield


def _run(client, headers, command):
    r = client.post("/api/admin/console", headers=headers, json={"command": command})
    assert r.status_code == 200, r.text
    return r.json()


def test_seed_commands_are_super_admin_only(client):
    # a plain member is forbidden from the console entirely
    from tests.conftest import register
    register(client, "member-x@technova.club", "Member X")
    h_member = auth_header(client, "member-x@technova.club")
    r = client.post("/api/admin/console", headers=h_member, json={"command": "seed events"})
    assert r.status_code == 403


def test_seed_events_is_idempotent(client):
    h = auth_header(client, "admin@technova.club")
    first = _run(client, h, "seed events")
    assert first["ok"] is True
    # running again adds zero (idempotent by title)
    second = _run(client, h, "seed events")
    assert "added 0" in second["output"]


def test_seed_competitions_creates_ranked_entries(client):
    h = auth_header(client, "admin@technova.club")
    _run(client, h, "seed competitions")
    comps = client.get("/api/competitions", headers=h).json()
    titles = {c["title"] for c in comps}
    assert "Fall Hackathon 2025" in titles
    # the closed hackathon should have ranked entries
    fall = next(c for c in comps if c["title"] == "Fall Hackathon 2025")
    detail = client.get(f"/api/competitions/{fall['id']}", headers=h).json()
    ranks = [e["rank"] for e in detail["entries"] if e["rank"]]
    assert 1 in ranks  # a winner exists


def test_unknown_command_returns_error_not_500(client):
    h = auth_header(client, "admin@technova.club")
    r = _run(client, h, "definitely-not-a-command")
    assert r["ok"] is False
    assert r["output"].startswith("!")
