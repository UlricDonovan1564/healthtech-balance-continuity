from decimal import Decimal

from healthtech_continuity.appointment_workflow import (
    AppointmentWindow,
    RechargeEvent,
    configure_for_window,
    handle_recharge,
)


class RecordingGateway:
    def __init__(self) -> None:
        self.recharge_request: dict[str, float] | None = None
        self.email_request: dict[str, str] | None = None

    def configure_autorecharge(
        self, *, trigger_balance: float, recharge_amount: float
    ) -> dict[str, str]:
        self.recharge_request = {
            "trigger_balance": trigger_balance,
            "recharge_amount": recharge_amount,
        }
        return {"status": "configured"}

    def send_email(self, *, to: str, subject: str, text: str) -> dict[str, str]:
        self.email_request = {"to": to, "subject": subject, "text": text}
        return {"message_id": "msg_appointment_ops_01"}


def test_low_balance_configures_recharge_and_event_notifies_operations() -> None:
    gateway = RecordingGateway()
    window = AppointmentWindow(
        appointment_reference="appt-1042",
        projected_service_spend=Decimal("18"),
        current_balance=Decimal("20"),
        reserve_balance=Decimal("5"),
        recharge_amount=Decimal("50"),
    )

    decision = configure_for_window(gateway, window)
    message_id = handle_recharge(
        gateway,
        RechargeEvent(
            appointment_reference="appt-1042",
            recharged_amount=Decimal("50"),
            resulting_balance=Decimal("70"),
            operations_email="care-ops@example.org",
        ),
    )

    assert decision.configure_recharge is True
    assert decision.trigger_balance == Decimal("23")
    assert gateway.recharge_request == {
        "trigger_balance": 23.0,
        "recharge_amount": 50.0,
    }
    assert gateway.email_request is not None
    assert gateway.email_request["to"] == "care-ops@example.org"
    assert "appt-1042" in gateway.email_request["text"]
    assert message_id == "msg_appointment_ops_01"

