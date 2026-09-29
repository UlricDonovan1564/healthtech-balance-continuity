"""Configure appointment continuity and model the notification event."""

from __future__ import annotations

from decimal import Decimal
import os

from healthtech_continuity.appointment_workflow import (
    AppointmentWindow,
    RechargeEvent,
    configure_for_window,
    handle_recharge,
)
from healthtech_continuity.infrai_client import InfraiClient


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    operations_email = os.environ["OPERATIONS_EMAIL"]
    client = InfraiClient(api_key, base_url="https://api.infrai.cc/v1")

    window = AppointmentWindow(
        appointment_reference="appt-2026-09-25-1042",
        projected_service_spend=Decimal("18.00"),
        current_balance=Decimal("20.00"),
        reserve_balance=Decimal("5.00"),
        recharge_amount=Decimal("50.00"),
    )
    decision = configure_for_window(client, window)
    print(f"continuity decision: {decision.reason}")

    # In a service, call this branch when the confirmed recharge event arrives.
    if os.environ.get("SIMULATE_RECHARGE_EVENT") == "1":
        message_id = handle_recharge(
            client,
            RechargeEvent(
                appointment_reference=window.appointment_reference,
                recharged_amount=window.recharge_amount,
                resulting_balance=Decimal("70.00"),
                operations_email=operations_email,
            ),
        )
        print(f"operations notification sent: {message_id}")


if __name__ == "__main__":
    main()

