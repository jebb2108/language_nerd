from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from translations import QUESTIONARY # noqa
from filters import IsBotFilter # noqa
from routers.commands.menu_commands import show_main_menu # noqa
from config import BOT_TOKEN_MAIN, db_pool, logger # noqa

router = Router(name=__name__)
# Фильтрация по токену

router.message.filter(IsBotFilter(BOT_TOKEN_MAIN))
router.callback_query.filter(IsBotFilter(BOT_TOKEN_MAIN))

class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()


@router.message(Command("start"), IsBotFilter(BOT_TOKEN_MAIN))
async def start_with_polling(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_exists = False

    # Инициализируем lang_code до блока try
    lang_code = message.from_user.language_code or "en"
    if lang_code not in ['en', 'ru']:
        lang_code = 'en'

    try:
        # Проверяем существование пользователя в БД
        async with db_pool.acquire() as conn: # noqa
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
            about="",
        )

    except Exception as e:
        logger.error(f"Error in start handler: {e}") # noqa

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
        logger.error(f"Error in camefrom handler: {e}") # noqa


@router.callback_query(F.data.startswith("lang_"), PollingStates.language_state)
async def handle_language_choice(callback: CallbackQuery, state: FSMContext):
    try:

        data = await state.get_data()
        lang_code = data.get('lang_code', 'en')

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
        user_id = data['user_id']
        username = data.get('username', 'None')
        first_name = data.get('first_name', 'None')
        camefrom = data.get('camefrom', 'None')
        await db_pool.create_users_table(user_id, username, first_name, camefrom, users_choice, lang_code)  # noqa

    except Exception as e:
        logger.error(f"Error in language choice: {e}") # noqa


@router.callback_query(F.data == "action_confirm", PollingStates.introduction_state)
async def start_main_menu(callback: CallbackQuery, state: FSMContext):
    # Получаем данные ДО очистки состояния
    data = await state.get_data()
    user_id = data.get("user_id", callback.from_user.id)  # Используем ID из колбэка как резерв

    # Удаляем все предыдущие сообщения
    await delete_previous_messages(callback.bot, callback.message.chat.id, state)

    # Очищаем состояние опроса
    await state.clear()

    # Заполняем память актуальной информацией о пользователе
    username, first_name, language, lang_code = await db_pool.get_user_info(user_id)  # noqa

    # Обновляем состояние с проверкой на None
    await state.update_data(
        user_id=user_id,
        username=username or "",
        first_name=first_name or "",
        language=language or "english",  # Значение по умолчанию
        lang_code=lang_code or "en",  # Значение по умолчанию
    )

    # Показываем главное меню
    await show_main_menu(callback.message, state)


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
