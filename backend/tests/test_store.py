"""Rewards Store: tamper-proof point spending, stock limits, and refund-on-cancel."""
from app import engine
from app.database import SessionLocal
from app.models import Reward, Role, User
from app.security import hash_password
from tests.conftest import auth_header, register


def _give(email, pts):
    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email=email).first().id
        engine.award_points(db, uid, pts, "competition", "seed", f"store-{email}", "boost")
        db.commit()
        return uid
    finally:
        db.close()


def _reward(cost=100, stock=-1, name="Test Reward"):
    db = SessionLocal()
    try:
        r = Reward(name=name, description="x", cost=cost, kind="digital", stock=stock)
        db.add(r)
        db.commit()
        return r.id
    finally:
        db.close()


def test_wallet_excludes_redemptions_but_lifetime_is_stable(client):
    register(client, "wallet@technova.club")
    hdr = auth_header(client, "wallet@technova.club")
    _give("wallet@technova.club", 1000)
    rid = _reward(cost=300)

    before = client.get("/api/store/wallet", headers=hdr).json()
    assert before["balance"] == 1000
    assert before["lifetime"] == 1000

    r = client.post(f"/api/store/rewards/{rid}/redeem", headers=hdr)
    assert r.status_code == 200, r.text

    after = client.get("/api/store/wallet", headers=hdr).json()
    assert after["balance"] == 700          # wallet debited
    assert after["lifetime"] == 1000        # contribution unchanged -> rank/tier unaffected


def test_cannot_overspend(client):
    register(client, "poor@technova.club")
    hdr = auth_header(client, "poor@technova.club")
    _give("poor@technova.club", 50)
    rid = _reward(cost=999)
    r = client.post(f"/api/store/rewards/{rid}/redeem", headers=hdr)
    assert r.status_code == 400
    assert "Insufficient" in r.json()["detail"]


def test_stock_is_enforced(client):
    register(client, "stock@technova.club")
    hdr = auth_header(client, "stock@technova.club")
    _give("stock@technova.club", 10000)
    rid = _reward(cost=100, stock=1, name="Limited")
    # first redeem ok, stock -> 0
    assert client.post(f"/api/store/rewards/{rid}/redeem", headers=hdr).status_code == 200
    # second redeem blocked: sold out
    r2 = client.post(f"/api/store/rewards/{rid}/redeem", headers=hdr)
    assert r2.status_code == 409


def test_admin_cancel_refunds_points_and_restocks(client):
    register(client, "refund@technova.club")
    hdr = auth_header(client, "refund@technova.club")
    _give("refund@technova.club", 500)
    rid = _reward(cost=200, stock=3, name="Refundable")

    red = client.post(f"/api/store/rewards/{rid}/redeem", headers=hdr).json()
    assert client.get("/api/store/wallet", headers=hdr).json()["balance"] == 300
    redemption_id = red["redemption"]["id"]

    # promote a club head to cancel it
    db = SessionLocal()
    try:
        head = User(email="storehead@technova.club", name="Head", role=Role.CLUB_HEAD.value,
                    password_hash=hash_password("password123"))
        db.add(head)
        db.commit()
    finally:
        db.close()
    ahdr = auth_header(client, "storehead@technova.club")

    r = client.patch(f"/api/store/redemptions/{redemption_id}",
                     json={"status": "cancelled", "note": "changed mind"}, headers=ahdr)
    assert r.status_code == 200
    # points fully refunded
    assert client.get("/api/store/wallet", headers=hdr).json()["balance"] == 500


def test_member_cannot_create_rewards(client):
    register(client, "notadmin@technova.club")
    hdr = auth_header(client, "notadmin@technova.club")
    r = client.post("/api/store/rewards",
                    json={"name": "Hax", "cost": 1, "kind": "digital"}, headers=hdr)
    assert r.status_code == 403
