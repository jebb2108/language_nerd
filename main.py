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
import asyncpg
from aiohttp import web
from asyncpg.pool import Pool
import os  # Для работы с файловой системой
from typing import List, Tuple, Optional  # Аннотации типов для лучшей читаемости
from dotenv import load_dotenv  # Для загрузки переменных окружения из .env файла

# Импорт компонентов из библиотеки aiogram для работы с Telegram API
from aiogram import Bot, Dispatcher, Router, F  # Основные компоненты
from aiogram.client.default import DefaultBotProperties  # Настройки бота по умолчанию
from aiogram.enums import ParseMode  # Режимы форматирования текста (HTML, Markdown)
from aiogram.filters import Command, CommandStart, StateFilter  # Фильтры для обработки команд
from aiogram.fsm.context import FSMContext  # Контекст машины состояний
from aiogram.fsm.state import State, StatesGroup  # Система состояний
from aiogram.fsm.storage.memory import MemoryStorage  # Хранилище состояний в оперативной памяти
from aiogram.types import (  # Типы данных Telegram
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardRemove
)

# Импорт текстовых сообщений из отдельного файла (mssgs.py)
from mssgs import *

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

WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8000

# Обработка порта с проверкой
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


""" 
=============== БОТ 1: ОСНОВНОЙ БОТ (ГЛАВНОЕ МЕНЮ) =============== 
Этот бот предоставляет простое меню с кнопками и информацией о проекте
"""

# Получаем токен бота из переменных окружения
BOT_TOKEN_MAIN = os.getenv("BOT_TOKEN_MAIN")

# Создаем маршрутизатор для обработки сообщений этого бота
router_main = Router()


@router_main.message(Command("start"))
async def start(message: Message):
    """
    Обработчик команды /start
    Показывает приветственное сообщение и главное меню
    """
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            # Кнопка перехода к боту-словарю
            InlineKeyboardButton(text="📚 Бот-словарь", url="https://t.me/lllang_dictbot"),
            # Кнопка технической поддержки
            InlineKeyboardButton(text="🛠 Поддержка", url="https://t.me/NonGrata4Life")
        ],
        [
            # Кнопка информации о боте
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ],
    ])
    # Отправляем приветственное сообщение с клавиатурой
    await message.answer(f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n{WELCOME}", reply_markup=keyboard)


@router_main.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    """
    Обработчик нажатия кнопки "О боте"
    Показывает подробную информацию о проекте
    """
    # Клавиатура только с кнопкой возврата
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
    ])

    # Редактируем текущее сообщение, заменяя его на текст "О боте"
    await callback.message.edit_text(ABOUT, reply_markup=keyboard)
    # Подтверждаем обработку callback (убираем часики на кнопке)
    await callback.answer()

@router_main.callback_query(F.data == "go_back")
async def go_back(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            # Кнопка перехода к боту-словарю
            InlineKeyboardButton(text="📚 Бот-словарь", url="https://t.me/lllang_dictbot"),
            # Кнопка технической поддержки
            InlineKeyboardButton(text="🛠 Поддержка", url="https://t.me/NonGrata4Life")
        ],
        [
            # Кнопка информации о боте
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ],
    ])
    # Отправляем приветственное сообщение с клавиатурой
    await callback.message.edit_text(f"👋 Привет, <b>{callback.from_user.first_name}</b>!\n\n{WELCOME}", reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()



@router_main.message()
async def handle_other_messages(message: Message):
    """
    Обработчик всех остальных сообщений (не команд)
    Напоминает пользователю использовать /start
    """
    await message.answer("Используйте /start для получения меню")


""" 
=============== БОТ 2: СЛОВАРЬ (УПРАВЛЕНИЕ ЛЕКСИКОНОМ) =============== 
Этот бот позволяет пользователям создавать и управлять персональным словарем
Каждый пользователь имеет свою собственную базу данных SQLite
"""

# Получаем токен бота-словаря из переменных окружения
BOT_TOKEN_DICT = os.getenv("BOT_TOKEN_DICT")

# Создаем маршрутизатор для обработки сообщений этого бота
router_dict = Router()

# Создаем хранилище состояний в оперативной памяти
storage = MemoryStorage()


# = СИСТЕМА СОСТОЯНИЙ (Finite State Machine) =
# Состояния помогают отслеживать, где находится пользователь в процессе работы

class WordStates(StatesGroup):
    """
    Состояния для процесса добавления нового слова:
    - waiting_for_pos: ожидание выбора части речи
    - waiting_for_custom_pos: ожидание ручного ввода части речи
    """
    waiting_for_pos = State()
    waiting_for_custom_pos = State()


class WordsViewState(StatesGroup):
    """Состояние для процесса просмотра словаря"""
    viewing_words = State()


class EditState(StatesGroup):
    """
    Состояния для процесса редактирования слова:
    - waiting_edit_word: ожидание нового текста слова
    - waiting_edit_pos: ожидание части речи
    - waiting_edit_value: ожидание нового значения
    """
    waiting_edit_word = State()
    waiting_edit_pos = State()
    waiting_edit_value = State()


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
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.critical(f"Database initialization failed: {e}")
        raise


async def close_db():
    """Закрытие пула соединений"""
    global db_pool
    if db_pool:
        await db_pool.close()

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


# = ОСНОВНЫЕ ОБРАБОТЧИКИ БОТА-СЛОВАРЯ =

@router_dict.message(Command("list"))
async def show_dictionary(message: Message, state: FSMContext):
    """
    Обработчик команды /list
    Показывает словарь пользователя с возможностью навигации
    """
    # Получаем ID пользователя
    user_id = message.from_user.id
    # Загружаем все слова из базы
    words = await get_words_from_db(user_id)

    # Если слов нет - сообщаем об этом
    if not words:
        await message.answer("📭 Ваш словарь пуст. Добавьте первое слово!")
        return

    # Сохраняем слова в контексте состояния
    await state.update_data(
        words=words,  # Список всех слов
        current_index=0,  # Текущий индекс (начинаем с первого слова)
        # Первая буква первого слова (для навигации по буквам)
        current_letter=words[0][0][0].upper() if words[0][0] else 'A'
    )

    # Показываем первое слово
    await show_current_word(message, state)
    # Переводим пользователя в состояние просмотра слов
    await state.set_state(WordsViewState.viewing_words)


async def show_current_word(message: Message, state: FSMContext, edit: bool = False, full_info: bool = False):
    """
    Показывает текущее слово с навигацией

    Параметры:
    - edit: True - редактирует существующее сообщение, False - отправляет новое
    - full_info: True - показывает полную информацию без сокращений
    """
    # Получаем данные из текущего состояния
    data = await state.get_data()
    # Список всех слов
    words = data.get("words", [])
    # Текущий индекс (какое слово показываем)
    current_index = data.get("current_index", 0)

    # Проверяем что у нас есть слова и индекс в допустимых пределах
    if not words or current_index >= len(words):
        await message.answer("❌ Слов не найдено")
        # Сбрасываем состояние
        await state.clear()
        return

    # Извлекаем данные текущего слова
    word, pos, value = words[current_index]

    # Форматируем сообщение с HTML-разметкой
    if full_info:
        # = РЕЖИМ ПОЛНОЙ ИНФОРМАЦИИ =
        text = (
            f"📖 <b>Полная информация:</b> {word}\n"
            f"🔢 <b>Номер слова:</b> {current_index + 1} out of {len(words)}\n"
            f"🔤 <b>Часть речи:</b> {pos}\n"
        )
        # Если есть значение слова - добавляем его полностью
        if value:
            text += f"💡 <b>Детальное значение:</b>\n{value}\n"

        # Клавиатура только с кнопкой возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
        ])
    else:
        # === СТАНДАРТНЫЙ РЕЖИМ (СОКРАЩЕННАЯ ИНФОРМАЦИЯ) ===
        text = (
            # Заголовок с выравниванием
            f"📖 <b>Слово</b>: {word}\n"
            f"🔢 <b>Номер слова:</b> {current_index + 1} out of {len(words)}\n"
            f"🔤 <b>Часть речи слова:</b> {pos}\n"
        )
        # Если есть значение - добавляем его (сокращаем если слишком длинное)
        if value:
            # Берем первые 50 символов или полное значение если оно короче
            shortened_value = value[:23] + '...' if len(value) > 23 else value
            text += f"💡 <b>Краткое значение:</b> {shortened_value}"

        # Создаем клавиатуру с кнопками действий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            # Кнопка показа полной информации
            [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="show_info")],
            # Кнопки навигации: предыдущее и следующее слово
            [
                InlineKeyboardButton(text="⬅️", callback_data="prev_word"),
                InlineKeyboardButton(text="➡️", callback_data="next_word")
            ],
            # Кнопки навигации по буквам
            [
                InlineKeyboardButton(text="⬆️ Буква", callback_data="prev_letter"),
                InlineKeyboardButton(text="Буква ⬇️", callback_data="next_letter")
            ],
            # Кнопки действий: редактирование и удаление
            [
                InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_word"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_word")
            ],
            # Кнопка отмены/выхода
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_words")]
        ])

    # Отправляем или редактируем сообщение
    if edit:
        # Редактируем существующее сообщение
        await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        # Отправляем новое сообщение
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


# = ОБРАБОТЧИКИ КНОПОК НАВИГАЦИИ =

@router_dict.callback_query(F.data == "prev_word", WordsViewState.viewing_words)
async def prev_word_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Предыдущее слово'"""
    # Получаем данные из состояния
    data = await state.get_data()
    current_index = data.get("current_index", 0)

    # Если это не первое слово
    if current_index > 0:
        # Уменьшаем индекс на 1
        await state.update_data(current_index=current_index - 1)
        # Показываем предыдущее слово (редактируем текущее сообщение)
        await show_current_word(callback.message, state, edit=True)
    else:
        # Если это первое слово - показываем подсказку
        await callback.answer("You're at the first word")

    # Подтверждаем обработку callback
    await callback.answer()


@router_dict.callback_query(F.data == "next_word", WordsViewState.viewing_words)
async def next_word_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Следующее слово'"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    # Если это не последнее слово
    if current_index < len(words) - 1:
        # Увеличиваем индекс на 1
        await state.update_data(current_index=current_index + 1)
        # Показываем следующее слово
        await show_current_word(callback.message, state, edit=True)
    else:
        # Если это последнее слово - показываем подсказку
        await callback.answer("You're at the last word")

    await callback.answer()


@router_dict.callback_query(F.data == "prev_letter", WordsViewState.viewing_words)
async def prev_letter_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Предыдущая буква'
    Переходит к первой букве в предыдущей группе слов
    """
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)
    current_letter = data.get("current_letter", 'A')

    # Получаем уникальные первые буквы всех слов
    letters = sorted(set(
        word[0][0].upper()
        for word in words
        if word[0] and len(word[0]) > 0  # Проверка что слово не пустое
    ))

    # Если нет букв - сообщаем об этом
    if not letters:
        await callback.answer("No letters found")
        return

    try:
        # Находим текущую позицию буквы в списке
        current_pos = letters.index(current_letter)
        # Вычисляем новую позицию (не меньше 0)
        new_pos = max(0, current_pos - 1)
        # Берем букву по новой позиции
        new_letter = letters[new_pos]
    except ValueError:
        # Если текущей буквы нет в списке - берем первую
        new_letter = letters[0]

    # Ищем первое слово с новой буквой
    new_index = next((
        i for i, word in enumerate(words)
        if word[0] and word[0][0].upper() == new_letter
    ), 0)  # Если не нашли - начинаем с 0

    # Обновляем состояние
    await state.update_data(
        current_index=new_index,
        current_letter=new_letter
    )
    # Показываем новое слово
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.callback_query(F.data == "next_letter", WordsViewState.viewing_words)
async def next_letter_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Следующая буква'
    Переходит к первой букве в следующей группе слов
    """
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)
    current_letter = data.get("current_letter", 'A')

    # Получаем уникальные первые буквы всех слов
    letters = sorted(set(
        word[0][0].upper()
        for word in words
        if word[0] and len(word[0]) > 0
    ))

    if not letters:
        await callback.answer("No letters found")
        return

    try:
        # Находим текущую позицию буквы
        current_pos = letters.index(current_letter)
        # Вычисляем новую позицию (не больше длины списка)
        new_pos = min(len(letters) - 1, current_pos + 1)
        new_letter = letters[new_pos]
    except ValueError:
        # Если текущей буквы нет - берем последнюю
        new_letter = letters[-1]

    # Ищем первое слово с новой буквой
    new_index = next((
        i for i, word in enumerate(words)
        if word[0] and word[0][0].upper() == new_letter
    ), 0)

    # Обновляем состояние
    await state.update_data(
        current_index=new_index,
        current_letter=new_letter
    )
    # Показываем новое слово
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.callback_query(F.data == "cancel_words", WordsViewState.viewing_words)
async def cancel_words_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Отмена'
    Выходит из режима просмотра слов
    """
    # Удаляем сообщение с навигацией
    await callback.message.delete()
    # Сбрасываем состояние
    await state.clear()
    await callback.answer()


@router_dict.callback_query(F.data == "delete_word", WordsViewState.viewing_words)
async def delete_word_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Удалить слово'
    Удаляет текущее слово из базы данных
    """
    # Получаем ID пользователя
    user_id = callback.from_user.id
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    # Проверяем что есть слова и индекс в допустимых пределах
    if not words or current_index >= len(words):
        await callback.answer("No word to delete")
        return

    # Извлекаем слово для удаления
    word, _, _ = words[current_index]

    # Пытаемся удалить слово из базы
    if await delete_word_from_db(user_id, word):
        # Если удаление успешно - загружаем обновленный список слов
        words = await get_words_from_db(user_id)

        # Если словарь стал пустым
        if not words:
            # Сбрасываем состояние
            await state.clear()
            return

        # Корректируем текущий индекс (чтобы не выйти за пределы)
        new_index = current_index if current_index < len(words) else len(words) - 1
        # Берем первую букву нового текущего слова
        new_letter = words[new_index][0][0].upper() if words[new_index][0] else 'A'

        # Обновляем состояние
        await state.update_data(
            words=words,
            current_index=new_index,
            current_letter=new_letter
        )

        # Обновляем интерфейс
        await show_current_word(callback.message, state, edit=True)
        # Показываем уведомление об успешном удалении
    else:
        # Если удаление не удалось
        await callback.answer(f"❌ Что-то пошло не так {word}")


@router_dict.callback_query(F.data == "edit_word", WordsViewState.viewing_words)
async def start_edit_word(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Редактировать'
    Начинает процесс редактирования слова
    """
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    # Проверяем что есть слова для редактирования
    if not words or current_index >= len(words):
        await callback.answer("No word to edit")
        return

    # Извлекаем данные текущего слова
    word, pos, value = words[current_index]

    # Сохраняем текущие значения для возможного сравнения
    await state.update_data(
        editing_word=word,  # Слово которое редактируем
        editing_pos=pos,  # Текущая часть речи
        editing_value=value,  # Текущее значение
        editing_index=current_index,  # Текущий индекс
        original_word=word,  # Оригинальное слово (для сравнения)
        original_pos=pos,  # Оригинальная часть речи
        original_value=value  # Оригинальное значение
    )

    # Создаем клавиатуру выбора поля для редактирования
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            # Кнопки выбора что редактировать
            InlineKeyboardButton(text="✏️ Слово", callback_data="edit_word_text"),
            InlineKeyboardButton(text="💡 Значение", callback_data="edit_word_value")
        ],
        [
            InlineKeyboardButton(text="🔤 Часть речи", callback_data="edit_word_pos")
        ],
        # Кнопка возврата
        [InlineKeyboardButton(text="↩️ Назад", callback_data="cancel_edit")]
    ])

    # Редактируем сообщение для показа меню редактирования
    await callback.message.edit_text(
        f"✏️ <b>Редактирование:</b> {word}\n"
        f"🔤 <b>Текущая часть речи:</b> {pos}\n"
        f"💡 <b>Текущее значение:</b> {value or 'None'}\n\n"
        "Выберите, что отредактировать:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    # Переводим пользователя в состояние редактирования
    await state.set_state(EditState.waiting_edit_word)


@router_dict.callback_query(F.data.startswith("edit_word_"), EditState.waiting_edit_word)
async def handle_edit_choice(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора поля для редактирования
    Определяет какое поле выбрал пользователь
    """
    # Извлекаем тип редактирования из callback_data
    edit_type = callback.data.replace("edit_word_", "")
    data = await state.get_data()
    word = data.get("editing_word", "")

    # В зависимости от выбранного поля
    if edit_type == "text":
        # Запрашиваем новый текст слова
        await callback.message.edit_text(f"✏️ Введите новое слово для <b>{word}</b>:", parse_mode=ParseMode.HTML)
        # Остаемся в том же состоянии (waiting_edit_word)
        await state.set_state(EditState.waiting_edit_word)
    elif edit_type == "value":
        # Запрашиваем новое значение
        await callback.message.edit_text(f"💡 Введите новое значение для <b>{word}</b>:", parse_mode=ParseMode.HTML)
        # Переводим в состояние ожидания значения
        await state.set_state(EditState.waiting_edit_value)
    elif edit_type == "pos":
        # Показываем клавиатуру выбора части речи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Noun", callback_data="newpos_noun"),
             InlineKeyboardButton(text="Verb", callback_data="newpos_verb")],
            [InlineKeyboardButton(text="Adjective", callback_data="newpos_adjective"),
             InlineKeyboardButton(text="Adverb", callback_data="newpos_adverb")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="cancel_edit")]
        ])
        await callback.message.edit_text(
            f"🔤 Выберите новую часть речи для <b>{word}</b>:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        # Переводим в состояние ожидания части речи
        await state.set_state(EditState.waiting_edit_pos)

    await callback.answer()


@router_dict.callback_query(F.data == "cancel_edit", EditState.waiting_edit_word)
@router_dict.callback_query(F.data == "cancel_edit", EditState.waiting_edit_value)
@router_dict.callback_query(F.data == "cancel_edit", EditState.waiting_edit_pos)
async def cancel_edit_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Назад' в режиме редактирования
    Отменяет редактирование и возвращает к просмотру слова
    """
    # Возвращаемся в состояние просмотра слов
    await state.set_state(WordsViewState.viewing_words)
    # Показываем текущее слово
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.callback_query(F.data == "show_info", WordsViewState.viewing_words)
async def show_full_info_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Информация'
    Показывает полную информацию о слове
    """
    # Редактируем сообщение для показа полной информации
    await show_current_word(callback.message, state, edit=True, full_info=True)
    await callback.answer()


@router_dict.callback_query(F.data == "go_back", WordsViewState.viewing_words)
async def go_back_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Назад' в режиме полной информации
    Возвращает к стандартному виду информации
    """
    # Возвращаемся к стандартному виду
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


# = ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ПОЛЕЙ =

@router_dict.message(EditState.waiting_edit_word)
async def handle_edit_word_text(message: Message, state: FSMContext):
    """
    Обработчик нового текста слова
    Вызывается когда пользователь вводит новое слово
    """
    user_id = message.from_user.id
    # Очищаем введенный текст

    data = await state.get_data()
    old_word = data.get("editing_word", "")
    original_word = data.get("original_word", "")

    # Если слово изменилось (а не только перевод или часть речи)
    if old_word != original_word:
        # Проверяем нет ли уже такого слова в словаре
        words = await get_words_from_db(user_id)
        if any(w[0].lower() == old_word.lower() for w in words):
            await message.answer("⚠️ Это слово уже существует в словаре")
            return

    # Обновляем данные в состоянии
    await state.update_data(editing_word=old_word)
    # Сохраняем изменения
    await save_edited_word(message, state, user_id)


@router_dict.message(EditState.waiting_edit_value)
async def handle_edit_word_value(message: Message, state: FSMContext):
    """
    Обработчик нового значения слова
    Вызывается когда пользователь вводит новое значение
    """
    # Очищаем введенный текст
    new_value = message.text.strip()
    # Обновляем данные в состоянии
    await state.update_data(editing_value=new_value)
    # Сохраняем изменения
    await save_edited_word(message, state, message.from_user.id)


@router_dict.callback_query(F.data.startswith("newpos_"), EditState.waiting_edit_pos)
async def handle_edit_word_pos(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора новой части речи
    Вызывается когда пользователь выбирает часть речи из кнопок
    """
    # Извлекаем часть речи из callback_data
    new_pos = callback.data.replace("newpos_", "")
    # Обновляем данные в состоянии
    await state.update_data(editing_pos=new_pos)
    # Сохраняем изменения
    await save_edited_word(callback.message, state, callback.from_user.id)
    await callback.answer()


async def save_edited_word(message: Message, state: FSMContext, user_id: int):
    """
    Сохраняет изменения слова в базе данных
    Общая функция для всех типов редактирования
    """
    data = await state.get_data()
    # Текущие значения из состояния
    new_word = data.get("editing_word", "")
    new_pos = data.get("editing_pos", "")
    new_value = data.get("editing_value", "")

    # Оригинальные значения (до редактирования)
    original_word = data.get("original_word", "")
    original_pos = data.get("original_pos", "")
    original_value = data.get("original_value", "")

    editing_index = data.get("editing_index", 0)

    # Проверяем были ли вообще изменения
    if (new_word == original_word and
            new_pos == original_pos and
            new_value == original_value):
        # Если изменений нет - сообщаем и возвращаемся к просмотру
        await message.answer("ℹ️ Изменений не обнаружено")
        await state.set_state(WordsViewState.viewing_words)
        await show_current_word(message, state, edit=True)
        return

    # Обновляем слово в базе данных
    success = await update_word_in_db(
        user_id,
        original_word,
        new_word,
        new_pos,
        new_value
    )

    if success:
        # Если обновление успешно - загружаем обновленный список слов
        words = await get_words_from_db(user_id)

        # Находим новую позицию слова в списке
        # (слово могло переместиться из-за алфавитной сортировки)
        new_index = next((
            i for i, w in enumerate(words)
            if w[0] == new_word
        ), editing_index)

        # Обновляем состояние
        await state.update_data(
            words=words,
            current_index=new_index
        )

        # Возвращаемся к просмотру
        await state.set_state(WordsViewState.viewing_words)
        # Показываем обновленное слово
        await show_current_word(message, state, edit=True)
    else:
        # Если обновление не удалось
        await message.answer("❌ Что-то пошло не так")
        await state.set_state(WordsViewState.viewing_words)
        await show_current_word(message, state, edit=True)


# = ОБРАБОТЧИКИ ДОБАВЛЕНИЯ НОВЫХ СЛОВ =

@router_dict.message(CommandStart())
async def start_command_handler(message: Message):
    """
    Обработчик команды /start для бота-словаря
    Показывает приветственное сообщение
    """
    # Персонализированное приветствие
    await message.answer(
        text=DICT_GREETING,
        parse_mode=ParseMode.HTML
    )


# Обработка кнопки Other (ручной ввод части речи)
@router_dict.callback_query(F.data == "pos_other", WordStates.waiting_for_pos)
async def ask_custom_part_of_speech(callback: CallbackQuery, state: FSMContext):
    """Запрос на ручной ввод части речи"""
    await callback.message.edit_text("✍️ Введите вашу часть речи:")
    # Переводим в состояние ожидания ручного ввода
    await state.set_state(WordStates.waiting_for_custom_pos)
    await callback.answer()


# Обработка ручного ввода части речи
@router_dict.message(WordStates.waiting_for_custom_pos)
async def handle_custom_part_of_speech(message: Message, state: FSMContext):
    """Обработка ручного ввода части речи"""
    # Очищаем введенный текст
    custom_pos = message.text.strip().lower()
    # Проверяем что ввод не пустой
    if not custom_pos:
        await message.answer("Пожалуйста, введите корректное значение")
        return

    # Получаем данные из состояния
    user_id = message.from_user.id
    data = await state.get_data()
    word = data["word"]
    value = data.get("value")

    # Сохраняем слово в базу
    if await add_word_to_db(user_id, word, custom_pos, value):
        # Формируем сообщение об успехе
        response = f"✅ Сохранено: {word} ({custom_pos})"
        if value:
            shortened_value = value[:23] + '...' if len(value) > 23 else value
            response += f"\nКраткое значение: {shortened_value}"
        await message.answer(response)
    else:
        await message.answer("❌ Что-то пошло не так")

    # Сбрасываем состояние
    await state.clear()


""" 
    Слова, не попавшие в регистр waiting_for_custom_pos, 
    проходят дальше в обработчике handle_part_of_speech_text
    
"""

@router_dict.message(WordStates.waiting_for_pos)
async def handle_part_of_speech_text(message: Message):
    """
    Напоминание использовать кнопки
    Вызывается если пользователь ввел текст вместо выбора части речи
    """
    await message.answer("⚠️ Пожалуйста, выберите часть речи")


# Обработка кнопки Cancel (отмена добавления слова)
@router_dict.callback_query(F.data == "pos_cancel", WordStates.waiting_for_pos)
async def cancel_adding_word(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления слова"""
    await state.clear()
    await callback.message.edit_text("❌ Добавление отменено")
    await callback.answer()



@router_dict.callback_query(F.data.startswith("pos_"), WordStates.waiting_for_pos)
async def save_new_word_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохраняет новое слово после выбора части речи
    Вызывается при нажатии на кнопку с частью речи
    """
    user_id = callback.from_user.id
    # Извлекаем часть речи из callback_data
    part_of_speech = callback.data.replace("pos_", "")
    data = await state.get_data()
    # Извлекаем слово и значение из состояния
    word = data.get("word")
    value = data.get("value")

    # Сохраняем слово в базу данных
    if await add_word_to_db(user_id, word, part_of_speech, value):
        # Формируем сообщение об успехе
        response = f"✅ Сохранено: {word} ({part_of_speech})"
        # Если есть значение - добавляем его (сокращаем если длинное)
        if value:
            shortened_value = value[:23] + '...' if len(value) > 23 else value
            response += f"\nКраткое значение: {shortened_value}"

        # Редактируем сообщение с результатом
        await callback.message.edit_text(response)
        await callback.answer()
        # Сбрасываем состояние
        await state.clear()
    else:
        # Если не удалось сохранить
        await callback.message.edit_text("❌ Что-то пошло не так")
        await callback.answer()




# ==== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ====

@router_dict.message()
async def universal_message_handler(message: Message, state: FSMContext):
    """
    Обрабатывает все текстовые сообщения, не являющиеся командами
    Определяет что хочет сделать пользователь на основе текущего состояния
    """
    # Игнорируем команды (они обрабатываются другими обработчиками)
    if message.text.startswith('/'):
        return

    logging.info(f"{message.from_user.id}: new message: {message.text}")

    # Получаем текущее состояние пользователя
    current_state = await state.get_state()

    # Если пользователь должен выбрать часть речи
    if current_state == WordStates.waiting_for_pos.state:
        # Напоминаем использовать кнопки
        await handle_part_of_speech_text(message)
        return

    # Если пользователь в процессе редактирования слова
    if current_state in [
        EditState.waiting_edit_word.state,
        EditState.waiting_edit_pos.state,
        EditState.waiting_edit_value.state
    ]:
        # Пропускаем сообщение (обработчики состояний сами обработают его)
        return

    # Если не в каком-то специальном состоянии - начинаем процесс добавления слова
    await process_word_input(message, state)


async def process_word_input(message: Message, state: FSMContext):
    """
    Обрабатывает ввод нового слова
    Начинает процесс добавления слова в словарь
    """
    user_id = message.from_user.id
    # Очищаем текст сообщения
    text = message.text.strip().lower()

    # Проверяем формат "слово:значение"
    if ':' in text:
        # Разделяем на слово и значение
        parts = text.split(':', 1)
        word = parts[0].strip()
        # Значение может быть пустым
        value = parts[1].strip() if parts[1].strip() else ""
    else:
        # Если нет двоеточия - только слово, без значения
        word, value = text, ""

    # Проверяем нет ли уже такого слова в словаре
    if await check_word_exists(user_id, word):
        await message.answer("⚠️ Слово уже существует")
        # Сбрасываем состояние
        await state.clear()
        return

    # Сохраняем слово и значение в состоянии
    await state.update_data(word=word, value=value)

    # Создаем клавиатуру выбора части речи
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Существительное", callback_data="pos_noun"),
        ],
        [
            InlineKeyboardButton(text="Глагол", callback_data="pos_verb"),
            InlineKeyboardButton(text="Прилагательное", callback_data="pos_adjective"),
        ],
        [
            InlineKeyboardButton(text="Наречие", callback_data="pos_adverb"),
            InlineKeyboardButton(text="Другое", callback_data="pos_other"),
        ],
        [
            InlineKeyboardButton(text="Отменить", callback_data="pos_cancel")
        ],

    ])

    # Спрашиваем часть речи
    await message.answer("❓ Какая это часть речи?", reply_markup=keyboard)
    # Переводим в состояние ожидания выбора части речи
    await state.set_state(WordStates.waiting_for_pos)

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
    words = await get_words_from_db(user_id)

    # Преобразование в JSON-совместимый формат
    words_json = []
    for word in words:
        words_json.append({
            'id': word[0],
            'word': word[2],
            'part_of_speech': word[3],
            'translation': word[4]
        })
    logging.info(f"Example: {words_json[0]}")

    return web.json_response(words_json)


# Инициализация HTTP-сервера
async def init_http_server():
    app = web.Application()
    app.router.add_get('/webapp', web_app_handler)
    app.router.add_get('/api/words', api_words_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()
    logging.info(f"HTTP server started on http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/webapp")

""" 
=============== ЗАПУСК ВСЕЙ СИСТЕМЫ =============== 
Функции для запуска обоих ботов параллельно
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
    # Запускаем бота в режиме опроса сервера Telegram
    await dp.start_polling(bot)


async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # Инициализация базы данных
    await init_db()
    logging.info("Database connection established")

    # Создаем задачи для ботов
    tasks = []
    if BOT_TOKEN_MAIN:
        logging.info("Starting Main Bot...")
        tasks.append(run_bot(BOT_TOKEN_MAIN, router_main))
        logging.info("Starting HTTP server...")
        tasks.append(init_http_server())

    if BOT_TOKEN_DICT:
        logging.info("Starting Dictionary Bot...")
        tasks.append(run_bot(BOT_TOKEN_DICT, router_dict, storage))

    if not tasks:
        logging.error("❌ Bot tokens not found.")
        return

    # Запускаем всех ботов параллельно
    await asyncio.gather(*tasks)

    # Закрываем соединение с БД при завершении
    await close_db()
    logging.info("Database connection closed")


# Точка входа в программу
if __name__ == "__main__":
    # Запускаем основную асинхронную функцию
    asyncio.run(main())