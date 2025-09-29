import logging
import asyncio
import asyncpg

from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
from collections import defaultdict
from contextlib import asynccontextmanager

from config import LOG_CONFIG, config

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="database")


# = КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =
class DatabaseService:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool | None] = None
        self.user_locks = defaultdict(asyncio.Lock)
        self.stats_lock = asyncio.Lock()
        self.initialized: bool = False

    async def connect(self):
        """Инициализация пула соединений и создание таблиц"""
        try:
            # Создаем пул соединений
            self._pool = await asyncpg.create_pool(
                config.DATABASE_URL, min_size=5, max_size=20, timeout=60
            )

            # Создаем таблицы
            await self.__create_words()
            await self.__create_users()
            await self.__create_users_profile()
            await self.__create_locations()
            await self.__create_weekly_reports()
            await self.__create_report_words()

            self.initialized = True
            logger.debug("Database pool initialized successfully")
            return self

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def __create_words(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                word TEXT NOT NULL,
                part_of_speech TEXT NOT NULL,
                translation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (user_id, word)
                ); 
            """
            )

    async def __create_users(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                            CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            username TEXT NOT NULL,
                            first_name TEXT NOT NULL,
                            camefrom TEXT NOT NULL,
                            language TEXT NOT NULL,
                            fluency SMALLINT NOT NULL,
                            topic TEXT NOT NULL,
                            lang_code TEXT NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            blocked_bot BOOLEAN DEFAULT FALSE,
                            UNIQUE (user_id)
                            ); """
            )

    async def __create_users_profile(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                            CREATE TABLE IF NOT EXISTS users_profile (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            status VARCHAR(50) NOT NULL,
                            prefered_name VARCHAR(50) NOT NULL,
                            birthday DATE NOT NULL,
                            dating BOOLEAN DEFAULT FALSE,
                            is_active BOOLEAN DEFAULT TRUE,
                            about TEXT NULL,
                            UNIQUE (user_id)
                            ); """
            )

    async def __create_locations(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                            CREATE TABLE IF NOT EXISTS locations (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            latitude TEXT NOT NULL,
                            longitude TEXT NOT NULL,
                            UNIQUE (user_id)
                            ); """
            )

    async def __create_weekly_reports(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                            CREATE TABLE IF NOT EXISTS weekly_reports (
                            report_id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            status TEXT DEFAULT 'OK',
                            generation_date TIMESTAMP DEFAULT NOW(),
                            sent BOOLEAN DEFAULT FALSE
                            ); """
            )

    async def __create_report_words(self):
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                            CREATE TABLE IF NOT EXISTS report_words (
                            word_id SERIAL PRIMARY KEY,
                            report_id INT REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
                            word TEXT NOT NULL,
                            sentence TEXT NOT NULL,
                            options TEXT[] NOT NULL,
                            correct_index INT NOT NULL
                            ); """
            )

    # Контекстный менеджер для работы с соединениями
    @asynccontextmanager
    async def acquire_connection(self):
        """Асинхронный контекстный менеджер для работы с соединениями"""
        conn = await self._pool.acquire()
        try:
            yield conn
        finally:
            await self._pool.release(conn)

    async def create_user(
        self,
        user_id: int,
        username: str,
        first_name: str,
        camefrom: str,
        language: str,
        fluency: int,
        topic: str,
        lang_code: str
    ):

        try:
            async with self.acquire_connection() as conn:
                result = await conn.execute(
                    """
                    INSERT INTO users (user_id, username, first_name, camefrom, language, fluency, topic, lang_code) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET username = EXCLUDED.username,
                        camefrom = EXCLUDED.camefrom,
                        first_name = EXCLUDED.first_name,
                        language = EXCLUDED.language,
                        fluency = EXCLUDED.fluency,
                        topic = EXCLUDED.topic,
                        lang_code = EXCLUDED.lang_code
                """,
                    user_id,
                    username,
                    first_name,
                    camefrom,
                    language,
                    fluency,
                    topic,
                    lang_code,
                )
                logger.info(f"User {user_id} created/updated: {result}")
                return True
        except Exception as e:
            logger.error(f"Error creating/updating user {user_id}: {e}")
            return False

    async def add_users_profile(
        self,
        user_id: int,
        prefered_name: str,
        birthday: datetime,
        about: str,
        dating: bool = False,
        status: str = "rookie",
    ) -> None:
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
            INSERT INTO users_profile (user_id, status, prefered_name, birthday, dating, about)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE
            SET status = EXCLUDED.status,
                prefered_name = EXCLUDED.prefered_name,
                birthday = EXCLUDED.birthday,
                dating = EXCLUDED.dating,
                about = EXCLUDED.about
            """,
                user_id,
                status,
                prefered_name,
                birthday,
                dating,
                about,
            )
            logger.info(
                f"User {user_id} profile added. Their name: {prefered_name}, birthday: {birthday}, dating paramm: {dating}, status: {status},\n intro: {about}"
            )
            return

    async def get_users_profile(self, user_id: int) -> dict:
        async with self.acquire_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users_profile WHERE user_id = $1", user_id
            )
            return dict(row) if row else None

    async def add_users_location(
        self, user_id: int, latitude: str, longitude: str
    ) -> None:
        async with self.acquire_connection() as conn:
            await conn.execute(
                """
                INSERT INTO locations (user_id, latitude, longitude)
                VALUES ($1,$2,$3)
                ON CONFLICT (user_id) DO UPDATE
                SET latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude
                """,
                user_id,
                latitude,
                longitude,
            )
            logger.info(f"User {user_id} location added: {latitude}, {longitude}")
            return

    async def get_criteria(self, user_id: int) -> dict:
        async with self.acquire_connection() as conn:
            row = await conn.fetchrow(
                "SELECT language, fluency, dating FROM users WHERE user_id = $1", user_id
            )
            return dict(row) if row else None

    async def change_topic(self, user_id: int, new_topic: str) -> None:
        async with self.acquire_connection() as conn:
            await conn.execute(
                """UPDATE users SET topic = $1 WHERE user_id = $2""",
                new_topic, user_id
            )

    async def get_users_location(self, user_id: int) -> dict:
        async with self.acquire_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM locations WHERE user_id = $1", user_id
            )
            logger.debug(f"User {user_id} location: {dict(row) if row else None}")
            return dict(row) if row else None

    async def get_user_info(self, user_id: int) -> dict:
        async with self.acquire_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            logger.debug(f"User {user_id} info: {dict(row) if row else None}")
            return dict(row) if row else None

    async def get_words(self, user_id: int) -> List[Tuple[str, str, str, str]]:
        async with self.acquire_connection() as conn:
            rows = await conn.fetch(
                "SELECT id, word, part_of_speech, translation FROM words WHERE user_id = $1 ORDER BY word",
                user_id,
            )
            return [
                (row["id"], row["word"], row["part_of_speech"], row["translation"])
                for row in rows
            ]

    async def add_word(self, user_id: int, word: str, pos: str, value: str) -> bool:
        if value is None:
            value = ""
        async with self.acquire_connection() as conn:
            try:
                await conn.execute(
                    "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                    user_id,
                    word,
                    pos,
                    value,
                )
                return True
            except Exception as e:
                logger.error(f"Database error: {e}")
                return False

    async def search_word(
        self, user_id: int, word: str
    ) -> List[Tuple[str, str, str, str]]:
        async with self.acquire_connection() as conn:
            row = await conn.fetchrow(
                "SELECT id, word, part_of_speech, translation FROM words WHERE user_id = $1 AND word = $2",
                user_id,
                word,
            )
            return [(row["id"], row["word"], row["part_of_speech"], row["translation"])]

    async def delete_word(self, user_id: int, word_id: int) -> bool:
        async with self.acquire_connection() as conn:
            result = await conn.execute(
                "DELETE FROM words WHERE user_id = $1 AND id = $2", user_id, word_id
            )
            return "DELETE" in result

    async def update_word(
        self, user_id: int, old_word: str, new_word: str, pos: str, value: str
    ) -> bool:
        async with self.user_locks[user_id]:
            async with self.acquire_connection() as conn:
                async with conn.transaction():
                    if old_word != new_word:
                        await conn.execute(
                            "DELETE FROM words WHERE user_id = $1 AND word = $2",
                            user_id,
                            old_word,
                        )
                        await conn.execute(
                            "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                            user_id,
                            new_word,
                            pos,
                            value,
                        )
                        return True
                    else:
                        result = await conn.execute(
                            """UPDATE words 
                            SET part_of_speech = $1, translation = $2 
                            WHERE user_id = $3 AND word = $4""",
                            pos,
                            value,
                            user_id,
                            new_word,
                        )
                        return "UPDATE" in result

    # Temperorary solution
    async def get_user_stats(self, user_id: int, pos: str = None):
        async with self.stats_lock:
            async with self.acquire_connection() as conn:
                try:
                    all_words_count_row = await conn.fetchrow(
                        """
                        SELECT
                          COUNT(*) FILTER (WHERE part_of_speech = 'noun')      AS nouns,
                          COUNT(*) FILTER (WHERE part_of_speech = 'verb')      AS verbs,
                          COUNT(*) FILTER (WHERE part_of_speech = 'adjective') AS adjectives,
                          COUNT(*) FILTER (WHERE part_of_speech = 'adverb')    AS adverbs,
                          COUNT(*) FILTER (WHERE part_of_speech = 'other')       AS other
                        FROM words
                        WHERE user_id = $1
                        """,
                        user_id,
                    )
                    if all_words_count_row and pos is None:
                        total_words = (
                            all_words_count_row["noun"]
                            + all_words_count_row["verb"]
                            + all_words_count_row["adjective"]
                            + all_words_count_row["adverb"]
                            + all_words_count_row["other"]
                        )

                        return total_words

                    elif all_words_count_row and pos is not None:
                        return all_words_count_row[pos]

                    else:
                        return 0

                except Exception as e:
                    logger.error(f"Database error: {e}")
                    return None

    async def get_user_stats_last_week(self, user_id: int):
        async with self.stats_lock:
            async with self.acquire_connection() as conn:
                try:
                    all_words_last_week_count_row = await conn.fetchrow(
                        """SELECT COUNT(*) FROM words WHERE user_id = $1 AND created_at >= $2""",
                        user_id,
                        datetime.now() - timedelta(days=7),
                    )
                    if all_words_last_week_count_row:
                        return all_words_last_week_count_row["count"]

                    else:
                        return 0

                except Exception as e:
                    logger.error(f"Database error: {e}")
                    return None

    async def check_user_exists(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow("SELECT 1 FROM users WHERE user_id = $1", user_id)
            )

    async def check_profile_exists(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow(
                    "SELECT 1 FROM users_profile WHERE user_id = $1", user_id
                )
            )

    async def check_location_exists(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return bool(
                await conn.fetchrow(
                    "SELECT 1 FROM locations WHERE user_id = $1", user_id
                )
            )

    async def check_nickname_exists(self, nickname: str):
        async with self.acquire_connection() as conn:
            return conn.fetchrow(
                "SELECT 1 FROM users_profile WHERE prefered_name = $1", nickname
            )

    async def get_weekly_words_by_user(self) -> List[Dict]:
        week_ago = datetime.now() - timedelta(days=7)
        async with self.acquire_connection() as conn:
            return await conn.fetch(
                "SELECT user_id, ARRAY_AGG(DISTINCT word) as words "
                "FROM words "
                "WHERE created_at <= $1 AND word IS NOT NULL "
                "GROUP BY user_id "
                "HAVING COUNT(word) > 1",
                week_ago,
            )

    async def create_report(self, user_id: int) -> int:
        async with self.acquire_connection() as conn:
            return await conn.fetchval(
                "INSERT INTO weekly_reports (user_id) VALUES ($1) RETURNING report_id",
                user_id,
            )

    async def add_words_to_report(self, report_id: int, words: List[Dict]):
        async with self.acquire_connection() as conn:
            for item in words:
                await conn.execute(
                    "INSERT INTO report_words (report_id, word, sentence, options, correct_index) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    report_id,
                    item["word"],
                    item["sentence"],
                    item["options"],
                    item["correct_index"],
                )

    async def get_report(self, report_id):
        async with self.acquire_connection() as conn:
            return await conn.fetchrow(
                "SELECT * FROM weekly_reports WHERE report_id = $1", report_id
            )

    async def get_word_data(self, word_id):
        async with self.acquire_connection() as conn:
            return await conn.fetchrow(
                "SELECT * FROM report_words WHERE word_id = $1", word_id
            )

    async def get_weekly_words(self, report_id):
        async with self.acquire_connection() as conn:
            result = await conn.fetch(
                "SELECT * FROM report_words WHERE report_id = $1", report_id
            )
            return [dict(row) for row in result]

    async def get_words_ids(self, report_id):
        async with self.acquire_connection() as conn:
            return await conn.fetch(
                "SELECT word_id FROM report_words WHERE report_id = $1", report_id
            )

    async def get_pending_reports(self) -> List[Dict]:
        async with self.acquire_connection() as conn:
            return await conn.fetch(
                "SELECT report_id, user_id FROM weekly_reports WHERE sent = FALSE AND status = 'OK'"
            )

    async def mark_user_as_blocked(self, user_id: int):
        async with self.acquire_connection() as conn:
            await conn.execute(
                "UPDATE users SET is_active = FALSE, blocked_bot = TRUE WHERE user_id = $1",
                user_id,
            )
            logger.info(f"Пользователь {user_id} помечен как заблокированный в БД.")

    # Обновить mark_report_as_sent для приема статуса
    async def mark_report_as_sent(self, report_id: int, status: str = "OK"):
        async with self.acquire_connection() as conn:
            await conn.execute(
                "UPDATE weekly_reports SET generation_date = NOW(), sent = TRUE, status = $1 WHERE report_id = $2",
                status,
                report_id,
            )
            logger.info(f"Отчет {report_id} помечен как {status} в БД.")

    async def is_user_blocked(self, user_id: int) -> bool:
        async with self.acquire_connection() as conn:
            return await conn.fetchval(
                "SELECT blocked_bot FROM users WHERE user_id = $1", user_id
            )

    async def cleanup_old_reports(self, days: int) -> Tuple[int, int]:
        cutoff_date = datetime.now() - timedelta(days=days)
        async with self.acquire_connection() as conn:
            words_rows = await conn.fetch(
                "DELETE FROM report_words "
                "WHERE report_id IN ("
                "   SELECT report_id FROM weekly_reports "
                "   WHERE generation_date < $1"
                ") RETURNING word_id",
                cutoff_date,
            )
            reports_rows = await conn.fetch(
                "DELETE FROM weekly_reports WHERE generation_date < $1 RETURNING report_id",
                cutoff_date,
            )
            return len(reports_rows), len(words_rows)

    def clean_locks(self):
        """Периодически очищаем неиспользуемые блокировки"""
        user_ids = list(self.user_locks.keys())
        for user_id in user_ids:
            if user_id in self.user_locks and not self.user_locks[user_id].locked():
                del self.user_locks[user_id]

    async def disconnect(self):
        if self.initialized:
            await self._pool.close()


database_service = DatabaseService()
