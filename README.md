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
| `APP_ENV` | no | `development` | `development` / `testing` / `production` |
| `LOG_LEVEL` | no | `INFO` | any Python logging level |
| `DEBUG` | no | `false` | |
| `ENABLE_DOCS` | no | `true` | set `false` to hide `/docs`, `/redoc`, `/openapi.json` |
| `DATABASE_URL` | yes | — | SQLAlchemy URL |
| `DB_POOL_SIZE` | no | `5` | server DBs only |
| `DB_MAX_OVERFLOW` | no | `10` | |
| `DB_POOL_RECYCLE` | no | `1800` | seconds |
| `DB_POOL_PRE_PING` | no | `true` | detect dropped connections |
| `DB_ECHO` | no | `false` | log SQL |
| `OPENAI_API_KEY` | yes | — | |
| `OPENAI_MODEL` | no | `gpt-5.5` | |
| `JWT_SECRET_KEY` | yes | — | **≥ 32 chars** (validated at startup) |
| `JWT_ALGORITHM` | no | `HS256` | one of HS256/HS384/HS512 |
| `JWT_EXPIRE_MINUTES` | no | `60` | must be > 0 |
| `WHATSAPP_VERIFY_TOKEN` | prod | `""` | **required in production** |
| `WHATSAPP_ACCESS_TOKEN` | prod | `""` | **required in production** |
| `WHATSAPP_PHONE_NUMBER_ID` | prod | `""` | **required in production** |
| `WHATSAPP_API_VERSION` | no | `v25.0` | |
| `CORS_ALLOW_ORIGINS` | no | `*` | comma-separated; lock down in prod |
| `CORS_ALLOW_METHODS` | no | `*` | comma-separated |
| `CORS_ALLOW_HEADERS` | no | `*` | comma-separated |
| `SCHEDULER_ENABLED` | no | `true` | |
| `SCHEDULER_HOUR` / `SCHEDULER_MINUTE` | no | `9` / `0` | daily reminder time |
| `SCHEDULER_MISFIRE_GRACE_TIME` | no | `3600` | seconds |
| `SCHEDULER_LOCK_ID` | no | `902025105` | PG advisory-lock key (one replica runs the job) |
| `WHATSAPP_MAX_RETRIES` | no | `3` | transient-failure retries |
| `WHATSAPP_RETRY_DELAY_SECONDS` | no | `2` | base for exponential backoff |
| `WHATSAPP_TIMEOUT_SECONDS` | no | `10` | per-request timeout |
| `NOTIFICATION_MODE` | no | `direct` | `direct` or `outbox` |
| `RATE_LIMIT_ENABLED` | no | `true` | |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | no | `5` | per IP |
| `RATE_LIMIT_REGISTER_PER_MINUTE` | no | `5` | per IP |
| `RATE_LIMIT_WEBHOOK_PER_MINUTE` | no | `100` | |

Invalid/missing required config fails fast at startup with a clear error. When
`APP_ENV=production`, the three WhatsApp credentials become required and are
validated at startup.

### API versioning

The application API is served under **`/api/v1`** (e.g. `/api/v1/auth/login`,
`/api/v1/dashboard/overview`). The legacy unversioned paths (`/auth/login`, …)
remain mounted for backwards compatibility. Operational/external endpoints
(`/health`, `/ready`, `/webhook`, `/`) are intentionally **unversioned**.
Versioning re-mounts the same router objects under a prefix — no endpoint code
is duplicated (`app/api/v1/__init__.py`).

### Rate limiting

`POST /auth/login`, `POST /auth/register` (5/min/IP) and `POST /webhook`
(100/min) are protected by a per-IP sliding-window limiter
(`app/core/rate_limit.py`). Over-limit requests get `429` with a `RATE_LIMITED`
error envelope. The limiter is in-memory (process-local) and hidden behind a
small `allow(...)` interface so it can be swapped for a Redis backend later
without touching routers. It is disabled under `APP_ENV=testing`.

### Production reliability (multi-replica)

- **Distributed scheduler lock** — each replica runs the in-process scheduler,
  but the daily reminder job acquires a PostgreSQL advisory lock
  (`SchedulerLockService`) first; only the winner runs the reminders, the rest
  log `scheduler_skipped_locked` and return. No Redis.
- **WhatsApp delivery retries** — `WhatsAppNotificationService` retries transient
  failures (timeout, connection error, HTTP 429/5xx) with exponential backoff
  (`retry_policy.py`), never retries client errors (400/401/403), logs each
  `whatsapp_retry_attempt`, and still returns `False` on final failure (delivery
  never breaks the workflow).
- **Notification outbox** — set `NOTIFICATION_MODE=outbox` to have the workflow
  persist a `PENDING` `NotificationOutbox` row instead of sending inline; an
  out-of-band relay delivers it, so a provider outage can't fail a run. Default
  `direct` preserves the original inline behavior.
- **Metrics** — `GET /metrics` exposes Prometheus-format counters/summaries
  (API requests + duration, workflow executions/failures/duration, payments
  processed, approval requests, reminders sent/failed). Process-local; a
  Prometheus server scrapes each replica.
- **Audit trail** — security/business actions (login success/failure, payment
  approve/reject, contract creation) are written to `audit_logs` via
  `AuditService`. Secrets are never stored.

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

## Production deployment

A checklist for running this as a real SaaS backend.

### 1. Environment setup

- Set `APP_ENV=production`. This makes the WhatsApp credentials required and
  validated at startup — a misconfigured deploy fails fast instead of half-working.
- Provide a strong `JWT_SECRET_KEY` (≥ 32 chars; see secret management below).
- Lock down `CORS_ALLOW_ORIGINS` to your front-end origins (never `*` with
  credentials in production).
- Consider `ENABLE_DOCS=false` to hide the interactive schema, and keep
  `DEBUG=false`.
- Tune the DB pool (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`) to your Postgres limits.

### 2. Secret management

- Never commit `.env` (it is git-ignored). Inject secrets via your platform's
  secret store / environment (Docker/OS env vars override `.env`).
- Generate the JWT secret with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- Rotating `JWT_SECRET_KEY` invalidates all existing tokens (users re-login) —
  rotate during a maintenance window.
- Secrets are never logged (passwords, tokens, API keys are excluded by design).

### 3. Migration process (run as an explicit deploy step)

```bash
docker compose exec app alembic current      # inspect current revision
docker compose exec app alembic upgrade head # apply pending migrations
```

Migrations are **not** auto-run on startup. Apply them before routing traffic to
a new build. Take a database backup first (below).

### 4. Docker deployment

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
```

The image runs as a non-root user, sets `restart: unless-stopped`, waits for
Postgres health before starting, and defines a container `HEALTHCHECK`. Remove
the `.:/app` bind mount from `docker-compose.yml` for production so the image is
the single source of truth. Behind a proxy/load balancer, forward
`X-Forwarded-For` (used for rate-limit keys) and `X-Request-ID` (log
correlation).

### 5. Health checks

- Liveness probe → `GET /health` (no I/O; restart the container if it fails).
- Readiness probe → `GET /ready` (checks DB + JWT/OpenAI/WhatsApp config; returns
  `503` until ready — keep traffic away while not ready).

### 6. Backup strategy

- Postgres is the only stateful component (the `postgres_data` volume).
- Schedule regular logical backups, e.g.
  `docker compose exec postgres pg_dump -U postgres payment_reminder > backup.sql`.
- Test restores periodically:
  `docker compose exec -T postgres psql -U postgres payment_reminder < backup.sql`.
- Always back up **before** running migrations.

### 7. Rollback process

1. Roll the application image back to the previous tag/build.
2. If the new release included a migration, roll it back:
   `docker compose exec app alembic downgrade -1` (every migration in this repo
   has a tested `downgrade`). For destructive schema changes, restore from the
   pre-migration backup instead.
3. Re-run readiness (`/ready`) before restoring traffic.

Because the scheduler uses `coalesce=True` + `misfire_grace_time`, a brief
downtime during a deploy will **not** trigger a burst of catch-up reminder runs.

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
pytest --ignore=tests/repositories -q     # add back individual repo tests as needed

# Full suite including Postgres-backed repository tests (inside the container):
docker compose exec app pytest -q
```

`tests/conftest.py` sets `APP_ENV=testing` (and a fallback `JWT_SECRET_KEY`)
before the app is imported, so a plain `pytest` is deterministic: the background
scheduler and rate limiting are disabled for the suite (no threads, no
self-throttling). The dedicated scheduler and rate-limit tests temporarily flip
`APP_ENV` to exercise the real (non-testing) behavior.

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
