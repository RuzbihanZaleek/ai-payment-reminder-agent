import json
import logging

from app.core.logger import (
    get_logger,
    set_request_id,
    get_request_id,
    JsonFormatter,
    RequestIdFilter,
)


def test_get_logger_returns_configured_logger():

    logger = get_logger("test.logger")

    assert isinstance(logger, logging.Logger)


def test_request_id_roundtrip():

    set_request_id("req-123")

    assert get_request_id() == "req-123"


def test_json_formatter_includes_event_and_structured_fields():

    set_request_id("req-abc")

    record = logging.LogRecord(
        name="app.agents.workflow_executor",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="workflow_node_completed",
        args=(),
        exc_info=None,
    )

    RequestIdFilter().filter(record)
    record.agent_run_id = 5
    record.node_name = "PaymentCreationNode"
    record.duration_ms = 12

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "workflow_node_completed"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-abc"
    assert payload["agent_run_id"] == 5
    assert payload["node_name"] == "PaymentCreationNode"
    assert payload["duration_ms"] == 12


def test_json_formatter_defaults_request_id_to_none():

    set_request_id(None)

    record = logging.LogRecord(
        name="x",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="some_event",
        args=(),
        exc_info=None,
    )

    RequestIdFilter().filter(record)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] is None