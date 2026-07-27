# AI Payment Reminder Agent

An agentic backend that reads inbound WhatsApp messages ("I paid $100 for INV001"),
detects and allocates payments across a customer's contracts, keeps running
balances, sends reminders on a schedule, and exposes authenticated reporting,
dashboard and analytics APIs — all with strict per-user (tenant) isolation.

Built with **FastAPI**, **SQLAlchemy**, **Pydantic**, **Alembic**, **APScheduler**
and **OpenAI** (via LangChain), organised around a strict layered architecture
with constructor-based dependency injection.

---

## Table of contents

- [Quick start](#quick-start)
- [Architecture overview](#architecture-overview)
- [Folder structure](#folder-structure)
- [Dependency injection](#dependency-injection)
- [The agent workflow](#the-agent-workflow)
- [Domain lifecycles](#domain-lifecycles)
  - [Payment lifecycle](#payment-lifecycle)
  - [Approval lifecycle](#approval-lifecycle)
  - [Reminder lifecycle](#reminder-lifecycle)
  - [Conversation memory](#conversation-memory)
- [Reporting & analytics](#reporting--analytics)
- [Authentication & tenant isolation](#authentication--tenant-isolation)
- [API conventions](#api-conventions)
  - [Pagination](#pagination)
  - [Filtering & sorting](#filtering--sorting)
  - [Standardized errors](#standardized-errors)
  - [Health & readiness](#health--readiness)
- [Environment variables](#environment-variables)
- [Docker usage](#docker-usage)
- [Database migrations](#database-migrations)
- [Testing guide](#testing-guide)
- [Developer onboarding](#developer-onboarding)

---

## Quick start

```bash
# 1. Configure environment
cp .env.example .env
# Fill in OPENAI_API_KEY and generate a JWT secret:
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))" >> .env

# 2. Start the stack (API + Postgres)
docker compose up -d --build

# 3. Apply database migrations
docker compose exec app alembic upgrade head

# 4. Verify
curl localhost:8000/health   # {"status":"ok"}
curl localhost:8000/ready    # dependency checks
# Interactive API docs: http://localhost:8000/docs
```

---

## Architecture overview

The codebase enforces a one-directional layered architecture. Each layer only
knows about the layer directly beneath it:

```
        HTTP request
             │
        ┌────▼─────┐   validate → delegate → map response → translate errors
        │  Routers │   (app/api) — no business logic
        └────┬─────┘
             │
   ┌─────────▼──────────┐   compose/aggregate/derive
   │ Reporting /        │   (reporting & analytics services)
   │ Analytics services │   reuse domain services; never touch repositories*
   └─────────┬──────────┘   (*agent/scheduler reporting read their repos directly)
             │
        ┌────▼─────┐   business rules (allocation, approval, reminders, balances)
        │ Services │   (app/services) — single source of every calculation
        └────┬─────┘
             │
      ┌──────▼───────┐   all database access, pagination, filtering, sorting
      │ Repositories │   (app/repositories)
      └──────┬───────┘
             │
        ┌────▼─────┐   SQLAlchemy models / Postgres
        │  Models  │   (app/models)
        └──────────┘
```

Cross-cutting rules that hold everywhere:

- **Repositories** own *all* SQL, plus pagination, filtering and sorting.
- **Services** own business logic and are the single source of every
  calculation (e.g. "confirmed money", "remaining balance"). Rules are never
  duplicated.
- **Reporting services** aggregate; **analytics services** derive insights from
  reporting output and never query repositories themselves.
- **Routers** are thin: validate the request, delegate to a service, map the
  result to a response model, and translate exceptions into the standard error
  envelope. No business logic.
- **The container** (`app/container.py`) is the only composition root — no
  service ever instantiates another service internally.
- **The agent workflow** and all business rules are frozen — production
  hardening never changed them.

A deeper walkthrough with diagrams lives in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Folder structure

```
app/
├── main.py              # FastAPI app: middleware, routers, exception handlers
├── container.py         # Composition root — create_*_service(db=...) factories
├── scheduler.py         # APScheduler daily reminder job
├── core/
│   ├── config.py        # Settings (env-driven, validated at startup)
│   ├── security.py      # Password hashing (PBKDF2) + JWT encode/decode
│   ├── logger.py        # Structured JSON logging + request-id correlation
│   └── errors.py        # Error codes, AppError types, exception handlers
├── api/                 # Routers (thin) + shared query-param dependencies
│   ├── health.py        # /health (liveness), /ready (readiness)
│   ├── auth.py          # /auth/register, /auth/login
│   ├── agent.py         # /agent/messages (internal workflow entry)
│   ├── whatsapp.py      # /webhook (Meta inbound)
│   ├── approval.py      # /approvals/*
│   ├── dashboard.py     # /dashboard/overview
│   ├── analytics.py     # /analytics/overview
│   ├── query_params.py  # pagination/filter query-param dependencies
│   └── reports/         # /reports/contracts, /reports/agent-runs, ...
├── services/            # Business logic + reporting + analytics services
├── repositories/        # DB access; pagination.py & filters.py live here
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models (pagination, errors, ...)
├── enums/               # Shared enums (statuses, SortOrder, ...)
├── agents/              # Agent nodes + PaymentWorkflow / ReminderWorkflow
└── llm/                 # OpenAI client + prompts

alembic/versions/        # Hand-written, chained migrations
tests/
├── unit-style tests under agents/, services/, repositories/, schemas/, core/, api/
└── integration/         # Full-stack (API→service→repo→SQLite) tests
```

---

## Dependency injection

Every collaborator is passed in through the constructor — nothing is
`new`-ed up inside a service, router or workflow. Wiring happens exclusively in
`app/container.py` through `create_*_service(db=None, ...)` factory functions:

```python
def create_payment_approval_service(db=None) -> PaymentApprovalService:
    if db is None:
        db = SessionLocal()
    return PaymentApprovalService(PaymentRepository(db), ContractRepository(db))
```

Routers obtain services through FastAPI `Depends`, opening one DB session per
request:

```python
def get_payment_approval_service():
    db = SessionLocal()
    try:
        yield create_payment_approval_service(db=db)
    finally:
        db.close()
```

Because `db` and `llm` are injectable, tests substitute an in-memory SQLite
session or a fake LLM without any monkeypatching of business code. There are no
service locators or global singletons.

---

## The agent workflow

Inbound messages are processed by `PaymentWorkflow` (`app/agents/`), an explicit
pipeline of single-responsibility nodes run in a fixed order by a
`WorkflowExecutor` that records an `AgentRun` and per-node `AgentEvent`s for
observability:

```
PaymentDetectionNode → ConfidenceCheckerNode → ContractResolverNode →
PaymentAllocationNode → ApprovalCreationNode → PaymentCreationNode →
BalanceUpdateNode → PaymentReceiptNode → ReminderDecisionNode →
ResponseGenerationNode → NotificationNode
```

- **PaymentDetectionNode** asks the LLM to extract intent/amount/reference.
- **ConfidenceCheckerNode** flags low-confidence detections for manual review.
- **ContractResolverNode** picks the target contract(s) for the sender.
- **PaymentAllocationNode** splits the amount across contracts (explicit
  reference first, then automatic allocation).
- **PaymentCreationNode / BalanceUpdateNode / PaymentReceiptNode** persist the
  payment, recompute the balance, and write a receipt.
- **ReminderDecisionNode / ResponseGenerationNode / NotificationNode** decide
  and send the WhatsApp reply.

`ReminderWorkflow` is a message-free variant used by the scheduler (no detection
/ confidence nodes — a reminder has no inbound message to analyse).

> The workflow shape and node responsibilities are a frozen contract; the
> production-hardening phase did not add, remove or reorder any node.

---

## Domain lifecycles

### Payment lifecycle

A payment carries two independent flags:

- `status` (`PENDING` / `APPROVED` / `REJECTED`) — drives the **balance**.
- `approval_status` (`PENDING` / `APPROVED` / `REJECTED`) — drives the **review
  queue**.

Rules (single-sourced in `PaymentService`):

- **Confirmed money** = payments with `approval_status == APPROVED`. Only these
  count toward `total_received`.
- **Remaining balance** = `total_amount − sum(APPROVED-status payments)`, floored
  at zero.
- A high-confidence AI detection is auto-approved (reduces balance immediately);
  a low-confidence one is created `PENDING` + `requires_manual_review` and does
  **not** affect the balance until a human approves it.

### Approval lifecycle

- Pending manual-review payments surface at `GET /approvals/pending`.
- `POST /approvals/{id}/approve` → `status`/`approval_status` become `APPROVED`
  (now confirmed money) and `approved_by`/`approved_at` are stamped.
- `POST /approvals/{id}/reject` → both become `REJECTED` (never affects balance).
- Every approve/reject is ownership-checked and logged.

### Reminder lifecycle

- APScheduler runs `send_daily_reminders` (`app/scheduler.py`) once a day.
- `ReminderService` selects contracts due a reminder; `ReminderPolicyService`
  holds the business rules (what's "due", de-duplication via `ReminderLog`).
- Each contract runs through `ReminderWorkflow`; a `SchedulerRun` + per-contract
  `SchedulerEvent`s record the outcome. A single contract failing never aborts
  the run.

### Conversation memory

`ConversationMemoryService` keeps a per-`whatsapp_chat_id` conversation with a
rolling message history and a summary, so the agent has context across messages.
The current message is persisted only *after* a successful run, so a failed run
leaves no partial history. Inbound webhooks are idempotent — a `ProcessedMessage`
row prevents re-processing a Meta retry.

---

## Reporting & analytics

- **Reporting services** (`*_reporting_service.py`) produce raw stats/history by
  composing domain services (payment/contract) or reading their own read-model
  repositories (agent/scheduler). Every query is scoped to the requesting user.
- **Analytics services** (`*_analytics_service.py`) derive insights (collection
  rate, success rate, averages, delivery rate) purely from reporting output.
- `DashboardService` and `AnalyticsService` are composers that assemble the
  per-domain sections into a single overview.

Scheduler and reminder-log stats are **system-level** and remain global; all
contract / payment / agent-run data is **user-scoped**.

---

## Authentication & tenant isolation

- `POST /auth/register` and `POST /auth/login` (JWT bearer tokens; passwords
  hashed with PBKDF2-HMAC-SHA256, no external hashing dependency).
- Protected endpoints depend on `get_current_user`, which resolves the user from
  the `Authorization: Bearer <jwt>` header.
- **Tenant isolation**: contracts belong to a user (`Contract.user_id`); payments
  and agent-runs are scoped by joining to their owning contract. A user can only
  read their own contracts, payments, receipts, agent-runs, dashboard and
  analytics. WhatsApp resolution is `phone → owning user → that user's contracts`,
  so a single run never mixes tenants.

---

## API conventions

### Pagination

All collection endpoints use **page-based** pagination:

```
GET /reports/contracts/{id}/payments?page=1&page_size=20
```

- `page` ≥ 1, `page_size` between 1 and 100 (defaults: page 1, size 20).
  Invalid values return `422`.
- Responses are wrapped in a standard envelope:

```json
{
  "items": [ ... ],
  "meta": { "total_items": 25, "total_pages": 3, "page": 1, "page_size": 10 }
}
```

Paginated endpoints: `/reports/contracts/{id}/payments`,
`/reports/contracts/{id}/receipts`, `/reports/agent-runs`,
`/reports/scheduler-runs`, `/approvals/pending`.

### Filtering & sorting

Filtering and sorting are implemented **only in repositories**; routers just
declare query parameters and forward neutral filter objects.

- `order=desc` (newest first, default) or `order=asc` (oldest first).
- Payments: `status`, `approval_status`, `date_from`, `date_to`, `min_amount`,
  `max_amount`.
- Agent runs: `status`, `date_from`, `date_to`.
- Scheduler runs: `status`.
- Approvals: `status` (pending / approved / rejected; defaults to pending).

Example: `GET /reports/agent-runs?status=FAILED&order=asc&page=2&page_size=50`.

### Standardized errors

Every failure returns one shape:

```json
{ "error": { "code": "CONTRACT_NOT_FOUND", "message": "Contract not found." } }
```

Codes include `CONTRACT_NOT_FOUND`, `PAYMENT_NOT_FOUND`, `AGENT_RUN_NOT_FOUND`,
`SCHEDULER_RUN_NOT_FOUND`, `EMAIL_ALREADY_REGISTERED`, `INVALID_CREDENTIALS`,
`UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `NOT_FOUND`,
`INTERNAL_SERVER_ERROR`. Routers raise typed `AppError`s; the handlers in
`app/core/errors.py` translate those, validation errors and any uncaught
exception (masked as a 500 — internals are never leaked).

### Health & readiness

- `GET /health` — **liveness**: process is up (no I/O). Used by the Docker
  `HEALTHCHECK`.
- `GET /ready` — **readiness**: verifies DB connectivity plus JWT / OpenAI /
  WhatsApp configuration; returns `503` until all checks pass.

---

## Environment variables

See [`.env.example`](.env.example). Summary:

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | — | SQLAlchemy URL |
| `OPENAI_API_KEY` | yes | — | |
| `OPENAI_MODEL` | no | `gpt-5.5` | |
| `JWT_SECRET_KEY` | yes | — | **≥ 32 chars** (validated at startup) |
| `JWT_ALGORITHM` | no | `HS256` | one of HS256/HS384/HS512 |
| `JWT_EXPIRE_MINUTES` | no | `60` | must be > 0 |
| `WHATSAPP_VERIFY_TOKEN` | no | `""` | needed to accept inbound webhooks |
| `WHATSAPP_ACCESS_TOKEN` | no | `""` | needed to send messages |
| `WHATSAPP_PHONE_NUMBER_ID` | no | `""` | |
| `WHATSAPP_API_VERSION` | no | `v25.0` | |

Invalid/missing required config fails fast at startup with a clear error.

---

## Docker usage

```bash
docker compose up -d --build      # build image + start app & postgres
docker compose logs -f app        # follow structured JSON logs
docker compose exec app <cmd>     # run a command in the API container
docker compose down               # stop (add -v to also drop the DB volume)
```

Production notes baked into the image / compose file:

- Runs as a non-root user; `PYTHONUNBUFFERED` / `PYTHONDONTWRITEBYTECODE` set.
- Container `HEALTHCHECK` hits `/health`; Postgres has a `pg_isready` healthcheck
  and the app waits for `service_healthy` before starting.
- `restart: unless-stopped` on both services.
- The `.:/app` bind mount is a **dev convenience** — remove it for a real
  deployment so the image is the single source of truth.
- Rebuild the image after changing `requirements.txt`.

---

## Database migrations

Migrations are hand-written and chained by revision id in `alembic/versions/`.

```bash
docker compose exec app alembic upgrade head        # apply all
docker compose exec app alembic downgrade -1        # roll back one
docker compose exec app alembic current             # show current revision
docker compose exec app alembic history             # show the chain
```

Migrations are **not** run automatically on startup — run `alembic upgrade head`
as an explicit deploy step.

---

## Testing guide

The suite favours fast unit tests, with a DB-backed integration layer.

```bash
# Unit + integration tests that don't need Postgres (SQLite / fakes).
# JWT_SECRET_KEY must be set (>= 32 chars) because Settings validates it.
JWT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") \
  pytest --ignore=tests/repositories -q     # add back individual repo tests as needed

# Full suite including Postgres-backed repository tests (inside the container):
docker compose exec -e JWT_SECRET_KEY=$JWT_SECRET_KEY app pytest -q
```

- `tests/agents`, `tests/services`, `tests/schemas`, `tests/core` — unit tests
  with fakes (no DB).
- `tests/repositories` — DB tests. Most need Postgres (the `db_session`
  fixture); `test_repository_filtering.py` uses in-memory SQLite and runs
  anywhere.
- `tests/api` — router tests via `TestClient` + dependency overrides.
- `tests/integration` — **full-stack** tests (real routers → services →
  repositories → in-memory SQLite), covering tenant isolation, pagination,
  filtering, the approval workflow, standardized errors and health.

---

## Developer onboarding

1. **Read the layering.** Start at a router (e.g. `app/api/approval.py`), follow
   it into its service, then its repository. The same shape repeats everywhere.
2. **Wiring is in one place.** To see how anything is constructed, read
   `app/container.py`. If you add a collaborator, inject it there — never inside
   a class.
3. **Where does code go?**
   - New SQL / query / filter / sort → a **repository**.
   - New rule / calculation → a **service** (reuse existing helpers; don't
     duplicate a rule).
   - New aggregation → a **reporting** service; new derived metric → an
     **analytics** service.
   - New endpoint → a thin **router** that validates, delegates and maps.
4. **Errors:** raise a typed `AppError` (see `app/core/errors.py`); never build
   ad-hoc error bodies.
5. **Collections:** reuse `PaginationParams`, `Page.build(...)` and the
   `app/repositories/pagination.py` helpers — don't re-implement paging.
6. **Tenant safety:** any new read of contracts/payments/agent-runs must be
   user-scoped. Add an isolation test.
7. **Before committing:** run the test suite (see above) and
   `alembic upgrade head` if you added a migration.
