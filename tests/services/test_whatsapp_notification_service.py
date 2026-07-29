from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.whatsapp_notification_service import WhatsAppNotificationService


class FakeResponse:

    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class RecordingPost:

    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def __call__(self, url, headers=None, json=None, **kwargs):

        self.calls.append(
            {"url": url, "headers": headers, "json": json, "kwargs": kwargs}
        )

        if self.exc is not None:
            raise self.exc

        return self.response


def _service(reminder_template_name="", reminder_template_language="en_US"):

    return WhatsAppNotificationService(
        access_token="TOKEN_ABC",
        phone_number_id="PHONE_123",
        api_version="v21.0",
        retry_delay_seconds=0,  # no real backoff sleeping in tests
        reminder_template_name=reminder_template_name,
        reminder_template_language=reminder_template_language,
    )


def _patch_post(monkeypatch, recorder):

    monkeypatch.setattr(
        "app.services.whatsapp_notification_service.httpx.post",
        recorder,
    )


def test_successful_send_returns_true(monkeypatch):

    recorder = RecordingPost(response=FakeResponse(status_code=200))
    _patch_post(monkeypatch, recorder)

    result = _service().send("15551234567", "Hello")

    assert result is True


def test_failed_http_response_returns_false(monkeypatch):

    recorder = RecordingPost(response=FakeResponse(status_code=400, text="bad request"))
    _patch_post(monkeypatch, recorder)

    result = _service().send("15551234567", "Hello")

    assert result is False


def test_request_exception_returns_false(monkeypatch):

    recorder = RecordingPost(exc=httpx.RequestError("network down"))
    _patch_post(monkeypatch, recorder)

    result = _service().send("15551234567", "Hello")

    assert result is False


def test_correct_headers_are_sent(monkeypatch):

    recorder = RecordingPost(response=FakeResponse(status_code=200))
    _patch_post(monkeypatch, recorder)

    _service().send("15551234567", "Hello")

    headers = recorder.calls[0]["headers"]

    assert headers["Authorization"] == "Bearer TOKEN_ABC"
    assert headers["Content-Type"] == "application/json"


def test_correct_payload_is_sent(monkeypatch):

    recorder = RecordingPost(response=FakeResponse(status_code=200))
    _patch_post(monkeypatch, recorder)

    _service().send("15551234567", "Your balance is $50")

    call = recorder.calls[0]

    assert call["url"] == (
        "https://graph.facebook.com/v21.0/PHONE_123/messages"
    )
    assert call["json"] == {
        "messaging_product": "whatsapp",
        "to": "15551234567",
        "type": "text",
        "text": {"body": "Your balance is $50"},
    }


def test_reminder_template_builds_expected_payload(monkeypatch):

    recorder = RecordingPost(response=FakeResponse(status_code=200))
    _patch_post(monkeypatch, recorder)

    service = _service(reminder_template_name="payment_reminder")

    result = service.send_payment_reminder_template(
        "15551234567",
        name="John",
        amount=Decimal("20"),
        due_date=date(2026, 7, 30),
    )

    assert result is True

    call = recorder.calls[0]

    assert call["url"] == (
        "https://graph.facebook.com/v21.0/PHONE_123/messages"
    )
    assert call["json"] == {
        "messaging_product": "whatsapp",
        "to": "15551234567",
        "type": "template",
        "template": {
            "name": "payment_reminder",
            "language": {"code": "en_US"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "John"},
                        {"type": "text", "text": "$20"},
                        {"type": "text", "text": "2026-07-30"},
                    ],
                }
            ],
        },
    }


def test_reminder_template_failure_returns_false(monkeypatch):

    recorder = RecordingPost(response=FakeResponse(status_code=400, text="bad"))
    _patch_post(monkeypatch, recorder)

    service = _service(reminder_template_name="payment_reminder")

    result = service.send_payment_reminder_template(
        "15551234567",
        name="John",
        amount=Decimal("20"),
        due_date=date(2026, 7, 30),
    )

    assert result is False


def test_reminder_template_retries_on_transport_error(monkeypatch):

    recorder = RecordingPost(exc=httpx.RequestError("network down"))
    _patch_post(monkeypatch, recorder)

    service = _service(reminder_template_name="payment_reminder")

    result = service.send_payment_reminder_template(
        "15551234567",
        name="John",
        amount=Decimal("20"),
        due_date=date(2026, 7, 30),
    )

    # Transport errors are retried, then reported as a failed delivery.
    assert result is False
    assert len(recorder.calls) > 1
