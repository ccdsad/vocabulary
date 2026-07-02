from piccolo.columns import JSONB, BigSerial, ForeignKey, Integer, OnDelete, Text, Timestamptz
from piccolo.table import Table

from db.word_meaning import WordMeaning


class LLMGeneration(Table, tablename='llm_generations'):
    id = BigSerial(primary_key=True)
    word_meaning = ForeignKey(
        references=WordMeaning,
        null=False,
        on_delete=OnDelete.cascade,
        db_column_name='word_meaning_id',
        index=True,
    )
    llm_model = Text(required=True)
    prompt_version = Integer(required=True)
    llm_payload = JSONB(required=True)
    created_at = Timestamptz()
