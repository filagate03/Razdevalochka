from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from yookassa import Configuration, Payment

logger = logging.getLogger(__name__)


class YooKassaService:
    def __init__(self, shop_id: str, secret_key: str) -> None:
        Configuration.configure(shop_id, secret_key)

    def create_payment(
        self,
        amount: float,
        currency: str,
        return_url: str,
        user_id: int,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        transaction_id = str(uuid.uuid4())
        metadata_payload = {"user_id": user_id, "transaction_id": transaction_id}
        if metadata:
            metadata_payload.update(metadata)
        payment = Payment.create(
            {
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "confirmation": {"type": "redirect", "return_url": return_url},
                "description": "Пополнение баланса",
                "metadata": metadata_payload,
            }
        )
        logger.info("Created YooKassa payment %s for user %s", payment.id, user_id)
        return {"payment_id": payment.id, "confirmation_url": payment.confirmation.confirmation_url}
