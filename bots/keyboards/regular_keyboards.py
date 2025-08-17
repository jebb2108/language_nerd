import sys

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translations import FIND_PARTNER, QUESTIONARY # noqa



def get_location_keyboard(lang_code):
    share_button = KeyboardButton(
        text=QUESTIONARY["share_location"][lang_code],
        request_location=True,
        is_persistent=True,
    )
    cancel_button = KeyboardButton(
        text=FIND_PARTNER["cancel"][lang_code]
    )
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [share_button],
            [cancel_button]
        ],
        resize_keyboard=True,
    )
    return markup