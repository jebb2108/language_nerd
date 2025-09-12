from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bots.partner_bot.translations import BUTTONS


def get_go_back_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back",
    )
    builder.add(go_back_button)
    return builder.as_markup(resize_keyboard=True)


def show_partner_menu_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    back_to_main_menu = InlineKeyboardButton(
        text=BUTTONS["main_bot"][lang_code],
        url="https://t.me/lllangbot",
        callback_data="main_menu",
    )
    search_button = InlineKeyboardButton(
        text=BUTTONS["search"][lang_code],
        callback_data="begin_search",
    )
    profile_button = InlineKeyboardButton(
        text=BUTTONS["profile"][lang_code],
        callback_data="profile",
    )
    about_button = InlineKeyboardButton(
        text=BUTTONS["about_bot"][lang_code],
        callback_data="about",
    )
    builder.add(back_to_main_menu, search_button, profile_button, about_button)
    builder.adjust(1, 1, 2)
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


def create_start_chat_button(lang_code, link):
    builder = InlineKeyboardBuilder()
    start_chat_button = InlineKeyboardButton(
        text=BUTTONS["open_chat"][lang_code],
        web_app=WebAppInfo(url=link),
    )
    builder.add(start_chat_button)
    return builder.as_markup(resize_keyboard=True)


def get_search_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    queue_info_button = InlineKeyboardButton(
        text=BUTTONS["queue_info"][lang_code], callback_data="queue_info"
    )
    cancel_button = InlineKeyboardButton(
        text=BUTTONS["cancel"][lang_code]
    )
    builder.add(queue_info_button, cancel_button)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
