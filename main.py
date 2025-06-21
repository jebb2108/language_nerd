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
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
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
    await message.answer("📝 Enter a new word to learn:")
    await state.set_state(WordStates.waiting_for_word)


# Обработчик для ввода слова (теперь корректно работает)
@dp.message(WordStates.waiting_for_word)
async def add_word(message: Message, state: FSMContext) -> None:
    # Сохраняем слово в состоянии
    await state.update_data(word=message.text)

    # Проверяем существование слова в БД
    conn = sqlite3.connect('dictionary.db')
    cursor = conn.cursor()
    if cursor.execute(SELECT_WORD, (message.text,)).fetchone():
        await message.answer("Word already exists")
        conn.close()
        await state.clear()
        return

    conn.close()

    # Переходим к выбору части речи
    await message.answer(
        "What part of speech is it?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Noun"), KeyboardButton(text="Verb")],
                [KeyboardButton(text="Adjective"), KeyboardButton(text="Adverb")]
            ],
            resize_keyboard=True,
        ),
    )
    await state.set_state(WordStates.waiting_for_part_of_speech)


@dp.message(WordStates.waiting_for_part_of_speech)
async def process_part_of_speech(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    word = data["word"]
    part_of_speech = message.text.lower()

    # Сохраняем в БД
    conn = sqlite3.connect('dictionary.db')
    cursor = conn.cursor()
    cursor.execute(INSERT_WORD, (word, part_of_speech, None))
    conn.commit()
    conn.close()

    print(word, part_of_speech)

    await message.answer(
        f"✅ Saved: {word} ({part_of_speech})",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())