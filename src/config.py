from dataclasses import dataclass


@dataclass
class PricingConfig:
    tax_rate: float = 0.18
    max_discount_percent: float = 0.30
    shipping_fee: float = 40.0


DEFAULT_CONFIG = PricingConfig()
