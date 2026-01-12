"""Order processing logic for the workflow demo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from audit import AuditLogger
from fraud import FraudService
from inventory import InventoryRepository
from loyalty import LoyaltyService
from pricing import PricingBreakdown, PricingService
from shipping import Address, ShippingLabel, ShippingService


class PaymentGateway(Protocol):
    def charge(self, account_id: str, amount: float) -> None:  # pragma: no cover - demo stub
        ...


@dataclass
class Order:
    sku: str
    quantity: int
    account_id: str
    region: str
    coupon_code: str | None = None
    shipping_method: str = "standard"
    shipping_address: Address | None = None
    loyalty_points_to_apply: int | None = None


@dataclass
class OrderResult:
    status: str
    pricing: PricingBreakdown | None = None
    shipping_label: ShippingLabel | None = None
    reason: str | None = None
    loyalty_points_awarded: int = 0


class OrderService:
    """Coordinates inventory, pricing, fraud review, payment capture, and shipping."""

    def __init__(
        self,
        inventory: InventoryRepository,
        payment_gateway: PaymentGateway,
        pricing: PricingService,
        shipping: ShippingService,
        fraud: FraudService,
        loyalty: LoyaltyService,
        audit: AuditLogger,
        safety_stock: int = 0,
    ) -> None:
        self._inventory = inventory
        self._payment_gateway = payment_gateway
        self._pricing = pricing
        self._shipping = shipping
        self._fraud = fraud
        self._loyalty = loyalty
        self._audit = audit
        self._safety_stock = safety_stock

    def place_order(self, order: Order) -> OrderResult:
        """Return fulfillment state after attempting to reserve stock."""
        required = order.quantity + max(self._safety_stock, 0)
        if not self._inventory.has_enough(order.sku, required):
            return OrderResult(status="insufficient_stock", reason="not_enough_inventory")

        loyalty_credit = None
        if order.loyalty_points_to_apply:
            try:
                loyalty_credit = self._loyalty.redeem(order.account_id, order.loyalty_points_to_apply)
            except Exception as exc:
                return OrderResult(status="loyalty_failed", reason=str(exc))

        pricing = self._pricing.calculate(
            sku=order.sku,
            quantity=order.quantity,
            region=order.region,
            coupon_code=order.coupon_code,
            shipping_method=order.shipping_method,
            apply_loyalty=loyalty_credit,
        )

        risk = self._fraud.score(order_total=pricing.total, region=order.region)
        if risk.is_blocked:
            self._audit.log("order_blocked", order.account_id, order.sku, risk.reason or "blocked")
            return OrderResult(status="blocked", pricing=pricing, reason=risk.reason)
        if risk.needs_review:
            self._audit.log("order_review", order.account_id, order.sku, risk.reason or "review")
            return OrderResult(status="manual_review", pricing=pricing, reason=risk.reason)

        try:
            self._payment_gateway.charge(order.account_id, pricing.total)
        except Exception as exc:
            self._audit.log("payment_failed", order.account_id, order.sku, str(exc))
            return OrderResult(status="payment_failed", pricing=pricing, reason=str(exc))

        self._inventory.remove_item(order.sku, order.quantity)

        label = None
        if order.shipping_address:
            label = self._shipping.create_label(
                order_id=order.account_id,
                address=order.shipping_address,
                method=order.shipping_method,
            )

        awarded_points = self._loyalty.accrue_points(order.account_id, pricing.total)
        self._audit.log(
            "order_fulfilled",
            order.account_id,
            order.sku,
            f"charged={pricing.total}, points_awarded={awarded_points}",
        )

        return OrderResult(
            status="fulfilled",
            pricing=pricing,
            shipping_label=label,
            loyalty_points_awarded=awarded_points,
        )
