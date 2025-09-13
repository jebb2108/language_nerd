import asyncio
from datetime import datetime, time

from aiogram.fsm.context import FSMContext

from app.bots.partner_bot.middlewares.resources_middleware import ResourcesMiddleware
from app.bots.partner_bot.utils.exc import StorageDataException


class DataStorage:
    def __init__(self):
        self.lock = None

    async def get_storage_data(
        self, user_id: int, state: FSMContext, database: ResourcesMiddleware
    ) -> dict:
        """Достаем нужные данные о пользователе"""
        if self.lock is None:
            self.lock = asyncio.Lock()

        async with self.lock:

            s_data = await state.get_data()

            # Проверяем наличие необходимых ключей
            keys = ["user_id", "username", "first_name", "lang_code"]
            data_status = all(key in s_data for key in keys)

            if not data_status:
                user_data = await self.set_user_info(user_id, database)
                if user_data:
                    await state.update_data(user_data)
                    return await state.get_data()
                else:
                    raise StorageDataException("Error while trying to access user data from database")


    @staticmethod
    async def set_user_info(user_id: int, database: ResourcesMiddleware) -> dict:
        """Гарантирует, что машина состояние имеет все данные о пользователе"""
        s_data = dict()
        if user_info := await database.get_user_info(user_id):
            if profile_info := await database.get_users_profile(user_id):

                birthday = profile_info["birthday"]
                if isinstance(birthday, datetime):
                    age_delta = datetime.now() - birthday
                else:
                    # Предполагаем, что birthday это date или строка
                    birthday_date = datetime.combine(birthday, time.min)
                    age_delta = datetime.now() - birthday_date

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

        return {}


data_storage = DataStorage()
