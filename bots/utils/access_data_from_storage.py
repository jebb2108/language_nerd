from datetime import datetime, time

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from middlewares.resources_middleware import ResourcesMiddleware # noqa


async def set_user_info(message: Message, state: FSMContext, database: ResourcesMiddleware):
    """ Гарантирует, что машина состояние имеет все данные о пользователе """

    user_id = message.from_user.id

    if await database.check_user_exists(user_id):
        user_info = await database.get_user_info(user_id)
        username = user_info["username"]
        language = user_info["language"]
        fluency = user_info["fluency"]
        lang_code = user_info["lang_code"]
        if await database.check_profile_exists(user_id):
            users_profile_info = await database.get_users_profile(user_id)
            prefered_name = users_profile_info["prefered_name"]
            birthday = users_profile_info["birthday"]
            age_delta = datetime.now() - datetime.combine(birthday, time.min)
            age_years = age_delta.days // 365
            status = users_profile_info["status"]
            about = users_profile_info["about"]

            await state.update_data(
                user_id=user_id,
                username=username,
                age=age_years,
                name=prefered_name,
                language=language,
                fluency=fluency,
                status=status,
                about=about,
                lang_code=lang_code,
            )
            return

        prefered_name = user_info["first_name"]
        await state.update_data(
            user_id=user_id,
            name=prefered_name,
            language=language,
            fluency=fluency,
            about='non-existent-yet',
            status='unknown',
            lang_code=lang_code,
        )
        return


async def get_storage_data(message: Message, state: FSMContext, database: ResourcesMiddleware):
    """Достаем нужные данные о пользователе"""
    data = await state.get_data()
    keys = ['user_id', 'username', 'first_name', 'lang_code']
    data_status = all([ data.get(key, None) for key in keys ])

    if not data_status:
        await set_user_info(message, state, database)
        return await state.get_data()

    return await state.get_data()
