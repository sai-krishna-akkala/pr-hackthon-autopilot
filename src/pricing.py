from src.config import DEFAULT_CONFIG


def calculate_discount(subtotal: float, loyalty_tier: str) -> float:
    tier_map = {
        "bronze": 0.02,
        "silver": 0.05,
        "gold": 0.10,
        "platinum": 0.15,
    }
    discount_percent = tier_map.get(loyalty_tier.lower(), 0.0)
    # BUG: Removed the max_discount_percent cap - discount could exceed 30%
    return round(subtotal * discount_percent, 2)


def calculate_tax(amount_after_discount: float) -> float:
    # BUG: No validation for negative amounts, will calculate negative tax
    return round(amount_after_discount * DEFAULT_CONFIG.tax_rate, 2)


def calculate_handling_fee(subtotal: float) -> float:
    """Calculate handling fee: 2% of subtotal, minimum $5."""
    fee = subtotal * 0.05  # BUG: Hardcoded 5% instead of using config's 2%
    return round(max(fee, 5.0), 2)
