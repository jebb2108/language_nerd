import re
from datetime import datetime
from logging import Filter

import aiohttp
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from app.bots.main_bot.utils.paytime import paytime
from app.bots.partner_bot.filters.answers import AnswerFilter

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
from app.bots.partner_bot.utils.access_data import data_storage as ds
from app.dependencies import get_db, get_rabbitmq
from app.models import Location, UserProfile
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
    # Извлекаем данные о пользователе
    user_id = message.from_user.id
    user_data = await ds.get_storage_data(user_id, state)
    language = user_data.get("language")
    lang_code = user_data.get("lang_code")
    # Пишем сообщение пользоватеою в ТГ
    greeting = f"{MESSAGES['intro'][lang_code].format(language=TRANSCRIPTIONS["languages"][language][lang_code])}\n"
    await message.answer(text=greeting, parse_mode=ParseMode.HTML)
    # Обновляем user_id в состоянии
    await state.update_data(**user_data)
    # Отправляем приветственное сообщение
    txt = QUESTIONARY["need_profile"][lang_code]
    await message.answer(text=txt, parse_mode=ParseMode.HTML)
    # Переходим в состояние ожидания имени
    return await state.set_state(PollingState.waiting_for_name)


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
            await state.update_data(nickname=message.text)
            return await state.set_state(PollingState.waiting_for_bday)

    except (
        EmptySpaceError,
        AlreadyExistsError,
        TooShortError,
        TooLongError,
        InvalidCharactersError,
    ) as e:
        await nickname_exception_handler(message, state, e, lang_code)
        return await state.set_state(PollingState.waiting_for_name)

    except Exception as e:
        await nickname_exception_handler(message, state, e, lang_code)
        return await state.set_state(PollingState.waiting_for_name)


@router.message(and_f(PollingState.waiting_for_bday, paytime))
async def process_age(message: Message, state: FSMContext):

    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    users_year = int(message.text.split(".")[2])
    this_year = datetime.now(tz=config.TZINFO).date().year
    # Проверям, чтобы возраст был валидным
    if this_year >= users_year >= 1900:
        if re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", message.text):
            try:
                datetime.strptime(message.text, "%d.%m.%Y")
                await state.update_data(bday=message.text)
                await message.answer(
                    text=QUESTIONARY["need_intro"][lang_code], parse_mode=ParseMode.HTML
                )
                return await state.set_state(PollingState.waiting_for_intro)

            except ValueError:
                pass

    msg = MESSAGES["wrong_birthday"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)
    return await state.set_state(PollingState.waiting_for_bday)


@router.message(and_f(PollingState.waiting_for_intro, paytime))
async def process_intro(message: Message, state: FSMContext):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    # Проверяем, чтобы сообщение было в диапозоне 500 символов
    if re.search(r"\S{10,500}", message.text):
        msg = QUESTIONARY["need_dating"][lang_code]
        await message.answer(
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=show_dating_keyboard(lang_code),
        )
        await state.update_data(about=message.text)
        return await state.set_state(PollingState.waiting_for_dating)

    msg = MESSAGES["wrong_intro"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)
    return await state.set_state(PollingState.waiting_for_intro)


@router.message(
    and_f(AnswerFilter("disagreed"), PollingState.waiting_for_dating, paytime)
)
async def disagreed_to_dating_handler(message: Message, state: FSMContext):
    """Обработчик отказа от дейтинга"""

    # Извлекаем данные из состояния
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    # DD.MM.YYYY -> YYYY-MM-DD
    formated_bday = datetime.strptime(data.get("bday"), "%d.%m.%Y").date().isoformat()

    # Публикуем профиль в RabbitMQ
    rabbit = await get_rabbitmq()
    await rabbit.publish_profile(
        UserProfile(
            user_id=data.get("user_id"),
            nickname=data.get("nickname"),
            about=data.get("about"),
            birthday=formated_bday,
        )
    )
    # Отправляем сообщение пользователю в ТГ
    msg = MESSAGES["no_worries_dating"][lang_code]
    await message.answer(
        text=msg, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove()
    )
    return await state.clear()


@router.message(and_f(AnswerFilter("agreed"), PollingState.waiting_for_dating, paytime))
async def agreed_to_dating_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    msg = QUESTIONARY["need_gender"][lang_code]
    await message.answer(
        text=msg,
        parse_mode=ParseMode.HTML,
        reply_markup=show_gender_keyboard(lang_code),
    )
    return await state.set_state(PollingState.waiting_for_gender)



@router.message(and_f(PollingState.waiting_for_gender, paytime))
async def process_gender(message: Message, state: FSMContext):

    rabbit = await get_rabbitmq()
    data = await state.get_data()

    # Достаем нужные данные о пользователе
    lang_code = data.get("lang_code")
    formated_bday = datetime.strptime(data.get("bday"), "%d.%m.%Y").date().isoformat()

    if message.text in BUTTONS["cancel"].values():
        # Публикуем сообщения в RabbitMQ
        await rabbit.publish_profile(
            UserProfile(
                user_id=data.get("user_id"),
                nickname=data.get("nickname"),
                about=data.get("about"),
                birthday=formated_bday,
            )
        )
        await rabbit.publish_location(Location(user_id=data.get("user_id")))
        # Пишем сообщение в ТГ
        await message.answer(
            text=MESSAGES["no_worries_dating"][lang_code],
            reply_markup=ReplyKeyboardRemove(),
        )

        return await state.clear()

    formated_gender = (
        "male" if message.text == BUTTONS["gender"]["male"][lang_code] else "female"
    )
    await state.update_data(gender=formated_gender)

    await rabbit.publish_profile(
        UserProfile(
            user_id=data.get("user_id"),
            nickname=data.get("nickname"),
            gender=formated_gender,
            birthday=formated_bday,
            about=data.get("about"),
            dating=True
        )
    )

    msg = QUESTIONARY["need_location"][lang_code]
    await message.answer(
        text=msg,
        parse_mode=ParseMode.HTML,
        reply_markup=show_location_keyboard(lang_code),
    )

    return await state.set_state(PollingState.waiting_for_location)


@router.message(and_f(PollingState.waiting_for_location, F.location, paytime))
async def process_location(message: Message, state: FSMContext):
    """Обработчик локации"""
    data = await state.get_data()
    user_id = data.get("user_id", 0)
    lang_code = data.get("lang_code", "en")

    # Сохраняем координаты в БД
    latitude = str(message.location.latitude) or None
    longitude = str(message.location.longitude) or None

    try:
        async with aiohttp.ClientSession() as session:
            url = config.GEO_API_URL.format(latitude, longitude, config.GEO_API_KEY)
            headers = {"Content-Type": "application/json"}
            async with session.get(
                url=url, headers=headers, ssl=config.VERIFY_SSL
            ) as resp:

                if resp.status != 200:
                    return logger.warning("there was an issue with geo site")

                else:
                    result: dict = await resp.json()
                    formated_result = result["features"][0]["properties"]
                    city = formated_result["city"]
                    country = formated_result["country"]
                    tzone = formated_result["timezone"]["name"]

                    logger.debug(
                        "Exrtacting address from geo coordinates went successful"
                    )

                    rabbit = await get_rabbitmq()
                    await rabbit.publish_location(
                        Location(
                            user_id=user_id,
                            latitude=latitude,
                            longitude=longitude,
                            city=city,
                            country=country,
                            tzone=tzone,
                        )
                    )
                    # Выводим благодарное сообщение
                    msg = MESSAGES["success"][lang_code]
                    await message.answer(text=msg, reply_markup=ReplyKeyboardRemove())

                    logger.debug("Published users geo & personal data 2 rabbitmq")
                    return await state.clear()

    except Exception as e:
        logger.error(f"There was an error occuring: {e}")


@router.message(
    and_f(PollingState.waiting_for_location, paytime)
)
async def cancel(message: Message, state: FSMContext):

    rabbit = await get_rabbitmq()
    data = await state.get_data()
    msg = MESSAGES["no_worries"][data.get("lang_code")]

    # Публикую сообщение с локацией пользователя
    await rabbit.publish_location(Location(user_id=message.from_user.id))
    await message.reply(text=msg, reply_markup=ReplyKeyboardRemove())
    return await state.clear()