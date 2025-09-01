import logging

from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Text, Bold
from aiogram.utils.markdown import html_decoration as hd
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from middlewares.resources_middleware import ResourcesMiddleware # noqa
from keyboards.inline_keyboards import begin_weekly_quiz_keyboard # noqa
from config import LOG_CONFIG # noqa

from translations import WEEKLY_QUIZ # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='weekly_message_commands')

# Инициализация роутера
router = Router(name=__name__)


async def send_user_report(
        bot: Bot,
        user_id: int,
        report_id: int,
        database: ResourcesMiddleware,
) -> bool:
    """
    Отправляет пользователю его еженедельный отчет.
    """
    try:
        report = await database.get_report(report_id)
        words = await database.get_weekly_words(report_id)
        user_info = await database.get_user_info(user_id)
        lang_code = user_info['lang_code']

        if not report or not words:
            logger.warning(f"No report data found for report_id: {report_id}")
            return False

        # Извлекаем ID отправленного сообщения
        await bot.send_message(
            chat_id=user_id,
            text=WEEKLY_QUIZ['weekly_report'][lang_code],
            reply_markup=begin_weekly_quiz_keyboard(lang_code, report_id)
        )

        return True

    except TelegramForbiddenError:
        raise
    except TelegramBadRequest:
        raise

    except Exception as e:
        logger.error(f"Ошибка при отправке отчета {report_id} пользователю {user_id}: {e}", exc_info=True)
        return False


@router.callback_query(lambda callback: callback.data.startswith("start_report:"))
async def start_report_handler(
        callback: types.CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
):

    await callback.answer()

    try:
        # Извлекаю все ID слов конкретного отчета
        report_id = int(callback.data.split(":", 1)[1])
        word_ids = [ row['word_id'] for row in await database.get_words_ids(report_id) ]

        if not word_ids:
            await callback.answer("Отчет не содержит слов для проверки.", show_alert=True)
            return

        user_id = callback.message.chat.id

        await state.update_data(
            user_id=user_id,
            report_id=report_id,
            word_ids=word_ids,
            current_index=0,
            right_choices=[],
            wrong_choices=[],
            db_pool=database,
        )

        await callback.bot.send_message(
            chat_id=user_id,
            text="Начинаем проверку знаний...",
        )

        # Передаем quiz_manager в send_question
        await send_question(callback, state)


    except Exception as e:
        logger.error(f"Ошибка в start_report_handler: {e}", exc_info=True)
        await callback.answer("Ошибка запуска проверки", show_alert=True)


async def send_question(callback, state, database):

    data = await state.get_data()
    idx = data.get("current_index")
    word_ids = data.get("word_ids")
    user_id = data.get("user_id")
    lang_code = data.get("lang_code", "en")
    db_pool = data.get("db_pool")

    if not all(key in data for key in ["current_index", "word_ids", "user_id", "db_pool"]):
        logger.error("Отсутствуют ключи в состоянии FSM!")
        return

    if idx >= len(word_ids):

        msg = WEEKLY_QUIZ['congradulations'][lang_code]
        rights = ', '.join(data.get("right_choices", [])) or WEEKLY_QUIZ["no_rights"][lang_code]
        wrongs = ', '.join(data.get("wrong_choices", [])) or WEEKLY_QUIZ["no_wrongs"][lang_code]
        await callback.bot.send_message(  # Используем bot из callback
            user_id=user_id,
            text=msg.format(rights=rights, wrongs=wrongs),
            callback='end_quiz',
        )
        return await state.clear()

    word_id = word_ids[idx]
    word_data = await database.get_word_data(word_id)

    if not word_data:
        await callback.bot.send_message(
            user_id=user_id,
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
        # В callback_data мы передаем word_id и индекс варианта
        call_back = f"quiz:{word_id}:{opt_idx}"
        row.append(InlineKeyboardButton(text=option, callback_data=call_back))
        if len(row) >= 2:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)

    await callback.bot.send_message(
        user_id=user_id,
        text=question_text,
        reply_markup=keyboard
    )


@router.callback_query(lambda callback: callback.data.startswith("quiz:"))
async def handle_word_quiz(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
):
    try:
        data = await state.get_data()
        db_pool = data.get("db_pool")
        user_id = callback.message.chat.id

        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Incorrect data of question", show_alert=True)
            return

        word_id = int(parts[1])
        selected_idx = int(parts[2])

        async with db_pool.acquire_connection() as conn:
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
                "✅ Правильно!\n\n",
                Bold("Слово: "), hd.quote(record['word'])
            ).as_markdown()
            # Сохраняем правильное слово в data
            r_choices = data.get("right_choices", [])
            r_choices.append(record["word"])
            await state.update_data(right_choices=r_choices)
        else:
            msg = Text(
                "❌ К сожалению, неверно.\n\n",
                Bold("Ваш ответ: "), hd.quote(selected_word), "\n",
                Bold("Правильный ответ: "), hd.quote(correct_word), "\n",
            ).as_markdown()
            # Сохраняем неправильное слово в data
            w_choices = data.get("wrong_choices", [])
            w_choices.append(record["word"])
            await state.update_data(wrong_choices=w_choices)

        await callback.answer()

        # Убираем кнопки с текущего сообщения
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Ошибка при удалении кнопок: {e}")

        # Отправляем результат ответа (используем user_id)
        await callback.bot.send_message(
            chat_id=user_id,
            text=msg,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

        # Переходим к следующему вопросу
        next_idx = data.get("current_index", 0) + 1
        await state.update_data(current_index=next_idx)

        # Передаем только quiz_manager
        await send_question(callback, state, database)

    except Exception as e:
        logger.error(f"Ошибка в handle_word_quiz: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке ответа", show_alert=True)


@router.callback_query()  # Без фильтров, перехватывает все запросы обратного вызова
async def handle_unhandled_callback_query(callback: types.CallbackQuery):
    logger.warning(f"Получен необработанный запрос обратного вызова: {callback.data}")
    await callback.answer("Извините, я не понял эту команду.", show_alert=True)