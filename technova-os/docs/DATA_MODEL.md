# Data model

Relational, normalized, portable across SQLite (dev) and PostgreSQL (prod). Foreign keys enforced
(PRAGMA on SQLite). Enums stored as strings for portability. JSON columns used only for genuinely
schemaless payloads (quiz items, test cases, rubric definitions, tech/skill arrays).

## Core entities & relationships

```
User 1───* UserSkill *───1 Skill
User 1───* LessonProgress *───1 Lesson *───1 Course *───0..1 Skill
User 1───* Submission *───1 Challenge *───0..1 Skill
User 1───* PointsLedgerEntry            (append-only; leaderboard is derived by SUM)
User 1───* UserAchievement *───1 Achievement
User 1───* Certificate                  (HMAC-signed, revocable)
User 1───* Notification
User 1───* Registration / Attendance *───1 Event
Project 1───* ProjectMember *───1 User
Project 1───* Task ; Project 1───* Review *───1 User(mentor)
Competition 1───* CompetitionEntry 1───* RubricScore *───1 User(judge)
AuditLog *───0..1 User(actor)
Resource, Announcement                  (standalone)
```

## Key design decisions

- **Points are a ledger, not a counter.** `PointsLedgerEntry` is append-only with a unique
  `dedupe_key = user:source_type:source_id`. The leaderboard and per-user totals are computed with
  `SUM(points)`. This makes scoring **auditable** and **impossible to double-count or farm**.
- **Evidence everywhere.** `UserSkill` tracks counts of lessons/quizzes/challenges/projects/teaching.
  `UserAchievement.evidence` and ledger `source_*` link every reward to the action that earned it.
- **Skill tiers are derived** from XP thresholds (`SKILL_TIER_XP`), not stored, so they can never
  drift from the underlying evidence.
- **Certificates are self-verifying** via an HMAC `signature`; verification needs no trust in the DB
  row alone, and `revoked` short-circuits verification.
- **Indexes** on hot paths: `points_ledger(user_id, created_at)`, unique constraints on all
  join tables (`user_skill`, `lesson_progress`, `attendance`, `registration`, `project_member`,
  `user_achievement`) to guarantee integrity.

## Extensibility

New modules (Robotics, IoT, Alumni, inter-school competitions…) add:
1. their own tables,
2. new event names + reactors in `engine.py`,
without touching existing modules. The event bus is the extension seam — a reactor can award points,
grant achievements, issue certificates and notify, all through existing primitives.
