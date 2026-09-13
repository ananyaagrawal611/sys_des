from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .config import get_settings


@dataclass(frozen=True)
class GeneratedTopic:
    question: str
    expected_answer: str


@dataclass(frozen=True)
class GradeResult:
    score: float
    correct: bool
    feedback: str


class AIProvider(Protocol):
    def generate_topic(self, day: date) -> GeneratedTopic: ...
    def grade_answer(self, question: str, expected: str, answer: str) -> GradeResult: ...


class MockAIProvider:
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
        return GradeResult(score=score, correct=correct, feedback="Good attempt." if correct else "Add more design detail.")


class MessagingProvider(Protocol):
    def send(self, recipient: str, text: str) -> None: ...


class ConsoleMessagingProvider:
    def send(self, recipient: str, text: str) -> None:
        print(f"[message to {recipient}] {text}")


def get_ai_provider() -> AIProvider:
    if get_settings().ai_provider.lower() != "mock":
        raise ValueError(f"Unsupported AI provider: {get_settings().ai_provider}")
    return MockAIProvider()


def get_messaging_provider() -> MessagingProvider:
    if get_settings().messaging_provider.lower() not in {"console", "mock"}:
        raise ValueError(f"Unsupported messaging provider: {get_settings().messaging_provider}")
    return ConsoleMessagingProvider()
