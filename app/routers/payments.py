from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from sqlalchemy import select

from app.dependencies import SessionDep
from app.models import PaymentModel
from app.schemas import PaymentCreateSchema, PaymentSchema
from app.services.payments import PaymentService

router = APIRouter(prefix="/payments", tags=["Платежи"])


@router.post(
    "", response_model=PaymentSchema, status_code=status.HTTP_201_CREATED
)
async def create_payment(
    payload: PaymentCreateSchema,
    db: SessionDep,
    response: Response,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
) -> PaymentModel:
    payment, created = await PaymentService(db).create(payload, idempotency_key)
    if not created:
        # Повтор с тем же Idempotency-Key: отдаём уже созданный платёж с 200
        response.status_code = status.HTTP_200_OK
    return payment


@router.get("", response_model=list[PaymentSchema])
async def get_payments(
    db: SessionDep,
    email: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[PaymentModel]:
    query = select(PaymentModel)
    if email:
        query = query.where(PaymentModel.email == email)
    if status_filter:
        query = query.where(PaymentModel.status == status_filter)
    result = await db.execute(query.order_by(PaymentModel.id))
    return list(result.scalars().all())


@router.get("/{payment_id}", response_model=PaymentSchema)
async def get_payment(payment_id: int, db: SessionDep) -> PaymentModel:
    payment = await PaymentService(db).get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment