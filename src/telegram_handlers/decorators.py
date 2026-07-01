import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from asyncpg import PostgresError
from telegram import Update
from telegram.ext import ContextTypes

from services.users import upsert_telegram_user


logger = logging.getLogger(__name__)
DB_USER_CONTEXT_KEY = "db_user"
Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]


def with_db_user(handler: Handler) -> Handler:
    @wraps(handler)
    async def wrapper(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if not update.effective_user or not update.effective_chat:
            return None

        try:
            db_user = await upsert_telegram_user(
                telegram_user=update.effective_user,
                chat=update.effective_chat,
            )
        except PostgresError:
            logger.exception("Failed to save Telegram user")
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Failed to save your user profile. Please try again.",
                    do_quote=True,
                )
            return None

        context.user_data[DB_USER_CONTEXT_KEY] = db_user
        return await handler(update, context, *args, **kwargs)

    return wrapper
