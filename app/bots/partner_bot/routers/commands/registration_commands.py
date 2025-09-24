import logging
import re
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from app.bots.partner_bot.keyboards.regular_keyboards import (
    show_dating_keyboard,
    show_location_keyboard,
)
from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.routers.commands.partner_commands import show_main_menu
from app.bots.partner_bot.translations import MESSAGES, QUESTIONARY, BUTTONS, TRANSCRIPTIONS
from app.bots.partner_bot.utils.access_data import data_storage
from config import config, LOG_CONFIG


class PollingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_bday = State()
    waiting_for_intro = State()
    waiting_for_dating = State()
    waiting_for_location = State()


# Инициализируем роутер
router = Router(name=__name__)

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name="registration_commands")


@router.message(Command("start", prefix="!/"))
async def start(message: Message, state: FSMContext, database: ResourcesMiddleware):
    if await database.check_profile_exists(message.from_user.id):
        return await show_main_menu(message, state, database)

    user_id = message.from_user.id

    user_data = await data_storage.get_storage_data(
        user_id=user_id, state=state, database=database
    )

    language = user_data.get("language")
    lang_code = user_data.get("lang_code")

    greeting = (
        f"{MESSAGES['intro'][lang_code].format(language=TRANSCRIPTIONS["languages"][language][lang_code])}\n"
    )
    await message.answer(text=greeting, parse_mode=ParseMode.HTML)

    # Обновляем user_id в состоянии
    await state.update_data(**user_data)
    # Отправляем приветственное сообщение
    txt = QUESTIONARY["need_profile"][lang_code]
    await message.answer(text=txt, parse_mode=ParseMode.HTML)
    # Переходим в состояние ожидания имени
    await state.set_state(PollingState.waiting_for_name)


@router.message(PollingState.waiting_for_name)
async def process_name(
    message: Message, state: FSMContext
):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if len(message.text) <= 50 and re.sub(r"\s", "", message.text) == message.text:
        await state.update_data(name=message.text)
        msg = QUESTIONARY["need_age"][lang_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        await state.set_state(PollingState.waiting_for_bday)
        return

    msg = MESSAGES["wrong_name"][lang_code]
    await message.reply(text=msg, parse_mode=ParseMode.HTML)
    await state.set_state(PollingState.waiting_for_name)


@router.message(PollingState.waiting_for_bday)
async def process_age(
    message: Message, state: FSMContext
):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if (
        datetime.now(tz=config.TZINFO).date().year
        >= int(message.text.split(".")[2])
        > 1900
    ):
        if re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", message.text):
            try:
                datetime.strptime(message.text, "%d.%m.%Y")
                await state.update_data(bday=message.text)
                await message.answer(
                    text=QUESTIONARY["need_intro"][lang_code], parse_mode=ParseMode.HTML
                )
                await state.set_state(PollingState.waiting_for_intro)
                return

            except ValueError:
                pass

    msg = MESSAGES["wrong_birthday"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)
    await state.set_state(PollingState.waiting_for_bday)


@router.message(PollingState.waiting_for_intro)
async def process_intro(
    message: Message, state: FSMContext
):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if re.search(r"\S{10,500}", message.text):
        msg = QUESTIONARY["need_dating"][lang_code]
        await message.answer(
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=show_dating_keyboard(lang_code),
        )
        await state.update_data(intro=message.text)
        await state.set_state(PollingState.waiting_for_dating)
        return

    msg = MESSAGES["wrong_intro"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)
    await state.set_state(PollingState.waiting_for_intro)


@router.message(
    PollingState.waiting_for_dating,
    lambda message: message.text
    == BUTTONS["yes_to_dating"][message.from_user.language_code],
)
async def agreed_to_dating_handler(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id", 0)
    name = data.get("name", "default")
    birthday = datetime.strptime(data.get("bday", "01.01.1800"), "%d.%m.%Y").date()
    intro = data.get("intro", "non-existent")
    lang_code = data.get("lang_code", "en")
    # Сохраняем профиль
    await database.add_users_profile(user_id, name, birthday, about=intro, dating=True)

    location_exists: bool = await database.check_location_exists(user_id)
    if not location_exists:
        msg = QUESTIONARY["need_location"][lang_code]
        await message.answer(
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=show_location_keyboard(lang_code),
        )
        await state.set_state(PollingState.waiting_for_location)
        return

    # Если локация каким-то образом существует, то переходим в главное меню
    else:
        await show_main_menu(message, state, database)


@router.message(
    PollingState.waiting_for_dating,
    lambda message: message.text
    == BUTTONS["no_to_dating"][message.from_user.language_code],
)
async def disagreed_to_dating_handler(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    data = await state.get_data()
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id", 0)
    name = data.get("name", "default")
    birthday = datetime.strptime(data.get("bday", "01.01.1800"), "%d.%m.%Y").date()
    intro = data.get("intro", "non-existent")
    lang_code = data.get("lang_code", "en")
    # Сохраняем профиль
    await database.add_users_profile(user_id, name, birthday, about=intro, dating=False)
    msg = MESSAGES["no_worries_dating"][lang_code]
    await message.answer(
        text=msg, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()


@router.message(PollingState.waiting_for_location, F.location)
async def process_location(
    message: Message, state: FSMContext, database: ResourcesMiddleware
):
    """Обработчик локации"""
    data = await state.get_data()
    user_id = data.get("user_id", 0)
    lang_code = data.get("lang_code", "en")
    # Сохраняем координаты в БД
    lattitude = str(message.location.latitude)
    longitude = str(message.location.longitude)
    await database.add_users_location(user_id, lattitude, longitude)
    # Выводим благодарное сообщение
    msg = MESSAGES["success"][lang_code]
    await message.answer(text=msg, reply_markup=ReplyKeyboardRemove())
    await state.clear()


@router.message(
    PollingState.waiting_for_location,
    lambda message: message.text
    == BUTTONS["cancel"].get(message.from_user.language_code, BUTTONS["cancel"]["en"]),
)
async def cancel(message: Message, state: FSMContext, database: ResourcesMiddleware):
    msg = MESSAGES["no_worries"][message.from_user.language_code]
    await database.add_users_location(message.from_user.id, "refused", "refused")
    await message.reply(text=msg, reply_markup=ReplyKeyboardRemove())
    await state.clear()
