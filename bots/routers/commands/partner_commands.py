from sys import prefix

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import KeyboardBuilder, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from aiogram.enums import ParseMode

from config import BOT_TOKEN_PARTNER # noqa
from middlewares.resources_middleware import ResourcesMiddleware # noqa
from middlewares.rate_limit_middleware import RateLimitMiddleware, RateLimitInfo # noqa
from utils.filters import IsBotFilter # noqa

from translations import QUESTIONARY, BUTTONS, FIND_PARTNER # noqa

from bots.keyboards.inline_keyboards import remove_keyboard

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))


@router.message(Command("start"), IsBotFilter(BOT_TOKEN_PARTNER))
async def start(message: Message, database: ResourcesMiddleware):

    lang_code = message.from_user.language_code
    greeting = f"{BUTTONS['hello'][lang_code]} <b>{message.from_user.first_name}</b>!\n\n"

    markup, txt = None, ''
    if not await database.check_location_exists(message.from_user.id):

        txt = QUESTIONARY["need_location"][lang_code]
        share_button = KeyboardButton(
            text=QUESTIONARY["share_location"][lang_code],
            request_location=True,
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
            one_time_keyboard=True,
        )

    await message.answer(text=greeting+txt, parse_mode=ParseMode.HTML, reply_markup=markup)

@router.message(Command('location'), prefix='!/')
@router.message(IsBotFilter(BOT_TOKEN_PARTNER))
async def get_my_location(message: Message, database: ResourcesMiddleware):
    result = await database.get_users_location(message.from_user.id)
    if result is None or result[0] == "refused":
        await message.answer(text="You didn't share your location")
        return
    lattitude = result['lattitude']
    longitude = result['longitude']
    await message.answer(
        text=f"Your location: <b>{lattitude}</b>, <b>{longitude}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=remove_keyboard()
    )


@router.message(F.location, IsBotFilter(BOT_TOKEN_PARTNER))
async def process_location(message: Message, database: ResourcesMiddleware):
    if not await database.check_location_exists(message.from_user.id):
        lattitude = str(message.location.latitude)
        longitude = str(message.location.longitude)
        database.add_users_location(message.from_user.id, lattitude, longitude)

        await message.answer(text='Thank you for your trust.', reply_markup=remove_keyboard())

@router.message(
    lambda message: message.text == FIND_PARTNER["cancel"].get(
        message.from_user.language_code, FIND_PARTNER["cancel"]["en"]), 
        IsBotFilter(BOT_TOKEN_PARTNER)
)
async def cancel(message: Message, database: ResourcesMiddleware):
    if not await database.check_location_exists(message.from_user.id):
        msg = FIND_PARTNER["no_worries"][message.from_user.language_code]
        database.add_users_location(message.from_user.id, "refused", "refused")
        await message.reply(text=msg, reply_markup=remove_keyboard())

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
