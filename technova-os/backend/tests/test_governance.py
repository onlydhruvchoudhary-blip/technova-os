"""Governance: tiers, points-weighted voting power, eligibility, and the voting API."""
import pytest

from app import engine, governance
from app.database import SessionLocal
from app.models import Proposal, Role, User
from app.security import hash_password
from tests.conftest import auth_header, register


# ---------------------------------------------------------------- unit: tiers & weights
def test_tier_ladder_is_monotonic():
    # points below the first threshold => Novice; huge points => top tier.
    assert governance.tier_for_points(0)["key"] == "novice"
    assert governance.tier_for_points(999999)["index"] == governance.TIERS[-1]["index"]
    # each higher point total gives an equal-or-higher tier
    last = -1
    for pts in [0, 500, 2000, 5000, 12000, 30000, 99999]:
        idx = governance.tier_for_points(pts)["index"]
        assert idx >= last
        last = idx


def test_vote_weight_is_capped_not_linear():
    # A member with 100x the points must NOT get 100x the vote weight.
    low = governance.vote_weight(600)       # Contributor
    high = governance.vote_weight(60000)    # Legend
    assert high > low                       # more contribution => more say
    assert high <= len(governance.TIERS)    # but hard-capped by tier count
    assert governance.vote_weight(0) >= 1   # anyone who can vote has >=1


def test_below_min_tier_cannot_vote_weight_zero_via_standing():
    db = SessionLocal()
    try:
        u = User(email="gov_new@technova.club", name="New", role=Role.MEMBER.value,
                 password_hash=hash_password("password123"))
        db.add(u)
        db.flush()
        st = governance.standing(db, u)
        assert st["can_vote"] is False
        assert st["vote_weight"] == 0
    finally:
        db.close()


# ---------------------------------------------------------------- API: voting flow
def test_low_tier_member_is_blocked_from_voting(client):
    register(client, "voter_low@technova.club")
    hdr = auth_header(client, "voter_low@technova.club")
    # create a proposal directly in the DB (open, min_tier=1)
    db = SessionLocal()
    try:
        p = Proposal(title="Test decision", options=["Approve", "Reject", "Abstain"],
                     status="open", min_tier=1, kind="decision")
        db.add(p)
        db.commit()
        pid = p.id
    finally:
        db.close()
    r = client.post(f"/api/governance/proposals/{pid}/vote", json={"choice": "Approve"}, headers=hdr)
    assert r.status_code == 403  # not enough points/tier


def test_eligible_member_votes_once_with_weight(client):
    register(client, "voter_ok@technova.club")
    hdr = auth_header(client, "voter_ok@technova.club")
    # give them enough points to clear the voting tier
    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email="voter_ok@technova.club").first().id
        engine.award_points(db, uid, 1200, "competition", "seed", "gov-test", "boost")
        db.commit()
        p = Proposal(title="Weighted vote", options=["Approve", "Reject", "Abstain"],
                     status="open", min_tier=1, kind="decision")
        db.add(p)
        db.commit()
        pid = p.id
    finally:
        db.close()

    r = client.post(f"/api/governance/proposals/{pid}/vote", json={"choice": "Approve"}, headers=hdr)
    assert r.status_code == 200, r.text
    assert r.json()["weight"] >= 1
    # second vote on same proposal is rejected
    r2 = client.post(f"/api/governance/proposals/{pid}/vote", json={"choice": "Reject"}, headers=hdr)
    assert r2.status_code == 409


def test_vote_on_proposal_with_deadline_does_not_500(client):
    """Regression: comparing utcnow() to a tz-naive SQLite closes_at must not raise."""
    import datetime as dt
    register(client, "voter_deadline@technova.club")
    hdr = auth_header(client, "voter_deadline@technova.club")
    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email="voter_deadline@technova.club").first().id
        engine.award_points(db, uid, 1200, "competition", "seed", "gov-deadline", "boost")
        db.commit()
        p = Proposal(title="Deadline vote", options=["Approve", "Reject", "Abstain"],
                     status="open", min_tier=1, kind="decision",
                     closes_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=3))
        db.add(p)
        db.commit()
        pid = p.id
    finally:
        db.close()
    r = client.post(f"/api/governance/proposals/{pid}/vote", json={"choice": "Approve"}, headers=hdr)
    assert r.status_code == 200, r.text


def test_standing_endpoint_shape(client):
    register(client, "standing@technova.club")
    hdr = auth_header(client, "standing@technova.club")
    r = client.get("/api/governance/standing", headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert "tier" in body and "vote_weight" in body and "eligibility" in body
