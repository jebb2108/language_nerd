import logging

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from middlewares.resources_middleware import ResourcesMiddleware  # noqa
from config import LOG_CONFIG  # noqa

from translations import WEEKLY_QUIZ # noqa
from keyboards.inline_keyboards import show_word_options_keyboard, get_finish_button # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='weekly_message_cb_handler')

router = Router(name=__name__)


@router.callback_query(lambda callback: callback.data.startswith("start_report:"))
async def start_report_handler(
        callback: types.CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
):

    await callback.answer()

    data = await state.get_data()

    try:
        user_id = callback.message.chat.id
        # Извлекаю все ID слов конкретного отчета
        report_id = int(callback.data.split(":", 1)[1])
        word_ids = [ row['word_id'] for row in await database.get_words_ids(report_id) ]
        lang_code = data.get('lang_code', (await database.get_user_info(user_id))['lang_code'])

        if not word_ids:
            await callback.answer("Отчет не содержит слов для проверки.", show_alert=True)
            return


        await state.update_data(
            user_id=user_id,
            report_id=report_id,
            word_ids=word_ids,
            current_index=0,
            right_choices=[],
            wrong_choices=[],
            lang_code=lang_code,
        )

        await callback.message.edit_text(
            text="Начинаем проверку знаний...",
        )

        # Передаем quiz_manager в send_question
        await send_question(callback, state, database)


    except Exception as e:
        logger.error(f"Ошибка в start_report_handler: {e}", exc_info=True)


@router.callback_query(lambda callback: callback.data.startswith("quiz:"))
async def handle_word_quiz(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
):
    await callback.answer()

    data = await state.get_data()
    user_id = data.get('user_id', 0)
    lang_code = data.get("lang_code", "en")

    parts = callback.data.split(":")
    if len(parts) != 3: return logger.error("Incorrect data of question")

    word_id = int(parts[1])
    selected_idx = int(parts[2])
    word_data = await database.get_word_data(word_id)

    if not word_data: return logger.error("Ошибка: данные вопроса не найдены")

    is_correct = selected_idx == word_data["correct_index"]
    correct_word = word_data["options"][word_data["correct_index"]]
    selected_word = word_data["options"][selected_idx]

    if is_correct:
        msg = WEEKLY_QUIZ['right_answer'][lang_code].format(correct_word=correct_word)
        # Сохраняем правильное слово в data
        r_choices = data.get("right_choices", [])
        r_choices.append(correct_word)
        await state.update_data(right_choices=r_choices)

    else:
        msg = WEEKLY_QUIZ['wrong_answer'][lang_code].format(
            selected_word=selected_word,
            correct_word=correct_word
        )
        # Сохраняем неправильное слово в data
        w_choices = data.get("wrong_choices", [])
        w_choices.append(word_data["word"])
        await state.update_data(wrong_choices=w_choices)

    try:
        # Отправляем результат ответа (используем user_id)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.edit_text(
            text=msg,
            parse_mode=ParseMode.HTML,
        )

        # Переходим к следующему вопросу
        next_idx = data.get("current_index", 0) + 1
        await state.update_data(current_index=next_idx)
        return await send_question(callback, state, database)


    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")


async def send_question(callback, state, database):

    data = await state.get_data()
    idx = data.get("current_index")
    word_ids = data.get("word_ids")
    user_id = data.get("user_id")
    lang_code = data.get("lang_code", "en")

    logger.debug(f"Data: {data}")

    if not all(key in data for key in ["current_index", "word_ids", "user_id", "lang_code"]):
        return logger.error("Отсутствуют ключи в состоянии FSM (Redis)!")

    if idx >= len(word_ids):

        msg = WEEKLY_QUIZ['congradulations'][lang_code]
        rights = ', '.join(data.get("right_choices", [])) or WEEKLY_QUIZ["no_rights"][lang_code]
        wrongs = ', '.join(data.get("wrong_choices", [])) or WEEKLY_QUIZ["no_wrongs"][lang_code]
        await callback.bot.send_message(  # Используем bot из callback
            chat_id=user_id,
            text=msg.format(rights=rights, wrongs=wrongs),
            reply_markup=get_finish_button(lang_code),
        )
        return await state.clear()

    word_id = word_ids[idx]
    word_data = await database.get_word_data(word_id)

    if not word_data: return logger.error("Ошибка: данные вопроса не найдены")
    sentence, new_indx, total = word_data['sentence'], idx+1, len(word_ids)
    msg = WEEKLY_QUIZ['question_text'][lang_code]
    await callback.bot.send_message(
        chat_id=user_id,
        text=msg.format(idx=new_indx, total=total, sentence=sentence),
        reply_markup=show_word_options_keyboard(word_data)
    )

@router.callback_query(lambda callback: callback.data.startswith("end_quiz"))
async def do_nothing(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    return