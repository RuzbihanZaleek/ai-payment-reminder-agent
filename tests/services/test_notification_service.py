import pytest

from app.services.notification_service import (
    NotificationService,
    FakeNotificationService,
)


def test_fake_service_returns_true():

    service = FakeNotificationService()

    result = service.send("chat_123", "Hello")

    assert result is True


def test_base_service_is_abstract():

    service = NotificationService()

    with pytest.raises(NotImplementedError):
        service.send("chat_123", "Hello")
