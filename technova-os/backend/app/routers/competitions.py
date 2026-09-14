"""Competition platform: registration, entries, rubric judging, results -> certificates + points."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (Competition, CompetitionEntry, RubricScore, User, Role, AuditLog)
from ..schemas import CompetitionCreate, EntryIn, ScoreIn
from ..security import get_current_user, require_role, has_role
from .. import engine

router = APIRouter(prefix="/api/competitions", tags=["competitions"])

DEFAULT_RUBRIC = [
    {"name": "Innovation", "max": 20}, {"name": "Technical Quality", "max": 25},
    {"name": "Usefulness", "max": 20}, {"name": "Design", "max": 15},
    {"name": "Presentation", "max": 10}, {"name": "Documentation", "max": 10},
]


@router.get("")
def list_competitions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comps = db.execute(select(Competition).order_by(Competition.id.desc())).scalars().all()
    out = []
    for c in comps:
        my_entry = db.execute(select(CompetitionEntry.id).where(
            CompetitionEntry.competition_id == c.id, CompetitionEntry.user_id == user.id)).first()
        out.append({
            "id": c.id, "title": c.title, "description": c.description, "kind": c.kind,
            "status": c.status, "entry_count": len(c.entries), "registered": bool(my_entry),
        })
    return out


@router.post("", status_code=201)
def create_competition(data: CompetitionCreate, user: User = Depends(require_role(Role.CLUB_HEAD)),
                       db: Session = Depends(get_db)):
    c = Competition(title=data.title, description=data.description, kind=data.kind,
                    rubric=data.rubric or DEFAULT_RUBRIC, created_by=user.id)
    db.add(c)
    db.add(AuditLog(actor_id=user.id, action="competition.create", target=data.title))
    db.commit()
    return {"id": c.id}


@router.get("/{comp_id}")
def get_competition(comp_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(Competition, comp_id)
    if not c:
        raise HTTPException(status_code=404, detail="Competition not found")
    is_judge = has_role(user, Role.MENTOR)
    entries = []
    for e in sorted(c.entries, key=lambda x: (x.rank or 999, -x.total_score)):
        item = {"id": e.id, "team_name": e.team_name, "title": e.title, "summary": e.summary,
                "total_score": round(e.total_score, 1), "rank": e.rank,
                "is_mine": e.user_id == user.id}
        if is_judge or c.status == "closed":
            item["scored_by_me"] = bool(db.execute(select(RubricScore.id).where(
                RubricScore.entry_id == e.id, RubricScore.judge_id == user.id)).first())
        entries.append(item)
    return {
        "id": c.id, "title": c.title, "description": c.description, "kind": c.kind,
        "status": c.status, "rubric": c.rubric, "entries": entries,
        "is_judge": is_judge, "can_manage": has_role(user, Role.CLUB_HEAD),
    }


@router.post("/{comp_id}/register", status_code=201)
def register_entry(comp_id: int, data: EntryIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    c = db.get(Competition, comp_id)
    if not c:
        raise HTTPException(status_code=404, detail="Competition not found")
    if c.status != "open":
        raise HTTPException(status_code=400, detail="Registration closed")
    exists = db.execute(select(CompetitionEntry.id).where(
        CompetitionEntry.competition_id == comp_id, CompetitionEntry.user_id == user.id)).first()
    if exists:
        raise HTTPException(status_code=409, detail="Already registered")
    e = CompetitionEntry(competition_id=comp_id, user_id=user.id, team_name=data.team_name,
                         title=data.title, summary=data.summary, project_id=data.project_id)
    db.add(e)
    db.commit()
    return {"id": e.id}


@router.post("/{comp_id}/status")
def set_status(comp_id: int, status: str, user: User = Depends(require_role(Role.CLUB_HEAD)),
               db: Session = Depends(get_db)):
    c = db.get(Competition, comp_id)
    if not c:
        raise HTTPException(status_code=404, detail="Competition not found")
    if status not in ("open", "judging", "closed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    c.status = status
    if status == "closed":
        _finalize(db, c, user)
    db.add(AuditLog(actor_id=user.id, action="competition.status",
                    target=f"competition:{comp_id}", detail=status))
    db.commit()
    return {"status": status}


@router.post("/entries/{entry_id}/score")
def score_entry(entry_id: int, data: ScoreIn, user: User = Depends(require_role(Role.MENTOR)),
                db: Session = Depends(get_db)):
    e = db.get(CompetitionEntry, entry_id)
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    c = db.get(Competition, e.competition_id)
    if c.status == "closed":
        raise HTTPException(status_code=400, detail="Competition already closed")
    # validate against rubric bounds
    rubric = {r["name"]: r["max"] for r in c.rubric}
    total = 0.0
    for name, val in data.scores.items():
        if name not in rubric:
            raise HTTPException(status_code=400, detail=f"Unknown criterion: {name}")
        if not (0 <= val <= rubric[name]):
            raise HTTPException(status_code=400, detail=f"{name} must be 0..{rubric[name]}")
        total += val
    existing = db.execute(select(RubricScore).where(
        RubricScore.entry_id == entry_id, RubricScore.judge_id == user.id)).scalar_one_or_none()
    if existing:
        existing.scores = data.scores
        existing.comment = data.comment
        existing.total = total
    else:
        db.add(RubricScore(entry_id=entry_id, judge_id=user.id, scores=data.scores,
                           comment=data.comment, total=total))
    db.flush()
    # average across judges
    all_scores = db.execute(select(RubricScore).where(RubricScore.entry_id == entry_id)).scalars().all()
    e.total_score = sum(s.total for s in all_scores) / len(all_scores)
    db.add(AuditLog(actor_id=user.id, action="competition.score", target=f"entry:{entry_id}"))
    db.commit()
    return {"total": total, "average": round(e.total_score, 1)}


def _finalize(db: Session, c: Competition, actor: User):
    ranked = sorted(c.entries, key=lambda e: e.total_score, reverse=True)
    placings = []
    for i, e in enumerate(ranked, start=1):
        e.rank = i
        placings.append({"user_id": e.user_id, "rank": i})
    if placings:
        engine.emit(db, engine.Event("competition.scored", actor.id, {
            "competition_id": c.id, "title": c.title, "placings": placings}))
