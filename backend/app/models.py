"""TECHNOVA OS relational data model.

Design notes:
- Points are an APPEND-ONLY ledger (PointsLedgerEntry). The leaderboard is derived by summing
  the ledger, never a mutable counter. Every entry has a unique dedupe_key => idempotent, no farming.
- Achievements and certificates link back to real evidence (source_type/source_id).
- Enums are stored as strings for portability across SQLite/Postgres.
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# --------------------------------------------------------------------------- roles
class Role(str, enum.Enum):
    GUEST = "GUEST"
    MEMBER = "MEMBER"
    COMMITTEE = "COMMITTEE"
    MENTOR = "MENTOR"
    ADVISOR = "ADVISOR"
    CLUB_HEAD = "CLUB_HEAD"
    SUPER_ADMIN = "SUPER_ADMIN"


ROLE_RANK = {
    Role.GUEST: 0, Role.MEMBER: 1, Role.COMMITTEE: 2, Role.MENTOR: 3,
    Role.ADVISOR: 4, Role.CLUB_HEAD: 5, Role.SUPER_ADMIN: 6,
}


# --------------------------------------------------------------------------- users
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.MEMBER.value, index=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    avatar_seed: Mapped[str] = mapped_column(String(40), default="nova")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hidden_from_leaderboard: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    skills: Mapped[list[UserSkill]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ledger: Mapped[list[PointsLedgerEntry]] = relationship(back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[list[UserAchievement]] = relationship(back_populates="user", cascade="all, delete-orphan")


# --------------------------------------------------------------------------- skills
class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # e.g. "python"
    name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(50), default="Programming")
    icon: Mapped[str] = mapped_column(String(20), default="⚙️")


SKILL_TIERS = ["None", "Beginner", "Intermediate", "Advanced", "Mentor"]
# XP thresholds to reach each tier index
SKILL_TIER_XP = [0, 100, 300, 700, 1500]


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    # evidence counters (what earned the XP) -> makes progression meaningful, not click-to-complete
    lessons: Mapped[int] = mapped_column(Integer, default=0)
    quizzes: Mapped[int] = mapped_column(Integer, default=0)
    challenges: Mapped[int] = mapped_column(Integer, default=0)
    projects: Mapped[int] = mapped_column(Integer, default=0)
    taught: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()

    def tier_index(self) -> int:
        idx = 0
        for i, t in enumerate(SKILL_TIER_XP):
            if self.xp >= t:
                idx = i
        return idx

    def tier(self) -> str:
        return SKILL_TIERS[self.tier_index()]


# --------------------------------------------------------------------------- academy
class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="Programming")
    difficulty: Mapped[str] = mapped_column(String(20), default="Beginner")
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    lessons: Mapped[list[Lesson]] = relationship(back_populates="course", cascade="all, delete-orphan",
                                                 order_by="Lesson.order")
    skill: Mapped[Skill | None] = relationship()


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    order: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(20), default="article")  # article|video|quiz
    content: Mapped[str] = mapped_column(Text, default="")            # markdown
    video_url: Mapped[str] = mapped_column(String(300), default="")
    xp: Mapped[int] = mapped_column(Integer, default=20)
    # quiz payload (list of {q, options[], answer_index}) if kind == quiz
    quiz: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pass_score: Mapped[int] = mapped_column(Integer, default=70)     # percent to pass a quiz

    course: Mapped[Course] = relationship(back_populates="lessons")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[int] = mapped_column(Integer, default=0)  # quiz score %
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------- challenges
class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    statement: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="Easy")  # Easy|Medium|Hard
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=50)
    function_name: Mapped[str] = mapped_column(String(80), default="solve")
    starter_code: Mapped[str] = mapped_column(Text, default="")
    # test cases: [{"args": [...], "expected": ...}], sample ones flagged
    sample_tests: Mapped[list] = mapped_column(JSON, default=list)
    hidden_tests: Mapped[list] = mapped_column(JSON, default=list)
    is_weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    weekly_kind: Mapped[str] = mapped_column(String(30), default="")  # Coding|AI|Design|Hardware...
    active_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    tests_passed: Mapped[int] = mapped_column(Integer, default=0)
    tests_total: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- projects
class ProjectState(str, enum.Enum):
    IDEA = "IDEA"
    PROPOSED = "PROPOSED"
    TEAM_FORMING = "TEAM_FORMING"
    PLANNING = "PLANNING"
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    DEMO = "DEMO"
    COMPLETED = "COMPLETED"
    SHOWCASE = "SHOWCASE"


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    problem: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list] = mapped_column(JSON, default=list)  # list of skill keys
    team_size: Mapped[int] = mapped_column(Integer, default=4)
    state: Mapped[str] = mapped_column(String(20), default=ProjectState.IDEA.value, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mentor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(300), default="")
    demo_url: Mapped[str] = mapped_column(String(300), default="")
    tech: Mapped[list] = mapped_column(JSON, default=list)
    showcase: Mapped[bool] = mapped_column(Boolean, default=False)  # public showcase
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list[ProjectMember]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship(back_populates="project", cascade="all, delete-orphan")
    reviews: Mapped[list[Review]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(40), default="Contributor")
    status: Mapped[str] = mapped_column(String(20), default="member")  # requested|member
    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Backlog")  # Backlog|To Do|In Progress|Review|Testing|Done
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    project: Mapped[Project] = relationship(back_populates="tasks")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stage: Mapped[str] = mapped_column(String(20), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[Project] = relationship(back_populates="reviews")


# --------------------------------------------------------------------------- events + attendance
class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(30), default="Workshop")
    location: Mapped[str] = mapped_column(String(160), default="")
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=100)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    attendance_open: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    registrations: Mapped[list[Registration]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_registration"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event: Mapped[Event] = relationship(back_populates="registrations")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_attendance"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    marked_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- competitions
class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(30), default="Project")  # Coding|Hackathon|Quiz|Project|Team
    starts_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # rubric: [{"name": "Innovation", "max": 20}, ...]
    rubric: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|judging|closed
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    entries: Mapped[list[CompetitionEntry]] = relationship(back_populates="competition", cascade="all, delete-orphan")


class CompetitionEntry(Base):
    __tablename__ = "competition_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    team_name: Mapped[str] = mapped_column(String(120), default="")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition: Mapped[Competition] = relationship(back_populates="entries")
    scores: Mapped[list[RubricScore]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class RubricScore(Base):
    __tablename__ = "rubric_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("competition_entries.id", ondelete="CASCADE"), index=True)
    judge_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scores: Mapped[dict] = mapped_column(JSON, default=dict)  # {criterion: value}
    comment: Mapped[str] = mapped_column(Text, default="")
    total: Mapped[float] = mapped_column(Float, default=0.0)
    entry: Mapped[CompetitionEntry] = relationship(back_populates="scores")


# --------------------------------------------------------------------------- achievements & certificates
# Rarity tiers, ordered from most common to rarest.
ACHIEVEMENT_RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(255), default="")
    icon: Mapped[str] = mapped_column(String(20), default="🏆")
    points: Mapped[int] = mapped_column(Integer, default=0)
    rarity: Mapped[str] = mapped_column(String(20), default="Common", index=True)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"), index=True)
    evidence: Mapped[str] = mapped_column(String(120), default="")  # source_type:source_id
    earned_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship(back_populates="achievements")
    achievement: Mapped[Achievement] = relationship()


class Certificate(Base):
    __tablename__ = "certificates"
    id: Mapped[int] = mapped_column(primary_key=True)
    cert_uid: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # Course|Competition Winner|Participation|Project|Leadership
    title: Mapped[str] = mapped_column(String(200))
    context: Mapped[str] = mapped_column(String(200), default="")  # event/project/competition name
    issuer: Mapped[str] = mapped_column(String(120), default="TECHNOVA")
    issued_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    signature: Mapped[str] = mapped_column(String(80), default="")  # HMAC for verification
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


# --------------------------------------------------------------------------- points ledger (append-only)
class PointsLedgerEntry(Base):
    __tablename__ = "points_ledger"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_points_dedupe"),
        Index("ix_points_user_created", "user_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    points: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20), default="learning")  # learning|challenge|attendance|project|social|competition
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(200), default="")
    dedupe_key: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship(back_populates="ledger")


# --------------------------------------------------------------------------- notifications, resources, announcements, audit
class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="info")
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(400), default="")
    link: Mapped[str] = mapped_column(String(200), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(400))
    kind: Mapped[str] = mapped_column(String(30), default="Article")
    technology: Mapped[str] = mapped_column(String(50), default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="Beginner")
    topic: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(Text, default="")


class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --------------------------------------------------------------------------- activity feed
# A public, club-wide stream of noteworthy events (badges earned, code graded, rewards redeemed,
# projects shipped, votes cast). Distinct from AuditLog (private/admin, security-oriented) and
# Notification (per-user, private): ActivityEvent is the social "pulse" of the club, readable by
# any member and streamed live over SSE. Only celebratory, non-sensitive events are recorded here.
class ActivityEvent(Base):
    __tablename__ = "activity_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)   # e.g. achievement, grading, redeem
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    actor_name: Mapped[str] = mapped_column(String(120), default="")  # denormalised for cheap reads
    icon: Mapped[str] = mapped_column(String(8), default="✨")
    text: Mapped[str] = mapped_column(String(240), default="")   # human-readable one-liner
    link: Mapped[str] = mapped_column(String(160), default="")
    points: Mapped[int] = mapped_column(default=0)               # optional points delta to show
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True)


# --------------------------------------------------------------------------- governance
# Proposals let contributing members vote on club decisions and project funding.
# Voting power is points-weighted (see app/governance.py) so real contribution earns real say,
# but the weight is capped by membership tier so a single big earner can't dominate.
class Proposal(Base):
    __tablename__ = "proposals"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(20), default="decision", index=True)  # decision | funding
    # For funding proposals: the amount requested and the project it funds (optional).
    amount: Mapped[int] = mapped_column(Integer, default=0)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    # Options members choose between, e.g. ["Approve", "Reject", "Abstain"].
    options: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | closed
    # Minimum membership-tier index required to vote (0 = anyone eligible). Snapshot of the rule.
    min_tier: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closes_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(200), default="")  # filled when closed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    votes: Mapped[list[Vote]] = relationship(back_populates="proposal", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("proposal_id", "user_id", name="uq_vote_once"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    choice: Mapped[str] = mapped_column(String(120))
    # Snapshot of the voter's weight + points at the moment they voted (audit-friendly, immutable).
    weight: Mapped[int] = mapped_column(Integer, default=1)
    points_at_vote: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    proposal: Mapped[Proposal] = relationship(back_populates="votes")


# --------------------------------------------------------------------------- rewards store
# Points are spent by writing NEGATIVE ledger entries (category "redemption"), so the same
# append-only, summed-balance model that powers the leaderboard also governs the wallet — there is
# no separate mutable balance column to tamper with. Stock + balance are validated server-side.
class Reward(Base):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    cost: Mapped[int] = mapped_column(Integer, default=0)                 # points price
    kind: Mapped[str] = mapped_column(String(16), default="digital")      # digital | physical | perk
    icon: Mapped[str] = mapped_column(String(16), default="🎁")
    stock: Mapped[int] = mapped_column(Integer, default=-1)               # -1 = unlimited
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    redemptions: Mapped[list[Redemption]] = relationship(back_populates="reward", cascade="all, delete-orphan")


class Redemption(Base):
    __tablename__ = "redemptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cost_at_claim: Mapped[int] = mapped_column(Integer, default=0)        # snapshot price paid
    status: Mapped[str] = mapped_column(String(12), default="claimed", index=True)  # claimed|fulfilled|cancelled
    # Ledger entry that debited the points — the audit link that makes a refund exact & traceable.
    ledger_dedupe: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reward: Mapped[Reward] = relationship(back_populates="redemptions")


# --------------------------------------------------------------------------- grading & peer review
# A CodeReviewSubmission is a piece of code submitted for automated checks + human peer review.
# Automated results are computed server-side (sandboxed); peer reviews score against a rubric and,
# once enough reviews land, the author is awarded points through the ledger.
class CodeReviewSubmission(Base):
    __tablename__ = "code_review_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    language: Mapped[str] = mapped_column(String(24), default="python")
    code: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # Automated analysis snapshot: {score, issues:[...], lines, ...}
    auto_report: Mapped[dict] = mapped_column(JSON, default=dict)
    auto_score: Mapped[int] = mapped_column(Integer, default=0)          # 0-100
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open|graded
    review_goal: Mapped[int] = mapped_column(Integer, default=2)         # reviews needed to finalise
    final_score: Mapped[float] = mapped_column(Float, default=0.0)       # avg peer score when graded
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reviews: Mapped[list[PeerReview]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class PeerReview(Base):
    __tablename__ = "peer_reviews"
    __table_args__ = (UniqueConstraint("submission_id", "reviewer_id", name="uq_review_once"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("code_review_submissions.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Rubric scores 1-5 each.
    correctness: Mapped[int] = mapped_column(Integer, default=3)
    readability: Mapped[int] = mapped_column(Integer, default=3)
    efficiency: Mapped[int] = mapped_column(Integer, default=3)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submission: Mapped[CodeReviewSubmission] = relationship(back_populates="reviews")
