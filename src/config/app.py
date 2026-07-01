from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    tg_access_token: str = Field(validation_alias="TG_ACCESS_TOKEN")
    openai_model: str = Field(default="gpt-5.4-mini", validation_alias="OPENAI_MODEL")
    openai_timeout_seconds: float = Field(
        default=12.0,
        validation_alias="OPENAI_TIMEOUT_SECONDS",
    )
    telegram_connect_timeout_seconds: float = Field(
        default=15.0,
        validation_alias="TELEGRAM_CONNECT_TIMEOUT_SECONDS",
    )
    telegram_read_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="TELEGRAM_READ_TIMEOUT_SECONDS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


app_settings = AppSettings()
