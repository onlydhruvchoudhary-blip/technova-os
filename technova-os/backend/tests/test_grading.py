"""Automated grading + peer-review: auto analysis, review rules, finalisation, points."""
from app import engine
from app.database import SessionLocal
from app.judge import analyze_code
from app.models import User
from tests.conftest import auth_header, register


def test_analyze_code_flags_and_scores():
    clean = analyze_code("def add(a, b):\n    \"\"\"Add.\"\"\"\n    return a + b\n")
    assert clean["score"] >= 90
    bad = analyze_code("import os\nx=1")  # blocked token 'os' + no docstring
    assert bad["score"] < clean["score"]
    assert any(i["level"] == "error" for i in bad["issues"])
    empty = analyze_code("   \n  ")
    assert empty["score"] == 0


def test_submit_runs_auto_analysis(client):
    register(client, "grad_author@technova.club")
    hdr = auth_header(client, "grad_author@technova.club")
    r = client.post("/api/grading/submissions", json={
        "title": "My sorter", "language": "python",
        "code": "def sort_it(xs):\n    return sorted(xs)\n", "description": "sorts",
    }, headers=hdr)
    assert r.status_code == 201, r.text
    body = r.json()
    assert 0 <= body["auto_score"] <= 100
    assert body["status"] == "open"


def test_cannot_review_own_submission(client):
    register(client, "grad_self@technova.club")
    hdr = auth_header(client, "grad_self@technova.club")
    sid = client.post("/api/grading/submissions", json={
        "title": "Mine", "code": "def f():\n    return 1\n",
    }, headers=hdr).json()["id"]
    r = client.post(f"/api/grading/submissions/{sid}/review", json={
        "correctness": 5, "readability": 5, "efficiency": 5, "comment": "great",
    }, headers=hdr)
    assert r.status_code == 403


def test_peer_reviews_finalise_and_award_points(client):
    register(client, "grad_a@technova.club")
    register(client, "grad_r1@technova.club")
    register(client, "grad_r2@technova.club")
    a = auth_header(client, "grad_a@technova.club")
    r1 = auth_header(client, "grad_r1@technova.club")
    r2 = auth_header(client, "grad_r2@technova.club")

    sid = client.post("/api/grading/submissions", json={
        "title": "Review me", "code": "def f(x):\n    return x * 2\n",
    }, headers=a).json()["id"]

    # author balance before
    db = SessionLocal()
    try:
        aid = db.query(User).filter_by(email="grad_a@technova.club").first().id
        before = engine.lifetime_points(db, aid)
    finally:
        db.close()

    # first review: still open (goal is 2)
    resp1 = client.post(f"/api/grading/submissions/{sid}/review", json={
        "correctness": 4, "readability": 4, "efficiency": 4, "comment": "solid"}, headers=r1)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "open"

    # second review: finalises
    resp2 = client.post(f"/api/grading/submissions/{sid}/review", json={
        "correctness": 5, "readability": 5, "efficiency": 5, "comment": "excellent"}, headers=r2)
    assert resp2.status_code == 200
    graded = resp2.json()
    assert graded["status"] == "graded"
    assert graded["final_score"] > 0

    # author earned points on finalisation
    db = SessionLocal()
    try:
        after = engine.lifetime_points(db, aid)
    finally:
        db.close()
    assert after > before


def test_duplicate_review_blocked(client):
    register(client, "grad_a2@technova.club")
    register(client, "grad_dup@technova.club")
    a = auth_header(client, "grad_a2@technova.club")
    rv = auth_header(client, "grad_dup@technova.club")
    sid = client.post("/api/grading/submissions", json={
        "title": "Dup", "code": "def f():\n    return 0\n", "description": "",
    }, headers=a).json()["id"]
    first = client.post(f"/api/grading/submissions/{sid}/review", json={
        "correctness": 3, "readability": 3, "efficiency": 3}, headers=rv)
    assert first.status_code == 200
    dup = client.post(f"/api/grading/submissions/{sid}/review", json={
        "correctness": 1, "readability": 1, "efficiency": 1}, headers=rv)
    assert dup.status_code == 409
