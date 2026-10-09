import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.constants import ALLOWED_STATUS_TRANSITIONS
from app.dependencies import SessionDep
from app.models import PaymentModel
from app.schemas import WebhookSchema

router = APIRouter(prefix="/webhooks", tags=["Вебхуки"])


@router.post("/bank")
async def webhook_bank(
    request: Request,
    webhook_data: WebhookSchema,
    db: SessionDep,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
):
    # Проверка подписи вебхука: HMAC-SHA256 от тела запроса.
    # Отсутствующий заголовок = подписи нет = считаем неверной подписью (401).
    body = await request.body()
    expected_signature = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if x_signature is None or not hmac.compare_digest(
        expected_signature, x_signature
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Блокируем строку платежа, чтобы избежать гонок при смене статуса
    result = await db.execute(
        select(PaymentModel)
        .where(PaymentModel.id == webhook_data.payment_id)
        .with_for_update()
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    allowed_transitions = ALLOWED_STATUS_TRANSITIONS.get(payment.status, [])
    if webhook_data.status not in allowed_transitions:
        return JSONResponse(
            status_code=409, content={"error": "invalid_transition"}
        )

    payment.status = webhook_data.status
    await db.commit()
    return {"result": "ok"}