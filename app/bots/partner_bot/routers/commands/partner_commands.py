from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command, and_f
from aiogram.enums import ParseMode

from app.bots.main_bot.filters.paytime import paytime
from app.bots.partner_bot.middlewares.rate_limit_middleware import RateLimitInfo
from app.dependencies import get_db
from config import config
from app.bots.partner_bot.translations import MESSAGES

from app.bots.partner_bot.keyboards.inline_keyboards import (
    show_partner_menu_keyboard,
)

from app.bots.partner_bot.utils.access_data import data_storage
from logging_config import opt_logger as log

# Инициализируем роутер
router = Router(name=__name__)

logger = log.setup_logger("partner_commands", config.LOG_LEVEL)


@router.message(and_f(Command("menu", prefix="!/"), paytime))
async def show_main_menu(message: Message, state: FSMContext, rate_limit_info: RateLimitInfo):
    """Главное меню бота"""
    database = await get_db()
    user_id = message.from_user.id
    data = await data_storage.get_storage_data(user_id, state)
    nickname = data.get("nickname", None)
    language = data.get("language")
    lang_code = data.get("lang_code")

    logger.debug(
        f"User %s message count: %s",
        user_id, rate_limit_info.message_count
    )

    if not await database.check_user_exists(user_id):
        await message.answer(text="I can`t seem to know you :( Go to @lllangbot")
        return

    elif nickname is None:
        await message.answer(
            text=MESSAGES["not_registered"][lang_code],
            parse_mode=ParseMode.HTML,
        )
        return

    greeting = MESSAGES["hello"][language] + " <b>" + nickname + "</b>!"
    intro = MESSAGES["full_intro"][lang_code]
    await state.update_data(
        user_id=user_id,
        lang_code=lang_code,
        first_name=message.from_user.first_name,
    )

    image_from_file = FSInputFile(config.ABS_PATH_TO_IMG_TWO)
    await message.answer_photo(
        photo=image_from_file,
        caption=greeting + "\n\n" + intro,
        reply_markup=show_partner_menu_keyboard(lang_code),
        parse_mode=ParseMode.HTML,
    )


