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


# --- APP_ENV / LOG_LEVEL ----------------------------------------------------

def test_invalid_app_env_is_rejected():
    with pytest.raises(ValidationError):
        _settings(APP_ENV="staging")


def test_invalid_log_level_is_rejected():
    with pytest.raises(ValidationError):
        _settings(LOG_LEVEL="LOUD")


def test_log_level_is_normalized_to_upper():
    assert _settings(LOG_LEVEL="debug").LOG_LEVEL == "DEBUG"


# --- Production hardening ----------------------------------------------------

def test_development_allows_missing_optional_config():
    # No WhatsApp credentials, defaults everywhere -> fine in development.
    settings = _settings(APP_ENV="development")
    assert settings.is_production is False


def test_production_requires_whatsapp_credentials():
    with pytest.raises(ValidationError):
        _settings(APP_ENV="production")  # WhatsApp creds missing


def test_production_succeeds_with_full_config():
    settings = _settings(
        APP_ENV="production",
        WHATSAPP_VERIFY_TOKEN="vt",
        WHATSAPP_ACCESS_TOKEN="at",
        WHATSAPP_PHONE_NUMBER_ID="pid",
    )
    assert settings.is_production is True


def test_production_still_enforces_secure_jwt_secret():
    with pytest.raises(ValidationError):
        _settings(
            APP_ENV="production",
            JWT_SECRET_KEY="short",
            WHATSAPP_VERIFY_TOKEN="vt",
            WHATSAPP_ACCESS_TOKEN="at",
            WHATSAPP_PHONE_NUMBER_ID="pid",
        )


# --- CORS parsing -----------------------------------------------------------

def test_cors_csv_is_parsed_into_list():
    settings = _settings(CORS_ALLOW_ORIGINS="https://a.com, https://b.com")
    assert settings.cors_allow_origins == ["https://a.com", "https://b.com"]


def test_cors_wildcard_default():
    assert _settings().cors_allow_origins == ["*"]
