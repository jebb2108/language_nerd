import os
from typing import *

import logging
import asyncpg
from asyncpg.pool import Pool

# Глобальный пул соединений
db_pool: Optional[Pool] = None

# Загружаем переменные окружения из файла .env (токены ботов и другие настройки)
# Получение и проверка переменных окружения
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "telegram_bot")

# Обработка порта с проверкой
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


# = ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =
# Каждый пользователь имеет свою базу данных SQLite в папке dbs

async def init_db():
    """Инициализация базы данных"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            min_size=5,
            max_size=20
        )
        async with db_pool.acquire() as conn:
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

            # Убедитесь, что таблица locks создается правильно
            await conn.execute("""
                            CREATE TABLE IF NOT EXISTS locks (
                                lock_name VARCHAR(50) PRIMARY KEY,
                                owner_id VARCHAR(50) NOT NULL,
                                expires_at TIMESTAMPTZ NOT NULL
                            );
                        """)

            # Создаем индекс
            await conn.execute("CREATE INDEX IF NOT EXISTS locks_expires_idx ON locks (expires_at);")

        logging.info("Database initialized successfully")
    except Exception as e:
        logging.critical(f"Database initialization failed: {e}")
        raise


async def close_db():
    """Закрытие пула соединений"""
    global db_pool
    if db_pool:
        await db_pool.close()

async def create_users_table(user_id, username, first_name, camefrom, language, lang_code):
    """Создает или обновляет запись пользователя с проверкой блокировки"""
    try:
        async with db_pool.acquire() as conn:
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
            logging.info(f"User {user_id} created/updated: {result}")
            return True
    except Exception as e:
        logging.error(f"Error creating/updating user {user_id}: {e}")
        return False


async def get_user_info(user_id):
    """Получает информацию о пользователе из базы данных"""

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username, first_name, language, lang_code FROM users WHERE user_id = $1",
            user_id
        )
        if row:
            return row["username"], row["first_name"], row["language"], row["lang_code"]
        return None, None, None, None


# Обновленные функции работы с БД
async def get_words_from_db(user_id: int) -> List[Tuple[str, str, str]]:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT word, part_of_speech, translation FROM words WHERE user_id = $1 ORDER BY word",
            user_id
        )
        return [(row['word'], row['part_of_speech'], row['translation']) for row in rows]

async def delete_word_from_db(user_id: int, word: str) -> bool:
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM words WHERE user_id = $1 AND word = $2",
            user_id, word
        )
        return "DELETE" in result

async def update_word_in_db(user_id: int, old_word: str, new_word: str, pos: str, value: str) -> bool:
    async with db_pool.acquire() as conn:
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

async def add_word_to_db(user_id: int, word: str, pos: str, value: str) -> bool:
    if value is None:
        value = ""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO words (user_id, word, part_of_speech, translation) VALUES ($1, $2, $3, $4)",
                user_id, word, pos, value
            )
            return True
        except Exception as e:
            logging.error(f"Database error: {e}")
            return False

async def check_word_exists(user_id: int, word: str) -> bool:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM words WHERE user_id = $1 AND word = $2 LIMIT 1",
            user_id, word
        )
        return row is not None