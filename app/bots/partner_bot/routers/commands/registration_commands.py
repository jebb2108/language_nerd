import re
from datetime import datetime

import aiohttp
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from app.bots.main_bot.utils.paytime import paytime
from app.bots.partner_bot.keyboards.regular_keyboards import (
    show_dating_keyboard,
    show_location_keyboard,
    show_gender_keyboard,
)
from app.bots.partner_bot.routers.commands.partner_commands import show_main_menu
from app.bots.partner_bot.translations import (
    MESSAGES,
    QUESTIONARY,
    BUTTONS,
    TRANSCRIPTIONS,
)
from app.bots.partner_bot.utils.exc_handlers import nickname_exception_handler
from app.bots.partner_bot.utils.access_data import data_storage
from app.dependencies import get_db
from app.validators.validation import validate_name
from app.validators.exc import (
    EmptySpaceError,
    AlreadyExistsError,
    TooShortError,
    TooLongError,
    InvalidCharactersError,
)

from config import config
from logging_config import opt_logger as log


class PollingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_bday = State()
    waiting_for_intro = State()
    waiting_for_dating = State()
    waiting_for_gender = State()
    waiting_for_location = State()


# Инициализируем роутер
router = Router(name=__name__)

logger = log.setup_logger("registration_commands", config.LOG_LEVEL)


@router.message(and_f(Command("start", prefix="!/"), paytime))
async def start(message: Message, state: FSMContext):

    database = await get_db()

    if await database.check_profile_exists(message.from_user.id):
        return await show_main_menu(message, state)

    user_id = message.from_user.id

    user_data = await data_storage.get_storage_data(user_id=user_id, state=state)

    language = user_data.get("language")
    lang_code = user_data.get("lang_code")

    greeting = f"{MESSAGES['intro'][lang_code].format(language=TRANSCRIPTIONS["languages"][language][lang_code])}\n"
    await message.answer(text=greeting, parse_mode=ParseMode.HTML)

    # Обновляем user_id в состоянии
    await state.update_data(**user_data)
    # Отправляем приветственное сообщение
    txt = QUESTIONARY["need_profile"][lang_code]
    await message.answer(text=txt, parse_mode=ParseMode.HTML)
    # Переходим в состояние ожидания имени
    await state.set_state(PollingState.waiting_for_name)


@router.message(and_f(PollingState.waiting_for_name, paytime))
async def process_name(message: Message, state: FSMContext):

    database = await get_db()
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    try:
        if await validate_name(message.text, database):
            # Этот блок выполняется только если исключений не было
            msg = QUESTIONARY["need_age"][lang_code]
            await message.answer(text=msg, parse_mode=ParseMode.HTML)
            await state.update_data(name=message.text)
            await state.set_state(PollingState.waiting_for_bday)

    except (
        EmptySpaceError,
        AlreadyExistsError,
        TooShortError,
        TooLongError,
        InvalidCharactersError,
    ) as e:
        await nickname_exception_handler(message, state, e, lang_code)
        return state.set_state(PollingState.waiting_for_name)

    except Exception as e:
        await nickname_exception_handler(message, state, e, lang_code)
        return state.set_state(PollingState.waiting_for_name)


@router.message(and_f(PollingState.waiting_for_bday, paytime))
async def process_age(message: Message, state: FSMContext):
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


@router.message(and_f(PollingState.waiting_for_intro, paytime))
async def process_intro(message: Message, state: FSMContext):
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
    and_f(
        paytime,
        PollingState.waiting_for_dating,
        lambda message: message.text
        == BUTTONS["yes_to_dating"][message.from_user.language_code],
    )
)
async def agreed_to_dating_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    msg = QUESTIONARY["need_gender"][lang_code]
    await message.answer(
        text=msg,
        parse_mode=ParseMode.HTML,
        reply_markup=show_gender_keyboard(lang_code),
    )
    await state.set_state(PollingState.waiting_for_gender)
    return


@router.message(and_f(PollingState.waiting_for_gender, paytime))
async def process_gender(message: Message, state: FSMContext):
    database = await get_db()
    data = await state.get_data()
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id")
    name = data.get("name")
    birthday = datetime.strptime(data.get("bday", "01.01.1800"), "%d.%m.%Y").date()
    intro = data.get("intro")
    gender = message.text
    lang_code = data.get("lang_code")
    # Сохраняем профиль
    if gender in BUTTONS["cancel"].values():
        await database.add_users_profile(
            user_id=user_id, prefered_name=name, birthday=birthday, about=intro
        )
        await database.add_users_location(user_id=user_id)
        await message.answer(
            text=MESSAGES["no_worries_dating"][lang_code],
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    male_gens = BUTTONS["gender"]["male"]
    formated_gender = "male" if gender in male_gens.values() else "female"
    await database.add_users_profile(
        user_id=user_id,
        prefered_name=name,
        birthday=birthday,
        gender=formated_gender,
        about=intro,
        dating=True,
    )

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

    await message.answer(
        text="Ooops! Looks like you already have some info about you",
        reply_parameters=ReplyKeyboardRemove(),
    )
    await show_main_menu(message, state)


@router.message(
    and_f(
        PollingState.waiting_for_dating,
        paytime,
        lambda message: message.text
        == BUTTONS["no_to_dating"][message.from_user.language_code],
    )
)
async def disagreed_to_dating_handler(message: Message, state: FSMContext):
    database = await get_db()
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


@router.message(and_f(PollingState.waiting_for_location, F.location, paytime))
async def process_location(message: Message, state: FSMContext):
    """Обработчик локации"""
    database = await get_db()
    data = await state.get_data()
    user_id = data.get("user_id", 0)
    lang_code = data.get("lang_code", "en")

    # Сохраняем координаты в БД
    lattitude = str(message.location.latitude) or None
    longitude = str(message.location.longitude) or None
    city, country, tzone = None, None, None

    try:
        async with aiohttp.ClientSession() as session:
            url = config.GEO_API_URL.format(lattitude, longitude, config.GEO_API_KEY)
            headers = {"Content-Type": "application/json"}
            async with session.get(
                url=url, headers=headers, ssl=config.VERIFY_SSL
            ) as resp:

                if resp.status != 200:
                    return logger.warning("there was an issue with geo site")

                result: dict = await resp.json()
                formated_result = result["features"][0]["properties"]
                city = formated_result["city"]
                country = formated_result["country"]
                tzone = formated_result["timezone"]["name"]

                logger.debug("Exrtacting address from geo coordinates went successful")

    except Exception as e:
        logger.error(f"There was an error occuring: {e}")

    finally:
        await database.add_users_location(
            user_id, lattitude, longitude, city, country, tzone
        )
        # Выводим благодарное сообщение
        msg = MESSAGES["success"][lang_code]
        await message.answer(text=msg, reply_markup=ReplyKeyboardRemove())


@router.message(
    and_f(
        PollingState.waiting_for_location, paytime,
        lambda message: message.text == BUTTONS["cancel"].get(
            message.from_user.language_code, BUTTONS["cancel"]["en"]
        )
    )
)
async def cancel(message: Message):
    database = await get_db()
    msg = MESSAGES["no_worries"][message.from_user.language_code]
    await database.add_users_location(message.from_user.id, "refused", "refused")
    await message.reply(text=msg, reply_markup=ReplyKeyboardRemove())
