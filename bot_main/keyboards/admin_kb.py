from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


admin_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance")],
        [InlineKeyboardButton(text="🔧 Настройки", callback_data="admin_settings")],
    ]
)
