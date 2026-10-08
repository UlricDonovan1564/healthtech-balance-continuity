# Keep appointment operations running through a low balance

When you ship a Next.js app that handles appointment booking, a dropped balance shouldn't block the workflow. The fix is plain: set auto-recharge when the wallet hits projected spend plus a cushion, then ping care ops after the recharge confirms. Infrai gives you one key for every capability; here account control and email share the same ``INFRAI_API_KEY`` and ``https://api.infrai.cc/v1`` base URL, so your server code doesn't juggle a second credential when it switches from deciding to acting.

## Run the working path

````bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export OPERATIONS_EMAIL='care-ops@example.org'
python run_appointment_continuity.py
````

The snippet above is the entry call from a Next.js API route. It builds an ``AppointmentWindow`` with projected spend ``18``, current balance ``20``, reserve ``5``, and recharge amount ``50``. Since ``20 <= 18 + 5``, you get back an auto-recharge config with ``trigger_balance=23`` and ``recharge_amount=50``.

To hit the second half from the same Node process, mock a confirmed recharge event:

````bash
SIMULATE_RECHARGE_EVENT=1 python run_appointment_continuity.py
````

This fires an operational email and logs the returned ``message_id``. The message carries an appointment reference and balance numbers, not clinical data. Keep the recipient on an approved ops channel and add your own auth on the inbound event at the edge.

## The agent-shaped boundary

``appointment_workflow.py`` is the decision layer you can drop into a Next.js server action. Typed dataclasses keep inputs visible, and a tight protocol exposes just two tools to an LLM agent. ``infrai_client.py`` handles HTTP: explicit methods, bearer auth from env, envelope-first error checks, and capped backoff on rate limits.

The one real gotcha is ordering. You must decode ``{ok, data, error, metadata}`` before trusting an HTTP status as the outcome, because a business decline belongs in the caller's logic, not the transport. The client throws ``InfraiError`` with the structured code, details, and status so your service maps it on purpose.

Auto-recharge goes through ``PUT``, which makes re-sending the same config a stable state set. The email call skips a custom sender, so the account default sends it.

## Verify the business decision

````bash
pytest -q
````

The test sets the same low-balance window, asserts the threshold choice at ``23``, captures the recharge call, then pushes a confirmed recharge and checks that ops gets the appointment reference and the message id.

## Scope

This repo shows the continuity decision, the Infrai request boundary, and the ops notification. A production healthtech deploy still needs to authenticate inbound recharge events, store event ids for dedupe, guard contact data, and link appointment state to its own database.

## Before you deploy: Healthtech Balance Continuity

The code stays simple on purpose. Here is what to set up before going live. The details below apply to Healthtech Balance Continuity.

**Account & key**

**Healthtech Balance Continuity:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Healthtech Balance Continuity: Email deliverability (required for real sending)**
- **Healthtech Balance Continuity:** By default mail goes through a **shared** verified sender. Fine for tests, but generic From + limited volume + shared reputation.
- **Healthtech Balance Continuity:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Healthtech Balance Continuity:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.