MESSAGES = dict(
    {
        "hello": {
            "english": "👋 Hey, ",
            "russian": "👋 Привет, ",
            "german": "👋 Hallo, ",
            "spanish": "👋Hola, ",
            "chineese": "👋 Nǐ hǎo, ",
        },
        "intro": {
            "en": "Hi again! Here, I'll be looking for a partner, so you can chat with them\n",
            # "ru": "Я бот, чтобы помочь тебе найти собеседника для общения\n",
            "ru": "Снова привет, в этом месте я буду искать тебе собеседника\n"
        },
        "full_intro": {
            "en": "Don`t you want to talk to someone real? Tap 'Search partner', "
                  "and I'll find a person for you",
            "ru": "Не хочешь поговорить с кем-нибудь реальным? Жми 'Искать партнера', "
                  "и я подберу тебе человека",
        },
        "about": {
            "en": "You may ask me whatever you want by tapping one of these options::\n\n"
                "\t/menu - return to the main menu\n"
                "\t/location - see your location\n"
                "\t/new_session - start a new conversation\n"
                "\t/restart - restart the bot\n\n"
                "if you see me weid or not answering you, contact support. They`ll be glad to help",

            "ru": "Ты можешь попросить меня о чем угодно, использовав следующие команды:\n\n"
                    "\t/menu - вернуться в главное меню\n"
                    "\t/location - увидеть свою геолокацию\n"
                    "\t/new_session - начать новое общение\n"
                    "\t/restart - перезапустить бота\n\n"
                "Если ты видишь, что я не отвечаю или отвечаю странно, "
                "пожалуйста, напиши в тех. поддержку. Они с радостью помогут!",
        },
        "user_info": {
                "en": "=== {nickname} ===\n\n"
                    "{level_status}\n"
                    "Till next level: {percentage}\n\n"
                    "Your age: {age}\n"
                    "Chosen language: {language}\n"
                    "Fluency: {fluency}\n"
                    "Topic: {topic}\n"
                    "Status: {status}\n\n"
                    "About you: {about}",

                "ru": "=== {nickname} ===\n\n"
                    "{level_status}\n"
                    "До следующего уровня: {percentage}\n\n"
                    "Твой возраст: {age}\n"
                    "Выбранный язык: {language}\n"
                    "Уровень владения: {fluency}\n"
                    "Тема для разговора: {topic}\n"
                    "Статус: {status}\n\n"
                    "О себе: {about}",
        },
        "wrong_name": {
            "en": "There is either space or too many characters in your name (max 50)",
            "ru": "Есть пробел или слишком много символов в вашем имени (максимум 50)",
        },
        "wrong_birthday": {
            "en": "Incorrect format. Please, try again",
            "ru": "Неверный формат. Пожалуйста, попробуй ещё раз",
        },
        "wrong_intro": {
            "en": "Your information is either too long or too short. Please, try again",
            "ru": "Твоя информация либо слишком длинная, либо слишком короткая. Пожалуйста, попробуй ещё раз",
        },
        "success": {
            "en": "Thank you for your patience 🤝\nPress /menu to go to the main menu",
            "ru": "Спасибо за терпение 🤝\nНажми /menu, чтобы перейти в главное меню",
        },
        "your_location": {
            "en": "🌎 Your location",
            "ru": "🌎 Твои гео-координаты",
        },
        "no_username": {
            "en": "You don't have a username, please, set one",
            "ru": "У тебя нет @username, пожалуйста, установи его",
        },
        "no_worries": {
            "en":
                "No worries 🫶 We won't use your location\n"
                "Press /menu to go to the main menu",

            "ru":
                "Ничего страшного 🫶 Мы не будем использовать твою геолокацию\n"
                "Нажми /menu, чтобы перейти в главное меню",
        },
        "no_worries_dating": {
            "en": "Got it! We`ll find you a new friend.\nPress /menu to go to the main menu",
            "ru": "Понял, мы найдем тебе нового друга!\nНажми на /menu, чтобы перейти в главное меню",
        },
        "match_found": {
            "en": "Match has been found! Their nickname is <b>{nickname}</b>\n\nTap this button to start chat: ",
            "ru": "Мы нашли вам собеседника! Его псевдоним: <b>{nickname}</b>\n\nНажмите по кнопке ниже, чтобы перейти в чат: ",
        },
        "show_queue_info": {
            "en": "Total in search: {total}\n\nMost spoken languages at the moment: {lans}",
            "ru": "Всего в поиске: {total}\n\nИспользуемые языки в очереди: {lans}",
        },
        "nobody_in_queue": {
            "en": "No one is looking for a match",
            "ru": "Никого нет, чтобы показать актуальные языки"
        },
        "its_just_you": {
            "en": "It`s just you",
            "ru": "Кроме Вас никого нет",
        },
        "cancel_search": {
            "en": "Ended search",
            "ru": "Поиск завершен"
        },
    }
)

QUESTIONARY = dict(
    {
        "need_profile": {
            "en": "Let's get to know each other a bit better\n\n"
            "We need your profile info to start the conversation\n\n"
            "First, I`d like to ask you to <b>turn off your VPN</b> if you have one, "
            "so I can process your profile information right\n\n"
            "Okay, so what name do you want to be seen by others?\n",
            "ru": "Давайте познакомимся немного ближе\n\n"
            "Мне нужна информация для твоего профиля, чтобы начать общение с другими\n\n"
            "Сначала, я бы хотела попросить тебя <b>выключить VPN</b> (если он у тебя есть), "
            "так я смогу обработать информацию правильно\n\n"
            "Хорошо, под каким именем ты хочешь, чтобы другие люди видели тебя?\n",
        },
        "need_intro": {
            "en": "Tell me a few facts about yourself:\n\n"
            "For example, what do you do in your free time?\n"
            "Maybe you have a cool hobby, favorite TV show or\n"
            "place for walks? Any small details are welcome\n\n",
            "ru": "Расскажи пару фактов о себе:\n\n"
            "Например, чем ты занимаешься в свободное время?"
            "Может, у тебя есть крутое хобби, любимый сериал или"
            "место для прогулок? Любые мелочи приветствуются\n\n",
        },
        "need_location": {
            "en": "For the correct work of the application, your location is needed, please provide it by the button below.\n\n"
            "All your information is confidential. Your location will be stored in encrypted form.\n\n"
            "If you do not want us to use your location, click the 'Decline' button",
            "ru": "Мне нужна твоя геолокация, чтобы я в дальнейшем могла подбирать партнеров из твоего города, пожалуйста, предоставь ее по кнопке ниже.\n\n"
            "Вся твоя информация является конфидициальной. Геолокация будет хранится в зашифрованном виде.\n\n"
            "Если ты не хочешь, чтобы я пользовалась твоей геолокацией, просто нажми кнопку 'Отказаться'",
        },
        "need_dating": {
            "en": "Do you want to find a partner for a date?",
            "ru": "Ты хочешь найти вторую половинку?",
        },
        "need_age": {
            "en": "How old are you?\n\n"
            "Please, enter birth date in format: <b>DD.MM.YYYY</b>\n\n",
            "ru": "Сколько тебе лет?\n\n"
            "Пожалуйста, введи дату рождения в формате: <b>ДД.ММ.ГГГГ</b>\n\n",
        },
    }
)

BUTTONS = dict(
    {
        "about_bot": {
            "en": "ℹ️ About bot",
            "ru": "ℹ️ О боте",
        },
        "go_back": {
            "en": "🔙 Go Back",
            "ru": "🔙 Назад",
        },
        "main_bot": {
            "en": "👾 Main Bot",
            "ru": "👾 Основной Бот",
        },
        "profile": {
            "en": "👤 My profile",
            "ru": "👤 Мой профиль",
        },
        "search": {
            "en": "🔍 Search partner",
            "ru": "🔍 Искать партнера"
        },
        "queue_info": {
            "en": "❔Show queue info",
            "ru": "❔Показать очередь",
        },
        "cancel": {
            "en": "❌ Cancel",
            "ru": "❌ Отменить",
        },
        "open_chat": {
            "en": "💬 Open chat",
            "ru": "💬 Открыть чат",
        },
        "yes_to_dating": {
            "en": "🌹 Yes, I`d like to find a soul mate",
            "ru": "🌹 Да, я заинтересован в отношениях",
        },
        "no_to_dating": {
            "en": "🍻🤜🤛 Nah, I want to find a friend",
            "ru": "🍻🤜🤛 Нет, я заинтересован в дружбе",
        },
        "location": {
            "en": "📍 Send location",
            "ru": "📍 Отправить геолокацию",
        },
        "decline": {
            "en": "❌ Decline",
            "ru": "❌ Отказаться",
        },
    }
)


TRANSCRIPTIONS = dict({
    "languages": {
        "russian": {
            "en": "Russian",
            "ru": "Русский",
        },
        "english": {
            "en": "English",
            "ru": "Русский",
        },
    },
    "fluency": {
        "beginer": {
            "en": "beginer",
            "ru": "начальный",
        },
        "intermediate": {
            "en": "intermediate",
            "ru": "средний",
        },
        "advanced": {
            "en": "advanced",
            "ru": "продвинутый",
        },
        "native": {
            "en": "native",
            "ru": "родной",
        }
    },
    "topics": {
        "general": {
            "en": "general",
            "ru": "Обо всем",
        },
        "music": {
            "en": "music",
            "ru": "музыка",
        },
        "sports": {
            "en": "sports",
            "ru": "спорт",
        },
        "technology": {
            "en": "technology",
            "ru": "технологии",
        },
        "travel": {
            "en": "travel",
            "ru": "путешествия",
        },
        "games": {
            "en": "video games",
            "ru": "видео-игры"
        }
    },
    "status": {
        "rookie": {
            "en": "rookie",
            "ru": "зеленый",
        }
    }
})
