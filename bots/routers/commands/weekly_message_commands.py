import asyncio
from typing import Union

from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text, Bold
from aiogram.utils.markdown import html_decoration as hd

from bots.config import logger
from bots.middlewares.resources_middleware import ResourcesMiddleware

# Инициализация роутера
router = Router(name=__name__)



async def send_user_report(
        bot: Bot,
        user_id: int,
        report_id: int,
        resources: ResourcesMiddleware,
) -> bool:
    """
    Отправляет пользователю его еженедельный отчет.
    """
    try:
        async with resources.db_pool.acquire() as conn:
            report = await conn.fetchrow(
                "SELECT * FROM weekly_reports WHERE report_id = $1",
                report_id
            )
            words = await conn.fetch(
                "SELECT * FROM report_words WHERE report_id = $1",
                report_id
            )

        if not report or not words:
            logger.warning(f"No report data found for report_id: {report_id}")
            return False

        message_text = (
            f"📊 Ваш еженедельный отчет по изученным словам:\n\n"
            f"Всего слов: {len(words)}\n\n"
            "Для начала проверки нажмите кнопку ниже 👇"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Начать проверку знаний",
                callback_data=f"start_report:{report_id}"
            )]
        ])

        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=keyboard
        )
        return True

    except Exception as e:
        logger.error(f"Error sending interactive report to {user_id}: {e}")
        return False


@router.callback_query(lambda c: c.data.startswith("start_report:"))
async def start_report_handler(
        callback: types.CallbackQuery,
        state: FSMContext,
        resources: ResourcesMiddleware,
):
    """
    Начинает интерактивный отчет-опрос по weekly_reports.
    """
    report_id = int(callback.data.split(":", 1)[1])

    async with resources.db_pool.acquire() as conn:
        words = await conn.fetch(
            "SELECT word_id FROM report_words WHERE report_id = $1",
            report_id
        )

    if not words:
        await callback.answer("Отчет не содержит слов для проверки.", show_alert=True)
        return

    # Инициализируем state
    await state.clear()
    await state.update_data(
        report_id=report_id,
        word_ids=[row["word_id"] for row in words],
        current_index=0,
        chat_id=callback.message.chat.id,
        db_pool=resources.db_pool,
    )

    await send_question(state, callback.bot)
    await callback.answer()


async def send_question(
        state: FSMContext,
        bot: Bot,
):
    """
    Отправляет пользователю текущий вопрос из отчета.
    """
    data = await state.get_data()
    idx = data.get("current_index")
    word_ids = data.get("word_ids")
    chat_id = data.get("chat_id")
    db_pool = data.get("db_pool")

    if idx >= len(word_ids):
        await bot.send_message(
            chat_id=chat_id,
            text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам."
        )
        await state.clear()
        return

    word_id = word_ids[idx]
    async with db_pool.acquire() as conn:
        word_data = await conn.fetchrow(
            "SELECT * FROM report_words WHERE word_id = $1",
            word_id
        )

    if not word_data:
        await bot.send_message(
            chat_id=chat_id,
            text="Ошибка: данные вопроса не найдены."
        )
        return

    question_text = (
        f"❓ Вопрос {idx + 1}/{len(word_ids)}\n\n"
        f"{word_data['sentence']}\n\n"
        "Выберите правильный вариант:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for opt_idx, option in enumerate(word_data["options"]):
        cb = f"quiz:{word_id}:{opt_idx}"
        row.append(InlineKeyboardButton(text=option, callback_data=cb))
        if len(row) >= 2:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)

    await bot.send_message(
        chat_id=chat_id,
        text=question_text,
        reply_markup=keyboard
    )


@router.callback_query(lambda callback: callback.data.startswith("quiz:"))
async def handle_word_quiz(
        callback: types.CallbackQuery,
        state: FSMContext,
):
    data = await state.get_data()
    db_pool = data.get("db_pool")
    """
    Обработка ответа на вопрос викторины.
    """
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные вопроса.", show_alert=True)
        return

    word_id = int(parts[1])
    selected_idx = int(parts[2])

    async with db_pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT word, options, correct_index FROM report_words WHERE word_id = $1",
            word_id
        )

    if not record:
        await callback.answer("Ошибка: данные вопроса не найдены.", show_alert=True)
        return

    is_correct = selected_idx == record["correct_index"]
    correct_word = record["options"][record["correct_index"]]
    selected_word = record["options"][selected_idx]

    if is_correct:
        msg = Text(
            "✅ Правильно! Отличная работа!\n\n",
            Bold("Слово: "), hd.quote(record['word'])
        ).as_markdown()
    else:
        msg = Text(
            "❌ К сожалению, неверно.\n\n",
            Bold("Ваш ответ: "), hd.quote(selected_word), "\n",
            Bold("Правильный ответ: "), hd.quote(correct_word), "\n",
            Bold("Слово: "), hd.quote(record['word'])
        ).as_markdown()

    await callback.answer()
    await callback.message.reply(text=msg, parse_mode="MarkdownV2")

    # Убираем кнопки с предыдущего сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    data = await state.get_data()
    next_idx = data.get("current_index", 0) + 1

    if next_idx >= len(data.get("word_ids", [])):
        await callback.bot.send_message(
            chat_id=data["chat_id"],
            text="🎉 Поздравляем! Вы завершили проверку знаний по всем словам."
        )
        await state.clear()
    else:
        await state.update_data(current_index=next_idx)
        await send_question(state, callback.bot)
