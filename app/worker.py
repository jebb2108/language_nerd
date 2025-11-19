import asyncio
import json
from datetime import datetime
from functools import wraps

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from faststream.rabbit.annotations import RabbitMessage

from app.dependencies import get_db
from config import config
from logging_config import opt_logger

logger = opt_logger.setup_logger("worker")
broker = RabbitBroker(config.RABBITMQ_URL, logger=logger)

# Словарь для хранения зарегистрированных
# обработчиков по их назначению (purpose)
purposes = {}

# Декоратор для регистрации функций обработчиков
def register_purpose(purpose: str):

    # Внешняя обертка декоратора,
    # принимающая параметр purpose
    def decorator(fn):
        # Сохраняем метаданные оригинальной функции
        @wraps(fn)
        # Асинхронная обертка вокруг оригинальной функции
        async def wrapper(data):
            # Вызов оригинальной асинхронной функции
            return await fn(data)

        # Регистрируем функцию-обертку в
        # словаре purposes под указанным ключом purpose
        purposes[purpose] = wrapper

        # Возвращаем зарегистрированную функцию-обертку
        return wrapper

    # Возвращаем сам декоратор
    return decorator



@register_purpose(config.ADD_USER_PURPOSE)
async def add_user(data: dict) -> None:
    database = await get_db()
    user = json.loads(data["user"])
    await database.create_user(**user)
    payment = json.loads(data["payment"])
    payment["untill"] = datetime.fromisoformat(payment["untill"])
    await database.create_payment(**payment)
    logger.info("New user & payment processed by worker")
    return None


@register_purpose(config.ADD_PROFILE_PURPOSE)
async def add_profile(data: dict) -> None:
    database = await get_db()
    profile = json.loads(data["profile"])
    bday = profile.get("birthday")
    day, month, year = bday.split('-')
    date_str = f"{year}-{month}-{day}"
    date_obj = datetime.fromisoformat(date_str).date()
    profile["birthday"] = date_obj
    await database.add_users_profile(**profile)
    return None


@register_purpose(config.ADD_LOCATION_PURPOSE)
async def add_location(data: dict) -> None:
    database = await get_db()
    location = json.loads(data["location"])
    await database.add_users_location(**location)
    return


@register_purpose(config.ADD_PAYMENT_PURPOSE)
async def add_payment(data: dict) -> None:
    database = await get_db()
    payment = json.loads(data["payment"])
    await database.create_payment(**payment)
    return None


@register_purpose(config.ADD_MATCHID_PURPOSE)
async def add_match_id(data: dict) -> None:
    database = await get_db()
    match_id = json.loads(data["match_id"])
    await database.create_match_id(match_id)
    return


@broker.subscriber(config.RABBITMQ_NEW_USERS_QUEUE)
async def handle_db_requests(data: dict, msg: "RabbitMessage"):
    """ Находит обработчик для запроса в БД """
    try:
        purpose = data.get("purpose")
        handler = purposes.get(purpose)
        # Вызываем соответствующий обработчик
        if handler: await handler(data)

        logger.info(f"Successfully processed message with purpose: {purpose}")

    except Exception as e:
        logger.error(f"Error in DB execution: {e}")

    finally:
        await msg.ack()


async def main():
    # Запуск основной программы
    logger.info("Starting worker ...")
    app = FastStream(broker, logger=logger)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
