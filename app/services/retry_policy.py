"""Reusable retry policy with exponential backoff for transient failures.

Retries only failures worth retrying (timeouts, connection errors, HTTP 429 and
5xx) and never retries deterministic client errors (400/401/403). Backoff is
exponential: ``delay * 2**(attempt-1)`` -> 2s, 4s, 8s for a 2s base.

Kept transport-agnostic: the caller runs one attempt and reports back via a
small ``RetryOutcome``; the policy only decides *whether* and *how long* to wait.
"""

import time
from dataclasses import dataclass

from app.core.logger import get_logger


logger = get_logger(__name__)


# HTTP status codes that are safe to retry (transient / server-side).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Deterministic client errors -- retrying cannot help.
_NON_RETRYABLE_STATUS = {400, 401, 403, 404, 405, 409, 422}


@dataclass
class RetryOutcome:
    """Result of a single attempt.

    - ``succeeded``: attempt fully succeeded, stop.
    - ``status_code``: HTTP status if a response came back (else None).
    - ``transport_error``: True if the attempt raised (timeout/connection).
    """

    succeeded: bool
    status_code: int | None = None
    transport_error: bool = False


def is_retryable(outcome: RetryOutcome) -> bool:
    if outcome.succeeded:
        return False

    if outcome.transport_error:
        # Timeouts / connection errors are transient.
        return True

    if outcome.status_code is None:
        return False

    return outcome.status_code in _RETRYABLE_STATUS


class RetryPolicy:

    def __init__(self, max_retries: int, base_delay_seconds: float, sleep=time.sleep):
        # max_retries is the number of *additional* attempts after the first.
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self._sleep = sleep

    def backoff_seconds(self, attempt: int) -> float:
        """Exponential backoff for a 1-based attempt number (2s, 4s, 8s, ...)."""

        return self.base_delay_seconds * (2 ** (attempt - 1))

    def run(self, operation, on_retry=None) -> RetryOutcome:
        """Execute ``operation()`` (returns a RetryOutcome) with retries.

        ``operation`` must never raise -- it reports transport failures via
        ``RetryOutcome(transport_error=True)``. ``on_retry(attempt, outcome)`` is
        invoked before each backoff sleep for logging.
        """

        attempt = 1
        outcome = operation()

        while (
            not outcome.succeeded
            and attempt <= self.max_retries
            and is_retryable(outcome)
        ):
            if on_retry is not None:
                on_retry(attempt, outcome)

            self._sleep(self.backoff_seconds(attempt))
            attempt += 1
            outcome = operation()

        return outcome
