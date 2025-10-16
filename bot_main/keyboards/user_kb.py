from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_payment_menu(user_id: int, stars_bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Карта РФ (ЮKassa) - 300₽", callback_data="pay_yookassa")],
            [InlineKeyboardButton(text="💳 Международная карта - $5", callback_data="pay_cloudpayments")],
            [InlineKeyboardButton(text="💎 USDT TRC20", callback_data="pay_usdt")],
            [InlineKeyboardButton(text="⚡ TON", callback_data="pay_ton")],
            [
                InlineKeyboardButton(
                    text="⭐ Telegram Stars",
                    url=f"https://t.me/{stars_bot_username}?start=user_{user_id}",
                )
            ],
        ]
    )


def get_buy_button(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пополнить баланс", callback_data="open_pay")]])
