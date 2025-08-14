import sys

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translations import BUTTONS, QUESTIONARY # noqa



def get_on_main_menu_keyboard(user_id, lang_code):
    # Формируем URL с user_id для Web App
    web_app_url = "https://lllang.site/?user_id=%s}".format(str(user_id))

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
    return keyboard


def get_go_back_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
    ])
    return keyboard


def show_where_from_keyboard(lang_code):
    # иначе запускаем опрос «откуда вы о нас узнали»
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}0"],
                callback_data="camefrom_friends"
            )
        ],
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}1"],
                callback_data="camefrom_search"
            )
        ],
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}2"],
                callback_data="camefrom_other"
            )
        ],
    ])
    return keyboard


def show_language_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_russian")],
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_english")],
        [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_german")],
        [InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_spanish")],
        [InlineKeyboardButton(text="🇨🇳 中文", callback_data="lang_chinese")],
    ])
    return keyboard


def confirm_choice_keyboard(lang_code):
    # Обновляем текст с подтверждением выбора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=QUESTIONARY["confirm"][lang_code],
            callback_data="action_confirm"
        )]
    ])
    return keyboard
