import re
from datetime import date, timedelta

from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .models import Answer, Topic, User
from .providers import AIProvider, GeneratedTopic
from .schemas import WebhookMessage


def parse_answer(text: str) -> str:
    match = re.match(r"^\s*Q1\s*:\s*(.+?)\s*$", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Answer must use the format Q1: <your answer>")
    return match.group(1).strip()


def parse_webhook_payload(payload: dict) -> WebhookMessage:
    """Normalize a direct payload or the nested shape sent by WhatsApp Cloud API."""
    if {"message_id", "phone_number", "text"} <= payload.keys():
        return WebhookMessage(**payload)
    try:
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        contact = payload["entry"][0]["changes"][0]["value"].get("contacts", [{}])[0]
        text = message["text"]["body"]
        return WebhookMessage(
            message_id=message["id"],
            phone_number=message["from"],
            text=text,
            display_name=contact.get("profile", {}).get("name"),
        )
    except (KeyError, IndexError, TypeError, ValidationError) as exc:
        raise ValueError("Unsupported webhook payload") from exc


def generate_topic(db: Session, provider: AIProvider, day: date | None = None) -> Topic:
    day = day or date.today()
    existing = db.scalar(select(Topic).where(Topic.topic_date == day))
    if existing:
        return existing
    generated: GeneratedTopic = provider.generate_topic(day)
    topic = Topic(topic_date=day, question=generated.question, expected_answer=generated.expected_answer)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


def update_streak(user: User, answered_on: date) -> None:
    if user.last_answer_date == answered_on:
        return
    if user.last_answer_date == answered_on - timedelta(days=1):
        user.current_streak = (user.current_streak or 0) + 1
    else:
        user.current_streak = 1
    user.longest_streak = max(user.longest_streak or 0, user.current_streak)
    user.last_answer_date = answered_on


def leaderboard(db: Session, limit: int = 10) -> list[User]:
    return list(db.scalars(select(User).order_by(desc(User.current_streak), desc(User.longest_streak)).limit(limit)))
