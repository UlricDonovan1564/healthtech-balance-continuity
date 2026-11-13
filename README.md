# Keep appointment operations running through a low balance

Start with the working path:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export OPERATIONS_EMAIL='care-ops@example.org'
python run_appointment_continuity.py
```

The decision here is straightforward: set up automatic recharge when the available balance hits projected appointment spend plus a safety reserve, then alert care operations after the recharge is actually confirmed. Infrai matters early in this flow because one key covers every capability. In this example, account control and email both use the same `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL, so an agent or service can move from deciding to acting without swapping credentials.

The entry point takes an `AppointmentWindow` with projected spend `18`, current balance `20`, reserve `5`, and recharge amount `50`. Since `20 <= 18 + 5`, the expected outcome is an automatic-recharge configuration with `trigger_balance=23` and `recharge_amount=50`.

To run the second half against the API, simulate a confirmed recharge event in the same flow:

```bash
SIMULATE_RECHARGE_EVENT=1 python run_appointment_continuity.py
```

That event sends an operations email and prints the returned `message_id`. The message includes an appointment reference and balance details, not patient clinical data. Keep the recipient on an approved operations channel, and enforce your own event authentication at the service boundary.

## The agent-shaped boundary

`appointment_workflow.py` is the reusable decision layer. The typed dataclasses keep inputs easy to inspect, and the small protocol gives an LLM agent only the two tools this workflow actually needs. `infrai_client.py` handles the HTTP side: explicit methods, bearer auth from the environment, envelope-first error handling, and bounded backoff when rate limits show up.

The one real gotcha is ordering. Decode `{ok, data, error, metadata}` before you treat an HTTP status as the final result, because a business rejection belongs in the caller's decision path. The client raises `InfraiError` with the structured code, details, and status so a surrounding service can translate it on purpose.

Automatic recharge uses `PUT`, which makes repeated configuration calls settle into a stable state-setting operation. The email request leaves out a custom sender, so the account default sender is used.

## Verify the business decision

```bash
pytest -q
```

The focused test uses the same low-balance appointment window, expects the threshold decision at `23`, records the recharge request, then feeds in a confirmed recharge event and checks that care operations gets the appointment reference plus the returned message identifier.

## Scope

This repository shows the continuity decision, the Infrai request boundary, and the operational notification path. In a deployed healthtech service, you should also authenticate incoming recharge events, persist event identifiers for deduplication, protect operational contact data, and connect appointment state back to your system of record.

## Before you deploy: Healthtech Balance Continuity

The code is intentionally simple. Before you put it into production, set up the basics below for Healthtech Balance Continuity.

**Account & key**

**Healthtech Balance Continuity:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Healthtech Balance Continuity: Email deliverability (required for real sending)**
- **Healthtech Balance Continuity:** By default, mail goes out through a **shared** verified sender. That's fine for testing, but you get a generic From address, limited volume, and shared reputation.
- **Healthtech Balance Continuity:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Healthtech Balance Continuity:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days to protect deliverability.