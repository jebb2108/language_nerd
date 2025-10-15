# import asyncio
# from datetime import datetime, timedelta
# from typing import TYPE_CHECKING
#
# import aiohttp
# from tenacity import retry, stop_after_attempt, wait_exponential
#
# from app.dependencies import get_db, get_main_bot
# from config import config
# from logging_config import opt_logger as log
#
# if TYPE_CHECKING:
#     from aiogram import Bot
#
# logger = log.setup_logger('sub_checker')
#
#
# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
# async def create_autopayment(user_id: int, amount: float) -> bool:
#     """Создание автоматического списания - возвращает True если платеж создан успешно"""
#     try:
#         database = await get_db()
#         payment_method_id = await database.get_user_payment_method(user_id)
#
#         if not payment_method_id:
#             raise Exception(f"No saved payment method for user {user_id}")
#
#         headers = {
#             'Authorization': f'Bearer {config.YOOKASSA_SECRET_KEY}',
#             'Content-Type': 'application/json',
#             'Idempotence-Key': f"auto_{user_id}_{int(datetime.now(tz=config.TZINFO).timestamp())}"
#         }
#
#         data = {
#             "amount": {
#                 "value": str(amount),
#                 "currency": "RUB"
#             },
#             "capture": True,
#             "description": "Автоматическое списание за подписку",
#             "metadata": {
#                 "user_id": user_id,
#                 "subscription_type": "monthly_auto",
#                 "auto_payment": True
#             },
#             "payment_method_id": payment_method_id,
#         }
#
#         async with aiohttp.ClientSession() as session:
#             async with session.post('https://api.yookassa.ru/v3/payments',
#                                     headers=headers,
#                                     json=data) as response:
#                 if response.status == 200:
#                     payment_data = await response.json()
#                     logger.info(f"Auto-payment created for user {user_id}: {payment_data['id']}")
#                 else:
#                     error_text = await response.text()
#                     raise Exception(f"Auto-payment creation failed: {error_text}")
#
#     except Exception as e:
#         logger.error(f"Failed to create auto-payment for user {user_id}: {e}")
#         return False
#
#
# async def handle_payment_creation_failure(user_id: int, bot: "Bot"):
#     """Обработка неудачного создания платежа (не путать с неудачным вебхуком)"""
#     try:
#         await bot.send_message(
#             chat_id=user_id,
#             text="❌ Не удалось создать автоматическое списание. Пожалуйста, проверьте способ оплаты."
#         )
#
#         database = await get_db()
#         await database.deactivate_subscription(user_id)
#
#         logger.info(f"Payment creation failed for user {user_id}")
#
#     except Exception as e:
#         logger.error(f"Error processing failed payment creation for user {user_id}: {e}")
#
#
# async def main():
#     database = await get_db()
#     bot: "Bot" = await get_main_bot()
#     current_time = datetime.now(tz=config.TZINFO)
#
#     # Обрабатываем по 100 пользователей за раз
#     batch_size = 100
#     offset = 0
#
#     while True:
#         payments_due_to = await database.get_sub_due_to_info(limit=batch_size, offset=offset)
#         if not payments_due_to:
#             break
#
#         for due_to_dict in payments_due_to:
#             user_id = due_to_dict["user_id"]
#             amount = due_to_dict["amount"]
#             untill = due_to_dict["untill"]
#
#             # Если подписка уже истекла и активна
#             if current_time > untill:
#                 success = await create_autopayment(user_id, amount)
#                 if not success:
#                     await handle_payment_creation_failure(user_id, bot)
#
#             # Уведомление за день до списания
#             elif untill - current_time <= timedelta(days=1):
#                 try:
#                     await bot.send_message(
#                         chat_id=user_id,
#                         text=f"💳 Завтра будет списан ежемесячный платеж {amount} рублей за подписку"
#                     )
#                 except Exception as e:
#                     logger.error(f"Failed to send notification to user {user_id}: {e}")
#
#         offset += batch_size
#         await asyncio.sleep(1)
#
# if __name__ == '__main__':
#     asyncio.run(main())