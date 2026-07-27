"""NotificationWorker orchestration behaviour (fakes, no DB)."""

from types import SimpleNamespace

from app.workers.notification_worker import NotificationWorker


class FakeOutboxRepository:
    def __init__(self, pending, recovered=0):
        self._pending = pending
        self._recovered = recovered
        self.processing = []
        self.sent = []
        self.failed = []
        self.retried = []
        self.recover_calls = []

    def recover_stuck_processing(self, timeout_minutes):
        self.recover_calls.append(timeout_minutes)
        return self._recovered

    def count_by_status(self, status):
        return len(self._pending)

    def get_pending(self, limit):
        return self._pending[:limit]

    def mark_processing(self, outbox_id):
        self.processing.append(outbox_id)

    def mark_sent(self, outbox_id):
        self.sent.append(outbox_id)

    def mark_failed(self, outbox_id, error):
        self.failed.append((outbox_id, error))

    def increment_retry(self, outbox_id, error, available_in_seconds=0.0):
        self.retried.append((outbox_id, error, available_in_seconds))


class FakeNotificationService:
    def __init__(self, results=None, raise_for=None):
        # results: dict recipient -> bool; raise_for: set of recipients to raise
        self.results = results or {}
        self.raise_for = raise_for or set()
        self.calls = []

    def send(self, recipient, message):
        self.calls.append(recipient)
        if recipient in self.raise_for:
            raise RuntimeError("boom")
        return self.results.get(recipient, True)


def _note(outbox_id, recipient, attempt_count=0):
    return SimpleNamespace(
        id=outbox_id,
        recipient=recipient,
        message="msg",
        attempt_count=attempt_count,
    )


def test_pending_notification_sent_successfully():
    repo = FakeOutboxRepository([_note(1, "a")])
    service = FakeNotificationService(results={"a": True})
    worker = NotificationWorker(repo, service, max_retries=3)

    result = worker.process_batch()

    assert repo.processing == [1]
    assert repo.sent == [1]
    assert repo.retried == []
    assert result.sent == 1


def test_failed_notification_retries_with_backoff():
    repo = FakeOutboxRepository([_note(1, "a", attempt_count=0)])
    service = FakeNotificationService(results={"a": False})
    worker = NotificationWorker(repo, service, max_retries=3, retry_base_delay_seconds=2)

    result = worker.process_batch()

    assert repo.sent == []
    assert len(repo.retried) == 1
    outbox_id, _error, backoff = repo.retried[0]
    assert outbox_id == 1
    assert backoff == 2  # base * 2**(1-1)
    assert result.retried == 1


def test_max_retry_marks_failed():
    # attempt_count already 2; this attempt (3rd) fails -> exhausted at max_retries=3
    repo = FakeOutboxRepository([_note(1, "a", attempt_count=2)])
    service = FakeNotificationService(results={"a": False})
    worker = NotificationWorker(repo, service, max_retries=3)

    result = worker.process_batch()

    assert repo.retried == []
    assert len(repo.failed) == 1
    assert repo.failed[0][0] == 1
    assert result.failed == 1


def test_one_failure_does_not_stop_others():
    repo = FakeOutboxRepository([_note(1, "a"), _note(2, "boom"), _note(3, "c")])
    service = FakeNotificationService(results={"a": True, "c": True}, raise_for={"boom"})
    worker = NotificationWorker(repo, service, max_retries=3)

    result = worker.process_batch()

    # All three were attempted despite the middle one raising.
    assert repo.processing == [1, 2, 3]
    assert repo.sent == [1, 3]
    assert result.sent == 2


def test_backoff_grows_with_attempts():
    repo = FakeOutboxRepository([_note(1, "a", attempt_count=1)])
    service = FakeNotificationService(results={"a": False})
    worker = NotificationWorker(repo, service, max_retries=5, retry_base_delay_seconds=2)

    worker.process_batch()

    _id, _error, backoff = repo.retried[0]
    assert backoff == 4  # base * 2**(2-1)


def test_worker_recovers_stuck_before_processing():
    repo = FakeOutboxRepository([_note(1, "a")], recovered=3)
    worker = NotificationWorker(
        repo, FakeNotificationService(), processing_timeout_minutes=15
    )

    result = worker.process_batch()

    assert repo.recover_calls == [15]
    assert result.recovered == 3


class _SpyAlertService:
    def __init__(self):
        self.errors = []

    def notify_warning(self, message, **context):
        pass

    def notify_error(self, message, **context):
        self.errors.append((message, context))


def test_failure_threshold_triggers_alert():
    # 2 notifications, both fail at max retries -> 2 failures >= threshold 2.
    repo = FakeOutboxRepository(
        [_note(1, "a", attempt_count=2), _note(2, "b", attempt_count=2)]
    )
    service = FakeNotificationService(results={"a": False, "b": False})
    alert = _SpyAlertService()
    worker = NotificationWorker(
        repo, service, max_retries=3, failure_alert_threshold=2, alert_service=alert
    )

    result = worker.process_batch()

    assert result.failed == 2
    assert len(alert.errors) == 1


def test_below_threshold_does_not_alert():
    repo = FakeOutboxRepository([_note(1, "a", attempt_count=2)])
    service = FakeNotificationService(results={"a": False})
    alert = _SpyAlertService()
    worker = NotificationWorker(
        repo, service, max_retries=3, failure_alert_threshold=5, alert_service=alert
    )

    worker.process_batch()

    assert alert.errors == []
