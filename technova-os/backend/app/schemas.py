"""Pydantic request/response schemas (input validation + typed responses)."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- auth
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: str
    bio: str = ""
    avatar_seed: str = "nova"


# ---- profile
class SkillOut(BaseModel):
    key: str
    name: str
    icon: str
    category: str
    xp: int
    tier: str
    tier_index: int
    lessons: int
    challenges: int
    projects: int


class AchievementOut(BaseModel):
    key: str
    name: str
    description: str
    icon: str
    points: int = 0
    rarity: str = "Common"
    earned_at: dt.datetime | None = None


class ProfileOut(BaseModel):
    user: UserOut
    points: int
    rank: int | None
    skills: list[SkillOut]
    achievements: list[AchievementOut]
    projects: list[dict]
    certificates: list[dict]
    stats: dict


# ---- academy
class LessonComplete(BaseModel):
    quiz_answers: list[int] | None = None


# ---- challenges
class SubmissionIn(BaseModel):
    code: str = Field(min_length=1, max_length=20000)


class ChallengeCreate(BaseModel):
    slug: str
    title: str
    statement: str
    difficulty: str = "Easy"
    skill_key: str | None = None
    points: int = 50
    function_name: str = "solve"
    starter_code: str = ""
    sample_tests: list = []
    hidden_tests: list = []
    is_weekly: bool = False
    weekly_kind: str = ""


# ---- projects
class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    problem: str = ""
    solution: str = ""
    description: str = ""
    required_skills: list[str] = []
    team_size: int = 4
    tech: list[str] = []


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "Backlog"
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assignee_id: int | None = None


class ReviewIn(BaseModel):
    stage: str = ""
    score: int = 0
    feedback: str


# ---- events
class EventCreate(BaseModel):
    title: str
    description: str = ""
    kind: str = "Workshop"
    location: str = ""
    starts_at: dt.datetime
    ends_at: dt.datetime | None = None
    capacity: int = 100
    is_public: bool = True


class AttendanceIn(BaseModel):
    token: str


# ---- competitions
class CompetitionCreate(BaseModel):
    title: str
    description: str = ""
    kind: str = "Project"
    rubric: list = []


class EntryIn(BaseModel):
    team_name: str = ""
    title: str = ""
    summary: str = ""
    project_id: int | None = None


class ScoreIn(BaseModel):
    scores: dict
    comment: str = ""


# ---- misc
class AnnouncementIn(BaseModel):
    title: str
    body: str = ""
    pinned: bool = False


class RoleUpdate(BaseModel):
    role: str
