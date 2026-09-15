"""Club governance: points-based ranks, officer/mentor eligibility, and weighted voting.

This is the connective tissue that turns earned points into real-world standing:

    do work -> earn points -> climb membership tiers -> unlock eligibility -> unlock voting power

Everything here derives from the append-only points ledger (via engine.lifetime_points), so it inherits
the same anti-farming guarantees as the leaderboard: you cannot buy standing, only earn it.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import engine

# --------------------------------------------------------------------------- membership tiers
# Ordered low -> high. `min_points` is the lifetime points needed to reach each tier.
# These are *membership* tiers (standing in the club), distinct from the RBAC Role which controls
# what buttons you can press. Tiers are earned automatically; Roles are granted by admins.
TIERS = [
    {"index": 0, "key": "novice",      "name": "Novice",      "min_points": 0,     "icon": "🌱"},
    {"index": 1, "key": "contributor", "name": "Contributor", "min_points": 500,   "icon": "⚙️"},
    {"index": 2, "key": "builder",     "name": "Builder",     "min_points": 2000,  "icon": "🔧"},
    {"index": 3, "key": "veteran",     "name": "Veteran",     "min_points": 5000,  "icon": "🏅"},
    {"index": 4, "key": "core",        "name": "Core Member", "min_points": 12000, "icon": "⭐"},
    {"index": 5, "key": "legend",      "name": "Legend",      "min_points": 30000, "icon": "👑"},
]

# You must be at least this tier index to cast a vote (Contributor). Keeps drive-by/new accounts out.
MIN_VOTING_TIER = 1

# Points threshold at which a member becomes *eligible* to be promoted to officer/mentor.
# Eligibility != the role itself — an admin still confirms it (see routers/governance.py).
ELIGIBILITY = [
    {"role": "MENTOR",  "label": "Mentor",  "min_points": 5000},
    {"role": "COMMITTEE", "label": "Officer / Committee", "min_points": 3000},
]


def tier_for_points(points: int) -> dict:
    """Return the highest tier whose min_points is satisfied."""
    current = TIERS[0]
    for t in TIERS:
        if points >= t["min_points"]:
            current = t
    return current


def next_tier(points: int) -> dict | None:
    """The next tier up, or None if already at the top."""
    cur = tier_for_points(points)
    for t in TIERS:
        if t["index"] == cur["index"] + 1:
            return t
    return None


def vote_weight(points: int) -> int:
    """Points-weighted vote power, but capped so no single member dominates.

    Design goals:
    - Reward contribution: more points => more weight.
    - Resist plutocracy: weight grows in *steps* (by tier), not linearly with raw points, and is
      hard-capped. A Legend has at most `len(TIERS)` votes' worth of influence, not thousands.
    - Everyone eligible always has at least 1 vote.
    """
    tier = tier_for_points(points)
    # weight == tier index, floored at 1 for anyone who can vote at all.
    return max(1, tier["index"])


def eligibility_for(points: int, current_role: str) -> list[dict]:
    """Which officer/mentor promotions this member now qualifies for (and hasn't already got)."""
    from .models import ROLE_RANK, Role

    try:
        have_rank = ROLE_RANK.get(Role(current_role), 0)
    except ValueError:
        have_rank = 0
    out = []
    for e in ELIGIBILITY:
        target_rank = ROLE_RANK.get(Role(e["role"]), 0)
        out.append({
            **e,
            "qualified": points >= e["min_points"],
            "already_held": have_rank >= target_rank,
        })
    return out


def standing(db: Session, user) -> dict:
    """Full governance snapshot for a user: points, tier, progress, voting power, eligibility."""
    points = engine.lifetime_points(db, user.id)
    tier = tier_for_points(points)
    nxt = next_tier(points)
    can_vote = tier["index"] >= MIN_VOTING_TIER
    return {
        "points": points,
        "tier": tier,
        "next_tier": nxt,
        "points_to_next": (nxt["min_points"] - points) if nxt else 0,
        "can_vote": can_vote,
        "vote_weight": vote_weight(points) if can_vote else 0,
        "min_voting_tier": TIERS[MIN_VOTING_TIER],
        "eligibility": eligibility_for(points, user.role),
    }
