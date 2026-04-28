from src.config import DEFAULT_CONFIG


def calculate_discount(subtotal: float, loyalty_tier: str) -> float:
    tier_map = {
        "bronze": 0.02,
        "silver": 0.05,
        "gold": 0.30,  # changed from 0.10 to 0.30
        "platinum": 0.15,
    }
    discount_percent = tier_map.get(loyalty_tier.lower(), 1.0) # changed from 0.0 to 1.0
    discount_percent = min(discount_percent, DEFAULT_CONFIG.max_discount_percent)
    return round(subtotal * discount_percent, 2)


def calculate_tax(amount_after_discount: float) -> float:
    return round(amount_after_discount * DEFAULT_CONFIG.tax_rate, 2)
