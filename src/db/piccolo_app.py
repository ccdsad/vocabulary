from pathlib import Path

from piccolo.conf.apps import AppConfig

from db import TABLES


APP_CONFIG = AppConfig(
    app_name="db",
    migrations_folder_path=Path(__file__).parents[2] / "db" / "migrations",
    table_classes=TABLES,
)
