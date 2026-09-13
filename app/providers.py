from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Protocol
import httpx

from .config import get_settings


@dataclass(frozen=True)
class GeneratedTopic:
    question: str
    expected_answer: str


@dataclass(frozen=True)
class LessonQuestionDraft:
    prompt: str
    reference_answer: str


@dataclass(frozen=True)
class GeneratedLesson:
    topic: str
    content: str
    questions: list[LessonQuestionDraft]


@dataclass(frozen=True)
class GradeResult:
    score: float
    correct: bool
    feedback: str
    correctness: int = 0
    tradeoff_reasoning: int = 0
    limitation_awareness: int = 0

    @property
    def total(self) -> int:
        return self.correctness + self.tradeoff_reasoning + self.limitation_awareness


class AIProvider(Protocol):
    def generate_topic(self, day: date) -> GeneratedTopic: ...
    def grade_answer(self, question: str, expected: str, answer: str) -> GradeResult: ...


class MockAIProvider:
    def generate_lesson(self, day_index: int) -> GeneratedLesson:
        path = Path(__file__).parent / "data" / "curriculum.json"
        lessons = json.loads(path.read_text(encoding="utf-8"))
        item = lessons[day_index % len(lessons)]
        return GeneratedLesson(
            topic=item["topic"],
            content=item["content"],
            questions=[LessonQuestionDraft(**question) for question in item["questions"]],
        )

    def generate_topic(self, day: date) -> GeneratedTopic:
        return GeneratedTopic(
            question=f"Q1: Design a URL shortener for 10 million daily users ({day.isoformat()}).",
            expected_answer="A highly available service with hashing, cache, database replication, and rate limiting.",
        )

    def grade_answer(self, question: str, expected: str, answer: str) -> GradeResult:
        # Stable grading for local development: substantive answers pass.
        words = len(answer.split())
        score = min(1.0, words / 20)
        correct = words >= 5
        lower = answer.lower()
        tradeoff_terms = ("but", "however", "trade-off", "latency", "cost")
        limitation_terms = ("limit", "stale", "fail", "risk", "complex", "miss")
        tradeoff = 2 if sum(term in lower for term in tradeoff_terms) >= 2 else int(any(term in lower for term in tradeoff_terms))
        limitation = 2 if sum(term in lower for term in limitation_terms) >= 2 else int(any(term in lower for term in limitation_terms))
        correctness = 2 if words >= 12 else int(bool(answer.strip()))
        return GradeResult(score=score, correct=correct, feedback="Good attempt." if correct else "Add more design detail.",
                           correctness=correctness, tradeoff_reasoning=tradeoff,
                           limitation_awareness=limitation)


class MessagingProvider(Protocol):
    def send(self, recipient: str, text: str) -> None: ...


class ConsoleMessagingProvider:
    def send(self, recipient: str, text: str) -> None:
        print(f"[message to {recipient}] {text}")


class MetaMessagingProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.meta_access_token or not settings.meta_phone_number_id:
            raise RuntimeError("Meta WhatsApp credentials are missing")
        self.url = (
            f"https://graph.facebook.com/{settings.meta_graph_api_version}/"
            f"{settings.meta_phone_number_id}/messages"
        )
        self.headers = {
            "Authorization": "Bearer " + settings.meta_access_token,
            "Content-Type": "application/json",
        }

    def send(self, recipient: str, text: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient.lstrip("+"),
            "type": "text",
            "text": {"body": text},
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(self.url, headers=self.headers, json=payload)
            response.raise_for_status()


def get_ai_provider() -> AIProvider:
    if get_settings().ai_provider.lower() != "mock":
        raise ValueError(f"Unsupported AI provider: {get_settings().ai_provider}")
    return MockAIProvider()


def get_messaging_provider() -> MessagingProvider:
    provider = get_settings().messaging_provider.lower()
    if provider == "meta":
        return MetaMessagingProvider()
    if provider not in {"console", "mock"}:
        raise ValueError(f"Unsupported messaging provider: {get_settings().messaging_provider}")
    return ConsoleMessagingProvider()


