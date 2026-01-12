"""Utility helpers for sending demo email notifications."""
from __future__ import annotations


DEFAULT_SENDER = "noreply@example.com"


def send_welcome_email(address: str, sender: str = DEFAULT_SENDER) -> None:
    print(f"[{sender}] Sending welcome email to {address}")


def send_order_receipt(address: str, order_id: str, sender: str = DEFAULT_SENDER) -> None:
    print(f"[{sender}] Sending order receipt for {order_id} to {address}")
