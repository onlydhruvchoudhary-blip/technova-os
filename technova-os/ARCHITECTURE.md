# TECHNOVA OS — Architecture & Implementation Plan

> The digital operating system of a technology club. One connected ecosystem:
> **Discover → Learn → Practice → Collaborate → Build → Compete → Showcase → Earn → Lead**

---

## 1. Guiding principle — the Ecosystem Engine

The distinguishing feature of TECHNOVA OS is **interconnection**. Rather than 20 disconnected CRUD apps,
every meaningful action emits a **domain event** onto an internal event bus. Reactors subscribe to those
events and update skills, points, achievements, certificates, notifications and the leaderboard.

```
                        ┌──────────────────────────┐
   lesson.completed ───►│                          │──► SkillXP  (skill progression)
   quiz.passed      ───►│      EVENT BUS           │──► PointsLedger (append-only, idempotent)
   challenge.solved ───►│  (emit → reactors)       │──► Achievements (evidence-linked)
   attendance.marked───►│                          │──► Certificates (verifiable)
   project.completed───►│                          │──► Notifications
   competition.scored──►│                          │──► Leaderboard (derived from ledger)
                        └──────────────────────────┘
```

This means: *complete a course → gain skill XP → skill unlocks harder challenges → solving them earns
points → points move you up the leaderboard → milestones grant achievements & certificates → your profile/
portfolio updates automatically.* Everything connects **by construction**, not by manual glue.

## 2. Technology stack & justification

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI (Python 3.13)** | Async, typed, auto OpenAPI docs, fast to build & test, great for a school-hosted service. |
| ORM/DB | **SQLAlchemy 2.0 + SQLite (dev) / PostgreSQL (prod)** | Same code both ways. SQLite runs on any school computer with zero setup; Postgres for real deployment. |
| Auth | **JWT (python-jose) + bcrypt (passlib)** | Stateless, standard, secure password hashing. |
| Frontend | **React + TypeScript + Vite** | Modern, fast HMR, type-safe, portfolio-grade. |
| Styling | Hand-rolled design system (CSS variables, dark/light) | No heavy UI deps → loads on weak hardware; full control of the "tech-org" look. |
| Tests | **pytest** (backend), integration journey tests | Covers auth, RBAC, points, leaderboard, attendance, certificates, ecosystem chain. |
| Deploy | **Docker + docker-compose**, `.env` config | internal platform → public showcase → hosted product. |

**Priorities honoured:** Reliability (append-only ledger, tests) > Security (RBAC, hashing, signed QR,
audit log, rate limits) > Maintainability (event bus, layered modules) > Performance (indexed queries,
derived leaderboard, SQLite/PG parity) > Deployability (Docker) > Scalability (stateless API, event bus
can move to a queue) > Portfolio quality.

## 3. Data model (core entities)

`User, Role` · `Skill, UserSkill` · `Course, Module, Lesson, Quiz, LessonProgress` ·
`Challenge, Submission` · `Project, ProjectMember, Task` · `Event, Attendance` ·
`Competition, CompetitionEntry, RubricScore` · `Achievement, UserAchievement` ·
`Certificate` · `PointsLedgerEntry` (append-only, source-tagged, idempotent) ·
`Notification` · `AuditLog` · `Resource` · `Announcement`.

Leaderboard is **derived** from `PointsLedgerEntry` (never a mutable counter) → no double counting,
fully auditable, and every point traces back to real evidence.

## 4. Authorization model (RBAC)

Roles, ascending: `GUEST < MEMBER < COMMITTEE < MENTOR < ADVISOR < CLUB_HEAD < SUPER_ADMIN`.
Endpoints declare a minimum role and/or ownership rule. Sensitive actions (issue certificate, award
points manually, create competitions, moderate) require elevated roles and are written to the audit log.

## 5. Anti-exploit / fairness

- **Append-only points ledger** with a unique `dedupe_key` per (user, source, source_id) → the same
  lesson/challenge/event can never be farmed twice.
- **Daily point caps** per category (learning, attendance, social) → no farming meaningless activity.
- **Signed, time-limited QR tokens** (HMAC, ~90s rotation, per-event nonce) → no forever-valid codes,
  no sharing screenshots after the fact.
- **Server-side judging** of challenges against hidden tests → scores aren't client-trusted.
- **Audit log** on every privileged mutation.
- Rate limiting on auth & submission endpoints.

## 6. Module map (progressive build)

M1 Foundation: config, DB, models, auth, RBAC, audit, health, tests. ✅
M2 Ecosystem engine: event bus, points ledger, achievements, leaderboard. ✅
M3 Academy: courses/lessons/quizzes → skill XP → progression. ✅
M4 Challenges: problems, safe judging, submissions → points. ✅
M5 Events + QR attendance (signed tokens). ✅
M6 Projects incubator + workspace + tasks + team matching. ✅
M7 Competitions + rubrics + certificates + verification. ✅
M8 Frontend: dashboard, profile/portfolio, academy, challenges, projects, leaderboard, admin, command center. ✅
M9 Deployment, docs, hardening, critic loop to ≥8.5.

## 7. Deployment path

- **Dev:** `uvicorn` + `vite dev` (proxy `/api`). SQLite file.
- **Prod:** Docker compose: API (gunicorn/uvicorn workers) + Postgres + built static frontend served by
  the API/or nginx. Secrets via env. Nightly `pg_dump` backup. Structured logging + `/api/health`.

## 8. Real-time delivery & scaling notes

The app pushes live updates over **Server-Sent Events** (SSE) on two channels: per-user
`/api/notifications/stream` and the club-wide `/api/activity/stream`. Each connection is
**bounded** (self-recycles ~2 min; the browser `EventSource` reconnects transparently) so no worker
is pinned indefinitely.

**Event-driven fan-out (implemented).** SSE delivery is **push-based via an in-process pub/sub
broker** (`app/broker.py`), *not* per-connection polling. The write path publishes once — but only
after the transaction commits: engine helpers (`record_activity()`, `notify()`) stash the message on
the SQLAlchemy session's `info` dict, and a single `after_commit` listener (registered on the
`Session` class in `database.py`) drains and publishes them; an `after_rollback` listener discards
them, so a rolled-back write is never broadcast. Each SSE generator subscribes to a topic (activity =
broadcast, notify = filtered to one `user_id`) and forwards frames as they arrive, with a 20s
keepalive comment to hold the connection warm. **DB load is now O(writes), independent of the number
of open connections.** Backpressure is bounded: each subscriber has a fixed-size queue and a slow
consumer's excess frames are dropped (the client's reconnect + REST backfill via
`/api/activity?before=` reconciles), so one stuck consumer can never block a writer.

**Remaining ceiling & scale-out path (single-process boundary).** The broker is in-memory, so it fans
out within **one** process. For a school tech club (tens to low-hundreds of concurrent members) a
single stateless service + one database is the right, low-ops choice. To run **N API workers** the
transport must move off-process — the broker's `publish()/subscribe()` interface is deliberately the
same shape as **Redis Pub/Sub** / **Postgres `LISTEN/NOTIFY`**, making that a drop-in swap. At that
point also move sessions/rate-limit counters (in-process today) to Redis. The
`_safe_activity()` SAVEPOINT wrapper and keyset-paginated feed reads are already in place, so the
migration is additive — no data-model change required.

**Load testing.** `scripts/loadtest.py` (stdlib-only, no k6/locust needed) drives a concurrent read
mix (leaderboard, activity feed, challenges, dashboard) plus concurrent SSE subscribers, and reports
throughput + **p50/p95/p99 latency**, failing (non-zero exit) above a configurable error-rate so it
can gate CI:

```
python scripts/loadtest.py --base http://localhost:8000 --users 40 --requests 20 --sse 20
```

For a formal production SLA, port the same scenarios to k6/locust against a Postgres-backed deploy.
