from functools import partial

import openai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from config.app import app_settings
from healthcheck import start_healthcheck_server
from telegram_handlers.context import USER_CONTEXT_TYPES
from telegram_handlers.review import (
    REVIEW_GRADE_CALLBACK_PREFIX,
    REVIEW_SHOW_CALLBACK,
    cancel_review,
    grade_review_answer,
    show_review_answer,
    start_review,
)
from telegram_handlers.vocabulary import add_word

PROMPT_VERSION = 1


if __name__ == '__main__':
    start_healthcheck_server()
    client = openai.AsyncOpenAI(
        api_key=app_settings.openai_api_key,
        timeout=app_settings.openai_timeout_seconds,
        max_retries=0,
    )
    request = HTTPXRequest(
        connect_timeout=app_settings.telegram_connect_timeout_seconds,
        read_timeout=app_settings.telegram_read_timeout_seconds,
    )
    get_updates_request = HTTPXRequest(
        connect_timeout=app_settings.telegram_connect_timeout_seconds,
        read_timeout=app_settings.telegram_read_timeout_seconds,
    )
    app = (
        ApplicationBuilder()
        .token(app_settings.tg_access_token)
        .context_types(USER_CONTEXT_TYPES)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )
    app.add_handler(CommandHandler('review', start_review))
    app.add_handler(CommandHandler('cancel', cancel_review))
    app.add_handler(CallbackQueryHandler(show_review_answer, pattern=f'^{REVIEW_SHOW_CALLBACK}$'))
    app.add_handler(
        CallbackQueryHandler(
            grade_review_answer,
            pattern=f'^{REVIEW_GRADE_CALLBACK_PREFIX}',
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            partial(
                add_word,
                client=client,
                llm_model=app_settings.openai_model,
                prompt_version=PROMPT_VERSION,
            ),
        )
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)
