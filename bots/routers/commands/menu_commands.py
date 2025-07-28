import os

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery

from config import BUTTONS, QUESTIONARY # noqa
from filters import IsBotFilter # noqa

router = Router(name=__name__)
# Фильтрация по токену
BOT_TOKEN_MAIN = os.getenv("BOT_TOKEN_MAIN")
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))

async def show_main_menu(message: Message, state: FSMContext):
    """Показывает главное меню для пользователя"""
    data = await state.get_data()
    user_id = data["user_id"]
    first_name = data["first_name"]
    lang_code = data["lang_code"]

    # Формируем URL с user_id
    web_app_url = f"https://lllang.site/index.html?user_id={user_id}"

    # Создаем клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTONS["dictionary"][lang_code], web_app=WebAppInfo(url=web_app_url)),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["find_partner"][lang_code], url="https://t.me/lllang_onlinebot"),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["about_bot"][lang_code], callback_data="about"),
            InlineKeyboardButton(text=BUTTONS["support"][lang_code], url="https://t.me/user_bot6426"),
        ],
    ])

    await message.answer(
        f"{BUTTONS['hello'][lang_code]}<b>{first_name}</b>!\n\n{QUESTIONARY['welcome'][lang_code]}",
        # Исправлены кавычки
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте"
    Показывает подробную информацию о проекте
    """

    data = await state.get_data()
    lang_code = data["lang_code"]
    # Клавиатура только с кнопкой возврата
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
    ])

    # Редактируем текущее сообщение, заменяя его на текст "О боте"
    await callback.message.edit_text(QUESTIONARY["about"][lang_code], reply_markup=keyboard)
    # Подтверждаем обработку callback (убираем часики на кнопке)
    await callback.answer()


@router.callback_query(F.data == "go_back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    first_name = data["first_name"]
    lang_code = data["lang_code"]

    # URL вашего Web App
    web_app_url = f"https://lllang.site/index.html?user_id={user_id}"

    # Создаем клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTONS["dictionary"][lang_code], web_app=WebAppInfo(url=web_app_url)),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["find_partner"][lang_code], url="https://t.me/lllang_onlinebot"),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["about_bot"][lang_code], callback_data="about"),
            InlineKeyboardButton(text=BUTTONS["support"][lang_code], url="https://t.me/user_bot6426"),
        ],
    ])

    # Отправляем приветственное сообщение с клавиатурой
    await callback.message.edit_text(
        f"{BUTTONS["hello"][lang_code]}<b>{first_name}</b>!\n\n{QUESTIONARY["welcome"][lang_code]}",
        reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()