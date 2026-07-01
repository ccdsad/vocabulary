from piccolo.engine.postgres import PostgresEngine

from config.db import db_settings


DB = PostgresEngine(
    config={"dsn": db_settings.database_dsn},
)
