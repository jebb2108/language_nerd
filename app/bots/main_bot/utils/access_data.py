import asyncio
from datetime import datetime, time
from aiogram.fsm.context import FSMContext
from app.bots.main_bot.utils.exc import StorageDataException
from app.dependencies import get_db


class DataStorage:
    def __init__(self):
        self.lock = asyncio.Lock()
        self._initialized = False

    async def init(self):
        self.database = await get_db()
        self._initialized = True

    async def get_storage_data(
        self, user_id: int, state: FSMContext) -> dict:
        """Достаем нужные данные о пользователе"""
        if not self._initialized: await self.init()

        async with self.lock:
            s_data = await state.get_data()

            # Проверяем наличие необходимых ключей
            keys = ["user_id", "first_name", "is_active", "lang_code"]
            if all(s_data.get(key, False) for key in keys):
                return s_data

            # Если данных нет в Redis, получаем из базы и сохраняем в Redis
            user_data = await self.set_user_info(user_id)
            if not user_data:
                raise StorageDataException

            await state.update_data(user_data)
            return user_data


    async def set_user_info(self, user_id: int) -> dict:
        """Гарантирует, что машина состояние имеет все данные о пользователе"""
        user_info = await self.database.get_user_info(user_id)
        if not user_info:
            return {}

        profile_info = await self.database.get_users_profile(user_id)
        result = {
            "user_id": user_id,
            "username": user_info["username"],
            "first_name": user_info["first_name"],
            "language": user_info["language"],
            "fluency": user_info["fluency"],
            "topic": user_info["topic"],
            "lang_code": user_info["lang_code"],
            "is_active": user_info["is_active"]
        }

        if profile_info:
            birthday = profile_info["birthday"]
            if not isinstance(birthday, datetime):
                birthday = datetime.combine(birthday, time.min)

            result.update(
                {
                    "age": (datetime.now() - birthday).days // 365,
                    "nickname": profile_info["nickname"],
                    "dating": profile_info["dating"],
                    "status": profile_info["status"],
                    "about": profile_info["about"],
                }
            )

        return result


data_storage = DataStorage()
