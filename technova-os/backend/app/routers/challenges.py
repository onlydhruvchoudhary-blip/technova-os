"""Coding challenge platform + weekly challenges. Safe judging -> ecosystem points."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import engine
from ..database import get_db
from ..judge import judge
from ..models import AuditLog, Challenge, Role, Skill, Submission, User
from ..schemas import ChallengeCreate, SubmissionIn
from ..security import get_current_user, require_role

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

# per-user submission throttle (anti spam / anti brute force of hidden tests)
_subs: dict[int, deque] = defaultdict(deque)
SUB_LIMIT = 10
SUB_WINDOW = 60


def _throttle(user_id: int):
    now = time.time()
    dq = _subs[user_id]
    while dq and dq[0] < now - SUB_WINDOW:
        dq.popleft()
    if len(dq) >= SUB_LIMIT:
        raise HTTPException(status_code=429, detail="Too many submissions. Wait a moment.")
    dq.append(now)


@router.get("")
def list_challenges(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                    weekly: bool | None = None):
    q = select(Challenge).where(Challenge.published == True)  # noqa
    if weekly is not None:
        q = q.where(Challenge.is_weekly == weekly)
    challenges = db.execute(q.order_by(Challenge.is_weekly.desc(), Challenge.id.desc())).scalars().all()
    solved = {s.challenge_id for s in db.execute(
        select(Submission).where(Submission.user_id == user.id, Submission.passed == True)  # noqa
    ).scalars().all()}
    out = []
    for c in challenges:
        n_solvers = db.execute(
            select(func.count(func.distinct(Submission.user_id)))
            .where(Submission.challenge_id == c.id, Submission.passed == True)  # noqa
        ).scalar_one()
        out.append({
            "id": c.id, "slug": c.slug, "title": c.title, "difficulty": c.difficulty,
            "points": c.points, "is_weekly": c.is_weekly, "weekly_kind": c.weekly_kind,
            "solved": c.id in solved, "solvers": int(n_solvers),
        })
    return out


@router.get("/{slug}")
def get_challenge(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.execute(select(Challenge).where(Challenge.slug == slug)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Challenge not found")
    last = db.execute(
        select(Submission).where(Submission.user_id == user.id, Submission.challenge_id == c.id)
        .order_by(Submission.created_at.desc())
    ).scalars().first()
    solved = bool(db.execute(select(Submission.id).where(
        Submission.user_id == user.id, Submission.challenge_id == c.id,
        Submission.passed == True)).first())  # noqa
    return {
        "id": c.id, "slug": c.slug, "title": c.title, "statement": c.statement,
        "difficulty": c.difficulty, "points": c.points, "function_name": c.function_name,
        "starter_code": c.starter_code or f"def {c.function_name}(*args):\n    # your code\n    pass\n",
        "sample_tests": c.sample_tests,  # samples are public
        "hidden_test_count": len(c.hidden_tests),
        "last_code": last.code if last else None,
        "solved": solved,
    }


@router.post("/{slug}/submit")
def submit(slug: str, data: SubmissionIn,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _throttle(user.id)
    c = db.execute(select(Challenge).where(Challenge.slug == slug)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Challenge not found")

    result = judge(data.code, c.function_name, c.sample_tests, c.hidden_tests)
    sub = Submission(
        user_id=user.id, challenge_id=c.id, code=data.code,
        passed=result["passed"], tests_passed=result["tests_passed"],
        tests_total=result["tests_total"], feedback=result["feedback"],
    )
    db.add(sub)
    db.flush()

    effects = []
    if result["passed"]:
        skill_key = None
        if c.skill_id:
            sk = db.get(Skill, c.skill_id)
            skill_key = sk.key if sk else None
        effects = engine.emit(db, engine.Event(
            "challenge.solved", user.id,
            {"challenge_id": c.id, "title": c.title, "points": c.points, "skill_key": skill_key}))
    db.commit()
    return {
        "passed": result["passed"],
        "tests_passed": result["tests_passed"],
        "tests_total": result["tests_total"],
        "feedback": result["feedback"],
        "sample_results": result["sample_results"],  # never includes hidden tests
        "effects": effects,
    }


@router.post("", status_code=201)
def create_challenge(data: ChallengeCreate,
                     user: User = Depends(require_role(Role.COMMITTEE)),
                     db: Session = Depends(get_db)):
    if db.execute(select(Challenge.id).where(Challenge.slug == data.slug)).first():
        raise HTTPException(status_code=409, detail="Slug already exists")
    skill_id = None
    if data.skill_key:
        sk = db.execute(select(Skill).where(Skill.key == data.skill_key)).scalar_one_or_none()
        skill_id = sk.id if sk else None
    c = Challenge(
        slug=data.slug, title=data.title, statement=data.statement, difficulty=data.difficulty,
        skill_id=skill_id, points=data.points, function_name=data.function_name,
        starter_code=data.starter_code, sample_tests=data.sample_tests,
        hidden_tests=data.hidden_tests, is_weekly=data.is_weekly, weekly_kind=data.weekly_kind,
        created_by=user.id,
    )
    db.add(c)
    db.add(AuditLog(actor_id=user.id, action="challenge.create", target=f"challenge:{data.slug}"))
    db.commit()
    return {"id": c.id, "slug": c.slug}
