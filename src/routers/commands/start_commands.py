from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.keyboards.inline_keyboards import show_where_from_keyboard
from src.middlewares.rate_limit_middleware import RateLimitInfo
from src.translations import QUESTIONARY, MESSAGES
from src.dependencies import get_gateway
from src.logconf import opt_logger as log

logger = log.setup_logger('start commands')

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

    gateway = await get_gateway()
    async with gateway:
        response = await gateway.get('check_user_exists', user_id)


    if response.json():
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
