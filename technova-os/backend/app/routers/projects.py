"""Project Incubator + Workspace + Team Matching + Mentor reviews."""
from __future__ import annotations

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Project, ProjectMember, Task, Review, ProjectState, User, UserSkill,
                      Skill, Role, AuditLog)
from ..schemas import ProjectCreate, TaskCreate, TaskUpdate, ReviewIn
from ..security import get_current_user, get_optional_user, has_role, require_role
from .. import engine

router = APIRouter(prefix="/api/projects", tags=["projects"])

STATE_ORDER = [s.value for s in ProjectState]
TASK_STATES = ["Backlog", "To Do", "In Progress", "Review", "Testing", "Done"]


def _slugify(title: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "project"
    slug, i = base, 1
    while db.execute(select(Project.id).where(Project.slug == slug)).first():
        i += 1
        slug = f"{base}-{i}"
    return slug


def _is_team(db: Session, project: Project, user: User) -> bool:
    if user.id == project.owner_id or user.id == project.mentor_id:
        return True
    return bool(db.execute(select(ProjectMember.id).where(
        ProjectMember.project_id == project.id, ProjectMember.user_id == user.id,
        ProjectMember.status == "member")).first())


@router.get("")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                  state: str | None = None, mine: bool = False):
    q = select(Project)
    if state:
        q = q.where(Project.state == state)
    projects = db.execute(q.order_by(Project.created_at.desc())).scalars().all()
    out = []
    for p in projects:
        members = [pm for pm in p.members if pm.status == "member"]
        if mine and user.id not in {m.user_id for m in members} and p.owner_id != user.id:
            continue
        out.append(_project_card(db, p, user))
    return out


def _project_card(db: Session, p: Project, user: User | None) -> dict:
    members = [pm for pm in p.members if pm.status == "member"]
    return {
        "id": p.id, "slug": p.slug, "title": p.title, "problem": p.problem,
        "state": p.state, "required_skills": p.required_skills, "tech": p.tech,
        "team_size": p.team_size, "member_count": len(members), "showcase": p.showcase,
        "owner_id": p.owner_id, "mentor_id": p.mentor_id,
        "is_member": bool(user and _is_team(db, p, user)),
    }


@router.post("", status_code=201)
def create_project(data: ProjectCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    slug = _slugify(data.title, db)
    p = Project(
        slug=slug, title=data.title, problem=data.problem, solution=data.solution,
        description=data.description, required_skills=data.required_skills,
        team_size=data.team_size, tech=data.tech, owner_id=user.id,
        state=ProjectState.PROPOSED.value,
    )
    db.add(p)
    db.flush()
    db.add(ProjectMember(project_id=p.id, user_id=user.id, role="Lead", status="member"))
    db.commit()
    return {"id": p.id, "slug": p.slug}


@router.get("/{slug}")
def get_project(slug: str, viewer: User | None = Depends(get_optional_user),
                db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    is_team = bool(viewer and _is_team(db, p, viewer))
    is_public = p.showcase or p.state == ProjectState.SHOWCASE.value
    if not is_team and not is_public and not (viewer and has_role(viewer, Role.MENTOR)):
        # private draft: only card-level info
        raise HTTPException(status_code=403, detail="This project is private")

    members = []
    for pm in p.members:
        u = db.get(User, pm.user_id)
        members.append({"user_id": pm.user_id, "name": u.name if u else "?", "role": pm.role,
                        "status": pm.status, "avatar_seed": u.avatar_seed if u else "nova"})
    tasks = [{"id": t.id, "title": t.title, "description": t.description, "status": t.status,
              "assignee_id": t.assignee_id, "order": t.order} for t in p.tasks]
    reviews = [{"id": r.id, "mentor_id": r.mentor_id, "stage": r.stage, "score": r.score,
                "feedback": r.feedback, "created_at": r.created_at} for r in p.reviews]
    return {
        **_project_card(db, p, viewer),
        "solution": p.solution, "description": p.description,
        "repo_url": p.repo_url, "demo_url": p.demo_url,
        "state_order": STATE_ORDER, "task_states": TASK_STATES,
        "members": members, "tasks": tasks, "reviews": reviews,
        "can_manage": bool(viewer and (viewer.id == p.owner_id or (viewer and has_role(viewer, Role.MENTOR)))),
    }


@router.post("/{slug}/join")
def join_project(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.execute(select(ProjectMember).where(
        ProjectMember.project_id == p.id, ProjectMember.user_id == user.id)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Already requested/joined")
    db.add(ProjectMember(project_id=p.id, user_id=user.id, role="Contributor", status="requested"))
    engine.notify(db, p.owner_id, "project", "Join request",
                  f"{user.name} wants to join {p.title}", f"/projects/{p.slug}")
    db.commit()
    return {"status": "requested"}


@router.post("/{slug}/members/{user_id}/approve")
def approve_member(slug: str, user_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.id != p.owner_id and not has_role(user, Role.MENTOR):
        raise HTTPException(status_code=403, detail="Only the project lead or a mentor can approve")
    pm = db.execute(select(ProjectMember).where(
        ProjectMember.project_id == p.id, ProjectMember.user_id == user_id)).scalar_one_or_none()
    if not pm:
        raise HTTPException(status_code=404, detail="No such request")
    pm.status = "member"
    engine.emit(db, engine.Event("project.joined", user_id, {"project_id": p.id}))
    engine.notify(db, user_id, "project", "Request approved",
                  f"You joined {p.title}", f"/projects/{p.slug}")
    db.commit()
    return {"status": "member"}


@router.post("/{slug}/state")
def set_state(slug: str, state: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.id != p.owner_id and not has_role(user, Role.MENTOR):
        raise HTTPException(status_code=403, detail="Not allowed")
    if state not in STATE_ORDER:
        raise HTTPException(status_code=400, detail="Invalid state")
    p.state = state
    if state == ProjectState.SHOWCASE.value:
        p.showcase = True
    if state == ProjectState.COMPLETED.value:
        member_ids = [pm.user_id for pm in p.members if pm.status == "member"]
        engine.emit(db, engine.Event("project.completed", p.owner_id, {
            "project_id": p.id, "title": p.title, "member_ids": member_ids,
            "skills": p.required_skills}))
    db.add(AuditLog(actor_id=user.id, action="project.state", target=f"project:{p.slug}", detail=state))
    db.commit()
    return {"state": state}


# ---- tasks (project management board)
@router.post("/{slug}/tasks", status_code=201)
def create_task(slug: str, data: TaskCreate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _is_team(db, p, user):
        raise HTTPException(status_code=403, detail="Only team members can add tasks")
    if data.status not in TASK_STATES:
        raise HTTPException(status_code=400, detail="Invalid status")
    t = Task(project_id=p.id, title=data.title, description=data.description,
             status=data.status, assignee_id=data.assignee_id)
    db.add(t)
    db.commit()
    return {"id": t.id}


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, data: TaskUpdate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    p = db.get(Project, t.project_id)
    if not _is_team(db, p, user):
        raise HTTPException(status_code=403, detail="Only team members can edit tasks")
    if data.status and data.status not in TASK_STATES:
        raise HTTPException(status_code=400, detail="Invalid status")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(t, field, val)
    db.commit()
    return {"ok": True}


# ---- mentor reviews
@router.post("/{slug}/reviews", status_code=201)
def add_review(slug: str, data: ReviewIn, user: User = Depends(require_role(Role.MENTOR)),
               db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    r = Review(project_id=p.id, mentor_id=user.id, stage=data.stage, score=data.score,
               feedback=data.feedback)
    db.add(r)
    db.flush()
    member_ids = [pm.user_id for pm in p.members if pm.status == "member"]
    engine.emit(db, engine.Event("mentor.review", user.id, {
        "review_id": r.id, "project_slug": p.slug, "member_ids": member_ids,
        "summary": data.feedback[:120]}))
    db.add(AuditLog(actor_id=user.id, action="project.review", target=f"project:{p.slug}"))
    db.commit()
    return {"id": r.id}


# ---- team matching (explainable, skill-based)
@router.get("/{slug}/matches")
def team_matches(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    needed = set(p.required_skills or [])
    current_ids = {pm.user_id for pm in p.members}
    # skills already covered by current team
    covered = set()
    for pm in p.members:
        for us in db.execute(select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id)
                             .where(UserSkill.user_id == pm.user_id)).all():
            _, sk = us
            covered.add(sk.key)
    gaps = needed - covered

    candidates = []
    users = db.execute(select(User).where(User.is_active == True)).scalars().all()  # noqa
    for u in users:
        if u.id in current_ids:
            continue
        user_skills = {}
        for us, sk in db.execute(select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id)
                                 .where(UserSkill.user_id == u.id)).all():
            user_skills[sk.key] = us.tier()
        matched = needed & set(user_skills.keys())
        fills_gap = gaps & set(user_skills.keys())
        if not matched:
            continue
        score = len(fills_gap) * 3 + len(matched)
        reasons = []
        if fills_gap:
            reasons.append("Fills team gap: " + ", ".join(sorted(fills_gap)))
        if matched - fills_gap:
            reasons.append("Also strong in: " + ", ".join(sorted(matched - fills_gap)))
        candidates.append({
            "user_id": u.id, "name": u.name, "avatar_seed": u.avatar_seed,
            "score": score, "skills": {k: user_skills[k] for k in matched},
            "reasons": reasons,
        })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return {"needed_skills": sorted(needed), "gaps": sorted(gaps), "candidates": candidates[:10]}


# ---- public showcase
@router.get("/showcase/public")
def public_showcase(db: Session = Depends(get_db)):
    projects = db.execute(select(Project).where(Project.showcase == True)  # noqa
                          .order_by(Project.created_at.desc())).scalars().all()
    out = []
    for p in projects:
        members = [pm for pm in p.members if pm.status == "member"]
        out.append({
            "slug": p.slug, "title": p.title, "problem": p.problem, "solution": p.solution,
            "description": p.description, "tech": p.tech, "repo_url": p.repo_url,
            "demo_url": p.demo_url, "member_count": len(members), "state": p.state,
        })
    return out
