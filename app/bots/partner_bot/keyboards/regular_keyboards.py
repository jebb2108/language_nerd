from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.bots.partner_bot.translations import BUTTONS


def show_location_keyboard(lang_code):
    builder = ReplyKeyboardBuilder()
    share_button = KeyboardButton(
        text=BUTTONS["location"][lang_code],
        request_location=True,
        is_persistent=True,
    )
    cancel_button = KeyboardButton(text=BUTTONS["cancel"][lang_code])
    builder.add(share_button, cancel_button)
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def show_dating_keyboard(lang_code):
    builder = ReplyKeyboardBuilder()
    yes_button = KeyboardButton(
        text=BUTTONS["yes_to_dating"][lang_code],
    )
    no_button = KeyboardButton(
        text=BUTTONS["no_to_dating"][lang_code],
    )
    builder.add(yes_button, no_button)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
