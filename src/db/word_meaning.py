from piccolo.columns import Array, BigSerial, ForeignKey, OnDelete, SmallInt, Text
from piccolo.table import Table

from db.word import Word


class WordMeaning(Table, tablename="word_meanings"):
    id = BigSerial(primary_key=True)
    word = ForeignKey(
        references=Word,
        null=False,
        on_delete=OnDelete.cascade,
        db_column_name="word_id",
    )
    definition_en = Text(required=True)
    simple_explanation_en = Text(null=True, default=None)
    translations_ru = Array(base_column=Text(), required=True)
    synonyms = Array(base_column=Text(), default=list)
    antonyms = Array(base_column=Text(), default=list)
    collocations = Array(base_column=Text(), default=list)
    example_en = Text(null=True, default=None)
    example_ru = Text(null=True, default=None)
    usage_note_ru = Text(null=True, default=None)
    meaning_order = SmallInt(default=1)
