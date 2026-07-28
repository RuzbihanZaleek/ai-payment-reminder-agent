import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# A JWT signing key shorter than this offers too little entropy for HS256 and is
# rejected at startup so a weak secret can never reach production.
_MIN_JWT_SECRET_LENGTH = 32

_SUPPORTED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}

_APP_ENVIRONMENTS = {"development", "testing", "production"}


def _split_csv(value: str) -> list[str]:
    """Parse a comma-separated env value into a clean list (``*`` -> ["*"])."""

    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    # --- Environment --------------------------------------------------------
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    ENABLE_DOCS: bool = True

    # --- Database -----------------------------------------------------------
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800  # seconds; recycle connections before the DB drops them
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    # --- OpenAI -------------------------------------------------------------
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.5"

    # --- WhatsApp (Meta Cloud API) ------------------------------------------
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_API_VERSION: str = "v25.0"

    # --- Authentication / JWT ----------------------------------------------
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # --- CORS ---------------------------------------------------------------
    # Comma-separated; "*" allows all. Exposed as lists via the properties below.
    CORS_ALLOW_ORIGINS: str = "*"
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    # --- Background scheduler ----------------------------------------------
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_HOUR: int = 9
    SCHEDULER_MINUTE: int = 0
    # If a run is missed (app was down), allow it to fire within this window,
    # coalesced into a single run -- never a burst of catch-up runs.
    SCHEDULER_MISFIRE_GRACE_TIME: int = 3600
    # PostgreSQL advisory-lock key guarding the daily reminder job so only one
    # replica executes it. An arbitrary but stable 64-bit integer.
    SCHEDULER_LOCK_ID: int = 902_025_105

    # --- WhatsApp delivery reliability -------------------------------------
    WHATSAPP_MAX_RETRIES: int = 3
    WHATSAPP_RETRY_DELAY_SECONDS: int = 2
    WHATSAPP_TIMEOUT_SECONDS: float = 10.0

    # --- Notifications ------------------------------------------------------
    # "direct" sends inline during the workflow (current behavior);
    # "outbox" records a PENDING NotificationOutbox row instead, delivered
    # out-of-band by the notification worker. Default preserves existing behavior.
    NOTIFICATION_MODE: str = "direct"

    # Background notification worker (drains the outbox).
    NOTIFICATION_WORKER_ENABLED: bool = True
    NOTIFICATION_WORKER_INTERVAL_SECONDS: int = 60
    NOTIFICATION_MAX_RETRIES: int = 3
    NOTIFICATION_WORKER_BATCH_SIZE: int = 50
    # Advisory-lock key so only one replica's worker runs at a time (distinct
    # from the reminder scheduler's lock).
    NOTIFICATION_WORKER_LOCK_ID: int = 902_025_106
    # A message stuck in PROCESSING longer than this is presumed abandoned (a
    # crashed worker) and returned to PENDING.
    NOTIFICATION_PROCESSING_TIMEOUT_MINUTES: int = 15
    # Emit an alert when a single worker pass fails at least this many messages.
    NOTIFICATION_FAILURE_ALERT_THRESHOLD: int = 10

    # --- Proactive AI financial analysis -----------------------------------
    PROACTIVE_ANALYSIS_ENABLED: bool = True
    PROACTIVE_ANALYSIS_INTERVAL_SECONDS: int = 86_400  # daily
    # Advisory-lock key so only one replica runs proactive analysis (distinct
    # from the reminder + notification-worker locks).
    PROACTIVE_ANALYSIS_LOCK_ID: int = 902_025_107

    # --- Rate limiting ------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_REGISTER_PER_MINUTE: int = 5
    RATE_LIMIT_WEBHOOK_PER_MINUTE: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # --- Derived helpers ----------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"

    @property
    def cors_allow_origins(self) -> list[str]:
        return _split_csv(self.CORS_ALLOW_ORIGINS)

    @property
    def cors_allow_methods(self) -> list[str]:
        return _split_csv(self.CORS_ALLOW_METHODS)

    @property
    def cors_allow_headers(self) -> list[str]:
        return _split_csv(self.CORS_ALLOW_HEADERS)

    # --- Field validation ---------------------------------------------------
    @field_validator("APP_ENV")
    @classmethod
    def _validate_app_env(cls, value: str) -> str:
        if value not in _APP_ENVIRONMENTS:
            raise ValueError(f"APP_ENV must be one of {sorted(_APP_ENVIRONMENTS)}.")
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        if value.upper() not in logging.getLevelNamesMapping():
            raise ValueError("LOG_LEVEL must be a valid logging level (e.g. INFO, DEBUG).")
        return value.upper()

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if len(value) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                "JWT_SECRET_KEY must be at least "
                f"{_MIN_JWT_SECRET_LENGTH} characters long."
            )
        return value

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def _validate_jwt_algorithm(cls, value: str) -> str:
        if value not in _SUPPORTED_JWT_ALGORITHMS:
            raise ValueError(
                f"JWT_ALGORITHM must be one of {sorted(_SUPPORTED_JWT_ALGORITHMS)}."
            )
        return value

    @field_validator("JWT_EXPIRE_MINUTES")
    @classmethod
    def _validate_jwt_expiry(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("JWT_EXPIRE_MINUTES must be a positive integer.")
        return value

    @field_validator("NOTIFICATION_MODE")
    @classmethod
    def _validate_notification_mode(cls, value: str) -> str:
        if value not in {"direct", "outbox"}:
            raise ValueError("NOTIFICATION_MODE must be 'direct' or 'outbox'.")
        return value

    # --- Production hardening ----------------------------------------------
    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        """Fail fast when production is missing security-critical configuration.

        The core secrets (DATABASE_URL / OPENAI_API_KEY / JWT_SECRET_KEY) are
        already required fields, so this focuses on the settings that are
        optional in dev but mandatory in production.
        """

        if not self.is_production:
            return self

        missing = [
            name
            for name, value in (
                ("WHATSAPP_VERIFY_TOKEN", self.WHATSAPP_VERIFY_TOKEN),
                ("WHATSAPP_ACCESS_TOKEN", self.WHATSAPP_ACCESS_TOKEN),
                ("WHATSAPP_PHONE_NUMBER_ID", self.WHATSAPP_PHONE_NUMBER_ID),
            )
            if not value
        ]

        if missing:
            raise ValueError(
                "The following settings are required when APP_ENV=production: "
                + ", ".join(missing)
            )

        return self


settings = Settings()
