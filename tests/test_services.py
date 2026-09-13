from datetime import date, timedelta

import pytest

from app.models import User
from app.services import parse_answer, parse_webhook_payload, update_streak


def test_parse_answer():
    assert parse_answer(" q1: cache and replication ") == "cache and replication"


def test_parse_answer_rejects_other_questions():
    with pytest.raises(ValueError):
        parse_answer("Q2: no")


def test_parse_nested_webhook():
    payload = {"entry": [{"changes": [{"value": {"messages": [
        {"id": "wamid.1", "from": "123", "text": {"body": "Q1: details"}}
    ]}}]}]}
    message = parse_webhook_payload(payload)
    assert message.message_id == "wamid.1"
    assert message.text == "Q1: details"


def test_streaks_consecutive_and_reset():
    user = User(phone_number="1")
    update_streak(user, date(2026, 1, 1))
    update_streak(user, date(2026, 1, 2))
    assert user.current_streak == 2
    update_streak(user, date(2026, 1, 4))
    assert user.current_streak == 1
    assert user.longest_streak == 2
