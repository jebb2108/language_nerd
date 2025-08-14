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

# Инициализируем роутер
router = Router(name=__name__)

# Фильтрация по токену
# router.message.filter(IsBotFilter(BOT_TOKEN_PARTNER))
# router.callback_query.filter(IsBotFilter(BOT_TOKEN_PARTNER))


@router.message(Command("start"))
async def start(message: Message, database: ResourcesMiddleware):

    lang_code = message.from_user.language_code
    greeting = f"{BUTTONS['hello'][lang_code]} <b>{message.from_user.first_name}</b>!\n\n"

    markup, txt = None, ''
    if not database.check_user_exists(message.from_user.id):
        builder = KeyboardBuilder(button_type=KeyboardButton)
        txt = QUESTIONARY["need_location"][lang_code]
        share_button = KeyboardButton(
            text=QUESTIONARY["share_location"][lang_code]
        )
        cancel_button = KeyboardButton(
            text=FIND_PARTNER["cancel"][lang_code]
        )
        builder.row(share_button)  # Добавление кнопок рядами
        builder.row(cancel_button)
        markup = builder.as_markup(resize_keyboard=True)

    await message.answer(
        text=greeting+txt,
        parse_mode=ParseMode.HTML,
        reply_markup=markup
    )

@router.message(F.location)
async def process_location(message: Message):
    lattitude = str(message.location.latitude)
    longitude = str(message.location.longitude)
    db.add_users_location(message.from_user.id, lattitude, longitude)
    await message.answer('Thank you for your trust.')

@router.message(lambda message: message.text == FIND_PARTNER["cancel"].get(message.from_user.language_code, FIND_PARTNER["cancel"]["en"]), IsBotFilter(BOT_TOKEN_PARTNER))
async def cancel(message: Message):
    msg = FIND_PARTNER["no_worries"][message.from_user.language_code]
    await message.reply(text=msg)

@router.message()
async def echo(message: Message, rate_limit_info: RateLimitInfo):
    # Убираем кнопки после любого сообщения
    remove_keyboard = ReplyKeyboardMarkup(
        keyboard=[],
        resize_keyboard=True,
        remove_keyboard=True
    )

    if message.text:
        await message.copy_to(message.chat.id)
    count = rate_limit_info.message_count
    first_message = rate_limit_info.last_message_time
    await message.reply(
        text=f"Your message: {message.text}\n"
        f"Rate limit info: {count} messages at {first_message}",
        reply_markup=remove_keyboard,
    )
