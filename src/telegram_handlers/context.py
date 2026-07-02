from typing import Any, NoReturn

from telegram.ext import CallbackContext, ContextTypes, ExtBot


class UserContext(CallbackContext[ExtBot[Any], dict[Any, Any], dict[Any, Any], dict[Any, Any]]):
    @property
    def user_data(self) -> dict[Any, Any]:
        user_data = super().user_data
        if user_data is None:
            raise RuntimeError('Telegram context user_data is not available')

        return user_data

    @user_data.setter
    def user_data(self, _: object) -> NoReturn:
        raise AttributeError('You can not assign a new value to user_data')


USER_CONTEXT_TYPES = ContextTypes(context=UserContext)
