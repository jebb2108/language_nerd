KEY = "7715248537:AAGHC6W-52_TMYn9L2n7vmBCaToSejpryAw"

GREETING = ( "\n\nЭтот бот поможет тебе:\n\n"
            
"📖 Сохранять новые английские слова, чтобы они всегда были под рукой.\n"
"💬 Находить собеседников для практики — общайся и улучшай разговорный навык!\n"
"✍️ Писать эссе — получай интересные темы и полезные советы.\n\n"
            
"Готов прокачать английский? Начни прямо сейчас!\n\n"
            
"👉 Чтобы добавить новое слово, введи /addword.\n"
"👉 Хочешь пообщаться? Используй команду /findpartner.\n"
"👉 Нужна тема для эссе? Жми /essaytopic.\n\n"
            
"Let’s make your English unstoppable! 🚀")

CREATE_TABLE = ("CREATE TABLE IF NOT EXISTS words ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "word TEXT NOT NULL, "
    "part_of_speech TEXT NULL, "
    "translation TEXT NULL)")

INSERT_WORD = "INSERT INTO words (word, part_of_speech, translation) VALUES (?, ?, ?)"

UPDATE_PART_OF_SPEECH = "UPDATE words SET part_of_speech = ? WHERE word = ?"

UPDATE_TRANSLATION = "UPDATE words SET translation = ? WHERE word = ?"

SELECT_WORD = "SELECT * FROM words WHERE word = ?"

