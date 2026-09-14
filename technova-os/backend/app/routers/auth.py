"""Authentication + basic rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User, Role, AuditLog
from ..schemas import RegisterIn, TokenOut, UserOut
from ..security import (hash_password, verify_password, create_access_token,
                        get_current_user, COOKIE_NAME)

_settings = get_settings()


def _set_auth_cookie(response: Response, token: str) -> None:
    # SameSite=None + Secure so the cookie survives inside the cross-origin preview iframe.
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, secure=True, samesite="none",
        max_age=_settings.access_token_expire_minutes * 60, path="/",
    )

router = APIRouter(prefix="/api/auth", tags=["auth"])

# simple in-memory rate limiter (per-IP) for auth endpoints
_hits: dict[str, deque] = defaultdict(deque)
RATE_LIMIT = 20      # requests
RATE_WINDOW = 60     # seconds


def _rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    dq = _hits[ip]
    while dq and dq[0] < now - RATE_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many attempts, slow down.")
    dq.append(now)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _rate_limit(request)
    exists = db.execute(select(User).where(User.email == data.email.lower())).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    # first ever user becomes SUPER_ADMIN
    is_first = db.execute(select(User.id)).first() is None
    user = User(
        email=data.email.lower(), name=data.name.strip(),
        password_hash=hash_password(data.password),
        role=Role.SUPER_ADMIN.value if is_first else Role.MEMBER.value,
        avatar_seed=data.name.strip().lower().replace(" ", "")[:20] or "nova",
    )
    db.add(user)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="user.register", target=f"user:{user.id}"))
    db.commit()
    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
def login(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    _rate_limit(request)
    user = db.execute(select(User).where(User.email == form.username.lower())).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenOut(access_token=token)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
