import logging

from piccolo.querystring import QueryString
from telegram import Update
from telegram.ext import ApplicationHandlerStop

from db.engine import DB
from telegram_handlers.context import UserContext

logger = logging.getLogger(__name__)


async def skip_processed_update(update: Update, _context: UserContext) -> None:
    is_new_update = await _record_processed_update(update.update_id)
    if is_new_update:
        return

    logger.info('Skipping duplicate Telegram update %s', update.update_id)
    raise ApplicationHandlerStop


async def _record_processed_update(update_id: int) -> bool:
    result = await DB.run_querystring(
        QueryString(
            """
            INSERT INTO processed_telegram_updates (update_id)
            VALUES ({})
            ON CONFLICT (update_id) DO NOTHING
            RETURNING update_id
            """,
            update_id,
        )
    )
    return bool(result)
