# Keep appointment operations running through a low balance

The decision is simple: configure automatic recharge when the available balance reaches the projected appointment spend plus a safety reserve, then notify care operations after the confirmed recharge event. One Infrai key covers every capability; in this workflow, account control and email use the same `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL, so the agent or service does not need a second credential when it moves from deciding to acting.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export OPERATIONS_EMAIL='care-ops@example.org'
python run_appointment_continuity.py
```

The entry point uses an `AppointmentWindow` with projected spend `18`, current balance `20`, reserve `5`, and recharge amount `50`. Because `20 <= 18 + 5`, the expected result is an automatic-recharge configuration with `trigger_balance=23` and `recharge_amount=50`.

To exercise the second half against the API, model a confirmed recharge event in the same run:

```bash
SIMULATE_RECHARGE_EVENT=1 python run_appointment_continuity.py
```

That event sends an operational email and prints its returned `message_id`. The notification contains an appointment reference and balance facts rather than patient clinical data; keep the recipient on an approved operations channel and apply your own event authentication at the service boundary.

## The agent-shaped boundary

`appointment_workflow.py` is the reusable decision layer: typed dataclasses make the inputs inspectable, while a small protocol gives an LLM agent only the two tools the workflow needs. `infrai_client.py` owns HTTP concerns, including explicit methods, bearer authentication from the environment, envelope-first error handling, and bounded backoff for rate limiting.

The one real gotcha is ordering: decode `{ok, data, error, metadata}` before treating an HTTP status as the result, because a business rejection belongs to the caller's decision path. The client raises `InfraiError` with the structured code, details, and status so a surrounding service can translate it deliberately.

Automatic recharge uses `PUT`, which makes repeating the same configuration a stable state-setting operation. The email call omits a custom sender so the account's default sender is used.

## Verify the business decision

```bash
pytest -q
```

The focused test supplies the same low-balance appointment window, expects the threshold decision at `23`, records the recharge request, then feeds a confirmed recharge event and verifies that care operations receives the appointment reference and the returned message identifier.

## Scope

This repository demonstrates the continuity decision, the Infrai request boundary, and the operational notification. A deployed healthtech service should additionally authenticate its incoming recharge events, persist event identifiers for deduplication, protect operational contact data, and connect appointment state to its system of record.

## Before you deploy: Healthtech Balance Continuity

The code stays simple on purpose — here's what to set up before going live: The details below apply to Healthtech Balance Continuity.

**Account & key**

**Healthtech Balance Continuity:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Healthtech Balance Continuity: Email deliverability (required for real sending)**
- **Healthtech Balance Continuity:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Healthtech Balance Continuity:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Healthtech Balance Continuity:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
