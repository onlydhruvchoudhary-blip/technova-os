"""The TECHNOVA Ecosystem Engine.

Every meaningful action emits a domain event. Reactors subscribe and update the connected systems:
points ledger, skill XP, achievements, certificates, notifications. This is what makes TECHNOVA OS a
single ecosystem instead of 20 disconnected apps.

Key guarantees:
- Points are append-only and idempotent (dedupe_key). Re-emitting the same event never double-awards.
- Daily category caps prevent farming.
- Achievements/certificates always carry evidence (source_type:source_id).
"""
from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .models import (
    SKILL_TIERS,
    Achievement,
    Certificate,
    Notification,
    PointsLedgerEntry,
    Skill,
    User,
    UserAchievement,
    UserSkill,
    utcnow,  # noqa: F401  re-exported as engine.utcnow for routers
)
from .security import sign_certificate

settings = get_settings()

CATEGORY_CAPS = {
    "learning": settings.daily_cap_learning,
    "attendance": settings.daily_cap_attendance,
    "social": settings.daily_cap_social,
}


@dataclass
class Event:
    name: str
    user_id: int
    payload: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- event bus
_reactors: dict[str, list[Callable]] = {}


def on(event_name: str):
    def deco(fn):
        _reactors.setdefault(event_name, []).append(fn)
        return fn
    return deco


def emit(db: Session, event: Event) -> list[dict]:
    """Dispatch an event to all reactors. Returns a list of effect summaries (for tests/UX)."""
    effects: list[dict] = []
    for reactor in _reactors.get(event.name, []):
        result = reactor(db, event)
        if result:
            effects.extend(result if isinstance(result, list) else [result])
    return effects


# --------------------------------------------------------------------------- points
def _points_today(db: Session, user_id: int, category: str) -> int:
    start = dt.datetime.now(dt.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.execute(
        select(func.coalesce(func.sum(PointsLedgerEntry.points), 0))
        .where(PointsLedgerEntry.user_id == user_id)
        .where(PointsLedgerEntry.category == category)
        .where(PointsLedgerEntry.created_at >= start)
    ).scalar_one()
    return int(total or 0)


def award_points(db: Session, user_id: int, points: int, category: str,
                 source_type: str, source_id: str, reason: str) -> dict:
    """Idempotent, capped point award. Returns {awarded, capped, duplicate}."""
    dedupe = f"{user_id}:{source_type}:{source_id}"
    exists = db.execute(
        select(PointsLedgerEntry.id).where(PointsLedgerEntry.dedupe_key == dedupe)
    ).first()
    if exists:
        return {"awarded": 0, "duplicate": True, "capped": False}

    cap = CATEGORY_CAPS.get(category)
    capped = False
    if cap is not None:
        remaining = cap - _points_today(db, user_id, category)
        if remaining <= 0:
            # Still record a 0-point entry so it isn't retried forever? No — record with 0 points, dedup keeps it once.
            points = 0
            capped = True
        elif points > remaining:
            points = remaining
            capped = True

    entry = PointsLedgerEntry(
        user_id=user_id, points=points, category=category,
        source_type=source_type, source_id=str(source_id),
        reason=reason, dedupe_key=dedupe,
    )
    db.add(entry)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"awarded": 0, "duplicate": True, "capped": False}
    return {"awarded": points, "duplicate": False, "capped": capped}


def total_points(db: Session, user_id: int) -> int:
    return int(db.execute(
        select(func.coalesce(func.sum(PointsLedgerEntry.points), 0))
        .where(PointsLedgerEntry.user_id == user_id)
    ).scalar_one() or 0)


def leaderboard(db: Session, limit: int = 100) -> list[dict]:
    rows = db.execute(
        select(User.id, User.name, User.role, User.avatar_seed,
               func.coalesce(func.sum(PointsLedgerEntry.points), 0).label("pts"))
        .join(PointsLedgerEntry, PointsLedgerEntry.user_id == User.id, isouter=True)
        .where(User.is_active == True)  # noqa: E712
        .where(User.hidden_from_leaderboard == False)  # noqa: E712
        .group_by(User.id)
        .order_by(func.coalesce(func.sum(PointsLedgerEntry.points), 0).desc(), User.name.asc())
        .limit(limit)
    ).all()
    out = []
    for i, r in enumerate(rows, start=1):
        out.append({"rank": i, "user_id": r.id, "name": r.name, "role": r.role,
                    "avatar_seed": r.avatar_seed, "points": int(r.pts or 0)})
    return out


def user_rank(db: Session, user_id: int) -> int | None:
    board = leaderboard(db, limit=100000)
    for row in board:
        if row["user_id"] == user_id:
            return row["rank"]
    return None


# --------------------------------------------------------------------------- skills
def add_skill_xp(db: Session, user_id: int, skill_key: str, xp: int, evidence: str) -> dict | None:
    skill = db.execute(select(Skill).where(Skill.key == skill_key)).scalar_one_or_none()
    if not skill:
        return None
    us = db.execute(
        select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.skill_id == skill.id)
    ).scalar_one_or_none()
    if not us:
        us = UserSkill(user_id=user_id, skill_id=skill.id, xp=0)
        db.add(us)
        db.flush()
    before = us.tier_index()
    us.xp += xp
    if evidence == "lesson":
        us.lessons += 1
    elif evidence == "quiz":
        us.quizzes += 1
    elif evidence == "challenge":
        us.challenges += 1
    elif evidence == "project":
        us.projects += 1
    elif evidence == "taught":
        us.taught += 1
    db.flush()
    after = us.tier_index()
    result = {"skill": skill_key, "xp": xp, "tier": SKILL_TIERS[after]}
    if after > before:
        result["tier_up"] = SKILL_TIERS[after]
        notify(db, user_id, "skill",
               f"Skill up: {skill.name} → {SKILL_TIERS[after]}",
               f"You reached {SKILL_TIERS[after]} in {skill.name}.", "/skills")
        # tier-up may unlock an achievement
        emit(db, Event("skill.tier_up", user_id,
                       {"skill_key": skill_key, "tier": SKILL_TIERS[after], "tier_index": after}))
    return result


# --------------------------------------------------------------------------- notifications
def notify(db: Session, user_id: int, kind: str, title: str, body: str = "", link: str = "") -> None:
    db.add(Notification(user_id=user_id, kind=kind, title=title, body=body, link=link))
    db.flush()


# --------------------------------------------------------------------------- achievements
def grant_achievement(db: Session, user_id: int, key: str, evidence: str = "") -> dict | None:
    ach = db.execute(select(Achievement).where(Achievement.key == key)).scalar_one_or_none()
    if not ach:
        return None
    exists = db.execute(
        select(UserAchievement.id).where(
            UserAchievement.user_id == user_id, UserAchievement.achievement_id == ach.id)
    ).first()
    if exists:
        return None
    db.add(UserAchievement(user_id=user_id, achievement_id=ach.id, evidence=evidence))
    db.flush()
    if ach.points:
        award_points(db, user_id, ach.points, "social", "achievement", key,
                     f"Achievement: {ach.name}")
    notify(db, user_id, "achievement", f"Achievement unlocked: {ach.name}", ach.description, "/profile")
    return {"achievement": key, "name": ach.name}


def _count_ledger(db: Session, user_id: int, source_type: str) -> int:
    return int(db.execute(
        select(func.count(PointsLedgerEntry.id))
        .where(PointsLedgerEntry.user_id == user_id,
               PointsLedgerEntry.source_type == source_type)
    ).scalar_one() or 0)


# --------------------------------------------------------------------------- certificates
def issue_certificate(db: Session, user_id: int, kind: str, title: str,
                      context: str = "", issuer: str = "TECHNOVA") -> Certificate:
    cert_uid = "TN-" + uuid.uuid4().hex[:10].upper()
    sig = sign_certificate(cert_uid, user_id, kind)
    cert = Certificate(cert_uid=cert_uid, user_id=user_id, kind=kind, title=title,
                       context=context, issuer=issuer, signature=sig)
    db.add(cert)
    db.flush()
    notify(db, user_id, "certificate", f"Certificate issued: {title}",
           f"Verify with ID {cert_uid}", f"/verify/{cert_uid}")
    return cert


# =========================================================================== REACTORS
# These wire the whole ecosystem together.

@on("lesson.completed")
def _r_lesson(db: Session, e: Event):
    effects = []
    xp = e.payload.get("xp", 20)
    skill_key = e.payload.get("skill_key")
    lesson_id = e.payload["lesson_id"]
    r = award_points(db, e.user_id, max(5, xp // 2), "learning", "lesson", lesson_id,
                     f"Completed lesson: {e.payload.get('title', '')}")
    effects.append({"points": r})
    if skill_key:
        s = add_skill_xp(db, e.user_id, skill_key, xp, "lesson")
        if s:
            effects.append({"skill": s})
    # first lesson achievement
    if _count_ledger(db, e.user_id, "lesson") == 1:
        grant_achievement(db, e.user_id, "first_lesson", f"lesson:{lesson_id}")
    return effects


@on("quiz.passed")
def _r_quiz(db: Session, e: Event):
    effects = []
    skill_key = e.payload.get("skill_key")
    lesson_id = e.payload["lesson_id"]
    score = e.payload.get("score", 100)
    r = award_points(db, e.user_id, 15, "learning", "quiz", lesson_id,
                     f"Passed quiz ({score}%)")
    effects.append({"points": r})
    if skill_key:
        add_skill_xp(db, e.user_id, skill_key, 30, "quiz")
    return effects


@on("course.completed")
def _r_course(db: Session, e: Event):
    grant_achievement(db, e.user_id, "course_complete", f"course:{e.payload['course_id']}")
    cert = issue_certificate(db, e.user_id, "Course Completion",
                             f"Completed {e.payload.get('title', 'a course')}",
                             context=e.payload.get("title", ""))
    return [{"certificate": cert.cert_uid}]


@on("challenge.solved")
def _r_challenge(db: Session, e: Event):
    effects = []
    pts = e.payload.get("points", 50)
    cid = e.payload["challenge_id"]
    skill_key = e.payload.get("skill_key")
    # challenge points are NOT in a capped category (they require real, judged work)
    r = award_points(db, e.user_id, pts, "challenge", "challenge", cid,
                     f"Solved challenge: {e.payload.get('title', '')}")
    effects.append({"points": r})
    if skill_key:
        add_skill_xp(db, e.user_id, skill_key, pts, "challenge")
    solved = _count_ledger(db, e.user_id, "challenge")
    if solved == 1:
        grant_achievement(db, e.user_id, "first_challenge", f"challenge:{cid}")
    if solved >= 10:
        grant_achievement(db, e.user_id, "ten_challenges", f"challenge:{cid}")
    return effects


@on("attendance.marked")
def _r_attendance(db: Session, e: Event):
    eid = e.payload["event_id"]
    r = award_points(db, e.user_id, 20, "attendance", "attendance", eid,
                     f"Attended: {e.payload.get('title', 'event')}")
    return [{"points": r}]


@on("project.joined")
def _r_project_join(db: Session, e: Event):
    return [{"points": award_points(db, e.user_id, 10, "social", "project_join",
                                    e.payload["project_id"], "Joined a project")}]


@on("project.completed")
def _r_project_done(db: Session, e: Event):
    effects = []
    pid = e.payload["project_id"]
    for member_id in e.payload.get("member_ids", [e.user_id]):
        award_points(db, member_id, 150, "project", "project_complete", pid,
                     f"Completed project: {e.payload.get('title', '')}")
        grant_achievement(db, member_id, "project_complete", f"project:{pid}")
        for sk in e.payload.get("skills", []):
            add_skill_xp(db, member_id, sk, 80, "project")
        cert = issue_certificate(db, member_id, "Project Completion",
                                 f"Built {e.payload.get('title', 'a project')}",
                                 context=e.payload.get("title", ""))
        effects.append({"member": member_id, "certificate": cert.cert_uid})
    return effects


@on("mentor.review")
def _r_review(db: Session, e: Event):
    # mentors earn social points for meaningful reviews; capped so it can't be farmed
    r = award_points(db, e.user_id, 15, "social", "review", e.payload["review_id"],
                     "Reviewed a project milestone")
    for member_id in e.payload.get("member_ids", []):
        notify(db, member_id, "review", "New mentor feedback",
               e.payload.get("summary", "A mentor reviewed your project."),
               f"/projects/{e.payload.get('project_slug', '')}")
    return [{"points": r}]


@on("competition.scored")
def _r_competition(db: Session, e: Event):
    effects = []
    for placing in e.payload.get("placings", []):
        uid = placing["user_id"]
        rank = placing["rank"]
        pts = {1: 300, 2: 200, 3: 120}.get(rank, 50)
        award_points(db, uid, pts, "competition", "competition",
                     f"{e.payload['competition_id']}:{uid}",
                     f"Competition rank #{rank}")
        kind = "Competition Winner" if rank == 1 else "Competition Participation"
        issue_certificate(db, uid, kind,
                          f"{'Winner' if rank == 1 else f'Rank #{rank}'}: {e.payload.get('title', '')}",
                          context=e.payload.get("title", ""))
        if rank == 1:
            grant_achievement(db, uid, "competition_winner", f"competition:{e.payload['competition_id']}")
        effects.append({"user_id": uid, "rank": rank, "points": pts})
    return effects


@on("teaching.credit")
def _r_teaching(db: Session, e: Event):
    r = award_points(db, e.user_id, 25, "social", "teaching", e.payload["ref"],
                     "Helped/taught a fellow member")
    add_skill_xp(db, e.user_id, e.payload.get("skill_key", ""), 40, "taught")
    grant_achievement(db, e.user_id, "team_mentor", f"teaching:{e.payload['ref']}")
    return [{"points": r}]


@on("skill.tier_up")
def _r_skill_tier(db: Session, e: Event):
    # "Specialist" = reached Advanced (or higher) in ANY skill. Evidence records which skill
    # first earned it. Granted once by design (grant_achievement is idempotent).
    if e.payload.get("tier_index", 0) >= 3:  # Advanced or Mentor
        grant_achievement(db, e.user_id, "skill_advanced",
                          f"skill:{e.payload.get('skill_key')}")
    return None
