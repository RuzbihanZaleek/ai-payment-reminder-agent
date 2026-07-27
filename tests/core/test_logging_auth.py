"""Authentication logging: events are emitted; secrets never are."""

import logging
from types import SimpleNamespace

from app.services.auth_service import AuthService, EmailAlreadyRegisteredError


_PASSWORD = "SuperSecretPW-do-not-log-12345"


class FakeUserRepository:

    def __init__(self, existing=None):
        self.existing = existing
        self.created = None

    def get_by_email(self, email):
        return self.existing

    def create(self, user):
        user.id = 1
        self.created = user
        return user


def _events(caplog):
    return {r.getMessage() for r in caplog.records}


def _no_password_leaked(caplog):
    for record in caplog.records:
        # Neither the rendered message nor any structured/extra attribute may
        # contain the raw password.
        assert _PASSWORD not in record.getMessage()
        for value in record.__dict__.values():
            assert _PASSWORD not in str(value)


def test_successful_registration_is_logged(caplog):
    caplog.set_level(logging.INFO)
    service = AuthService(FakeUserRepository(existing=None))

    service.register("a@b.com", _PASSWORD)

    assert "auth_register_success" in _events(caplog)
    _no_password_leaked(caplog)


def test_duplicate_registration_is_logged(caplog):
    caplog.set_level(logging.INFO)
    service = AuthService(FakeUserRepository(existing=SimpleNamespace(id=1)))

    try:
        service.register("a@b.com", _PASSWORD)
    except EmailAlreadyRegisteredError:
        pass

    assert "auth_register_failed" in _events(caplog)
    _no_password_leaked(caplog)


def test_successful_login_is_logged(caplog):
    from app.core.security import hash_password

    caplog.set_level(logging.INFO)
    user = SimpleNamespace(id=7, hashed_password=hash_password(_PASSWORD))
    service = AuthService(FakeUserRepository(existing=user))

    result = service.authenticate("a@b.com", _PASSWORD)

    assert result is user
    assert "auth_login_success" in _events(caplog)
    _no_password_leaked(caplog)


def test_failed_login_wrong_password_is_logged_with_reason(caplog):
    from app.core.security import hash_password

    caplog.set_level(logging.INFO)
    user = SimpleNamespace(id=7, hashed_password=hash_password("the-real-password"))
    service = AuthService(FakeUserRepository(existing=user))

    result = service.authenticate("a@b.com", _PASSWORD)

    assert result is None
    assert "auth_login_failed" in _events(caplog)
    reasons = {getattr(r, "reason", None) for r in caplog.records}
    assert "invalid_password" in reasons
    _no_password_leaked(caplog)


def test_failed_login_unknown_user_is_logged_with_reason(caplog):
    caplog.set_level(logging.INFO)
    service = AuthService(FakeUserRepository(existing=None))

    result = service.authenticate("nobody@b.com", _PASSWORD)

    assert result is None
    reasons = {getattr(r, "reason", None) for r in caplog.records}
    assert "user_not_found" in reasons
    _no_password_leaked(caplog)
