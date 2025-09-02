import sys

from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translations import BUTTONS, FIND_PARTNER, QUESTIONARY, WEEKLY_QUIZ # noqa
from config import VERSION # noqa


def get_on_main_menu_keyboard(user_id, lang_code):
    # Формируем URL с user_id для Web App
    web_app_url = f"https://dict.lllang.site/?user_id={user_id}&v={VERSION}"

    builder = InlineKeyboardBuilder()
    dict_button = InlineKeyboardButton(
        text=BUTTONS["dictionary"][lang_code],
        web_app=WebAppInfo(url=web_app_url),
    )
    find_partner_button = InlineKeyboardButton(
        text=BUTTONS["find_partner"][lang_code],
        url="https://t.me/lllang_onlinebot",
    )
    about_bot_button = InlineKeyboardButton(
        text=BUTTONS["about_bot"][lang_code],
        callback_data="about",
    )
    support_button = InlineKeyboardButton(
        text=BUTTONS["support"][lang_code],
        url="https://t.me/user_bot6426",
    )
    builder.add(dict_button, find_partner_button, about_bot_button, support_button)
    builder.adjust(1, 1, 2)

    return builder.as_markup(resize_keyboard=True)


def get_go_back_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back",
    )
    builder.add(go_back_button)
    return builder.as_markup(resize_keyboard=True)


def show_where_from_keyboard(lang_code):
    # иначе запускаем опрос «откуда вы о нас узнали»
    builder = InlineKeyboardBuilder()
    friends_button = InlineKeyboardButton(
        text=QUESTIONARY["where_youcamefrom"][f"{lang_code}0"],
        callback_data="camefrom_friends",
    )
    search_button = InlineKeyboardButton(
        text=QUESTIONARY["where_youcamefrom"][f"{lang_code}1"],
        callback_data="camefrom_search",
    )
    through_ad_button = InlineKeyboardButton(
        text=QUESTIONARY["where_youcamefrom"][f"{lang_code}2"],
        callback_data="camefrom_other",
    )
    builder.add(friends_button, search_button, through_ad_button)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def show_language_keyboard():
    builder = InlineKeyboardBuilder()
    russian_button = InlineKeyboardButton(
        text="🇷🇺 Русский",
        callback_data="lang_russian",
    )
    english_button = InlineKeyboardButton(
        text="🇺🇸 English",
        callback_data="lang_english",
    )
    german_button = InlineKeyboardButton(
        text="🇩🇪 Deutsch",
        callback_data="lang_german",
    )
    spanish_button = InlineKeyboardButton(
        text="🇪🇸 Español",
        callback_data="lang_spanish",
    )
    chinese_button = InlineKeyboardButton(
        text="🇨🇳 中文",
        callback_data="lang_chinese",
    )
    builder.add(russian_button, english_button, german_button, spanish_button, chinese_button)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def show_fluency_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    for key, value in QUESTIONARY["fluency_levels"][lang_code].items():
        builder.row(InlineKeyboardButton(text=value, callback_data=f"fluency_{key}"))

    return builder.as_markup(resize_keyboard=True)


def confirm_choice_keyboard(lang_code):
    # Обновляем текст с подтверждением выбора
    builder = InlineKeyboardBuilder()
    confirm_button = InlineKeyboardButton(
        text=QUESTIONARY["confirm"][lang_code],
        callback_data="action_confirm",
    )
    builder.add(confirm_button)
    return builder.as_markup(resize_keyboard=True)

def show_partner_menu_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    profile_button = InlineKeyboardButton(
        text=BUTTONS["profile"][lang_code],
        callback_data="profile",
    )
    back_to_main_menu = InlineKeyboardButton(
        text=BUTTONS["main_bot"][lang_code],
        url="https://t.me/lllangbot",
        callback_data="main_menu",
    )
    about_button = InlineKeyboardButton(
        text=BUTTONS["about_bot"][lang_code],
        callback_data="about",
    )
    builder.add(back_to_main_menu, profile_button, about_button)
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

def get_back_to_partner_menu_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    back_to_main_menu = InlineKeyboardButton(
        text=BUTTONS["main_bot"][lang_code],
        url="https://t.me/lllangbot",
        callback_data="main_bot",
    )
    builder.add(back_to_main_menu)
    return builder.as_markup(resize_keyboard=True)

def open_chat_keyboard(lang_code, link):
    builder = InlineKeyboardBuilder()
    open_chat_button = InlineKeyboardButton(
        text=BUTTONS["open_chat"][lang_code],
        web_app=WebAppInfo(url=link),
    )
    builder.add(open_chat_button)
    return builder.as_markup(resize_keyboard=True)

def begin_weekly_quiz_keyboard(lang_code, report_id):
    builder = InlineKeyboardBuilder()
    begin_quiz_button = InlineKeyboardButton(
        text=WEEKLY_QUIZ["begin"][lang_code],
        callback_data=f"start_report:{report_id}"
    )
    builder.add(begin_quiz_button)
    return builder.as_markup(resize_keyboard=True)

def show_word_options_keyboard(word_data):
    builder = InlineKeyboardBuilder()
    for opt_idx, option in enumerate(word_data["options"]):
        # В callback_data мы передаем word_id и индекс варианта
        call_back = f"quiz:{word_data['word_id']}:{opt_idx}"
        builder.row(InlineKeyboardButton(text=option, callback_data=call_back))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
