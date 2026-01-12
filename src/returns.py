"""Return and refund processing flow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from audit import AuditLogger
from inventory import InventoryRepository
from loyalty import LoyaltyService
from pricing import PricingBreakdown, PricingService
from shipping import Address, ShippingService


class RefundGateway(Protocol):
    def refund(self, account_id: str, amount: float) -> None:
        ...


@dataclass
class ReturnRequest:
    account_id: str
    order_id: str
    sku: str
    quantity: int
    region: str
    reason: str
    shipping_address: Address


@dataclass
class ReturnResult:
    status: str
    refund: Optional[PricingBreakdown] = None
    reason: Optional[str] = None


class ReturnService:
    def __init__(
        self,
        inventory: InventoryRepository,
        refund_gateway: RefundGateway,
        pricing: PricingService,
        shipping: ShippingService,
        loyalty: LoyaltyService,
        audit: AuditLogger,
    ) -> None:
        self._inventory = inventory
        self._refund_gateway = refund_gateway
        self._pricing = pricing
        self._shipping = shipping
        self._loyalty = loyalty
        self._audit = audit

    def process(self, request: ReturnRequest) -> ReturnResult:
        if request.quantity <= 0:
            return ReturnResult(status="rejected", reason="invalid_quantity")

        try:
            refund_breakdown = self._pricing.calculate(
                sku=request.sku,
                quantity=request.quantity,
                region=request.region,
                coupon_code=None,
                shipping_method="standard",
                apply_loyalty=None,
            )
        except Exception as exc:
            return ReturnResult(status="rejected", reason=str(exc))

        try:
            self._refund_gateway.refund(request.account_id, refund_breakdown.total)
        except Exception as exc:  # pragma: no cover - demo stub
            return ReturnResult(status="payment_failed", refund=refund_breakdown, reason=str(exc))

        self._inventory.add_item(request.sku, request.quantity)
        self._loyalty.clawback(request.account_id, int(refund_breakdown.total))

        # Issue a return label for the customer to ship back the product.
        self._shipping.create_label(
            order_id=request.order_id,
            address=request.shipping_address,
            method="standard",
        )

        self._audit.log(
            event="return_processed",
            account_id=request.account_id,
            sku=request.sku,
            details=f"Return {request.order_id} for {request.quantity}x {request.sku} approved",
        )

        return ReturnResult(status="refunded", refund=refund_breakdown)
