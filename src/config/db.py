from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    database_dsn: str = Field(validation_alias='DATABASE_DSN')

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )


db_settings = DatabaseSettings()
