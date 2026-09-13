from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_answer_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    answers = relationship("Answer", back_populates="user")


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("provider_message_id", name="uq_provider_message"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_message_id: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    answer_text: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    correct: Mapped[bool] = mapped_column(default=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="answers")
    topic = relationship("Topic")


class DailyLesson(Base):
    """Curriculum-backed lesson tables used by the WhatsApp learning flow."""
    __tablename__ = "daily_lessons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    questions = relationship("LessonQuestion", cascade="all, delete-orphan", back_populates="lesson")


class LessonQuestion(Base):
    __tablename__ = "lesson_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("daily_lessons.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    reference_answer: Mapped[str] = mapped_column(Text)
    lesson = relationship("DailyLesson", back_populates="questions")
    __table_args__ = (UniqueConstraint("lesson_id", "number"),)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("lesson_questions.id"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    correctness: Mapped[int] = mapped_column(Integer)
    tradeoff_reasoning: Mapped[int] = mapped_column(Integer)
    limitation_awareness: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "question_id"),)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
