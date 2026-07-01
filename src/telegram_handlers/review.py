import logging
import re
from typing import Any, cast

from asyncpg import PostgresError
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db.user import User
from services.review import (
    DEFAULT_REVIEW_LIMIT,
    ReviewCard,
    ReviewGrade,
    apply_review_grade,
    count_due_user_words,
    get_due_user_word_ids,
    get_review_card,
)
from telegram_handlers.decorators import DB_USER_CONTEXT_KEY, with_db_user


logger = logging.getLogger(__name__)
REVIEW_SESSION_CONTEXT_KEY = "review_session"
REVIEW_SHOW_CALLBACK = "review:show"
REVIEW_GRADE_CALLBACK_PREFIX = "review:grade:"


@with_db_user
async def start_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    if not _is_private_chat(update):
        return

    if context.user_data.get(REVIEW_SESSION_CONTEXT_KEY):
        await update.effective_message.reply_text(
            "Review is already in progress. Use /cancel to stop it."
        )
        return

    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    try:
        user_word_ids = await get_due_user_word_ids(
            user=db_user,
            limit=DEFAULT_REVIEW_LIMIT,
        )
    except PostgresError:
        logger.exception("Failed to load due review words")
        await update.effective_message.reply_text(
            "Failed to load review words. Please try again."
        )
        return

    if not user_word_ids:
        await update.effective_message.reply_text("No words to review now.")
        return

    context.user_data[REVIEW_SESSION_CONTEXT_KEY] = {
        "user_word_ids": user_word_ids,
        "index": 0,
        "reviewed": 0,
        ReviewGrade.AGAIN.value: 0,
        ReviewGrade.HARD.value: 0,
        ReviewGrade.GOOD.value: 0,
        ReviewGrade.EASY.value: 0,
    }
    await update.effective_message.reply_text(
        f"Review started: {len(user_word_ids)} words due."
    )
    await _reply_with_current_review_card(update, context)


@with_db_user
async def cancel_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    if not _is_private_chat(update):
        return

    session = context.user_data.pop(REVIEW_SESSION_CONTEXT_KEY, None)
    if not session:
        await update.effective_message.reply_text("Nothing to cancel.")
        return

    reviewed = int(session["reviewed"])
    remaining = max(0, len(session["user_word_ids"]) - int(session["index"]))
    await update.effective_message.reply_text(
        f"Review cancelled.\n\nReviewed this session: {reviewed}\nRemaining due: {remaining}"
    )


@with_db_user
async def show_review_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    session = context.user_data.get(REVIEW_SESSION_CONTEXT_KEY)
    if not session:
        await query.edit_message_text("No active review. Send /review to start.")
        return

    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    card = await _get_current_review_card(db_user, session)
    if card is None:
        await _advance_missing_card(update, context)
        return

    await query.edit_message_text(
        _format_review_answer(card, session),
        reply_markup=_review_grade_keyboard(),
    )


@with_db_user
async def grade_review_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    await query.answer()
    session = context.user_data.get(REVIEW_SESSION_CONTEXT_KEY)
    if not session:
        await query.edit_message_text("No active review. Send /review to start.")
        return

    grade_value = query.data.removeprefix(REVIEW_GRADE_CALLBACK_PREFIX)
    try:
        grade = ReviewGrade(grade_value)
    except ValueError:
        await query.edit_message_text("Unknown review result. Send /review to restart.")
        context.user_data.pop(REVIEW_SESSION_CONTEXT_KEY, None)
        return

    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    user_word_id = int(session["user_word_ids"][int(session["index"])])
    try:
        reviewed_word = await apply_review_grade(
            user=db_user,
            user_word_id=user_word_id,
            grade=grade,
        )
    except PostgresError:
        logger.exception("Failed to save review grade")
        await query.edit_message_text("Failed to save review result. Please try again.")
        return

    if reviewed_word is not None:
        session["reviewed"] = int(session["reviewed"]) + 1
        session[grade.value] = int(session[grade.value]) + 1
    session["index"] = int(session["index"]) + 1

    await _edit_to_current_review_card(update, context)


async def handle_review_text_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    user: User,
    answer: str,
) -> None:
    if update.effective_message is None:
        return

    session = context.user_data.get(REVIEW_SESSION_CONTEXT_KEY)
    if not session:
        return

    card = await _get_current_review_card(user, session)
    if card is None:
        await _advance_missing_card(update, context)
        return

    is_correct = _normalize_answer(answer) == _normalize_answer(card.lemma)
    prefix = "Looks correct." if is_correct else "Not quite."
    await update.effective_message.reply_text(
        f"{prefix}\n\n{_format_review_answer(card, session)}",
        reply_markup=_review_grade_keyboard(),
        do_quote=True,
    )


async def _reply_with_current_review_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if update.effective_message is None:
        return

    session = context.user_data[REVIEW_SESSION_CONTEXT_KEY]
    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    card = await _get_current_review_card(db_user, session)
    if card is None:
        await _advance_missing_card(update, context)
        return

    await update.effective_message.reply_text(
        _format_review_front(card, session),
        reply_markup=_show_answer_keyboard(),
    )


async def _edit_to_current_review_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    session = context.user_data[REVIEW_SESSION_CONTEXT_KEY]
    if int(session["index"]) >= len(session["user_word_ids"]):
        await _finish_review(update, context)
        return

    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    card = await _get_current_review_card(db_user, session)
    if card is None:
        await _advance_missing_card(update, context)
        return

    await query.edit_message_text(
        _format_review_front(card, session),
        reply_markup=_show_answer_keyboard(),
    )


async def _advance_missing_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    session = context.user_data[REVIEW_SESSION_CONTEXT_KEY]
    session["index"] = int(session["index"]) + 1
    await _edit_to_current_review_card(update, context)


async def _finish_review(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    session = context.user_data.pop(REVIEW_SESSION_CONTEXT_KEY)
    db_user = cast(User, context.user_data[DB_USER_CONTEXT_KEY])
    try:
        due_now = await count_due_user_words(user=db_user)
    except PostgresError:
        logger.exception("Failed to count due review words")
        due_now = None

    text = (
        "Review complete.\n\n"
        f"Reviewed: {session['reviewed']}\n"
        f"Again: {session[ReviewGrade.AGAIN.value]}\n"
        f"Hard: {session[ReviewGrade.HARD.value]}\n"
        f"Good: {session[ReviewGrade.GOOD.value]}\n"
        f"Easy: {session[ReviewGrade.EASY.value]}"
    )
    if due_now is not None:
        text += f"\n\nDue now: {due_now}"

    if query is not None:
        await query.edit_message_text(text)


async def _get_current_review_card(
    user: User,
    session: dict[str, Any],
) -> ReviewCard | None:
    index = int(session["index"])
    user_word_id = int(session["user_word_ids"][index])
    return await get_review_card(user=user, user_word_id=user_word_id)


def _format_review_front(card: ReviewCard, session: dict[str, Any]) -> str:
    return (
        f"{_position_text(session)}\n\n"
        "Translate or recall:\n\n"
        f"{', '.join(card.translations_ru)}"
    )


def _format_review_answer(card: ReviewCard, session: dict[str, Any]) -> str:
    transcription = f" {card.transcription}" if card.transcription else ""
    parts = [
        _position_text(session),
        f"{', '.join(card.translations_ru)}",
        f"Answer:\n{card.lemma}{transcription}",
        f"Meaning:\n{card.simple_explanation_en or card.definition_en}",
    ]
    if card.example_en:
        parts.append(f"Example:\n{card.example_en}")
    if card.example_ru:
        parts.append(card.example_ru)
    parts.append("How well did you remember it?")
    return "\n\n".join(parts)


def _position_text(session: dict[str, Any]) -> str:
    return f"{int(session['index']) + 1}/{len(session['user_word_ids'])}"


def _normalize_answer(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _show_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Show answer", callback_data=REVIEW_SHOW_CALLBACK)]]
    )


def _review_grade_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Again",
                    callback_data=f"{REVIEW_GRADE_CALLBACK_PREFIX}{ReviewGrade.AGAIN.value}",
                ),
                InlineKeyboardButton(
                    "Hard",
                    callback_data=f"{REVIEW_GRADE_CALLBACK_PREFIX}{ReviewGrade.HARD.value}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "Good",
                    callback_data=f"{REVIEW_GRADE_CALLBACK_PREFIX}{ReviewGrade.GOOD.value}",
                ),
                InlineKeyboardButton(
                    "Easy",
                    callback_data=f"{REVIEW_GRADE_CALLBACK_PREFIX}{ReviewGrade.EASY.value}",
                ),
            ],
        ]
    )


def _is_private_chat(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.type == Chat.PRIVATE
