from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bots.partner_bot.translations import BUTTONS


def show_topic_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    for key, value in BUTTONS["topics"][lang_code].items():
        builder.row(InlineKeyboardButton(text=value, callback_data=f"chtopic_{key}"))
    builder.row(InlineKeyboardButton(text=BUTTONS["cancel"][lang_code], callback_data="cancel_topic"))
    return builder.as_markup()


def get_go_back_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back",
    )
    builder.add(go_back_button)
    return builder.as_markup()


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
    builder.row(back_to_main_menu)
    builder.row(search_button)
    builder.row(profile_button, about_button)
    return builder.as_markup()


def get_back_to_partner_menu_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    back_to_main_menu = InlineKeyboardButton(
        text=BUTTONS["main_bot"][lang_code],
        url="https://t.me/lllangbot",
        callback_data="main_bot",
    )
    builder.add(back_to_main_menu)
    return builder.as_markup()


def get_payment_keyboard(lang_code, url):
    builder = InlineKeyboardBuilder()
    payment_button = InlineKeyboardButton(
        text=BUTTONS["payment"][lang_code], url=url
    )
    builder.add(payment_button)
    return builder.as_markup()

