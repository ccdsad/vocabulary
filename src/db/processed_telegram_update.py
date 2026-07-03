from piccolo.columns import BigInt, Timestamptz
from piccolo.table import Table


class ProcessedTelegramUpdate(Table, tablename='processed_telegram_updates'):
    update_id = BigInt(primary_key=True)
    processed_at = Timestamptz()
