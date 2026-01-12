"""Product catalog with pricing metadata used by pricing and shipping."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Product:
    sku: str
    name: str
    price: float
    weight_kg: float
    category: str
    is_fragile: bool = False


class CatalogService:
    def __init__(self, products: Optional[Dict[str, Product]] = None) -> None:
        self._products: Dict[str, Product] = products or {
            "widget-basic": Product(
                sku="widget-basic",
                name="Basic Widget",
                price=25.0,
                weight_kg=0.4,
                category="widgets",
            ),
            "widget-pro": Product(
                sku="widget-pro",
                name="Pro Widget",
                price=60.0,
                weight_kg=0.8,
                category="widgets",
                is_fragile=True,
            ),
            "bolt-pack": Product(
                sku="bolt-pack",
                name="Bolt Pack (100x)",
                price=15.0,
                weight_kg=0.3,
                category="hardware",
            ),
        }

    def get(self, sku: str) -> Product:
        if sku not in self._products:
            raise KeyError(f"Unknown product: {sku}")
        return self._products[sku]
