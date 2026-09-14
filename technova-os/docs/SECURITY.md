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
- [ ] Add Alembic migrations; take regular DB backups (compose `backup` service does nightly).
