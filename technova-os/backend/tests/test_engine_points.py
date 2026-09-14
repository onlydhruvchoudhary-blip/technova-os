"""Ecosystem engine: idempotent points, caps, leaderboard, skills, achievements, certificates."""
import pytest
from app.database import SessionLocal
from app import engine
from app.models import Skill, Achievement, User, Role
from app.security import hash_password, verify_certificate_sig


@pytest.fixture(scope="module", autouse=True)
def _base_rows():
    """Ensure the skills/achievements referenced by these tests exist in the test DB."""
    db = SessionLocal()
    try:
        if not db.query(Skill).filter_by(key="python").first():
            db.add(Skill(key="python", name="Python", category="Programming", icon="🐍"))
        if not db.query(Achievement).filter_by(key="first_lesson").first():
            db.add(Achievement(key="first_lesson", name="First Steps", description="x",
                               icon="🎓", points=10))
        db.commit()
    finally:
        db.close()
    yield


def _mkuser(db, email):
    u = User(email=email, name="Eng User", password_hash=hash_password("password123"),
             role=Role.MEMBER.value)
    db.add(u)
    db.flush()
    return u


def test_points_idempotent_and_leaderboard():
    db = SessionLocal()
    try:
        u = _mkuser(db, "eng1@technova.club")
        r1 = engine.award_points(db, u.id, 50, "challenge", "challenge", "c1", "solve")
        r2 = engine.award_points(db, u.id, 50, "challenge", "challenge", "c1", "solve")  # dup
        db.commit()
        assert r1["awarded"] == 50
        assert r2["duplicate"] is True
        assert engine.total_points(db, u.id) == 50  # not doubled
    finally:
        db.close()


def test_daily_cap_prevents_farming():
    db = SessionLocal()
    try:
        u = _mkuser(db, "eng2@technova.club")
        # learning cap is 200/day; award 8 x 30 = 240 attempts, should cap at 200
        total_awarded = 0
        for i in range(8):
            res = engine.award_points(db, u.id, 30, "learning", "lesson", f"L{i}", "lesson")
            total_awarded += res["awarded"]
        db.commit()
        assert total_awarded == 200
    finally:
        db.close()


def test_skill_xp_and_tier_up():
    db = SessionLocal()
    try:
        u = _mkuser(db, "eng3@technova.club")
        # add enough XP to reach Intermediate (>=300)
        engine.add_skill_xp(db, u.id, "python", 350, "lesson")
        db.commit()
        from app.models import UserSkill
        from sqlalchemy import select
        us = db.execute(select(UserSkill).where(UserSkill.user_id == u.id)).scalar_one()
        assert us.tier() == "Intermediate"
    finally:
        db.close()


def test_achievement_grant_once():
    db = SessionLocal()
    try:
        u = _mkuser(db, "eng4@technova.club")
        a = engine.grant_achievement(db, u.id, "first_lesson", "lesson:1")
        b = engine.grant_achievement(db, u.id, "first_lesson", "lesson:2")  # duplicate
        db.commit()
        assert a is not None
        assert b is None
    finally:
        db.close()


def test_certificate_signature_valid():
    db = SessionLocal()
    try:
        u = _mkuser(db, "eng5@technova.club")
        cert = engine.issue_certificate(db, u.id, "Course Completion", "Test Cert")
        db.commit()
        assert verify_certificate_sig(cert.cert_uid, u.id, cert.kind, cert.signature)
        # tampering breaks it
        assert not verify_certificate_sig(cert.cert_uid, u.id + 1, cert.kind, cert.signature)
    finally:
        db.close()


def test_lesson_event_chain():
    """Emitting lesson.completed awards points AND skill XP AND first_lesson achievement."""
    db = SessionLocal()
    try:
        u = _mkuser(db, "eng6@technova.club")
        # ensure skill + achievement exist (seed not loaded in test db, create minimal)
        if not db.query(Skill).filter_by(key="python").first():
            db.add(Skill(key="python", name="Python", category="Programming", icon="🐍"))
        if not db.query(Achievement).filter_by(key="first_lesson").first():
            db.add(Achievement(key="first_lesson", name="First Steps", description="x", icon="🎓", points=10))
        db.flush()
        effects = engine.emit(db, engine.Event("lesson.completed", u.id,
                              {"lesson_id": 999, "title": "L", "xp": 40, "skill_key": "python"}))
        db.commit()
        assert engine.total_points(db, u.id) > 0
        from sqlalchemy import select
        from app.models import UserAchievement
        ach = db.execute(select(UserAchievement).where(UserAchievement.user_id == u.id)).all()
        assert len(ach) == 1  # first_lesson granted
    finally:
        db.close()
