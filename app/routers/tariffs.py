
from fastapi import APIRouter
from sqlalchemy import select

from app.dependencies import SessionDep
from app.models import TariffModel
from app.schemas import TariffSchema

router = APIRouter(prefix="/tariffs", tags=["Тарифы"])


@router.get("", response_model=list[TariffSchema])
async def get_tariffs(db: SessionDep) -> list[TariffModel]:
    result = await db.execute(select(TariffModel).order_by(TariffModel.id))
    return list(result.scalars().all())