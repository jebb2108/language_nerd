"""
ТЕЛЕГРАМ-БОТЫ: ГЛАВНЫЙ БОТ И БОТ-СЛОВАРЬ

Этот файл содержит двух Telegram-ботов, работающих одновременно:
1. Основной бот (Main Bot) - предоставляет меню и информацию
2. Бот-словарь (Dictionary Bot) - позволяет управлять персональным словарем

Оба бота запускаются параллельно из одного файла
"""

import asyncio  # Для асинхронного выполнения задач
import logging  # Для записи логов работы бота
import sys  # Для работы с системными функциями
from pyexpat.errors import messages
from webbrowser import Error

import asyncpg
from aiohttp import web
from asyncpg.pool import Pool
import os  # Для работы с файловой системой
from typing import List, Tuple, Optional, Union  # Аннотации типов для лучшей читаемости
from dotenv import load_dotenv  # Для загрузки переменных окружения из .env файла

# Импорт компонентов из библиотеки aiogram для работы с Telegram API
from aiogram import Bot, Dispatcher, Router, F  # Основные компоненты
from aiogram.client.default import DefaultBotProperties  # Настройки бота по умолчанию
from aiogram.enums import ParseMode  # Режимы форматирования текста (HTML, Markdown)
from aiogram.filters import Command, CommandStart  # Фильтры для обработки команд
from aiogram.fsm.context import FSMContext  # Контекст машины состояний
from aiogram.fsm.state import State, StatesGroup  # Система состояний
from aiogram.fsm.storage.memory import MemoryStorage  # Хранилище состояний в оперативной памяти
from aiogram.types import (  # Типы данных Telegram
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardRemove, WebAppInfo
)

# Импорт текстовых сообщений из отдельного файла (config.py)
from config import *

# Загрузка переменных окружения ДОЛЖНА БЫТЬ ВЫЗВАНА
load_dotenv(""".env""")

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


""" 
=============== БОТ 1: ОСНОВНОЙ БОТ (ГЛАВНОЕ МЕНЮ) =============== 
Этот бот предоставляет простое меню с кнопками и информацией о проекте
"""

# Получаем токен бота из переменных окружения
BOT_TOKEN_MAIN = os.getenv("BOT_TOKEN_MAIN")

# Создаем хранилище состояний в оперативной памяти
storage = MemoryStorage()

# Создаем маршрутизатор для обработки сообщений этого бота
router_main = Router()

class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()


@router_main.message(Command("start"))
async def start_with_polling(message: Message, state: FSMContext):

    user_id = message.from_user.id
    try:
        # Проверяем существование пользователя в БД
        async with db_pool.acquire() as conn:
            user_exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE user_id = $1",
                user_id
            )

        # Новый пользователь - начинаем опрос
        await state.update_data(
            user_id=user_id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "",
            lang_code=message.from_user.language_code or "en",
            chosen_language="",
            camefrom="",
            about="",
        )

    except Exception as e:
        logging.error(f"Error in start handler: {e}")

    # Если пользователь существует - показываем главное меню
    if user_exists:
        await show_main_menu(message, state)
        return

    # Получаем данные из состояния
    data = await state.get_data()
    lang_code = data['lang_code']
    if lang_code not in ['en', 'ru']:
        lang_code = 'en'

    # Создаем безопасные callback-данные
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                    text=QUESTIONARY["where_youcamefrom"][f"{lang_code}0"],
                    callback_data="camefrom_friends"
            )
        ],
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}1"],
                callback_data="camefrom_search"
            )
        ],
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}2"],
                callback_data="camefrom_other"
            )
        ]
    ])
        # Отправляю через функцию с сохранением ID сообщения
    await send_message_with_save(message, QUESTIONARY["intro"][lang_code], state, True, keyboard )
    await state.set_state(PollingStates.camefrom_state)


@router_main.callback_query(F.data.startswith("camefrom_"), PollingStates.camefrom_state)
async def handle_camefrom(callback: CallbackQuery, state: FSMContext):
    try:
        camefrom = callback.data.split("_")[1]
        await state.update_data(camefrom=camefrom)

        data = await state.get_data()
        lang_code = data.get('lang_code', 'en')

        # Кнопки выбора языка с простыми callback-данными
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_russian"),
            ],
            [
                InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_english")
            ],
            [
                InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_german"),
            ],
            [
                InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_spanish")
            ],
            [
                InlineKeyboardButton(text="🇨🇳 中文", callback_data="lang_chineese")
            ]
        ])

        await send_message_with_save(callback, QUESTIONARY["lang_pick"][lang_code], state, True, keyboard)
        await state.set_state(PollingStates.language_state)
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in camefrom handler: {e}")


@router_main.callback_query(F.data.startswith("lang_"), PollingStates.language_state)
async def handle_language_choice(callback: CallbackQuery, state: FSMContext):
    try:

        data = await state.get_data()
        lang_code = data.get('lang_code', 'en')

        # Кнопка подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=QUESTIONARY["confirm"][lang_code],
                callback_data="action_confirm"
            )]
        ])

        users_choice = callback.data.split("_")[1]

        await callback.message.edit_text(
            text=f"➪ Вы выбрали: {users_choice}\n\n{QUESTIONARY['gratitude'][lang_code]}",
            reply_markup=keyboard
        )
        await state.set_state(PollingStates.introduction_state)
        await callback.answer()

        # Сохраняем пользователя в БД
        user_id = data['user_id']
        username = data.get('username', 'None')
        first_name = data.get('first_name', 'None')
        camefrom = data.get('camefrom', 'None')
        await create_users_table(user_id, username, first_name, camefrom, users_choice, lang_code)

    except Exception as e:
        logging.error(f"Error in language choice: {e}")




@router_main.callback_query(F.data == "action_confirm", PollingStates.introduction_state)
async def start_main_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    # Удаляем все предыдущие сообщения
    await delete_previous_messages(callback.bot, callback.message.chat.id, state)
    # Очищаем состояние опроса
    await state.clear()

    # Заполняем память актуальной информацией о пользователе
    username, first_name, language, lang_code = await get_user_info(user_id)
    await state.update_data(
        user_id = user_id,
        username = username,
        first_name = first_name,
        language = language,
        lang_code = lang_code,
    )

    # Показываем главное меню
    await show_main_menu(callback.message, state)


async def show_main_menu(message: Message, state: FSMContext):
    """Показывает главное меню для пользователя"""
    data = await state.get_data()
    user_id = data["user_id"]
    first_name = data["first_name"]
    lang_code = data["lang_code"]

    # Формируем URL с user_id
    web_app_url = f"https://jebb2108.github.io/index.html?user_id={user_id}"

    # Создаем клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTONS["dictionary"][lang_code], web_app=WebAppInfo(url=web_app_url)),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["find_partner"][lang_code], url="https://t.me/lllang_dictbot"),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["about_bot"][lang_code], callback_data="about"),
            InlineKeyboardButton(text=BUTTONS["support"][lang_code], url="https://t.me/user_bot6426"),
        ],
    ])

    await message.answer(
        f"{BUTTONS["hello"][lang_code]}<b>{first_name}</b>!\n\n{QUESTIONARY["welcome"][lang_code]}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router_main.callback_query(F.data == "about")
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте"
    Показывает подробную информацию о проекте
    """

    data = await state.get_data()
    lang_code = data["lang_code"]
    # Клавиатура только с кнопкой возврата
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
    ])

    # Редактируем текущее сообщение, заменяя его на текст "О боте"
    await callback.message.edit_text(QUESTIONARY["about"][lang_code], reply_markup=keyboard)
    # Подтверждаем обработку callback (убираем часики на кнопке)
    await callback.answer()


@router_main.callback_query(F.data == "go_back")
async def go_back(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    first_name = data["first_name"]
    lang_code = data["lang_code"]
    # URL вашего Web App
    web_app_url = "https://jebb2108.github.io/index.html"

    # Создаем клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTONS["dictionary"][lang_code], web_app=WebAppInfo(url=web_app_url)),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["find_partner"][lang_code], url="https://t.me/lllang_dictbot"),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["about_bot"][lang_code], callback_data="about"),
            InlineKeyboardButton(text=BUTTONS["support"][lang_code], url="https://t.me/user_bot6426"),
        ],
    ])

    # Отправляем приветственное сообщение с клавиатурой
    await callback.message.edit_text(f"{BUTTONS["hello"][lang_code]}<b>{first_name}</b>!\n\n{QUESTIONARY["welcome"][lang_code]}", reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


async def send_message_with_save(message: Union[Message, CallbackQuery], text: str, state: FSMContext, markup=False, keyboard=None):
    if isinstance(message, CallbackQuery):
        message = message.message
    if markup:
        sent_message = await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    else:
        sent_message = await message.answer(text)

    data = await state.get_data()
    curr_messages = data.get("messages_to_delete", [])
    curr_messages.append(sent_message.message_id)

    await state.update_data(messages_to_delete=curr_messages)
    return sent_message


async def delete_previous_messages(bot: Bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    if "messages_to_delete" in data:
        for msg_id in data["messages_to_delete"]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
        await state.update_data(messages_to_delete=[])


@router_main.message()
async def handle_other_messages(message: Message):
    """
    Обработчик всех остальных сообщений (не команд)
    Напоминает пользователю использовать /start
    """
    await message.answer("Используйте /start для получения меню")


"""
=============== ЗАПУСК WEB API ===============
Функции для запуска WEB приложения, отображающее выученные слова
"""


# Создаем HTTP-сервер для Web App
async def web_app_handler(request):
    return web.FileResponse("webapp/dist/index.html")


# API для получения слов пользователя
async def api_words_handler(request):
    user_id = int(request.query.get('user_id'))
    # Используем правильную функцию для получения слов
    words = await get_words_from_db(user_id)

    # Преобразование в JSON-совместимый формат
    words_json = []
    for word_tuple in words:
        # word_tuple: (word, part_of_speech, translation)
        words_json.append({
            'word': word_tuple[0],
            'part_of_speech': word_tuple[1],
            'translation': word_tuple[2]
        })

    logging.info(f"Sent {len(words_json)} words for user {user_id}")
    return web.json_response(words_json)


# = ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =
# Каждый пользователь имеет свою базу данных SQLite в папке dbs

async def init_db():
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
    """Создает или обновляет запись пользователя"""
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


"""
=============== ЗАПУСК WEB API ===============
Функции для запуска WEB приложения, отображающее выученные слова
"""


# Создаем HTTP-сервер для Web App
async def web_app_handler(request):
    return web.FileResponse("webapp/dist/index.html")


# API для получения слов пользователя
async def api_words_handler(request):
    user_id = int(request.query.get('user_id'))
    # Используем правильную функцию для получения слов
    words = await get_words_from_db(user_id)

    # Преобразование в JSON-совместимый формат
    words_json = []
    for word_tuple in words:
        # word_tuple: (word, part_of_speech, translation)
        words_json.append({
            'word': word_tuple[0],
            'part_of_speech': word_tuple[1],
            'translation': word_tuple[2]
        })

    logging.info(f"Sent {len(words_json)} words for user {user_id}")
    return web.json_response(words_json)



"""
===== ЗАПУСК ВСЕЙ СИСТЕМЫ =====
"""


async def run_bot(bot_token: str, router: Router, storage=None):
    """
    Запускает одного бота
    Параметры:
    - bot_token: токен Telegram бота
    - router: маршрутизатор с обработчиками
    - storage: хранилище состояний (опционально)
    """
    # Создаем объект бота с HTML-форматированием по умолчанию
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Создаем диспетчер
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    # Подключаем маршрутизатор с обработчиками
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бота в режиме опроса сервера Telegram
    await dp.start_polling(bot)



async def run():

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    await init_db()
    bot = Bot(token=BOT_TOKEN_MAIN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.include_router(router_main)

    logging.info("Starting main bot (polling)…")
    await dp.start_polling(bot)
    await close_db()

if __name__ == "__main__":
    asyncio.run(run())