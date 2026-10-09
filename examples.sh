#!/usr/bin/env bash
# Примеры запросов к API (запускать при поднятом uvicorn на :8000)
set -e

BASE="http://localhost:8000"
JSON="Content-Type: application/json"

echo "== 1. Список тарифов =="
curl -s $BASE/api/v1/tariffs

echo -e "\n\n== 2. Платёж картой (standard, без промокода) -> 201 =="
curl -s -X POST $BASE/api/v1/payments -H "$JSON" \
  -d '{"tariff_id": 2, "email": "test@example.com", "method": "card"}'

echo -e "\n\n== 3. Платёж с промокодом KVITTO10 -> discount 199000, amount 1791000 =="
curl -s -X POST $BASE/api/v1/payments -H "$JSON" \
  -d '{"tariff_id": 2, "email": "test@example.com", "method": "card", "promo_code": "kvitto10"}'

echo -e "\n\n== 4. Рассрочка на 3 месяца -> schedule [663334, 663333, 663333] =="
curl -s -X POST $BASE/api/v1/payments -H "$JSON" \
  -d '{"tariff_id": 2, "email": "test@example.com", "method": "installment", "installment_months": 3}'

echo -e "\n\n== 5. Повтор с тем же Idempotency-Key -> 200 и тот же платёж =="
curl -s -X POST $BASE/api/v1/payments -H "$JSON" -H "Idempotency-Key: my-key" \
  -d '{"tariff_id": 1, "email": "test@example.com", "method": "card"}'
echo " <- первый (201)"
curl -s -o /dev/null -w "повтор: HTTP %{http_code}\n" \
  -X POST $BASE/api/v1/payments -H "$JSON" -H "Idempotency-Key: my-key" \
  -d '{"tariff_id": 1, "email": "test@example.com", "method": "card"}'

echo -e "\n== 6. Рассрочка без installment_months -> 422 =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST $BASE/api/v1/payments -H "$JSON" \
  -d '{"tariff_id": 2, "email": "test@example.com", "method": "installment"}'

echo -e "\n== 7. Несуществующий промокод -> 422 =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST $BASE/api/v1/payments -H "$JSON" \
  -d '{"tariff_id": 2, "email": "test@example.com", "method": "card", "promo_code": "UNKNOWN"}'

echo -e "\n== 8. GET платежа по id -> 200 / несуществующий -> 404 =="
curl -s $BASE/api/v1/payments/1
curl -s -o /dev/null -w "\nплатёж 999: HTTP %{http_code}\n" $BASE/api/v1/payments/999

echo -e "\n== 9. GET /payments с фильтрами (email и status) =="
curl -s "$BASE/api/v1/payments?email=test@example.com&status=pending"

echo -e "\n== 10. Вебхук банка: успешный переход pending -> succeeded =="
SECRET="secret_key"
PAYLOAD='{"payment_id": 1, "status": "succeeded"}'
SIG=$(python3 -c "
import hmac, hashlib, sys
body = sys.argv[1].encode()
print(hmac.new(b'$SECRET', body, hashlib.sha256).hexdigest())
" "$PAYLOAD")
curl -s -X POST $BASE/api/v1/webhooks/bank -H "$JSON" \
  -H "X-Signature: $SIG" -d "$PAYLOAD"

echo -e "\n\n== 11. Вебхук: неверная подпись -> 401 =="
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST $BASE/api/v1/webhooks/bank -H "$JSON" \
  -H "X-Signature: deadbeef" -d '{"payment_id": 1, "status": "succeeded"}'

echo -e "\n== 12. Вебхук: запрещённый переход succeeded -> refunded при статусе pending -> 409 =="
curl -s -o /dev/null -w "HTTP %{http_code} (ждём 409, статус успел смениться на succeeded)\n" \
  -X POST $BASE/api/v1/webhooks/bank -H "$JSON" \
  -H "X-Signature: $SIG" -d '{"payment_id": 1, "status": "refunded"}'

echo
echo "Готово."