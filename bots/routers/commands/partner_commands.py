import logging
import re
from json import dumps

import aiohttp
import asyncio
import json
from datetime import datetime, time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
from aiogram.enums import ParseMode

from config import BOT_TOKEN_PARTNER # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa
from middlewares.rate_limit_middleware import RateLimitMiddleware, RateLimitInfo # noqa
from utils.filters import IsBotFilter # noqa

from translations import QUESTIONARY, BUTTONS, FIND_PARTNER # noqa
from config import LOG_CONFIG # noqa

from keyboards.inline_keyboards import show_partner_menu_keyboard, open_chat_keyboard # noqa
from keyboards.regular_keyboards import show_location_keyboard, show_dating_keyboard # noqa

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='partner_commands')


class PollingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_bday = State()
    waiting_for_intro = State()
    waiting_for_dating = State()
    waiting_for_location = State()

class SearchStates(StatesGroup):
    waiting_for_criteria = State()

@router.message(Command("menu"), IsBotFilter(BOT_TOKEN_PARTNER))
async def show_main_menu(message: Message, state: FSMContext, database: ResourcesMiddleware):
    """ Главное меню бота """
    data = await get_state_data(message, state, database)
    name = data.get("name")
    lang_code = data.get("lang_code")

    greeting = FIND_PARTNER["hello"][lang_code] + " <b>" + name + "</b>!"
    intro = FIND_PARTNER["intro"][lang_code]
    await state.update_data(
        lang_code=lang_code,
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
    )
    await message.answer(
        text=greeting + "\n\n" + intro,
        parse_mode=ParseMode.HTML,
        reply_markup=show_partner_menu_keyboard(lang_code)
    )

@router.message(Command("start"), IsBotFilter(BOT_TOKEN_PARTNER))
async def start(message: Message, state: FSMContext, database: ResourcesMiddleware):

    if await database.check_profile_exists(message.from_user.id):
        await show_main_menu(message, state, database)

    user_id = message.from_user.id
    lang_code = message.from_user.language_code
    greeting = (
        f"{BUTTONS['hello'][lang_code]} <b>{message.from_user.first_name}</b>!\n\n"
        f"{FIND_PARTNER['intro'][lang_code]}\n"
    )
    await message.answer(text=greeting, parse_mode=ParseMode.HTML)
    if not await database.check_profile_exists(user_id):
        # Обновляем user_id в состоянии
        await state.update_data(user_id=user_id, lang_code=lang_code)
        # Отправляем приветственное сообщение
        txt = QUESTIONARY["need_profile"][lang_code]
        await message.answer(text=txt, parse_mode=ParseMode.HTML)
        # Переходим в состояние ожидания имени
        return await state.set_state(PollingState.waiting_for_name)


@router.message(PollingState.waiting_for_name, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_name(message: Message, state: FSMContext, database: ResourcesMiddleware):

    data = await get_state_data(message, state, database)
    lang_code = data.get("lang_code", "en")

    if (len(message.text) <= 50 and
            re.sub(r'\s', '', message.text) == message.text):
        await state.update_data(name=message.text)
        msg = QUESTIONARY["age"][lang_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return await state.set_state(PollingState.waiting_for_bday)

    msg = QUESTIONARY["wrong_name"][lang_code]
    await message.reply(text=msg, parse_mode=ParseMode.HTML)

@router.message(PollingState.waiting_for_bday, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_age(message: Message, state: FSMContext, database: ResourcesMiddleware):

    data = await get_state_data(message, state, database)
    lang_code = data.get("lang_code", "en")

    if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', message.text):
        date_obj = datetime.strptime(message.text, '%d.%m.%Y').date()
        await state.update_data(bday=date_obj)
        await message.answer(text=QUESTIONARY["need_intro"][lang_code], parse_mode=ParseMode.HTML)
        return await state.set_state(PollingState.waiting_for_intro)

    msg = QUESTIONARY["wrong_birthday"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)


@router.message(PollingState.waiting_for_intro, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_intro(message: Message, state: FSMContext, database: ResourcesMiddleware):

    data = await get_state_data(message, state, database)
    lang_code = data.get("lang_code", "en")

    if re.search(r'\S{10,500}', message.text):
        msg = QUESTIONARY["need_dating"][lang_code]
        await message.answer(
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=show_dating_keyboard(lang_code),
        )
        await state.update_data(intro=message.text)
        return await state.set_state(PollingState.waiting_for_dating)

    msg = QUESTIONARY["wrong_intro"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML)


@router.message(
    PollingState.waiting_for_dating, IsBotFilter(BOT_TOKEN_PARTNER),
    lambda message: message.text == FIND_PARTNER["yes_to_dating"][message.from_user.language_code]
)
async def agreed_to_dating_handler(message: Message, state: FSMContext, database: ResourcesMiddleware):
    data = await get_state_data(message, state, database)
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id", 0)
    name = data.get("name", "default")
    birthday = data.get("bday", None)
    intro = data.get("intro", "non-existent")
    lang_code = data.get("lang_code", "en")
    # Сохраняем профиль
    await database.add_users_profile(user_id, name, birthday, about=intro, dating=True)

    location_exists: bool = await database.check_location_exists(user_id)
    if not location_exists:
        msg = QUESTIONARY["need_location"][lang_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML, reply_markup=show_location_keyboard(lang_code))
        return await state.set_state(PollingState.waiting_for_location)

    # Если локация каким-то образом существует, то переходим в главное меню
    else: await show_main_menu(message, state, database)

@router.message(
    PollingState.waiting_for_dating, IsBotFilter(BOT_TOKEN_PARTNER),
    lambda message: message.text == FIND_PARTNER["no_to_dating"][message.from_user.language_code]
)
async def disagreed_to_dating_handler(message: Message, state: FSMContext, database: ResourcesMiddleware):
    data = await get_state_data(message, state, database)
    # Достаем нужные данные о пользователе
    user_id = data.get("user_id", 0)
    name = data.get("name", "default")
    birthday = data.get("bday", None)
    intro = data.get("intro", "non-existent")
    lang_code = data.get("lang_code", "en")
    # Сохраняем профиль
    await database.add_users_profile(user_id, name, birthday, about=intro)
    msg = FIND_PARTNER["no_worries_dating"][lang_code]
    await message.answer(text=msg, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())


@router.message(PollingState.waiting_for_location, F.location, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_location(message: Message, state: FSMContext, database: ResourcesMiddleware):
    """Обработчик локации"""
    data = await get_state_data(message, state, database)
    user_id = data.get("user_id", 0)
    lang_code = data.get("lang_code", "en")
    # Сохраняем координаты в БД
    lattitude = str(message.location.latitude)
    longitude = str(message.location.longitude)
    await database.add_users_location(user_id, lattitude, longitude)
    # Выводим благодарное сообщение
    msg = FIND_PARTNER["success"][lang_code]
    await message.answer(text=msg, reply_markup=ReplyKeyboardRemove())


@router.message(PollingState.waiting_for_location, IsBotFilter(BOT_TOKEN_PARTNER),
    lambda message: message.text == FIND_PARTNER["cancel"].get(
        message.from_user.language_code, FIND_PARTNER["cancel"]["en"])
)
async def cancel(message: Message, state: FSMContext, database: ResourcesMiddleware):
    msg = FIND_PARTNER["no_worries"][message.from_user.language_code]
    await database.add_users_location(message.from_user.id, "refused", "refused")
    await message.reply(text=msg, reply_markup=ReplyKeyboardRemove())

@router.message(Command('location'), IsBotFilter(BOT_TOKEN_PARTNER))
async def get_my_location(message: Message, database: ResourcesMiddleware):
    """ Обработчик команды /location """
    lang_code = message.from_user.language_code
    result = await database.get_users_location(message.from_user.id)
    if result is None or result["latitude"] == "refused":
        await message.answer(text="You didn't share your location")
        return
    latitude = result['latitude']
    longitude = result['longitude']

    msg = FIND_PARTNER["your_location"][lang_code]
    await message.answer(
        text=f"{msg}: <b>{latitude}</b>, <b>{longitude}</b>",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("new_session"), IsBotFilter(BOT_TOKEN_PARTNER))
async def new_session_handler(
        message: Message,
        state: FSMContext,
        redis: ResourcesMiddleware,
        http_session: ResourcesMiddleware,
        database: ResourcesMiddleware
):
    """Обработчик команды /new_session - запускает поиск партнера"""
    data = await get_state_data(message, state, database)
    user_id = data.get("user_id", 0)
    username = data.get("username", "")
    language = data.get("language")

    if username == "NO USERNAME":
        msg = FIND_PARTNER["no_username"][message.from_user.language_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return

    # Отменяем предыдущий поиск, если он был
    active_tasks = await redis.get(f"active_search_tasks:{user_id}")
    if active_tasks and user_id in active_tasks:
        await redis.delete(f"active_search_tasks:{user_id}")
        logger.info(f"Отменен предыдущий поиск для пользователя {user_id}")

    # Показываем сообщение о начале поиска
    search_message = await message.answer(
        f"🔍 Ищем партнера для общения на <b>{language}</b>...",
        parse_mode=ParseMode.HTML
    )

    # Формируем критерии поиска
    criteria = {
        "language": language,
    }

    # Запускаем поиск партнера
    task = asyncio.create_task(
        find_partner_and_notify(user_id, username, criteria, search_message, redis, http_session)
    )

    await redis.setex(f"searching_users:{user_id}", 210, json.dumps({"user_id": user_id, "criteria": str(language), "task": str(task)}))


async def find_partner_and_notify(user_id, username, criteria, message, redis, session):
    """Фоновая задача для поиска партнера и уведомления пользователя"""
    try:
        async with session.post(
                'http://localhost:4000/api/generate_link',
                json={
                    "user_id": str(user_id),
                    "username": username,
                    "criteria": criteria
                }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()

                if data.get("status") == "found":
                    # Партнер найден сразу
                    link = data["link"]
                    await message.edit_text(
                        "✅ Партнер найден! Нажмите кнопку чтобы начать общение:",
                        reply_markup=open_chat_keyboard('ru', link)
                    )
                else:
                    # Запускаем периодическую проверку статуса
                    await check_search_status_periodically(user_id, message, redis, session)
            else:
                await message.edit_text(
                    "❌ Произошла ошибка при поиске партнера. Попробуйте позже."
                )

            # Удаляем задачу из активных
            active_tasks = await redis.get(f"active_search_tasks:{user_id}")
            if active_tasks and user_id in active_tasks:
                await redis.delete(f"active_search_tasks:{user_id}")



    except Exception as e:
        logger.error(f"Ошибка при поиске партнера: {e}")
        await message.edit_text("❌ Произошла ошибка при поиске партнера. Попробуйте позже.")

    finally:
        # Удаляем задачу из активных
        active_tasks = await redis.get(f"active_search_tasks:{user_id}")
        if active_tasks and user_id in active_tasks:
            await redis.delete(f"active_search_tasks:{user_id}")


async def check_search_status_periodically(user_id, message, redis, session, interval=5, max_checks=30):
    """Периодическая проверка статуса поиска (до 2.5 минут)"""
    # async with aiohttp.ClientSession() as session:
    for i in range(max_checks):

        # Проверяем, не была ли задача отменена
        active_tasks = await redis.get(f"active_search_tasks:{user_id}")
        if active_tasks and user_id in active_tasks:
            return

        async with session.get(
                f'http://localhost:4000/api/search_status/{user_id}'
        ) as resp:
            if resp.status == 200:
                data = await resp.json()

                if data.get("status") == "found":
                    # Партнер найден
                    link = data["link"]
                    await message.edit_text(
                        "✅ Партнер найден! Нажмите кнопку чтобы начать общение:",
                        reply_markup=open_chat_keyboard("en", link)
                    )
                    return
                # Обновляем статус поиска каждые 15 секунд
                elif i % 3 == 0:
                    t = ['', str(i * 5) + ' сек'] if i * 5 < 60 else [str(i * 5 // 60) + ' мин ',
                                                                      str(i * 5 % 60) + ' сек']
                    result = ''.join(t if t[1] != '0 сек' else t[0])
                    await message.edit_text(
                        f"🔍 Ищем подходящего партнера...\n\n Время ожидания: {result if result else 'только что'} "
                    )

                await asyncio.sleep(interval)

            else:
                logger.error(f"Ошибка HTTP при проверке статуса: {resp.status}")


    # Если партнер не найден после всех попыток
    await message.edit_text("❌ К сожалению, не удалось найти подходящего партнера :(")



@router.message(IsBotFilter(BOT_TOKEN_PARTNER))
async def echo(message: Message, rate_limit_info: RateLimitInfo):
    # Убираем кнопки после любого сообщения

    if message.text:
        await message.copy_to(message.chat.id)
    count = rate_limit_info.message_count
    first_message = rate_limit_info.last_message_time
    await message.reply(
        text=f"Your message: {message.text}\n"
        f"Rate limit info: {count} messages at {first_message}",
    )


async def set_user_info(message: Message, state: FSMContext, database: ResourcesMiddleware):
    """ Гарантирует, что машина состояние имеет все данные о пользователе """
    user_id = message.from_user.id

    if await database.check_user_exists(user_id):
        user_info = await database.get_user_info(user_id)
        username = user_info["username"]
        language = user_info["language"]
        fluency = user_info["fluency"]
        lang_code = user_info["lang_code"]
        if await database.check_profile_exists(user_id):
            users_profile_info = await database.get_users_profile(user_id)
            prefered_name = users_profile_info["prefered_name"]
            birthday = users_profile_info["birthday"]
            age_delta = datetime.now() - datetime.combine(birthday, time.min)
            age_years = age_delta.days // 365
            status = users_profile_info["status"]
            about = users_profile_info["about"]

            await state.update_data(
                user_id=user_id,
                username=username,
                age=age_years,
                name=prefered_name,
                language=language,
                fluency=fluency,
                status=status,
                about=about,
                lang_code=lang_code,
            )
            return

        prefered_name = user_info["first_name"]
        await state.update_data(
            user_id=user_id,
            name=prefered_name,
            status='unknown',
            language=language,
            fluency=fluency,
            about='non-existent',
            lang_code=lang_code,
        )
        return


async def get_state_data(message: Message, state: FSMContext, database: ResourcesMiddleware):
    """Достаем нужные данные о пользователе"""
    data = await state.get_data()
    if data.get("user_id", None) != message.from_user.id:
        await set_user_info(message, state, database)
        return await state.get_data()

    return await state.get_data()