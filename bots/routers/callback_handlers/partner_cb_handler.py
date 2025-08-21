import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from config import LOG_CONFIG, BOT_TOKEN_PARTNER # noqa
from utils.filters import IsBotFilter # noqa
from keyboards.inline_keyboards import get_back_to_partner_menu_keyboard, get_go_back_keyboard, show_partner_menu_keyboard # noqa
from translations import FIND_PARTNER # noqa


router = Router(name=__name__)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='partner_cb_handler')


@router.callback_query(F.data == "main_bot", IsBotFilter(BOT_TOKEN_PARTNER))
async def main_menu_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "profile", IsBotFilter(BOT_TOKEN_PARTNER))
async def profile_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = data["username"]
    nickname = data["name"]
    age = " " * 13 + str(data["age"])
    status = " " * 8 + data["status"]
    about = data["about"]

    lang_status = f"   [🟩🟩🟩🟩⬜⬜] Уровень владения: 40%\n▰▰▰▰▱▱▱▱▱▱ 127 слов\n(топ 20% юзеров)"

    msg = f"Info for you - {username}\n\n{lang_status}\n\nNickname: {nickname}\nAge: {age}\nStatus: {status}\nAbout you: {about}"
    await callback.answer(text=msg, show_alert=True)


@router.callback_query(F.data == "about", IsBotFilter(BOT_TOKEN_PARTNER))
async def about_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")

    await callback.message.edit_text(
        text=FIND_PARTNER["about"][lang_code],
        reply_markup=get_go_back_keyboard(lang_code),
    )

@router.callback_query(F.data == "go_back", IsBotFilter(BOT_TOKEN_PARTNER))
async def go_back_handler(callback: CallbackQuery, state: FSMContext):

    await callback.answer()

    data = await state.get_data()
    lang_code = data.get("lang_code")

    msg = FIND_PARTNER["full_intro"][lang_code]

    await callback.message.edit_text(
        text=msg,
        reply_markup=show_partner_menu_keyboard(lang_code),
    )
