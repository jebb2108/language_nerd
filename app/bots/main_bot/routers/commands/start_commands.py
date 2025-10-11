from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bots.main_bot.middlewares.rate_limit_middleware import RateLimitInfo
from app.bots.main_bot.translations import QUESTIONARY, MESSAGES
from app.dependencies import get_db
from app.bots.main_bot.keyboards.inline_keyboards import show_where_from_keyboard
from logging_config import opt_logger as log
from config import config

logger = log.setup_logger('main start commands', config.LOG_LEVEL)

# Инициализируем роутер
router = Router(name=__name__)

@router.message(Command("start", prefix="!/"))
async def start_with_polling(message: Message, state: FSMContext, rate_limit_info: RateLimitInfo):
    """
    Стартовая команда: проверяем в БД существование пользователя,
    сохраняем основные поля в state и либо идём в show_main_menu, либо стартуем опрос.
    """
    logger.debug(f"Current message count: {rate_limit_info.message_count}")

    # Проверяем, есть ли запись в users
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    lang_code = message.from_user.language_code

    if not username:
        username = "NO USERNAME"

    database = await get_db()
    user_exists = await database.check_user_exists(user_id)

    if user_exists:
        # если пользователь есть — сразу меню
        return await message.answer(
            text="Press /menu to open menu"
        )

    msg = (
        f"{MESSAGES['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{QUESTIONARY["intro"][lang_code]}"
    )

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=msg,
        reply_markup=show_where_from_keyboard(lang_code),
    )

    await state.update_data(
        user_id=user_id, username=username, first_name=first_name, lang_code=lang_code
    )
