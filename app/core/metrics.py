"""Lightweight in-process metrics with a Prometheus text exposition.

No Prometheus server and no client library -- just a tiny thread-safe registry
that renders the standard text format for `GET /metrics` to scrape. Metrics are
process-local (each replica exposes its own; a Prometheus server aggregates
across them), which is the conventional model.

Counters are monotonic; "summaries" track a running ``_sum`` and ``_count`` so
average duration = sum / count.
"""

import threading


class MetricsRegistry:

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}
        self._summary_sum: dict[str, float] = {}
        self._summary_count: dict[str, int] = {}
        self._help: dict[str, str] = {}

    def inc(self, name: str, amount: float = 1.0, help: str = "") -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + amount
            if help and name not in self._help:
                self._help[name] = help

    def observe(self, name: str, value: float, help: str = "") -> None:
        with self._lock:
            self._summary_sum[name] = self._summary_sum.get(name, 0.0) + value
            self._summary_count[name] = self._summary_count.get(name, 0) + 1
            if help and name not in self._help:
                self._help[name] = help

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "summary_sum": dict(self._summary_sum),
                "summary_count": dict(self._summary_count),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._summary_sum.clear()
            self._summary_count.clear()

    def render(self) -> str:
        lines: list[str] = []

        with self._lock:
            for name in sorted(self._counters):
                if name in self._help:
                    lines.append(f"# HELP {name} {self._help[name]}")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {self._counters[name]}")

            for name in sorted(self._summary_sum):
                if name in self._help:
                    lines.append(f"# HELP {name} {self._help[name]}")
                lines.append(f"# TYPE {name} summary")
                lines.append(f"{name}_sum {self._summary_sum[name]}")
                lines.append(f"{name}_count {self._summary_count.get(name, 0)}")

        return "\n".join(lines) + "\n"


# Module-level singleton used across the app.
metrics = MetricsRegistry()


# --- Domain-specific recorders (keep call sites readable) -------------------

def record_api_request(duration_seconds: float) -> None:
    metrics.inc("api_requests_total", help="Total HTTP requests handled")
    metrics.observe(
        "api_request_duration_seconds", duration_seconds, help="HTTP request duration"
    )


def record_workflow(success: bool, duration_seconds: float) -> None:
    metrics.inc("agent_workflow_executions_total", help="Agent workflow executions")
    if not success:
        metrics.inc("agent_workflow_failures_total", help="Agent workflow failures")
    metrics.observe(
        "agent_workflow_duration_seconds", duration_seconds, help="Agent workflow duration"
    )


def record_payment_processed() -> None:
    metrics.inc("payments_processed_total", help="Payments created/processed")


def record_approval_request() -> None:
    metrics.inc("payment_approval_requests_total", help="Payment approval decisions")


def record_reminder(sent: bool) -> None:
    if sent:
        metrics.inc("reminders_sent_total", help="Reminders sent")
    else:
        metrics.inc("reminders_failed_total", help="Reminders failed")


def record_notification_processed() -> None:
    metrics.inc(
        "notification_outbox_processed_total",
        help="Outbox notifications delivered successfully",
    )


def record_notification_failed() -> None:
    metrics.inc(
        "notification_outbox_failed_total",
        help="Outbox notifications permanently failed",
    )


def record_notification_retry() -> None:
    metrics.inc(
        "notification_outbox_retry_total",
        help="Outbox notification delivery retries scheduled",
    )
