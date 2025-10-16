from __future__ import annotations

import logging
from typing import Iterable

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot_main.config import get_settings
from bot_main.database import crud
from bot_main.database.models import User
from bot_main.keyboards.admin_kb import admin_menu

logger = logging.getLogger(__name__)

router = Router()
settings = get_settings()


class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    confirmation = State()


def is_admin(message: Message | CallbackQuery) -> bool:
    user_id = message.from_user.id if message.from_user else None
    return bool(user_id and user_id in settings.admin_ids)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    await message.answer("Админ-панель", reply_markup=admin_menu)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    stats = await crud.get_statistics(session)
    text = (
        "📊 Статистика:\n"
        f"Всего пользователей: {stats['total_users']}\n"
        f"Активных за 7 дней: {stats['active_users']}\n"
        f"Всего генераций: {stats['total_generations']}\n"
        f"Доход RUB: {stats['income_rub']:.2f}\n"
        f"Доход USDT: {stats['income_usdt']:.2f}\n"
        f"Доход TON: {stats['income_ton']:.2f}\n"
        f"Доход Stars: {stats['income_xtr']:.2f}\n"
    )
    await message.answer(text)


@router.message(Command("user"))
async def cmd_user(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    if not command.args:
        await message.answer("Использование: /user <telegram_id>")
        return
    try:
        telegram_id = int(command.args)
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    user = await crud.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("Пользователь не найден")
        return

    text = (
        f"👤 ID: {user.telegram_id}\n"
        f"Username: @{user.username}\n"
        f"Баланс: {user.balance}\n"
        f"Лимиты: {user.generations_left}\n"
        f"Премиум: {'Да' if user.is_premium else 'Нет'}\n"
        f"Заблокирован: {'Да' if user.is_banned else 'Нет'}\n"
        f"Последняя активность: {user.last_activity}"
    )
    await message.answer(text)


@router.message(Command("addlimits"))
async def cmd_addlimits(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    if not command.args:
        await message.answer("Использование: /addlimits <telegram_id> <количество>")
        return
    try:
        user_id_str, amount_str = command.args.split()
        user_id = int(user_id_str)
        amount = int(amount_str)
    except ValueError:
        await message.answer("Неверные параметры")
        return
    await crud.update_user_limits(session, user_id, amount)
    await message.answer(f"Добавлено {amount} лимитов пользователю {user_id}")


@router.message(Command("setpremium"))
async def cmd_setpremium(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    if not command.args:
        await message.answer("Использование: /setpremium <telegram_id>")
        return
    try:
        user_id = int(command.args)
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    await crud.set_user_premium(session, user_id, True)
    await message.answer(f"Пользователь {user_id} получил премиум")


@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    if not command.args:
        await message.answer("Использование: /ban <telegram_id>")
        return
    try:
        user_id = int(command.args)
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    await session.execute(
        User.__table__.update().where(User.telegram_id == user_id).values(is_banned=True)
    )
    await message.answer(f"Пользователь {user_id} заблокирован")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        await message.answer("⛔ Доступ запрещен")
        return
    await message.answer("Введите текст рассылки:")
    await state.set_state(BroadcastStates.waiting_for_text)


@router.message(BroadcastStates.waiting_for_text)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    await state.update_data(text=message.text)
    await message.answer("Отправьте фото (или /skip):")
    await state.set_state(BroadcastStates.waiting_for_photo)


@router.message(Command("skip"), BroadcastStates.waiting_for_photo)
async def broadcast_skip_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo=None)
    await state.set_state(BroadcastStates.confirmation)
    data = await state.get_data()
    await message.answer(f"Подтвердите рассылку:\n\n{data['text']}\n\nОтправить? (да/нет)")


@router.message(BroadcastStates.waiting_for_photo, F.photo)
async def broadcast_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(BroadcastStates.confirmation)
    data = await state.get_data()
    await message.answer(f"Подтвердите рассылку:\n\n{data['text']}\n\nОтправить? (да/нет)")


@router.message(BroadcastStates.confirmation)
async def broadcast_confirm(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.text and message.text.lower() not in {"да", "yes"}:
        await message.answer("Рассылка отменена")
        await state.clear()
        return

    data = await state.get_data()
    await message.answer("Начинаю рассылку...")
    users: Iterable[User] = await crud.list_users(session)
    total = 0
    async for chunk in _broadcast_iter(message.bot, users, data):
        total += chunk
        await message.answer(f"Отправлено: {total}")
    await message.answer("Рассылка завершена")
    await state.clear()


async def _broadcast_iter(bot, users: Iterable[User], data: dict):
    sent = 0
    text = data.get("text", "")
    photo = data.get("photo")
    for user in users:
        try:
            if photo:
                await bot.send_photo(user.telegram_id, photo, caption=text)
            else:
                await bot.send_message(user.telegram_id, text)
            sent += 1
            if sent % 100 == 0:
                yield 100
        except Exception:  # pragma: no cover
            logger.exception("Broadcast error for user %s", user.telegram_id)
    if sent % 100:
        yield sent % 100
