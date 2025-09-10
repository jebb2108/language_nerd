import asyncio
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

    await rabbit.publish_delayed_message({"data": "test"}, 5000)


if __name__ == "__main__":
    asyncio.run(main())
