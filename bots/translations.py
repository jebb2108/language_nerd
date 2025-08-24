# DICT_GREETING = (
#     "Это твой личный помощник для прокачки словарного запаса! 📚✨\n\n"
#     "<b>Что я умею:</b>\n"
#     "➕ Сохранять английские слова + перевод с частью речи\n"
#     "✏️ Редактировать или ❌ удалять записи (все под твоим контролем!)\n"
#     "📋 Просматривать коллекцию слов — команда /list\n\n"
#     "<b>Как начать?</b> Легко!\n"
#     "🔸 Пиши новое слово (например: <i>book</i>)\n"
#     "🔸 Или сразу с переводом: <i>book: книга</i>\n\n"
#     "Готов(а) покорять английский? Напиши слово дня: <b>embrace</b> 🚀"
# )

QUESTIONARY = dict(
    {
        "intro": {
            "en": ("Great! Here are the next steps for you:\n\n"

                   "1️⃣ A few general questions — you're here\n"
                   "2️⃣ Filling out a questionnaire about yourself\n"
                   "3️⃣ By choice Preselection of interesting interviewees\n\n"

                   "And in the next Monday, the bots will choose tasks to reinforce new words\n\n"


                   "👀 Tell me where you heard about us?\n"),
            "ru": ("Отлично! Вот, какие дальнейшие шаги тебя ждут:\n\n"

                   "1️⃣ Пара общих вопросов — ты находишься здесь\n"
                   "2️⃣ Заполнение анкеты о себе\n"
                   "3️⃣ По желанию Предвыбор интересных собеседников\n\n"

                   "А в ближайший понедельник бот подберет тебе задания на закрепрение новых слов\n\n"


                   "👀 Подскажи, откуда ты о нас узнал?\n"),
        },

        "where_youcamefrom": {
            "en0": "My coworkers or friends told me",
            "ru0": "Мои коллеги или друзья рассказали мне",

            "en1": "Found it on the Internet",
            "ru1": "Нашел в Интернете",

            "en2": "Through an advertisement",
            "ru2": "Через рекламу",
        },

        "lang_pick": {
            "en": "What language would you like to learn?",
            "ru": "Какой язык вы хотите изучать?",
        },

        "languages": {
            "en0": "Russian",
            "en1": "English",
            "en2": "German",
            "en3": "Spanish",
            "en4": "Chineese",

            "ru0": "Русский",
            "ru1": "Английский",
            "ru2": "Немецкий",
            "ru3": "Испанский",
            "ru4": "Китайский",
        },

        "fluency": {
            "en": "What is your level of fluency?",
            "ru": "Каков ваш уровень владения языком?",
        },

        "fluency_levels": {
            "en": {
                "beginner": "Beginner",
                "intermediate": "Intermediate",
                "advanced": "Advanced",
                "native": "Native",
            },
            "ru": {
                "beginner": "Начинающий",
                "intermediate": "Средний",
                "advanced": "Продвинутый",
                "native": "Родной",
            },
        },

        "need_profile": {
            "en": "Let's get to know each other a bit better\n\n"
                  "We need your profile info to start the conversation\n\n"
                  "First, I`d like to ask you to <b>turn off your VPN</b> if you have one, "
                  "so I can process your profile information right\n\n"
                  "Okay, so what name do you want to be seen by others?\n",

            "ru": "Давайте познакомимся немного больше\n\n"
                  "Нам нужна ваша информация о профиле, чтобы начать общение\n\n"
                  "Сначала, я бы хотел попросить вас <b>выключить VPN</b>, если вы его имеете, "
                  "чтобы я мог обработать вашу информацию правильно\n\n"
                  "Хорошо, под каким именем вы хотите, чтобы другие люди видели вас?\n",
        },

        "need_intro": {
            "en": "Tell me more about yourself in a few sentences:\n\n"
                  "For example, what are your hobbies?\n"
                  "What do you like to do in your free time? And so on\n\n",

            "ru": "Расскажите немного о себе в несколько предложений:\n\n"
                  "Например, какие у вас хобби?\n"
                  "Что вы любите делать в свободное время? И так далее\n\n",
        },

        "need_dating": {
            "en": "Do you want to find a partner for a date?",
            "ru": "Вы хотите найти вторую половинку?",
        },

        "age": {
            "en": "How old are you?\n\n"
                  "Please, enter birth date in format: <b>DD.MM.YYYY</b>\n\n",
            "ru": "Сколько вам лет?\n\n"
                  "Пожалуйста, введите дату рождения в формате: <b>ДД.ММ.ГГГГ</b>\n\n",
        },

        "wrong_name": {
            "en": "there is either space or too many characters in your name (max 50)",
            "ru": "есть ли пробел или слишком много символов в вашем имени (максимум 50)",
        },

        "wrong_birthday": {
            "en": "Incorrect format. Please, try again",
            "ru": "Неверный формат. Пожалуйста, попробуйте ещё раз",
        },

        "wrong_intro": {
            "en": "Your information is either too long or incorrect. Please, try again",
            "ru": "Ваша информация либо слишком длинная, либо неверная. Пожалуйста, попробуйте ещё раз",
        },

        "need_location": {
            "en": "For the correct work of the application, your location is needed, please provide it by the button below.\n\n"
                  "All your information is confidential. Your location will be stored in encrypted form.\n\n"
                  "If you do not want us to use your location, click the 'Decline' button",

            "ru": "Для корректной работы приложения нужна ваша геолокация, пожалуйста, предоставьте ее по кнопке ниже.\n\n"
                  "Вся ваша информация является конфидициальной. Геолокация будет хранится в зашифрованном виде.\n\n"
                  "Если вы не хотите, чтобы мы использовали вашу геолокацию, то нажмите кнопку 'Отказаться'",
        },

        "share_location": {
            "en": "📍 Send location",
            "ru": "📍 Отправить геолокацию",
        },

        "terms": {
            "en": "In order to use our service, you must agree to the user agreement",
            "ru": "В целях использования нашего сервиса, вы должны подтвердить, что вы согласны с пользовательским соглашением",
        },

        "confirm": {
            "en": "I agree",
            "ru": "Согласен",
        },
        "gratitude": {
            "en": "Thank you for your patience",
            "ru": "Спасибо за терпение",
        },

        "welcome": {
            "en": (
                "I'm so glad to see you here and"
                "will be your language learning assistant. Here's what I can do:\n\n"
                "✨ <b>Dictionary</b> — save and learn new words easily\n"
                "🤝 <b>Practice</b> — chat with other students (coming soon!)\n"
                "🛠 <b>Technical support</b> — I'll help if something breaks\n\n"
                "Just click the button below and choose what interests you! 😊"
            ),
            "ru": (
                "Очень рад видеть тебя здесь!\n\n"
                "Я — твой помощник в изучении языков, и вот что умею:\n\n"
                "✨ <b>Словарь</b> — сохраняй и учи новые слова легко\n"
                "🤝 <b>Практика</b> — общайся с другими учениками (скоро запуск!)\n"
                "🛠 <b>Техподдержка</b> — помогу, если что-то сломалось\n\n"
                "Просто нажми на кнопку ниже и выбери, что тебя интересует! 😊"
            ),
        },

        "about": {
            "en": (
                "I'm here to make your language learning easier and enjoyable 🌍📚\n\n"
                "My mission is to give you:\n"
                "🔹 <b>A handy dictionary</b> at your fingertips (you'll never forget a word!)\n"
                "🔹 <b>Real conversations</b> with people from all over the world — no unnecessary complications\n"
                "🔹 <b>AI features:</b> Every week, you'll get a mini quiz to test the words you've learned over the week\n\n"
                "✨ This app also includes all the essential tools to help your language learning journey be as great as your vibrant soul :)\n\n"
                "Here, you can learn at your own pace and make friends along the way!"
            ),
            "ru": (
                "Я создан, чтобы твое изучение языков было проще и приятнее 🌍📚\n\n"
                "Мя миссия — дать тебе:\n"
                "🔹 <b>Удобный словарь</b> под рукой (никогда не забудешь слово!)\n"
                "🔹 <b>Живое общение</b> с людьми по всему миру — без лишних сложностей\n"
                "🔹 <b>Возможности ИИ:</b> Раз в неделю тебе будет приходить мини тест "
                "на проверку выученных слов за неделю\n\n"
                "✨ Так же это приложение в себе носит самые необходимые полезности,"
                "чтобы твой рост в изучении языка был великим, как твоя душевнатя натура :)\n\n"
                "Здесь ты сможешь учиться в своем ритме и находить друзей в процессе!"
            ),

        },

    })

BUTTONS = dict({
    "hello": {
        "en": "👋 Hello, ",
        "ru": "👋 Привет, ",
    },

    "dictionary": {
        "en": "📚 Dictionary",
        "ru": "📚 Словарь",
    },

    "find_partner": {
        "en": "🌐 Find partner",
        "ru": "🌐 Найти собеседника",
    },

    "about_bot": {
        "en": "ℹ️ About bot",
        "ru": "ℹ️ О боте",
    },

    "support": {
        "en": "🛠 Support",
        "ru": "🛠 Поддержка",
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

    "open_chat": {
        "en": "💬 Open chat",
        "ru": "💬 Открыть чат",
    },
})

FIND_PARTNER = dict({
    "hello": {
        "en": "👋 Hello, ",
        "ru": "👋 Привет, ",
    },

    "intro": {
        "en": "I`m a bot to help you find a partner for communication\n",
        "ru": "Я бот, чтобы помочь тебе найти собеседника для общения\n",
    },
    "full_intro": {
        "en": "I`m here to help us find a partner and "
              "practice your communication skills on the selected language",
        "ru": "Я здесь, чтобы помочь нам найти собеседника и "
              "попрактиковать твои навыки общения на выбранном языке",
    },

    "about": {
        "en": "You can use the following commands:\n\n"
              "\t/menu - return to the main menu\n"
              "\t/location - see your location\n"
              "\t/new_session - start a new conversation\n"
              "\t/restart - restart the bot\n\n"
              
           "if you have any questions, please contact the support",

        "ru": "Вы можете использовать следующие команды:\n\n"
              "\t/menu - вернуться в главное меню\n"
              "\t/location - увидеть свою геолокацию\n"
              "\t/new_session - начать новое общение\n"
              "\t/restart - перезапустить бота\n\n"
           "Если у вас есть вопросы, пожалуйста, обратитесь в поддержку",
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

    "cancel": {
        "en": "❌ Decline",
        "ru": "❌ Отказаться",
    },

    "success": {
        "en": "Thank you for your patience 🤝\nPress /menu to return to the main menu",
        "ru": "Спасибо за терпение 🤝\nНажмите на /menu, чтобы перейти в главное меню",
    },

    "your_location": {
        "en": "🌎 Your location",
        "ru": "🌎 Ваши гео-координаты",
    },

    'no_worries': {
        "en": "No worries 🫶 We won't use your location",
        "ru": "Ничего страшного 🫶 Мы не будем использовать вашу геолокацию",
    },

    "no_worries_dating": {
        "en": "Got it! We`ll find you a new friend.\nPress /menu to go to the main menu",
        "ru": "Понял, мы найдем вам нового друга!\nНажмите на /menu, чтобы перейти в главное меню",
    }
})
