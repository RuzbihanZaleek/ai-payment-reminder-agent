"""SystemReportingService + NotificationRecoveryService + AlertService."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.system_reporting_service import SystemReportingService
from app.services.notification_recovery_service import NotificationRecoveryService
from app.services.alert_service import LoggingAlertService
from app.models.notification_outbox import NotificationOutbox


# --- SystemReportingService -------------------------------------------------

class FakeOutboxRepo:
    def __init__(self, counts, oldest_created_at=None):
        self._counts = counts
        self._oldest = (
            SimpleNamespace(created_at=oldest_created_at)
            if oldest_created_at is not None
            else None
        )

    def count_by_status(self, status):
        return self._counts.get(status, 0)

    def get_oldest_pending(self):
        return self._oldest


class FakeSchedulerRepo:
    def __init__(self, last_run=None, failed=0):
        self._last_run = last_run
        self._failed = failed

    def get_last_run(self):
        return self._last_run

    def count_failed(self):
        return self._failed


def test_system_stats_aggregates_queue_and_scheduler():
    oldest = datetime.now(timezone.utc) - timedelta(seconds=120)
    outbox = FakeOutboxRepo(
        counts={NotificationOutbox.PENDING: 4, NotificationOutbox.FAILED: 2},
        oldest_created_at=oldest,
    )
    last_run = SimpleNamespace(started_at=datetime(2026, 7, 28, 9, 0, 0))
    scheduler = FakeSchedulerRepo(last_run=last_run, failed=3)

    stats = SystemReportingService(outbox, scheduler).get_system_stats()

    assert stats["notification_queue_size"] == 4
    assert stats["failed_notification_count"] == 2
    assert stats["oldest_pending_notification_age_seconds"] >= 120
    assert stats["scheduler_last_run"] == datetime(2026, 7, 28, 9, 0, 0)
    assert stats["scheduler_failure_count"] == 3


def test_system_stats_handles_empty_queue():
    outbox = FakeOutboxRepo(counts={})
    scheduler = FakeSchedulerRepo(last_run=None, failed=0)

    stats = SystemReportingService(outbox, scheduler).get_system_stats()

    assert stats["notification_queue_size"] == 0
    assert stats["oldest_pending_notification_age_seconds"] is None
    assert stats["scheduler_last_run"] is None


# --- NotificationRecoveryService --------------------------------------------

class FakeRecoveryRepo:
    def __init__(self):
        self.retried = []
        self.discarded = []

    def get_failed(self):
        return ["f1"]

    def get_by_status(self, status):
        return ["p1"]

    def retry_failed(self, outbox_id):
        self.retried.append(outbox_id)
        return SimpleNamespace(id=outbox_id, status="PENDING")

    def discard_failed(self, outbox_id):
        self.discarded.append(outbox_id)
        return SimpleNamespace(id=outbox_id, status="DISCARDED")


def test_recovery_service_delegates():
    repo = FakeRecoveryRepo()
    service = NotificationRecoveryService(repo)

    assert service.list_failed() == ["f1"]
    assert service.list_pending() == ["p1"]
    assert service.retry(5).status == "PENDING"
    assert service.discard(6).status == "DISCARDED"
    assert repo.retried == [5]
    assert repo.discarded == [6]


# --- AlertService -----------------------------------------------------------

def test_logging_alert_service_emits_events(caplog):
    import logging

    caplog.set_level(logging.WARNING)
    service = LoggingAlertService()

    service.notify_warning("something odd", count=3)
    service.notify_error("something broke")

    events = {r.getMessage() for r in caplog.records}
    assert "alert_warning" in events
    assert "alert_error" in events
