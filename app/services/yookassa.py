import uuid

from yookassa import Payment, Configuration

from config import config


class YookassaService:

    Configuration.account_id = config.YOOKASSA_SHOP_ID
    Configuration.secret_key = config.YOOKASSA_SECRET_KEY

    @staticmethod
    async def create_monthly_payment_link(user_id: int):
        # Создание платежа в ЮKassa
        payment = Payment.create({
            "amount": {
                "value": "199.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/lllangbot"
            },
            "capture": True,
            "description": "Оплата подписки",
            "metadata": {
                "user_id": user_id,
                "subscription_type": "monthly_auto",
                "auto_payment": True
            },
            # "save_payment_method": True
        }, uuid.uuid4())

        return payment.confirmation.confirmation_url


yookassa_service = YookassaService()