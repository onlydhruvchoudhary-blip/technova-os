"""Authentication, hashing, JWT, RBAC dependencies, and signed QR/certificate tokens."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User, Role, ROLE_RANK

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
ALGO = "HS256"
COOKIE_NAME = "technova_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def create_access_token(user_id: int) -> str:
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGO)


def _extract_token(request: Request, bearer: str | None) -> str | None:
    """Token can arrive via (in priority order):
      1. the Authorization: Bearer header (standard, local dev, tests),
      2. the X-Auth-Token custom header (survives proxies that strip Authorization),
      3. the auth cookie (survives when custom headers are also stripped).
    This layered approach makes auth robust behind sandboxed preview/reverse proxies."""
    if bearer:
        return bearer
    x = request.headers.get("x-auth-token")
    if x:
        return x
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        return cookie
    return None


def get_current_user(request: Request,
                     token: str | None = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> User:
    cred_exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    tok = _extract_token(request, token)
    if not tok:
        raise cred_exc
    try:
        payload = jwt.decode(tok, settings.secret_key, algorithms=[ALGO])
        uid = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise cred_exc
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise cred_exc
    return user


def get_optional_user(request: Request,
                      token: str | None = Depends(oauth2_scheme),
                      db: Session = Depends(get_db)) -> User | None:
    tok = _extract_token(request, token)
    if not tok:
        return None
    try:
        payload = jwt.decode(tok, settings.secret_key, algorithms=[ALGO])
        return db.get(User, int(payload.get("sub")))
    except (JWTError, TypeError, ValueError):
        return None


def require_role(min_role: Role):
    """Dependency factory enforcing a minimum role rank."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK.get(Role(user.role), 0) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Requires role {min_role.value} or higher")
        return user
    return checker


def has_role(user: User, min_role: Role) -> bool:
    return ROLE_RANK.get(Role(user.role), 0) >= ROLE_RANK[min_role]


# --------------------------------------------------------------------------- signed QR tokens
def make_qr_token(event_id: int, window: int | None = None) -> str:
    """Time-limited signed token. Rotates every qr_window_seconds -> cannot be reused forever."""
    w = window if window is not None else int(time.time()) // settings.qr_window_seconds
    msg = f"{event_id}:{w}".encode()
    sig = hmac.new(settings.qr_secret.encode(), msg, hashlib.sha256).hexdigest()[:16]
    return f"{event_id}.{w}.{sig}"


def verify_qr_token(token: str, event_id: int) -> bool:
    try:
        eid, w, sig = token.split(".")
        eid, w = int(eid), int(w)
    except (ValueError, AttributeError):
        return False
    if eid != event_id:
        return False
    now_w = int(time.time()) // settings.qr_window_seconds
    # accept current or immediately previous window (clock skew / scan latency)
    for cand in (now_w, now_w - 1):
        if hmac.compare_digest(sig, make_qr_token(event_id, cand).split(".")[2]):
            return True
    return False


# --------------------------------------------------------------------------- certificate signatures
def sign_certificate(cert_uid: str, user_id: int, kind: str) -> str:
    msg = f"{cert_uid}:{user_id}:{kind}".encode()
    return hmac.new(settings.qr_secret.encode(), msg, hashlib.sha256).hexdigest()[:32]


def verify_certificate_sig(cert_uid: str, user_id: int, kind: str, signature: str) -> bool:
    return hmac.compare_digest(signature, sign_certificate(cert_uid, user_id, kind))
