import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery

from middlewares.resources_middleware import ResourcesMiddleware # noqa
from keyboards.inline_keyboards import show_language_keyboard, show_fluency_keyboard, confirm_choice_keyboard # noqa

from config import LOG_CONFIG # noqa
from translations import QUESTIONARY # noqa
from routers.commands.menu_commands import show_main_menu  # noqa


logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='registration_cb_handler')

router = Router(name=__name__)


@router.callback_query(F.data.startswith("camefrom_"))
async def handle_camefrom(callback: CallbackQuery, state: FSMContext):
    """
    После вопроса «откуда узнали» переходим к выбору языка.
    """
    await callback.answer()

    camefrom = callback.data.split("_", 1)[1]


    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    message_mgr = data["message_mgr"]

    await message_mgr.send_message_with_save(
        chat_id=callback.message.chat.id,
        text=QUESTIONARY["lang_pick"][lang_code],
        reply_markup=show_language_keyboard(),
    )
    
    await state.update_data(user_id=callback.from_user.id, camefrom=camefrom)
    
        
@router.callback_query(F.data.startswith("lang_"))
async def handle_fluency_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    
    users_choice = callback.data.split("_", 1)[1]
    msg = (
            f"➪ Вы выбрали: {users_choice}\n\n"
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
    lang_code = data.get("lang_code", "en")

    users_choice = callback.data.split("_", 1)[1]

    # Отправляем сообщение с подтверждением
    msg = (
            f"➪ Вы выбрали: {users_choice}\n\n"
            f"{QUESTIONARY['terms'][lang_code]}"
    )
    await callback.message.edit_text(
        text=msg,
        reply_markup=confirm_choice_keyboard(lang_code),
    )
    
    await state.update_data(fluency=users_choice)


@router.callback_query(F.data == "action_confirm")
async def go_to_main_menu(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware
):
    
    await callback.answer()

    data = await state.get_data()
    user_id = data.get("user_id", 0)
    username = data.get("username", "")
    first_name = data.get("first_name", "")
    camefrom = data.get("camefrom", "")
    language = data.get("language", "")
    fluency = data.get("fluency", "in_making")
    lang_code = data.get("lang_code", "en")
    message_mgr = data.get("message_mgr")
    
    gratitude_msg = QUESTIONARY["gratitude"][lang_code]
    
    orig_message = data.get('orig_message')

    await callback.answer(
        text=gratitude_msg,
    )

    await message_mgr.delete_previous_messages(
        chat_id=callback.message.chat.id
    )
    
    # Сохраняем нового пользователя в БД
    await database.create_user(user_id, username, first_name, camefrom, language, fluency, lang_code)

    # После сохранения сразу показываем главное меню
    await show_main_menu(orig_message, state)
