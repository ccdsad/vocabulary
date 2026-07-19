import logging
from typing import Protocol

from asyncpg import PostgresError
from telegram.error import TelegramError

from services.review import count_due_user_words
from services.users import get_all_users

logger = logging.getLogger(__name__)


class MessageSender(Protocol):
    async def send_message(self, chat_id: int, text: str) -> object: ...


async def send_review_reminders(bot: MessageSender) -> int:
    try:
        users = await get_all_users()
    except PostgresError:
        logger.exception('Failed to load users for review reminders')
        return 0

    sent_count = 0
    for user in users:
        try:
            due_count = await count_due_user_words(user=user)
        except PostgresError:
            logger.exception('Failed to count due review words for user %s', user.id)
            continue

        if due_count == 0:
            continue

        try:
            await bot.send_message(
                chat_id=int(user.chat_id),
                text=f'You have {due_count} words due for review. Send /review to start.',
            )
        except TelegramError:
            logger.exception('Failed to send review reminder to chat %s', user.chat_id)
            continue

        sent_count += 1
    return sent_count
