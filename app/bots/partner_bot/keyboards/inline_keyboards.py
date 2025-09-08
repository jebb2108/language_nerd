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
