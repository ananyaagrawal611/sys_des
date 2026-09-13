from app.db import SessionLocal, init_db
from app.learning import ensure_today_lesson, format_lesson
from app.models import User
from app.providers import get_messaging_provider
from sqlalchemy import select

if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        lesson = ensure_today_lesson(db)
        text = format_lesson(lesson)
        provider = get_messaging_provider()
        for user in db.scalars(select(User)):
            provider.send(user.phone_number, text)
