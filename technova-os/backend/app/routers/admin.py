"""Admin dashboard: member/role management, analytics, audit log, moderation. RBAC-gated."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (User, Role, ROLE_RANK, AuditLog, Course, LessonProgress, Lesson,
                      Project, Event, Attendance, Challenge, Submission, Certificate,
                      Competition, PointsLedgerEntry, Registration, Skill)
from ..schemas import RoleUpdate
from ..security import get_current_user, require_role, has_role
from .. import engine
import uuid
from pydantic import BaseModel


class ConsoleCmd(BaseModel):
    command: str

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/members")
def members(user: User = Depends(require_role(Role.ADVISOR)), db: Session = Depends(get_db)):
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role,
             "is_active": u.is_active, "points": engine.total_points(db, u.id),
             "created_at": u.created_at} for u in users]


@router.post("/members/{user_id}/role")
def set_role(user_id: int, data: RoleUpdate, actor: User = Depends(require_role(Role.CLUB_HEAD)),
             db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        new_role = Role(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    # cannot assign a role higher than your own, and only SUPER_ADMIN can make SUPER_ADMIN
    if ROLE_RANK[new_role] >= ROLE_RANK[Role(actor.role)] and not has_role(actor, Role.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Cannot assign a role at or above your own")
    if new_role == Role.SUPER_ADMIN and not has_role(actor, Role.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Only a Super Admin can grant Super Admin")
    old = target.role
    target.role = new_role.value
    db.add(AuditLog(actor_id=actor.id, action="member.role_change",
                    target=f"user:{user_id}", detail=f"{old} -> {new_role.value}"))
    engine.notify(db, user_id, "role", "Your role changed",
                  f"You are now {new_role.value}", "/profile")
    db.commit()
    return {"role": new_role.value}


@router.post("/members/{user_id}/deactivate")
def deactivate(user_id: int, actor: User = Depends(require_role(Role.CLUB_HEAD)),
               db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    target.is_active = False
    db.add(AuditLog(actor_id=actor.id, action="member.deactivate", target=f"user:{user_id}"))
    db.commit()
    return {"is_active": False}


@router.get("/audit")
def audit(user: User = Depends(require_role(Role.CLUB_HEAD)), db: Session = Depends(get_db)):
    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).scalars().all()
    out = []
    for a in rows:
        actor = db.get(User, a.actor_id) if a.actor_id else None
        out.append({"id": a.id, "actor": actor.name if actor else "system", "action": a.action,
                    "target": a.target, "detail": a.detail, "created_at": a.created_at})
    return out


@router.get("/analytics")
def analytics(user: User = Depends(require_role(Role.ADVISOR)), db: Session = Depends(get_db)):
    now = engine.utcnow()
    total_members = db.execute(select(func.count(User.id)).where(User.is_active == True)).scalar_one()  # noqa
    # active = earned any points in the last 30 days
    from datetime import timedelta
    since = now - timedelta(days=30)
    active = db.execute(select(func.count(func.distinct(PointsLedgerEntry.user_id)))
                        .where(PointsLedgerEntry.created_at >= since)).scalar_one()

    # attendance rate
    total_reg = db.execute(select(func.count(Registration.id))).scalar_one()
    total_att = db.execute(select(func.count(Attendance.id))).scalar_one()
    attendance_rate = round(100 * total_att / total_reg) if total_reg else 0

    projects_completed = db.execute(select(func.count(Project.id))
                                    .where(Project.state.in_(["COMPLETED", "SHOWCASE"]))).scalar_one()
    challenges_solved = db.execute(select(func.count(func.distinct(Submission.id)))
                                   .where(Submission.passed == True)).scalar_one()  # noqa

    # popular courses (by completed lessons)
    course_rows = db.execute(
        select(Course.title, func.count(LessonProgress.id).label("done"))
        .join(Lesson, Lesson.course_id == Course.id)
        .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .where(LessonProgress.completed == True)  # noqa
        .group_by(Course.id).order_by(func.count(LessonProgress.id).desc()).limit(5)
    ).all()

    # projects by tech (aggregate JSON tech arrays)
    tech_counter: dict[str, int] = {}
    for (tech,) in db.execute(select(Project.tech)).all():
        for t in (tech or []):
            tech_counter[t] = tech_counter.get(t, 0) + 1
    projects_by_tech = sorted(tech_counter.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        "club": {
            "total_members": int(total_members), "active_members": int(active),
            "attendance_rate": attendance_rate,
            "projects_completed": int(projects_completed),
            "competitions": db.execute(select(func.count(Competition.id))).scalar_one(),
            "challenges_solved": int(challenges_solved),
            "certificates_issued": db.execute(select(func.count(Certificate.id))).scalar_one(),
            "events_held": db.execute(select(func.count(Event.id))).scalar_one(),
        },
        "popular_courses": [{"title": t, "completions": int(d)} for t, d in course_rows],
        "projects_by_tech": [{"tech": t, "count": c} for t, c in projects_by_tech],
        "points_by_category": _points_by_category(db),
    }


# ============================================================ ADMIN COMMAND CONSOLE
CONSOLE_HELP = """TECHNOVA OS — Admin Command Console (Super Admin only)
Available commands:
  help                                 show this help
  whoami                               show your account summary
  grant points <email> <amount>        add leaderboard points (uncapped 'competition' ledger)
  grant xp <email> <skill> <amount>    add skill XP (skill = key, e.g. python, or 'all')
  solve <email> <count>                mark <count> distinct challenges solved
  role <email> <ROLE>                  set a member's role (MEMBER..SUPER_ADMIN)
  rename <email> <new name>            rename a member
  hide <email> / unhide <email>        toggle leaderboard visibility
  achievement <email> <key>            grant an achievement (e.g. competition_winner)
  cert <email> <kind> | <title>        issue a certificate
  reset points <email>                 wipe a member's points ledger
  stats                                club-wide counts
Use 'me' as <email> to target yourself."""


def _find_user(db: Session, actor: User, ident: str) -> User | None:
    if ident == "me":
        return actor
    return db.execute(select(User).where(User.email == ident.lower())).scalar_one_or_none()


def _run_console(db: Session, actor: User, raw: str) -> str:
    parts = raw.strip().split()
    if not parts:
        return ""
    cmd = parts[0].lower()

    if cmd == "help":
        return CONSOLE_HELP
    if cmd == "whoami":
        return (f"{actor.name} <{actor.email}> | role={actor.role} | "
                f"points={engine.total_points(db, actor.id)} | "
                f"hidden={actor.hidden_from_leaderboard}")
    if cmd == "stats":
        return (f"members={db.execute(select(func.count(User.id))).scalar_one()} "
                f"projects={db.execute(select(func.count(Project.id))).scalar_one()} "
                f"challenges={db.execute(select(func.count(Challenge.id))).scalar_one()} "
                f"events={db.execute(select(func.count(Event.id))).scalar_one()} "
                f"certs={db.execute(select(func.count(Certificate.id))).scalar_one()}")

    if cmd == "grant" and len(parts) >= 4 and parts[1] == "points":
        u = _find_user(db, actor, parts[2])
        if not u:
            return f"! no user '{parts[2]}'"
        amt = int(parts[3])
        engine.award_points(db, u.id, amt, "competition", "console_grant",
                            uuid.uuid4().hex, "Console point grant")
        db.commit()
        return f"✓ +{amt} points to {u.name}. total={engine.total_points(db, u.id)}"

    if cmd == "grant" and len(parts) >= 5 and parts[1] == "xp":
        u = _find_user(db, actor, parts[2])
        if not u:
            return f"! no user '{parts[2]}'"
        skill_arg, amt = parts[3], int(parts[4])
        keys = ([s.key for s in db.execute(select(Skill)).scalars().all()]
                if skill_arg == "all" else [skill_arg])
        applied = [k for k in keys if engine.add_skill_xp(db, u.id, k, amt, "project")]
        db.commit()
        return f"✓ +{amt} XP to {u.name} on: {', '.join(applied) or '(no valid skill)'}"

    if cmd == "solve" and len(parts) >= 3:
        u = _find_user(db, actor, parts[1])
        if not u:
            return f"! no user '{parts[1]}'"
        target = int(parts[2])
        solved = {s.challenge_id for s in db.execute(
            select(Submission).where(Submission.user_id == u.id,
                                     Submission.passed == True)).scalars().all()}  # noqa
        py = db.execute(select(Skill).where(Skill.key == "python")).scalar_one_or_none()
        # create filler challenges if needed
        have = db.execute(select(func.count(Challenge.id))).scalar_one()
        i = have
        while len(solved) < target:
            allc = db.execute(select(Challenge)).scalars().all()
            todo = [c for c in allc if c.id not in solved]
            if not todo:
                i += 1
                slug = f"console-practice-{i:04d}"
                ch = Challenge(slug=slug, title=f"Practice #{i}", statement="Return a+b.",
                               difficulty="Easy", skill_id=py.id if py else None, points=30,
                               function_name="solve", starter_code="def solve(a,b):\n    pass\n",
                               sample_tests=[{"args": [1, 2], "expected": 3}],
                               hidden_tests=[{"args": [4, 5], "expected": 9}], created_by=actor.id)
                db.add(ch)
                db.flush()
                todo = [ch]
            ch = todo[0]
            db.add(Submission(user_id=u.id, challenge_id=ch.id, code="def solve(a,b):\n    return a+b\n",
                              passed=True, tests_passed=2, tests_total=2, feedback="console grant"))
            engine.award_points(db, u.id, ch.points, "challenge", "challenge", ch.id, f"Solved: {ch.title}")
            solved.add(ch.id)
        engine.grant_achievement(db, u.id, "first_challenge", "console")
        engine.grant_achievement(db, u.id, "ten_challenges", "console")
        db.commit()
        return f"✓ {u.name} now has {len(solved)} distinct challenges solved"

    if cmd == "role" and len(parts) >= 3:
        u = _find_user(db, actor, parts[1])
        if not u:
            return f"! no user '{parts[1]}'"
        try:
            u.role = Role(parts[2].upper()).value
        except ValueError:
            return f"! invalid role '{parts[2]}'"
        db.commit()
        return f"✓ {u.name} is now {u.role}"

    if cmd == "rename" and len(parts) >= 3:
        u = _find_user(db, actor, parts[1])
        if not u:
            return f"! no user '{parts[1]}'"
        new_name = " ".join(parts[2:])
        u.name = new_name
        u.avatar_seed = new_name.lower().replace(" ", "")[:20] or "nova"
        db.commit()
        return f"✓ renamed to {new_name}"

    if cmd in ("hide", "unhide") and len(parts) >= 2:
        u = _find_user(db, actor, parts[1])
        if not u:
            return f"! no user '{parts[1]}'"
        u.hidden_from_leaderboard = (cmd == "hide")
        db.commit()
        return f"✓ {u.name} {'hidden from' if cmd == 'hide' else 'visible on'} leaderboard"

    if cmd == "achievement" and len(parts) >= 3:
        u = _find_user(db, actor, parts[1])
        if not u:
            return f"! no user '{parts[1]}'"
        r = engine.grant_achievement(db, u.id, parts[2], "console")
        db.commit()
        return f"✓ granted '{parts[2]}' to {u.name}" if r else f"! unknown/duplicate achievement '{parts[2]}'"

    if cmd == "cert" and "|" in raw:
        head, title = raw.split("|", 1)
        hp = head.split()
        u = _find_user(db, actor, hp[1]) if len(hp) >= 2 else None
        if not u:
            return "! usage: cert <email> <kind> | <title>"
        kind = " ".join(hp[2:]) or "Recognition"
        c = engine.issue_certificate(db, u.id, kind, title.strip(), context="Console")
        db.commit()
        return f"✓ issued certificate {c.cert_uid} to {u.name}"

    if cmd == "reset" and len(parts) >= 3 and parts[1] == "points":
        u = _find_user(db, actor, parts[2])
        if not u:
            return f"! no user '{parts[2]}'"
        db.query(PointsLedgerEntry).filter(PointsLedgerEntry.user_id == u.id).delete()
        db.commit()
        return f"✓ wiped points ledger for {u.name}"

    return f"! unknown command '{raw}'. Type 'help'."


@router.post("/console")
def admin_console(cmd: ConsoleCmd, actor: User = Depends(require_role(Role.SUPER_ADMIN)),
                  db: Session = Depends(get_db)):
    """God-mode command console. Super Admin only. Every command is written to the audit log."""
    try:
        output = _run_console(db, actor, cmd.command)
        ok = not output.startswith("!")
    except Exception as e:  # never leak a stack trace to the client
        output = f"! error: {str(e)[:200]}"
        ok = False
    db.add(AuditLog(actor_id=actor.id, action="admin.console",
                    target=cmd.command[:120], detail=("ok" if ok else "err")))
    db.commit()
    return {"ok": ok, "output": output}


def _points_by_category(db: Session):
    rows = db.execute(
        select(PointsLedgerEntry.category, func.sum(PointsLedgerEntry.points))
        .group_by(PointsLedgerEntry.category)
    ).all()
    return [{"category": c, "points": int(p or 0)} for c, p in rows]
