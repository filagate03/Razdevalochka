from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    balance = Column(Numeric(10, 2), default=0)
    generations_left = Column(Integer, default=5)
    is_premium = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=dt.datetime.utcnow)
    last_activity = Column(DateTime, default=dt.datetime.utcnow, index=True)

    generations = relationship("Generation", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    amount = Column(Numeric(10, 2))
    currency = Column(String(10))
    payment_method = Column(String(30))
    status = Column(String(20), default="pending", index=True)
    invoice_id = Column(String(255))
    provider_payment_id = Column(String(255))
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="transactions")


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    input_file_id = Column(String(255))
    output_file_id = Column(String(255))
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    user = relationship("User", back_populates="generations")
