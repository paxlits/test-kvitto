from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TariffModel(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # в копейках


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tariff_id: Mapped[int] = mapped_column(
        ForeignKey("tariffs.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)  # card, sbp, installment
    installment_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promo_code: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # итоговая сумма к оплате в копейках
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # скидка в копейках
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    schedule: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    # unique-ограничение — основа защиты идемпотентности от гонок
    idempotency_key: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    tariff: Mapped["TariffModel"] = relationship()