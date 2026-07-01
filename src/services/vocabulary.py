from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import timedelta
from typing import Any

import openai

from db.engine import DB
from db.llm_generation import LLMGeneration
from db.user import User
from db.user_word import UserWord
from db.word import Word
from db.word_meaning import WordMeaning
from enums import UserWordStatus
from schemas.vocabulary import VocabularyGeneration


@dataclass(frozen=True)
class VocabularyEntry:
    user_word_id: int
    lemma: str
    part_of_speech: str
    transcription: str | None
    cefr_level: str | None
    translations_ru: list[str]
    definition_en: str
    simple_explanation_en: str | None
    synonyms: list[str]
    antonyms: list[str]
    collocations: list[str]
    example_en: str | None
    example_ru: str | None
    usage_note_ru: str | None


SYSTEM_PROMPT = """
Return only valid JSON for an English vocabulary item for a Russian-speaking learner.
Use the most common meaning unless context clearly says otherwise. Normalize the lemma
to dictionary form. Keep English simple. Example must be 6-20 words.

Schema:
{
  "input": "original user input",
  "lemma": "dictionary form",
  "part_of_speech": "noun|verb|adjective|adverb|phrasal verb|idiom|phrase|other",
  "transcription": "IPA or null",
  "cefr_level": "A1|A2|B1|B2|C1|C2|null",
  "translations_ru": ["1-3 common Russian translations"],
  "definition_en": "short English definition",
  "simple_explanation_en": "very simple English explanation or null",
  "synonyms": ["useful close synonyms"],
  "antonyms": ["useful antonyms"],
  "common_collocations": ["2-4 common collocations"],
  "example_en": "natural English example, 6-20 words",
  "example_ru": "natural Russian translation",
  "usage_note_ru": "short Russian usage note or null"
}
Use null for unknown optional fields and [] for empty lists.
"""


async def add_vocabulary_from_text(
    *,
    user: User,
    text: str,
    client: openai.AsyncOpenAI,
    llm_model: str,
    prompt_version: int,
) -> UserWord:
    resp = await client.responses.create(
        model=llm_model,
        instructions=SYSTEM_PROMPT,
        input=text,
        max_output_tokens=700,
    )
    vocabulary = VocabularyGeneration.model_validate_json(resp.output_text)
    return await save_vocabulary_generation(
        user=user,
        vocabulary=vocabulary,
        llm_model=llm_model,
        prompt_version=prompt_version,
        llm_payload=vocabulary.model_dump(mode="json"),
    )


async def find_or_attach_existing_vocabulary_entry(
    *,
    user: User,
    text: str,
) -> VocabularyEntry | None:
    normalized_text = text.strip()
    if not normalized_text:
        return None

    user_word = (
        await UserWord.objects()
        .where(
            (UserWord.user == user.id)
            & (UserWord.original_input.ilike(normalized_text))
        )
        .first()
    )
    if user_word is not None:
        return await get_vocabulary_entry(user_word=user_word)

    word = await Word.objects().where(Word.lemma.ilike(normalized_text)).first()
    if word is None:
        return None

    meaning = (
        await WordMeaning.objects()
        .where((WordMeaning.word == word.id) & (WordMeaning.meaning_order == 1))
        .first()
    )
    if meaning is None:
        return None

    user_word = (
        await UserWord.objects()
        .where((UserWord.user == user.id) & (UserWord.meaning == meaning.id))
        .first()
    )
    if user_word is None:
        now = datetime.now(UTC)
        user_word = UserWord(
            user=user.id,
            word=word.id,
            meaning=meaning.id,
            original_input=normalized_text,
            status=UserWordStatus.LEARNING.value,
            next_review_at=now + timedelta(minutes=10),
        )
        await user_word.save().run()

    return await get_vocabulary_entry(user_word=user_word)


async def get_vocabulary_entry(*, user_word: UserWord) -> VocabularyEntry | None:
    word = await Word.objects().where(Word.id == _db_id(user_word.word)).first()
    meaning = (
        await WordMeaning.objects()
        .where(WordMeaning.id == _db_id(user_word.meaning))
        .first()
    )
    if word is None or meaning is None:
        return None

    return VocabularyEntry(
        user_word_id=int(user_word.id),
        lemma=word.lemma,
        part_of_speech=word.part_of_speech,
        transcription=word.transcription,
        cefr_level=word.cefr_level,
        translations_ru=list(meaning.translations_ru),
        definition_en=meaning.definition_en,
        simple_explanation_en=meaning.simple_explanation_en,
        synonyms=list(meaning.synonyms),
        antonyms=list(meaning.antonyms),
        collocations=list(meaning.collocations),
        example_en=meaning.example_en,
        example_ru=meaning.example_ru,
        usage_note_ru=meaning.usage_note_ru,
    )


async def save_vocabulary_generation(
    *,
    user: User,
    vocabulary: VocabularyGeneration,
    llm_model: str,
    prompt_version: int,
    llm_payload: dict[str, Any],
) -> UserWord:
    async with DB.transaction():
        word = await _upsert_word(vocabulary=vocabulary)
        meaning = await _upsert_word_meaning(
            word=word,
            vocabulary=vocabulary,
        )
        user_word = await _upsert_user_word(
            user=user,
            word=word,
            meaning=meaning,
            vocabulary=vocabulary,
        )
        await LLMGeneration(
            word_meaning=meaning.id,
            llm_model=llm_model,
            prompt_version=prompt_version,
            llm_payload=llm_payload,
        ).save().run()

    return user_word


async def _upsert_word(*, vocabulary: VocabularyGeneration) -> Word:
    word = (
        await Word.objects()
        .where(
            (Word.lemma == vocabulary.lemma)
            & (Word.part_of_speech == vocabulary.part_of_speech.value)
        )
        .first()
    )
    if word is None:
        word = Word(
            lemma=vocabulary.lemma,
            part_of_speech=vocabulary.part_of_speech.value,
            transcription=vocabulary.transcription,
            cefr_level=vocabulary.cefr_level.value
            if vocabulary.cefr_level is not None
            else None,
        )
        await word.save().run()
        return word

    word.transcription = vocabulary.transcription
    word.cefr_level = (
        vocabulary.cefr_level.value if vocabulary.cefr_level is not None else None
    )
    await word.save(columns=[Word.transcription, Word.cefr_level]).run()
    return word


async def _upsert_word_meaning(
    *,
    word: Word,
    vocabulary: VocabularyGeneration,
) -> WordMeaning:
    meaning_order = 1
    meaning = (
        await WordMeaning.objects()
        .where(
            (WordMeaning.word == word.id)
            & (WordMeaning.meaning_order == meaning_order)
        )
        .first()
    )
    if meaning is None:
        meaning = WordMeaning(
            word=word.id,
            definition_en=vocabulary.definition_en,
            simple_explanation_en=vocabulary.simple_explanation_en,
            translations_ru=vocabulary.translations_ru,
            synonyms=vocabulary.synonyms,
            antonyms=vocabulary.antonyms,
            collocations=vocabulary.common_collocations,
            example_en=vocabulary.example_en,
            example_ru=vocabulary.example_ru,
            usage_note_ru=vocabulary.usage_note_ru,
            meaning_order=meaning_order,
        )
        await meaning.save().run()
        return meaning

    meaning.definition_en = vocabulary.definition_en
    meaning.simple_explanation_en = vocabulary.simple_explanation_en
    meaning.translations_ru = vocabulary.translations_ru
    meaning.synonyms = vocabulary.synonyms
    meaning.antonyms = vocabulary.antonyms
    meaning.collocations = vocabulary.common_collocations
    meaning.example_en = vocabulary.example_en
    meaning.example_ru = vocabulary.example_ru
    meaning.usage_note_ru = vocabulary.usage_note_ru
    await meaning.save(
        columns=[
            WordMeaning.definition_en,
            WordMeaning.simple_explanation_en,
            WordMeaning.translations_ru,
            WordMeaning.synonyms,
            WordMeaning.antonyms,
            WordMeaning.collocations,
            WordMeaning.example_en,
            WordMeaning.example_ru,
            WordMeaning.usage_note_ru,
        ]
    ).run()
    return meaning


async def _upsert_user_word(
    *,
    user: User,
    word: Word,
    meaning: WordMeaning,
    vocabulary: VocabularyGeneration,
) -> UserWord:
    user_word = (
        await UserWord.objects()
        .where((UserWord.user == user.id) & (UserWord.meaning == meaning.id))
        .first()
    )
    if user_word is None:
        now = datetime.now(UTC)
        user_word = UserWord(
            user=user.id,
            word=word.id,
            meaning=meaning.id,
            original_input=vocabulary.input,
            status=UserWordStatus.LEARNING.value,
            next_review_at=now + timedelta(minutes=10),
        )
        await user_word.save().run()
        return user_word

    user_word.word = word.id
    user_word.original_input = vocabulary.input
    await user_word.save(columns=[UserWord.word, UserWord.original_input]).run()
    return user_word


def _db_id(value: Any) -> int:
    return int(value.id if hasattr(value, "id") else value)
