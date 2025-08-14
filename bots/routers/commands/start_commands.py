import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from middlewares.resources_middleware import ResourcesMiddleware # noqa

from translations import QUESTIONARY # noqa
from utils.filters import IsBotFilter # noqa
from utils.message_mgr import MessageManager # noqa
from config import BOT_TOKEN_MAIN, LOG_CONFIG # noqa
from keyboards.inline_keyboards import show_where_from_keyboard, show_language_keyboard, confirm_choice_keyboard # noqa
from routers.commands.menu_commands import show_main_menu  # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='start_commands')

# Инициализируем роутер
router = Router(name=__name__)

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
        await show_main_menu(message, state)
        return

    await message_mgr.send_message_with_save(
        chat_id=message.chat.id,
        text=QUESTIONARY["intro"][lang_code],
        reply_markup=show_where_from_keyboard(lang_code),
    )


