import logging
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, Concatenate

from asyncpg import PostgresError
from telegram import Update

from services.users import upsert_telegram_user
from telegram_handlers.context import UserContext

logger = logging.getLogger(__name__)
DB_USER_CONTEXT_KEY = 'db_user'
type Handler[**P] = Callable[Concatenate[Update, UserContext, P], Coroutine[Any, Any, Any]]


def with_db_user[**P](handler: Handler[P]) -> Handler[P]:
    @wraps(handler)
    async def wrapper(
        update: Update,
        context: UserContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Any:
        if not update.effective_user or not update.effective_chat:
            return None

        try:
            db_user = await upsert_telegram_user(
                telegram_user=update.effective_user,
                chat=update.effective_chat,
            )
        except PostgresError:
            logger.exception('Failed to save Telegram user')
            if update.effective_message:
                await update.effective_message.reply_text(
                    'Failed to save your user profile. Please try again.',
                    do_quote=True,
                )
            return None

        context.user_data[DB_USER_CONTEXT_KEY] = db_user
        return await handler(update, context, *args, **kwargs)

    return wrapper
