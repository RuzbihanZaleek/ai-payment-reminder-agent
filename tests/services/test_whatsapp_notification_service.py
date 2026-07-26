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


def _service():

    return WhatsAppNotificationService(
        access_token="TOKEN_ABC",
        phone_number_id="PHONE_123",
        api_version="v21.0",
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
