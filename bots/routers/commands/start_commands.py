import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from translations import QUESTIONARY # noqa
from utils.filters import IsBotFilter # noqa
from utils.message_mgr import MessageManager # noqa
from config import BOT_TOKEN_MAIN, LOG_CONFIG # noqa
from routers.commands.menu_commands import show_main_menu  # noqa
from routers.commands.markups import show_where_from_keyboard, show_language_keyboard, confirm_choice_keyboard # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa


logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='start_commands')

# Инициализируем роутер
router = Router(name=__name__)

class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))

@router.message(Command("start"), IsBotFilter(BOT_TOKEN_MAIN))
async def start_with_polling(
        message: Message,
        state: FSMContext,
        database: ResourcesMiddleware,
):
    """
    Стартовая команда: проверяем в БД существование пользователя,
    сохраняем основные поля в state и либо идём в show_main_menu, либо стартуем опрос.
    """

    user_id = message.from_user.id
    lang_code = message.from_user.language_code or "en"

    # Создаем экземпляр класса MessageManager
    message_mgr = MessageManager(bot=message.bot, state=state)

    # Проверяем, есть ли запись в users
    user_exists = await database.check_user_exists(user_id)

    # Обновляем данные в state
    await state.update_data(
        user_id=user_id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        lang_code=lang_code,
        message_mgr=message_mgr,
    )

    if user_exists:
        # если пользователь есть — сразу меню
        await show_main_menu(message, state, database)
        return

    await message_mgr.send_message_with_save(
        chat_id=message.chat.id,
        text=QUESTIONARY["intro"][lang_code],
        reply_markup=show_where_from_keyboard(lang_code),
    )
    await state.set_state(PollingStates.camefrom_state)


@router.callback_query(F.data.startswith("camefrom_"), PollingStates.camefrom_state)
async def handle_camefrom(callback: CallbackQuery, state: FSMContext):
    """
    После вопроса «откуда узнали» переходим к выбору языка.
    """
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
        await callback.answer()

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
    await callback.answer()


@router.callback_query(F.data == "action_confirm", PollingStates.introduction_state)
async def go_to_main_menu(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware
):
    data = await state.get_data()
    message_mgr = data.get("message_mgr")

    await message_mgr.delete_previous_messages(
        chat_id=callback.message.chat.id
    )

    await state.clear()
    # После сохранения сразу показываем главное меню
    await show_main_menu(callback.message, state, database)