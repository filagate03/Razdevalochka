from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from bot_main.database import crud
from bot_main.database.session import get_session

logger = logging.getLogger(__name__)

app = FastAPI()


class YooKassaWebhook(BaseModel):
    object: Dict[str, Any]


class CloudPaymentsWebhook(BaseModel):
    TransactionId: str
    Status: str
    Amount: float
    AccountId: str


class CryptoBotWebhook(BaseModel):
    update_id: int
    update_type: str
    payload: Dict[str, Any]


@app.post("/yookassa_webhook")
async def yookassa_webhook(payload: YooKassaWebhook, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    payment = payload.object
    if payment.get("status") != "succeeded":
        return JSONResponse({"status": "ignored"})

    invoice_id = payment.get("id")
    metadata = payment.get("metadata", {})
    user_id = int(metadata.get("user_id"))
    await crud.update_transaction_status(session, invoice_id=invoice_id, status="completed", provider_payment_id=invoice_id)
    user = await crud.get_user_by_telegram_id(session, user_id)
    limit_bonus = 100 if (metadata.get("is_premium") or (user and user.is_premium)) else 10
    await crud.update_user_limits(session, user_id, limit_bonus)
    await crud.adjust_user_balance(session, user_id, float(payment["amount"]["value"]))
    logger.info("YooKassa payment completed for user %s", user_id)
    return JSONResponse({"status": "ok"})


@app.post("/cloudpayments_webhook")
async def cloudpayments_webhook(payload: CloudPaymentsWebhook, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    if payload.Status.lower() != "pay":
        return JSONResponse({"status": "ignored"})

    await crud.update_transaction_status(
        session,
        invoice_id=payload.TransactionId,
        status="completed",
        provider_payment_id=payload.TransactionId,
        completed_at=dt.datetime.utcnow(),
    )
    user_id = int(payload.AccountId)
    user = await crud.get_user_by_telegram_id(session, user_id)
    limit_bonus = 100 if (user and user.is_premium) else 10
    await crud.update_user_limits(session, user_id, limit_bonus)
    await crud.adjust_user_balance(session, user_id, float(payload.Amount))
    logger.info("CloudPayments payment completed for user %s", user_id)
    return JSONResponse({"code": 0})


@app.post("/cryptobot_webhook")
async def cryptobot_webhook(payload: CryptoBotWebhook, session: AsyncSession = Depends(get_session)) -> JSONResponse:
    if payload.update_type != "invoice_paid":
        return JSONResponse({"status": "ignored"})

    invoice = payload.payload
    invoice_id = str(invoice.get("invoice_id"))
    transaction = await crud.update_transaction_status(session, invoice_id=invoice_id, status="completed")
    user_id = transaction.user_id if transaction else int(invoice.get("description", "0") or 0)
    user = await crud.get_user_by_telegram_id(session, user_id)
    limit_bonus = 100 if (user and user.is_premium) else 10
    await crud.update_user_limits(session, user_id, limit_bonus)
    await crud.adjust_user_balance(session, user_id, float(invoice.get("amount")))
    logger.info("CryptoBot invoice paid for user %s", user_id)
    return JSONResponse({"status": "ok"})
