import asyncio
import logging
import sys
from os import getenv
from typing import Any, Dict
import sqlite3

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from messages import *

TOKEN = KEY
dp = Dispatcher()

# Состояния FSM
class WordStates(StatesGroup):
    waiting_for_word = State()  # Ожидание слова
    waiting_for_part_of_speech = State()  # Ожидание части речи
    waiting_for_translation = State()  # Ожидание перевода


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await message.answer(f"🌟 Welcome! {GREETING}")


# Новый обработчик для начала добавления слова
@dp.message(Command("addword"))
async def start_add_word(message: Message, state: FSMContext) -> None:
    msg = await message.answer("📝 Enter a new word to learn:")
    await state.set_state(WordStates.waiting_for_word)
    await state.update_data(prev_msg_id=msg.message_id)


# Обработчик для ввода слова
@dp.message(WordStates.waiting_for_word)
async def add_word(message: Message, state: FSMContext) -> None:
    word = message.text.strip()

    # Проверяем существование слова в БД
    conn = sqlite3.connect('dictionary.db')
    cursor = conn.cursor()
    if cursor.execute(SELECT_WORD, (word,)).fetchone():
        await message.answer("⚠️ Word already exists")
        conn.close()
        await state.clear()
        return

    conn.close()

    await state.update_data(word=word)

    # Inline-клавиатура с частями речи
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Noun", callback_data="pos_noun"),
         InlineKeyboardButton(text="Verb", callback_data="pos_verb")],
        [InlineKeyboardButton(text="Adjective", callback_data="pos_adjective"),
         InlineKeyboardButton(text="Adverb", callback_data="pos_adverb")]
    ])

    await message.answer("❓ What part of speech is it?", reply_markup=keyboard)
    await state.set_state(WordStates.waiting_for_part_of_speech)


# Обработчик для выбора части речи через inline-кнопку
@dp.callback_query(F.data.startswith("pos_"), WordStates.waiting_for_part_of_speech)
async def process_part_of_speech_callback(callback: CallbackQuery, state: FSMContext) -> None:
    part_of_speech = callback.data.replace("pos_", "")
    data = await state.get_data()
    word = data.get("word")

    # Сохраняем в БД
    conn = sqlite3.connect('dictionary.db')
    cursor = conn.cursor()
    cursor.execute(INSERT_WORD, (word, part_of_speech, None))
    conn.commit()
    conn.close()

    logging.info(f"Saved: {word} ({part_of_speech})")

    await callback.message.edit_text(f"✅ Saved: {word} ({part_of_speech})")
    await callback.answer()  # Чтобы убрать "часики"
    await state.clear()


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
