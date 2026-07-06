from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _get_owned_schedule_event(quiz: models.Quiz, user: models.User):
    for event in quiz.subtopic.schedule_events:
        if getattr(event.plan, "user_id", None) == user.id:
            return event
    return None


@router.get("/{quiz_id}", response_model=schemas.QuizOut)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quiz = (
        db.query(models.Quiz)
        .options(
            joinedload(models.Quiz.subtopic)
            .joinedload(models.Subtopic.schedule_events)
            .joinedload(models.ScheduleEvent.plan),
        )
        .filter(models.Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    owned = any(event.plan.user_id == current_user.id for event in quiz.subtopic.schedule_events)
    if not owned:
        raise HTTPException(status_code=403, detail="Not authorized for this quiz")

    # Strip correct_answer before sending to the client
    public_questions = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz.questions_json
    ]

    return schemas.QuizOut(
        quiz_id=quiz.id,
        subtopic_title=quiz.subtopic.title,
        questions=public_questions,
        pass_threshold=quiz.pass_threshold,
    )


@router.post("/{quiz_id}/submit", response_model=schemas.QuizSubmitResponse)
def submit_quiz(
    quiz_id: int,
    payload: schemas.QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quiz = (
        db.query(models.Quiz)
        .options(
            joinedload(models.Quiz.subtopic)
            .joinedload(models.Subtopic.schedule_events)
            .joinedload(models.ScheduleEvent.plan),
        )
        .filter(models.Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    owned_event = _get_owned_schedule_event(quiz, current_user)
    if owned_event is None:
        raise HTTPException(status_code=403, detail="Not authorized for this quiz")

    questions = quiz.questions_json
    if len(payload.answers) != len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(questions)} answers, got {len(payload.answers)}",
        )

    correct_count = sum(
        1 for given, q in zip(payload.answers, questions)
        if given == q.get("correct_answer")
    )
    score_percent = round((correct_count / len(questions)) * 100, 2)
    passed = score_percent >= quiz.pass_threshold

    if passed:
        owned_event.status = models.ScheduleStatus.DONE
        db.add(owned_event)
        db.commit()

    return schemas.QuizSubmitResponse(
        score_percent=score_percent,
        passed=passed,
        schedule_event_status=owned_event.status.value,
    )
