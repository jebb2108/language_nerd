from aiogram.types import InlineKeyboardButton, WebAppInfo
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
    shop_button = InlineKeyboardButton(
        text=BUTTONS["shop"][lang_code],
        callback_data="shop:0",
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
    builder.row(shop_button)
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


def open_chat_keyboard(lang_code, link):
    builder = InlineKeyboardBuilder()
    open_chat_button = InlineKeyboardButton(
        text=BUTTONS["open_chat"][lang_code],
        web_app=WebAppInfo(url=link),
    )
    builder.add(open_chat_button)
    return builder.as_markup()


def create_start_chat_button(lang_code, link):
    builder = InlineKeyboardBuilder()
    start_chat_button = InlineKeyboardButton(
        text=BUTTONS["open_chat"][lang_code],
        web_app=WebAppInfo(url=link),
    )
    builder.add(start_chat_button)
    return builder.as_markup()


def get_search_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    queue_info_button = InlineKeyboardButton(
        text=BUTTONS["queue_info"][lang_code], callback_data="queue_info"
    )
    cancel_button = InlineKeyboardButton(
        text=BUTTONS["cancel"][lang_code], callback_data="cancel"
    )
    builder.add(queue_info_button, cancel_button)
    builder.adjust(1)
    return builder.as_markup()


def get_payment_keyboard(lang_code, url):
    builder = InlineKeyboardBuilder()
    payment_button = InlineKeyboardButton(
        text=BUTTONS["payment"][lang_code], url=url
    )
    builder.add(payment_button)
    return builder.as_markup()

def get_shop_keyboard(lang_code, indx):
    builder = InlineKeyboardBuilder()
    make_payment = InlineKeyboardButton(
        text=BUTTONS["make_payment"][lang_code] if indx != 9 else "Приведи друга",
        callback_data=f"make_payment:{indx}"
    )
    next_button = InlineKeyboardButton(
        text=BUTTONS["next"][lang_code], callback_data=f"shop:{indx+1 if not indx==9 else 0}"
    )
    prev_button = InlineKeyboardButton(
        text=BUTTONS["prev"][lang_code], callback_data=f"shop:{indx-1 if not indx==0 else 9}"
    )
    exit_button = InlineKeyboardButton(
        text=BUTTONS["exit"][lang_code], callback_data="exit_shop"
    )
    builder.row(make_payment)
    builder.row(prev_button, next_button)
    builder.row(exit_button)
    return builder.as_markup()
