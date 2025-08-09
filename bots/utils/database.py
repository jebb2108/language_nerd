from datetime import datetime, timedelta
import sys
import asyncio
import random
from random import random
from typing import  Dict, Tuple, List
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import logger  # noqa


# = КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =
class Database:

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        # Блокировки на уровне пользователя
        self.user_locks = defaultdict(asyncio.Lock)
        # Блокировка для операций со статистикой
        self.stats_lock = asyncio.Lock()
        self._initialize()

    async def _initialize(self):
        try:
            await self.__create_words()
            await self.__create_users()
            await self.__create_weekly_reports()
            await self.__create_report_words()

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    async def __create_words(self):
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

    async def __create_users(self):
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

    async def __create_weekly_reports(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                            CREATE TABLE IF NOT EXISTS weekly_reports (
                            report_id SERIAL PRIMARY KEY,
                            user_id INT NOT NULL,
                            generation_date TIMESTAMP DEFAULT NOW(),
                            sent BOOLEAN DEFAULT FALSE
                            ); """)

    async def __create_report_words(self):
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
    async def get_words(self, user_id: int) -> List[Tuple[str, str, str, str]]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, word, part_of_speech, translation FROM words WHERE user_id = $1 ORDER BY word",
                user_id
            )
            return [(row['id'], row['word'], row['part_of_speech'], row['translation']) for row in rows]

    async def search_word(self, user_id: int, word: str) -> List[Tuple[str, str, str, str]]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, word, part_of_speech, translation FROM words WHERE user_id = $1 AND word = $2",
                user_id, word
            )
            return [(row['id'], row['word'], row['part_of_speech'], row['translation'])]

    async def delete_word(self, user_id: int, word_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM words WHERE user_id = $1 AND id = $2",
                user_id, word_id
            )
            return "DELETE" in result

    async def update_word(
            self,
            user_id: int,
            old_word: str,
            new_word: str,
            pos: str
            , value: str
    ) -> bool:

        async with self.user_locks[user_id]:  # Блокировка на уровне пользователя
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():  # Явная транзакция
                    if old_word != new_word:
                        await conn.execute(
                            "DELETE FROM words WHERE user_id = $1 AND word = $2",
                            user_id, old_word
                        )
                        await conn.execute(
                            "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                            user_id, new_word, pos, value
                        )

                        if random.random() < 0.05:
                            self.clean_locks()

                        return True
                    else:
                        result = await conn.execute(
                            """UPDATE words 
                            SET part_of_speech = $1, translation = $2 
                            WHERE user_id = $3 AND word = $4""",
                            pos, value, user_id, new_word
                        )
                        return "UPDATE" in result

    async def add_word(self, user_id: int, word: str, pos: str, value: str) -> bool:
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
        async with self.stats_lock:
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

    async def acquire(self):
        return await self.db_pool.acquire()

    def clean_locks(self):
        """Периодически очищаем неиспользуемые блокировки"""
        # Создаем копию ключей для безопасной итерации
        user_ids = list(self.user_locks.keys())

        for user_id in user_ids:
            # Проверяем, не заблокирован ли объект
            if not self.user_locks[user_id].locked():
                # Дополнительная проверка на случай параллельного доступа
                if user_id in self.user_locks and not self.user_locks[user_id].locked():
                    del self.user_locks[user_id]


# ========== КЛАСС ДЛЯ РАБОТЫ С ОТЧЕТАМИ ==========
class ReportDatabase(Database):
    def __init__(self, db_pool):
        super().__init__(db_pool)

    async def get_weekly_words_by_user(self) -> List[Dict]:
        """Получает слова за неделю, сгруппированные по пользователям"""
        week_ago = datetime.now() - timedelta(days=7)
        async with self.db_pool.acquire() as conn:
            return await conn.fetch(
                "SELECT user_id, ARRAY_AGG(DISTINCT word) as words "
                "FROM words "
                "WHERE created_at <= $1 AND word IS NOT NULL "
                "GROUP BY user_id "
                "HAVING COUNT(word) > 1",
                week_ago
            )

    async def create_report(self, user_id: int) -> int:
        """Создает новый отчет и возвращает его ID"""
        async with self.db_pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO weekly_reports (user_id) VALUES ($1) RETURNING report_id",
                user_id
            )

    async def add_words_to_report(self, report_id: int, words: List[Dict]):
        """Добавляет слова в отчет"""
        async with self.db_pool.acquire() as conn:
            for item in words:
                await conn.execute(
                    "INSERT INTO report_words (report_id, word, sentence, options, correct_index) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    report_id,
                    item["word"],
                    item["sentence"],
                    item["options"],
                    item["correct_index"]
                )

    async def get_pending_reports(self) -> List[Dict]:
        """Получает все неотправленные отчеты"""
        async with self.db_pool.acquire() as conn:
            return await conn.fetch(
                "SELECT report_id, user_id FROM weekly_reports WHERE sent = FALSE"
            )

    async def mark_report_as_sent(self, report_id: int):
        """Помечает отчет как отправленный"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE weekly_reports SET sent = TRUE WHERE report_id = $1",
                report_id
            )

    async def cleanup_old_reports(self, days: int) -> Tuple[int, int]:
        """Удаляет старые отчеты и возвращает количество удаленных отчетов и слов"""
        cutoff_date = datetime.now() - timedelta(days=days)

        async with self.db_pool.acquire() as conn:
            # Получаем список отчетов для удаления
            old_reports = await conn.fetch(
                "SELECT report_id FROM weekly_reports WHERE generation_date < $1",
                cutoff_date
            )

            if not old_reports:
                return 0, 0

            report_ids = [r["report_id"] for r in old_reports]

            # Удаляем связанные слова отчетов
            words_deleted = await conn.execute(
                "DELETE FROM report_words WHERE report_id = ANY($1::int[])",
                report_ids
            )

            # Удаляем сами отчеты
            reports_deleted = await conn.execute(
                "DELETE FROM weekly_reports WHERE report_id = ANY($1::int[])",
                report_ids
            )

            return reports_deleted.split()[1], words_deleted.split()[1]
