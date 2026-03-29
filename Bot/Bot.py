import asyncio
import logging
from aiogram import Bot, Dispatcher

from TgBot.Bot.database.init_db import init_db, engine
from TgBot.Bot.middleware.promptBootstrap import PromptBootstrapMiddleware
from handlers import handler
from TgBot.ENV import env
from models import Base

logging.basicConfig(level=logging.INFO)


async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    bot = Bot(token=env.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_routers(handler.rt)
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(on_startup)
    dp.update.middleware(PromptBootstrapMiddleware())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
