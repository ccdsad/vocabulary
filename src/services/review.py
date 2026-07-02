from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any

from db.user import User
from db.user_word import UserWord
from db.word import Word
from db.word_meaning import WordMeaning
from enums import UserWordStatus

DEFAULT_REVIEW_LIMIT = 20
MIN_EASE_FACTOR = Decimal('1.30')


class ReviewGrade(StrEnum):
    AGAIN = 'again'
    HARD = 'hard'
    GOOD = 'good'
    EASY = 'easy'


@dataclass(frozen=True)
class ReviewCard:
    user_word_id: int
    lemma: str
    transcription: str | None
    translations_ru: list[str]
    definition_en: str
    simple_explanation_en: str | None
    example_en: str | None
    example_ru: str | None


async def get_due_user_word_ids(
    *,
    user: User,
    limit: int = DEFAULT_REVIEW_LIMIT,
    now: datetime | None = None,
) -> list[int]:
    now = now or datetime.now(UTC)
    rows = (
        await UserWord.select(UserWord.id, UserWord.next_review_at)
        .where((UserWord.user == user.id) & (UserWord.status != UserWordStatus.SUSPENDED.value))
        .order_by(UserWord.next_review_at)
        .run()
    )
    due_rows = [row for row in rows if row['next_review_at'] is None or row['next_review_at'] <= now]
    return [int(row['id']) for row in due_rows[:limit]]


async def count_due_user_words(
    *,
    user: User,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    rows = (
        await UserWord.select(UserWord.next_review_at)
        .where((UserWord.user == user.id) & (UserWord.status != UserWordStatus.SUSPENDED.value))
        .run()
    )
    return sum(1 for row in rows if row['next_review_at'] is None or row['next_review_at'] <= now)


async def get_review_card(*, user: User, user_word_id: int) -> ReviewCard | None:
    user_word = await UserWord.objects().where((UserWord.id == user_word_id) & (UserWord.user == user.id)).first()
    if user_word is None:
        return None

    word = await Word.objects().where(Word.id == _db_id(user_word.word)).first()
    meaning = await WordMeaning.objects().where(WordMeaning.id == _db_id(user_word.meaning)).first()
    if word is None or meaning is None:
        return None

    return ReviewCard(
        user_word_id=int(user_word.id),
        lemma=word.lemma,
        transcription=word.transcription,
        translations_ru=list(meaning.translations_ru),
        definition_en=meaning.definition_en,
        simple_explanation_en=meaning.simple_explanation_en,
        example_en=meaning.example_en,
        example_ru=meaning.example_ru,
    )


async def apply_review_grade(
    *,
    user: User,
    user_word_id: int,
    grade: ReviewGrade,
    now: datetime | None = None,
) -> UserWord | None:
    now = now or datetime.now(UTC)
    user_word = await UserWord.objects().where((UserWord.id == user_word_id) & (UserWord.user == user.id)).first()
    if user_word is None:
        return None

    ease_factor = Decimal(user_word.ease_factor)
    interval_days = int(user_word.interval_days)
    repetitions = int(user_word.repetitions)
    lapses = int(user_word.lapses)

    if grade == ReviewGrade.AGAIN:
        repetitions = 0
        lapses += 1
        ease_factor = max(MIN_EASE_FACTOR, ease_factor - Decimal('0.20'))
        interval_days = 0
        next_review_at = now + timedelta(minutes=10)
        status = UserWordStatus.LEARNING.value
    elif grade == ReviewGrade.HARD:
        ease_factor = max(MIN_EASE_FACTOR, ease_factor - Decimal('0.15'))
        interval_days = 1 if interval_days == 0 else max(1, round(interval_days * 1.2))
        repetitions += 1
        next_review_at = now + timedelta(days=interval_days)
        status = UserWordStatus.REVIEW.value
    elif grade == ReviewGrade.GOOD:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 3
        else:
            interval_days = max(1, round(interval_days * float(ease_factor)))
        repetitions += 1
        next_review_at = now + timedelta(days=interval_days)
        status = UserWordStatus.REVIEW.value
    else:
        ease_factor += Decimal('0.15')
        if repetitions == 0:
            interval_days = 3
        elif repetitions == 1:
            interval_days = 7
        else:
            interval_days = max(1, round(interval_days * float(ease_factor) * 1.3))
        repetitions += 1
        next_review_at = now + timedelta(days=interval_days)
        status = UserWordStatus.REVIEW.value

    user_word.ease_factor = ease_factor
    user_word.interval_days = interval_days
    user_word.repetitions = repetitions
    user_word.lapses = lapses
    user_word.status = status
    user_word.last_reviewed_at = now
    user_word.next_review_at = next_review_at
    await user_word.save(
        columns=[
            UserWord.ease_factor,
            UserWord.interval_days,
            UserWord.repetitions,
            UserWord.lapses,
            UserWord.status,
            UserWord.last_reviewed_at,
            UserWord.next_review_at,
        ]
    ).run()
    return user_word


def _db_id(value: Any) -> int:
    return int(value.id if hasattr(value, 'id') else value)
