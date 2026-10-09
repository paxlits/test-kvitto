import os

# Безусловно переопределяем на SQLite in-memory,
# чтобы тесты не зависели от окружения (локально или в CI).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["WEBHOOK_SECRET"] = "secret_key"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.constants import TARIFFS_INIT
from app.database import get_session
from app.models import Base, TariffModel
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    yield factory

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    # Инициализация тарифов
    async with session_factory() as session:
        session.add_all([TariffModel(**data) for data in TARIFFS_INIT])
        await session.commit()

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()