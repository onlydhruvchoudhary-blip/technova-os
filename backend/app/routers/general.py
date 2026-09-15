"""Leaderboard, notifications, resources, announcements, certificates+verification, search, command center."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import engine
from ..database import get_db
from ..models import (
    ActivityEvent,
    Announcement,
    AuditLog,
    Certificate,
    Challenge,
    Course,
    Event,
    Notification,
    PointsLedgerEntry,
    Project,
    Resource,
    Role,
    User,
)
from ..schemas import AnnouncementIn
from ..security import get_current_user, get_optional_user, require_role, verify_certificate_sig

router = APIRouter(prefix="/api", tags=["general"])


# ---------------------------------------------------------------- leaderboard
@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                    limit: int = 50):
    board = engine.leaderboard(db, limit=limit)
    # category breakdown for the current user (transparency of scoring)
    rows = db.execute(
        select(PointsLedgerEntry.category, func.sum(PointsLedgerEntry.points))
        .where(PointsLedgerEntry.user_id == user.id)
        .group_by(PointsLedgerEntry.category)
    ).all()
    breakdown = {cat: int(pts or 0) for cat, pts in rows}
    return {"board": board, "me": {"rank": engine.user_rank(db, user.id),
                                   "points": engine.total_points(db, user.id),
                                   "breakdown": breakdown}}


# ---------------------------------------------------------------- notifications
@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc()).limit(50)).scalars().all()
    unread = sum(1 for n in rows if not n.read)
    return {"unread": unread, "items": [{
        "id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link,
        "read": n.read, "created_at": n.created_at} for n in rows]}


@router.post("/notifications/read")
def mark_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id,
                                  Notification.read == False).update({"read": True})  # noqa
    db.commit()
    return {"ok": True}


@router.get("/notifications/stream")
async def notifications_stream(token: str, db: Session = Depends(get_db)):
    """Server-Sent Events stream for near-instant notifications (replaces fixed polling).

    An EventSource cannot send custom/Authorization headers, so the JWT is passed as ?token=.
    The stream is bounded (self-recycles) so it never pins a worker indefinitely; the client
    reconnects automatically. Each event carries the current unread count.
    """
    import asyncio
    import json as _json

    from ..database import SessionLocal
    from ..security import user_from_token

    user = user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = user.id

    from ..broker import broker

    def _unread() -> int:
        s = SessionLocal()
        try:
            return int(s.execute(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id, Notification.read == False)  # noqa
            ).scalar_one())
        finally:
            s.close()

    async def event_gen():
        # Event-driven: push the current unread count once, then only when a new notification for
        # THIS user is published to the broker. No per-second polling per connection.
        q = broker.subscribe("notify", user_id=user_id)
        try:
            yield f"data: {_json.dumps({'unread': _unread(), 'latest': None})}\n\n"
            deadline = asyncio.get_event_loop().time() + 120
            while asyncio.get_event_loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=20)
                    payload = {"unread": _unread(),
                               "latest": {"kind": msg.data.get("kind"),
                                          "title": msg.data.get("title"),
                                          "body": msg.data.get("body"),
                                          "link": msg.data.get("link")}}
                    yield f"data: {_json.dumps(payload)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            broker.unsubscribe(q)
        yield "event: reconnect\ndata: {}\n\n"

    from starlette.responses import StreamingResponse
    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- activity feed (club pulse)
def _activity_dict(a: ActivityEvent) -> dict:
    return {"id": a.id, "kind": a.kind, "icon": a.icon, "actor": a.actor_name,
            "text": a.text, "link": a.link, "points": a.points,
            "created_at": a.created_at.isoformat() if a.created_at else None}


@router.get("/activity")
def activity_feed(limit: int = 30, before: int | None = None,
                  db: Session = Depends(get_db),
                  _user: User = Depends(get_current_user)):
    """Paginated, club-wide public activity pulse (newest first).

    Keyset pagination via `before` (an event id) keeps it O(limit) regardless of table size —
    pass the smallest id you've already seen to fetch the next page.
    """
    limit = max(1, min(limit, 100))
    stmt = select(ActivityEvent).order_by(ActivityEvent.id.desc()).limit(limit)
    if before:
        stmt = select(ActivityEvent).where(ActivityEvent.id < before).order_by(
            ActivityEvent.id.desc()).limit(limit)
    rows = list(db.execute(stmt).scalars())
    return {"items": [_activity_dict(a) for a in rows],
            "next_before": rows[-1].id if len(rows) == limit else None}


@router.get("/activity/stream")
async def activity_stream(token: str, db: Session = Depends(get_db)):
    """SSE stream of the live club activity pulse. Auth via ?token= (EventSource can't set headers).

    Bounded lifetime (self-recycles ~2 min); the browser EventSource reconnects transparently.
    Emits only events newer than the highest id seen at connect time, so reconnects don't replay.
    """
    import asyncio
    import json as _json

    from ..security import user_from_token

    user = user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from ..broker import broker

    async def event_gen():
        # Event-driven: subscribe to the broker and forward pushed frames. No per-second DB poll.
        q = broker.subscribe("activity")
        try:
            yield ": connected\n\n"  # immediate frame so clients/proxies confirm the open stream
            # bounded lifetime; browser EventSource reconnects transparently
            deadline = asyncio.get_event_loop().time() + 120
            while asyncio.get_event_loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=20)
                    yield f"data: {_json.dumps(msg.data)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"  # comment frame keeps the connection warm
        finally:
            broker.unsubscribe(q)
        yield "event: reconnect\ndata: {}\n\n"

    from starlette.responses import StreamingResponse
    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- resources
@router.get("/resources")
def list_resources(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                   technology: str | None = None, difficulty: str | None = None,
                   q: str | None = None):
    query = select(Resource)
    if technology:
        query = query.where(Resource.technology == technology)
    if difficulty:
        query = query.where(Resource.difficulty == difficulty)
    if q:
        like = f"%{q}%"
        query = query.where(or_(Resource.title.ilike(like), Resource.description.ilike(like),
                                Resource.topic.ilike(like)))
    rows = db.execute(query.order_by(Resource.technology, Resource.difficulty)).scalars().all()
    return [{"id": r.id, "title": r.title, "url": r.url, "kind": r.kind,
             "technology": r.technology, "difficulty": r.difficulty, "topic": r.topic,
             "description": r.description} for r in rows]


# ---------------------------------------------------------------- announcements
@router.get("/announcements")
def list_announcements(db: Session = Depends(get_db), viewer: User | None = Depends(get_optional_user)):
    rows = db.execute(select(Announcement).order_by(Announcement.pinned.desc(),
                                                    Announcement.created_at.desc()).limit(20)).scalars().all()
    return [{"id": a.id, "title": a.title, "body": a.body, "pinned": a.pinned,
             "created_at": a.created_at} for a in rows]


@router.post("/announcements", status_code=201)
def create_announcement(data: AnnouncementIn, user: User = Depends(require_role(Role.COMMITTEE)),
                        db: Session = Depends(get_db)):
    a = Announcement(title=data.title, body=data.body, pinned=data.pinned, created_by=user.id)
    db.add(a)
    db.flush()
    # notify all active members
    for uid, in db.execute(select(User.id).where(User.is_active == True)).all():  # noqa
        engine.notify(db, uid, "announcement", data.title, data.body[:120], "/")
    db.commit()
    return {"id": a.id}


# ---------------------------------------------------------------- certificates + verification (public)
@router.get("/certificates/me")
def my_certificates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Certificate).where(Certificate.user_id == user.id,
                                                Certificate.revoked == False)  # noqa
                      .order_by(Certificate.issued_at.desc())).scalars().all()
    return [{"cert_uid": c.cert_uid, "kind": c.kind, "title": c.title, "context": c.context,
             "issuer": c.issuer, "issued_at": c.issued_at} for c in rows]


@router.post("/certificates/{cert_uid}/revoke")
def revoke_certificate(cert_uid: str, user: User = Depends(require_role(Role.CLUB_HEAD)),
                       db: Session = Depends(get_db)):
    """Revoke a certificate issued in error. Audited; verification will then report invalid."""
    c = db.execute(select(Certificate).where(Certificate.cert_uid == cert_uid)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Certificate not found")
    c.revoked = True
    db.add(AuditLog(actor_id=user.id, action="certificate.revoke", target=f"cert:{cert_uid}"))
    engine.notify(db, c.user_id, "certificate", "A certificate was revoked",
                  f"{c.title} ({cert_uid}) is no longer valid.", "")
    db.commit()
    return {"revoked": True}


@router.get("/verify/{cert_uid}")
def verify_certificate(cert_uid: str, db: Session = Depends(get_db)):
    """PUBLIC endpoint: anyone can verify a certificate's authenticity."""
    c = db.execute(select(Certificate).where(Certificate.cert_uid == cert_uid)).scalar_one_or_none()
    if not c:
        return {"valid": False, "reason": "No certificate with that ID"}
    if c.revoked:
        return {"valid": False, "reason": "Certificate has been revoked"}
    valid = verify_certificate_sig(c.cert_uid, c.user_id, c.kind, c.signature)
    recipient = db.get(User, c.user_id)
    return {
        "valid": valid,
        "cert_uid": c.cert_uid, "kind": c.kind, "title": c.title, "context": c.context,
        "issuer": c.issuer, "issued_at": c.issued_at,
        "recipient": recipient.name if recipient else "Unknown",
    }


# ---------------------------------------------------------------- global search
@router.get("/search")
def search(q: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if len(q) < 2:
        return {"results": []}
    like = f"%{q}%"
    results = []
    for p in db.execute(select(Project).where(Project.title.ilike(like)).limit(6)).scalars().all():
        results.append({"type": "project", "title": p.title, "link": f"/projects/{p.slug}"})
    for c in db.execute(select(Course).where(Course.title.ilike(like)).limit(6)).scalars().all():
        results.append({"type": "course", "title": c.title, "link": f"/academy/{c.slug}"})
    for ch in db.execute(select(Challenge).where(Challenge.title.ilike(like)).limit(6)).scalars().all():
        results.append({"type": "challenge", "title": ch.title, "link": f"/challenges/{ch.slug}"})
    for e in db.execute(select(Event).where(Event.title.ilike(like)).limit(6)).scalars().all():
        results.append({"type": "event", "title": e.title, "link": "/events"})
    for u in db.execute(select(User).where(User.name.ilike(like), User.is_active == True).limit(6)).scalars().all():  # noqa
        results.append({"type": "member", "title": u.name, "link": f"/members/{u.id}"})
    for r in db.execute(select(Resource).where(Resource.title.ilike(like)).limit(6)).scalars().all():
        results.append({"type": "resource", "title": r.title, "link": r.url})
    return {"results": results}


# ---------------------------------------------------------------- members directory
@router.get("/members")
def list_members(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    users = db.execute(select(User).where(User.is_active == True).order_by(User.name)).scalars().all()  # noqa
    return [{"id": u.id, "name": u.name, "role": u.role, "avatar_seed": u.avatar_seed,
             "points": engine.total_points(db, u.id)} for u in users]


# ---------------------------------------------------------------- command center (live club screen)
@router.get("/command-center")
def command_center(db: Session = Depends(get_db)):
    now = engine.utcnow()
    upcoming = db.execute(select(Event).where(Event.starts_at >= now, Event.is_public == True)  # noqa
                          .order_by(Event.starts_at).limit(5)).scalars().all()
    announcements = db.execute(select(Announcement).order_by(Announcement.pinned.desc(),
                                                             Announcement.created_at.desc()).limit(4)).scalars().all()
    weekly = db.execute(select(Challenge).where(Challenge.is_weekly == True,  # noqa
                                                Challenge.published == True)  # noqa
                        .order_by(Challenge.id.desc()).limit(4)).scalars().all()
    active_projects = db.execute(select(Project).where(
        Project.state.in_(["DEVELOPMENT", "TESTING", "PLANNING", "DEMO"]))
        .order_by(Project.created_at.desc()).limit(6)).scalars().all()
    stats = {
        "members": db.execute(select(func.count(User.id)).where(User.is_active == True)).scalar_one(),  # noqa
        "projects": db.execute(select(func.count(Project.id))).scalar_one(),
        "events": db.execute(select(func.count(Event.id))).scalar_one(),
        "challenges": db.execute(select(func.count(Challenge.id))).scalar_one(),
    }
    return {
        "board": engine.leaderboard(db, limit=8),
        "upcoming_events": [{"title": e.title, "kind": e.kind, "starts_at": e.starts_at,
                             "location": e.location} for e in upcoming],
        "announcements": [{"title": a.title, "body": a.body[:160]} for a in announcements],
        "weekly_challenges": [{"title": c.title, "kind": c.weekly_kind, "slug": c.slug} for c in weekly],
        "active_projects": [{"title": p.title, "state": p.state, "slug": p.slug} for p in active_projects],
        "stats": stats,
    }
