"""End-to-end user journey proving the ECOSYSTEM is connected:
Register -> Login -> Learn (course->skill) -> Solve challenge (points) -> Attendance ->
Project -> Review -> Competition -> Certificate -> Leaderboard.

Runs against a freshly-seeded copy of the app DB.
"""
import pytest
from app.seed import seed
from tests.conftest import register, auth_header


@pytest.fixture(scope="module", autouse=True)
def _seed():
    seed(reset=True)  # populate skills, courses, challenges, achievements, demo users
    yield


def test_full_ecosystem_journey(client):
    # -- Discover / Register a brand new student
    r = register(client, "journey@technova.club", "Journey Student")
    assert r.status_code == 201
    h = auth_header(client, "journey@technova.club")

    # baseline profile
    prof = client.get("/api/me/profile", headers=h).json()
    assert prof["points"] == 0
    assert prof["stats"]["challenges_solved"] == 0

    # -- LEARN: complete the first Python lesson -> earns points + python skill XP
    course = client.get("/api/academy/courses/python-foundations", headers=h).json()
    first_lesson_id = course["lessons"][0]["id"]
    res = client.post(f"/api/academy/lessons/{first_lesson_id}/complete", headers=h,
                      json={}).json()
    assert res["passed"] is True

    prof = client.get("/api/me/profile", headers=h).json()
    assert prof["points"] > 0
    assert any(s["key"] == "python" for s in prof["skills"])  # skill created from learning
    assert any(a["key"] == "first_lesson" for a in prof["achievements"])  # achievement fired

    # -- Progression gate: lesson 3 is locked until lesson 2 done
    locked_lesson_id = course["lessons"][2]["id"]
    r = client.get(f"/api/academy/lessons/{locked_lesson_id}", headers=h)
    assert r.status_code == 403  # gated

    # -- PRACTICE: solve a coding challenge -> real judged points + skill XP + achievement
    ch = client.get("/api/challenges/sum-two", headers=h).json()
    submit = client.post("/api/challenges/sum-two/submit", headers=h,
                         json={"code": "def add(a, b):\n    return a + b\n"}).json()
    assert submit["passed"] is True

    prof2 = client.get("/api/me/profile", headers=h).json()
    assert prof2["stats"]["challenges_solved"] == 1
    assert prof2["points"] > prof["points"]  # challenge points added
    assert any(a["key"] == "first_challenge" for a in prof2["achievements"])

    # wrong submission does not double count / grant points
    bad = client.post("/api/challenges/sum-two/submit", headers=h,
                      json={"code": "def add(a, b):\n    return a - b\n"}).json()
    assert bad["passed"] is False
    prof3 = client.get("/api/me/profile", headers=h).json()
    assert prof3["points"] == prof2["points"]  # no change

    # resubmitting the SAME solved challenge does not double points (idempotent ledger)
    client.post("/api/challenges/sum-two/submit", headers=h,
                json={"code": "def add(a, b):\n    return a + b\n"})
    prof4 = client.get("/api/me/profile", headers=h).json()
    assert prof4["points"] == prof2["points"]

    # -- COMPETE (attendance flow with signed QR) : club head opens attendance
    h_admin = auth_header(client, "admin@technova.club")
    events = client.get("/api/events", headers=h_admin).json()
    workshop = next(e for e in events if e["kind"] == "Workshop")
    eid = workshop["id"]
    client.post(f"/api/events/{eid}/attendance/open?open=true", headers=h_admin)
    qr = client.get(f"/api/events/{eid}/qr", headers=h_admin).json()
    # student scans a bad token -> rejected
    bad_att = client.post(f"/api/events/{eid}/attendance", headers=h, json={"token": "bogus.0.deadbeef"})
    assert bad_att.status_code == 400
    # student scans the valid token -> present + points
    ok_att = client.post(f"/api/events/{eid}/attendance", headers=h, json={"token": qr["token"]})
    assert ok_att.status_code == 200
    # cannot mark twice
    dup_att = client.post(f"/api/events/{eid}/attendance", headers=h, json={"token": qr["token"]})
    assert dup_att.status_code == 409

    # -- BUILD: create a project, it appears on the portfolio
    proj = client.post("/api/projects", headers=h, json={
        "title": "Journey Bot", "problem": "p", "solution": "s",
        "required_skills": ["python"], "team_size": 3, "tech": ["Python"]}).json()
    slug = proj["slug"]

    # mentor reviews the project -> feedback becomes history + notifies members
    h_mentor = auth_header(client, "mentor@technova.club")
    rev = client.post(f"/api/projects/{slug}/reviews", headers=h_mentor,
                      json={"stage": "PLANNING", "score": 8, "feedback": "Good direction, add tests."})
    assert rev.status_code == 201

    # owner completes the project -> points + achievement + certificate for members
    client.post(f"/api/projects/{slug}/state?state=COMPLETED", headers=h)
    prof5 = client.get("/api/me/profile", headers=h).json()
    assert any(a["key"] == "project_complete" for a in prof5["achievements"])

    # certificate exists and is publicly verifiable
    certs = client.get("/api/certificates/me", headers=h).json()
    assert len(certs) >= 1
    cert_uid = certs[0]["cert_uid"]
    verify = client.get(f"/api/verify/{cert_uid}").json()  # no auth -> public
    assert verify["valid"] is True
    assert verify["recipient"] == "Journey Student"

    # -- LEAD: leaderboard reflects contributions with category breakdown
    lb = client.get("/api/leaderboard", headers=h).json()
    assert lb["me"]["rank"] is not None
    assert lb["me"]["breakdown"]  # points across categories
    assert "challenge" in lb["me"]["breakdown"]

    # notifications were generated across the journey
    notes = client.get("/api/notifications", headers=h).json()
    assert notes["unread"] >= 1


def test_certificate_verification_rejects_fake(client):
    v = client.get("/api/verify/TN-FAKE000").json()
    assert v["valid"] is False


def test_team_matching_is_explainable(client):
    h = auth_header(client, "admin@technova.club")
    projects = client.get("/api/projects", headers=h).json()
    slug = projects[0]["slug"]
    matches = client.get(f"/api/projects/{slug}/matches", headers=h).json()
    assert "candidates" in matches
    # every candidate must carry a human-readable reason (explainable matching)
    for c in matches["candidates"]:
        assert c["reasons"]
