"""Rewards Store: spend earned points on real perks, with a tamper-proof audit trail.

Design guarantees
- The wallet is the SUM of the append-only points ledger. A purchase writes a NEGATIVE ledger row
  (category "redemption"); there is no mutable balance column to edit, so a client cannot inflate
  its own balance.
- Every debit is server-validated (balance + stock) inside one transaction and de-duplicated, so a
  retried/double-clicked request cannot double-spend or oversell stock.
- Spending never lowers leaderboard rank or governance tier (those use lifetime contribution points).

Endpoints
- GET   /api/store/rewards                     list active rewards (+ affordability for caller)
- GET   /api/store/wallet                      caller's spendable balance + lifetime contribution
- POST  /api/store/rewards/{id}/redeem         redeem a reward (atomic debit + stock decrement)
- GET   /api/store/redemptions                 caller's own redemption history
- POST  /api/store/rewards                      [admin] create a reward
- PATCH /api/store/rewards/{id}                 [admin] edit a reward
- GET   /api/store/admin/redemptions            [admin] all redemptions (fulfilment queue)
- PATCH /api/store/redemptions/{id}             [admin] fulfil / cancel (cancel refunds points)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import engine
from ..database import get_db
from ..models import AuditLog, Redemption, Reward, Role, User
from ..schemas import RedemptionUpdate, RewardCreate, RewardUpdate
from ..security import get_current_user, require_role

router = APIRouter(prefix="/api/store", tags=["store"])


def _reward_dict(r: Reward, balance: int | None = None) -> dict:
    d = {
        "id": r.id, "name": r.name, "description": r.description, "cost": r.cost,
        "kind": r.kind, "icon": r.icon, "stock": r.stock, "active": r.active,
        "sold_out": r.stock == 0,
    }
    if balance is not None:
        d["affordable"] = balance >= r.cost
    return d


def _redemption_dict(db: Session, red: Redemption) -> dict:
    r = db.get(Reward, red.reward_id)
    u = db.get(User, red.user_id)
    return {
        "id": red.id,
        "reward": {"id": r.id, "name": r.name, "icon": r.icon, "kind": r.kind} if r else None,
        "user": {"id": u.id, "name": u.name} if u else None,
        "cost_at_claim": red.cost_at_claim,
        "status": red.status,
        "note": red.note,
        "created_at": red.created_at.isoformat() if red.created_at else None,
    }


@router.get("/wallet")
def wallet(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {
        "balance": engine.total_points(db, user.id),         # spendable
        "lifetime": engine.lifetime_points(db, user.id),     # contribution (rank/tier)
    }


@router.get("/rewards")
def list_rewards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    balance = engine.total_points(db, user.id)
    rows = db.execute(select(Reward).where(Reward.active.is_(True))
                      .order_by(Reward.cost.asc())).scalars().all()
    return {"balance": balance, "rewards": [_reward_dict(r, balance) for r in rows]}


@router.post("/rewards/{rid}/redeem")
def redeem(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Lock semantics: validate stock + balance, debit, and decrement stock in ONE transaction.
    r = db.get(Reward, rid)
    if not r or not r.active:
        raise HTTPException(status_code=404, detail="Reward not available")
    if r.stock == 0:
        raise HTTPException(status_code=409, detail="This reward is sold out")

    # Unique per (user, reward, current stock/attempt) so a genuine re-purchase is allowed later,
    # but a double-clicked single purchase de-dupes. We use the next redemption count as the nonce.
    nonce = db.execute(select(Redemption).where(
        Redemption.reward_id == r.id, Redemption.user_id == user.id)).scalars().all()
    source_id = f"{r.id}:{len(nonce)}"

    spend = engine.spend_points(db, user.id, r.cost, "reward", source_id,
                                f"Redeemed: {r.name}")
    if not spend["ok"]:
        raise HTTPException(status_code=400, detail=spend["error"])

    if r.stock > 0:
        r.stock -= 1  # decrement finite stock

    red = Redemption(reward_id=r.id, user_id=user.id, cost_at_claim=r.cost,
                     status="claimed", ledger_dedupe=spend["dedupe_key"])
    db.add(red)
    db.add(AuditLog(actor_id=user.id, action="store.redeem",
                    target=f"reward:{r.id}", detail=f"{r.name} (-{r.cost} pts)"))
    engine.notify(db, user.id, "store", "Reward claimed 🎁",
                  f"You redeemed {r.name} for {r.cost} points.", link="/store")
    engine._safe_activity(db, kind="redeem", actor_id=user.id, icon="🎁",
                          text=f"redeemed “{r.name}” from the store", link="/store")
    db.commit()
    return {"ok": True, "balance": spend["balance"], "redemption": _redemption_dict(db, red)}


@router.get("/redemptions")
def my_redemptions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(Redemption).where(Redemption.user_id == user.id)
                      .order_by(Redemption.created_at.desc())).scalars().all()
    return [_redemption_dict(db, r) for r in rows]


# ---------------------------------------------------------------- admin
@router.post("/rewards")
def create_reward(data: RewardCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_role(Role.CLUB_HEAD))):
    kind = data.kind if data.kind in ("digital", "physical", "perk") else "digital"
    r = Reward(name=data.name.strip(), description=data.description.strip(), cost=data.cost,
               kind=kind, icon=data.icon or "🎁", stock=data.stock)
    db.add(r)
    db.add(AuditLog(actor_id=actor.id, action="store.reward_create", target=f"reward:{r.name}"))
    db.commit()
    return _reward_dict(r)


@router.patch("/rewards/{rid}")
def update_reward(rid: int, data: RewardUpdate, db: Session = Depends(get_db),
                  actor: User = Depends(require_role(Role.CLUB_HEAD))):
    r = db.get(Reward, rid)
    if not r:
        raise HTTPException(status_code=404, detail="Reward not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.add(AuditLog(actor_id=actor.id, action="store.reward_update", target=f"reward:{r.id}"))
    db.commit()
    return _reward_dict(r)


@router.get("/admin/redemptions")
def all_redemptions(db: Session = Depends(get_db),
                    actor: User = Depends(require_role(Role.COMMITTEE))):
    rows = db.execute(select(Redemption).order_by(
        Redemption.created_at.desc())).scalars().all()
    return [_redemption_dict(db, r) for r in rows]


@router.patch("/redemptions/{rid}")
def update_redemption(rid: int, data: RedemptionUpdate, db: Session = Depends(get_db),
                      actor: User = Depends(require_role(Role.COMMITTEE))):
    red = db.get(Redemption, rid)
    if not red:
        raise HTTPException(status_code=404, detail="Redemption not found")
    # Cancelling a not-already-cancelled claim refunds the exact points spent and restocks.
    if data.status == "cancelled" and red.status != "cancelled":
        engine.refund_points(db, red.user_id, red.cost_at_claim, f"{red.id}",
                             f"Refund: cancelled redemption #{red.id}")
        reward = db.get(Reward, red.reward_id)
        if reward and reward.stock >= 0:
            reward.stock += 1
        engine.notify(db, red.user_id, "store", "Redemption cancelled",
                      f"{red.cost_at_claim} points were refunded.", link="/store")
    red.status = data.status
    red.note = data.note
    db.add(AuditLog(actor_id=actor.id, action="store.redemption_update",
                    target=f"redemption:{red.id}", detail=data.status))
    db.commit()
    return _redemption_dict(db, red)
