import json
import logging
import sys
from contextvars import ContextVar


# Per-request correlation id, populated by the API middleware.
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


# Attributes that already live on every LogRecord -- everything else passed via
# ``extra=`` is treated as a structured field.
_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class RequestIdFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:

        record.request_id = _request_id_ctx.get()

        return True


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        data = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }

        # Fold any structured fields passed through ``extra=`` into the payload.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in data:
                data[key] = value

        if record.exc_info:
            data["error"] = self.formatException(record.exc_info)

        return json.dumps(data, default=str)


_configured = False


def _resolve_level(level: int | str | None) -> int:
    """Resolve the effective log level, defaulting to the configured LOG_LEVEL."""

    if level is None:
        # Imported lazily to avoid a hard import cycle at module load.
        from app.core.config import settings

        level = settings.LOG_LEVEL

    if isinstance(level, str):
        return logging.getLevelNamesMapping().get(level.upper(), logging.INFO)

    return level


def configure_logging(level: int | str | None = None) -> None:
    """Attach a JSON stdout handler to the root logger (idempotent).

    The level defaults to ``settings.LOG_LEVEL`` so operators control verbosity
    per environment without code changes.
    """

    global _configured

    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(_resolve_level(level))

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for ``name``."""

    configure_logging()

    return logging.getLogger(name)
