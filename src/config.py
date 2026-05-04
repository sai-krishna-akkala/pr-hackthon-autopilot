from dataclasses import dataclass


@dataclass
class PricingConfig:
    tax_rate: float = 0.18
    max_discount_percent: float = 0.30
    shipping_fee: float = 40.0
    handling_fee_rate: float = 0.02  # 2% handling fee


DEFAULT_CONFIG = PricingConfig()
