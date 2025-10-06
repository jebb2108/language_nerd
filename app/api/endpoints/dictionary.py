from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_db
from app.models.dict_models import UserDictionaryRequest
from config import config
from logging_config import opt_logger as log

logger = log.setup_logger('dictionary_endpoints', config.LOG_LEVEL)

router = APIRouter(prefix="/api")


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
            "context": word[4]
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
    is_publick = request.is_public
    context = request.context

    if not all([user_id, word, part_of_speech, translation]):
        raise HTTPException(status_code=400, detail="Missing fields")

    try:

        await db.add_word(user_id, word, part_of_speech, translation, is_publick, context)

    except Exception as e:
        logger.error(f"Error in api_add_word_handler: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "success"}


@router.get("/words/search")
async def api_search_word_handler(request: UserDictionaryRequest, db=Depends(get_db)):
    user_id = request.user_id
    word = request.word
    if not user_id or not word:
        raise HTTPException(status_code=400, detail="Missing parameters")
    try:
        result = await db.search_word(int(user_id), word)
        if result:
            return {
                "id": result[0],
                "word": result[1],
                "part_of_speech": result[2],
                "translation": result[3],
            }
        return {}

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