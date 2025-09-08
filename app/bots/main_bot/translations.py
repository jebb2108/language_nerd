MESSAGES = dict(
    {
        "hello": {
            "en": "👋 Hello, ",
            "ru": "👋 Привет, ",
        },
        "welcome": {
            "en": (
                "I'm so glad to see you here and"
                "will be your language learning assistant. Here's what I can do:\n\n"
                "✨ <b>Dictionary</b> — save and learn new words easily\n"
                "🤝 <b>Practice</b> — chat with other students (coming soon!)\n"
                "🛠 <b>Technical support</b> — I'll help if something breaks\n\n"
                "Just choose what interests you by clicking one of the buttons below! 😊"
            ),
            "ru": (
                "Очень рад видеть тебя здесь!\n\n"
                "Я — твой помощник в изучении языков, и вот что умею:\n\n"
                "✨ <b>Словарь</b> — сохраняй и учи новые слова легко\n"
                "🤝 <b>Практика</b> — общайся с другими учениками (скоро запуск!)\n"
                "🛠 <b>Техподдержка</b> — помогу, если что-то сломалось\n\n"
                "Просто выбери, что тебя интересует, нажав на одну из кнопок ниже! 😊"
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
                "Welcome! Here are the next steps for you:\n\n"
                "1️⃣ A few general questions — you're here\n"
                "2️⃣ Filling out a questionnaire about yourself\n"
                "3️⃣ By choice Preselection of interesting interviewees\n\n"
                "And in the next Monday, the bots will choose tasks to reinforce new words\n\n"
                "👀 Tell me where you heard about us?\n"
            ),
            "ru": (
                "Добро пожаловать! Вот что тебя ждёт:\n\n"
                "1️⃣ Пара общих вопросов —> ты находишься здесь\n"
                "2️⃣ В боте-собесденике нужно будет заполнить анкету о себе\n"
                "3️⃣ По желанию предвыбор интересных собеседников, включая dating\n\n"
                "А в ближайший понедельник бот подберет тебе задания на закрепрение новых слов\n\n"
                "👀 Подскажи, откуда ты о нас узнал?\n"
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
        "terms": {
            "en": "In order to use our service, you must agree to the user agreement",
            "ru": "В целях использования нашего сервиса, вы должны подтвердить, что вы согласны с пользовательским соглашением",
        },
        # TODO: Исправить логику на более читаемый алгоритм
        "where_youcamefrom": {
            "en0": "My coworkers or friends told me",
            "ru0": "Мои коллеги или друзья рассказали мне",
            "en1": "Found it on the Internet",
            "ru1": "Нашел в Интернете",
            "en2": "Through an advertisement",
            "ru2": "Через рекламу",
        },
    }
)

BUTTONS = dict(
    {
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
