from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot_main.config import get_settings
from bot_main.database import crud
from bot_main.keyboards.user_kb import get_payment_menu
from bot_main.services.ai_api import AIService

logger = logging.getLogger(__name__)

router = Router()
settings = get_settings()


@router.message(F.command == "start")
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
    if user.is_banned:
        await message.answer("🚫 Доступ к сервису ограничен. Свяжитесь с поддержкой.")
        return

    text = (
        "👋 Добро пожаловать в AI обработку фото!\n\n"
        f"Доступно генераций: {user.generations_left}\n"
        "Отправьте фото, и мы улучшим его за секунды."
    )
    await message.answer(text, reply_markup=get_payment_menu(user.telegram_id, settings.stars_bot_username))


@router.message(F.command == "balance")
async def cmd_balance(message: Message, session: AsyncSession) -> None:
    user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
    text = (
        f"💰 Баланс: {user.balance:.2f}\n"
        f"🎯 Лимиты: {user.generations_left}\n"
        f"⭐ Премиум: {'Да' if user.is_premium else 'Нет'}"
    )
    await message.answer(text)


@router.message(F.command == "buy")
async def cmd_buy(message: Message, session: AsyncSession) -> None:
    user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "Выберите способ оплаты:", reply_markup=get_payment_menu(user.telegram_id, settings.stars_bot_username)
    )


@router.message(F.command == "help")
async def cmd_help(message: Message) -> None:
    await message.answer(
        "ℹ️ Отправьте фото — получите улучшенную версию.\n"
        "Пополните лимиты через /buy. Вопросы — /support."
    )


@router.message(F.command == "history")
async def cmd_history(message: Message, session: AsyncSession) -> None:
    generations = await crud.get_user_generations(session, message.from_user.id)
    if not generations:
        await message.answer("История пуста. Отправьте фото для обработки.")
        return

    for generation in generations:
        await message.answer_photo(generation.output_file_id, caption=generation.created_at.strftime("%d.%m %H:%M"))


@router.message(F.photo)
async def handle_photo(message: Message, session: AsyncSession, ai_service: AIService) -> None:
    user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)

    if user.is_banned:
        await message.answer("🚫 Вы заблокированы в сервисе.")
        return

    if user.generations_left <= 0:
        await message.answer(
            "❌ Лимит исчерпан. Пополните баланс:",
            reply_markup=get_payment_menu(user.telegram_id, settings.stars_bot_username),
        )
        return

    status = await message.answer("⏳ Обрабатываю фото...")
    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        stream = await message.bot.download_file(file.file_path)
        image_bytes = stream.read()

        result_bytes = await ai_service.process_image(image_bytes)
        result_file = BufferedInputFile(result_bytes, filename="result.jpg")
        sent = await message.answer_photo(result_file, caption="✅ Готово!")

        await crud.create_generation(
            session,
            user_id=user.telegram_id,
            input_file_id=photo.file_id,
            output_file_id=sent.photo[-1].file_id,
        )
        await crud.update_user_limits(session, user.telegram_id, -1)
        await status.delete()
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("Error processing photo: %s", exc)
        await status.edit_text("❌ Ошибка обработки. Попробуйте позже.")
