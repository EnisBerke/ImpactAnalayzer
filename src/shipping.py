"""Shipping workflow for order fulfillment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Address:
    name: str
    line1: str
    city: str
    region: str
    postal_code: str
    country: str


@dataclass
class ShippingLabel:
    order_id: str
    carrier: str
    method: str
    tracking_number: str
    address: Address
    cost: float


class ShippingService:
    """Fake shipping service that issues labels and handles method validation."""

    def __init__(self) -> None:
        self._issued: dict[str, ShippingLabel] = {}

    def create_label(
        self,
        order_id: str,
        address: Address,
        method: str = "standard",
        carrier: str = "DHL",
    ) -> ShippingLabel:
        if not self._is_supported(method):
            raise ValueError(f"Unsupported shipping method: {method}")

        tracking = f"{carrier}-{order_id}-TRACK"
        cost = 5.0 if method == "standard" else 12.0
        label = ShippingLabel(
            order_id=order_id,
            carrier=carrier,
            method=method,
            tracking_number=tracking,
            address=address,
            cost=cost,
        )
        self._issued[order_id] = label
        return label

    def _is_supported(self, method: str) -> bool:
        return method in {"standard", "express"}

    def get_label(self, order_id: str) -> Optional[ShippingLabel]:
        return self._issued.get(order_id)
