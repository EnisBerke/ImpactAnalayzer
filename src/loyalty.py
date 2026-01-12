"""Loyalty program tracking simple point accrual and redemption."""
from __future__ import annotations

from typing import Dict


class LoyaltyService:
    def __init__(self) -> None:
        self._balances: Dict[str, int] = {}

    def accrue_points(self, account_id: str, order_total: float) -> int:
        points = int(order_total)
        self._balances[account_id] = self._balances.get(account_id, 0) + points
        return points

    def get_balance(self, account_id: str) -> int:
        return self._balances.get(account_id, 0)

    def redeem(self, account_id: str, points: int) -> float:
        available = self.get_balance(account_id)
        if points > available:
            raise ValueError("Not enough points to redeem")
        self._balances[account_id] = available - points
        # Convert points to a fixed monetary value.
        return round(points * 0.01, 2)

    def restore(self, account_id: str, points: int) -> None:
        if points <= 0:
            return
        self._balances[account_id] = self._balances.get(account_id, 0) + points

    def clawback(self, account_id: str, points: int) -> None:
        # Remove points when an order is refunded or fails after accrual.
        if points <= 0:
            return
        current = self._balances.get(account_id, 0)
        self._balances[account_id] = max(0, current - points)
