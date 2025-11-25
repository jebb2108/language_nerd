from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_db, get_redis
from app.models.dict_models import UserDictionaryRequest
from config import config
from exc import PaymentException
from logging_config import opt_logger as log

router = APIRouter(prefix="/api")
logger = log.setup_logger('dictionary_endpoints')


@router.get("/words")
async def api_words_handler(
    user_id: int = Query(..., description="User ID"),
    db=Depends(get_db),
):
    words = await db.get_words(user_id)
    return [
        {
            "id": word[0],
            "word": word[1],
            "part_of_speech": word[2],
            "translation": word[3],
            "is_public": word[4],
            "context": word[5]
        }
        for word in words
    ]


@router.post("/words")
async def api_add_word_handler(
    request: UserDictionaryRequest,
    db=Depends(get_db),
):
    user_id = request.user_id
    word = request.word
    part_of_speech = request.part_of_speech
    translation = request.translation
    is_public = request.is_public
    context = request.context

    if not all([user_id, word, part_of_speech, translation]):
        raise HTTPException(status_code=400, detail="Missing fields")
    try:
        await db.add_word(user_id, word, part_of_speech, translation, is_public, context)

    except PaymentException:
        logger.error("User is not active")
        raise HTTPException(status_code=403, detail="User is not active")

    except Exception as e:
        logger.error(f"Error in api_add_word_handler: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "success"}


@router.get("/words/search")
async def api_search_word_handler(
        request: UserDictionaryRequest,
        redis=Depends(get_redis),
        db=Depends(get_db)
):
    user_id = request.user_id
    word = request.word
    if not user_id or not word:
        raise HTTPException(status_code=400, detail="Missing parameters")

    try:
        # Ищем слово от других участников
        all_users_words = await redis.get_searched_words(word)
        if not all_users_words:
            all_users_words: dict = await db.get_words_by_different_users(word)
            interval = config.CACHE_INTERVAL_PER_SEARCH
            await redis.save_search_result(word, all_users_words, interval)

        # Находим слово самого пользователя (если есть)
        this_user_word = await db.search_word(int(user_id), word)
        return {"user_word": this_user_word, "all_users_words": all_users_words}

    except Exception as e:
        logger.error(f"Error in api_search_word_handler: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/words/{word_id}")
async def api_delete_word_handler(word_id: int, user_id: int, db=Depends(get_db)):
    if not user_id or not word_id:
        raise HTTPException(status_code=400, detail="Missing parameters")

    await db.delete_word(user_id, word_id)
    return {"status": "deleted"}


@router.get("/stats")
async def api_stats_handler(user_id: int, db=Depends(get_db)):

    stats = await db.get_user_stats(user_id)
    # Гарантируем, что всегда возвращаем все поля
    if stats is None:
        return {"total_words": 0, "nouns": 0, "verbs": 0}

    return {
        "total_words": stats[0], "nouns": stats[1], "verbs": stats[2]
    }