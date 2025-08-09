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
from config import BOT_TOKEN_MAIN, logger # noqa
from routers.commands.menu_commands import show_main_menu  # переиспользуемый метод # noqa

from middlewares.resources_middleware import ResourcesMiddleware # noqa

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
        resources: ResourcesMiddleware,
):
    """
    Стартовая команда: проверяем в БД существование пользователя,
    сохраняем основные поля в state и либо идём в show_main_menu, либо стартуем опрос.
    """
    db_pool = resources.db_pool
    user_id = message.from_user.id
    lang_code = message.from_user.language_code or "en"

    # Проверяем, есть ли запись в users
    try:
        async with db_pool.acquire() as conn:
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
        db_pool=db_pool,
    )

    if user_exists:
        # если пользователь есть — сразу меню
        await show_main_menu(message, state)
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

    await send_message_with_save(
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

        await send_message_with_save(
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
):
    """
    Сохраняем выбор языка, создаём запись в БД и идём в главное меню.
    """
    try:
        data = await state.get_data()
        lang_code = data.get("lang_code", "en")
        user_id = data["user_id"]
        username = data.get("username", "")
        first_name = data.get("first_name", "")
        camefrom = data.get("camefrom", "")
        db_pool = data.get("db_pool")

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
        await state.set_state(PollingStates.introduction_state)
        await callback.answer()

        # Сохраняем нового пользователя в БД
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, camefrom, chosen_language, lang_code)
                VALUES ($1,$2,$3,$4,$5,$6)
                """,
                user_id, username, first_name, camefrom, users_choice, lang_code
            )

        # После сохранения сразу показываем главное меню
        await show_main_menu(callback.message, state)

    except Exception as e:
        logger.error(f"Error in handle_language_choice: {e}")


async def send_message_with_save(
        message: Union[Message, CallbackQuery],
        text: str,
        state: FSMContext,
        markup: bool = False,
        keyboard: InlineKeyboardMarkup = None,
):
    """
    Отправляет (или редактирует) сообщение, сохраняет его ID в state для последующего удаления.
    """
    if isinstance(message, CallbackQuery):
        chat_msg = message.message
    else:
        chat_msg = message

    if markup and keyboard:
        sent = await chat_msg.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        sent = await chat_msg.answer(text=text)

    data = await state.get_data()
    msgs = data.get("messages_to_delete", [])
    msgs.append(sent.message_id)
    await state.update_data(messages_to_delete=msgs)
    return sent


async def delete_previous_messages(
        bot: Bot,
        chat_id: int,
        state: FSMContext
):
    data = await state.get_data()
    for msg_id in data.get("messages_to_delete", []):
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    await state.update_data(messages_to_delete=[])
