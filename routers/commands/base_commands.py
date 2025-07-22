import logging
from typing import Union

from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo

from config import QUESTIONARY, BUTTONS
from db_cmds import lock_manager, db_pool, create_users_table, get_user_info

router = Router(name=__name__)


class PollingStates(StatesGroup):
    camefrom_state = State()
    language_state = State()
    introduction_state = State()


@router.message(Command("start"))
async def start_with_polling(message: Message, state: FSMContext):
    # Проверяем наличие блокировки
    if not lock_manager.has_lock:
        logging.warning("Skipping message processing - no lock")
        return

    user_id = message.from_user.id
    try:
        # Проверяем существование пользователя в БД
        async with db_pool.acquire() as conn:
            user_exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE user_id = $1",
                user_id
            )

        # Новый пользователь - начинаем опрос
        await state.update_data(
            user_id=user_id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "",
            lang_code=message.from_user.language_code or "en",
            chosen_language="",
            camefrom="",
            about="",
        )

    except Exception as e:
        logging.error(f"Error in start handler: {e}")

    # Если пользователь существует - показываем главное меню
    if user_exists:
        await show_main_menu(message, state)
        return

    # Получаем данные из состояния
    data = await state.get_data()
    lang_code = data['lang_code']
    if lang_code not in ['en', 'ru']:
        lang_code = 'en'

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
    if not lock_manager.has_lock:
        await callback.answer("⏳ Please try again later...")
        return

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
        logging.error(f"Error in camefrom handler: {e}")


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
        await create_users_table(user_id, username, first_name, camefrom, users_choice, lang_code)

    except Exception as e:
        logging.error(f"Error in language choice: {e}")


@router.callback_query(F.data == "action_confirm", PollingStates.introduction_state)
async def start_main_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    # Удаляем все предыдущие сообщения
    await delete_previous_messages(callback.bot, callback.message.chat.id, state)
    # Очищаем состояние опроса
    await state.clear()

    # Заполняем память актуальной информацией о пользователе
    username, first_name, language, lang_code = await get_user_info(user_id)
    await state.update_data(
        user_id=user_id,
        username=username,
        first_name=first_name,
        language=language,
        lang_code=lang_code,
    )

    # Показываем главное меню
    await show_main_menu(callback.message, state)


async def show_main_menu(message: Message, state: FSMContext):
    """Показывает главное меню для пользователя"""
    data = await state.get_data()
    user_id = data["user_id"]
    first_name = data["first_name"]
    lang_code = data["lang_code"]

    # Формируем URL с user_id
    web_app_url = f"https://jebb2108.github.io/index.html?user_id={user_id}"

    # Создаем клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTONS["dictionary"][lang_code], web_app=WebAppInfo(url=web_app_url)),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["find_partner"][lang_code], url="https://t.me/lllang_onlinebot"),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["about_bot"][lang_code], callback_data="about"),
            InlineKeyboardButton(text=BUTTONS["support"][lang_code], url="https://t.me/user_bot6426"),
        ],
    ])

    await message.answer(
        f"{BUTTONS["hello"][lang_code]}<b>{first_name}</b>!\n\n{QUESTIONARY["welcome"][lang_code]}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "О боте"
    Показывает подробную информацию о проекте
    """

    data = await state.get_data()
    lang_code = data["lang_code"]
    # Клавиатура только с кнопкой возврата
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Go Back", callback_data="go_back")]
    ])

    # Редактируем текущее сообщение, заменяя его на текст "О боте"
    await callback.message.edit_text(QUESTIONARY["about"][lang_code], reply_markup=keyboard)
    # Подтверждаем обработку callback (убираем часики на кнопке)
    await callback.answer()


@router.callback_query(F.data == "go_back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    first_name = data["first_name"]
    lang_code = data["lang_code"]
    # URL вашего Web App
    web_app_url = "https://jebb2108.github.io/index.html"

    # Создаем клавиатуру с кнопкой Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BUTTONS["dictionary"][lang_code], web_app=WebAppInfo(url=web_app_url)),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["find_partner"][lang_code], url="https://t.me/lllang_onlinebot"),
        ],
        [
            InlineKeyboardButton(text=BUTTONS["about_bot"][lang_code], callback_data="about"),
            InlineKeyboardButton(text=BUTTONS["support"][lang_code], url="https://t.me/user_bot6426"),
        ],
    ])

    # Отправляем приветственное сообщение с клавиатурой
    await callback.message.edit_text(
        f"{BUTTONS["hello"][lang_code]}<b>{first_name}</b>!\n\n{QUESTIONARY["welcome"][lang_code]}",
        reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await callback.answer()


async def send_message_with_save(message: Union[Message, CallbackQuery], text: str, state: FSMContext, markup=False,
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
