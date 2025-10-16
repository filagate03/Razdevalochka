from __future__ import annotations

import logging
from typing import Any, Dict

from aiocryptopay import AioCryptoPay, Networks

logger = logging.getLogger(__name__)


class CryptoBotService:
    def __init__(self, token: str, network: Networks = Networks.MAIN_NET) -> None:
        self._client = AioCryptoPay(token=token, network=network)

    async def create_invoice(self, asset: str, amount: float, description: str) -> Dict[str, Any]:
        invoice = await self._client.create_invoice(asset=asset, amount=amount, description=description)
        logger.info("Created CryptoBot invoice %s", invoice.invoice_id)
        return {"invoice_id": invoice.invoice_id, "pay_url": invoice.bot_invoice_url}

    async def close(self) -> None:
        await self._client.close()
