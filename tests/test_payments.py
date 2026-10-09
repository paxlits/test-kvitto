import hashlib
import hmac
import json

SECRET = "secret_key"


def _sign(payload: dict) -> tuple[bytes, str]:
    """Подпись вебхука считается от тела запроса (компактный JSON)."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


async def test_tariffs_list(client):
    response = await client.get("/api/v1/tariffs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "basic"
    assert data[0]["price"] == 990000


async def test_amount_with_and_without_promo(client):
    # без промокода
    response = await client.post(
        "/api/v1/payments",
        json={"tariff_id": 2, "email": "test@example.com", "method": "card"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 1990000
    assert data["discount"] == 0

    # с промокодом KVITTO10 (10%)
    response = await client.post(
        "/api/v1/payments",
        json={
            "tariff_id": 2,
            "email": "test2@example.com",
            "method": "card",
            "promo_code": "KVITTO10",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 1791000
    assert data["discount"] == 199000

    # промокод в нижнем регистре
    response = await client.post(
        "/api/v1/payments",
        json={
            "tariff_id": 2,
            "email": "test3@example.com",
            "method": "card",
            "promo_code": "kvitto10",
        },
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 1791000

    # неизвестный промокод
    response = await client.post(
        "/api/v1/payments",
        json={
            "tariff_id": 2,
            "email": "test4@example.com",
            "method": "card",
            "promo_code": "UNKNOWN",
        },
    )
    assert response.status_code == 422


async def test_installment_schedule_sum(client):
    cases = [(2, 3, 1990000), (1, 6, 990000), (3, 12, 2990000)]
    for tariff_id, months, amount in cases:
        response = await client.post(
            "/api/v1/payments",
            json={
                "tariff_id": tariff_id,
                "email": "test@example.com",
                "method": "installment",
                "installment_months": months,
            },
        )
        assert response.status_code == 201
        schedule = response.json()["schedule"]
        assert schedule is not None
        assert len(schedule) == months
        assert sum(schedule) == amount


async def test_installment_requires_months(client):
    response = await client.post(
        "/api/v1/payments",
        json={
            "tariff_id": 2,
            "email": "test@example.com",
            "method": "installment",
        },
    )
    assert response.status_code == 422


async def test_idempotency_key(client):
    payload = {
        "tariff_id": 1,
        "email": "test@example.com",
        "method": "card",
    }
    headers = {"Idempotency-Key": "test-key-123"}

    first = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert first.status_code == 201
    first_data = first.json()

    second = await client.post("/api/v1/payments", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["id"] == first_data["id"]

    # Убеждаемся, что создан ровно один платёж
    listing = await client.get(
        "/api/v1/payments", params={"email": "test@example.com"}
    )
    assert len(listing.json()) == 1


async def test_invalid_status_transition_returns_409(client):
    response = await client.post(
        "/api/v1/payments",
        json={"tariff_id": 1, "email": "test@example.com", "method": "card"},
    )
    assert response.status_code == 201
    payment_id = response.json()["id"]
    payment_status = response.json()["status"]

    payload = {"payment_id": payment_id, "status": "refunded"}
    body, signature = _sign(payload)

    response = await client.post(
        "/api/v1/webhooks/bank",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 409
    assert response.json() == {"error": "invalid_transition"}

    # Статус не изменился
    check = await client.get(f"/api/v1/payments/{payment_id}")
    assert check.json()["status"] == payment_status


async def test_webhook_invalid_signature_returns_401(client):
    response = await client.post(
        "/api/v1/payments",
        json={"tariff_id": 1, "email": "test@example.com", "method": "card"},
    )
    payment_id = response.json()["id"]

    payload = {"payment_id": payment_id, "status": "succeeded"}
    response = await client.post(
        "/api/v1/webhooks/bank",
        json=payload,
        headers={"X-Signature": "deadbeef"},
    )
    assert response.status_code == 401


async def test_valid_status_transition(client):
    response = await client.post(
        "/api/v1/payments",
        json={"tariff_id": 1, "email": "test@example.com", "method": "card"},
    )
    payment_id = response.json()["id"]

    payload = {"payment_id": payment_id, "status": "succeeded"}
    body, signature = _sign(payload)
    resp = await client.post(
        "/api/v1/webhooks/bank",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"result": "ok"}

    check = await client.get(f"/api/v1/payments/{payment_id}")
    assert check.json()["status"] == "succeeded"


async def test_payment_not_found_returns_404(client):
    response = await client.get("/api/v1/payments/999")
    assert response.status_code == 404


async def test_webhook_payment_not_found_returns_404(client):
    payload = {"payment_id": 999, "status": "succeeded"}
    body, signature = _sign(payload)
    resp = await client.post(
        "/api/v1/webhooks/bank",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 404


async def test_payment_response_has_only_tz_fields(client):
    """Ответ платежа содержит ровно поля из ТЗ, ничего лишнего
    (promo_code / idempotency_key / служебные поля наружу не уходят)."""
    response = await client.post(
        "/api/v1/payments",
        json={"tariff_id": 2, "email": "test@example.com", "method": "card"},
    )
    assert response.status_code == 201
    data = response.json()
    expected = {
        "id",
        "status",
        "tariff_id",
        "amount",
        "discount",
        "method",
        "installment_months",
        "schedule",
        "email",
        "created_at",
    }
    assert set(data.keys()) == expected
