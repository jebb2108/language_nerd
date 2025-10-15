from aiogram import Bot
from datetime import datetime, timedelta
from fastapi import Request, BackgroundTasks, APIRouter

from app.dependencies import get_main_bot, get_db, get_redis_client
from app.services.database import DatabaseService
from logging_config import opt_logger as log
from config import config


router = APIRouter(prefix="/api")
logger = log.setup_logger('webhook_payments')



@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    signature = request.headers.get("Authorization")

    if not verify_signature(data, signature):
        return {"status": "error"}

    # Обрабатываем в фоне
    background_tasks.add_task(process_payment_webhook, data)
    return {"status": "ok"}


def verify_signature(body, signature):
    import hmac
    import hashlib
    import json

    # Генерируем подпись из тела запроса
    message = json.dumps(body, separators=(',', ':'), ensure_ascii=False).encode()
    expected_signature = hmac.new(
        config.YOOKASSA_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


async def process_payment_webhook(data):
    try:
        if data['event'] == 'payment.succeeded':
            payment = data['object']

            # Проверяем, это автоматический платеж или обычный
            is_auto_payment = payment['metadata'].get('auto_payment', False)

            if is_auto_payment:
                await handle_auto_payment_success(payment)
            else:
                await handle_regular_payment_success(payment)

        elif data['event'] == 'payment.canceled':
            payment = data['object']
            is_auto_payment = payment['metadata'].get('auto_payment', False)

            if is_auto_payment:
                await handle_auto_payment_failed(payment)

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")


async def handle_auto_payment_success(payment: dict):
    """Обработка успешного автоматического списания"""
    try:
        user_id = int(payment['metadata']['user_id'])

        # Активируем подписку
        await activate_subscription(user_id, payment)

        logger.info(f"Auto-payment succeeded for user {user_id}, payment {payment['id']}")

    except Exception as e:
        logger.error(f"Failed to process auto-payment success: {e}")


async def handle_auto_payment_failed(payment: dict):
    """Обработка неудачного автоматического списания"""
    try:
        user_id = int(payment['metadata']['user_id'])

        # Деактивируем подписку
        await deactivate_subscription(user_id)

        # Уведомляем пользователя
        await notify_user_auto_failed(user_id)

        logger.info(f"Auto-payment failed for user {user_id}, payment {payment['id']}")

    except Exception as e:
        logger.error(f"Failed to process auto-payment failure: {e}")


async def handle_regular_payment_success(payment: dict):
    """Обработка обычного успешного платежа (существующая логика)"""
    try:
        user_id = int(payment['metadata']['user_id'])

        # Сохраняем payment_method_id для будущих автоматических списаний
        if payment.get('payment_method'):
            payment_method_id = payment['payment_method']['id']
            await save_payment_method(user_id, payment_method_id)

        # Активируем подписку
        await activate_subscription(user_id, payment)

        # Уведомляем пользователя
        await notify_user_via_bot(user_id)

    except Exception as e:
        logger.error(f"Failed to process regular payment: {e}")


async def activate_subscription(user_id: int, payment: dict):
    """Активация подписки после успешного платежа"""
    database: DatabaseService = await get_db()
    redis_client = await get_redis_client()

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


async def notify_user_via_bot(user_id):
    try:
        bot: "Bot" = await get_main_bot()
        redis_client = await get_redis_client()
        message_id = await redis_client.get(f"user_payment:{user_id}")
        await bot.edit_message_text(
            text="✅ Платеж прошел успешно! Подписка активирована",
            chat_id=user_id,
            message_id=int(message_id)
        )
    except Exception as e:
        logger.error(f"Can't notify user {user_id}: {e}")
        # Можно сохранить в очередь для повторной отправки