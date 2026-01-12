"""Promotion rules for discounts and free shipping codes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from catalog import Product


@dataclass
class PromotionResult:
    discount: float = 0.0
    free_shipping: bool = False
    applied_code: Optional[str] = None
    reason: Optional[str] = None


class PromotionService:
    """Evaluates coupons and simple product/category promotions."""

    def apply_coupon(self, product: Product, quantity: int, coupon_code: Optional[str]) -> PromotionResult:
        if not coupon_code:
            return PromotionResult()

        code = coupon_code.lower()
        if code == "save10":
            discount = min(product.price * quantity * 0.10, 25.0)
            return PromotionResult(discount=round(discount, 2), applied_code=coupon_code)
        if code == "freeship":
            return PromotionResult(free_shipping=True, applied_code=coupon_code)
        if code == "bogo" and quantity >= 2:
            # Buy one get one free on the same SKU.
            return PromotionResult(discount=product.price, applied_code=coupon_code)

        return PromotionResult(discount=0.0, applied_code=None, reason="coupon_not_applied")

    def category_discount(self, product: Product) -> float:
        # Example: 5% off hardware items.
        if product.category == "hardware":
            return round(product.price * 0.05, 2)
        return 0.0
