import random

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command

from app.bots.main_bot.utils.access_data import data_storage as ds
from config import config
from logging_config import opt_logger as log
from app.dependencies import get_db, get_report_processer
from app.bots.main_bot.translations import NOTIFICATIONS


logger = log.setup_logger('send_pending_handler')

router = Router(name=__name__)

@router.message(
    Command("notify_users", prefix="!"),
    lambda message: message.from_user.id == int(config.ADMIN_ID)
)
async def notify_users(message: Message, state: FSMContext):
    database = await get_db()
    data = await ds.get_storage_data(message.from_user.id, state)
    all_users = await database.get_all_users()
    pending_report_processer = await get_report_processer()
    results: dict = await pending_report_processer.process_all_pending_reports()
    lang_code = data.get("lang_code")

    msg_list = NOTIFICATIONS["havent_seen_you"][lang_code]
    rand_int = random.randint(0, len(msg_list)-1)
    for user in all_users:
        if user not in results["success_ids"]:
            await message.bot.send_message(chat_id=user, text=msg_list[rand_int])

    await message.answer(
        f"reports sent: {results["success_count"]}\n"
        f"failed reports: {results["failed_count"]}\n"
        f"detailed: {results["failed_reports"]}"
    )


