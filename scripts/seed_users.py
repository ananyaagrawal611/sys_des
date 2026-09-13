from app.db import SessionLocal, init_db
from app.learning import ensure_users

if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        ensure_users(db)
    print("Seeded configured learners")
