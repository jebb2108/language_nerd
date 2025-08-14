from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from translations import BUTTONS, QUESTIONARY # noqa
from utils.filters import IsBotFilter # noqa
from config import BOT_TOKEN_MAIN # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa
from keyboards.inline_keyboards import get_on_main_menu_keyboard, get_go_back_keyboard # noqa

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену основного бота
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))


@router.message(Command("menu"), IsBotFilter(BOT_TOKEN_MAIN))
async def show_main_menu(message: Message, state: FSMContext):

    user_id = message.from_user.id
    user_name = message.from_user.username
    first_name = message.from_user.first_name
    lang_code = message.from_user.language_code or "en"

    await state.update_data(
        user_id=user_id,
        username=user_name,
        first_name=first_name,
        lang_code=lang_code,
    )

    msg = (
        f"{BUTTONS['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{QUESTIONARY['welcome'][lang_code]}"
    )

    await message.answer(
        text=msg,
        reply_markup=get_on_main_menu_keyboard(user_id, lang_code),
        parse_mode=ParseMode.HTML,
    )


