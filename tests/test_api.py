def test_health_and_topic(client):
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/topics/today")
    assert response.status_code == 200
    assert response.json()["question"].startswith("Q1:")


def test_webhook_idempotency_and_leaderboard(client):
    payload = {
        "message_id": "provider-1",
        "phone_number": "+15550001",
        "text": "Q1: I would use a cache, replicated database, queues, rate limits, and observability.",
        "display_name": "A",
    }
    first = client.post("/webhooks/messages", json=payload)
    assert first.status_code == 200
    assert first.json()["status"] == "recorded"
    duplicate = client.post("/webhooks/messages", json=payload)
    assert duplicate.json()["status"] == "duplicate"
    assert client.get("/leaderboard").json()[0]["current_streak"] == 1


def test_invalid_webhook(client):
    response = client.post("/webhooks/messages", json={
        "message_id": "provider-2", "phone_number": "+15550002", "text": "hello"
    })
    assert response.status_code == 400
