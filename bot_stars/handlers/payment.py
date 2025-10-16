from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, PreCheckoutQuery

from bot_main.database import crud
from bot_main.database.session import SessionFactory

logger = logging.getLogger(__name__)

router = Router()


def get_pay_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 50 ⭐", callback_data="pay_stars", pay=False)],
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    deep_link = message.text.split(maxsplit=1)[1] if message.text and len(message.text.split(maxsplit=1)) > 1 else ""
    await message.answer(
        "Добро пожаловать в Stars бот. Нажмите кнопку, чтобы оплатить.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Оплатить 50 ⭐", callback_data=f"pay_stars:{deep_link}")]]
        ),
    )


@router.callback_query(F.data.startswith("pay_stars"))
async def pay_stars(call: CallbackQuery) -> None:
    await call.answer()
    payload = call.data.split(":", 1)[1] if ":" in call.data else ""
    user_id = 0
    if payload.startswith("user_"):
        try:
            user_id = int(payload.split("_", 1)[1])
        except ValueError:
            user_id = 0

    prices = [LabeledPrice(label="XTR", amount=50)]
    await call.message.answer_invoice(
        title="Пополнение лимитов",
        description="Получите 10 генераций за 50 ⭐",
        prices=prices,
        payload=f"user_{user_id}",
        provider_token="",
        currency="XTR",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Оплатить 50 ⭐", pay=True)]]
        ),
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload or "user_0"
    try:
        user_id = int(payload.split("_", 1)[1])
    except ValueError:
        user_id = 0

    async with SessionFactory() as session:
        await crud.update_user_limits(session, user_id, 10)
        await crud.create_transaction(
            session,
            user_id=user_id,
            amount=payment.total_amount,
            currency="XTR",
            payment_method="telegram_stars",
            status="completed",
            provider_payment_id=payment.telegram_payment_charge_id,
        )
        await session.commit()

    await message.answer("✅ Оплата принята! Лимиты добавлены. Вернитесь в основной бот.")
    logger.info("Stars payment completed for user %s", user_id)
