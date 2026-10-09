# CLAUDE.md

## Правила для ассистента

### Код
- Соблюдать стиль кода согласно ruff
- Все суммы в копейках - целые числа (int), никаких float
- Использовать Pydantic v2
- Следовать принципам REST API

### Стек
- FastAPI, Python 3.11+, SQLAlchemy 2.0, PostgreSQL, Alembic, pytest, httpx

### Бизнес-логика
- Тарифы создаются при старте: basic(990000), standard(1990000), premium(2990000)
- Промокод KVITTO10 - 10% скидки, регистронезависимый
- method: card/sbp/installment
- installment_months: 3,6,12 (только для installment)
- График рассрочки: сумма всех платежей = amount_final; остаток - в первые платежи
- Статусы: pending → succeeded/failed, succeeded → refunded
- Идемпотентность по Idempotency-Key (возврат 200 при повторе)

### Тестирование
- Запуск тестов: pytest -v
- Использовать SQLite in-memory для тестов
- Покрыть все критичные кейсы из ТЗ

### Docker
- Запуск: docker compose up
- PostgreSQL + приложение
