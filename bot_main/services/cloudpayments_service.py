from __future__ import annotations

import base64
import logging
from typing import Any, Dict

import aiohttp

logger = logging.getLogger(__name__)


class CloudPaymentsService:
    def __init__(self, public_id: str, api_secret: str) -> None:
        credentials = f"{public_id}:{api_secret}".encode()
        self._auth_header = base64.b64encode(credentials).decode()

    async def create_payment(self, amount: float, currency: str, description: str, account_id: int) -> Dict[str, Any]:
        payload = {
            "Amount": amount,
            "Currency": currency,
            "Description": description,
            "AccountId": str(account_id),
        }

        headers = {"Authorization": f"Basic {self._auth_header}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.cloudpayments.ru/payments/cards/charge",
                json=payload,
                headers=headers,
                timeout=30,
            ) as response:
                data = await response.json()
                if response.status != 200 or not data.get("Success"):
                    logger.error("CloudPayments error: %s", data)
                    raise RuntimeError("CloudPayments charge failed")
                return data
