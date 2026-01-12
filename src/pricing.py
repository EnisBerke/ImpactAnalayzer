"""Pricing helpers for orders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from catalog import CatalogService
from promotions import PromotionService
from tax import TaxService


@dataclass
class PricingBreakdown:
    subtotal: float
    discount: float
    tax: float
    shipping: float
    total: float
    coupon_applied: Optional[str] = None
    reason: Optional[str] = None

    @property
    def effective_subtotal(self) -> float:
        return max(0.0, self.subtotal - self.discount)


class PricingService:
    """Calculates order totals using catalog, promotions, tax, and shipping rules."""

    SHIPPING_BY_METHOD = {
        "standard": 5.00,
        "express": 12.00,
    }

    def __init__(
        self,
        catalog: CatalogService,
        promotions: PromotionService,
        tax: TaxService,
    ) -> None:
        self._catalog = catalog
        self._promotions = promotions
        self._tax = tax

    def _bulk_discount(self, product, quantity: int) -> float:
        if quantity >= 20:
            return round(product.price * quantity * 0.15, 2)
        if quantity >= 10:
            return round(product.price * quantity * 0.12, 2)
        if quantity >= 5:
            return round(product.price * quantity * 0.07, 2)
        return 0.0

    def calculate(
        self,
        sku: str,
        quantity: int,
        region: str = "US",
        coupon_code: Optional[str] = None,
        shipping_method: str = "standard",
        apply_loyalty: Optional[float] = None,
    ) -> PricingBreakdown:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        product = self._catalog.get(sku)
        subtotal = product.price * quantity

        promo = self._promotions.apply_coupon(product, quantity, coupon_code)
        category_discount = self._promotions.category_discount(product)
        bulk_discount = self._bulk_discount(product, quantity)
        discount = promo.discount + (category_discount * quantity) + bulk_discount

        base_shipping = self.SHIPPING_BY_METHOD.get(shipping_method, 0.0)
        bulk_shipping = 0.0
        if quantity >= 20:
            bulk_shipping = 6.0
        elif quantity >= 10:
            bulk_shipping = 3.0
        shipping = 0.0 if promo.free_shipping else base_shipping + bulk_shipping
        taxable_amount = max(0.0, subtotal - discount) + shipping
        tax_breakdown = self._tax.calculate(taxable_amount, region, category=product.category)

        total = taxable_amount + tax_breakdown.amount
        if apply_loyalty:
            total = max(0.0, total - apply_loyalty)

        return PricingBreakdown(
            subtotal=subtotal,
            discount=round(discount, 2),
            tax=round(tax_breakdown.amount, 2),
            shipping=shipping,
            total=round(total, 2),
            coupon_applied=promo.applied_code,
            reason=promo.reason,
        )
