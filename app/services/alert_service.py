"""Operational alerting abstraction.

A minimal, replaceable interface for operational alerts. The default
``LoggingAlertService`` emits structured log events (which any log-based alerting
pipeline can trigger on); swapping in a PagerDuty/Slack/email implementation is a
matter of providing another subclass -- no external providers are wired here.
"""

from app.core.logger import get_logger


logger = get_logger(__name__)


class AlertService:

    def notify_warning(self, message: str, **context) -> None:
        raise NotImplementedError

    def notify_error(self, message: str, **context) -> None:
        raise NotImplementedError


class LoggingAlertService(AlertService):
    """Default alerting: structured warning/error log events."""

    def notify_warning(self, message: str, **context) -> None:
        logger.warning("alert_warning", extra={"alert_message": message, **context})

    def notify_error(self, message: str, **context) -> None:
        logger.error("alert_error", extra={"alert_message": message, **context})


# Process-wide default so call sites without DI (e.g. the health probe) can alert.
default_alert_service: AlertService = LoggingAlertService()
