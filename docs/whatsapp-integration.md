# WhatsApp Integration

How the agent talks to WhatsApp — both **incoming** messages (a customer replies
"I paid") and **outgoing** proactive **payment reminders** (the daily "your
payment is still pending"). Everything runs on the single FastAPI app already
deployed at `https://payagent.site`; there is no separate WhatsApp service.

---

## 1. Code map

| Concern | Location |
| --- | --- |
| Webhook (verify + receive) | [app/api/whatsapp.py](../app/api/whatsapp.py) |
| Payment vs. assistant routing | `MessageRouterService` (`app/services/message_router_service.py`) |
| Outbound WhatsApp client (text **+ templates**) | [app/services/whatsapp_notification_service.py](../app/services/whatsapp_notification_service.py) |
| Reminder eligibility rules | [app/services/reminder_policy_service.py](../app/services/reminder_policy_service.py) |
| "Which contracts are due" | `ReminderService` (`app/services/reminder_service.py`) |
| Run one reminder for a contract | `ReminderExecutionService` (`app/services/reminder_execution_service.py`) |
| Reminder message + delivery | `ReminderWorkflow` → `NotificationNode` (`app/agents/`) |
| Reminder tracking (dedup) | `ReminderLog` + `ReminderLogRepository` |
| Scheduler (daily job) | [app/scheduler.py](../app/scheduler.py) |
| WhatsApp write authorization | `WhatsAppAuthorizationService` |

---

## 2. Incoming messages (unchanged)

```
Customer → Meta Cloud API → POST /webhook → resolve sender's contract(s)
   → MessageRouterService.is_payment()
        ├─ payment  → payment workflow (records the payment)
        └─ other    → AI assistant (read-only over WhatsApp)
   → reply sent back via WhatsAppNotificationService.send()
```

- The sender is identified by matching the phone to a contract's
  `whatsapp_chat_id`; the owning user is derived from that contract.
- Messages are idempotent (`ProcessedMessageRepository`): a repeated Meta
  delivery is acknowledged and dropped.
- **Security:** lender-side write actions (create/approve/reject/send-reminders)
  are blocked over WhatsApp and audited. WhatsApp is read-only for writes.

Replies to a reminder ("I paid") flow through this **existing** path — Phase 3
adds no new inbound handling.

---

## 3. Automatic payment reminders (Phase 3)

### Flow

```
APScheduler (daily @ SCHEDULER_HOUR:MINUTE in REMINDER_TIMEZONE)
   → send_daily_reminders()            # advisory-locked: one replica only
      → ReminderService.get_pending_reminders()
           # keeps only contracts that pass ReminderPolicyService
      → for each due contract: ReminderExecutionService.execute(contract)
           → ReminderWorkflow → NotificationNode
                → WhatsAppNotificationService.send_payment_reminder_template()
      → ReminderLog row written (so the same contract isn't reminded twice today)
```

### Eligibility rules

A reminder is sent for a contract only when **all** hold
([reminder_policy_service.py](../app/services/reminder_policy_service.py)):

1. Contract status is `ACTIVE`.
2. The contract has already started (`start_date <= today`).
3. There is still a balance owed (`remaining > 0`).
4. No payment has been recorded **today**.
5. No reminder has already been sent **today** (duplicate prevention).

The "current time ≥ reminder time" rule is enforced by the scheduler itself —
the daily job fires once at `SCHEDULER_HOUR:MINUTE` in `REMINDER_TIMEZONE`, so a
reminder can only go out at/after that wall-clock time.

### Scheduler architecture

- **APScheduler** `BackgroundScheduler`, started from the FastAPI lifespan
  (disabled under `APP_ENV=testing`).
- The daily reminder job is guarded by a **PostgreSQL advisory lock**
  (`SCHEDULER_LOCK_ID`), so running multiple API replicas is safe — exactly one
  replica runs the reminders each day; the rest skip.
- `max_instances=1`, `coalesce=True`, and `misfire_grace_time` guarantee a
  downtime window never produces a burst of catch-up runs.
- One contract failing does not abort the run; each failure is recorded as a
  `SchedulerEvent` (`status="FAILED"`), counted in metrics, and alerted.

### Tracking & duplicate prevention

`ReminderLog` (`contract_id`, `sent_at`, `message`, `status`) records each
successfully-sent reminder. `has_sent_today(contract_id)` is what rule 5 checks.

> A **failed** delivery is intentionally **not** written to `ReminderLog` — that
> keeps the day open for a retry on the next run, and failures are already
> visible via `SchedulerEvent`, `/metrics`, and alerts.

---

## 4. WhatsApp templates (required for proactive messages)

Meta only delivers **free-form text** inside the 24-hour customer-service window
(i.e. shortly after the customer messaged you). A daily reminder is
**business-initiated**, so outside that window Meta **requires a pre-approved
message template** — a free-text reminder would be rejected.

`WhatsAppNotificationService` therefore exposes:

```python
send_payment_reminder_template(recipient, name, amount, due_date) -> bool
```

which fills the approved template's body placeholders **in order**:

| Placeholder | Value |
| --- | --- |
| `{{1}}` | customer name |
| `{{2}}` | amount (e.g. `$20`) |
| `{{3}}` | due date (ISO, e.g. `2026-07-30`) |

Create a template in Meta whose body matches, for example:

> Hi {{1}}, your payment of {{2}} scheduled for {{3}} is still pending. Please
> complete it when possible.

Set its name in `WHATSAPP_REMINDER_TEMPLATE_NAME` and language in
`WHATSAPP_REMINDER_TEMPLATE_LANGUAGE`. Text (in-session) replies still use the
plain `send()` path — only proactive reminders use the template.

> If `WHATSAPP_REMINDER_TEMPLATE_NAME` is blank, reminders fall back to plain
> text. That is for **dev/testing only** — in production Meta rejects proactive
> text, so a template name is required.

> **Note (outbox mode):** template delivery uses the `direct` notification path
> (the production default). If `NOTIFICATION_MODE=outbox`, reminders are relayed
> as text by the notification worker — keep `direct` for template reminders.

---

## 5. Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `WHATSAPP_VERIFY_TOKEN` | — | Webhook verification token (required in prod) |
| `WHATSAPP_ACCESS_TOKEN` | — | Meta Cloud API token (required in prod) |
| `WHATSAPP_PHONE_NUMBER_ID` | — | Sender phone number id (required in prod) |
| `WHATSAPP_API_VERSION` | `v25.0` | Graph API version |
| `WHATSAPP_REMINDER_TEMPLATE_NAME` | `""` | Approved reminder template name |
| `WHATSAPP_REMINDER_TEMPLATE_LANGUAGE` | `en_US` | Template language code |
| `SCHEDULER_HOUR` / `SCHEDULER_MINUTE` | `9` / `0` | Daily reminder time |
| `REMINDER_TIMEZONE` | `UTC` | Timezone the reminder time is interpreted in |
| `SCHEDULER_LOCK_ID` | `902025105` | Advisory-lock key (multi-replica safety) |
| `WHATSAPP_MAX_RETRIES` / `WHATSAPP_RETRY_DELAY_SECONDS` / `WHATSAPP_TIMEOUT_SECONDS` | `3` / `2` / `10` | Delivery retry/backoff/timeout |

No new database migration is required for Phase 3 — it reuses the existing
`contracts`, `payments`, and `reminder_logs` tables.

---

## 6. Testing locally

```bash
# Unit tests for the reminder path + template delivery:
pytest tests/services/test_whatsapp_notification_service.py \
       tests/agents/test_notification_node.py \
       tests/services/test_reminder_policy_service.py \
       tests/services/test_reminder_execution_service.py \
       tests/test_scheduler.py -q
```

To exercise a reminder end-to-end without waiting for the cron, call the job
directly in a shell:

```python
from app.scheduler import send_daily_reminders
send_daily_reminders()   # respects the advisory lock + eligibility rules
```

---

## 7. Production deployment

1. Create and get **approval** for the reminder template in the Meta dashboard
   (§8). Templates can take minutes to hours to be approved.
2. Set the reminder env vars on the server `.env`:
   `WHATSAPP_REMINDER_TEMPLATE_NAME`, `WHATSAPP_REMINDER_TEMPLATE_LANGUAGE`,
   and `REMINDER_TIMEZONE` (plus the existing WhatsApp creds).
3. Choose the daily send time via `SCHEDULER_HOUR` / `SCHEDULER_MINUTE`
   (interpreted in `REMINDER_TIMEZONE`).
4. Redeploy:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```
   No migration to run (Phase 3 adds no tables/columns).
5. Verify the scheduler registered the job in the logs (`scheduler_started`).
   If running multiple replicas, only one will log `scheduler_run_started` each
   day — the others log `scheduler_skipped_locked`.

---

## 8. Remaining manual Meta configuration

1. **Webhook** (if not already done): callback URL `https://payagent.site/webhook`,
   verify token = `WHATSAPP_VERIFY_TOKEN`, subscribed to the `messages` field.
2. **Message template**: WhatsApp Manager → *Message templates* → create a
   template (category **Utility**) with a body using `{{1}}`, `{{2}}`, `{{3}}`
   as described in §4. Submit for approval.
3. Once approved, put its exact name in `WHATSAPP_REMINDER_TEMPLATE_NAME` and its
   language code in `WHATSAPP_REMINDER_TEMPLATE_LANGUAGE`, then redeploy.
