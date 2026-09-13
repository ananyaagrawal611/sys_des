from datetime import date

from pydantic import BaseModel, Field


class TopicResponse(BaseModel):
    id: int
    topic_date: date
    question: str
    expected_answer: str | None = None


class WebhookMessage(BaseModel):
    message_id: str = Field(min_length=1)
    phone_number: str = Field(min_length=1)
    text: str = Field(min_length=1)
    display_name: str | None = None


class AnswerResponse(BaseModel):
    status: str
    score: float | None = None
    correct: bool | None = None
    current_streak: int | None = None
    feedback: str | None = None


class LeaderboardEntry(BaseModel):
    phone_number: str
    display_name: str | None
    current_streak: int
    longest_streak: int
