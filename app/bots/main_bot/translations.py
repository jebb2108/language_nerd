MESSAGES = dict(
    {
        "hello": {
            "en": "👋 Hello, ",
            "ru": "👋 Привет, ",
        },
        "welcome": {
            "en": (
                "I`m Sam. Your language learning assistant. Here's what I can do:\n\n"
                "✨ <b>Dictionary</b> — save and learn new words easily\n"
                "🤝 <b>Practice</b> — chat with other students (coming soon!)\n"
                "🛠 <b>Technical support</b> — I'll help if something breaks\n\n"
            ),
            "ru": (
                "Я Сэм. Помогу тебе в закреплении изученного.\n\nВот что я умею:"
                "✨ <b>Словарь</b> — сохраняй и закрепляй новые слова легко\n"
                "🤝 <b>Практика</b> — общайся с другими учениками\n"
                "🛠 <b>Техподдержка</b> — помогу, если что-то сломалось\n\n"
            ),
        },
        "get_to_know": {
            "en": "\n\nDon`t forget to complete your registration! Just click 'Find partner' below to do so",
            "ru": "\n\nНе забудь завершить регистрацию! Просто нажми на 'Найти собеседника' ниже для продолжения"
        },
        "about": {
            "en": (
                "I'm just like a human being, the only difference being that my inner world is made up of ones and zeros."
                "My greatest joy will be helping you reinforce new words and idioms."
                "✨ I'll give you everything you need to do this, and once a week I'll give you tests to reinforce your knowledge."
                "With me, you can progress in language learning at your own pace and make friends along the way!"
            ),
            "ru": (
                "Я совсем как человек с той лишь разницей, что мой внутренний мир состоит из нулей и единиц\n\n"
                "Для меня самой большой радостью будет помочь тебе с закреплением новых слов и идиом\n\n"
                "✨ Дам тебе все самое необходимое для этого, а раз в неделю буду писать тебе тесты на закрепление\n\n"
                "Со мною ты сможешь двигаться в изучении языка в своем ритме и находить друзей в процессе!"
            ),
        },
        "you_chose": {
            "en": "➪ You chose:",
            "ru": "➪ Ты выбрал:",
        },
        "gratitude": {
            "en": "Thank you for your patience",
            "ru": "Спасибо за терпение",
        },
    }
)

QUESTIONARY = dict(
    {
        "intro": {
            "en": (
                "My name is Sam. I'm a smart helper "
                "who will help you reinforce new words so they're never forgotten. "
                "Here's what awaits you:\n\n"
                    "1️⃣ A few general questions — you're here\n"
                    "2️⃣ Filling out a questionnaire about yourself\n"
                    "3️⃣ By choice preselection of interesting partners, including dating\n\n"
                    "And in the next Monday, I`ll send you a quiz for reinforcement\n\n"
                "👀 Tell me where you heard about me?\n"
            ),
            "ru": (
                "Меня зовут Sam. Я умная помощница, помогаю людям закреплять новые слова, "
                "чтобы они никогда не забывались. Вот что тебя ждёт:\n\n"
                    "1️⃣ Пара общих вопросов —> ты находишься здесь\n"
                    "2️⃣ Нужно будет заполнить небольшую анкету о себе\n"
                    "3️⃣ По желанию предвыбор интересных собеседников, включая dating\n\n"
                "А в ближайший понедельник я подберу тебе задания на закрепрение новых слов\n\n"
                "👀 Подскажи, откуда ты обо мне узнал?\n"
            ),
        },
        "pick_lang": {
            "en": "What language would you like to learn?",
            "ru": "Какой язык ты будешь изучать?",
        },
        "fluency": {
            "en": "What is your level of fluency?",
            "ru": "Какой твой уровень владения языком?",
        },
        "fluency_levels": {
            "en": {
                "beginer": "🏁 Beginer",
                "intermediate": "👟 Intermediate",
                "advanced": "🦾 Advanced",
                "native": "🗿  Native",
            },

            "ru": {
                "beginer": "🏁 Начальный",
                "intermediate": "👟 Средний",
                "advanced": "🦾 Продвинутый",
                "native": "🗿  Родной",
            },
        },
        "choose_topic": {
            "en": "What interests you the most from the options below?",
            "ru": "Какое увлечение тебя интересует больше всего из предложенного выбора ниже?",
        },
        "topics": {
            "en": {
                "general": "🗞️ General",
                "music": "🎵  Music",
                "movies": "🍿  Movies",
                "sports": "🏈   Sports",
                "technology": "🧠 Technology",
                "travel": "✈️   Travel",
                "games": "🎮 Video games",
            },
            "ru": {
                "general": "🗞️   Обо всем",
                "music": "🎵  Музыка",
                "movies": "🍿  Фильмы",
                "sports": "🏈   Спорт",
                "technology": "🧠 Технологии",
                "travel": "✈️ Путешествия",
                "games": "🎮  Видеоигры",
            },
        },
        "terms": {
            "en": "In order to use our service, you must agree to the user agreement",
            "ru": "В целях использования нашего сервиса, вы должны подтвердить, что вы согласны с пользовательским соглашением",
        },
        # TODO: Исправить логику на более читаемый алгоритм
        "where_youcamefrom": {
            "en0": "🗣️ Friends told me",
            "ru0": "🗣️ Знакомые рассказали мне",
            "en1": "🌐 Found it on the Internet",
            "ru1": "🌐 Нашел в Интернете",
            "en2": "📇 Through an advertisement",
            "ru2": "📇 Через рекламу",
        },
    }
)

BUTTONS = dict(
    {
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
        "confirm": {
            "en": "I agree",
            "ru": "Согласен",
        },
    }
)

WEEKLY_QUIZ = dict(
    {
        "begin": {"en": "Start quiz", "ru": "Начать проверку знаний"},
        "weekly_report": {
            "en": (
                "📊 Your weekly report with learned words:\n\n"
                "Total words: {total}\n\n"
                "Click button below to proceed 👇"
            ),
            "ru": (
                "📊 Ваш еженедельный отчет по изученным словам:\n\n"
                "Всего слов: {total}\n\n"
                "Для начала проверки нажмите кнопку ниже 👇"
            ),
        },
        "no_rights": {
            "en": "No right answers",
            "ru": "Нет правильных ответов",
        },
        "no_wrongs": {
            "en": "No wrong answers",
            "ru": "Нет ошибочных ответов",
        },
        "question_text": {
            "en": (
                "❓ Question {idx}/{total}\n\n"
                "{sentence}\n\n"
                "Choose the right answer:"
            ),
            "ru": (
                "❓ Вопрос {idx}/{total}\n\n"
                "{sentence}\n\n"
                "Выберите правильный вариант:"
            ),
        },
        "right_answer": {
            "en": "<b>✅ That`s correct!</b>\n\n" "<b>Word:</b> <i>{correct_word}</i>",
            "ru": "<b>✅ Правильно!</b>\n\n" "<b>Слово:</b> <i>{correct_word}</i>",
        },
        "wrong_answer": {
            "en": (
                "❌ Unfortunately, that`s incorrect\n\n"
                "<b>Your answer:</b> <i>{selected_word}</i>\n"
                "<b>Correct answer:</b> <i>{correct_word}</i>\n"
            ),
            "ru": (
                "❌ К сожалению, неверно\n\n"
                "<b>Ваш ответ: </b><i>{selected_word}</i>\n"
                "<b>Правильный ответ: </b><i>{correct_word}</i>\n"
            ),
        },
        "congradulations": {
            "en": (
                "congrades! You completed this quiz for all the learned words this week.\n\n"
                "Words which you chose right: {rights}\n"
                "Words which you made a mistake with: {wrongs}\n"
            ),
            "ru": (
                "🎉 Поздравляем! Вы завершили проверку знаний по всем словам за эту неделю.\n\n"
                "Слова, на которые вы ответили правильно: {rights}\n"
                "Ошибочные ответы: {wrongs}\n"
            ),
        },
        "finish_button": {
            "en": "End this quiz",
            "ru": "Завершить тест",
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
            "ru": "обо всем",
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