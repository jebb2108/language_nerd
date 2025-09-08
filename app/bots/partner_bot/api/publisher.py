import asyncio
import aio_pika
from app.dependencies import get_rabbitmq


async def main():
    rabbit = await get_rabbitmq()
    await rabbit.publish_message(
        {
            "user_id": 2345,
            "username": "gabriel",
            "criteria": {"language": "english", "dating": "true"},
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
