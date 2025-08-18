import logging
import asyncio
import os
from bs4 import BeautifulSoup
from urllib.parse import quote

from aiohttp import web, ClientSession, ClientTimeout
from config import LOG_CONFIG

logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(name='web_launcher')

db = None

def get_base_path():
    return os.path.dirname(os.path.abspath(__file__))

async def api_parse_word_handler(request):
    """API для парсинга определений слова с Merriam-Webster"""
    try:
        word = request.match_info['word']

        # Обработка слова для URL
        word_clean = word.strip().lower().replace(' ', '-')
        word_encoded = quote(word_clean, safe='-_.')
        url = f"https://www.merriam-webster.com/dictionary/{word_encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        timeout = ClientTimeout(total=10)
        try:
            async with ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        definitions = []
                        # Поиск элементов с определениями
                        for item in soup.select('.dtText, .sb .dtText, .vg .dtText'):
                            text = item.get_text().strip()

                            # Удаление начальных символов : и пробелов
                            if text.startswith(':'):
                                text = text[1:].strip()

                            # Удаление примеров использования в скобках
                            if '(' in text and ')' in text:
                                text = text.split('(')[0].strip()

                            definitions.append(text)
                            if len(definitions) >= 3:
                                break

                        return web.json_response(definitions[:3])

                    return web.json_response(
                        {"error": f"Слово не найдено или ошибка сервера (HTTP {resp.status})"},
                        status=resp.status
                    )

        except asyncio.TimeoutError:
            return web.json_response({"error": "Таймаут запроса"}, status=504)

    except Exception as e:
        logger.error(f"Ошибка в api_parse_word_handler: {str(e)}")
        return web.json_response({"error": "Внутренняя ошибка сервера"}, status=500)


async def index_handler(request):
    """Обработчик главной страницы"""
    base_path = get_base_path()
    index_path = os.path.join(base_path, '../web/templates/index.html')
    return web.FileResponse(index_path)


async def api_words_handler(request):
    """API для получения слов пользователя"""
    try:
        user_id = request.query.get('user_id')
        if not user_id:
            return web.json_response({"error": "User ID is required"}, status=400)

        words = await db.get_words(int(user_id))
        words_json = [
            {
                'id': word[0],
                'word': word[1],
                'part_of_speech': word[2],
                'translation': word[3]
            } for word in words
        ]
        return web.json_response(words_json)
    except Exception as e:
        logger.error(f"Error in api_words_handler: {str(e)}")
        return web.json_response({"error": "Internal server error"}, status=500)


async def api_add_word_handler(request):
    """API для добавления слова"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        word = data.get('word')
        part_of_speech = data.get('part_of_speech')
        translation = data.get('translation')

        if not all([user_id, word, part_of_speech, translation]):
            return web.json_response({"error": "Missing fields"}, status=400)
        await db.add_word(int(user_id), word, part_of_speech, translation)
        return web.json_response({"status": "success"})
    except Exception as e:
        logger.error(f"Error in api_add_word_handler: {str(e)}")
        return web.json_response({"error": "Internal server error"}, status=500)


async def api_full_search_handler(request):
    """Комбинированный обработчик поиска слова в БД и парсинга определений"""
    try:
        user_id = request.query.get('user_id')
        word = request.query.get('word')
        if not user_id or not word:
            return web.json_response({"error": "Missing parameters"}, status=400)

        # 1. Поиск в базе данных пользователя
        db_result = None
        try:
            result = await db.search_word(int(user_id), word)
            if result:
                db_result = {
                    'id': result[0],
                    'word': result[1],
                    'part_of_speech': result[2],
                    'translation': result[3]
                }
        except Exception as e:
            logger.error(f"Database search error: {str(e)}")

        # 2. Парсинг определений с сайта
        definitions = []
        try:
            word_clean = word.strip().lower().replace(' ', '-')
            word_encoded = quote(word_clean, safe='-_.')
            url = f"https://www.merriam-webster.com/dictionary/{word_encoded}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            timeout = ClientTimeout(total=10)
            async with ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # Извлекаем определения
                        for item in soup.select('.dtText, .sb .dtText, .vg .dtText'):
                            text = item.get_text().strip()

                            # Очистка текста
                            if text.startswith(':'):
                                text = text[1:].strip()
                            if '(' in text and ')' in text:
                                text = text.split('(', 1)[0].strip()

                            definitions.append(text)
                            if len(definitions) >= 3:
                                break
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}")

        return web.json_response({
            'db_result': db_result,
            'definitions': definitions[:3]  # Не более 3 определений
        })

    except Exception as e:
        logger.error(f"Error in api_full_search_handler: {str(e)}")
        return web.json_response({"error": "Internal server error"}, status=500)

async def api_delete_word_handler(request):
    """API для удаления слова"""
    try:
        user_id = request.query.get('user_id')
        word = int(request.match_info['word_id'])
        if not user_id:
            return web.json_response({"error": "User ID is required"}, status=400)

        await db.delete_word(int(user_id), word)
        return web.json_response({"status": "deleted"})
    except Exception as e:
        logger.error(f"Error in api_delete_word_handler: {str(e)}")
        return web.json_response({"error": "Internal server error"}, status=500)


async def api_stats_handler(request):
    """API для статистики"""
    try:
        user_id = request.query.get('user_id')
        if not user_id:
            return web.json_response({"error": "User ID is required"}, status=400)

        stats = await db.get_user_stats(int(user_id))
        return web.json_response({
            'total_words': stats[0],
            'nouns': stats[1],
            'verbs': stats[2]
        })
    except Exception as e:
        logger.error(f"Error in api_stats_handler: {str(e)}")
        return web.json_response({"error": "Internal server error"}, status=500)




async def start_web_app(database):
    global db
    """Запуск веб-сервера"""
    app = web.Application()
    db = database
    # Основные роутеры
    app.router.add_get('/', index_handler)
    app.router.add_get('/api/words', api_words_handler)
    app.router.add_post('/api/words', api_add_word_handler)
    app.router.add_get('/api/words/search', api_parse_word_handler)
    app.router.add_delete('/api/words/{word_id}', api_delete_word_handler)
    # app.router.add_get('/api/parse/{word}', api_parse_word_handler)
    app.router.add_get('/api/stats', api_stats_handler)

    # Статические файлы
    static_path = os.path.join(get_base_path(), '../web/static')
    app.router.add_static('/static/', static_path)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 2222)
    await site.start()
    logger.info("Web server started on port 2222")
    return runner