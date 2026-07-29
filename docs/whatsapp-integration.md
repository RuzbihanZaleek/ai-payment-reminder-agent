# WhatsApp Cloud API Integration

How the AI Payment Reminder Agent talks to users over WhatsApp via the Meta
WhatsApp Cloud API.

> **Status:** WhatsApp is fully integrated and production-hardened. This document
> describes the existing implementation. WhatsApp is intentionally limited to
> **payment submission + read-only questions**; lender-side write actions
> (create/approve/reject contracts and payments) are blocked on this channel and
> are only available through the authenticated app (JWT). See
> [Security model](#security-model).

---

## Where the code lives

Rather than a single package, the integration is layered across the existing
architecture (routers thin, business logic in services):

| Concern | Location |
| --- | --- |
| Webhook endpoints (verify + receive) | `app/api/whatsapp.py` |
| Payment-vs-assistant routing | `app/services/message_router_service.py` |
| Outbound send client (Graph API, `httpx`, retry/backoff) | `app/services/whatsapp_notification_service.py` |
| Channel authorization guard (blocks writes over WhatsApp) | `app/services/whatsapp_authorization_service.py` |
| Phone helpers (normalize / mask / validate) | `app/core/phone.py` |
| Payment detection + workflow | `app/agents/` (PaymentMessageAgent, PaymentWorkflow) |
| Conversational AI | `app/ai/assistant/` (AssistantService) |
| Configuration | `app/core/config.py` (`WHATSAPP_*`) |
| Composition / DI | `app/container.py` |

---

## Architecture

```
                         WhatsApp User
                              |
                              v
                    Meta WhatsApp Cloud API
                              |
                              v
                Cloudflare  (HTTPS + DDoS + DNS)
                              |
                              v
                   Cloudflare Tunnel (cloudflared)
                              |
                              v
   FastAPI webhook   POST /webhook  ==  POST /webhooks/whatsapp
                              |
                              v
                    MessageRouterService
                    (reuses PaymentMessageAgent)
                    /                       \
         payment message                non-payment message
                 |                              |
                 v                              v
         PaymentWorkflow                  AssistantService
         (record payment,            (read-only Q&A; write intents
          allocate, receipt)          rejected by the WhatsApp guard)
                 |                              |
                 +--------------+---------------+
                                |
                                v
                          PostgreSQL
                                |
                                v
              WhatsAppNotificationService.send()
                   (reply back to the user)
```

---

## Message flow

### 1. Webhook verification (one-time, `GET`)

Meta calls the webhook with `hub.mode`, `hub.verify_token`, `hub.challenge`. The
handler checks the token against `WHATSAPP_VERIFY_TOKEN` and echoes the challenge
back as plain text (or `403` on mismatch).

### 2. Receiving a message (`POST`)

1. **Extract** `(message_id, sender_phone, body)` from the Meta payload. Non-message
   events (delivery/status updates) are acknowledged and ignored.
2. **Idempotency** — if `message_id` was already processed, acknowledge and drop
   (Meta retries aggressively). Backed by the `processed_messages` table.
3. **Resolve sender** — look up active contracts by `whatsapp_chat_id == sender_phone`
   and derive the owning user (tenant scope). Unknown senders are acknowledged and
   ignored.
4. **Route** via `MessageRouterService.is_payment(...)`, which reuses the existing
   `PaymentMessageAgent` detector:
   - **Payment** (e.g. "I paid today's $20") &rarr; the **unchanged** `PaymentWorkflow`
     records/allocates the payment and generates the reply.
   - **Non-payment** (e.g. "How much remaining?") &rarr; `AssistantService` answers
     from real data, gated by the WhatsApp authorization guard.
5. **Reply** — the generated message is sent back to the user via
   `WhatsAppNotificationService.send()`.

### 3. Sending a message (outbound)

`POST https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages`
with `Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}` and a text body. Transient
failures (timeout, connection error, HTTP 429/5xx) are retried with exponential
backoff; a final failure returns `False` and never breaks the request flow.

---

## Security model

WhatsApp senders are **not authenticated users** — identity is only derived from
contract ownership. So `WhatsAppAuthorizationService` **denies lender-side write
intents** over WhatsApp (create contract, approve/reject payment, send reminders,
confirm a pending action) and audits the attempt (`WHATSAPP_ACTION_BLOCKED`, with
a masked phone). Allowed over WhatsApp:

- Submitting payments ("I paid $20") &rarr; payment workflow.
- Read-only questions (balance, next payment, contract status, history, insights).

Lender writes require the authenticated app (`/assistant/chat`, `/advisor/analyze`,
REST APIs) where JWT establishes a verified identity.

> Example: _"Can I pay tomorrow instead?"_ is a schedule write. The agent will
> explain that rescheduling must be done in the app — it is not performed over
> WhatsApp.

---

## Environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `WHATSAPP_VERIFY_TOKEN` | prod | Any secret string you choose; Meta echoes it during verification. |
| `WHATSAPP_ACCESS_TOKEN` | prod | Bearer token from the Meta app (WhatsApp &rarr; API setup). |
| `WHATSAPP_PHONE_NUMBER_ID` | prod | The sending phone number's id. |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | no | WABA id; not needed to send — useful for management/onboarding. |
| `WHATSAPP_API_VERSION` | no | Graph API version, default `v25.0`. |
| `WHATSAPP_MAX_RETRIES` | no | Outbound send retries (default 3). |
| `WHATSAPP_RETRY_DELAY_SECONDS` | no | Backoff base (default 2). |
| `WHATSAPP_TIMEOUT_SECONDS` | no | Per-request timeout (default 10). |

In `APP_ENV=production`, the first three are validated at startup — the app
refuses to boot without them. See `.env.example`.

---

## Webhook endpoints

Both paths map to the **same** handler, so Meta can be configured with either:

- `https://payagent.site/webhook`
- `https://payagent.site/webhooks/whatsapp`

These endpoints are unversioned on purpose (a fixed external contract) and
rate-limited (`RATE_LIMIT_WEBHOOK_PER_MINUTE`, default 100/min).

---

## Local testing

Run the WhatsApp test suite:

```bash
pytest tests/api/test_whatsapp_api.py \
       tests/api/test_whatsapp_conversation.py \
       tests/api/test_whatsapp_idempotency.py -q
```

Exercise verification manually (with the app running and `WHATSAPP_VERIFY_TOKEN=tok`):

```bash
curl "http://localhost:8000/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=tok&hub.challenge=PING"
# -> PING
```

Simulate an inbound message (a known sender must have an active contract whose
`whatsapp_chat_id` equals `from`):

```bash
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "wamid.test1",
            "from": "15551234567",
            "text": {"body": "I paid today's 20"}
          }]
        }
      }]
    }]
  }'
```

---

## Meta webhook setup

1. In the Meta app dashboard, add the **WhatsApp** product and note the
   **Phone number ID**, **WhatsApp Business Account ID**, and a temporary/permanent
   **access token**.
2. Put those (plus a `WHATSAPP_VERIFY_TOKEN` of your choosing) into the server's
   `.env`.
3. Under **WhatsApp &rarr; Configuration &rarr; Webhook**, set the callback URL to
   `https://payagent.site/webhooks/whatsapp` and the verify token to the same
   `WHATSAPP_VERIFY_TOKEN`. Meta will call the `GET` endpoint to verify.
4. **Subscribe** the webhook to the `messages` field.
5. Send a WhatsApp message to the business number and confirm a reply.

---

## Production deployment

1. Ensure `.env` on the server has `APP_ENV=production` and the WhatsApp
   credentials (the app validates them at startup).
2. Deploy with the production compose file:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml exec app alembic upgrade head
   ```
3. Traffic path: Meta &rarr; Cloudflare (HTTPS) &rarr; Cloudflare Tunnel &rarr; the
   FastAPI container. No inbound port is opened; the webhook is reachable only
   through the tunnel at `https://payagent.site`.
4. Verify end-to-end:
   ```bash
   curl "https://payagent.site/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=$WHATSAPP_VERIFY_TOKEN&hub.challenge=PING"
   curl https://payagent.site/health
   ```

No database migration is required for this phase (`WHATSAPP_BUSINESS_ACCOUNT_ID`
is configuration only; no schema change).
