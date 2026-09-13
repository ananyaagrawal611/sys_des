import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Submission, User, WebhookEvent
from .providers import get_ai_provider, get_messaging_provider
from .repositories import store
from .services import update_streak


def local_today() -> date:
    try:
        zone = ZoneInfo(get_settings().timezone)
    except ZoneInfoNotFoundError:
        # Windows installations may not ship the IANA database; UTC keeps
        # local development deterministic until tzdata is installed.
        zone = timezone.utc
    return datetime.now(zone).date()


def ensure_users(db: Session) -> None:
    settings = get_settings()
    for name, phone in ((settings.user_1_name, settings.user_1_phone), (settings.user_2_name, settings.user_2_phone)):
        user = db.scalar(select(User).where(User.phone_number == phone))
        if user:
            user.display_name = name
        else:
            db.add(User(phone_number=phone, display_name=name))
    db.commit()


def ensure_today_lesson(db: Session):
    today = local_today()
    lesson = store.get_lesson(db, today)
    if lesson:
        return lesson
    epoch = date(2026, 1, 1)
    return store.create_lesson(db, today, get_ai_provider().generate_lesson((today - epoch).days))


def format_lesson(lesson) -> str:
    questions = "\n\n".join(f"Q{q.number}. {q.prompt}" for q in lesson.questions)
    return f"🧠 System Design Bite: {lesson.topic}\n\n{lesson.content}\n\nTrade-off questions:\n{questions}\n\nReply with A1: your answer. Use STATUS for today's scores."


def shared_status(db: Session, lesson) -> str:
    lines = [f"📊 Today: {lesson.topic}"]
    for user in db.scalars(select(User).order_by(User.id)):
        score, solved = store.daily_score(db, user.id, lesson.id)
        lines.append(f"{user.display_name}: {solved}/{len(lesson.questions)} answered, {score} points, 🔥 {user.current_streak}")
    return "\n".join(lines)


def handle_message(db: Session, phone: str, text: str) -> str:
    ensure_users(db)
    user = db.scalar(select(User).where(User.phone_number == phone))
    if not user:
        return "This phone number is not enrolled."
    lesson = ensure_today_lesson(db)
    command = text.strip()
    if command.upper() == "STATUS":
        return shared_status(db, lesson)
    if command.upper() == "HELP":
        return "Reply with A1: ..., A2: ..., or STATUS."
    match = re.match(r"^A(\d+)\s*:\s*(.+)$", command, re.IGNORECASE | re.DOTALL)
    if not match:
        return "I could not parse that. Reply like A1: your explanation, or send STATUS."
    number, answer = int(match.group(1)), match.group(2).strip()
    question = store.get_question(db, lesson.id, number)
    if not question:
        return f"Today's lesson has questions 1 to {len(lesson.questions)}."
    grade = get_ai_provider().grade_answer(question.prompt, question.reference_answer, answer)
    store.save_submission(db, Submission(user_id=user.id, question_id=question.id, answer=answer,
        correctness=grade.correctness, tradeoff_reasoning=grade.tradeoff_reasoning,
        limitation_awareness=grade.limitation_awareness, total_score=grade.total, feedback=grade.feedback))
    update_streak(user, local_today())
    db.commit()
    status = shared_status(db, lesson)
    return f"✅ {user.display_name}, Q{number}: {grade.total}/6\n{grade.feedback}\n\n{status}"


def record_webhook_event(db: Session, message_id: str) -> bool:
    if db.scalar(select(WebhookEvent).where(WebhookEvent.provider_message_id == message_id)):
        return False
    db.add(WebhookEvent(provider_message_id=message_id))
    try:
        db.commit()
    except IntegrityError:
        # A concurrent delivery won the unique constraint; treat it as a duplicate.
        db.rollback()
        return False
    return True
