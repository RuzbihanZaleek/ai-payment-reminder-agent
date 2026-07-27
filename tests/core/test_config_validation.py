"""Startup validation of required configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


_BASE = dict(
    DATABASE_URL="postgresql://localhost/db",
    OPENAI_API_KEY="sk-test",
    JWT_SECRET_KEY="x" * 32,
)


def _settings(**overrides):
    # _env_file=None so the developer's real .env never influences the test.
    return Settings(_env_file=None, **{**_BASE, **overrides})


def test_valid_settings_load():
    settings = _settings()
    assert settings.JWT_ALGORITHM == "HS256"


def test_short_jwt_secret_is_rejected():
    with pytest.raises(ValidationError):
        _settings(JWT_SECRET_KEY="too-short")


def test_unsupported_jwt_algorithm_is_rejected():
    with pytest.raises(ValidationError):
        _settings(JWT_ALGORITHM="none")


def test_non_positive_jwt_expiry_is_rejected():
    with pytest.raises(ValidationError):
        _settings(JWT_EXPIRE_MINUTES=0)
