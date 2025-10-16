import asyncio
from datetime import datetime, timedelta

from aiogram import Bot
from fastapi import Request, BackgroundTasks, APIRouter

from app.dependencies import get_main_bot, get_db, get_redis_client
from app.services.database import DatabaseService
from config import config
from logging_config import opt_logger as log

router = APIRouter(prefix="/api")
logger = log.setup_logger('webhook_payments')


@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    user_id = data['object']['metadata']['user_id']
    logger.info("Yookassa webhook received for user %s", user_id)
    background_tasks.add_task(process_payment_webhook, data)
    return {"status": "ok"}


async def process_payment_webhook(data):
    try:
        if data['event'] == 'payment.succeeded':
            payment = data['object']
            user_id = payment['metadata']['user_id']

            # Проверяем, это автоматический платеж или обычный
            is_auto_payment = payment['metadata'].get('auto_payment', False)

            if is_auto_payment and payment['payment_method'].get('saved', False):
                logger.info("Auto-payment being processed for user %s...", user_id)
                await handle_auto_payment_succeeded(payment)
            else:
                logger.info("Regular payment being processed for user %s...", user_id)
                # await handle_regular_payment_success(payment)

        elif data['event'] == 'payment.canceled':
            payment = data['object']
            user_id = payment['metadata']['user_id']
            is_auto_payment = payment['metadata'].get('auto_payment', False)

            expired_on_confirmation = \
                payment["cancellation_details"]["reason"]  == "expired_on_confirmation"

            logger.info("Auto-payment declined for user %s", user_id)
            logger.info("Initiator: %s", payment["cancellation_details"]["party"])
            logger.info("Reason: %s", payment["cancellation_details"]["reason"])

            if expired_on_confirmation: return

            elif is_auto_payment:
                await handle_auto_payment_failed(payment)


    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")


async def handle_auto_payment_succeeded(payment: dict):
    """Обработка успешного автоматического списания"""
    user_id = int(payment['metadata']['user_id'])
    try:
        # Активируем подписку
        await activate_subscription(user_id, payment)
        # Уведомляем пользователя
        await notify_user_auto_succeeded(user_id)

    except Exception as e:
        logger.error(f"Failed to process auto-payment success: {e}")


async def handle_auto_payment_failed(payment: dict):
    """Обработка неудачного автоматического списания"""
    user_id = int(payment['metadata']['user_id'])
    try:
        # Деактивируем подписку
        await deactivate_subscription(user_id)
        # Уведомляем пользователя
        await notify_user_auto_failed(user_id)

    except Exception as e:
        logger.info(f"Failed to process auto-payment failure: {e}")


async def activate_subscription(user_id: int, payment: dict):
    """Активация подписки после успешного платежа"""
    database: DatabaseService = await get_db()
    redis_client = await get_redis_client()
    payment_method_id = payment["payment_method"].get("id")
    new_untill = datetime.now(tz=config.TZINFO) + timedelta(days=31)

    await database.create_payment(
        user_id=user_id,
        period="month",
        amount=payment['amount']['value'],
        currency=payment['amount']['currency'],
        trial=False,
        untill=new_untill,
        payment_id=payment['id']
    )

    await database.activate_subscription(user_id)
    await database.save_payment_method(user_id, payment_method_id)

    await redis_client.setex(
        f"user_paid:{user_id}",
        timedelta(hours=2),
        new_untill.isoformat()
    )


async def deactivate_subscription(user_id: int):
    """Деактивация подписки при неудачном списании"""
    database: DatabaseService = await get_db()
    # Логика деактивации подписки
    await database.deactivate_subscription(user_id)


async def save_payment_method(user_id: int, payment_method_id: str):
    """Сохранение payment_method_id для автоматических списаний"""
    database: DatabaseService = await get_db()
    await database.save_payment_method(user_id, payment_method_id)


async def notify_user_auto_failed(user_id: int):
    """Уведомление о неудачном автоматическом списании"""
    try:
        bot: Bot = await get_main_bot()
        await bot.send_message(
            chat_id=user_id,
            text="❌ Не удалось автоматически продлить подписку. "
                 "Пожалуйста, проверьте способ оплаты или обновите карту."
        )
    except Exception as e:
        logger.error(f"Can't notify user {user_id} about auto-failure: {e}")


async def notify_user_auto_succeeded(user_id):
    try:
        bot: "Bot" = await get_main_bot()
        redis_client = await get_redis_client()
        message_id = await redis_client.get(f"user_payment:{user_id}")
        await asyncio.sleep(1)
        await bot.edit_message_text(
            text="✅ Платеж прошел успешно! Подписка активирована",
            chat_id=user_id,
            message_id=int(message_id)
        )
    except Exception as e:
        logger.error(f"Can't notify user {user_id}: {e}")
        # Можно сохранить в очередь для повторной отправки