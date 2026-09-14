"""Member profile = technology portfolio. Aggregates the whole ecosystem for one user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (User, UserSkill, Skill, UserAchievement, Achievement,
                      Project, ProjectMember, Certificate, Submission)
from ..schemas import UserOut
from ..security import get_current_user, get_optional_user, has_role
from ..models import Role
from .. import engine

router = APIRouter(prefix="/api", tags=["profile"])


def build_profile(db: Session, user: User, viewer: User | None) -> dict:
    # skills
    rows = db.execute(
        select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.user_id == user.id).order_by(UserSkill.xp.desc())
    ).all()
    skills = [{
        "key": s.key, "name": s.name, "icon": s.icon, "category": s.category,
        "xp": us.xp, "tier": us.tier(), "tier_index": us.tier_index(),
        "lessons": us.lessons, "challenges": us.challenges, "projects": us.projects,
    } for us, s in rows]

    # achievements
    arows = db.execute(
        select(UserAchievement, Achievement).join(Achievement, Achievement.id == UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user.id).order_by(UserAchievement.earned_at.desc())
    ).all()
    achievements = [{
        "key": a.key, "name": a.name, "description": a.description, "icon": a.icon,
        "points": a.points, "rarity": a.rarity, "earned_at": ua.earned_at,
    } for ua, a in arows]

    # projects
    prows = db.execute(
        select(Project, ProjectMember).join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id, ProjectMember.status == "member")
    ).all()
    projects = [{
        "id": p.id, "slug": p.slug, "title": p.title, "state": p.state,
        "role": pm.role, "showcase": p.showcase,
    } for p, pm in prows]

    # certificates (only owner or elevated viewers see full list)
    certs = []
    if viewer and (viewer.id == user.id or has_role(viewer, Role.MENTOR)):
        crows = db.execute(select(Certificate).where(Certificate.user_id == user.id,
                                                     Certificate.revoked == False)).scalars().all()  # noqa
        certs = [{"cert_uid": c.cert_uid, "kind": c.kind, "title": c.title,
                  "context": c.context, "issued_at": c.issued_at} for c in crows]

    challenges_solved = db.execute(
        select(Submission).where(Submission.user_id == user.id, Submission.passed == True)  # noqa
    ).scalars().all()
    solved_ids = {s.challenge_id for s in challenges_solved}

    return {
        "user": UserOut.model_validate(user).model_dump(),
        "points": engine.total_points(db, user.id),
        "rank": engine.user_rank(db, user.id),
        "skills": skills,
        "achievements": achievements,
        "projects": projects,
        "certificates": certs,
        "stats": {
            "challenges_solved": len(solved_ids),
            "projects": len(projects),
            "achievements": len(achievements),
            "skills": len(skills),
        },
    }


@router.get("/me/profile")
def my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_profile(db, user, user)


@router.get("/users/{user_id}/profile")
def user_profile(user_id: int, viewer: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u or not u.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return build_profile(db, u, viewer)


@router.get("/achievements")
def all_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full achievement catalogue with the viewer's earned/locked status."""
    earned = {
        ua.achievement_id: ua.earned_at
        for ua in db.execute(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        ).scalars()
    }
    rows = db.execute(select(Achievement).order_by(Achievement.points.asc())).scalars().all()
    items = [{
        "key": a.key, "name": a.name, "description": a.description, "icon": a.icon,
        "points": a.points, "rarity": a.rarity,
        "earned": a.id in earned, "earned_at": earned.get(a.id),
    } for a in rows]
    unlocked = sum(1 for i in items if i["earned"])
    return {
        "items": items,
        "unlocked": unlocked,
        "total": len(items),
        "points_earned": sum(i["points"] for i in items if i["earned"]),
        "points_available": sum(i["points"] for i in items),
    }
