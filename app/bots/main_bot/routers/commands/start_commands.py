import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bots.main_bot.middlewares.resources_middleware import ResourcesMiddleware

from app.bots.main_bot.translations import QUESTIONARY
from app.bots.main_bot.utils.filters import IsBotFilter
from config import config, LOG_CONFIG
from app.bots.main_bot.keyboards.inline_keyboards import show_where_from_keyboard
from app.bots.main_bot.routers.commands.menu_commands import show_main_menu

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="start_commands")

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(config.BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(config.BOT_TOKEN_MAIN))


@router.message(Command("start", prefix="!/"), IsBotFilter(config.BOT_TOKEN_MAIN))
async def start_with_polling(
    message: Message,
    state: FSMContext,
    database: ResourcesMiddleware,
):
    """
    Стартовая команда: проверяем в БД существование пользователя,
    сохраняем основные поля в state и либо идём в show_main_menu, либо стартуем опрос.
    """

    # Проверяем, есть ли запись в users
    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        username = "NO USERNAME"

    first_name = message.from_user.first_name
    lang_code = message.from_user.language_code or "en"
    user_exists = await database.check_user_exists(user_id)

    if user_exists:
        # если пользователь есть — сразу меню
        return await show_main_menu(message, state, database)

    # Обновляем данные в state
    await state.update_data(
        user_id=user_id,
        username=username,
        first_name=first_name,
        lang_code=lang_code,
    )

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=QUESTIONARY["intro"][lang_code],
        reply_markup=show_where_from_keyboard(lang_code),
    )
