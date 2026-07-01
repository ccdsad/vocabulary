from db.llm_generation import LLMGeneration
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
]

__all__ = [
    "LLMGeneration",
    "TABLES",
    "User",
    "UserWord",
    "Word",
    "WordMeaning",
]
