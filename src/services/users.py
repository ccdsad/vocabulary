from telegram import Chat
from telegram import User as TelegramUser

from db.user import User


async def get_all_users() -> list[User]:
    return await User.objects().run()


async def upsert_telegram_user(
    *,
    telegram_user: TelegramUser,
    chat: Chat,
) -> User:
    user = await User.objects().where(User.tg_user_id == telegram_user.id).first()
    if user is None:
        user = User(
            tg_user_id=telegram_user.id,
            chat_id=chat.id,
            first_name=telegram_user.first_name,
            is_bot=telegram_user.is_bot,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            language_code=telegram_user.language_code,
        )
        await user.save().run()
        return user

    user.chat_id = chat.id
    user.first_name = telegram_user.first_name
    user.is_bot = telegram_user.is_bot
    user.last_name = telegram_user.last_name
    user.username = telegram_user.username
    user.language_code = telegram_user.language_code
    await user.save(
        columns=[
            User.chat_id,
            User.first_name,
            User.is_bot,
            User.last_name,
            User.username,
            User.language_code,
        ]
    ).run()
    return user
