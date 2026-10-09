from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.constants import ALLOWED_INSTALLMENT_MONTHS, ALLOWED_METHODS


class TariffSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: int  # в копейках


class PaymentCreateSchema(BaseModel):
    # validate_default=True: без него Pydantic v2 не применяет field_validator
    # к значениям по умолчанию (например, installment_months=None)
    model_config = ConfigDict(from_attributes=True, validate_default=True)

    tariff_id: int
    email: EmailStr
    method: str
    installment_months: int | None = None
    promo_code: str | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in ALLOWED_METHODS:
            raise ValueError("Invalid method")
        return v

    @field_validator("installment_months")
    @classmethod
    def validate_installment_months(
        cls, v: int | None, info
    ) -> int | None:
        method = info.data.get("method")
        if method == "installment":
            if v not in ALLOWED_INSTALLMENT_MONTHS:
                raise ValueError("installment_months must be 3, 6, or 12")
        elif v is not None:
            raise ValueError(
                "installment_months should only be provided for installment"
            )
        return v


class PaymentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    tariff_id: int
    amount: int  # в копейках
    discount: int  # в копейках
    method: str
    installment_months: int | None = None
    schedule: list[int] | None = None  # список сумм в копейках
    email: str
    created_at: datetime


class WebhookSchema(BaseModel):
    payment_id: int
    status: str