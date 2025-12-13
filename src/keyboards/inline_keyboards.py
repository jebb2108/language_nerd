from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import config
from src.translations import QUESTIONARY, BUTTONS, WEEKLY_QUIZ


def get_go_back_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back",
    )
    builder.add(go_back_button)
    return builder.as_markup()

def show_where_from_keyboard(lang_code):
    # иначе запускаем опрос «откуда вы о нас узнали»
    builder = InlineKeyboardBuilder()
    friends_button = InlineKeyboardButton(
        text=QUESTIONARY["where_youcamefrom"][f"{lang_code}0"],
        callback_data="camefrom_friends",
    )
    search_button = InlineKeyboardButton(
        text=QUESTIONARY["where_youcamefrom"][f"{lang_code}1"],
        callback_data="camefrom_search",
    )
    through_ad_button = InlineKeyboardButton(
        text=QUESTIONARY["where_youcamefrom"][f"{lang_code}2"],
        callback_data="camefrom_other",
    )
    builder.add(friends_button, search_button, through_ad_button)
    builder.adjust(1)
    return builder.as_markup()


def show_language_keyboard(new=False):
    builder = InlineKeyboardBuilder()
    russian_button = InlineKeyboardButton(
        text="🇷🇺 Русский",
        callback_data="chlang_russian" if new else "lang_russian",
    )
    english_button = InlineKeyboardButton(
        text="🇺🇸 English",
        callback_data="chlang_english" if new else "lang_english",
    )
    german_button = InlineKeyboardButton(
        text="🇩🇪 Deutsch",
        callback_data="chlang_german" if new else "lang_german",
    )
    spanish_button = InlineKeyboardButton(
        text="🇪🇸 Español",
        callback_data="chlang_spanish" if new else "lang_spanish",
    )
    chinese_button = InlineKeyboardButton(
        text="🇨🇳 中文",
        callback_data="chlang_chinese" if new else "lang_chinese",
    )
    builder.add(
        russian_button, english_button, german_button, spanish_button, chinese_button
    )
    builder.adjust(1)
    return builder.as_markup()


def show_fluency_keyboard(lang_code, new=False):
    builder = InlineKeyboardBuilder()
    for key, value in QUESTIONARY["fluency_levels"][lang_code].items():
        builder.row(InlineKeyboardButton(
            text=value, callback_data=f"chfluency_{key}" if new else f"fluency_{key}"
        ))

    return builder.as_markup()

def show_topic_keyboard(lang_code, selected_options: list, new=False):
    builder = InlineKeyboardBuilder()
    for key, value in QUESTIONARY["topics"][lang_code].items():
        builder.row(InlineKeyboardButton(
            text=value if not key in selected_options else value + " ✅",
            callback_data=f"chtopic_{key}" if new else f"topic_{key}")
        )

    return builder.as_markup()



def payment_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    start_trial = InlineKeyboardButton(
        text=BUTTONS["start_trial"][lang_code],
        callback_data="start_trial",
    )
    builder.add(start_trial)
    return builder.as_markup()


def confirm_choice_keyboard(lang_code):
    # Обновляем текст с подтверждением выбора
    builder = InlineKeyboardBuilder()
    confirm_button = InlineKeyboardButton(
        text=BUTTONS["confirm"][lang_code],
        callback_data="action_confirm",
    )
    builder.add(confirm_button)
    return builder.as_markup()


def get_on_main_menu_keyboard(lang_code):
    # Формируем URL с user_id для Web App
    web_app_url = f"https://dict.lllang.site/?v={config.version}"
    find_partner_url = f"https://chat.lllang.site/?v={config.version}"

    builder = InlineKeyboardBuilder()
    profile_button = InlineKeyboardButton(
        text=BUTTONS["profile"][lang_code],
        callback_data="profile",
    )
    dict_button = InlineKeyboardButton(
        text=BUTTONS["dictionary"][lang_code],
        web_app=WebAppInfo(url=web_app_url),
    )
    find_partner_button = InlineKeyboardButton(
        text=BUTTONS["find_partner"][lang_code],
        web_app=WebAppInfo(url=find_partner_url)
    )
    subscription_details = InlineKeyboardButton(
        text=BUTTONS["sub_details"][lang_code],
        callback_data="sub_details",
    )
    about_bot_button = InlineKeyboardButton(
        text=BUTTONS["about_bot"][lang_code],
        callback_data="about",
    )
    support_button = InlineKeyboardButton(
        text=BUTTONS["support"][lang_code],
        url="https://t.me/user_bot6426",
    )
    builder.row(profile_button)
    builder.row(dict_button, find_partner_button)
    builder.row(subscription_details)
    builder.row(about_bot_button, support_button)
    return builder.as_markup()

def about_me_keyboard(lcode):
    lang_code =  lcode if lcode in ['en', 'ru'] else 'en'
    builder = InlineKeyboardBuilder()
    community_button = InlineKeyboardButton(
        text=BUTTONS["community"][lcode],
        url=f"https://t.me/language_nerds_{lang_code}"
    )
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lcode],
        callback_data="go_back",
    )
    builder.row(community_button)
    builder.row(go_back_button)
    return builder.as_markup()


def show_word_options_keyboard(word_data):
    builder = InlineKeyboardBuilder()
    for opt_idx, option in enumerate(word_data["options"]):
        # В callback_data мы передаем word_id и индекс варианта
        call_back = f"quiz:{word_data['word_id']}:{opt_idx}"
        builder.row(InlineKeyboardButton(text=option, callback_data=call_back))
    builder.adjust(2)
    return builder.as_markup()


def get_finish_button(lang_code):
    builder = InlineKeyboardBuilder()
    finish_button = InlineKeyboardButton(
        text=WEEKLY_QUIZ["finish_button"][lang_code],
        callback_data="end_quiz",
    )
    builder.add(finish_button)
    return builder.as_markup()


def begin_daily_quiz_keyboard(lang_code, report_id, show_info: bool = True):
    builder = InlineKeyboardBuilder()
    learning_info_button = InlineKeyboardButton(
        text=WEEKLY_QUIZ["learning_info"][lang_code], callback_data=f"how_it_works:{report_id}"
    )
    begin_quiz_button = InlineKeyboardButton(
        text=WEEKLY_QUIZ["begin"][lang_code], callback_data=f"start_report:{report_id}"
    )
    if show_info:
        builder.row(learning_info_button)
    builder.row(begin_quiz_button)
    return builder.as_markup()

def thought_time_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    thought_time_button = InlineKeyboardButton(
        text=WEEKLY_QUIZ["thought_time"][lang_code], callback_data="thougth_time"
    )
    builder.row(thought_time_button)
    return builder.as_markup()

def get_payment_keyboard(lang_code, url):
    builder = InlineKeyboardBuilder()
    payment_button = InlineKeyboardButton(
        text=BUTTONS["payment"][lang_code], url=url
    )
    builder.add(payment_button)
    return builder.as_markup()

def get_subscription_keyboard(lang_code: str, is_active: bool, paused: bool = False):
    builder = InlineKeyboardBuilder()
    cancel_subscription_button = InlineKeyboardButton(
        text=BUTTONS["cancel_sub"][lang_code],
        callback_data="cancel_subscription"
    )
    resume_subscription_button = InlineKeyboardButton(
        text=BUTTONS["resume_sub"][lang_code],
        callback_data="resume_subscription"
    )
    activate_subscription_button = InlineKeyboardButton(
        text=BUTTONS["activate_sub"][lang_code],
        callback_data="activate_subscription"
    )
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back",
    )

    if paused:
        builder.row(resume_subscription_button)
    elif is_active:
        builder.row(cancel_subscription_button)
    else:
        builder.row(activate_subscription_button)

    builder.row(go_back_button)
    return builder.as_markup()


def get_profile_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    edit_profile_button = InlineKeyboardButton(
        text=BUTTONS["edit_profile"][lang_code],
        callback_data="edit_profile"
    )
    shop_button = InlineKeyboardButton(
        text=BUTTONS["shop"][lang_code],
        callback_data="shop:0",
    )
    go_back_button = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back",
    )
    builder.row(edit_profile_button)
    builder.row(shop_button)
    builder.row(go_back_button)
    return builder.as_markup()

def choose_nickname_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    cancel_button = InlineKeyboardButton(
        text=BUTTONS["cancel"][lang_code],
        callback_data="go_back"
    )
    builder.row(cancel_button)
    return builder.as_markup()

def choose_intro_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    cancel_button = InlineKeyboardButton(
        text=BUTTONS["cancel"][lang_code],
        callback_data="go_back"
    )
    builder.row(cancel_button)
    return builder.as_markup()

def get_menu_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    menu_button = InlineKeyboardButton(
        text=BUTTONS["menu"][lang_code],
        callback_data="start_main_page"
    )
    builder.row(menu_button)
    return builder.as_markup()


def get_edit_options(lang_code):
    builder = InlineKeyboardBuilder()
    change_nickname_button = InlineKeyboardButton(
        text=BUTTONS["edit_nickname"][lang_code],
        callback_data="profile_change:nickname"
    )
    change_lang_button = InlineKeyboardButton(
        text=BUTTONS["edit_lang"][lang_code],
        callback_data="profile_change:language"
    )
    change_topic_button = InlineKeyboardButton(
        text=BUTTONS["edit_topic"][lang_code],
        callback_data="profile_change:topics"
    )
    change_intro_button = InlineKeyboardButton(
        text=BUTTONS["edit_intro"][lang_code],
        callback_data="profile_change:intro"
    )
    go_back = InlineKeyboardButton(
        text=BUTTONS["go_back"][lang_code],
        callback_data="go_back"
    )
    builder.row(change_nickname_button, change_lang_button)
    builder.row(change_topic_button, change_intro_button)
    builder.row(go_back)
    return builder.as_markup()


def get_shop_keyboard(lang_code, indx):
    builder = InlineKeyboardBuilder()
    make_payment = InlineKeyboardButton(
        text=BUTTONS["make_payment"][lang_code] if indx != 9 else "Приведи друга",
        callback_data=f"go_back"
    )
    next_button = InlineKeyboardButton(
        text=BUTTONS["next"][lang_code], callback_data=f"shop:{indx+1 if not indx==9 else 0}"
    )
    prev_button = InlineKeyboardButton(
        text=BUTTONS["prev"][lang_code], callback_data=f"shop:{indx-1 if not indx==0 else 9}"
    )
    exit_button = InlineKeyboardButton(
        text=BUTTONS["exit"][lang_code], callback_data="go_back"
    )
    builder.row(make_payment)
    builder.row(prev_button, next_button)
    builder.row(exit_button)
    return builder.as_markup()


def get_search_keyboard(lang_code):
    builder = InlineKeyboardBuilder()
    queue_info_button = InlineKeyboardButton(
        text=BUTTONS["queue_info"][lang_code], callback_data="queue_info"
    )
    cancel_button = InlineKeyboardButton(
        text=BUTTONS["cancel"][lang_code], callback_data="cancel"
    )
    builder.add(queue_info_button, cancel_button)
    builder.adjust(1)
    return builder.as_markup()
