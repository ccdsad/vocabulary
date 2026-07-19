import argparse
import asyncio
import logging

from telegram import Bot
from telegram.request import HTTPXRequest

from config.app import get_telegram_settings
from telegram_handlers.review_jobs import send_review_reminders

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog='vocabulary')
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('bot', help='Run the Telegram webhook bot')
    subparsers.add_parser('send-review-reminders', help='Send due review reminders once and exit')

    args = parser.parse_args()
    if args.command == 'bot':
        from main import run_bot  # noqa: PLC0415

        run_bot()
        return

    if args.command == 'send-review-reminders':
        sent_count = asyncio.run(_send_review_reminders())
        logger.info('Sent %s review reminders', sent_count)
        return

    parser.error(f'Unknown command: {args.command}')


async def _send_review_reminders() -> int:
    telegram_settings = get_telegram_settings()
    request = HTTPXRequest(
        connect_timeout=telegram_settings.telegram_connect_timeout_seconds,
        read_timeout=telegram_settings.telegram_read_timeout_seconds,
    )
    async with Bot(token=telegram_settings.tg_access_token, request=request) as bot:
        return await send_review_reminders(bot)


if __name__ == '__main__':
    main()
