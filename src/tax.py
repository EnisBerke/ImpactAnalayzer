"""Tax calculation broken out for reuse by pricing and returns."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class TaxBreakdown:
    rate: float
    amount: float
    region: str
    category: str


class TaxService:
    REGIONAL_RATES: Dict[str, Dict[str, float]] = {
        "US": {"default": 0.07, "hardware": 0.08},
        "EU": {"default": 0.20},
        "UK": {"default": 0.17},
    }

    def calculate(self, taxable_amount: float, region: str, category: str = "default") -> TaxBreakdown:
        region_rates = self.REGIONAL_RATES.get(region, {"default": 0.0})
        rate = region_rates.get(category, region_rates.get("default", 0.0))
        amount = taxable_amount * rate
        return TaxBreakdown(rate=rate, amount=amount, region=region, category=category)
