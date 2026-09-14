"""TECHNOVA Academy: learning paths, lessons, quizzes, progression -> emits ecosystem events."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import engine
from ..database import get_db
from ..models import Course, Lesson, LessonProgress, Skill, User
from ..schemas import LessonComplete
from ..security import get_current_user

router = APIRouter(prefix="/api/academy", tags=["academy"])


@router.get("/courses")
def list_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                 category: str | None = None):
    q = select(Course).where(Course.published == True)  # noqa
    if category:
        q = q.where(Course.category == category)
    courses = db.execute(q.order_by(Course.order, Course.title)).scalars().all()
    # completion per course for this user
    out = []
    for c in courses:
        total = len(c.lessons)
        done = db.execute(
            select(func.count(LessonProgress.id))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(Lesson.course_id == c.id, LessonProgress.user_id == user.id,
                   LessonProgress.completed == True)  # noqa
        ).scalar_one()
        out.append({
            "id": c.id, "slug": c.slug, "title": c.title, "description": c.description,
            "category": c.category, "difficulty": c.difficulty,
            "lessons": total, "completed": int(done),
            "progress": round(100 * done / total) if total else 0,
            "skill_key": c.skill.key if c.skill else None,
        })
    return out


@router.get("/courses/{slug}")
def get_course(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.execute(select(Course).where(Course.slug == slug)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    progress = {p.lesson_id: p for p in db.execute(
        select(LessonProgress).where(LessonProgress.user_id == user.id)
    ).scalars().all()}
    lessons = []
    prev_done = True  # first lesson always unlocked
    for i, lesson in enumerate(c.lessons):
        p = progress.get(lesson.id)
        done = bool(p and p.completed)
        unlocked = i == 0 or prev_done  # progression gate
        lessons.append({
            "id": lesson.id, "title": lesson.title, "order": lesson.order, "kind": lesson.kind,
            "xp": lesson.xp, "completed": done, "score": p.score if p else 0,
            "unlocked": unlocked, "has_quiz": bool(lesson.quiz),
        })
        prev_done = done
    return {
        "id": c.id, "slug": c.slug, "title": c.title, "description": c.description,
        "category": c.category, "difficulty": c.difficulty,
        "skill_key": c.skill.key if c.skill else None,
        "lessons": lessons,
    }


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    # gate: previous lesson must be complete
    siblings = lesson.course.lessons
    idx = [s.id for s in siblings].index(lesson.id)
    if idx > 0:
        prev = siblings[idx - 1]
        pp = db.execute(select(LessonProgress).where(
            LessonProgress.user_id == user.id, LessonProgress.lesson_id == prev.id)).scalar_one_or_none()
        if not (pp and pp.completed):
            raise HTTPException(status_code=403, detail="Complete the previous lesson first")
    p = db.execute(select(LessonProgress).where(
        LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id)).scalar_one_or_none()
    quiz_public = None
    if lesson.quiz:
        # never expose answer_index to the client
        quiz_public = [{"q": item["q"], "options": item["options"]} for item in lesson.quiz.get("items", [])]
    return {
        "id": lesson.id, "title": lesson.title, "kind": lesson.kind, "content": lesson.content,
        "video_url": lesson.video_url, "xp": lesson.xp, "quiz": quiz_public,
        "pass_score": lesson.pass_score, "course_slug": lesson.course.slug,
        "completed": bool(p and p.completed), "score": p.score if p else 0,
        "skill_key": lesson.course.skill.key if lesson.course.skill else None,
    }


@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, data: LessonComplete,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    skill_key = lesson.course.skill.key if lesson.course.skill else None

    score = 100
    passed = True
    if lesson.quiz:
        items = lesson.quiz.get("items", [])
        answers = data.quiz_answers or []
        if len(answers) != len(items):
            raise HTTPException(status_code=400, detail="Answer every question")
        correct = sum(1 for i, item in enumerate(items) if answers[i] == item["answer_index"])
        score = round(100 * correct / len(items)) if items else 100
        passed = score >= lesson.pass_score
        if not passed:
            return {"passed": False, "score": score,
                    "message": f"Scored {score}%. Need {lesson.pass_score}% to pass. Try again."}

    p = db.execute(select(LessonProgress).where(
        LessonProgress.user_id == user.id, LessonProgress.lesson_id == lesson.id)).scalar_one_or_none()
    already = bool(p and p.completed)
    if not p:
        p = LessonProgress(user_id=user.id, lesson_id=lesson.id)
        db.add(p)
    p.completed = True
    p.score = score
    p.completed_at = engine.utcnow()
    db.flush()

    effects = []
    if not already:
        effects = engine.emit(db, engine.Event(
            "lesson.completed", user.id,
            {"lesson_id": lesson.id, "title": lesson.title, "xp": lesson.xp, "skill_key": skill_key}))
        if lesson.quiz and passed:
            engine.emit(db, engine.Event(
                "quiz.passed", user.id,
                {"lesson_id": lesson.id, "score": score, "skill_key": skill_key}))

        # course completion?
        total = len(lesson.course.lessons)
        done = db.execute(
            select(func.count(LessonProgress.id)).join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(Lesson.course_id == lesson.course_id, LessonProgress.user_id == user.id,
                   LessonProgress.completed == True)  # noqa
        ).scalar_one()
        if done >= total:
            engine.emit(db, engine.Event("course.completed", user.id,
                                         {"course_id": lesson.course_id, "title": lesson.course.title}))
    db.commit()
    return {"passed": True, "score": score, "already_completed": already, "effects": effects}


@router.get("/skills")
def all_skills(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    skills = db.execute(select(Skill).order_by(Skill.category, Skill.name)).scalars().all()
    return [{"key": s.key, "name": s.name, "icon": s.icon, "category": s.category} for s in skills]
