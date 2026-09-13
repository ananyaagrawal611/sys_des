def test_whatsapp_webhook_sends_reply_and_normalizes_phone(client, monkeypatch):
    sent = []

    class FakeMessagingProvider:
        def send(self, recipient, text):
            sent.append((recipient, text))

    monkeypatch.setattr("app.main.get_messaging_provider", lambda: FakeMessagingProvider())
    response = client.post(
        "/webhooks/whatsapp",
        json={
            "message_id": "whatsapp-reply-1",
            "phone_number": "910000000001",
            "text": "A1: Use caching, replication, queues, and rate limiting.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert sent
    assert sent[0][0] == "910000000001"
    assert "Learner 1" in sent[0][1]


def test_whatsapp_webhook_reports_outbound_failure(client, monkeypatch):
    class FailingMessagingProvider:
        def send(self, recipient, text):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.main.get_messaging_provider", lambda: FailingMessagingProvider())
    response = client.post(
        "/webhooks/whatsapp",
        json={
            "message_id": "whatsapp-reply-failure",
            "phone_number": "910000000001",
            "text": "HELP",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to send WhatsApp response"


def test_whatsapp_status_event_is_explicitly_ignored(client):
    response = client.post(
        "/webhooks/whatsapp",
        json={"entry": [{"changes": [{"value": {"statuses": [{"id": "status-1"}]}}]}]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "reason": "status_event"}


def test_admin_send_topic_delivers_lesson(client, monkeypatch):
    sent = []

    class FakeMessagingProvider:
        def send(self, recipient, text):
            sent.append((recipient, text))

    monkeypatch.setattr("app.main.get_messaging_provider", lambda: FakeMessagingProvider())
    response = client.post("/admin/jobs/send-topic")

    assert response.status_code == 200
    assert response.json() == {"status": "sent", "recipients": 2}
    assert len(sent) == 2
    assert all("System Design Bite" in text and "Reply with A1:" in text for _, text in sent)
