from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.filters.approved import approved
from src.keyboards.inline_keyboards import get_payment_keyboard
from src.middlewares.rate_limit_middleware import RateLimitInfo
from src.translations import MESSAGES
from src.utils.access_data import data_storage as ds
from src.dependencies import get_gateway
from src.exc import StorageDataException
from src.logconf import opt_logger as log

logger = log.setup_logger('common')

router = Router(name=__name__)

@router.message(approved)
async def get_help_handler(message: Message, state: FSMContext, rate_limit_info: RateLimitInfo):
    """ Обрабатывает остальные сообщения пользователя """

    user_id = message.from_user.id
    logger.debug(
        f"User %s message count: %s",
        user_id, rate_limit_info.message_count
    )
    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")
        is_active = data.get("is_active")
        if not is_active: return

        await message.bot.send_message(
            chat_id=message.chat.id, text=MESSAGES["get_help"][lang_code]
        )

    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in get_help_handler: {e}")


@router.message()
async def pay_cmd(message: Message, state: FSMContext, rate_limit_info: RateLimitInfo):

    user_id = message.from_user.id
    gateway = await get_gateway()

    async with gateway:
        response = await gateway.get('check_user_exists', user_id)

        if response.status_code == 200:
            response = await gateway.get('yookassa_link', user_id)
            link = response.json()
        elif response.status_code == 404:
            await message.answer("You`re not registered. Press /start to do so")
            return
        else:
            return

    logger.debug(
        f"User %s message count: %s",
        user_id, rate_limit_info.message_count
    )

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        await message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )


    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await message.answer("You`re not registered. Press /start to do so")
        return

    except Exception as e:
        return logger.error(f"Error in pay_cmd handler: {e}")
