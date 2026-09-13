# SysDesign Streak

Initial MVP for a daily system-design learning streak. The service exposes a
small FastAPI HTTP API, persists progress in SQLite with SQLAlchemy, and keeps
AI and messaging integrations behind replaceable providers. In a fresh
installation both providers are deterministic local/mock implementations.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configuration is read from environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./sysdesign.db` | SQLAlchemy database URL |
| `AI_PROVIDER` | `mock` | Provider name (`mock` is the built-in provider) |
| `MESSAGING_PROVIDER` | `console` | Provider name (`console`/`mock` are built in) |
| `ADMIN_TOKEN` | unset | If set, required as `X-Admin-Token` on admin routes |
| `LOG_LEVEL` | `INFO` | Application log level |

## Run and test

```bash
uvicorn app.main:app --reload
pytest -q
```

The API docs are available at `/docs`. `GET /health` is a dependency-free
readiness check.

## MVP flow

1. `POST /topics/generate` creates today's deterministic topic.
2. A messaging provider sends it to users.
3. `POST /webhooks/messages` accepts provider payloads containing an answer
   such as `Q1: 2.5 million requests per second`.
4. The answer is graded, recorded once per provider message ID, and updates the
   user's streak and leaderboard.
5. Admin routes can trigger topic and leaderboard jobs.

The webhook parser intentionally accepts common WhatsApp-style JSON wrappers
as well as a simple `{message_id, phone_number, text}` payload.

> **Production note:** WhatsApp Cloud API group support must be explicitly
> verified before production. This MVP does not claim that group webhooks and
> outbound group messaging are supported.

