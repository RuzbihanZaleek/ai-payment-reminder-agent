import pytest

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.services.auth_service import AuthService, EmailAlreadyRegisteredError


def test_password_hash_and_verify():

    hashed = hash_password("s3cret")

    assert hashed != "s3cret"
    assert verify_password("s3cret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_password_hash_is_salted():

    assert hash_password("same") != hash_password("same")


def test_jwt_roundtrip():

    token = create_access_token(42)

    assert decode_access_token(token) == 42


def test_jwt_invalid_returns_none():

    assert decode_access_token("not-a-token") is None


class FakeUserRepository:

    def __init__(self):
        self.by_email = {}
        self._next_id = 1

    def get_by_email(self, email):
        return self.by_email.get(email)

    def get_by_id(self, user_id):
        return next((u for u in self.by_email.values() if u.id == user_id), None)

    def create(self, user):
        user.id = self._next_id
        self._next_id += 1
        self.by_email[user.email] = user
        return user


def test_register_creates_hashed_user():

    service = AuthService(FakeUserRepository())

    user = service.register("a@b.com", "pw")

    assert user.id is not None
    assert user.email == "a@b.com"
    assert user.hashed_password != "pw"


def test_register_duplicate_email_raises():

    service = AuthService(FakeUserRepository())
    service.register("a@b.com", "pw")

    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("a@b.com", "other")


def test_authenticate_success():

    service = AuthService(FakeUserRepository())
    service.register("a@b.com", "pw")

    assert service.authenticate("a@b.com", "pw") is not None


def test_authenticate_wrong_password():

    service = AuthService(FakeUserRepository())
    service.register("a@b.com", "pw")

    assert service.authenticate("a@b.com", "nope") is None


def test_authenticate_unknown_email():

    service = AuthService(FakeUserRepository())

    assert service.authenticate("missing@b.com", "pw") is None