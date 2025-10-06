import json
from datetime import datetime, timedelta
from json import JSONDecodeError

from fastapi import Request, BackgroundTasks, APIRouter
from aiogram import Bot

from app.dependencies import get_main_bot, get_db, get_redis_client
from app.services.database import DatabaseService
from config import config
from logging_config import opt_logger as log

logger = log.setup_logger('webhook_payments')

router = APIRouter(prefix="/api")


@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, background_tasks: BackgroundTasks):
    # Проверка подписи (важно для безопасности!)
    data = await request.json()
    signature = request.headers.get("Authorization")

    if not verify_signature(data, signature):
        return {"status": "error"}

    # Обрабатываем в фоне
    background_tasks.add_task(process_payment_webhook, data)
    return {"status": "ok"}


def verify_signature(body, signature):
    # Реализуйте проверку подписи ЮKassa
    logger.debug(f"Body: {body}")
    logger.debug(f"Signature: {signature}")
    return True  # Заглушка


async def process_payment_webhook(data):
    try:
        if data['event'] == 'payment.succeeded':
            payment = data['object']
            user_id = payment['metadata']['user_id']  # Получаем из metadata

            # Активируем подписку
            await activate_subscription(user_id, payment)

            # Пытаемся уведомить пользователя через бота
            await notify_user_via_bot(user_id)

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")


async def activate_subscription(user_id, payment):

    database: "DatabaseService" = await get_db()
    redis_client = await get_redis_client()
    new_until = datetime.now(tz=config.TZINFO) + timedelta(days=31)
    payment_id = payment["id"]

    await database.create_payment(
        user_id=user_id,
        period=config.MONTH,
        amount=199,
        currency='RUB',
        trial=False,
        untill=new_until,
        payment_id=payment_id
    )

    await redis_client.setex(f"user_paid:{user_id}", timedelta(hours=2), new_until.isoformat())


async def notify_user_via_bot(user_id):
    try:
        bot: "Bot" = await get_main_bot()
        await bot.send_message(user_id, "✅ Платеж прошел успешно! Подписка активирована.")
    except Exception as e:
        logger.error(f"Can't notify user {user_id}: {e}")
        # Можно сохранить в очередь для повторной отправки
