import logging

from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from typing import Union
from translations import QUESTIONARY # noqa
from utils.filters import IsBotFilter # noqa
from utils.message_mgr import MessageManager # noqa
from config import BOT_TOKEN_MAIN, LOG_CONFIG # noqa
from routers.commands.menu_commands import show_main_menu  # переиспользуемый метод # noqa

from middlewares.resources_middleware import ResourcesMiddleware # noqa

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='start_commands')

# Инициализируем роутер
router = Router(name=__name__)

class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()

# Фильтрация по токену
router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))

@router.message(Command("start"), IsBotFilter(BOT_TOKEN_MAIN))
async def start_with_polling(
        message: Message,
        state: FSMContext,
        database: ResourcesMiddleware,
):
    """
    Стартовая команда: проверяем в БД существование пользователя,
    сохраняем основные поля в state и либо идём в show_main_menu, либо стартуем опрос.
    """
    db = database
    user_id = message.from_user.id
    lang_code = message.from_user.language_code or "en"

    # Создаем экземпляр класса MessageManager
    message_mgr = MessageManager(bot=message.bot, state=state)

    # Проверяем, есть ли запись в users
    try:
        async with db.acquire_connection() as conn:
            user_exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE user_id = $1", user_id
            )
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        user_exists = False

    # Обновляем данные в state
    await state.update_data(
        user_id=user_id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        lang_code=lang_code,
        chosen_language="",
        camefrom="",
        about="",
        messages_to_delete=[],
        message_mgr=message_mgr,
        db=database,
    )

    if user_exists:
        # если пользователь есть — сразу меню
        await show_main_menu(message, state, database)
        return

    # иначе запускаем опрос «откуда вы о нас узнали»
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}0"],
                callback_data="camefrom_friends"
            )
        ],
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}1"],
                callback_data="camefrom_search"
            )
        ],
        [
            InlineKeyboardButton(
                text=QUESTIONARY["where_youcamefrom"][f"{lang_code}2"],
                callback_data="camefrom_other"
            )
        ],
    ])


    await message_mgr.send_message_with_save(
        message=message,
        text=QUESTIONARY["intro"][lang_code],
        state=state,
        markup=True,
        keyboard=keyboard
    )
    await state.set_state(PollingStates.camefrom_state)


@router.callback_query(F.data.startswith("camefrom_"), PollingStates.camefrom_state)
async def handle_camefrom(
        callback: CallbackQuery,
        state: FSMContext,
):
    """
    После вопроса «откуда узнали» переходим к выбору языка.
    """
    try:
        camefrom = callback.data.split("_", 1)[1]
        await state.update_data(camefrom=camefrom)

        data = await state.get_data()
        lang_code = data.get("lang_code", "en")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_russian")],
            [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_english")],
            [InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_german")],
            [InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_spanish")],
            [InlineKeyboardButton(text="🇨🇳 中文", callback_data="lang_chinese")],
        ])

        data = await state.get_data()
        msg_mgr = data["message_mgr"]

        await msg_mgr.send_message_with_save(
            message=callback,
            text=QUESTIONARY["lang_pick"][lang_code],
            state=state,
            markup=True,
            keyboard=keyboard
        )
        await state.set_state(PollingStates.language_state)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in handle_camefrom: {e}")


@router.callback_query(F.data.startswith("lang_"), PollingStates.language_state)
async def handle_language_choice(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware,
):

    """
    Сохраняем выбор языка, создаём запись в БД и идём в главное меню.
    """
    data = await state.get_data()
    lang_code = data.get("lang_code", "en")
    user_id = data["user_id"]
    username = data.get("username", "")
    first_name = data.get("first_name", "")
    camefrom = data.get("camefrom", "")

    users_choice = callback.data.split("_", 1)[1]

    # Обновляем текст с подтверждением выбора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=QUESTIONARY["confirm"][lang_code],
            callback_data="action_confirm"
        )]
    ])

    await callback.message.edit_text(
        f"➪ Вы выбрали: {users_choice}\n\n{QUESTIONARY['gratitude'][lang_code]}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
    try:

        # Сохраняем нового пользователя в БД
        async with database.acquire_connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, camefrom, language, lang_code)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                user_id, username, first_name, camefrom, users_choice, lang_code
            )

    except Exception as e:
        logger.error(f"Error in passing user to DB: {e}")

    finally:
        await state.set_state(PollingStates.introduction_state)

@router.callback_query(F.data == "action_confirm", PollingStates.introduction_state)
async def go_to_main_menu(
        callback: CallbackQuery,
        state: FSMContext,
        database: ResourcesMiddleware
):
    data = await state.get_data()
    message_mgr = data["message_mgr"]

    await message_mgr.delete_previous_messages(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        state=state,
    )
    await state.clear()
    # После сохранения сразу показываем главное меню
    await show_main_menu(callback.message, state, database)