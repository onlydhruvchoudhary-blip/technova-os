"""Governance: membership tiers, officer/mentor eligibility, and points-weighted voting.

Endpoints
- GET  /api/governance/standing            -> the current user's tier, voting power, eligibility
- GET  /api/governance/tiers               -> the tier ladder + rules (public reference)
- GET  /api/governance/proposals           -> list proposals (with live tallies)
- POST /api/governance/proposals           -> create a proposal (committee+; funding needs club head)
- GET  /api/governance/proposals/{id}      -> one proposal + full tally + your vote
- POST /api/governance/proposals/{id}/vote -> cast a weighted vote (once, while open)
- POST /api/governance/proposals/{id}/close-> close voting + record outcome (committee+)
- POST /api/governance/eligibility/claim   -> notify admins you qualify for a promotion
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import engine, governance
from ..database import get_db
from ..models import ROLE_RANK, AuditLog, Project, Proposal, Role, User, Vote, utcnow
from ..schemas import ProposalCreate, VoteIn
from ..security import get_current_user, require_role

router = APIRouter(prefix="/api/governance", tags=["governance"])


def _is_past(when: dt.datetime | None) -> bool:
    """Has `when` passed? Robust to naive datetimes (SQLite returns tz-naive values)."""
    if when is None:
        return False
    now = utcnow()
    if when.tzinfo is None:
        # Treat stored naive timestamps as UTC to match utcnow().
        when = when.replace(tzinfo=dt.UTC)
    return now > when


def _tally(db: Session, proposal: Proposal) -> dict:
    """Aggregate votes by choice: both raw headcount and total weight."""
    votes = db.execute(select(Vote).where(Vote.proposal_id == proposal.id)).scalars().all()
    by_choice: dict[str, dict] = {opt: {"count": 0, "weight": 0} for opt in (proposal.options or [])}
    for v in votes:
        slot = by_choice.setdefault(v.choice, {"count": 0, "weight": 0})
        slot["count"] += 1
        slot["weight"] += v.weight
    total_weight = sum(s["weight"] for s in by_choice.values())
    # Leading option by weight (ignoring "Abstain").
    ranked = sorted(
        ((k, s) for k, s in by_choice.items() if k.lower() != "abstain"),
        key=lambda kv: kv[1]["weight"], reverse=True,
    )
    leader = ranked[0][0] if ranked and ranked[0][1]["weight"] > 0 else None
    return {
        "by_choice": by_choice,
        "total_votes": len(votes),
        "total_weight": total_weight,
        "leader": leader,
    }


def _serialize(db: Session, p: Proposal, user: User | None = None) -> dict:
    proj = db.get(Project, p.project_id) if p.project_id else None
    data = {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "kind": p.kind,
        "amount": p.amount,
        "project": {"id": proj.id, "slug": proj.slug, "title": proj.title} if proj else None,
        "options": p.options or [],
        "status": p.status,
        "min_tier": p.min_tier,
        "outcome": p.outcome,
        "closes_at": p.closes_at.isoformat() if p.closes_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "tally": _tally(db, p),
    }
    if user is not None:
        mine = db.execute(select(Vote).where(
            Vote.proposal_id == p.id, Vote.user_id == user.id)).scalar_one_or_none()
        data["my_vote"] = mine.choice if mine else None
    return data


@router.get("/tiers")
def get_tiers():
    """Public reference: the tier ladder and the governance rules."""
    return {
        "tiers": governance.TIERS,
        "min_voting_tier": governance.TIERS[governance.MIN_VOTING_TIER],
        "eligibility": governance.ELIGIBILITY,
    }


@router.get("/standing")
def my_standing(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return governance.standing(db, user)


@router.get("/proposals")
def list_proposals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(Proposal).order_by(
        Proposal.status.desc(), Proposal.created_at.desc())).scalars().all()
    return [_serialize(db, p, user) for p in rows]


@router.get("/proposals/{pid}")
def get_proposal(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Proposal, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _serialize(db, p, user)


@router.post("/proposals")
def create_proposal(data: ProposalCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_role(Role.COMMITTEE))):
    kind = data.kind if data.kind in ("decision", "funding") else "decision"
    # Funding proposals move real money/resources -> require Club Head or higher to raise.
    if kind == "funding" and ROLE_RANK.get(Role(actor.role), 0) < ROLE_RANK[Role.CLUB_HEAD]:
        raise HTTPException(status_code=403, detail="Only a Club Head can raise a funding proposal")
    if data.project_id and not db.get(Project, data.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    options = [o.strip() for o in (data.options or []) if o.strip()]
    if len(options) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two options")

    p = Proposal(
        title=data.title.strip(),
        description=data.description.strip(),
        kind=kind,
        amount=data.amount if kind == "funding" else 0,
        project_id=data.project_id,
        options=options,
        min_tier=governance.MIN_VOTING_TIER,
        created_by=actor.id,
        closes_at=utcnow() + dt.timedelta(days=data.closes_in_days),
    )
    db.add(p)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="governance.proposal_create",
                    target=f"proposal:{p.id}", detail=f"{kind}: {p.title}"))
    # Let voting-eligible members know a vote is open.
    for u in db.execute(select(User).where(User.is_active.is_(True))).scalars().all():
        if governance.tier_for_points(engine.lifetime_points(db, u.id))["index"] >= governance.MIN_VOTING_TIER:
            engine.notify(db, u.id, "governance",
                          "New vote open", p.title, link="/governance")
    db.commit()
    return _serialize(db, p, actor)


@router.post("/proposals/{pid}/vote")
def cast_vote(pid: int, data: VoteIn, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    p = db.get(Proposal, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if p.status != "open":
        raise HTTPException(status_code=400, detail="This proposal is closed")
    if _is_past(p.closes_at):
        raise HTTPException(status_code=400, detail="Voting has ended for this proposal")
    if data.choice not in (p.options or []):
        raise HTTPException(status_code=400, detail="Invalid choice")

    # Eligibility + weight are computed from the live points ledger.
    points = engine.lifetime_points(db, user.id)
    tier = governance.tier_for_points(points)
    if tier["index"] < p.min_tier:
        needed = governance.TIERS[p.min_tier]
        raise HTTPException(
            status_code=403,
            detail=f"You must reach {needed['name']} ({needed['min_points']}+ pts) to vote. "
                   f"You're {needed['min_points'] - points} points away.")

    existing = db.execute(select(Vote).where(
        Vote.proposal_id == p.id, Vote.user_id == user.id)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="You have already voted on this proposal")

    weight = governance.vote_weight(points)
    db.add(Vote(proposal_id=p.id, user_id=user.id, choice=data.choice,
                weight=weight, points_at_vote=points))
    db.add(AuditLog(actor_id=user.id, action="governance.vote",
                    target=f"proposal:{p.id}", detail=f"{data.choice} (w{weight})"))
    engine._safe_activity(db, kind="vote", actor_id=user.id, icon="🗳️",
                          text=f"voted on “{p.title}”", link="/governance")
    db.commit()
    return {"ok": True, "weight": weight, "tally": _tally(db, p)}


@router.post("/proposals/{pid}/close")
def close_proposal(pid: int, db: Session = Depends(get_db),
                   actor: User = Depends(require_role(Role.COMMITTEE))):
    p = db.get(Proposal, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if p.status == "closed":
        raise HTTPException(status_code=400, detail="Already closed")
    p.status = "closed"
    tally = _tally(db, p)
    p.outcome = (f"{tally['leader']} wins ({tally['by_choice'].get(tally['leader'], {}).get('weight', 0)} "
                 f"of {tally['total_weight']} weighted votes)") if tally["leader"] else "No decision (no votes)"
    db.add(AuditLog(actor_id=actor.id, action="governance.proposal_close",
                    target=f"proposal:{p.id}", detail=p.outcome))
    db.commit()
    return _serialize(db, p, actor)


@router.post("/eligibility/claim")
def claim_eligibility(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Members who cross a threshold can flag themselves to admins for promotion review."""
    points = engine.lifetime_points(db, user.id)
    quals = [e for e in governance.eligibility_for(points, user.role)
             if e["qualified"] and not e["already_held"]]
    if not quals:
        raise HTTPException(status_code=400, detail="You don't currently qualify for a new role")
    labels = ", ".join(q["label"] for q in quals)
    # Notify every club-head+ admin.
    admins = db.execute(select(User).where(
        User.role.in_([Role.CLUB_HEAD.value, Role.SUPER_ADMIN.value]))).scalars().all()
    for a in admins:
        engine.notify(db, a.id, "governance",
                      "Promotion request",
                      f"{user.name} qualifies for: {labels} ({points} pts)",
                      link="/admin")
    db.add(AuditLog(actor_id=user.id, action="governance.eligibility_claim",
                    target=f"user:{user.id}", detail=labels))
    db.commit()
    return {"ok": True, "claimed": labels}
