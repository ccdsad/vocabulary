from db.llm_generation import LLMGeneration
from db.processed_telegram_update import ProcessedTelegramUpdate
from db.user import User
from db.user_word import UserWord
from db.word import Word
from db.word_meaning import WordMeaning

TABLES = [
    User,
    Word,
    WordMeaning,
    UserWord,
    LLMGeneration,
    ProcessedTelegramUpdate,
]

__all__ = [
    'TABLES',
    'LLMGeneration',
    'ProcessedTelegramUpdate',
    'User',
    'UserWord',
    'Word',
    'WordMeaning',
]
