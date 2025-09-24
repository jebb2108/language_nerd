import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bots.partner_bot.translations import TRANSCRIPTIONS
from config import LOG_CONFIG, config, LANG_CODE_LIST
from app.bots.main_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.main_bot.keyboards.inline_keyboards import (
    show_language_keyboard,
    show_fluency_keyboard,
    show_topic_keyboard,
    confirm_choice_keyboard,
)
from app.bots.main_bot.translations import MESSAGES, QUESTIONARY
from app.bots.main_bot.routers.commands.menu_commands import show_main_menu

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="registration_cb_handler")

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

    msg = f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["came_from"][users_choice][lang_code]}\n\n" \
          f"{QUESTIONARY["pick_lang"][lang_code]}"

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
    msg = f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["languages"][users_choice][lang_code]}\n\n" \
          f"{QUESTIONARY['fluency'][lang_code]}"
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
    users_choice = callback.data.split("_", 1)[1]

    # Отправляем сообщение с подтверждением
    msg = f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["fluency"][users_choice][lang_code]}\n\n" \
          f"{QUESTIONARY['choose_topic'][lang_code]}"
    await callback.message.edit_text(
        text=msg,
        reply_markup=show_topic_keyboard(lang_code),
    )


    await state.update_data(fluency=users_choice)


@router.callback_query(F.data.startswith("topic_"))
async def handle_topic_choice(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")
    users_choice = callback.data.split('_', 1)[1]

    # Отправляем сообщение с подтверждением
    msg = f"{MESSAGES["you_chose"][lang_code]} {TRANSCRIPTIONS["topics"][users_choice][lang_code]}\n\n" \
          f"{QUESTIONARY['terms'][lang_code]}"

    await callback.message.edit_text(
        text=msg,
        reply_markup=confirm_choice_keyboard(lang_code),
    )

    await state.update_data(topic=users_choice)


@router.callback_query(F.data == "action_confirm")
async def go_to_main_menu(
    callback: CallbackQuery, state: FSMContext, database: ResourcesMiddleware
):

    await callback.answer()
    await callback.message.delete()

    data = await state.get_data()
    user_id = int(data.get("user_id"))
    username = data.get("username")
    first_name = data.get("first_name")
    camefrom = data.get("camefrom")
    language = data.get("language")
    fluency = data.get("fluency")
    topic = data.get("topic", "general")
    lang_code = data.get("lang_code")
    if lang_code not in LANG_CODE_LIST: lang_code = "en"

    gratitude_msg = MESSAGES["gratitude"][lang_code]

    await callback.answer(text=gratitude_msg)

    # Сохраняем нового пользователя в БД
    await database.create_user(
        user_id, username, first_name, camefrom, language, fluency, topic, lang_code
    )

    # После сохранения сразу показываем главное меню
    await show_main_menu(callback.message, state, database)
