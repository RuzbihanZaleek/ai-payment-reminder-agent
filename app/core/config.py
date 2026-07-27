from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# A JWT signing key shorter than this offers too little entropy for HS256 and is
# rejected at startup so a weak secret can never reach production.
_MIN_JWT_SECRET_LENGTH = 32

_SUPPORTED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


class Settings(BaseSettings):
    DATABASE_URL: str

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.5"

    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_API_VERSION: str = "v25.0"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

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


settings = Settings()