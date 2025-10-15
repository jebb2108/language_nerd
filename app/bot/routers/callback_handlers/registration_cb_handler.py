from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from app.bot.keyboards.inline_keyboards import (
    show_language_keyboard,
    show_fluency_keyboard,
    show_topic_keyboard,
    confirm_choice_keyboard,
    payment_keyboard,
    get_on_main_menu_keyboard,
)
from app.bot.translations import MESSAGES, QUESTIONARY, TRANSCRIPTIONS
from app.dependencies import get_rabbitmq
from app.models import NewUser, NewPayment
from config import config
from logging_config import opt_logger as log

logger = log.setup_logger("registration_cb_handler", config.LOG_LEVEL)
router = Router(name=__name__)


@router.callback_query(F.data.startswith("camefrom_"))
async def handle_camefrom(callback: CallbackQuery, state: FSMContext):
    """
    После вопроса «откуда узнали» переходим к выбору языка.
    """
    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")

    users_choice = callback.data.split("_", 1)[1]

    msg = (
        f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["came_from"][users_choice][lang_code]}\n\n"
        f"{QUESTIONARY["pick_lang"][lang_code]}"
    )

    await callback.message.edit_text(
        text=msg,
        reply_markup=show_language_keyboard(),
    )

    await state.update_data(camefrom=users_choice)


@router.callback_query(F.data.startswith("lang_"))
async def handle_fluency_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")

    users_choice = callback.data.split("_", 1)[1]
    msg = (
        f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["languages"][users_choice][lang_code]}\n\n"
        f"{QUESTIONARY['fluency'][lang_code]}"
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=show_fluency_keyboard(lang_code),
    )

    await state.update_data(language=users_choice)


@router.callback_query(F.data.startswith("fluency_"))
async def handle_language_choice(callback: CallbackQuery, state: FSMContext):
    """
    Сохраняем выбор языка
    """
    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")
    users_choice = int(callback.data.split("_", 1)[1])

    # Отправляем сообщение с подтверждением
    msg = (
        f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["fluency"][users_choice][lang_code]}\n\n"
        f"{QUESTIONARY['choose_topic'][lang_code]}"
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=show_topic_keyboard(lang_code),
    )

    await state.update_data(fluency=users_choice)


@router.callback_query(F.data.startswith("topic_"))
async def handle_transaction_offer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")
    users_choice = callback.data.split("_", 1)[1]
    msg = (
        f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["topics"][users_choice][lang_code]}\n\n"
        f"{QUESTIONARY['payment_offer'][lang_code]}"
    )

    await callback.message.edit_text(
        text=msg,
        reply_markup=payment_keyboard(lang_code),
    )

    await state.update_data(topic=users_choice)


@router.callback_query(F.data == "start_trial")
async def handle_topic_choice(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")

    # Отправляем сообщение с подтверждением
    msg = f"{QUESTIONARY['terms'][lang_code]}"

    await callback.message.edit_text(
        text=msg,
        reply_markup=confirm_choice_keyboard(lang_code),
    )


@router.callback_query(F.data == "action_confirm")
async def go_to_main_menu(callback: CallbackQuery, state: FSMContext):

    await callback.answer()
    await callback.message.delete()
    rabbit = await get_rabbitmq()
    data = await state.get_data()

    lang_code = data.get("lang_code")
    if lang_code not in ["en", "ru", "de", "es", "zh"]:
        lang_code = "en"

    msg = f"{MESSAGES['welcome'][lang_code]}"
    msg += MESSAGES["get_to_know"][lang_code]

    image_from_file = FSInputFile(config.ABS_PATH_TO_IMG_ONE)
    await callback.message.answer_photo(
        photo=image_from_file,
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )
    # Отправляем нового пользователя и транзакцию в RabbitMQ
    # на сохранение в основную БД
    trial_dt_obj = datetime.now(tz=config.TZINFO) + timedelta(days=3)
    await rabbit.publish_user(
        NewUser(
            user_id=int(data.get("user_id")),
            username=data.get("username"),
            first_name=data.get("first_name"),
            camefrom=data.get("camefrom"),
            language=data.get("language"),
            fluency=int(data.get("fluency")),
            topic=data.get("topic"),
            lang_code=lang_code,
        ),
        NewPayment(user_id=int(data.get("user_id")), untill=trial_dt_obj),
    )
