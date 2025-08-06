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

from translations import BUTTONS, QUESTIONARY  # noqa
from filters import IsBotFilter  # noqa
from config import BOT_TOKEN_MAIN  # noqa
from de_injection import ResourcesMiddleware, Resources  # noqa

# Инициализируем DI-контейнер и роутер
resources = Resources()
router = Router(name=__name__)

# Фильтрация по токену основного бота
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))

# Привязываем middleware к роутеру
router.message.middleware(ResourcesMiddleware(resources))
router.callback_query.middleware(ResourcesMiddleware(resources))


@router.message(Command("menu"))
async def show_main_menu(
        message: Message,
        state: FSMContext,
        resources: Resources,
):
    """
    Показывает главное меню для пользователя.
    Язык пользователя берём из БД, а не из state.
    """
    user = message.from_user
    user_id = user.id
    first_name = user.first_name or ""
    # Получаем язык из БД
    lang_code = await resources.db.get_user_language(user_id)

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


@router.callback_query(F.data == "about")
async def about(
        callback: CallbackQuery,
        resources: Resources,
):
    """
    Обработчик нажатия кнопки "О боте".
    Берём текст из QUESTIONARY, ничего не храним в state.
    """
    # Получаем язык прямо из БД
    lang_code = await resources.db.get_user_language(callback.from_user.id)

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


@router.callback_query(F.data == "go_back")
async def go_back(
        callback: CallbackQuery,
        resources: Resources,
):
    """
    Возвращает пользователя назад в главное меню, повторно вызывая те же кнопки.
    """
    user = callback.from_user
    user_id = user.id
    first_name = user.first_name or ""
    lang_code = await resources.db.get_user_language(user_id)

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
