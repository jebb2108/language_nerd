# from dotenv import load_dotenv
#
# # Импорт текстовых сообщений из отдельного файла (config.py)
# from config import *
#
# # Загрузка переменных окружения ДОЛЖНА БЫТЬ ВЫЗВАНА
# load_dotenv(""".env""")
# #
#
# # = ОСНОВНЫЕ ОБРАБОТЧИКИ БОТА-СОБЕСЕДНИКА =
# @router_communication.message()
# async def echo(message: Message):
#     if message.text:
#         await message.answer(message.text)
#
#
#
# """
# =============== ЗАПУСК ВСЕЙ СИСТЕМЫ ===============
# """
#
# async def run_bot(bot_token: str, router: Router, storage=None):
#     """
#     Запускает одного бота
#     Параметры:
#     - bot_token: токен Telegram бота
#     - router: маршрутизатор с обработчиками
#     - storage: хранилище состояний (опционально)
#     """
#     # Создаем объект бота с HTML-форматированием по умолчанию
#     bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
#     # Создаем диспетчер
#     dp = Dispatcher(storage=storage) if storage else Dispatcher()
#     # Подключаем маршрутизатор с обработчиками
#     dp.include_router(router)
#     # Запускаем бота в режиме опроса сервера Telegram
#     await dp.start_polling(bot)
#     # Закрываем соединение с БД при завершении
#     await close_db()
#     logging.info("Database connection closed")
#
#
# async def run():
#
#     # Настройка логирования
#     logging.basicConfig(
#         level=logging.INFO,
#         stream=sys.stdout,
#         format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
#     )
#
#     await init_db()
#     bot = Bot(token=BOT_TOKEN_PARTNER, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
#     dp = Dispatcher(storage=storage)
#     dp.include_router(router_communication)
#
#     logging.info("Starting partner bot (polling)…")
#     await dp.start_polling(bot)
#     await close_db()
#
#
# # Точка входа в программу
# if __name__ == "__main__":
#     # Запускаем основную асинхронную функцию
#     asyncio.run(run())