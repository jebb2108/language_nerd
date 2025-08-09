import sys
from typing import *
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import logger


# = КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =
class Database:

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        try:
            self._create_words()
            self._create_users()
            self._create_weekly_reports()
            self._create_report_words()

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")


    async def _create_words(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                            CREATE TABLE IF NOT EXISTS words (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            word TEXT NOT NULL,
                            part_of_speech TEXT NOT NULL,
                            translation TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            UNIQUE (user_id, word)
                            ); 
                        """)

    async def _create_users(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                            CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            username TEXT NOT NULL,
                            first_name TEXT NOT NULL,
                            camefrom TEXT NOT NULL,
                            language TEXT NOT NULL,
                            lang_code TEXT NOT NULL,
                            about TEXT NULL,
                            UNIQUE (user_id)
                            ); """)

    async def _create_weekly_reports(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                            CREATE TABLE IF NOT EXISTS weekly_reports (
                            report_id SERIAL PRIMARY KEY,
                            user_id INT NOT NULL,
                            generation_date TIMESTAMP DEFAULT NOW(),
                            sent BOOLEAN DEFAULT FALSE
                            ); """)

    async def _create_report_words(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                            CREATE TABLE IF NOT EXISTS report_words (
                            word_id SERIAL PRIMARY KEY,
                            report_id INT REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
                            word TEXT NOT NULL,
                            sentence TEXT NOT NULL,
                            options TEXT[] NOT NULL,
                            correct_index INT NOT NULL
                            ); """)


    async def create_users_table(self, user_id, username, first_name, camefrom, language, lang_code):
        """Создает или обновляет запись пользователя с проверкой блокировки"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, camefrom, language, lang_code) 
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET username = EXCLUDED.username,
                        camefrom = EXCLUDED.camefrom,
                        first_name = EXCLUDED.first_name,
                        language = EXCLUDED.language,
                        lang_code = EXCLUDED.lang_code
                """, user_id, username, first_name, camefrom, language, lang_code)
                logger.info(f"User {user_id} created/updated: {result}")
                return True
        except Exception as e:
            logger.error(f"Error creating/updating user {user_id}: {e}")
            return False

    async def get_user_info(self, user_id):
        """Получает информацию о пользователе из базы данных"""

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT username, first_name, language, lang_code FROM users WHERE user_id = $1",
                user_id
            )
            if row:
                return row["username"], row["first_name"], row["language"], row["lang_code"]
            return None, None, None, None

    # Обновленные функции работы с БД
    async def get_words_from_db(self, user_id: int) -> List[Tuple[str, str, str, str]]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, word, part_of_speech, translation FROM words WHERE user_id = $1 ORDER BY word",
                user_id
            )
            return [(row['id'], row['word'], row['part_of_speech'], row['translation']) for row in rows]

    async def search_word_in_db(self, user_id: int, word: str) -> List[Tuple[str, str, str, str]]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, word, part_of_speech, translation FROM words WHERE user_id = $1 AND word = $2",
                user_id, word
            )
            return [(row['id'], row['word'], row['part_of_speech'], row['translation'])]

    async def delete_word_from_db(self, user_id: int, word_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM words WHERE user_id = $1 AND id = $2",
                user_id, word_id
            )
            return "DELETE" in result

    async def update_word_in_db(self, user_id: int, old_word: str, new_word: str, pos: str, value: str) -> bool:
        async with self.db_pool.acquire() as conn:
            # Если слово изменилось
            if old_word != new_word:
                await conn.execute(
                    "DELETE FROM words WHERE user_id = $1 AND word = $2",
                    user_id, old_word
                )
                await conn.execute(
                    "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                    user_id, new_word, pos, value
                )
                return True
            else:
                result = await conn.execute(
                    """UPDATE words 
                    SET part_of_speech = $1, translation = $2 
                    WHERE user_id = $3 AND word = $4""",
                    pos, value, user_id, new_word
                )
                return "UPDATE" in result

    async def add_word_to_db(self, user_id: int, word: str, pos: str, value: str) -> bool:
        if value is None:
            value = ""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                    user_id, word, pos, value
                )
                return True
            except Exception as e:
                logger.error(f"Database error: {e}")
                return False

    # Temperorary solution
    async def get_user_stats(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE part_of_speech = 'noun')      AS nouns,
                      COUNT(*) FILTER (WHERE part_of_speech = 'verb')      AS verbs,
                      COUNT(*) FILTER (WHERE part_of_speech = 'adjective') AS adjectives,
                      COUNT(*) FILTER (WHERE part_of_speech = 'adverb')    AS adverbs
                    FROM words
                    WHERE user_id = $1
                    """,
                    user_id
                )
                if row:
                    total_words = row['nouns'] + row['verbs']
                    # row — Record, можно обращаться как row['nouns'], row.nouns и т.д.
                    return total_words, row['nouns'], row['verbs']
                else:
                    return 0, 0, 0
            except Exception as e:
                logger.error(f"Database error: {e}")
                return None

    async def check_word_exists(self, user_id: int, word: str) -> bool:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM words WHERE user_id = $1 AND word = $2 LIMIT 1",
                user_id, word
            )
            return row is not None
