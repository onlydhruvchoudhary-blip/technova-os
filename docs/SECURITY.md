# Security & anti-exploit model

## Authentication
- Passwords hashed with **bcrypt** (passlib). Never stored or logged in plaintext.
- **JWT** access tokens (HS256), expiry configurable (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- Rate limiting on `/api/auth/*` (per-IP) and on challenge submissions (per-user).

## Authorization (RBAC)
Seven ascending roles: `GUEST < MEMBER < COMMITTEE < MENTOR < ADVISOR < CLUB_HEAD < SUPER_ADMIN`.
- Endpoints declare a minimum role via the `require_role(...)` dependency, plus ownership rules
  (e.g. only a project's lead or a mentor can approve members / advance state).
- Role changes are constrained: you cannot grant a role at or above your own; only a Super Admin
  can mint another Super Admin. Every change is written to the audit log.
- The **first registered user** becomes Super Admin (bootstraps the club), everyone else is a Member.

## Anti-exploit / fairness
| Threat | Safeguard |
|---|---|
| Point farming | **Daily category caps** (learning/attendance/social) enforced server-side. |
| Double counting | **Append-only ledger** with a unique `dedupe_key` per (user, source, source_id). Re-emitting an event awards nothing. |
| Fake attendance | QR tokens are **HMAC-signed and time-limited** (~90s window, current+previous accepted). Screenshots expire; one record per (event,user). |
| Cheating challenges | Server-side judging vs **hidden tests**; only sample results are returned. |
| Untrusted code | Runs in an **isolated subprocess** (`python -I`) with a static import guard, `RLIMIT_AS`/`RLIMIT_CPU`, wall-clock timeout, and `open`/`input` disabled. |
| Forged certificates | Certificates carry an **HMAC signature**; `/api/verify/{id}` recomputes it. Revoked certs verify as invalid. |
| Unauthorized certificate creation | Certificates are only issued by the engine from real events, never by a public endpoint. |
| Role abuse | Role assignment rules + audit log. |
| Privileged action tracking | **Audit log** on role changes, event/competition creation, scoring, revocation, state changes. |

## Transport / browser hardening (HTTP response headers)
Applied by `SecurityHeadersMiddleware` to every response:

| Header | Value | Notes |
|---|---|---|
| `Content-Security-Policy` | `default-src 'self'`; `script-src 'self'`; `style-src 'self' 'unsafe-inline'`; `img-src 'self' data:`; `object-src 'none'`; `base-uri 'self'`; `form-action 'self'`; `connect-src 'self'` | App loads no external scripts/fonts/images; `unsafe-inline` style is required for React inline `style` attributes. `frame-ancestors` deliberately omitted (see below). |
| `X-Content-Type-Options` | `nosniff` | Always. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Always. |
| `X-XSS-Protection` | `0` | Modern guidance: rely on CSP, disable the legacy auditor. |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Always. |
| `X-Frame-Options` | `SAMEORIGIN` | **Production only** (would break the cross-origin dev/preview iframe). |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | **Production only.** |

## Observability
`RequestContextMiddleware` stamps every response with `X-Request-ID` (echoing an inbound id if
present) and `X-Response-Time-ms`, and emits a structured `technova.access` log line per request
(method, path, status, duration, request id) — enough to trace and support a live deployment.

## Privacy — collect the minimum
- Only name + email + password are collected at registration. No phone, address, DOB, etc.
- Private data (member emails, attendance, draft projects, mentor feedback, admin data) is gated
  behind auth + role checks. Public surfaces (showcase, certificate verification, command center,
  public events) expose only non-sensitive fields.

## Hardening checklist for production
- [ ] Set strong `SECRET_KEY` and `QR_SECRET` (32+ random bytes each).
- [ ] Restrict CORS `allow_origins` to your domain (currently `*` for dev convenience).
- [ ] Serve over HTTPS (reverse proxy).
- [ ] Move the code judge to a container/nsjail/gVisor sandbox with no network for scale.
- [x] Security headers (CSP + nosniff + Referrer-Policy + Permissions-Policy always; X-Frame-Options + HSTS in production).
- [x] Per-request tracing (`X-Request-ID`, `X-Response-Time-ms`, structured access log).
- [x] CI gate (`ruff` lint + fresh-DB `alembic upgrade` + `pytest` + frontend typecheck/build) on every push.
- [x] Alembic migrations in place (auto-applied on startup); nightly DB backups via compose `backup` service.
