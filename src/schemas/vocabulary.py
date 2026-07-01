from pydantic import BaseModel, ConfigDict, Field, field_validator

from enums import CefrLevel, PartOfSpeech


class VocabularyGeneration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    part_of_speech: PartOfSpeech
    transcription: str | None = None
    cefr_level: CefrLevel | None = None
    translations_ru: list[str] = Field(min_length=1)
    definition_en: str = Field(min_length=1)
    simple_explanation_en: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    common_collocations: list[str] = Field(default_factory=list)
    example_en: str | None = None
    example_ru: str | None = None
    usage_note_ru: str | None = None

    @field_validator(
        "translations_ru",
        "synonyms",
        "antonyms",
        "common_collocations",
    )
    @classmethod
    def reject_blank_list_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("list items must not be blank")
        return value

    @field_validator(
        "input",
        "lemma",
        "definition_en",
        "transcription",
        "simple_explanation_en",
        "example_en",
        "example_ru",
        "usage_note_ru",
    )
    @classmethod
    def reject_blank_strings(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("example_en")
    @classmethod
    def validate_example_word_count(cls, value: str | None) -> str | None:
        if value is None:
            return value

        word_count = len(value.split())
        if not 6 <= word_count <= 20:
            raise ValueError("example_en must contain 6 to 20 words")
        return value
