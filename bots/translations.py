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

        "need_location": {
            "en": "For the correct work of the application, your location is needed, please provide it by the button below.\n"
                  "All your information is confidential. Your location will be stored in encrypted form.\n"
                  "If you do not want us to use your location, click the 'Decline' button",

            "ru": "Для корректной работы приложения нужна ваша геолокация, пожалуйста, предоставьте ее по кнопке ниже.\n"
                  "Вся ваша информация является конфидициальной. Геолокация будет хранится в зашифрованном виде.\n"
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
                "I'm so glad to see you here!\n"
                "I'm your language learning assistant, and here's what I can do:\n\n"
                "✨ <b>Dictionary</b> — save and learn new words easily\n"
                "🤝 <b>Practice</b> — chat with other students (coming soon!)\n"
                "🛠 <b>Technical support</b> — I'll help if something breaks\n\n"
                "Just click the button below and choose what interests you! 😊"
            ),
            "ru": (
                "Очень рад видеть тебя здесь!\n"
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

    "go_back": {
        "en": "🔙 Go Back",
        "ru": "🔙 Назад",
    },

    "support": {
        "en": "🛠 Support",
        "ru": "🛠 Поддержка",
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

    "location": {
        "en": "📍 Send location",
        "ru": "📍 Отправить геолокацию",
    },

    "cancel": {
        "en": "❌ Decline",
        "ru": "❌ Отказаться",
    },

    'no_worries': {
        "en": "No worries, we won't use your location",
        "ru": "Ничего страшного, мы не будем использовать вашу геолокацию",
    }
})
