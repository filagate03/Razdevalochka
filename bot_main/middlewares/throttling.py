from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 10.0) -> None:
        super().__init__()
        self.rate_limit = rate_limit
        self._timestamps: Dict[int, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            async with self._lock:
                last_call = self._timestamps[event.from_user.id]
                now = time.time()
                if now - last_call < self.rate_limit:
                    await event.answer("⏳ Подождите несколько секунд перед следующей генерацией.")
                    return None
                self._timestamps[event.from_user.id] = now
        return await handler(event, data)
