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
