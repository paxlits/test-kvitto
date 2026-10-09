# test-kvitto

API платежей на FastAPI согласно ТЗ.

## Стек

- FastAPI
- Python 3.11+
- Pydantic v2
- SQLite (aiosqlite) по умолчанию, PostgreSQL (asyncpg) — опционально
- SQLAlchemy 2.0 (async)
- Alembic
- pytest + httpx
- Docker

## Структура проекта

```
main.py                      # точка входа, инициализация БД и тарифов
app/
  config.py                  # настройки (DATABASE_URL, WEBHOOK_SECRET)
  constants.py               # тарифы, промокод, статусы
  database.py                # engine, session_factory, get_session
  dependencies.py            # SessionDep
  models.py                  # TariffModel, PaymentModel
  schemas.py                 # Pydantic-схемы
  routers/                   # tariffs, payments, webhooks
  services/payments.py       # бизнес-логика платежей, рассрочка
migrations/                  # Alembic (миграция 0001)
tests/                       # pytest
```

## Запуск

### Локально

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

По умолчанию БД — SQLite (файл `kvitto.db` в папке проекта), схема и тарифы создаются автоматически при старте. Ничего настраивать не нужно.

Для PostgreSQL: в `.env` поменяй `DATABASE_URL` на `postgresql+asyncpg://user:password@host:5432/dbname` и прогони миграции:

```bash
alembic upgrade head
uvicorn main:app --reload
```

Приложение будет доступно по адресу: http://localhost:8000
Документация: http://localhost:8000/docs

### Через Docker

```bash
docker compose up
```

Приложение поднимется на SQLite (`kvitto.db` создаётся в папке проекта на хосте).

## Тесты

```bash
pytest -v
```

## Примеры запросов

Все примеры ниже собраны в одном скрипте — `bash examples.sh` при запущенном `uvicorn` на `:8000`.

### Получить тарифы
```bash
curl http://localhost:8000/api/v1/tariffs
```

### Создать платеж картой
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "tariff_id": 2,
    "email": "test@example.com",
    "method": "card"
  }'
```

### Создать платеж в рассрочку
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "tariff_id": 2,
    "email": "test@example.com",
    "method": "installment",
    "installment_months": 3
  }'
```

### Создать платеж с промокодом
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "tariff_id": 2,
    "email": "test@example.com",
    "method": "card",
    "promo_code": "KVITTO10"
  }'
```

### Повтор запроса с Idempotency-Key (вернёт 200 с тем же платежом)
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-unique-key" \
  -d '{
    "tariff_id": 2,
    "email": "test@example.com",
    "method": "card"
  }'
```

### Получить платеж
```bash
curl http://localhost:8000/api/v1/payments/1
```

### Вебхук банка (подпись HMAC-SHA256)
```bash
SECRET="secret_key"
PAYLOAD='{"payment_id": 1, "status": "succeeded"}'
SIG=$(python3 -c "
import hmac, hashlib, sys
body=sys.argv[1].encode()
print(hmac.new(b'$SECRET', body, hashlib.sha256).hexdigest())
" "$PAYLOAD")
curl -X POST http://localhost:8000/api/v1/webhooks/bank \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$PAYLOAD"
```

## Деньги

Все суммы — целые числа в копейках (никаких float): тариф standard = 1 990 000 копеек, скидка KVITTO10 = 199 000, к оплате 1 791 000. График рассрочки делит сумму на равные платежи, остаток — в первые платежи, поэтому `sum(schedule) == amount` всегда.