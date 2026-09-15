"""Automated Grading & Peer-Review engine.

Flow
  1. A member submits code -> automated static analysis runs immediately (sandboxed blocklist +
     structural heuristics), producing an auto_score and an issue list.
  2. The submission enters a peer-review queue. Other members score it against a 3-axis rubric
     (correctness / readability / efficiency, 1-5 each) and leave a comment.
  3. Once `review_goal` reviews land, the submission is finalised: final_score = average peer score,
     and the AUTHOR earns points (scaled by quality) plus each REVIEWER earns a small social award.

Anti-abuse
  - You cannot review your own submission, and you can review a given submission only once.
  - Author/reviewer points flow through the same capped, idempotent ledger as everything else.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import engine
from ..database import get_db
from ..judge import analyze_code
from ..models import AuditLog, CodeReviewSubmission, PeerReview, User
from ..schemas import CodeSubmissionIn, PeerReviewIn
from ..security import get_current_user

router = APIRouter(prefix="/api/grading", tags=["grading"])

REVIEW_AXES = ("correctness", "readability", "efficiency")


def _submission_dict(db: Session, s: CodeReviewSubmission, user: User | None = None,
                     include_code: bool = False) -> dict:
    author = db.get(User, s.author_id)
    reviews = s.reviews
    d = {
        "id": s.id,
        "title": s.title,
        "language": s.language,
        "description": s.description,
        "author": {"id": author.id, "name": author.name, "avatar_seed": author.avatar_seed} if author else None,
        "auto_score": s.auto_score,
        "auto_report": s.auto_report,
        "status": s.status,
        "review_goal": s.review_goal,
        "review_count": len(reviews),
        "final_score": round(s.final_score, 2),
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
    if include_code:
        d["code"] = s.code
        d["reviews"] = [{
            "reviewer": (db.get(User, r.reviewer_id).name if db.get(User, r.reviewer_id) else "?"),
            "correctness": r.correctness, "readability": r.readability, "efficiency": r.efficiency,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reviews]
    if user is not None:
        d["is_author"] = s.author_id == user.id
        d["has_reviewed"] = any(r.reviewer_id == user.id for r in reviews)
        d["can_review"] = (s.status == "open" and s.author_id != user.id
                           and not d["has_reviewed"])
    return d


@router.get("/submissions")
def list_submissions(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                     status: str | None = None, mine: bool = False):
    q = select(CodeReviewSubmission)
    if status:
        q = q.where(CodeReviewSubmission.status == status)
    if mine:
        q = q.where(CodeReviewSubmission.author_id == user.id)
    rows = db.execute(q.order_by(CodeReviewSubmission.created_at.desc())).scalars().all()
    return [_submission_dict(db, s, user) for s in rows]


@router.get("/submissions/{sid}")
def get_submission(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.get(CodeReviewSubmission, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _submission_dict(db, s, user, include_code=True)


@router.post("/submissions", status_code=201)
def create_submission(data: CodeSubmissionIn, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    report = analyze_code(data.code, data.language)
    s = CodeReviewSubmission(
        author_id=user.id, title=data.title.strip(), language=data.language,
        code=data.code, description=data.description.strip(),
        auto_report=report, auto_score=report["score"], status="open",
    )
    db.add(s)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="grading.submit", target=f"submission:{s.id}",
                    detail=f"auto {report['score']}/100"))
    db.commit()
    return _submission_dict(db, s, user, include_code=True)


@router.post("/submissions/{sid}/review")
def submit_review(sid: int, data: PeerReviewIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    s = db.get(CodeReviewSubmission, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    if s.status != "open":
        raise HTTPException(status_code=400, detail="This submission is already graded")
    if s.author_id == user.id:
        raise HTTPException(status_code=403, detail="You cannot review your own submission")
    if db.execute(select(PeerReview).where(
            PeerReview.submission_id == s.id, PeerReview.reviewer_id == user.id)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already reviewed this submission")

    review = PeerReview(submission_id=s.id, reviewer_id=user.id,
                        correctness=data.correctness, readability=data.readability,
                        efficiency=data.efficiency, comment=data.comment.strip())
    db.add(review)
    db.flush()
    db.refresh(s)  # s.reviews now includes the new review exactly once

    # reward the reviewer a small (capped) social award for constructive review work
    engine.award_points(db, user.id, 15, "social", "peer_review", f"{s.id}:{user.id}",
                        f"Reviewed submission #{s.id}")
    engine.notify(db, s.author_id, "grading", "New review on your submission",
                  f"{user.name} reviewed “{s.title}”.", link=f"/grading/{s.id}")

    # finalise once the review goal is met
    reviews = list(s.reviews)
    if len(reviews) >= s.review_goal and s.status == "open":
        def avg(field: str) -> float:
            return sum(getattr(r, field) for r in reviews) / len(reviews)
        # rubric mean on a 1-5 scale -> 0-100
        mean_5 = sum(avg(a) for a in REVIEW_AXES) / len(REVIEW_AXES)
        s.final_score = mean_5 * 20
        s.status = "graded"
        # author points: scale peer result into a fair award (max 120)
        award = int(round(s.final_score / 100 * 120))
        engine.award_points(db, s.author_id, award, "learning", "code_review", str(s.id),
                            f"Peer-reviewed submission graded {s.final_score:.0f}/100")
        engine.notify(db, s.author_id, "grading", "Your submission was graded 🎓",
                      f"“{s.title}” scored {s.final_score:.0f}/100 (+{award} pts).",
                      link=f"/grading/{s.id}")
        db.add(AuditLog(actor_id=user.id, action="grading.finalise",
                        target=f"submission:{s.id}", detail=f"{s.final_score:.0f}/100"))
        engine._safe_activity(db, kind="grading", actor_id=s.author_id, icon="🎓",
                              text=f"had “{s.title}” peer-graded {s.final_score:.0f}/100",
                              link=f"/grading/{s.id}", points=award)

    db.commit()
    return _submission_dict(db, s, user, include_code=True)
