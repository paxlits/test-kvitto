from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.config import settings
from app.constants import TARIFFS_INIT
from app.database import engine, session_factory
from app.models import Base, TariffModel
from app.routers.payments import router as payments_router
from app.routers.tariffs import router as tariffs_router
from app.routers.webhooks import router as webhooks_router


async def _init_db() -> None:
    # Схему в Postgres накатывает Alembic (`alembic upgrade head`).
    # create_all оставляем только для SQLite — удобный локальный/дев-режим.
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Засев тарифов идемпотентен — добавляем только отсутствующие.
    async with session_factory() as session:
        result = await session.execute(select(TariffModel.id))
        existing_ids = set(result.scalars().all())
        for tariff_data in TARIFFS_INIT:
            if tariff_data["id"] not in existing_ids:
                session.add(TariffModel(**tariff_data))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _init_db()
    yield
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.include_router(tariffs_router, prefix=settings.API_V1_STR)
app.include_router(payments_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)