"""WhatsApp delivery retry behaviour (retry policy + service integration)."""

import httpx

from app.services.retry_policy import RetryPolicy, RetryOutcome, is_retryable
from app.services.whatsapp_notification_service import WhatsAppNotificationService


# --- Retry policy -----------------------------------------------------------

def test_backoff_is_exponential():
    policy = RetryPolicy(max_retries=3, base_delay_seconds=2, sleep=lambda s: None)

    assert policy.backoff_seconds(1) == 2
    assert policy.backoff_seconds(2) == 4
    assert policy.backoff_seconds(3) == 8


def test_transient_failures_are_retryable():
    assert is_retryable(RetryOutcome(succeeded=False, status_code=500)) is True
    assert is_retryable(RetryOutcome(succeeded=False, status_code=429)) is True
    assert is_retryable(RetryOutcome(succeeded=False, transport_error=True)) is True


def test_client_errors_are_not_retryable():
    assert is_retryable(RetryOutcome(succeeded=False, status_code=400)) is False
    assert is_retryable(RetryOutcome(succeeded=False, status_code=401)) is False
    assert is_retryable(RetryOutcome(succeeded=False, status_code=403)) is False


def test_policy_stops_after_max_retries():
    attempts = {"n": 0}

    def op():
        attempts["n"] += 1
        return RetryOutcome(succeeded=False, status_code=500)

    RetryPolicy(max_retries=3, base_delay_seconds=1, sleep=lambda s: None).run(op)

    # 1 initial + 3 retries.
    assert attempts["n"] == 4


# --- Service integration ----------------------------------------------------

class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


def _service(monkeypatch, responses):
    """A service whose httpx.post yields the given responses/exceptions in order."""

    calls = {"n": 0}

    def fake_post(*args, **kwargs):
        item = responses[calls["n"]]
        calls["n"] += 1
        if isinstance(item, Exception):
            raise item
        return _Resp(item)

    monkeypatch.setattr(httpx, "post", fake_post)

    service = WhatsAppNotificationService(
        access_token="t",
        phone_number_id="p",
        api_version="v25.0",
        max_retries=3,
        retry_delay_seconds=0,  # no real sleeping in tests
    )
    return service, calls


def test_retries_on_500_then_succeeds(monkeypatch):
    service, calls = _service(monkeypatch, [500, 500, 200])

    assert service.send("15551234567", "hi") is True
    assert calls["n"] == 3


def test_retries_on_timeout(monkeypatch):
    service, calls = _service(
        monkeypatch, [httpx.TimeoutException("timeout"), 200]
    )

    assert service.send("15551234567", "hi") is True
    assert calls["n"] == 2


def test_no_retry_on_400(monkeypatch):
    service, calls = _service(monkeypatch, [400, 200])

    assert service.send("15551234567", "hi") is False
    # Only one attempt: 400 is not retryable.
    assert calls["n"] == 1


def test_final_failure_returns_false(monkeypatch):
    service, calls = _service(monkeypatch, [500, 500, 500, 500])

    assert service.send("15551234567", "hi") is False
    assert calls["n"] == 4  # 1 + 3 retries, all failed
