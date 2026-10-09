TARIFFS_INIT = [
    {"id": 1, "title": "basic", "price": 990000},  # 9 900 ₽ в копейках
    {"id": 2, "title": "standard", "price": 1990000},  # 19 900 ₽ в копейках
    {"id": 3, "title": "premium", "price": 2990000},  # 29 900 ₽ в копейках
]

PROMO_CODE = "KVITTO10"
PROMO_DISCOUNT_PERCENT = 10

ALLOWED_METHODS = ["card", "sbp", "installment"]
ALLOWED_INSTALLMENT_MONTHS = [3, 6, 12]

ALLOWED_STATUS_TRANSITIONS = {
    "pending": ["succeeded", "failed"],
    "succeeded": ["refunded"],
    "failed": [],
    "refunded": [],
}