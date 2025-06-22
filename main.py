import asyncio
import logging
import sys
import sqlite3
import os
from typing import List, Tuple, Optional
from dotenv import load_dotenv

# Основные компоненты aiogram
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Импорт конфигурационных данных
from messages import *

# Загрузка переменных окружения
load_dotenv()

""" =============== BOT 1: Main Bot =============== """
BOT_TOKEN_MAIN = os.getenv("BOT_TOKEN_MAIN")
router_main = Router()


@router_main.message(Command("start"))
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Бот-словарь", url="https://t.me/lllangbot"),
            # InlineKeyboardButton(text="🛠 Техподдержка")
        ],
        [
            # InlineKeyboardButton(text="💬 Практика общения"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ]
    ])
    await message.answer(WELCOME, reply_markup=keyboard)


@router_main.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(ABOUT)
    await callback.answer()


@router_main.message()
async def handle_other_messages(message: Message):
    await message.answer("Используйте /start для получения меню")


""" =============== BOT 2: Dictionary Bot =============== """
BOT_TOKEN_DICT = os.getenv("BOT_TOKEN_DICT")
router_dict = Router()
storage = MemoryStorage()


# Состояния для словарного бота
class WordStates(StatesGroup):
    waiting_for_pos = State()
    waiting_for_custom_pos = State()


class WordsViewState(StatesGroup):
    viewing_words = State()


class EditState(StatesGroup):
    waiting_edit_word = State()
    waiting_edit_pos = State()
    waiting_edit_value = State()


def get_user_db_path(user_id: int) -> str:
    """Генерирует путь к персональной базе данных пользователя"""
    return f'dbs/dictionary_{user_id}.db'


def ensure_user_db(user_id: int):
    """Создает базу данных и таблицу при первом обращении"""
    db_path = get_user_db_path(user_id)
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(CREATE_TABLE)  # SQL-запрос из messages.py
        conn.commit()
        conn.close()
        logging.info(f"Created new database for user {user_id}")


async def get_words_from_db(user_id: int) -> List[Tuple[str, str, str]]:
    """Получает все слова пользователя из базы (асинхронная обертка)"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT word, part_of_speech, translation FROM words ORDER BY word")
        return cursor.fetchall()  # Возвращает список кортежей (слово, часть_речи, перевод)
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return []
    finally:
        conn.close()


async def delete_word_from_db(user_id: int, word: str) -> bool:
    """Удаляет слово из базы данных пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM words WHERE word = ?", (word,))
        conn.commit()
        return cursor.rowcount > 0  # True если удаление прошло успешно
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        conn.close()


async def update_word_in_db(user_id: int, old_word: str, new_word: str, pos: str, value: str) -> bool:
    """Обновляет слово в базе данных (с проверкой изменения слова)"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        if old_word != new_word:
            # Если слово изменилось - удаляем старую и создаем новую запись
            cursor.execute("DELETE FROM words WHERE word = ?", (old_word,))
            cursor.execute("""
                INSERT INTO words (word, part_of_speech, translation)
                VALUES (?, ?, ?)
            """, (new_word, pos, value))
        else:
            # Если слово не менялось - обновляем остальные поля
            cursor.execute("""
                UPDATE words 
                SET part_of_speech = ?, translation = ?
                WHERE word = ?
            """, (pos, value, new_word))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        conn.close()


async def add_word_to_db(user_id: int, word: str, pos: str, value: str) -> bool:
    """Добавляет новое слово в базу данных пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(INSERT_WORD, (word, pos, value))  # INSERT_WORD из messages.py
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        conn.close()


async def check_word_exists(user_id: int, word: str) -> bool:
    """Проверяет существует ли слово в базе пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(SELECT_WORD, (word,))  # SELECT_WORD из messages.py
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        conn.close()


"""
Обработчики команд и сообщений:
Сердце бота - функции, реагирующие на действия пользователя.

Принцип работы:
1. Telegram сервер отправляет событие (сообщение, нажатие кнопки)
2. Диспетчер (dp) находит подходящий обработчик
3. Выполняется асинхронная функция (корутина)
4. Бот отправляет ответ

Ключевые элементы декораторов:
- @dp.message(Command("words")): реагирует на команду /words
- @dp.callback_query(F.data == ...): обрабатывает нажатие кнопки
"""


@router_dict.message(Command("list"))
async def show_dictionary(message: Message, state: FSMContext):
    """Обработка команды /words - показывает словарь пользователя"""
    user_id = message.from_user.id
    words = await get_words_from_db(user_id)

    if not words:
        await message.answer("📭 Your dictionary is empty. Add some words first!")
        return

    # Сохраняем слова в контексте состояния
    await state.update_data(
        words=words,
        current_index=0,
        current_letter=words[0][0][0].upper() if words[0][0] else 'A'
    )

    # Показываем первое слово
    await show_current_word(message, state)
    await state.set_state(WordsViewState.viewing_words)


async def show_current_word(message: Message, state: FSMContext, edit: bool = False, full_info: bool = False):
    """
    Отображает текущее слово с навигацией

    Параметры:
    - full_info: True - показать полную информацию без сокращений
    """
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if not words or current_index >= len(words):
        await message.answer("❌ No words found")
        await state.clear()
        return

    word, pos, value = words[current_index]

    # Форматируем сообщение с HTML-разметкой
    if full_info:
        # Полная информация без сокращений
        text = (
            f"📖 <b>Full information for:</b> {word}\n"
            f"🔢 <b>Position:</b> {current_index + 1} of {len(words)}\n"
            f"🔤 <b>Part of speech:</b> {pos}\n"
        )
        if value:
            text += f"💡 <b>Full meaning:</b>\n{value}\n"

        # Клавиатура только с кнопкой возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
        ])
    else:
        # Стандартный вид с сокращениями
        text = (
            f"📖 <b>Word</b>: {word}{' ' * (70 - len(word))}{current_index + 1} out of {len(words)} 🔢\n"
            f"🔤 <b>Part of speech:</b> {pos}\n"
        )
        if value:
            text += f"💡 <b>Meaning:</b> {value[:50] + '...' if len(value) > 50 else value}\n"

        # Стандартная клавиатура с действиями
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ Info", callback_data="show_info")],
            [InlineKeyboardButton(text="⬅️", callback_data="prev_word"),
             InlineKeyboardButton(text="➡️", callback_data="next_word")],
            [InlineKeyboardButton(text="⬆️ Letter", callback_data="prev_letter"),
             InlineKeyboardButton(text="Letter ⬇️", callback_data="next_letter")],
            [InlineKeyboardButton(text="✏️ Edit", callback_data="edit_word"),
             InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_word")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_words")]
        ])

    # Отправляем или редактируем сообщение
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


"""
Обработка нажатий кнопок:
Когда пользователь нажимает inline-кнопку, Telegram отправляет CallbackQuery

Принцип работы:
1. Кнопка создается с callback_data="действие"
2. Обработчик регистрируется через @dp.callback_query(F.data == "действие")
3. В обработчике:
   - Обновляем состояние
   - Меняем интерфейс
   - Отвечаем на callback (callback.answer())
"""


@router_dict.callback_query(F.data == "prev_word", WordsViewState.viewing_words)
async def prev_word_handler(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Предыдущее слово'"""
    data = await state.get_data()
    current_index = data.get("current_index", 0)

    if current_index > 0:
        await state.update_data(current_index=current_index - 1)
        await show_current_word(callback.message, state, edit=True)
    else:
        await callback.answer("You're at the first word")

    await callback.answer()  # Обязательно подтверждаем обработку


@router_dict.callback_query(F.data == "next_word", WordsViewState.viewing_words)
async def next_word_handler(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Следующее слово'"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if current_index < len(words) - 1:
        await state.update_data(current_index=current_index + 1)
        await show_current_word(callback.message, state, edit=True)
    else:
        await callback.answer("You're at the last word")

    await callback.answer()


@router_dict.callback_query(F.data == "prev_letter", WordsViewState.viewing_words)
async def prev_letter_handler(callback: CallbackQuery, state: FSMContext):
    """Переход к первой букве в предыдущей группе слов"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)
    current_letter = data.get("current_letter", 'A')

    # Получаем уникальные буквы из слов
    letters = sorted(set(word[0][0].upper() for word in words if word[0] and len(word[0]) > 0))

    if not letters:
        await callback.answer("No letters found")
        return

    # Находим текущую позицию буквы в алфавите
    try:
        current_pos = letters.index(current_letter)
        new_pos = max(0, current_pos - 1)
        new_letter = letters[new_pos]
    except ValueError:
        new_letter = letters[0]

    # Ищем первое слово на новую букву
    new_index = next((i for i, word in enumerate(words)
                      if word[0] and word[0][0].upper() == new_letter), 0)

    await state.update_data(
        current_index=new_index,
        current_letter=new_letter
    )
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.callback_query(F.data == "next_letter", WordsViewState.viewing_words)
async def next_letter_handler(callback: CallbackQuery, state: FSMContext):
    """Переход к первой букве в следующей группе слов"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)
    current_letter = data.get("current_letter", 'A')

    # Получаем уникальные буквы из слов
    letters = sorted(set(word[0][0].upper() for word in words if word[0] and len(word[0]) > 0))

    if not letters:
        await callback.answer("No letters found")
        return

    # Находим текущую позицию буквы в алфавите
    try:
        current_pos = letters.index(current_letter)
        new_pos = min(len(letters) - 1, current_pos + 1)
        new_letter = letters[new_pos]
    except ValueError:
        new_letter = letters[-1]

    # Ищем первое слово на новую букву
    new_index = next((i for i, word in enumerate(words)
                      if word[0] and word[0][0].upper() == new_letter), 0)

    await state.update_data(
        current_index=new_index,
        current_letter=new_letter
    )
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.callback_query(F.data == "cancel_words", WordsViewState.viewing_words)
async def cancel_words_handler(callback: CallbackQuery, state: FSMContext):
    """Выход из режима просмотра слов"""
    await callback.message.delete()  # Удаляем сообщение с навигацией
    await state.clear()  # Сбрасываем состояние
    await callback.answer()


@router_dict.callback_query(F.data == "delete_word", WordsViewState.viewing_words)
async def delete_word_handler(callback: CallbackQuery, state: FSMContext):
    """Удаление текущего слова из базы данных"""
    user_id = callback.from_user.id
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if not words or current_index >= len(words):
        await callback.answer("No word to delete")
        return

    word, _, _ = words[current_index]

    # Удаляем слово из базы
    if await delete_word_from_db(user_id, word):
        # Обновляем список слов
        words = await get_words_from_db(user_id)

        if not words:
            # Если словарь пуст - выходим из режима просмотра
            await callback.message.edit_text("✅ Word deleted\n")
            await state.clear()
            return

        # Корректируем текущий индекс
        new_index = current_index if current_index < len(words) else len(words) - 1
        new_letter = words[new_index][0][0].upper() if words[new_index][0] else 'A'

        await state.update_data(
            words=words,
            current_index=new_index,
            current_letter=new_letter
        )

        # Обновляем интерфейс
        await show_current_word(callback.message, state, edit=True)
        await callback.answer(f"✅ {word} deleted")
    else:
        await callback.answer(f"❌ Failed to delete {word}")


@router_dict.callback_query(F.data == "edit_word", WordsViewState.viewing_words)
async def start_edit_word(callback: CallbackQuery, state: FSMContext):
    """Начало процесса редактирования слова"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if not words or current_index >= len(words):
        await callback.answer("No word to edit")
        return

    word, pos, value = words[current_index]

    # Сохраняем текущие значения для возможного сравнения
    await state.update_data(
        editing_word=word,
        editing_pos=pos,
        editing_value=value,
        editing_index=current_index,
        original_word=word,
        original_pos=pos,
        original_value=value
    )

    # Клавиатура выбора редактируемого поля
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Word", callback_data="edit_word_text"),
            InlineKeyboardButton(text="💡 Meaning", callback_data="edit_word_value")
        ],
        [
            InlineKeyboardButton(text="🔤 Part of Speech", callback_data="edit_word_pos")
        ],
        [InlineKeyboardButton(text="↩️ Back", callback_data="cancel_edit")]
    ])

    await callback.message.edit_text(
        f"✏️ <b>Editing:</b> {word}\n"
        f"🔤 <b>Current POS:</b> {pos}\n"
        f"💡 <b>Current Meaning:</b> {value or 'None'}\n\n"
        "Select what to edit:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await state.set_state(EditState.waiting_edit_word)


@router_dict.callback_query(F.data.startswith("edit_word_"), EditState.waiting_edit_word)
async def handle_edit_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    edit_type = callback.data.replace("edit_word_", "")
    data = await state.get_data()
    word = data.get("editing_word", "")

    if edit_type == "text":
        await callback.message.edit_text(f"✏️ Enter new text for <b>{word}</b>:", parse_mode=ParseMode.HTML)
        await state.set_state(EditState.waiting_edit_word)
    elif edit_type == "value":
        await callback.message.edit_text(f"💡 Enter new meaning for <b>{word}</b>:", parse_mode=ParseMode.HTML)
        await state.set_state(EditState.waiting_edit_value)
    elif edit_type == "pos":
        # Клавиатура с выбором части речи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Noun", callback_data="newpos_noun"),
             InlineKeyboardButton(text="Verb", callback_data="newpos_verb")],
            [InlineKeyboardButton(text="Adjective", callback_data="newpos_adjective"),
             InlineKeyboardButton(text="Adverb", callback_data="newpos_adverb")],
            [InlineKeyboardButton(text="↩️ Back", callback_data="cancel_edit")]
        ])
        await callback.message.edit_text(f"🔤 Select new part of speech for <b>{word}</b>:",
                                         reply_markup=keyboard,
                                         parse_mode=ParseMode.HTML)
        await state.set_state(EditState.waiting_edit_pos)

    await callback.answer()


@router_dict.callback_query(F.data == "cancel_edit", EditState.waiting_edit_word)
@router_dict.callback_query(F.data == "cancel_edit", EditState.waiting_edit_value)
@router_dict.callback_query(F.data == "cancel_edit", EditState.waiting_edit_pos)
async def cancel_edit_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования и возврат к просмотру"""
    await state.set_state(WordsViewState.viewing_words)
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.callback_query(F.data == "show_info", WordsViewState.viewing_words)
async def show_full_info_handler(callback: CallbackQuery, state: FSMContext):
    """Показывает полную информацию о слове"""
    # Редактируем текущее сообщение для показа полной информации
    await show_current_word(callback.message, state, edit=True, full_info=True)
    await callback.answer()


@router_dict.callback_query(F.data == "go_back", WordsViewState.viewing_words)
async def go_back_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к стандартному виду информации"""
    # Возвращаем стандартный вид
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@router_dict.message(EditState.waiting_edit_word)
async def handle_edit_word_text(message: Message, state: FSMContext):
    """Обработка нового текста слова"""
    user_id = message.from_user.id
    new_word = message.text.strip()
    data = await state.get_data()
    old_word = data.get("editing_word", "")
    original_word = data.get("original_word", "")

    # Проверка на дубликаты (если слово изменилось)
    if new_word != original_word:
        words = await get_words_from_db(user_id)
        if any(w[0].lower() == new_word.lower() for w in words):
            await message.answer("⚠️ This word already exists in the dictionary")
            return

    # Обновляем данные и сохраняем
    await state.update_data(editing_word=new_word)
    await save_edited_word(message, state, user_id)


@router_dict.message(EditState.waiting_edit_value)
async def handle_edit_word_value(message: Message, state: FSMContext):
    """Обработка нового значения слова"""
    new_value = message.text.strip()
    await state.update_data(editing_value=new_value)
    await save_edited_word(message, state, message.from_user.id)


@router_dict.callback_query(F.data.startswith("newpos_"), EditState.waiting_edit_pos)
async def handle_edit_word_pos(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора новой части речи"""
    new_pos = callback.data.replace("newpos_", "")
    await state.update_data(editing_pos=new_pos)
    await save_edited_word(callback.message, state, callback.from_user.id)
    await callback.answer()


# Обработка кнопки Cancel
@router_dict.callback_query(F.data == "pos_cancel", WordStates.waiting_for_pos)
async def cancel_adding_word(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления слова"""
    await state.clear()
    await callback.message.edit_text("❌ Adding word canceled.")
    await callback.answer()


# Обработка кнопки Other
@router_dict.callback_query(F.data == "pos_other", WordStates.waiting_for_pos)
async def ask_custom_part_of_speech(callback: CallbackQuery, state: FSMContext):
    """Запрос на ручной ввод части речи"""
    await callback.message.edit_text("✍️ Please enter the part of speech manually:")
    await state.set_state(WordStates.waiting_for_custom_pos)
    await callback.answer()


# Обработка ручного ввода части речи
@router_dict.message(WordStates.waiting_for_custom_pos)
async def handle_custom_part_of_speech(message: Message, state: FSMContext):
    """Обработка ручного ввода части речи"""
    custom_pos = message.text.strip()
    if not custom_pos:
        await message.answer("Please enter a valid part of speech.")
        return

    # Сохраняем слово
    user_id = message.from_user.id
    data = await state.get_data()
    word = data["word"]
    value = data.get("value")

    if await add_word_to_db(user_id, word, custom_pos, value):
        response = f"✅ Saved: {word} ({custom_pos})"
        if value:
            response += f"\nMeaning: {value[:50] + '...' if len(value) > 50 else value}"
        await message.answer(response)
    else:
        await message.answer("❌ Failed to save word")

    await state.clear()


async def save_edited_word(message: Message, state: FSMContext, user_id: int):
    """Сохранение изменений слова в базе данных"""
    data = await state.get_data()
    # Текущие значения из состояния
    new_word = data.get("editing_word", "")
    new_pos = data.get("editing_pos", "")
    new_value = data.get("editing_value", "")

    # Оригинальные значения (для сравнения)
    original_word = data.get("original_word", "")
    original_pos = data.get("original_pos", "")
    original_value = data.get("original_value", "")

    editing_index = data.get("editing_index", 0)

    # Проверка на наличие изменений
    if (new_word == original_word and
            new_pos == original_pos and
            new_value == original_value):
        await message.answer("ℹ️ No changes detected")
        await state.set_state(WordsViewState.viewing_words)
        await show_current_word(message, state, edit=True)
        return

    # Обновляем слово в базе
    success = await update_word_in_db(user_id, original_word, new_word, new_pos, new_value)
    if success:
        # Обновляем список слов
        words = await get_words_from_db(user_id)

        # Находим новую позицию слова
        new_index = next((i for i, w in enumerate(words) if w[0] == new_word), editing_index)

        await state.update_data(
            words=words,
            current_index=new_index
        )

        # Возвращаемся к просмотру
        await state.set_state(WordsViewState.viewing_words)
        await show_current_word(message, state, edit=True)
    else:
        await message.answer("❌ Failed to update word")
        await state.set_state(WordsViewState.viewing_words)
        await show_current_word(message, state, edit=True)

    """
    Процесс добавления новых слов:
    1. Пользователь отправляет слово (или слово:значение)
    2. Бот переводит в состояние ожидания части речи
    3. Пользователь выбирает часть речи
    4. Бот сохраняет слово в БД

    FSMContext - контекст состояния, хранящий данные между шагами
    """


@router_dict.message(CommandStart())
async def start_command_handler(message: Message):
    """Обработка команды /start - приветствие"""
    await message.answer(f"👋 Hello, {message.from_user.first_name}! {GREETING}", parse_mode=ParseMode.HTML)


@router_dict.message(WordStates.waiting_for_pos)
async def handle_part_of_speech_text(message: Message):
    """Напоминание использовать кнопки при вводе текста вместо выбора части речи"""
    await message.answer("⚠️ Please select a part of speech from the buttons above")


@router_dict.callback_query(F.data.startswith("pos_"), WordStates.waiting_for_pos)
async def save_new_word_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохранение нового слова после выбора части речи"""
    user_id = callback.from_user.id
    part_of_speech = callback.data.replace("pos_", "")
    data = await state.get_data()
    word = data.get("word")
    value = data.get("value")

    # Сохраняем в БД
    if await add_word_to_db(user_id, word, part_of_speech, value):
        # Формируем сообщение об успехе
        response = f"✅ Saved: {word} ({part_of_speech})"
        if value:
            response += f"\nMeaning: {value[:50] + '...' if len(value) > 50 else value}"

        await callback.message.edit_text(response)
        await callback.answer()
        await state.clear()  # Выходим из состояния
    else:
        await callback.message.edit_text("❌ Failed to save word")
        await callback.answer()


@router_dict.message()
async def universal_message_handler(message: Message, state: FSMContext):
    """
    Универсальный обработчик текстовых сообщений

    Логика работы:
    1. Пропускаем команды (они обрабатываются отдельно)
    2. Проверяем текущее состояние пользователя
    3. В зависимости от состояния:
       - Если в процессе добавления слова: просим использовать кнопки
       - Если в режиме редактирования: пропускаем
       - Иначе: начинаем процесс добавления нового слова
    """
    # Игнорируем команды
    if message.text.startswith('/'):
        return

    # Получаем текущее состояние пользователя
    current_state = await state.get_state()

    # Если пользователь должен выбрать часть речи
    if current_state == WordStates.waiting_for_pos.state:
        await handle_part_of_speech_text(message)
        return

    # Если в режиме редактирования - пропускаем
    if current_state in [
        EditState.waiting_edit_word.state,
        EditState.waiting_edit_pos.state,
        EditState.waiting_edit_value.state
    ]:
        return

    # Начинаем процесс добавления нового слова
    await process_word_input(message, state)


async def process_word_input(message: Message, state: FSMContext):
    """Обработка ввода нового слова"""
    user_id = message.from_user.id
    text = message.text.strip()

    if ':' in text:
        parts = text.split(':', 1)
        word = parts[0].strip()
        value = parts[1].strip() if parts[1].strip() else None
    else:
        word, value = text, None

    if await check_word_exists(user_id, word):
        await message.answer("⚠️ Word already exists")
        await state.clear()
        return

    await state.update_data(word=word, value=value)

    # Добавляем кнопки Other и Cancel
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Noun", callback_data="pos_noun"),
         InlineKeyboardButton(text="Verb", callback_data="pos_verb")],
        [InlineKeyboardButton(text="Adjective", callback_data="pos_adjective"),
         InlineKeyboardButton(text="Adverb", callback_data="pos_adverb")],
        [
            InlineKeyboardButton(text="Other", callback_data="pos_other"),
            InlineKeyboardButton(text="Cancel", callback_data="pos_cancel")
        ]
    ])

    await message.answer("❓ What part of speech is it?", reply_markup=keyboard)
    await state.set_state(WordStates.waiting_for_pos)


""" =============== Запуск всех ботов =============== """

async def run_bot(bot_token: str, router: Router, storage=None):
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage) if storage else Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    if not os.path.exists("dbs"):
        os.makedirs("dbs")

    tasks = []
    if BOT_TOKEN_MAIN:
        tasks.append(run_bot(BOT_TOKEN_MAIN, router_main))

    if BOT_TOKEN_DICT:
        tasks.append(run_bot(BOT_TOKEN_DICT, router_dict, storage))

    if not tasks:
        logging.error("❌ Bot tokens not found.")
        return

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())