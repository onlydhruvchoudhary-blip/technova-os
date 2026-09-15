"""Activity feed: events are recorded on real workflows, feed is auth-gated and keyset-paginated."""
from app import engine
from app.database import SessionLocal
from app.models import ActivityEvent, Reward, User
from tests.conftest import auth_header, register


def _give(email, pts):
    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email=email).first().id
        engine.award_points(db, uid, pts, "competition", "seed", f"act-{email}", "boost")
        db.commit()
        return uid
    finally:
        db.close()


def _reward(cost=50, stock=-1, name="Sticker"):
    db = SessionLocal()
    try:
        r = Reward(name=name, description="x", cost=cost, kind="digital", stock=stock)
        db.add(r)
        db.commit()
        return r.id
    finally:
        db.close()


def test_activity_feed_requires_auth(client):
    assert client.get("/api/activity").status_code == 401


def test_redeem_records_activity_event(client):
    register(client, "act1@t.io")
    hdr = auth_header(client, "act1@t.io")
    _give("act1@t.io", 500)
    rid = _reward(cost=50, name="Cool Sticker")
    r = client.post(f"/api/store/rewards/{rid}/redeem", headers=hdr)
    assert r.status_code == 200, r.text

    feed = client.get("/api/activity", headers=hdr).json()
    assert any(i["kind"] == "redeem" and "Cool Sticker" in i["text"] for i in feed["items"])
    # actor name is denormalised and present
    top = next(i for i in feed["items"] if i["kind"] == "redeem")
    assert top["actor"]
    assert top["icon"] == "🎁"


def test_grant_achievement_records_activity(client):
    register(client, "act2@t.io")
    hdr = auth_header(client, "act2@t.io")
    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email="act2@t.io").first().id
        # ensure an achievement exists to grant
        from app.models import Achievement
        if not db.query(Achievement).filter_by(key="first_steps").first():
            db.add(Achievement(key="first_steps", name="First Steps",
                               description="x", icon="👟", points=10))
            db.commit()
        engine.grant_achievement(db, uid, "first_steps", "test")
        db.commit()
    finally:
        db.close()
    feed = client.get("/api/activity", headers=hdr).json()
    assert any(i["kind"] == "achievement" for i in feed["items"])


def test_activity_keyset_pagination(client):
    register(client, "act3@t.io")
    hdr = auth_header(client, "act3@t.io")
    db = SessionLocal()
    try:
        uid = db.query(User).filter_by(email="act3@t.io").first().id
        for i in range(6):
            engine.record_activity(db, "test", f"did thing {i}", actor_id=uid, icon="✅")
        db.commit()
    finally:
        db.close()
    page1 = client.get("/api/activity?limit=3", headers=hdr).json()
    assert len(page1["items"]) == 3
    assert page1["next_before"] is not None
    page2 = client.get(f"/api/activity?limit=3&before={page1['next_before']}", headers=hdr).json()
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)  # no overlap across pages
    # newest-first ordering
    assert page1["items"][0]["id"] > page1["items"][-1]["id"]


def test_safe_activity_never_breaks_outer_transaction(client):
    """A failing feed insert (bad FK) must roll back only itself, leaving the session usable."""
    db = SessionLocal()
    try:
        # bad FK: this insert fails inside its savepoint and is discarded, but must NOT raise
        engine._safe_activity(db, kind="test", text="orphan", actor_id=999999, icon="👻")
        # the session is still healthy — a valid write after the failure commits fine
        engine.record_activity(db, "test", "healthy", icon="✅")
        db.commit()
        assert db.query(ActivityEvent).filter_by(text="orphan").count() == 0
        assert db.query(ActivityEvent).filter_by(text="healthy").count() == 1
    finally:
        db.close()
