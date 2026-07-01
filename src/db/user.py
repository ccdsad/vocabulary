from piccolo.columns import BigInt, BigSerial, Boolean, Text, Timestamptz, Varchar
from piccolo.table import Table


class User(Table, tablename="users"):
    id = BigSerial(primary_key=True)
    tg_user_id = BigInt(unique=True, required=True)
    chat_id = BigInt(unique=True, required=True)
    first_name = Text(required=True)
    is_bot = Boolean(required=True)
    last_name = Text(null=True, default=None)
    username = Text(null=True, default=None)
    language_code = Varchar(length=10, null=True, default=None)
    created_at = Timestamptz()
