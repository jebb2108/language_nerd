from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from typing import Union

from translations import QUESTIONARY  # noqa
from filters import IsBotFilter  # noqa
from routers.commands.menu_commands import show_main_menu  # noqa
from config import BOT_TOKEN_MAIN, logger, Resources  # Импортируем Resources здесь! # noqa

router = Router(name=__name__)
# Фильтрация по токену

router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))


class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()


@router.message(Command("start"), IsBotFilter(BOT_TOKEN_MAIN))
async def start_with_polling(message: Message, state: FSMContext, data: dict):
    # Получаем resources из диспетчера
    resources: Resources = data["resources"]
    db_pool = resources.db_pool

    if not resources:
        logger.error("Resources not found in start handler")
        return

    user_id = message.from_user.id
    user_exists = False
    lang_code = message.from_user.language_code or "en"

    try:
        # Проверяем существование пользователя в БД
        async with db_pool.acquire() as conn:  # noqa
            user_exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE user_id = $1",
                user_id
            )

        # Обновляем состояние с инициализированным lang_code
        await state.update_data(
            user_id=user_id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "",
            lang_code=lang_code,  # Используем уже инициализированное значение
            chosen_language="",
            camefrom="",
            about=""
        )

    except Exception as e:
        logger.error(f"Error in start handler: {e}")  # noqa

    # Если пользователь существует - показываем главное меню
    if user_exists:
        await show_main_menu(message, state)
        return

    # Создаем безопасные callback-данные
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
        ]
    ])
    # Отправляю через функцию с сохранением ID сообщения
    await send_message_with_save(message, QUESTIONARY["intro"][lang_code], state, True, keyboard)
    await state.set_state(PollingStates.camefrom_state)


@router.callback_query(F.data.startswith("camefrom_"), PollingStates.camefrom_state)
async def handle_camefrom(callback: CallbackQuery, state: FSMContext):
    try:
        camefrom = callback.data.split("_")[1]
        await state.update_data(camefrom=camefrom)

        data = await state.get_data()
        lang_code = data.get('lang_code', 'en')

        # Кнопки выбора языка с простыми callback-данными
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_russian"),
            ],
            [
                InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_english")
            ],
            [
                InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_german"),
            ],
            [
                InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_spanish")
            ],
            [
                InlineKeyboardButton(text="🇨🇳 中文", callback_data="lang_chineese")
            ]
        ])

        await send_message_with_save(callback, QUESTIONARY["lang_pick"][lang_code], state, True, keyboard)
        await state.set_state(PollingStates.language_state)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in camefrom handler: {e}")  # noqa


@router.callback_query(F.data.startswith("lang_"), PollingStates.language_state)
async def handle_language_choice(callback: CallbackQuery, state: FSMContext, data: dict):

    # Получаем resources из диспетчера
    resources: Resources = data["resources"]
    db_pool = resources.db_pool

    if not resources:
        logger.error("Resources not found in language choice handler")
        return

    try:
        state_data = await state.get_data()
        lang_code = state_data.get('lang_code', 'en')

        # Кнопка подтверждения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=QUESTIONARY["confirm"][lang_code],
                callback_data="action_confirm"
            )]
        ])

        users_choice = callback.data.split("_")[1]

        await callback.message.edit_text(
            text=f"➪ Вы выбрали: {users_choice}\n\n{QUESTIONARY['gratitude'][lang_code]}",
            reply_markup=keyboard
        )
        await state.set_state(PollingStates.introduction_state)
        await callback.answer()

        # Сохраняем пользователя в БД
        user_id = state_data['user_id']
        username = state_data.get('username', 'None')
        first_name = state_data.get('first_name', 'None')
        camefrom = state_data.get('camefrom', 'None')

        # Используем ресурсы для доступа к БД
        await db_pool.create_users_table(user_id, username, first_name, camefrom, users_choice,
                                                   lang_code)  # noqa

    except Exception as e:
        logger.error(f"Error in language choice: {e}")  # noqa

async def send_message_with_save(message: Union[Message, CallbackQuery], text: str, state: FSMContext, markup=False, # noqa
                                 keyboard=None):
    if isinstance(message, CallbackQuery):
        message = message.message
    if markup:
        sent_message = await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    else:
        sent_message = await message.answer(text)

    data = await state.get_data()
    curr_messages = data.get("messages_to_delete", [])
    curr_messages.append(sent_message.message_id)

    await state.update_data(messages_to_delete=curr_messages)
    return sent_message


async def delete_previous_messages(bot: Bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    if "messages_to_delete" in data:
        for msg_id in data["messages_to_delete"]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
        await state.update_data(messages_to_delete=[])
