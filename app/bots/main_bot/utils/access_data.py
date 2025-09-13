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

            # Проверяем наличие необходимых ключей
            keys = ["user_id", "username", "first_name", "lang_code"]
            if all(key in s_data for key in keys):
                return s_data

            # Если данных нет в Redis, получаем из базы и сохраняем в Redis
            user_data = await self.set_user_info(user_id, database)
            if not user_data:
                raise StorageDataException(
                    "Error while trying to access user data from database"
                )

            await state.update_data(user_data)
            return user_data

    @staticmethod
    async def set_user_info(user_id: int, database: ResourcesMiddleware) -> dict:
        """Гарантирует, что машина состояние имеет все данные о пользователе"""
        user_info = await database.get_user_info(user_id)
        if not user_info:
            return {}

        profile_info = await database.get_users_profile(user_id)
        result = {
            "user_id": user_id,
            "username": user_info["username"],
            "first_name": user_info["first_name"],
            "language": user_info["language"],
            "fluency": user_info["fluency"],
            "lang_code": user_info["lang_code"],
        }

        if profile_info:
            birthday = profile_info["birthday"]
            if not isinstance(birthday, datetime):
                birthday = datetime.combine(birthday, time.min)

            result.update(
                {
                    "age": (datetime.now() - birthday).days // 365,
                    "pref_name": profile_info["prefered_name"],
                    "status": profile_info["status"],
                    "about": profile_info["about"],
                }
            )

        return result


data_storage = DataStorage()
