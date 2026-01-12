"""Simple in-memory audit log for order events."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class AuditEntry:
    event: str
    account_id: str
    sku: Optional[str]
    details: str
    at: datetime


class AuditLogger:
    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    def log(self, event: str, account_id: str, sku: Optional[str], details: str) -> None:
        self._entries.append(
            AuditEntry(
                event=event,
                account_id=account_id,
                sku=sku,
                details=details,
                at=datetime.utcnow(),
            )
        )

    def entries(self) -> List[AuditEntry]:
        return list(self._entries)
