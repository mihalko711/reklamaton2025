import asyncio
import sqlite3

from aiogram import Bot, Dispatcher, BaseMiddleware
from dotenv import load_dotenv

from user_bio_registration import user_route

load_dotenv()
import os

from handlers import router

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            zodiac_sign TEXT,
            height REAL,
            weight REAL,
            has_children BOOLEAN,
            attitude_alcohol INTEGER,
            attitude_tobacco INTEGER
        )
    ''')
    conn.commit()
    conn.close()


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        conn = sqlite3.connect('users.db')
        try:
            data['db'] = conn
            result = await handler(event, data)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


dp.message.middleware(DatabaseMiddleware())
dp.include_router(router)
dp.include_router(user_route)


async def main():
    init_db()
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
