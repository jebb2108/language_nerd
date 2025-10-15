from datetime import timedelta

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.inline_keyboards import get_payment_keyboard
from app.bot.middlewares.rate_limit_middleware import RateLimitInfo
from app.bot.translations import MESSAGES
from app.bot.utils.access_data import data_storage as ds
from app.bot.filters.paytime import paytime
from exc import StorageDataException
from app.dependencies import get_redis_client, get_yookassa
from logging_config import opt_logger as log

logger = log.setup_logger('common')

router = Router(name=__name__)

@router.message(paytime)
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
    redis_client = await get_redis_client()
    yookassa_client = await get_yookassa()

    logger.debug(
        f"User %s message count: %s",
        user_id, rate_limit_info.message_count
    )

    try:
        data = await ds.get_storage_data(user_id, state)
        lang_code = data.get("lang_code")

        # Отправка ссылки на оплату
        link = await yookassa_client.create_monthly_payment_link(user_id)
        sent = await message.answer(
            text=MESSAGES['payment_needed'][lang_code],
            reply_markup=get_payment_keyboard(lang_code, link),
            parse_mode=ParseMode.HTML,
        )

        await redis_client.setex(
            f'user_payment:{user_id}', timedelta(minutes=10), sent.message_id
        )


    except StorageDataException:
        logger.error(f"User {user_id} trying to access data but doesn`t exist in DB")
        await message.answer("You`re not registered. Press /start to do so")

    except Exception as e:
        logger.error(f"Error in pay_cmd handler: {e}")
