from aiogram import F, Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    CallbackQuery,
)

from translations import BUTTONS, QUESTIONARY # noqa
from utils.filters import IsBotFilter # noqa
from config import BOT_TOKEN_MAIN # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену основного бота
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))


@router.message(Command("menu"), IsBotFilter(BOT_TOKEN_MAIN))
async def show_main_menu(
        message: Message,
        state: FSMContext,
        database: ResourcesMiddleware,
):
    await state.update_data(
        user_id= message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        lang_code=message.from_user.language_code or "en",
    )

    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    lang_code = message.from_user.language_code or "en"

    # Формируем URL с user_id для Web App
    web_app_url = f"https://lllang.site/?user_id={user_id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS["dictionary"][lang_code],
                web_app=WebAppInfo(url=web_app_url),
            ),
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS["find_partner"][lang_code],
                url="https://t.me/lllang_onlinebot",
            ),
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS["about_bot"][lang_code],
                callback_data="about",
            ),
            InlineKeyboardButton(
                text=BUTTONS["support"][lang_code],
                url="https://t.me/user_bot6426",
            ),
        ],
    ])

    await message.answer(
        f"{BUTTONS['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{QUESTIONARY['welcome'][lang_code]}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "about", IsBotFilter(BOT_TOKEN_MAIN))
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """

    data = await state.get_data()
    lang_code = data.get("lang_code")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
    ])

    # Редактируем текущее сообщение
    await callback.message.edit_text(
        QUESTIONARY["about"][lang_code],
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()  # убираем "часики" на кнопке


@router.callback_query(F.data == "go_back", IsBotFilter(BOT_TOKEN_MAIN))
async def go_back(
        callback: CallbackQuery,
        state: FSMContext,
):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    data = await state.get_data()
    user_id = data.get("user_id")
    first_name = data.get("first_name")
    lang_code = data.get("lang_code")

    web_app_url = f"https://lllang.site/?user_id={user_id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS["dictionary"][lang_code],
                web_app=WebAppInfo(url=web_app_url),
            ),
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS["find_partner"][lang_code],
                url="https://t.me/lllang_onlinebot",
            ),
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS["about_bot"][lang_code],
                callback_data="about",
            ),
            InlineKeyboardButton(
                text=BUTTONS["support"][lang_code],
                url="https://t.me/user_bot6426",
            ),
        ],
    ])

    await callback.message.edit_text(
        f"{BUTTONS['hello'][lang_code]} <b>{first_name}</b>!\n\n"
        f"{QUESTIONARY['welcome'][lang_code]}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
