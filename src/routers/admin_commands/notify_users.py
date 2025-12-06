# import random
# from datetime import timedelta, datetime
#
# from aiogram import Router
# from aiogram.filters import Command
# from aiogram.fsm.context import FSMContext
# from aiogram.types import Message
#
# from src.translations import NOTIFICATIONS
# from src.utils.access_data import data_storage as ds
# from dependencies import get_db, get_report_processer
# from config import config
# from logconf import opt_logger as log
#
# logger = log.setup_logger('send_pending_handler')
#
# router = Router(name=__name__)
#
# @router.message(
#     Command("notify_users", prefix="!"),
#     lambda message: message.from_user.id == int(config.ADMIN_ID)
# )
# async def notify_users(message: Message, state: FSMContext):
#     database = await get_db()
#     data = await ds.get_storage_data(message.from_user.id, state)
#     all_users = await database.get_all_users_for_notification()
#     pending_report_processer = await get_report_processer()
#     results: dict = await pending_report_processer.process_all_pending_reports()
#     lang_code = data.get("lang_code")
#
#     notified_count = 0
#     current_time = datetime.now(tz=config.TZINFO).replace(tzinfo=None)
#     msg_list = NOTIFICATIONS["havent_seen_you"][lang_code]
#     for user_id, last_notified in all_users:
#         if (user_id not in results["success_ids"] and
#                 current_time - timedelta(days=3) >= last_notified):
#             notified_count += 1
#             rand_int = random.randint(0, len(msg_list) - 1)
#             await message.src.send_message(chat_id=user_id, text=msg_list[rand_int])
#             await database.update_notified_time(user_id)
#
#     await message.answer(
#         f"reports sent: {results["success_count"]}\n"
#         f"failed reports: {results["failed_count"]}\n"
#         f"detailed: {results["failed_reports"]}\n"
#         f"notified_count: {notified_count}"
#     )
#
#
