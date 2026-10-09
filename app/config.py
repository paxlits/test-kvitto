from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "test-kvitto"
    API_V1_STR: str = "/api/v1"

    # Асинхронный URL для приложения.
    # По умолчанию SQLite — работает без внешней БД (если в .env не задано иное).
    # Для PostgreSQL: postgresql+asyncpg://user:password@host:5432/dbname
    DATABASE_URL: str = "sqlite+aiosqlite:///./kvitto.db"

    # Секрет для проверки подписи вебхука (HMAC-SHA256).
    # Без дефолта: приложение не стартует, если секрет не задан
    # (см. .env / .env.example).
    WEBHOOK_SECRET: str


settings = Settings()