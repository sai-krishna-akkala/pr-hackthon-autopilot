from src.config import DEFAULT_CONFIG


def calculate_discount(subtotal: float, loyalty_tier: str) -> float:
    tier_map = {
        "bronze": 0.03,
        "silver": 0.07,
        "gold": 0.15,#changed from 0.12 to 0.15
        "platinum": 0.30, #changed from 0.20 to 0.30
        "diamond": 0.25,
    }
    discount_percent = tier_map.get(loyalty_tier.lower(), 0.0)
   
    return round(subtotal * discount_percent, 2)


def calculate_tax(amount_after_discount: float) -> float:
    return round(amount_after_discount * DEFAULT_CONFIG.tax_rate, 2)


def calculate_handling_fee(subtotal: float) -> float:
    """New handling fee: 2% of subtotal, minimum $5."""
    fee = subtotal * DEFAULT_CONFIG.handling_fee_rate
    return round(max(fee, 5.0), 2)
