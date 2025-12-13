from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile


from src.filters.approved import approved
from src.keyboards.inline_keyboards import (
    get_on_main_menu_keyboard,
)
from src.middlewares.rate_limit_middleware import RateLimitInfo
from src.translations import MESSAGES
from src.utils.access_data import data_storage as ds
from src.dependencies import get_gateway
from src.config import config
from src.logconf import opt_logger as log

logger = log.setup_logger("main menu commands")

# Инициализируем роутер
router = Router(name=__name__)


@router.message(
    and_f(Command("menu", prefix="!/"), approved)
)
async def show_main_menu(message: Message, state: FSMContext, rate_limit_info: RateLimitInfo):

    logger.debug(
        f"User %s message count: %s",
        message.from_user.id, rate_limit_info.message_count
    )

    # Получаем данные из состояния
    user_id = message.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")
    is_active = data.get("is_active")
    if not is_active: return

    msg = f"{MESSAGES['welcome'][lang_code]}"
    if data.get("nickname", False):
        msg += MESSAGES["pin_me"][lang_code]
    else:
        msg += MESSAGES["get_to_know"][lang_code]

    image_from_file = FSInputFile(config.bot.abs_img_path)
    await message.answer_photo(
        photo=image_from_file,
        caption=msg,
        reply_markup=get_on_main_menu_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )


@router.message(and_f(Command("location", prefix="!/"), approved))
async def get_my_location(message: Message, state: FSMContext):
    """Обработчик команды /location"""

    user_id = message.from_user.id
    data = await ds.get_storage_data(user_id, state)
    lang_code = data.get("lang_code")

    gateway = await get_gateway()
    async with gateway() as session:
        location = await session.get('get_users_location', user_id)
        if not location:
            await message.answer(text=MESSAGES["no_location"][lang_code])
            return

        else:
            city = data["city"] # noqa
            country = data["country"] # noqa

            msg = MESSAGES["your_location"][lang_code]
            await message.answer(
                text=f"{msg}: <b>{city}</b>, <b>{country}</b>",
                parse_mode=ParseMode.HTML,
            )