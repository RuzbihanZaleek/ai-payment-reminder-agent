from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.5"

    WHATSAPP_VERIFY_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()