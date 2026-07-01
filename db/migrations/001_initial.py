from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.engine.finder import engine_finder


ID = "001"
VERSION = "1.34.0"
DESCRIPTION = "Initial schema"


async def run_statements(statements: list[str]) -> None:
    engine = engine_finder()
    for statement in statements:
        await engine.run_ddl(statement)


async def forwards():
    manager = MigrationManager(
        migration_id=ID,
        app_name="db",
        description=DESCRIPTION,
    )

    async def run():
        await run_statements(
            [
                """
            CREATE TABLE users
            (
                id            BIGSERIAL PRIMARY KEY,
                tg_user_id    BIGINT      NOT NULL UNIQUE,
                chat_id       BIGINT      NOT NULL UNIQUE,
                first_name    TEXT        NOT NULL,
                is_bot        BOOL        NOT NULL,
                last_name     TEXT,
                username      TEXT,
                language_code VARCHAR(10),
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
                """
            CREATE INDEX users_username_lower_idx
                ON users (lower(username))
                WHERE username IS NOT NULL
            """,
                """
            CREATE TABLE words
            (
                id             BIGSERIAL PRIMARY KEY,
                lemma          TEXT        NOT NULL,
                part_of_speech TEXT        NOT NULL,
                transcription  TEXT,
                cefr_level     VARCHAR(2),
                created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                UNIQUE (lemma, part_of_speech),
                CONSTRAINT words_cefr_level_check
                    CHECK (
                        cefr_level IS NULL
                        OR cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')
                    )
            )
            """,
                """
            CREATE TABLE word_meanings
            (
                id                    BIGSERIAL PRIMARY KEY,
                word_id               BIGINT    NOT NULL
                    REFERENCES words (id) ON DELETE CASCADE,
                definition_en         TEXT      NOT NULL,
                simple_explanation_en TEXT,
                translations_ru       TEXT[]    NOT NULL
                    CHECK (cardinality(translations_ru) > 0),
                synonyms              TEXT[]    NOT NULL DEFAULT '{}',
                antonyms              TEXT[]    NOT NULL DEFAULT '{}',
                collocations          TEXT[]    NOT NULL DEFAULT '{}',
                example_en            TEXT,
                example_ru            TEXT,
                usage_note_ru         TEXT,
                meaning_order         SMALLINT  NOT NULL DEFAULT 1
                    CHECK (meaning_order > 0),

                UNIQUE (word_id, meaning_order),
                UNIQUE (word_id, id)
            )
            """,
                """
            CREATE TABLE user_words
            (
                id               BIGSERIAL PRIMARY KEY,
                user_id          BIGINT        NOT NULL
                    REFERENCES users (id) ON DELETE CASCADE,
                word_id          BIGINT        NOT NULL
                    REFERENCES words (id) ON DELETE CASCADE,
                meaning_id       BIGINT        NOT NULL,
                original_input   TEXT          NOT NULL,
                context          TEXT,
                status           TEXT          NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'learning', 'review', 'suspended')),
                ease_factor      NUMERIC(4, 2) NOT NULL DEFAULT 2.50
                    CHECK (ease_factor > 0),
                interval_days    INTEGER       NOT NULL DEFAULT 0
                    CHECK (interval_days >= 0),
                repetitions      INTEGER       NOT NULL DEFAULT 0
                    CHECK (repetitions >= 0),
                lapses           INTEGER       NOT NULL DEFAULT 0
                    CHECK (lapses >= 0),
                next_review_at   TIMESTAMPTZ,
                last_reviewed_at TIMESTAMPTZ,
                created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

                UNIQUE (user_id, meaning_id),
                FOREIGN KEY (word_id, meaning_id)
                    REFERENCES word_meanings (word_id, id)
                    ON DELETE CASCADE
            )
            """,
                "CREATE INDEX user_words_word_id_idx ON user_words (word_id)",
                """
            CREATE INDEX user_words_meaning_id_idx ON user_words (meaning_id)
            """,
                """
            CREATE INDEX user_words_due_idx
                ON user_words (user_id, next_review_at)
                WHERE status != 'suspended'
                  AND next_review_at IS NOT NULL
            """,
                """
            CREATE TABLE llm_generations
            (
                id              BIGSERIAL PRIMARY KEY,
                word_meaning_id BIGINT      NOT NULL
                    REFERENCES word_meanings (id) ON DELETE CASCADE,
                llm_model       TEXT        NOT NULL,
                prompt_version  INTEGER     NOT NULL CHECK (prompt_version > 0),
                llm_payload     JSONB       NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
                """
            CREATE INDEX llm_generations_word_meaning_id_idx
                ON llm_generations (word_meaning_id)
            """,
            ]
        )

    async def backwards():
        await run_statements(
            [
                "DROP TABLE IF EXISTS llm_generations",
                "DROP TABLE IF EXISTS user_words",
                "DROP TABLE IF EXISTS word_meanings",
                "DROP TABLE IF EXISTS words",
                "DROP TABLE IF EXISTS users",
            ]
        )

    manager.add_raw(run)
    manager.add_raw_backwards(backwards)

    return manager
