"""
ТЕЛЕГРАМ-БОТЫ: ГЛАВНЫЙ БОТ И БОТ-ПАРТНЕР

Этот проект содержит двух Telegram-ботов, работающих одновременно:
1. Основной бот (Main Bot) - предоставляет меню и информацию
2. Бот-партнер (Partner Bot) - позволяет общаться с другими пользователем

Оба бота запускаются параллельно друг другу из разных файлов
"""

import sys
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Загрузка переменных окружения ДОЛЖНА БЫТЬ ВЫЗВАНА
load_dotenv(""".env""")

# Импорт функций БД
from db_cmds import *

from routers import router as main_router

# Получаем токен бота из переменных окружения
BOT_TOKEN_MAIN = os.getenv("BOT_TOKEN_MAIN")

# Создаем хранилище состояний в оперативной памяти
storage = MemoryStorage()

"""
=============== ЗАПУСК WEB API ===============
Функции для запуска WEB приложения, отображающее выученные слова
"""


# Создаем HTTP-сервер для Web App
async def web_app_handler(request):
    return web.FileResponse("webapp/dist/index.html")


# API для получения слов пользователя
async def api_words_handler(request):
    user_id = int(request.query.get('user_id'))
    # Используем правильную функцию для получения слов
    words = await get_words_from_db(user_id)

    # Преобразование в JSON-совместимый формат
    words_json = []
    for word_tuple in words:
        # word_tuple: (word, part_of_speech, translation)
        words_json.append({
            'word': word_tuple[0],
            'part_of_speech': word_tuple[1],
            'translation': word_tuple[2]
        })

    logging.info(f"Sent {len(words_json)} words for user {user_id}")
    return web.json_response(words_json)

"""
=============== ЗАПУСК WEB API ===============
Функции для запуска WEB приложения, отображающее выученные слова
"""


# Создаем HTTP-сервер для Web App
async def web_app_handler(request):
    return web.FileResponse("webapp/dist/index.html")


# API для получения слов пользователя
async def api_words_handler(request):
    user_id = int(request.query.get('user_id'))
    # Используем правильную функцию для получения слов
    words = await get_words_from_db(user_id)

    # Преобразование в JSON-совместимый формат
    words_json = []
    for word_tuple in words:
        # word_tuple: (word, part_of_speech, translation)
        words_json.append({
            'word': word_tuple[0],
            'part_of_speech': word_tuple[1],
            'translation': word_tuple[2]
        })

    logging.info(f"Sent {len(words_json)} words for user {user_id}")
    return web.json_response(words_json)



"""
===== ЗАПУСК ВСЕЙ СИСТЕМЫ =====
"""

async def run():
    """
    Запускает одного бота
    Параметры:
    - bot_token: токен Telegram бота
    - router: маршрутизатор с обработчиками
    - storage: хранилище состояний (опционально)
    """
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # Инициализация БД в первую очередь
    await init_db()

    # Небольшая задержка для инициализации блокировки
    await asyncio.sleep(1)

    # Запуск бота
    bot = Bot(token=BOT_TOKEN_MAIN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.include_router(main_router)

    logging.info("Starting main bot (polling)…")
    # # Удаляем вебхук
    # await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)
    await close_db()

if __name__ == "__main__":
    asyncio.run(run())