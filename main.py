import asyncio
import logging
import sys
import sqlite3
import os
from typing import List, Tuple, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ... (остальные импорты из вашего кода)
from messages import *

TOKEN = KEY
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Состояния FSM
class WordStates(StatesGroup):
    waiting_for_part_of_speech = State()


class WordsViewState(StatesGroup):
    viewing_words = State()


class EditState(StatesGroup):
    waiting_edit_word = State()
    waiting_edit_pos = State()
    waiting_edit_value = State()


# ========== БАЗОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ==========

def get_user_db_path(user_id: int) -> str:
    """Возвращает путь к файлу БД пользователя"""
    return f'dbs/dictionary_{user_id}.db'


def ensure_user_db(user_id: int):
    """Создает БД пользователя, если не существует"""
    db_path = get_user_db_path(user_id)
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(CREATE_TABLE)
        conn.commit()
        conn.close()
        logging.info(f"Created new database for user {user_id}")


async def get_words_from_db(user_id: int) -> List[Tuple[str, str, str]]:
    """Получаем все слова из базы данных пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT word, part_of_speech, translation FROM words ORDER BY word")
        words = cursor.fetchall()
        return words
    except sqlite3.Error as e:
        logging.error(f"Database error for user {user_id}: {e}")
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
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error for user {user_id}: {e}")
        return False
    finally:
        conn.close()


async def update_word_in_db(user_id: int, old_word: str, new_word: str, pos: str, value: str) -> bool:
    """Обновляет слово в базе данных пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if old_word != new_word:
            cursor.execute("DELETE FROM words WHERE word = ?", (old_word,))
            # ИСПРАВЛЕНО: translation → value
            cursor.execute("""
                INSERT INTO words (word, part_of_speech, translation)
                VALUES (?, ?, ?)
            """, (new_word, pos, value))
        else:
            # ИСПРАВЛЕНО: translation → value
            cursor.execute("""
                UPDATE words 
                SET part_of_speech = ?, translation = ?
                WHERE word = ?
            """, (pos, value, new_word))

        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error for user {user_id}: {e}")
        return False
    finally:
        conn.close()


async def add_word_to_db(user_id: int, word: str, pos: str, value: str) -> bool:
    """Добавляет новое слово в БД пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(INSERT_WORD, (word, pos, value))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error for user {user_id}: {e}")
        return False
    finally:
        conn.close()


async def check_word_exists(user_id: int, word: str) -> bool:
    """Проверяет существование слова в БД пользователя"""
    ensure_user_db(user_id)
    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(SELECT_WORD, (word,))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logging.error(f"Database error for user {user_id}: {e}")
        return False
    finally:
        conn.close()


# ========== ОБРАБОТЧИКИ ДЛЯ ПРОСМОТРА СЛОВ ==========

@dp.message(Command("words"))
async def cmd_words(message: Message, state: FSMContext):
    """Обработчик команды /words - показывает слова из базы пользователя"""
    user_id = message.from_user.id

    # Получаем слова из базы данных пользователя
    words = await get_words_from_db(user_id)

    if not words:
        await message.answer("📭 Your dictionary is empty. Add some words first!")
        return

    # Определяем первую букву первого слова
    first_letter = words[0][0][0].upper() if words[0][0] and len(words[0][0]) > 0 else 'A'

    # Сохраняем слова и текущую позицию в состоянии
    await state.update_data(
        words=words,
        current_index=0,
        current_letter=first_letter
    )

    # Показываем первое слово
    await show_current_word(message, state)
    await state.set_state(WordsViewState.viewing_words)


async def show_current_word(message: Message, state: FSMContext, edit: bool = False):
    """Показывает текущее слово с клавиатурой навигации"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if not words or current_index >= len(words):
        await message.answer("❌ No words found")
        await state.clear()
        return

    # Получаем данные записи
    word, pos, value = words[current_index]

    # Формируем текст сообщения
    text = f"📖 <b>Word</b>: {word}{' ' * (70 - len(word))}{current_index + 1} of {len(words)} 🔢\n"
    text += f"🔤 <b>Part of speech:</b> {pos}\n"
    if value:
        text += f"💡 <b>Meaning:</b> {value}\n"

    # Создаем клавиатуру навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️", callback_data="prev_word"),
            InlineKeyboardButton(text="➡️", callback_data="next_word")
        ],
        [
            InlineKeyboardButton(text="⬆️ Letter", callback_data="prev_letter"),
            InlineKeyboardButton(text="Letter ⬇️", callback_data="next_letter")
        ],
        [
            InlineKeyboardButton(text="✏️ Edit", callback_data="edit_word"),
            InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_word")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_words")]
    ])

    if edit:
        # Редактируем существующее сообщение
        await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        # Отправляем новое сообщение
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "prev_word", WordsViewState.viewing_words)
async def prev_word(callback: CallbackQuery, state: FSMContext):
    """Показывает предыдущее слово"""
    data = await state.get_data()
    current_index = data.get("current_index", 0)

    if current_index > 0:
        await state.update_data(current_index=current_index - 1)
        await show_current_word(callback.message, state, edit=True)
    else:
        await callback.answer("You're at the first word")

    await callback.answer()


@dp.callback_query(F.data == "next_word", WordsViewState.viewing_words)
async def next_word(callback: CallbackQuery, state: FSMContext):
    """Показывает следующее слово"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if current_index < len(words) - 1:
        await state.update_data(current_index=current_index + 1)
        await show_current_word(callback.message, state, edit=True)
    else:
        await callback.answer("You're at the last word")

    await callback.answer()


@dp.callback_query(F.data == "prev_letter", WordsViewState.viewing_words)
async def prev_letter(callback: CallbackQuery, state: FSMContext):
    """Переходит к предыдущей букве"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)
    current_letter = data.get("current_letter", 'A')

    # Получаем уникальные буквы
    letters = sorted(set(word[0][0].upper() for word in words if word[0] and len(word[0]) > 0))

    if not letters:
        await callback.answer("No letters found")
        return

    # Находим текущую позицию буквы
    try:
        current_pos = letters.index(current_letter)
        new_pos = max(0, current_pos - 1)
        new_letter = letters[new_pos]
    except ValueError:
        new_letter = letters[0]

    # Находим первое слово на новую букву
    new_index = next((i for i, word in enumerate(words)
                      if word[0] and word[0][0].upper() == new_letter), 0)

    await state.update_data(
        current_index=new_index,
        current_letter=new_letter
    )
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@dp.callback_query(F.data == "next_letter", WordsViewState.viewing_words)
async def next_letter(callback: CallbackQuery, state: FSMContext):
    """Переходит к следующей букве"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)
    current_letter = data.get("current_letter", 'A')

    # Получаем уникальные буквы
    letters = sorted(set(word[0][0].upper() for word in words if word[0] and len(word[0]) > 0))

    if not letters:
        await callback.answer("No letters found")
        return

    # Находим текущую позицию буквы
    try:
        current_pos = letters.index(current_letter)
        new_pos = min(len(letters) - 1, current_pos + 1)
        new_letter = letters[new_pos]
    except ValueError:
        new_letter = letters[-1]

    # Находим первое слово на новую букву
    new_index = next((i for i, word in enumerate(words)
                      if word[0] and word[0][0].upper() == new_letter), 0)

    await state.update_data(
        current_index=new_index,
        current_letter=new_letter
    )
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@dp.callback_query(F.data == "cancel_words", WordsViewState.viewing_words)
async def cancel_words(callback: CallbackQuery, state: FSMContext):
    """Отменяет просмотр слов"""
    await callback.message.delete()
    await state.clear()
    await callback.answer()


# ========== ОБРАБОТЧИКИ ДЛЯ УДАЛЕНИЯ И РЕДАКТИРОВАНИЯ ==========

@dp.callback_query(F.data == "delete_word", WordsViewState.viewing_words)
async def delete_word_handler(callback: CallbackQuery, state: FSMContext):
    """Удаляет текущее слово"""
    user_id = callback.from_user.id
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if not words or current_index >= len(words):
        await callback.answer("No word to delete")
        return

    word, _, _ = words[current_index]

    # Удаляем слово из базы данных пользователя
    if await delete_word_from_db(user_id, word):
        # Обновляем список слов
        words = await get_words_from_db(user_id)

        if not words:
            await callback.message.edit_text("✅ Word deleted\n")
            await state.clear()
            return

        # Определяем новый текущий индекс
        new_index = current_index if current_index < len(words) else len(words) - 1
        new_letter = words[new_index][0][0].upper() if words[new_index][0] else 'A'

        await state.update_data(
            words=words,
            current_index=new_index,
            current_letter=new_letter
        )

        # Показываем новое текущее слово
        await show_current_word(callback.message, state, edit=True)
        await callback.answer(f"✅ {word} deleted")
    else:
        await callback.answer(f"❌ Failed to delete {word}")


@dp.callback_query(F.data == "edit_word", WordsViewState.viewing_words)
async def start_edit_word(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс редактирования слова"""
    data = await state.get_data()
    words = data.get("words", [])
    current_index = data.get("current_index", 0)

    if not words or current_index >= len(words):
        await callback.answer("No word to edit")
        return

    word, pos, value = words[current_index]

    # Сохраняем данные для редактирования
    await state.update_data(
        editing_word=word,
        editing_pos=pos,
        editing_value=value,
        editing_index=current_index,
        original_word=word,  # Добавляем
        original_pos=pos,  # оригинальные
        original_value=value  # значения
    )

    # Создаем клавиатуру для выбора, что редактировать
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


@dp.callback_query(F.data.startswith("edit_word_"), EditState.waiting_edit_word)
async def handle_edit_choice(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор редактируемого поля"""
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


@dp.callback_query(F.data == "cancel_edit", EditState.waiting_edit_word)
@dp.callback_query(F.data == "cancel_edit", EditState.waiting_edit_value)
@dp.callback_query(F.data == "cancel_edit", EditState.waiting_edit_pos)
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    """Отменяет редактирование"""
    await state.set_state(WordsViewState.viewing_words)
    await show_current_word(callback.message, state, edit=True)
    await callback.answer()


@dp.message(EditState.waiting_edit_word)
async def handle_edit_word_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_word = message.text.strip()
    data = await state.get_data()
    old_word = data.get("editing_word", "")
    original_word = data.get("original_word", "")  # Получаем оригинальное слово

    # Если новое слово совпадает с оригинальным - пропускаем проверку
    if new_word != original_word:
        # Проверяем, не существует ли уже нового слова в БД пользователя
        words = await get_words_from_db(user_id)
        if any(w[0].lower() == new_word.lower() for w in words):
            await message.answer("⚠️ This word already exists in the dictionary")
            return

    # Обновляем данные
    await state.update_data(editing_word=new_word)
    await save_edited_word(message, state, user_id)


@dp.message(EditState.waiting_edit_value)
async def handle_edit_word_value(message: Message, state: FSMContext):
    """Обрабатывает новое значение"""
    new_value = message.text.strip()
    await state.update_data(editing_value=new_value)
    await save_edited_word(message, state, message.from_user.id)


@dp.callback_query(F.data.startswith("newpos_"), EditState.waiting_edit_pos)
async def handle_edit_word_pos(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает новую часть речи"""
    new_pos = callback.data.replace("newpos_", "")
    await state.update_data(editing_pos=new_pos)
    await save_edited_word(callback.message, state, callback.from_user.id)
    await callback.answer()


async def save_edited_word(message: Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    # Получаем текущие значения
    new_word = data.get("editing_word", "")
    new_pos = data.get("editing_pos", "")
    new_value = data.get("editing_value", "")

    # Получаем оригинальные значения
    original_word = data.get("original_word", "")
    original_pos = data.get("original_pos", "")
    original_value = data.get("original_value", "")

    editing_index = data.get("editing_index", 0)

    # Проверяем, были ли какие-либо изменения
    if (new_word == original_word and
            new_pos == original_pos and
            new_value == original_value):
        await message.answer("ℹ️ No changes detected")
        await state.set_state(WordsViewState.viewing_words)
        await show_current_word(message, state, edit=True)
        return

    # Обновляем слово в базе данных пользователя
    success = await update_word_in_db(user_id, original_word, new_word, new_pos, new_value)
    if success:
        # Обновляем список слов
        words = await get_words_from_db(user_id)

        # Находим новую позицию отредактированного слова
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


# ========== ОСНОВНОЙ КОД ДОБАВЛЕНИЯ СЛОВ ==========

@dp.message(CommandStart())
async def start(message: Message):
    """Обработка команды /start"""
    await message.answer(f"👋 Hello, {message.from_user.first_name}! {GREETING}", parse_mode=ParseMode.HTML)


async def process_word_input(message: Message, state: FSMContext):
    """Обработка ввода слова - основная логика"""
    user_id = message.from_user.id

    # Обработка ввода слова и значения
    if ':' in message.text:
        parts = message.text.split(':', 1)
        word = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    else:
        word = message.text.strip()
        value = None

    # Проверяем существование слова в БД пользователя
    if await check_word_exists(user_id, word):
        await message.answer("⚠️ Word already exists")
        await state.clear()
        return

    # Сохраняем данные в состоянии
    await state.update_data(word=word, value=value)

    # Inline-клавиатура с частями речи
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Noun", callback_data="pos_noun"),
         InlineKeyboardButton(text="Verb", callback_data="pos_verb")],
        [InlineKeyboardButton(text="Adjective", callback_data="pos_adjective"),
         InlineKeyboardButton(text="Adverb", callback_data="pos_adverb")]
    ])

    # Отправляем сообщение и устанавливаем состояние
    await message.answer("❓ What part of speech is it?", reply_markup=keyboard)
    await state.set_state(WordStates.waiting_for_part_of_speech)


@dp.message(WordStates.waiting_for_part_of_speech)
async def handle_part_of_speech_text(message: Message):
    """Обработка текстовых сообщений в состоянии ожидания части речи"""
    await message.answer("⚠️ Please select a part of speech from the buttons above")


@dp.callback_query(F.data.startswith("pos_"), WordStates.waiting_for_part_of_speech)
async def process_part_of_speech_callback(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    part_of_speech = callback.data.replace("pos_", "")
    data = await state.get_data()
    word = data.get("word")
    value = data.get("value")

    # Сохраняем в БД пользователя
    if await add_word_to_db(user_id, word, part_of_speech, value):
        # Формируем ответное сообщение
        response = f"✅ Saved: {word} ({part_of_speech})"
        if value:
            response += f"\nMeaning: {value[:50] + '...' if len(value) > 50 else value}"

        await callback.message.edit_text(response)
        await callback.answer()
        await state.clear()
    else:
        await callback.message.edit_text("❌ Failed to save word")
        await callback.answer()


@dp.message()
async def handle_all_messages(message: Message, state: FSMContext):
    """Основной обработчик для всех сообщений"""
    # Пропускаем команды
    if message.text.startswith('/'):
        return

    current_state = await state.get_state()

    # Если в состоянии ожидания части речи
    if current_state == WordStates.waiting_for_part_of_speech.state:
        await handle_part_of_speech_text(message)
        return

    # Если в состоянии редактирования
    if current_state in [
        EditState.waiting_edit_word.state,
        EditState.waiting_edit_pos.state,
        EditState.waiting_edit_value.state
    ]:
        return

    # Обрабатываем как новое слово
    await process_word_input(message, state)


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())