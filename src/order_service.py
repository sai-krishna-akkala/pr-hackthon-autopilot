from src.config import DEFAULT_CONFIG
from src.pricing import calculate_discount, calculate_tax, calculate_handling_fee


def calculate_order_total(subtotal: float, loyalty_tier: str, include_shipping: bool = True) -> dict:
    if subtotal < 0:
        raise ValueError("subtotal cannot be negative")

    discount = calculate_discount(subtotal, loyalty_tier)
    amount_after_discount = round(subtotal - discount, 2)
    tax = calculate_tax(amount_after_discount)
    shipping_fee = DEFAULT_CONFIG.shipping_fee if include_shipping else 0.0
    handling_fee = calculate_handling_fee(subtotal)
    total = round(amount_after_discount + tax + shipping_fee + handling_fee, 2)

    return {
        "subtotal": subtotal,
        "discount": discount,
        "amount_after_discount": amount_after_discount,
        "tax": tax,
        "shipping_fee": shipping_fee2,
        "handling_fee": handling_fee2,
        "total": total,
    }
