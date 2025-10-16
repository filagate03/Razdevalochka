from __future__ import annotations

import logging
from typing import Any, Dict

import aiohttp

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def process_image(self, image_bytes: bytes, mode: str = "enhance", quality: str = "high") -> bytes:
        data = {"mode": mode, "quality": quality}
        headers: Dict[str, str] = {"Authorization": f"Bearer {self._api_key}"}

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("image", image_bytes, filename="photo.jpg", content_type="image/jpeg")
            for key, value in data.items():
                form.add_field(key, value)

            async with session.post(self._base_url, data=form, headers=headers, timeout=60) as response:
                if response.status >= 400:
                    body = await response.text()
                    logger.error("AI API error %s: %s", response.status, body)
                    raise RuntimeError(f"AI API returned status {response.status}")

                return await response.read()
