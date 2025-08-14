import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery

from middlewares.resources_middleware import ResourcesMiddleware # noqa
from keyboards.inline_keyboards import show_where_from_keyboard, show_language_keyboard, confirm_choice_keyboard # noqa

from config import LOG_CONFIG # noqa
from translations import QUESTIONARY # noqa
from routers.commands.menu_commands import show_main_menu  # noqa


logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='registration_cb_handler')

router = Router(name=__name__)


class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()


@router.callback_query(F.data.startswith("camefrom_"), PollingStates.camefrom_state)
async def handle_camefrom(callback: CallbackQuery, state: FSMContext):
    """
    После вопроса «откуда узнали» переходим к выбору языка.
    """
    await callback.answer()

    try:
        camefrom = callback.data.split("_", 1)[1]
        await state.update_data(camefrom=camefrom)

        data = await state.get_data()
        lang_code = data.get("lang_code", "en")
        message_mgr = data["message_mgr"]

        await message_mgr.send_message_with_save(
            chat_id=callback.message.chat.id,
            text=QUESTIONARY["lang_pick"][lang_code],
            reply_markup=show_language_keyboard(),
        )
        await state.set_state(PollingStates.language_state)

    except Exception as e:
        logger.error(f"Error in handle_camefrom: {e}")


@router.callback_query(F.data.startswith("lang_"), PollingStates.language_state)
async def handle_language_choice(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
):

    """
    Сохраняем выбор языка, создаём запись в БД и идём в главное меню.
    """
    await callback.answer()

    data = await state.get_data()
    user_id = data["user_id"]
    username = data.get("username", "")
    first_name = data.get("first_name", "")
    camefrom = data.get("camefrom", "")
    lang_code = data.get("lang_code", "en")

    users_choice = callback.data.split("_", 1)[1]

    # Отправляем сообщение с подтверждением
    msg = (
            f"➪ Вы выбрали: {users_choice}\n\n"
            f"{QUESTIONARY['gratitude'][lang_code]}"
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=confirm_choice_keyboard(lang_code),
    )
    # Сохраняем нового пользователя в БД
    await database.add_user(user_id, username, first_name, camefrom, users_choice, lang_code)
    await state.set_state(PollingStates.introduction_state)


@router.callback_query(F.data == "action_confirm", PollingStates.introduction_state)
async def go_to_main_menu(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware
):
    await callback.answer()

    data = await state.get_data()
    message_mgr = data.get("message_mgr")

    await message_mgr.delete_previous_messages(
        chat_id=callback.message.chat.id
    )

    await state.clear()
    # После сохранения сразу показываем главное меню
    await show_main_menu(callback.message, state, database)
