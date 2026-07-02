from decimal import Decimal

from piccolo.columns import (
    BigSerial,
    ForeignKey,
    Integer,
    Numeric,
    OnDelete,
    Text,
    Timestamptz,
)
from piccolo.table import Table

from db.user import User
from db.word import Word
from db.word_meaning import WordMeaning
from enums import UserWordStatus


class UserWord(Table, tablename='user_words'):
    id = BigSerial(primary_key=True)
    user = ForeignKey(
        references=User,
        null=False,
        on_delete=OnDelete.cascade,
        db_column_name='user_id',
    )
    word = ForeignKey(
        references=Word,
        null=False,
        on_delete=OnDelete.cascade,
        db_column_name='word_id',
        index=True,
    )
    meaning = ForeignKey(
        references=WordMeaning,
        null=False,
        on_delete=OnDelete.cascade,
        db_column_name='meaning_id',
        index=True,
    )
    original_input = Text(required=True)
    context = Text(null=True, default=None)
    status = Text(default=UserWordStatus.NEW.value, choices=UserWordStatus)
    ease_factor = Numeric(digits=(4, 2), default=Decimal('2.50'))
    interval_days = Integer(default=0)
    repetitions = Integer(default=0)
    lapses = Integer(default=0)
    next_review_at = Timestamptz(null=True, default=None)
    last_reviewed_at = Timestamptz(null=True, default=None)
    created_at = Timestamptz()
