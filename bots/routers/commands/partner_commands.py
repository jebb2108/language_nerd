import re
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import KeyboardBuilder, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from aiogram.enums import ParseMode

from config import BOT_TOKEN_PARTNER # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa
from middlewares.rate_limit_middleware import RateLimitMiddleware, RateLimitInfo # noqa
from utils.filters import IsBotFilter # noqa

from translations import QUESTIONARY, BUTTONS, FIND_PARTNER # noqa

from keyboards.inline_keyboards import remove_keyboard # noqa

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))


class PollingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_bday = State()
    waiting_for_intro = State()
    waiting_for_location = State()

@router.message(Command("start"), IsBotFilter(BOT_TOKEN_PARTNER))
async def start(message: Message, state: FSMContext, database: ResourcesMiddleware):

    lang_code = message.from_user.language_code
    greeting = (
        f"{BUTTONS['hello'][lang_code]} <b>{message.from_user.first_name}</b>!\n\n"
        f"{FIND_PARTNER['intro'][lang_code]}"
    )
    if not await database.check_profile_exists(message.from_user.id):
        # Обновляем user_id в состоянии
        await state.update_data(user_id=message.from_user.id, lang_code=lang_code)
        # Отправляем приветственное сообщение
        txt = QUESTIONARY["need_profile"][lang_code]
        await message.answer(text=greeting+txt, parse_mode=ParseMode.HTML)
        # Переходим в состояние ожидания имени
        return await state.set_state(PollingState.waiting_for_name)


@router.message(PollingState.waiting_for_name, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_name(message: Message, state: FSMContext):

    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if (len(message.text) <= 50 and
            re.sub(r'\s', '', message.text) == message.text):
        await state.update_data(name=message.text)
        msg = QUESTIONARY["age"][lang_code]
        await message.answer(text=msg, parse_mode=ParseMode.HTML)
        return await state.set_state(PollingState.waiting_for_bday)

    msg = QUESTIONARY["wrong_name"][lang_code]
    await message.reply(msg, parse_mode=ParseMode.HTML)

@router.message(PollingState.waiting_for_bday, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_age(message: Message, state: FSMContext):

    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', message.text):
        date_obj = datetime.strptime(message.text, '%d.%m.%Y').date()
        await state.update_data(bday=date_obj)
        await message.answer(text=QUESTIONARY["need_intro"][lang_code], parse_mode=ParseMode.HTML)
        return await state.set_state(PollingState.waiting_for_intro)

    await message.answer(text=QUESTIONARY["wrong_birthday"][lang_code], parse_mode=ParseMode.HTML)


@router.message(PollingState.waiting_for_intro, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_intro(message: Message, state: FSMContext, database: ResourcesMiddleware):

    data = await state.get_data()
    lang_code = data.get("lang_code", "en")

    if re.search(r'\S{1,500}', message.text):
        # Достаем нужные данные о пользователе
        user_id = data.get("user_id", 0)
        name = data.get("name", "default")
        birthday = data.get("bday", "default")
        # Сохраняем профиль
        await database.add_users_profile(user_id, name, birthday, message.text)

        if not await database.check_location_exists(message.from_user.id):
            msg = QUESTIONARY["need_location"][lang_code]
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

            await message.answer(text=msg, parse_mode=ParseMode.HTML, reply_markup=markup)

            return await state.set_state(PollingState.waiting_for_location)

    await message.answer(text=QUESTIONARY["wrong_info"][lang_code], parse_mode=ParseMode.HTML)



@router.message(PollingState.waiting_for_location, F.location, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_location(message: Message, state: FSMContext, database: ResourcesMiddleware):
    if not await database.check_location_exists(message.from_user.id):
        lattitude = str(message.location.latitude)
        longitude = str(message.location.longitude)
        await database.add_users_location(message.from_user.id, lattitude, longitude)

        await message.answer(text='Thank you for your trust', reply_markup=ReplyKeyboardRemove())
        await state.clear()


@router.message(PollingState.waiting_for_location, IsBotFilter(BOT_TOKEN_PARTNER),
    lambda message: message.text == FIND_PARTNER["cancel"].get(
        message.from_user.language_code, FIND_PARTNER["cancel"]["en"])
)
async def cancel(message: Message, state: FSMContext, database: ResourcesMiddleware):
    if not await database.check_location_exists(message.from_user.id):
        msg = FIND_PARTNER["no_worries"][message.from_user.language_code]
        database.add_users_location(message.from_user.id, "refused", "refused")
        await message.reply(text=msg, reply_markup=ReplyKeyboardRemove())
        await state.clear()

@router.message(Command('location'), IsBotFilter(BOT_TOKEN_PARTNER))
async def get_my_location(message: Message, database: ResourcesMiddleware):
    result = await database.get_users_location(message.from_user.id)
    if result is None or result["latitude"] == "refused":
        await message.answer(text="You didn't share your location")
        return
    latitude = result['latitude']
    longitude = result['longitude']
    await message.answer(
        text=f"Your location: <b>{latitude}</b>, <b>{longitude}</b>",
        parse_mode=ParseMode.HTML,
    )

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
        reply_markup=remove_keyboard(),
    )
