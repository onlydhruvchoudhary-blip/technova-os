"""Event management + signed-QR attendance (time-limited, anti-abuse)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import engine
from ..config import get_settings
from ..database import get_db
from ..models import Attendance, AuditLog, Event, Registration, Role, User
from ..schemas import AttendanceIn, EventCreate
from ..security import get_current_user, get_optional_user, make_qr_token, require_role, verify_qr_token

router = APIRouter(prefix="/api/events", tags=["events"])
settings = get_settings()


@router.get("")
def list_events(viewer: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    q = select(Event)
    if not viewer:
        q = q.where(Event.is_public == True)  # noqa
    events = db.execute(q.order_by(Event.starts_at.desc())).scalars().all()
    out = []
    for e in events:
        reg_count = db.execute(select(func.count(Registration.id))
                               .where(Registration.event_id == e.id)).scalar_one()
        att_count = db.execute(select(func.count(Attendance.id))
                               .where(Attendance.event_id == e.id)).scalar_one()
        registered = bool(viewer and db.execute(select(Registration.id).where(
            Registration.event_id == e.id, Registration.user_id == viewer.id)).first())
        attended = bool(viewer and db.execute(select(Attendance.id).where(
            Attendance.event_id == e.id, Attendance.user_id == viewer.id)).first())
        out.append({
            "id": e.id, "title": e.title, "description": e.description, "kind": e.kind,
            "location": e.location, "starts_at": e.starts_at, "ends_at": e.ends_at,
            "capacity": e.capacity, "is_public": e.is_public, "attendance_open": e.attendance_open,
            "registrations": int(reg_count), "attendance": int(att_count),
            "registered": registered, "attended": attended,
        })
    return out


@router.post("", status_code=201)
def create_event(data: EventCreate, user: User = Depends(require_role(Role.COMMITTEE)),
                 db: Session = Depends(get_db)):
    e = Event(title=data.title, description=data.description, kind=data.kind,
              location=data.location, starts_at=data.starts_at, ends_at=data.ends_at,
              capacity=data.capacity, is_public=data.is_public, created_by=user.id)
    db.add(e)
    db.add(AuditLog(actor_id=user.id, action="event.create", target=data.title))
    db.commit()
    return {"id": e.id}


@router.post("/{event_id}/register")
def register(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    reg_count = db.execute(select(func.count(Registration.id))
                           .where(Registration.event_id == e.id)).scalar_one()
    if reg_count >= e.capacity:
        raise HTTPException(status_code=409, detail="Event is full")
    exists = db.execute(select(Registration.id).where(
        Registration.event_id == e.id, Registration.user_id == user.id)).first()
    if exists:
        raise HTTPException(status_code=409, detail="Already registered")
    db.add(Registration(event_id=e.id, user_id=user.id))
    db.commit()
    return {"status": "registered"}


@router.post("/{event_id}/attendance/open")
def open_attendance(event_id: int, open: bool = True,
                    user: User = Depends(require_role(Role.COMMITTEE)),
                    db: Session = Depends(get_db)):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    e.attendance_open = open
    db.add(AuditLog(actor_id=user.id, action="attendance.toggle",
                    target=f"event:{event_id}", detail=str(open)))
    db.commit()
    return {"attendance_open": open}


@router.get("/{event_id}/qr")
def get_qr(event_id: int, user: User = Depends(require_role(Role.COMMITTEE)),
           db: Session = Depends(get_db)):
    """Return a fresh, time-limited signed token. Organiser screen refreshes this every ~90s."""
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not e.attendance_open:
        raise HTTPException(status_code=400, detail="Attendance is not open for this event")
    token = make_qr_token(event_id)
    return {"token": token, "expires_in": settings.qr_window_seconds, "event_id": event_id}


@router.post("/{event_id}/attendance")
def mark_attendance(event_id: int, data: AttendanceIn,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not e.attendance_open:
        raise HTTPException(status_code=400, detail="Attendance is closed")
    if not verify_qr_token(data.token, event_id):
        raise HTTPException(status_code=400, detail="Invalid or expired QR code")
    exists = db.execute(select(Attendance.id).where(
        Attendance.event_id == event_id, Attendance.user_id == user.id)).first()
    if exists:
        raise HTTPException(status_code=409, detail="Attendance already recorded")
    db.add(Attendance(event_id=event_id, user_id=user.id))
    engine.emit(db, engine.Event("attendance.marked", user.id,
                                 {"event_id": event_id, "title": e.title}))
    db.commit()
    return {"status": "present", "event": e.title}
