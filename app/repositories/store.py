from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import DailyLesson, LessonQuestion, Submission
from ..providers import GeneratedLesson


def get_lesson(db: Session, lesson_date: date) -> DailyLesson | None:
    return db.scalar(select(DailyLesson).where(DailyLesson.lesson_date == lesson_date))


def create_lesson(db: Session, lesson_date: date, draft: GeneratedLesson) -> DailyLesson:
    existing = get_lesson(db, lesson_date)
    if existing:
        return existing
    lesson = DailyLesson(lesson_date=lesson_date, topic=draft.topic, content=draft.content)
    db.add(lesson)
    db.flush()
    for number, question in enumerate(draft.questions, 1):
        db.add(LessonQuestion(lesson_id=lesson.id, number=number,
                              prompt=question.prompt, reference_answer=question.reference_answer))
    db.commit()
    return get_lesson(db, lesson_date)  # type: ignore[return-value]


def get_question(db: Session, lesson_id: int, number: int) -> LessonQuestion | None:
    return db.scalar(select(LessonQuestion).where(
        LessonQuestion.lesson_id == lesson_id, LessonQuestion.number == number))


def save_submission(db: Session, submission: Submission) -> Submission:
    previous = db.scalar(select(Submission).where(
        Submission.user_id == submission.user_id, Submission.question_id == submission.question_id))
    if previous:
        for field in ("answer", "correctness", "tradeoff_reasoning", "limitation_awareness", "total_score", "feedback"):
            setattr(previous, field, getattr(submission, field))
        result = previous
    else:
        db.add(submission)
        result = submission
    db.commit()
    db.refresh(result)
    return result


def daily_score(db: Session, user_id: int, lesson_id: int) -> tuple[int, int]:
    total, count = db.execute(
        select(func.coalesce(func.sum(Submission.total_score), 0), func.count(Submission.id))
        .join(LessonQuestion, LessonQuestion.id == Submission.question_id)
        .where(Submission.user_id == user_id, LessonQuestion.lesson_id == lesson_id)
    ).one()
    return int(total), int(count)
