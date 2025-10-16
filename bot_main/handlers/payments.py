from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot_main.config import get_settings
from bot_main.database import crud
from bot_main.keyboards.user_kb import get_payment_menu
from bot_main.services.cloudpayments_service import CloudPaymentsService
from bot_main.services.cryptobot_service import CryptoBotService
from bot_main.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)

router = Router()
settings = get_settings()

yookassa_service = YooKassaService(settings.yookassa_shop_id, settings.yookassa_secret_key)
cloudpayments_service = CloudPaymentsService(settings.cloudpayments_public_id, settings.cloudpayments_api_secret)
crypto_service = CryptoBotService(settings.cryptobot_api_token)


@router.callback_query(lambda c: c.data == "open_pay")
async def open_pay(call: CallbackQuery, session: AsyncSession) -> None:
    await call.answer()
    await call.message.edit_text(
        "Выберите способ оплаты:",
        reply_markup=get_payment_menu(call.from_user.id, settings.stars_bot_username),
    )


@router.callback_query(lambda c: c.data == "pay_yookassa")
async def pay_yookassa(call: CallbackQuery, session: AsyncSession) -> None:
    await call.answer()
    user = await crud.get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.first_name)
    bot_info = await call.bot.get_me()
    payment = yookassa_service.create_payment(
        300.0,
        "RUB",
        f"https://t.me/{bot_info.username}",
        user.telegram_id,
        metadata={"is_premium": user.is_premium},
    )
    await crud.create_transaction(
        session,
        user_id=user.telegram_id,
        amount=300.0,
        currency="RUB",
        payment_method="yookassa",
        status="pending",
        invoice_id=payment["payment_id"],
    )
    await call.message.answer(f"Оплатите по ссылке: {payment['confirmation_url']}")


@router.callback_query(lambda c: c.data == "pay_cloudpayments")
async def pay_cloudpayments(call: CallbackQuery, session: AsyncSession) -> None:
    await call.answer()
    user = await crud.get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.first_name)
    result = await cloudpayments_service.create_payment(5.0, "USD", "Пополнение баланса", user.telegram_id)
    await crud.create_transaction(
        session,
        user_id=user.telegram_id,
        amount=5.0,
        currency="USD",
        payment_method="cloudpayments",
        status="processing",
        invoice_id=str(result.get("Model", {}).get("TransactionId")),
    )
    await call.message.answer("Форма оплаты отправлена. Следуйте инструкциям CloudPayments.")


@router.callback_query(lambda c: c.data == "pay_usdt")
async def pay_usdt(call: CallbackQuery, session: AsyncSession) -> None:
    await call.answer()
    user = await crud.get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.first_name)
    invoice = await crypto_service.create_invoice("USDT", 5.0, f"Пополнение для @{call.from_user.username or call.from_user.id}")
    await crud.create_transaction(
        session,
        user_id=user.telegram_id,
        amount=5.0,
        currency="USDT",
        payment_method="cryptobot_usdt",
        status="pending",
        invoice_id=str(invoice["invoice_id"]),
    )
    await call.message.answer(f"Ссылка для оплаты: {invoice['pay_url']}")


@router.callback_query(lambda c: c.data == "pay_ton")
async def pay_ton(call: CallbackQuery, session: AsyncSession) -> None:
    await call.answer()
    user = await crud.get_or_create_user(session, call.from_user.id, call.from_user.username, call.from_user.first_name)
    invoice = await crypto_service.create_invoice("TON", 5.0, f"Пополнение для @{call.from_user.username or call.from_user.id}")
    await crud.create_transaction(
        session,
        user_id=user.telegram_id,
        amount=5.0,
        currency="TON",
        payment_method="cryptobot_ton",
        status="pending",
        invoice_id=str(invoice["invoice_id"]),
    )
    await call.message.answer(f"Ссылка для оплаты: {invoice['pay_url']}")
