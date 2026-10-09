
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import PROMO_CODE, PROMO_DISCOUNT_PERCENT
from app.models import PaymentModel, TariffModel
from app.schemas import PaymentCreateSchema


def calculate_installment_schedule(amount: int, months: int) -> list[int]:
    """
    Расчет графика рассрочки.
    Сумма к оплате делится на срок в копейках.
    Сумма всех платежей графика ровно равна сумме к оплате;
    лишние копейки - в первые платежи.
    """
    if amount <= 0 or months <= 0:
        return []

    base = amount // months
    remainder = amount % months
    schedule = []
    for i in range(months):
        if i < remainder:
            schedule.append(base + 1)
        else:
            schedule.append(base)
    return schedule


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, payment_id: int) -> PaymentModel | None:
        return await self.db.get(PaymentModel, payment_id)

    async def find_by_idempotency_key(self, key: str) -> PaymentModel | None:
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def create(
        self, data: PaymentCreateSchema, idempotency_key: str | None
    ) -> tuple[PaymentModel, bool]:
        """
        Создать платёж.

        Возвращает (payment, created):
        - created=True  — платёж создан (ответ 201);
        - created=False — вернули существующий по Idempotency-Key (ответ 200).

        Защита от гонок: уникальный индекс на idempotency_key + обработка
        IntegrityError на уровне БД.
        """
        if idempotency_key:
            existing = await self.find_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing, False

        tariff = await self.db.get(TariffModel, data.tariff_id)
        if tariff is None:
            raise HTTPException(status_code=422, detail="Tariff not found")

        amount = tariff.price
        discount = 0
        if data.promo_code:
            if data.promo_code.upper() == PROMO_CODE:
                discount = amount * PROMO_DISCOUNT_PERCENT // 100
            else:
                raise HTTPException(status_code=422, detail="Invalid promo code")

        amount_final = amount - discount
        schedule = None
        if data.method == "installment" and data.installment_months:
            schedule = calculate_installment_schedule(
                amount_final, data.installment_months
            )

        payment = PaymentModel(
            tariff_id=data.tariff_id,
            email=str(data.email),
            method=data.method,
            installment_months=(
                data.installment_months if data.method == "installment" else None
            ),
            promo_code=data.promo_code.upper() if data.promo_code else None,
            amount=amount_final,
            discount=discount,
            status="pending",
            schedule=schedule,
            idempotency_key=idempotency_key,
        )
        self.db.add(payment)
        try:
            await self.db.commit()
        except IntegrityError:
            # Гонка: параллельный запрос уже создал платёж с этим ключом.
            await self.db.rollback()
            if idempotency_key:
                existing = await self.find_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return existing, False
            raise

        await self.db.refresh(payment)
        return payment, True