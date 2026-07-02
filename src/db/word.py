from piccolo.columns import BigSerial, Text, Timestamptz, Varchar
from piccolo.table import Table

from enums import CefrLevel


class Word(Table, tablename='words'):
    id = BigSerial(primary_key=True)
    lemma = Text(required=True)
    part_of_speech = Text(required=True)
    transcription = Text(null=True, default=None)
    cefr_level = Varchar(
        length=2,
        null=True,
        default=None,
        choices=CefrLevel,
    )
    created_at = Timestamptz()
