"""Business decisions for funded appointment operations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class ContinuityGateway(Protocol):
    def configure_autorecharge(
        self, *, trigger_balance: float, recharge_amount: float
    ) -> object:
        pass

    def send_email(self, *, to: str, subject: str, text: str) -> object:
        pass


@dataclass(frozen=True)
class AppointmentWindow:
    appointment_reference: str
    projected_service_spend: Decimal
    current_balance: Decimal
    reserve_balance: Decimal
    recharge_amount: Decimal


@dataclass(frozen=True)
class ContinuityDecision:
    configure_recharge: bool
    trigger_balance: Decimal
    reason: str


@dataclass(frozen=True)
class RechargeEvent:
    appointment_reference: str
    recharged_amount: Decimal
    resulting_balance: Decimal
    operations_email: str


def plan_continuity(window: AppointmentWindow) -> ContinuityDecision:
    trigger = window.projected_service_spend + window.reserve_balance
    needs_configuration = window.current_balance <= trigger
    reason = (
        "balance is at or below appointment spend plus the safety reserve"
        if needs_configuration
        else "balance remains above appointment spend plus the safety reserve"
    )
    return ContinuityDecision(needs_configuration, trigger, reason)


def configure_for_window(
    gateway: ContinuityGateway, window: AppointmentWindow
) -> ContinuityDecision:
    decision = plan_continuity(window)
    if decision.configure_recharge:
        gateway.configure_autorecharge(
            trigger_balance=float(decision.trigger_balance),
            recharge_amount=float(window.recharge_amount),
        )
    return decision


def handle_recharge(gateway: ContinuityGateway, event: RechargeEvent) -> str:
    result = gateway.send_email(
        to=event.operations_email,
        subject=f"Balance restored for {event.appointment_reference}",
        text=(
            f"Automatic recharge completed for {event.appointment_reference}. "
            f"Amount: {event.recharged_amount}; resulting balance: "
            f"{event.resulting_balance}. Appointment operations can continue."
        ),
    )
    if not isinstance(result, dict) or not isinstance(result.get("message_id"), str):
        raise RuntimeError("email.send response did not include message_id")
    return result["message_id"]
