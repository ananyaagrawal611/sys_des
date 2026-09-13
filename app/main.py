from datetime import date
import hashlib
import hmac

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db, init_db
from .models import Answer, Topic, User
from .providers import get_ai_provider, get_messaging_provider
from .schemas import AnswerResponse, LeaderboardEntry, TopicResponse, WebhookMessage
from .services import generate_topic, leaderboard, parse_answer, parse_webhook_payload, update_streak
from .learning import handle_message, record_webhook_event, ensure_today_lesson, format_lesson
from .config import get_settings

app = FastAPI(title="SysDesign Streak", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


def admin_auth(x_admin_token: str | None = Header(default=None)) -> None:
    configured = get_settings().admin_token
    if configured and x_admin_token != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/topics/generate", response_model=TopicResponse)
def create_topic(db: Session = Depends(get_db), _: None = Depends(admin_auth)) -> object:
    return generate_topic(db, get_ai_provider())


@app.get("/topics/today", response_model=TopicResponse)
def today_topic(db: Session = Depends(get_db)) -> object:
    topic = db.scalar(select(Topic).where(Topic.topic_date == date.today()))
    if not topic:
        topic = generate_topic(db, get_ai_provider())
    return topic


@app.post("/webhooks/messages", response_model=AnswerResponse)
def receive_message(payload: dict, db: Session = Depends(get_db)) -> AnswerResponse:
    try:
        payload = parse_webhook_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    existing = db.scalar(select(Answer).where(Answer.provider_message_id == payload.message_id))
    if existing:
        return AnswerResponse(status="duplicate", score=existing.score, correct=existing.correct,
                              current_streak=existing.user.current_streak)
    try:
        answer_text = parse_answer(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    topic = db.scalar(select(Topic).where(Topic.topic_date == date.today()))
    if not topic:
        topic = generate_topic(db, get_ai_provider())
    user = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if not user:
        user = User(phone_number=payload.phone_number, display_name=payload.display_name)
        db.add(user)
        db.flush()
    result = get_ai_provider().grade_answer(topic.question, topic.expected_answer, answer_text)
    answer = Answer(provider_message_id=payload.message_id, user_id=user.id, topic_id=topic.id,
                    answer_text=answer_text, score=result.score, correct=result.correct)
    db.add(answer)
    update_streak(user, date.today())
    db.commit()
    get_messaging_provider().send(payload.phone_number, result.feedback)
    return AnswerResponse(status="recorded", score=result.score, correct=result.correct,
                          current_streak=user.current_streak, feedback=result.feedback)


@app.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)) -> list[LeaderboardEntry]:
    return [LeaderboardEntry(phone_number=u.phone_number, display_name=u.display_name,
                             current_streak=u.current_streak, longest_streak=u.longest_streak)
            for u in leaderboard(db)]


@app.post("/admin/jobs/leaderboard")
def run_leaderboard(_: None = Depends(admin_auth), db: Session = Depends(get_db)) -> dict[str, int]:
    return {"entries": len(leaderboard(db))}


@app.post("/admin/jobs/topics", response_model=TopicResponse)
def run_topic_job(_: None = Depends(admin_auth), db: Session = Depends(get_db)) -> object:
    return generate_topic(db, get_ai_provider())


@app.get("/webhooks/whatsapp")
def verify_whatsapp(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> int:
    if hub_mode == "subscribe" and hub_verify_token == get_settings().whatsapp_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    raw_body = await request.body()
    settings = get_settings()
    if settings.meta_app_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            settings.meta_app_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
    try:
        body = __import__("json").loads(raw_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    try:
        message = parse_webhook_payload(body)
    except ValueError:
        return {"status": "ignored"}
    if not record_webhook_event(db, message.message_id):
        return {"status": "duplicate"}
    handle_message(db, message.phone_number, message.text)
    return {"status": "processed"}


@app.post("/dev/messages")
def dev_message(payload: dict, db: Session = Depends(get_db)) -> dict[str, str]:
    return {"reply": handle_message(db, payload["phone"], payload["text"])}


@app.post("/dev/send-daily")
def dev_send_daily(db: Session = Depends(get_db)) -> dict[str, str]:
    lesson = ensure_today_lesson(db)
    for user in db.scalars(select(User)):
        get_messaging_provider().send(user.phone_number, format_lesson(lesson))
    return {"status": "sent"}


@app.post("/dev/send-summary")
def dev_send_summary(db: Session = Depends(get_db)) -> dict[str, str]:
    lesson = ensure_today_lesson(db)
    message = "Shared progress update\n" + handle_message(db, get_settings().user_1_phone, "STATUS")
    for user in db.scalars(select(User)):
        get_messaging_provider().send(user.phone_number, message)
    return {"status": "sent"}
