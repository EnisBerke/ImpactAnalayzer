"""Simple fraud scoring for orders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskAssessment:
    score: float
    reason: Optional[str] = None

    @property
    def is_blocked(self) -> bool:
        return self.score >= 0.8

    @property
    def needs_review(self) -> bool:
        return 0.5 <= self.score < 0.8


class FraudService:
    """Toy fraud model based on region and order amount."""

    def score(self, order_total: float, region: str) -> RiskAssessment:
        score = 0.1
        reason = None

        if order_total > 500:
            score += 0.4
            reason = "high_amount"

        if region not in {"US", "EU", "UK"}:
            score += 0.3
            reason = "unsupported_region" if not reason else f"{reason}+unsupported_region"

        if order_total <= 0:
            score += 0.2
            reason = "invalid_amount"

        return RiskAssessment(score=score, reason=reason)
