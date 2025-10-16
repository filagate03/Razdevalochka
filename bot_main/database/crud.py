from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Generation, Transaction, User


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str], first_name: Optional[str]) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        user.last_activity = dt.datetime.utcnow()
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        registered_at=dt.datetime.utcnow(),
        last_activity=dt.datetime.utcnow(),
    )
    session.add(user)
    await session.flush()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def update_user_limits(session: AsyncSession, telegram_id: int, delta: int) -> None:
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(generations_left=User.generations_left + delta, last_activity=dt.datetime.utcnow())
    )


async def set_user_premium(session: AsyncSession, telegram_id: int, premium: bool) -> None:
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(is_premium=premium, last_activity=dt.datetime.utcnow())
    )


async def adjust_user_balance(session: AsyncSession, telegram_id: int, delta: float) -> None:
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(balance=func.coalesce(User.balance, 0) + delta, last_activity=dt.datetime.utcnow())
    )


async def create_transaction(
    session: AsyncSession,
    *,
    user_id: int,
    amount: float,
    currency: str,
    payment_method: str,
    status: str,
    invoice_id: Optional[str] = None,
    provider_payment_id: Optional[str] = None,
) -> Transaction:
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        status=status,
        invoice_id=invoice_id,
        provider_payment_id=provider_payment_id,
        created_at=dt.datetime.utcnow(),
        completed_at=dt.datetime.utcnow() if status == "completed" else None,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def update_transaction_status(
    session: AsyncSession,
    *,
    invoice_id: str,
    status: str,
    provider_payment_id: Optional[str] = None,
    completed_at: Optional[dt.datetime] = None,
) -> Optional[Transaction]:
    result = await session.execute(select(Transaction).where(Transaction.invoice_id == invoice_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        return None

    transaction.status = status
    transaction.provider_payment_id = provider_payment_id or transaction.provider_payment_id
    if status == "completed":
        transaction.completed_at = completed_at or dt.datetime.utcnow()
    await session.flush()
    return transaction


async def create_generation(
    session: AsyncSession,
    *,
    user_id: int,
    input_file_id: str,
    output_file_id: str,
) -> Generation:
    generation = Generation(
        user_id=user_id,
        input_file_id=input_file_id,
        output_file_id=output_file_id,
        created_at=dt.datetime.utcnow(),
    )
    session.add(generation)
    await session.flush()
    return generation


async def get_user_generations(session: AsyncSession, telegram_id: int, limit: int = 10) -> List[Generation]:
    result = await session.execute(
        select(Generation)
        .where(Generation.user_id == telegram_id)
        .order_by(Generation.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_statistics(session: AsyncSession) -> dict[str, float | int]:
    total_users = await session.scalar(select(func.count()).select_from(User))
    active_users = await session.scalar(
        select(func.count()).where(User.last_activity > dt.datetime.utcnow() - dt.timedelta(days=7))
    )
    total_generations = await session.scalar(select(func.count()).select_from(Generation))

    income_rub = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.currency == "RUB", Transaction.status == "completed"
        )
    )
    income_usdt = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.currency == "USDT", Transaction.status == "completed"
        )
    )
    income_ton = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.currency == "TON", Transaction.status == "completed"
        )
    )
    income_xtr = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.currency == "XTR", Transaction.status == "completed"
        )
    )

    return {
        "total_users": int(total_users or 0),
        "active_users": int(active_users or 0),
        "total_generations": int(total_generations or 0),
        "income_rub": float(income_rub or 0),
        "income_usdt": float(income_usdt or 0),
        "income_ton": float(income_ton or 0),
        "income_xtr": float(income_xtr or 0),
    }


async def list_users(session: AsyncSession) -> Iterable[User]:
    result = await session.execute(select(User).order_by(User.registered_at))
    return result.scalars().all()
