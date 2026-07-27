# Architecture deep-dive

This complements the [README](../README.md) with request/data flows and the
reasoning behind the layering. See the README for setup, API conventions and
onboarding.

## Layer responsibilities

| Layer | Owns | Must not |
| --- | --- | --- |
| Routers (`app/api`) | request validation, delegation, response mapping, error translation | contain business logic or SQL |
| Analytics services | derive insights from reporting output | query repositories directly |
| Reporting services | aggregate stats/history | duplicate domain calculations |
| Domain services (`app/services`) | business rules, single source of every calculation | open sessions / build SQL |
| Repositories (`app/repositories`) | all SQL, pagination, filtering, sorting | hold business rules |
| Models (`app/models`) | table shape, indexes, relationships | — |

Dependencies point in one direction (top → bottom). The **container**
(`app/container.py`) is the only place that wires concrete instances together.

## Request flow — reading a paginated, filtered collection

```
GET /reports/contracts/42/payments?status=APPROVED&page=2&page_size=20&order=desc
   │
   ▼  app/api/reports/contracts.py
Router
   • require_owned_contract(42)          → 404 CONTRACT_NOT_FOUND if not owned
   • PaginationParams (page/size/order)  → 422 on invalid values
   • payment_filter_params → PaymentFilter (neutral value object)
   • delegate ↓, then Page.build(result, page, page_size)
   │
   ▼  PaymentReportingService.get_payment_history(...)
Reporting service → PaymentService.get_contract_payments_page(...)
   │
   ▼  PaymentRepository.get_by_contract_id_page(...)
Repository
   • apply filters (status/approval/date/amount)
   • apply_ordering(query, Payment.id, order)
   • paginate(query, page, page_size) → PageResult(items, total)
   │
   ▼  Page envelope { items, meta: { total_items, total_pages, page, page_size } }
```

`PageResult` (repository, framework-neutral) is mapped to the API `Page`
envelope in the router via `Page.build`, which derives `total_pages`. Filtering
and paging never leak above the repository.

## Request flow — inbound WhatsApp message

```
POST /webhook (Meta)
   │
   ▼  app/api/whatsapp.py
   • extract (message_id, phone, body)
   • idempotency: skip if ProcessedMessage(message_id) exists
   • resolve contracts for phone → scope to the first contract's owning user
   • load conversation memory (summary + recent messages)
   │
   ▼  AgentExecutionService.execute(...)  → creates AgentRun, runs PaymentWorkflow
   │
   ▼  PaymentWorkflow (WorkflowExecutor records AgentRun + AgentEvent per node)
   PaymentDetection → ConfidenceChecker → ContractResolver → PaymentAllocation →
   ApprovalCreation → PaymentCreation → BalanceUpdate → PaymentReceipt →
   ReminderDecision → ResponseGeneration → Notification
   │
   ▼  on success only: persist user + assistant messages, mark ProcessedMessage
```

A failed run is **not** marked processed, so Meta's retry can reprocess it; and
no conversation history is written for a failed run.

## Tenant isolation model

There is no separate tenant table. Ownership flows from `Contract.user_id`:

```
User ──1:N──> Contract ──1:N──> Payment
                     └──1:N──> AgentRun ──1:N──> AgentEvent
```

- Contract queries filter on `Contract.user_id`.
- Payment / AgentRun queries **join** to `Contract` and filter on
  `Contract.user_id` (see `get_by_approval_status_for_user_page`,
  `get_for_user_page`).
- Scheduler runs / reminder logs are system-level infrastructure and stay
  global (not user-scoped) by design.

## Observability

- `app/core/logger.py` emits structured JSON to stdout and injects a per-request
  correlation id (`X-Request-ID`, set by middleware in `app/main.py`).
- Background scheduler runs set their own correlation id
  (`scheduler-run-<id>`) so their logs are traceable without an HTTP request.
- The `WorkflowExecutor` persists an `AgentRun` and one `AgentEvent` per node
  (with duration), giving a durable trace of every message processed.
- Secrets (passwords, JWT secret, access tokens, API keys) are never logged.

## Production request flow

```
Client
  │  (TLS-terminating proxy / load balancer)
  │   forwards X-Forwarded-For + X-Request-ID
  ▼
FastAPI app (uvicorn, non-root container)
  • CORS middleware (origins from settings)
  • request-id middleware  → sets correlation id (from header or generated)
  • rate-limit dependency  → 429 RATE_LIMITED on auth/webhook abuse (per IP)
  • auth dependency        → 401 UNAUTHORIZED without a valid JWT
  • router → service → repository → Postgres (pooled: pre-ping + recycle)
  • standardized error envelope on any failure
  ▲
  └── /health (liveness) and /ready (readiness: DB + config) drive orchestration
```

The API is served under `/api/v1` (legacy unversioned paths kept for
compatibility); `/health`, `/ready`, `/webhook` and `/` stay unversioned.

## Scheduler lifecycle

The background reminder scheduler's lifetime is bound to the app process via a
FastAPI **lifespan** (`app/main.py`), so there is no global unmanaged instance:

```
app startup ──▶ lifespan enter ──▶ start_scheduler()
                                      │  skipped if APP_ENV=testing or
                                      │  SCHEDULER_ENABLED=false
                                      │  start failure is logged, app stays up
                                      ▼
                              APScheduler running (single process, one job)
                                 CronTrigger(hour, minute)
                                 max_instances=1, coalesce=True,
                                 misfire_grace_time=SCHEDULER_MISFIRE_GRACE_TIME
                                      │
app shutdown ─▶ lifespan exit ─▶ shutdown_scheduler()  (clean stop, wait=False)
```

Each fire runs `send_daily_reminders`, which mints its own `correlation_id`,
creates a `SchedulerRun`, and logs `scheduler_run_started` /
`scheduler_run_completed` with `scheduler_run_id`, `duration_ms`,
`processed_contract_count`, `success_count` and `failed_count`.

## Failure recovery flow

- **A single contract fails** → recorded as a `FAILED` `SchedulerEvent`; the run
  continues with the remaining contracts (`failed_count` incremented).
- **The whole run fails** (e.g. can't fetch contracts) → the `SchedulerRun` is
  marked `FAILED` with `completed_at` set, the exception is logged, and it
  re-raises to APScheduler — the application process stays alive.
- **App was down over a scheduled fire** → `coalesce=True` + `misfire_grace_time`
  mean at most **one** catch-up run fires within the grace window, never a burst.
- **Dropped DB connections** → `pool_pre_ping=True` transparently re-establishes
  a connection; `pool_recycle` retires connections before the server times them
  out.
- **Inbound webhook retries** → idempotency via `ProcessedMessage`; a failed run
  is not marked processed, so Meta's retry can safely reprocess it.
- **Unexpected exceptions** → masked as a `500 INTERNAL_SERVER_ERROR` envelope
  (internals never leaked); full traceback logged with the correlation id.

## Database indexes

`alembic/versions/e6f7a8b9c0d1_add_performance_indexes.py` adds indexes on the
columns existing queries filter, join or order on: tenant scoping
(`contracts.user_id`), WhatsApp lookups (`contracts.whatsapp_chat_id`), status
columns, reporting-join foreign keys, and the chronological columns used for
newest/oldest ordering and date-range filtering. Already-unique columns
(`reference_code`, `email`, `message_id`, `conversation_summaries.conversation_id`)
are not re-indexed — their unique constraint already provides a backing index.
The same indexes are declared on the models via `index=True` so ORM metadata and
the migration stay in sync.
```
