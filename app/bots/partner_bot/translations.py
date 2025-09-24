MESSAGES = dict(
    {
        "hello": {
            "english": "👋 Hey, ",
            "russian": "👋 Привет, ",
            "german": "👋 Hallo, ",
            "spanish": "👋 Hola, ",
            "chinese": "👋 你好, ",
        },
        "intro": {
            "en": "Hi again! Here, I'll be looking for a partner, so you can chat with them\n",
            "ru": "Снова привет, в этом месте я буду искать тебе собеседника\n",
            "de": "Hallo nochmal, ich suche hier jemanden, der mit Ihnen reden kann\n",
            "es": "Hola de nuevo, estaré buscando alguien para hablar contigo en este lugar\n",
            "zh": "你好，我正在寻找可以在这里与你聊天的人\n"
        },
        "full_intro": {
            "en": "Don`t you want to talk to anyone? Tap <b>Search partner</b>, "
                  "and I'll find a person for you",
            "ru": "Не хочешь поговорить с кем-нибудь? Жми <b>Искать партнера</b>, "
                  "чтобы я подобрала тебе собеседника",
            "de": "Möchten Sie mit jemandem sprechen? Klicken Sie auf <b>Partner finden</b>, "
                  "damit ich Ihnen einen Gesprächspartner vermitteln kann",
            "es": "¿No quieres hablar con alguien? Pulsa <b>Buscar compañero</b>, "
                  "y encontraré una persona para ti",
            "zh": "你不想和任何人聊天吗？点击<b>搜索伙伴</b>，我会为你找到一个人"
        },
        "about": {
            "en": "You may ask me by tapping one of these options::\n\n"
                "\t/menu - return to the main menu\n"
                "\t/location - see your location\n"
                "\t/new_session - start a new conversation\n"
                "\t/restart - restart the bot\n\n"
                "if you see me I`m not answering or anything else, contact support. They`ll help",
            "ru": "Ты можешь попросить меня, выбрав следующие команды:\n\n"
                    "\t/menu - вернуться в главное меню\n"
                    "\t/location - увидеть свою геолокацию\n"
                    "\t/new_session - начать новое общение\n"
                    "\t/restart - перезапустить бота\n\n"
                "Если ты видишь, что я не отвечаю или что-то пошло не так, "
                "пожалуйста, напиши в тех. поддержку. Они помогут",
            "de": "Sie können mich durch Antippen einer dieser Optionen bitten::\n\n"
                "\t/menu - zum Hauptmenü zurückkehren\n"
                "\t/location - Ihren Standort anzeigen\n"
                "\t/new_session - ein neues Gespräch beginnen\n"
                "\t/restart - den Bot neu starten\n\n"
                "Wenn Sie sehen, dass ich nicht antworte oder sonst etwas, kontaktieren Sie den Support. Sie werden helfen",
            "es": "Puedes pedirme pulsando una de estas opciones::\n\n"
                "\t/menu - volver al menú principal\n"
                "\t/location - ver tu ubicación\n"
                "\t/new_session - comenzar una nueva conversación\n"
                "\t/restart - reiniciar el bot\n\n"
                "Si ves que no respondo o algo más, contacta con soporte. Ellos ayudarán",
            "zh": "您可以通过点击以下选项之一来请求我：：\n\n"
                "\t/menu - 返回主菜单\n"
                "\t/location - 查看您的位置\n"
                "\t/new_session - 开始新的对话\n"
                "\t/restart - 重新启动机器人\n\n"
                "如果您发现我没有回答或其他问题，请联系支持人员。他们会帮助您"
        },
        "user_info": {
            "en": "=== <b>{nickname}</b> ===\n\n"
                "Your age: <b>{age}</b>\n"
                "Chosen language: <b>{language}</b>\n"
                "Fluency: <b>{fluency}</b>\n"
                "Topic: <b>{topic}</b>\n\n"
                "About you: {about}",
            "ru": "=== <b>{nickname}</b> ===\n\n"
                "Твой возраст: <b>{age}</b>\n"
                "Выбранный язык: <b>{language}</b>\n"
                "Уровень владения: <b>{fluency}</b>\n"
                "Тема для разговора: <b>{topic}</b>\n\n"
                "О себе: {about}",
            "de": "=== <b>{nickname}</b> ===\n\n"
                "Ihr Alter: <b>{age}</b>\n"
                "Gewählte Sprache: <b>{language}</b>\n"
                "Sprachkenntnisse: <b>{fluency}</b>\n"
                "Thema: <b>{topic}</b>\n\n"
                "Über Sie: {about}",
            "es": "=== <b>{nickname}</b> ===\n\n"
                "Tu edad: <b>{age}</b>\n"
                "Idioma elegido: <b>{language}</b>\n"
                "Fluidez: <b>{fluency}</b>\n"
                "Tema: <b>{topic}</b>\n\n"
                "Sobre ti: {about}",
            "zh": "=== <b>{nickname}</b> ===\n\n"
                "您的年龄: <b>{age}</b>\n"
                "选择的语言: <b>{language}</b>\n"
                "流利程度: <b>{fluency}</b>\n"
                "话题: <b>{topic}</b>\n\n"
                "关于您: {about}"
        },
        "wrong_name": {
            "en": "There is either space or too many characters in your name (max 50)",
            "ru": "Есть пробел или слишком много символов в вашем имени (максимум 50)",
            "de": "Es gibt entweder Leerzeichen oder zu viele Zeichen in Ihrem Namen (max. 50)",
            "es": "Hay un espacio o demasiados caracteres en tu nombre (máximo 50)",
            "zh": "您的姓名中要么有空格，要么字符过多（最多50个字符）"
        },
        "wrong_birthday": {
            "en": "Incorrect format. Please, try again",
            "ru": "Неверный формат. Пожалуйста, попробуй ещё раз",
            "de": "Falsches Format. Bitte versuchen Sie es erneut",
            "es": "Formato incorrecto. Por favor, inténtalo de nuevo",
            "zh": "格式不正确。请再试一次"
        },
        "wrong_intro": {
            "en": "Your information is either too long or too short. Please, try again",
            "ru": "Твоя информация либо слишком длинная, либо слишком короткая. Пожалуйста, попробуй ещё раз",
            "de": "Ihre Informationen sind entweder zu lang oder zu kurz. Bitte versuchen Sie es erneut",
            "es": "Tu información es demasiado larga o demasiado corta. Por favor, inténtalo de nuevo",
            "zh": "您的信息要么太长，要么太短。请再试一次"
        },
        "success": {
            "en": "Thank you for your patience 🤝\nPress /menu to go to the main menu",
            "ru": "Спасибо за терпение 🤝\nНажми /menu, чтобы перейти в главное меню",
            "de": "Vielen Dank für Ihre Geduld 🤝\nDrücken Sie /menu, um zum Hauptmenü zu gelangen",
            "es": "Gracias por tu paciencia 🤝\nPresiona /menu para ir al menú principal",
            "zh": "感谢您的耐心 🤝\n按 /menu 返回主菜单"
        },
        "your_location": {
            "en": "🌎 Your location",
            "ru": "🌎 Твои гео-координаты",
            "de": "🌎 Ihr Standort",
            "es": "🌎 Tu ubicación",
            "zh": "🌎 您的位置"
        },
        "no_username": {
            "en": "You don't have a username, please, set one",
            "ru": "У тебя нет @username, пожалуйста, установи его",
            "de": "Sie haben keinen Benutzernamen, bitte setzen Sie einen",
            "es": "No tienes un nombre de usuario, por favor, establece uno",
            "zh": "您没有用户名，请设置一个"
        },
        "no_worries": {
            "en": "No worries 🫶 We won't use your location\nPress /menu to go to the main menu",
            "ru": "Ничего страшного 🫶 Мы не будем использовать твою геолокацию\nНажми /menu, чтобы перейти в главное меню",
            "de": "Keine Sorge 🫶 Wir werden Ihren Standort nicht verwenden\nDrücken Sie /menu, um zum Hauptmenü zu gelangen",
            "es": "No te preocupes 🫶 No usaremos tu ubicación\nPresiona /menu para ir al menú principal",
            "zh": "不用担心 🫶 我们不会使用您的位置\n按 /menu 返回主菜单"
        },
        "no_worries_dating": {
            "en": "Got it! We`ll find you a new friend.\nPress /menu to go to the main menu",
            "ru": "Понял, мы найдем тебе нового друга!\nНажми на /menu, чтобы перейти в главное меню",
            "de": "Verstanden! Wir finden Ihnen einen neuen Freund.\nDrücken Sie /menu, um zum Hauptmenü zu gelangen",
            "es": "¡Entendido! Te encontraremos un nuevo amigo.\nPresiona /menu para ir al menú principal",
            "zh": "明白了！我们会为您找到新朋友。\n按 /menu 返回主菜单"
        },
        "match_found": {
            "en": "Match has been found! Their nickname is <b>{nickname}</b>\n\nTap this button to start chat: ",
            "ru": "Мы нашли вам собеседника! Его псевдоним: <b>{nickname}</b>\n\nНажмите по кнопке ниже, чтобы перейти в чат: ",
            "de": "Ein Match wurde gefunden! Ihr Spitzname ist <b>{nickname}</b>\n\nTippen Sie auf diese Schaltfläche, um den Chat zu starten: ",
            "es": "¡Se ha encontrado una coincidencia! Su apodo es <b>{nickname}</b>\n\nPulsa este botón para comenzar a chatear: ",
            "zh": "已找到匹配！他们的昵称是 <b>{nickname}</b>\n\n点击此按钮开始聊天："
        },
        "show_queue_info": {
            "en": "Total in search: {total}\n\nMost spoken languages at the moment: {lans}",
            "ru": "Всего в поиске: {total}\n\nИспользуемые языки в очереди: {lans}",
            "de": "Gesamt in der Suche: {total}\n\nMeistgesprochene Sprachen im Moment: {lans}",
            "es": "Total en búsqueda: {total}\n\nIdiomas más hablados en este momento: {lans}",
            "zh": "搜索总数: {total}\n\n当前最常用的语言: {lans}"
        },
        "nobody_in_queue": {
            "en": "No one is looking for a match",
            "ru": "Никого нет, чтобы показать актуальные языки",
            "de": "Niemand sucht nach einem Match",
            "es": "Nadie está buscando una coincidencia",
            "zh": "没人在寻找匹配"
        },
        "its_just_you": {
            "en": "It`s just you",
            "ru": "Кроме Вас никого нет",
            "de": "Es sind nur Sie",
            "es": "Eres solo tú",
            "zh": "只有您一个人"
        },
        "cancel_search": {
            "en": "Ended search",
            "ru": "Поиск завершен",
            "de": "Suche beendet",
            "es": "Búsqueda terminada",
            "zh": "搜索已结束"
        },
    }
)

QUESTIONARY = dict(
    {
        "need_profile": {
            "en": "Let's get to know each other a bit better\n\n"
                "First, I`d like to ask you to <b>turn off your VPN</b> if you have one, "
                "so I can process your profile information right\n\n"
                "Okay, so what name do you want to be seen by others?\n",
            "ru": "Давайте познакомимся немного ближе\n\n"
                "Сначала, я бы хотела попросить тебя <b>выключить VPN</b> (если он у тебя есть), "
                "так я смогу обработать информацию правильно\n\n"
                "Хорошо, под каким именем ты хочешь, чтобы другие люди видели тебя?\n",
            "de": "Lernen wir uns etwas besser kennen\n\n"
                "Zuerst möchte ich Sie bitten, <b>Ihren VPN auszuschalten</b>, falls Sie einen haben, "
                "damit ich Ihre Profilinformationen richtig verarbeiten kann\n\n"
                "Okay, unter welchem Namen möchten Sie von anderen gesehen werden?\n",
            "es": "Vamos a conocernos un poco mejor\n\n"
                "Primero, me gustaría pedirte que <b>apagues tu VPN</b> si tienes uno, "
                "para que pueda procesar la información de tu perfil correctamente\n\n"
                "Bien, ¿qué nombre quieres que otros vean?\n",
            "zh": "让我们更好地了解彼此\n\n"
                "首先，如果您有VPN，我想请您<b>关闭VPN</b>，"
                "这样我就能正确处理您的个人资料信息\n\n"
                "好的，您希望别人看到什么名字？\n"
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
            "de": "Erzählen Sie mir ein paar Fakten über sich:\n\n"
                "Zum Beispiel, was machen Sie in Ihrer Freizeit?\n"
                "Vielleicht haben Sie ein cooles Hobby, eine Lieblingsfernsehsendung oder\n"
                "einen Ort für Spaziergänge? Jedes kleine Detail ist willkommen\n\n",
            "es": "Cuéntame algunos datos sobre ti:\n\n"
                "Por ejemplo, ¿qué haces en tu tiempo libre?\n"
                "¿Tal vez tienes un hobby genial, un programa de TV favorito o\n"
                "un lugar para pasear? Cualquier pequeño detalle es bienvenido\n\n",
            "zh": "告诉我一些关于您的事实：\n\n"
                "例如，您在空闲时间做什么？\n"
                "也许您有很酷的爱好、最喜欢的电视节目或\n"
                "散步的地方？欢迎任何小细节\n\n"
        },
        "need_location": {
            "en": "For the correct work of the application, your location is needed, please provide it by the button below.\n\n"
                "All your information is confidential. Your location will be stored in encrypted form.\n\n"
                "If you do not want us to use your location, click the 'Decline' button",
            "ru": "Мне нужна твоя геолокация, чтобы я в дальнейшем могла подбирать партнеров из твоего города, пожалуйста, предоставь ее по кнопке ниже.\n\n"
                "Вся твоя информация является конфидициальной. Геолокация будет хранится в зашифрованном виде.\n\n"
                "Если ты не хочешь, чтобы я пользовалась твоей геолокацией, просто нажми кнопку 'Отказаться'",
            "de": "Für die korrekte Funktion der Anwendung wird Ihr Standort benötigt, bitte geben Sie ihn über die Schaltfläche unten an.\n\n"
                "Alle Ihre Informationen sind vertraulich. Ihr Standort wird verschlüsselt gespeichert.\n\n"
                "Wenn Sie nicht möchten, dass wir Ihren Standort verwenden, klicken Sie auf die Schaltfläche 'Ablehnen'",
            "es": "Para el correcto funcionamiento de la aplicación, se necesita tu ubicación, por favor proporciónala mediante el botón de abajo.\n\n"
                "Toda tu información es confidencial. Tu ubicación se almacenará en forma cifrada.\n\n"
                "Si no quieres que usemos tu ubicación, haz clic en el botón 'Rechazar'",
            "zh": "为了应用程序的正常工作，需要您的位置，请通过下面的按钮提供。\n\n"
                "您的所有信息都是保密的。您的位置将以加密形式存储。\n\n"
                "如果您不希望我们使用您的位置，请点击'拒绝'按钮"
        },
        "need_dating": {
            "en": "Do you want to find a partner for a date?",
            "ru": "Ты хочешь найти вторую половинку?",
            "de": "Möchten Sie einen Partner für ein Date finden?",
            "es": "¿Quieres encontrar una pareja para una cita?",
            "zh": "您想找约会对象吗？"
        },
        "need_age": {
            "en": "How old are you?\n\n"
            "Please, enter birth date in format: <b>DD.MM.YYYY</b>\n\n",
            "ru": "Сколько тебе лет?\n\n"
            "Пожалуйста, введи дату рождения в формате: <b>ДД.ММ.ГГГГ</b>\n\n",
            "de": "Wie alt sind Sie?\n\n"
            "Bitte geben Sie das Geburtsdatum im Format ein: <b>TT.MM.JJJJ</b>\n\n",
            "es": "¿Cuántos años tienes?\n\n"
            "Por favor, introduce la fecha de nacimiento en formato: <b>DD.MM.AAAA</b>\n\n",
            "zh": "您多大了？\n\n"
            "请输入出生日期，格式为：<b>DD.MM.YYYY</b>\n\n"
        },
    }
)

BUTTONS = dict(
    {
        "about_bot": {
            "en": "ℹ️ About me",
            "ru": "ℹ️ Обо мне",
            "de": "ℹ️ Über mich",
            "es": "ℹ️ Acerca de mí",
            "zh": "ℹ️ 关于我"
        },
        "go_back": {
            "en": "🔙 Go Back",
            "ru": "🔙 Назад",
            "de": "🔙 Zurück",
            "es": "🔙 Volver",
            "zh": "🔙 返回"
        },
        "main_bot": {
            "en": "👾 Main menu",
            "ru": "👾 Основое меню",
            "de": "👾 Hauptmenü",
            "es": "👾 Menú principal",
            "zh": "👾 主菜单"
        },
        "profile": {
            "en": "👤 Profile",
            "ru": "👤 Профиль",
            "de": "👤 Profil",
            "es": "👤 Perfil",
            "zh": "👤 个人资料"
        },
        "search": {
            "en": "🔍 Search partner",
            "ru": "🔍 Искать партнера",
            "de": "🔍 Partner suchen",
            "es": "🔍 Buscar compañero",
            "zh": "🔍 搜索伙伴"
        },
        "queue_info": {
            "en": "❔Show queue info",
            "ru": "❔Показать очередь",
            "de": "❔Warteschlange anzeigen",
            "es": "❔Mostrar información de cola",
            "zh": "❔ 显示队列信息"
        },
        "cancel": {
            "en": "❌ Cancel",
            "ru": "❌ Отменить",
            "de": "❌ Abbrechen",
            "es": "❌ Cancelar",
            "zh": "❌ 取消"
        },
        "open_chat": {
            "en": "💬 Open chat",
            "ru": "💬 Открыть чат",
            "de": "💬 Chat öffnen",
            "es": "💬 Abrir chat",
            "zh": "💬 打开聊天"
        },
        "yes_to_dating": {
            "en": "🌹 Yes, I`d like to find a soul mate",
            "ru": "🌹 Да, я заинтересован в отношениях",
            "de": "🌹 Ja, ich möchte eine Seelenverwandte finden",
            "es": "🌹 Sí, me gustaría encontrar un alma gemela",
            "zh": "🌹 是的，我想找个灵魂伴侣"
        },
        "no_to_dating": {
            "en": "🍻🤜🤛 Nah, I want to find a friend",
            "ru": "🍻🤜🤛 Нет, я заинтересован в дружбе",
            "de": "🍻🤜🤛 Nein, ich möchte einen Freund finden",
            "es": "🍻🤜🤛 No, quiero encontrar un amigo",
            "zh": "🍻🤜🤛 不，我想找个朋友"
        },
        "location": {
            "en": "📍 Send location",
            "ru": "📍 Отправить геолокацию",
            "de": "📍 Standort senden",
            "es": "📍 Enviar ubicación",
            "zh": "📍 发送位置"
        },
        "decline": {
            "en": "❌ Decline",
            "ru": "❌ Отказаться",
            "de": "❌ Ablehnen",
            "es": "❌ Rechazar",
            "zh": "❌ 拒绝"
        },
    }
)


TRANSCRIPTIONS = dict({
    "came_from": {
        "friends": {
            "en": "through friends",
            "ru": "через знакомых",
            "de": "durch Freunde",
            "es": "a través de amigos",
            "zh": "通过朋友"
        },
        "search": {
            "en": "on internet",
            "ru": "по интернету",
            "de": "im Internet",
            "es": "en internet",
            "zh": "在互联网上"
        },
        "other": {
            "en": "through ads",
            "ru": "через рекламу",
            "de": "durch Werbung",
            "es": "a través de anuncios",
            "zh": "通过广告"
        },
    },
    "languages": {
        "russian": {
            "en": "Russian",
            "ru": "Русский",
            "de": "Russisch",
            "es": "Ruso",
            "zh": "俄语"
        },
        "english": {
            "en": "English",
            "ru": "Английский",
            "de": "Englisch",
            "es": "Inglés",
            "zh": "英语"
        },
        "german": {
            "en": "German",
            "ru": "Немецкий",
            "de": "Deutsch",
            "es": "Alemán",
            "zh": "德语"
        },
        "spanish": {
            "en": "Spanish",
            "ru": "Испанский",
            "de": "Spanisch",
            "es": "Español",
            "zh": "西班牙语"
        },
        "chinese": {
            "en": "Chinese",
            "ru": "Китайский",
            "de": "Chinesisch",
            "es": "Chino",
            "zh": "中文"
        }
    },
    "fluency": {
        "beginner": {
            "en": "beginner",
            "ru": "начальный",
            "de": "anfänger",
            "es": "principiante",
            "zh": "初级"
        },
        "intermediate": {
            "en": "intermediate",
            "ru": "средний",
            "de": "fortgeschritten",
            "es": "intermedio",
            "zh": "中级"
        },
        "advanced": {
            "en": "advanced",
            "ru": "продвинутый",
            "de": "weit fortgeschritten",
            "es": "avanzado",
            "zh": "高级"
        },
        "native": {
            "en": "native",
            "ru": "родной",
            "de": "muttersprache",
            "es": "nativo",
            "zh": "母语"
        }
    },
    "topics": {
        "general": {
            "en": "general",
            "ru": "обо всем",
            "de": "allgemein",
            "es": "general",
            "zh": "通用"
        },
        "music": {
            "en": "music",
            "ru": "музыка",
            "de": "musik",
            "es": "música",
            "zh": "音乐"
        },
        "sports": {
            "en": "sports",
            "ru": "спорт",
            "de": "sport",
            "es": "deportes",
            "zh": "体育"
        },
        "technology": {
            "en": "technology",
            "ru": "технологии",
            "de": "technologie",
            "es": "tecnología",
            "zh": "技术"
        },
        "travel": {
            "en": "travel",
            "ru": "путешествия",
            "de": "reisen",
            "es": "viajes",
            "zh": "旅行"
        },
        "games": {
            "en": "video games",
            "ru": "видео-игры",
            "de": "videospiele",
            "es": "videojuegos",
            "zh": "视频游戏"
        }
    },
    "status": {
        "rookie": {
            "en": "rookie",
            "ru": "зеленый",
            "de": "Anfänger",
            "es": "novato",
            "zh": "新手"
        }
    }
})