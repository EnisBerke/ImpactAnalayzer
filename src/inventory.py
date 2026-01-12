"""Inventory domain objects and storage access."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class InventoryItem:
    sku: str
    quantity: int


class InventoryRepository:
    """In-memory inventory store used by the order service demo."""

    def __init__(self) -> None:
        self._items: Dict[str, InventoryItem] = {}

    def add_item(self, sku: str, quantity: int) -> None:
        if sku in self._items:
            self._items[sku].quantity += quantity
        else:
            self._items[sku] = InventoryItem(sku=sku, quantity=quantity)

    def remove_item(self, sku: str, quantity: int) -> None:
        if not self.has_enough(sku, quantity):
            raise ValueError(f"Not enough stock for {sku}")
        self._items[sku].quantity -= quantity

    def reserve_with_buffer(self, sku: str, quantity: int, safety_buffer: int) -> bool:
        """Reserve inventory only if enough quantity remains after a safety buffer."""
        required = quantity + max(safety_buffer, 0)
        if not self.has_enough(sku, required):
            return False
        self._items[sku].quantity -= quantity
        return True

    def has_enough(self, sku: str, quantity: int) -> bool:
        item = self._items.get(sku)
        return bool(item and item.quantity >= quantity)

    def get_quantity(self, sku: str) -> int:
        item = self._items.get(sku)
        return item.quantity if item else 0
