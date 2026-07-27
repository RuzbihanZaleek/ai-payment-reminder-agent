"""In-memory rate limiting foundation.

A deliberately small sliding-window limiter used as FastAPI dependencies on
abuse-prone endpoints (auth + webhook). It is process-local -- fine for a single
instance and for tests -- and hidden behind a tiny ``allow(...)`` interface so it
can later be swapped for a Redis-backed backend without touching the routers:
implement the same ``allow`` method and replace the module-level backend.

No Redis is introduced here (per phase constraints).
"""

import time
from collections import defaultdict, deque

from fastapi import Depends, Request

from app.core.config import settings
from app.core.errors import RateLimitedError
from app.core.logger import get_logger


logger = get_logger(__name__)

_WINDOW_SECONDS = 60


class InMemoryRateLimitBackend:
    """Sliding-window counter keyed by an opaque string (e.g. ``scope:ip``)."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        cutoff = now - window_seconds

        bucket = self._hits[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            return False

        bucket.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


# Module-level backend -- swap this single object for a Redis-backed one later.
_backend = InMemoryRateLimitBackend()


def get_backend() -> InMemoryRateLimitBackend:
    return _backend


def _client_ip(request: Request) -> str:
    # Respect a proxy's forwarded IP if present; fall back to the socket peer.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


class RateLimit:
    """A configurable per-IP rate-limit dependency.

    ``limit_getter`` is read at request time so limits stay driven by settings
    (and remain easy to change per environment).
    """

    def __init__(self, scope: str, limit_getter):
        self.scope = scope
        self.limit_getter = limit_getter

    def __call__(self, request: Request) -> None:
        # Disabled entirely under testing so the suite isn't throttled; the
        # dedicated rate-limit tests flip APP_ENV to exercise the real path.
        if not settings.RATE_LIMIT_ENABLED or settings.is_testing:
            return

        limit = self.limit_getter()
        key = f"{self.scope}:{_client_ip(request)}"

        if not _backend.allow(key, limit, _WINDOW_SECONDS):
            logger.info(
                "rate_limit_exceeded",
                extra={"scope": self.scope, "limit_per_minute": limit},
            )
            raise RateLimitedError("Too many requests. Please retry shortly.")


# Ready-made dependencies for the protected endpoints.
rate_limit_login = RateLimit("login", lambda: settings.RATE_LIMIT_LOGIN_PER_MINUTE)
rate_limit_register = RateLimit("register", lambda: settings.RATE_LIMIT_REGISTER_PER_MINUTE)
rate_limit_webhook = RateLimit("webhook", lambda: settings.RATE_LIMIT_WEBHOOK_PER_MINUTE)


# Re-exported so routers can write Depends(...) without importing fastapi here.
login_rate_limit = Depends(rate_limit_login)
register_rate_limit = Depends(rate_limit_register)
webhook_rate_limit = Depends(rate_limit_webhook)
