import asyncio
from datetime import datetime, time

from aiogram.fsm.context import FSMContext

from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.utils.exc import StorageDataException


class DataStorage:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def get_storage_data(
        self, user_id: int, state: FSMContext, database: ResourcesMiddleware
    ) -> dict:
        """Достаем нужные данные о пользователе"""
        async with self.lock:
            s_data = await state.get_data()
            keys = ["user_id", "username", "first_name", "lang_code"]
            data_status = all([s_data.get(key, False) for key in keys])

            if not data_status:
                if s_data := await self.set_user_info(user_id, database):
                    await state.update_data(s_data)
                    return await state.get_data()
                raise StorageDataException("Error while trying to access data")

            return s_data

    @staticmethod
    async def set_user_info(user_id: int, database: ResourcesMiddleware) -> dict:
        """Гарантирует, что машина состояние имеет все данные о пользователе"""
        s_data = dict()
        if user_info := await database.get_user_info(user_id):
            if profile_info := await database.get_users_profile(user_id):

                birthday = profile_info["birthday"]
                age_delta = datetime.now() - datetime.combine(birthday, time.min)
                s_data.update(
                    user_id=user_id,
                    username=user_info["username"],
                    first_name=user_info["first_name"],
                    language=user_info["language"],
                    fluency=user_info["fluency"],
                    lang_code=user_info["lang_code"],
                    age=age_delta.days // 365,
                    pref_name=profile_info["prefered_name"],
                    status=profile_info["status"],
                    about=profile_info["about"],
                )
                return s_data

            s_data.update(
                user_id=user_info["user_id"],
                username=user_info["username"],
                first_name=user_info["first_name"],
                language=user_info["language"],
                fluency=user_info["fluency"],
                lang_code=user_info["lang_code"],
            )

            return s_data

        return s_data


data_storage = DataStorage()
