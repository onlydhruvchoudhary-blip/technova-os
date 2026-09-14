"""Production middleware: request IDs, timing/structured logging, and security headers.

These are cross-cutting concerns that make the API observable and safe to expose publicly,
without touching individual route handlers.
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("technova.access")


# Content-Security-Policy for the SPA. Everything is served same-origin; the app uses no external
# scripts, fonts, or images. React sets inline `style` attributes (avatars/layout), so style-src
# must allow 'unsafe-inline'; avatars/QR are inline SVG/text so img-src only needs self + data:.
# `frame-ancestors` is intentionally omitted here and handled by env-gated X-Frame-Options, so the
# dev/preview cross-origin iframe keeps working.
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",  # includes the same-origin SSE stream
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])


# Security headers appropriate for an API + SPA served from one origin.
# (X-Frame-Options is applied conditionally below so dev/preview iframes still work.)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "0",  # modern browsers: rely on CSP, disable legacy auditor
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time each request, and emit a structured access log line."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            # The app's global exception handler will format the body; log the failure here.
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("rid=%s %s %s -> 500 in %.1fms",
                             rid, request.method, request.url.path, elapsed)
            raise
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time-ms"] = f"{elapsed:.1f}"
        # Skip noisy static asset logs; log API + navigation requests.
        if not request.url.path.startswith("/assets/"):
            logger.info("rid=%s %s %s -> %s in %.1fms",
                        rid, request.method, request.url.path,
                        response.status_code, elapsed)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add hardening headers to every response."""

    def __init__(self, app, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        # Clickjacking + HSTS only in production (dev/preview run inside a cross-origin iframe,
        # so X-Frame-Options there would break the live preview).
        if self.is_production:
            response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
