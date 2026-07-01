import logging
from contextlib import suppress
from typing import cast

import openai
from asyncpg import PostgresError
from pydantic import ValidationError
from telegram import Chat, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from db.user import User
from services.vocabulary import (
    VocabularyEntry,
    add_vocabulary_from_text,
    find_or_attach_existing_vocabulary_entry,
    get_vocabulary_entry,
)
from telegram_handlers.decorators import DB_USER_CONTEXT_KEY, with_db_user
from telegram_handlers.review import (
    REVIEW_SESSION_CONTEXT_KEY,
    handle_review_text_answer,
)


logger = logging.getLogger(__name__)


@with_db_user
async def add_word(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    client: openai.AsyncOpenAI,
    llm_model: str,
    prompt_version: int,
) -> None:
    if not update.effective_message:
        return

    if not _is_private_chat(update):
        return

    tg_message = update.effective_message
    if not tg_message.text:
        return

    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    if context.user_data.get(REVIEW_SESSION_CONTEXT_KEY):
        await handle_review_text_answer(
            update,
            context,
            user=db_user,
            answer=tg_message.text.strip(),
        )
        return

    try:
        existing_entry = await find_or_attach_existing_vocabulary_entry(
            user=db_user,
            text=tg_message.text,
        )
    except PostgresError:
        logger.exception("Failed to find existing vocabulary entry")
        await tg_message.reply_text(
            "Failed to check the vocabulary entry. Please try again.",
            do_quote=True,
        )
        return

    if existing_entry is not None:
        await tg_message.reply_text(
            _format_vocabulary_entry(existing_entry, already_saved=True),
            do_quote=True,
        )
        return

    status_message = await tg_message.reply_text("Generating vocabulary entry...")
    try:
        user_word = await add_vocabulary_from_text(
            user=db_user,
            text=tg_message.text.strip(),
            client=client,
            llm_model=llm_model,
            prompt_version=prompt_version,
        )
        entry = await get_vocabulary_entry(user_word=user_word)
    except openai.APITimeoutError:
        logger.exception("OpenAI vocabulary generation timed out")
        await status_message.edit_text(
            "OpenAI took too long to answer. Please try again."
        )
        return
    except openai.APIConnectionError:
        logger.exception("OpenAI connection failed")
        await status_message.edit_text(
            "OpenAI connection failed. Please try again."
        )
        return
    except openai.APIError:
        logger.exception("OpenAI API failed")
        await status_message.edit_text("OpenAI failed. Please try again.")
        return
    except ValidationError:
        logger.exception("OpenAI returned an invalid vocabulary response")
        await status_message.edit_text(
            "OpenAI returned an invalid vocabulary response. Please try again."
        )
        return
    except PostgresError:
        logger.exception("Failed to save vocabulary generation")
        await status_message.edit_text(
            "Failed to save the vocabulary entry. Please try again."
        )
        return

    with suppress(TelegramError):
        await status_message.delete()
    await tg_message.reply_text(
        _format_vocabulary_entry(entry, already_saved=False)
        if entry is not None
        else "Your word is saved, okay :)",
        do_quote=True,
    )


def _is_private_chat(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.type == Chat.PRIVATE


def _format_vocabulary_entry(
    entry: VocabularyEntry,
    *,
    already_saved: bool,
) -> str:
    header = (
        "✅ Already in your vocabulary"
        if already_saved
        else "✅ Saved to your vocabulary"
    )
    title = entry.lemma
    if entry.cefr_level:
        title = f"{title} · {entry.cefr_level}"

    parts = [
        header,
        title,
        f"🇷🇺  Перевод\n{', '.join(entry.translations_ru)}",
        f"📖 Значение\n{entry.simple_explanation_en or entry.definition_en}",
    ]
    if entry.example_en:
        example = f"💬 Пример\n{entry.example_en}"
        if entry.example_ru:
            example = f"{example}\n\n{entry.example_ru}"
        parts.append(example)
    elif entry.example_ru:
        parts.append(f"💬 Пример\n{entry.example_ru}")
    if entry.synonyms:
        parts.append(f"🔁 Синонимы\n{_format_bullets(entry.synonyms)}")
    if entry.collocations:
        parts.append(f"🔗 Частые сочетания\n{_format_bullets(entry.collocations)}")
    if entry.usage_note_ru:
        parts.append(f"💡 Обрати внимание\n{entry.usage_note_ru}")

    return "\n\n".join(parts)


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"• {item}" for item in items)
    if entry.example_ru:
        parts.append(f"RU: {entry.example_ru}")
    if entry.collocations:
        parts.append(f"Collocations: {', '.join(entry.collocations[:4])}")
    if entry.usage_note_ru:
        parts.append(f"Note: {entry.usage_note_ru}")

    return "\n\n".join(parts)
