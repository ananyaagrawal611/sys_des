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
