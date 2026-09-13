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
| `MESSAGING_PROVIDER` | `console` | Use `meta` for WhatsApp Cloud API |
| `META_ACCESS_TOKEN` | unset | Meta access token; never commit or log it |
| `META_PHONE_NUMBER_ID` | unset | Meta WhatsApp phone number ID |
| `META_GRAPH_API_VERSION` | `v21.0` | Graph API version used for outbound messages |
| `WHATSAPP_VERIFY_TOKEN` | unset | Random value configured in Meta webhook settings |
| `META_APP_SECRET` | unset | Enables `X-Hub-Signature-256` validation on webhook POSTs |

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

## Connecting Meta WhatsApp Cloud API

1. In Meta for Developers, create/select an app, add WhatsApp, and obtain a
   test or production phone number and its **Phone Number ID**.
2. Create a long-lived/system-user access token with the WhatsApp messaging
   permissions required by the deployment. Store it only in a secret manager
   as `META_ACCESS_TOKEN`; do not paste it into source, logs, or chat.
3. Set `MESSAGING_PROVIDER=meta`, `META_PHONE_NUMBER_ID`, and optionally
   `META_GRAPH_API_VERSION`. The app sends text messages to
   `https://graph.facebook.com/{version}/{phone-number-id}/messages` using
   `Authorization: Bearer {META_ACCESS_TOKEN}`.
4. Deploy the service over HTTPS. In Meta Webhooks, set the callback URL to
   `https://<host>/webhooks/whatsapp`, set the same random
   `WHATSAPP_VERIFY_TOKEN`, and subscribe the WhatsApp `messages` field.
5. Set `META_APP_SECRET` to the app secret. When configured, every webhook
   POST must include a valid `X-Hub-Signature-256` HMAC-SHA256 signature.
   Requests with a missing or invalid signature are rejected with 403.
6. Send a test message and confirm the webhook payload is accepted once;
   provider retries are idempotent by message ID.

The WhatsApp Cloud API integration here supports direct user messages only.
Verify group webhook and outbound group-message support with Meta before
production integration.

## Curriculum and WhatsApp learning flow

The archive curriculum is included in `app/data/curriculum.json`. The
`/dev/messages` endpoint accepts `A1: ...`, `A2: ...`, `STATUS`, and `HELP`;
answers are persisted in curriculum tables and scored on correctness,
trade-offs, and limitations. `POST /webhooks/whatsapp` accepts the same
WhatsApp Cloud payload shape and records message IDs before processing, so
retries remain idempotent. Use `/dev/send-daily` and `/dev/send-summary` for
local console delivery, or configure the existing provider adapters for a
managed sender. The scripts directory contains equivalent scheduler-friendly
commands.

> **Production note:** WhatsApp Cloud API group support must be explicitly
> verified before production. This MVP does not claim that group webhooks and
> outbound group messaging are supported.
