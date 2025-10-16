from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Update
from fastapi import HTTPException, Request
import uvicorn

from bot_main.config import get_settings
from bot_main.database.session import SessionFactory
from bot_main.handlers import admin as admin_handlers
from bot_main.handlers import payments as payments_handlers
from bot_main.handlers import user as user_handlers
from bot_main.middlewares.throttling import ThrottlingMiddleware
from bot_main.services.ai_api import AIService
from bot_main.webhook import app as fastapi_app

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

settings = get_settings()


def setup_dispatcher(bot: Bot) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottlingMiddleware(10))

    ai_service = AIService(settings.ai_api_url, settings.ai_api_key)

    async def session_middleware(handler, event, data):
        async with SessionFactory() as session:
            data["session"] = session
            data["ai_service"] = ai_service
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    dp.message.middleware.register(session_middleware)
    dp.callback_query.middleware.register(session_middleware)

    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(payments_handlers.router)

    return dp


async def set_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="balance", description="Баланс и лимиты"),
        BotCommand(command="buy", description="Пополнить лимиты"),
        BotCommand(command="history", description="История генераций"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)


async def start_webhook_server(stop_event: asyncio.Event) -> None:
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    stop_waiter = asyncio.create_task(stop_event.wait(), name="stop_event_waiter")
    server_task = asyncio.create_task(server.serve(), name="uvicorn_server")
    done, pending = await asyncio.wait({stop_waiter, server_task}, return_when=asyncio.FIRST_COMPLETED)
    if server_task in done:
        stop_event.set()
    else:
        server.should_exit = True
        await server_task
    for task in pending:
        task.cancel()


async def main() -> None:
    bot = Bot(token=settings.main_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = setup_dispatcher(bot)

    webhook_path = "/telegram-webhook"

    if not any(route.path == webhook_path for route in fastapi_app.router.routes):

        @fastapi_app.post(webhook_path)
        async def telegram_webhook(request: Request) -> dict[str, str]:  # type: ignore[misc]
            secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret != settings.webhook_secret:
                raise HTTPException(status_code=403, detail="Invalid secret token")
            data = await request.json()
            update = Update.model_validate(data)
            await dp.feed_webhook_update(bot, update)
            return {"status": "ok"}

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler(*_: object) -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal_handler)

    await bot.set_webhook(
        url=f"{settings.webhook_base_url}{webhook_path}",
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
    )
    await set_commands(bot)
    await dp.emit_startup(bot)

    tasks = [asyncio.create_task(start_webhook_server(stop_event), name="webhook_server")]

    await stop_event.wait()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await dp.emit_shutdown(bot)
    await bot.delete_webhook()
    await payments_handlers.crypto_service.close()
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
