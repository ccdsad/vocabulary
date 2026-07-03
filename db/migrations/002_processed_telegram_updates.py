from typing import cast

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.engine.base import Engine
from piccolo.engine.finder import engine_finder

ID = '002'
VERSION = '1.34.0'
DESCRIPTION = 'Track processed Telegram updates'


async def run_statements(statements: list[str]) -> None:
    engine = cast(Engine, engine_finder())
    for statement in statements:
        await engine.run_ddl(statement)


async def forwards() -> MigrationManager:
    manager = MigrationManager(
        migration_id=ID,
        app_name='db',
        description=DESCRIPTION,
    )

    async def run() -> None:
        await run_statements(
            [
                """
            CREATE TABLE processed_telegram_updates
            (
                update_id    BIGINT PRIMARY KEY,
                processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            ]
        )

    async def backwards() -> None:
        await run_statements(['DROP TABLE IF EXISTS processed_telegram_updates'])

    manager.add_raw(run)
    manager.add_raw_backwards(backwards)

    return manager
