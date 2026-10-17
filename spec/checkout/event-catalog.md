# Checkout event catalog (proposed)

| Field | Value |
|---|---|
| Artifact | FP-API-002 (new, proposed) |
| Version | 0.1.0 |
| Date | 2026-10-17 |
| Status | **PROPOSED. NOT PROTOCOL-FROZEN. REQUIRES SECURITY REVIEW.** Event names, fields, the replay window and the retry schedule are proposals. Nothing here is implemented or approved, and it is not protocol evidence |
| Owner | Payments Core lead, Merchant PM |
| Governing document | [19 — Checkout session and wallet-connection profile](../19-checkout-session-and-wallet-connect-profile.md) §16. On any difference, document 19 decides |

## 1. Events

| Event | Session state | Emitted at (doc 19 §5.2) | A merchant may fulfil? |
|---|---|---|---|
| `checkout.session.opened` | `open` | TR-01. The session was created. It does **not** mean a customer has seen the page | No |
| `checkout.session.processing` | `processing` | TR-13, the first time only: a transaction hash is recorded and it is not final | No |
| `checkout.session.completed` | `completed` | TR-16, TR-19: final, under the finality rule approved for the chain | **Yes, and only here** |
| `checkout.session.failed` | `failed` | TR-17, TR-20, TR-21: positive evidence that no successful payment occurred, and no further attempt is allowed | No |
| `checkout.session.expired` | `expired` | TR-23: `expires_at` passed before any submission | No |
| `checkout.session.unknown` | `unknown` | TR-15, TR-18: a submission may have occurred and the outcome is not known | **No** |
| `checkout.session.cancelled` | `cancelled` | TR-22: ended by the customer or the merchant before any submission | No |

No event is sent for an attempt that fails and is retried inside the session, for a connection, a quote or a signature. Those are audit events (doc 19 §5.8).

## 2. Envelope

```json
{
  "id": "evt_01J9ZK3Q8X7M4N2B6C5D0E1F2G",
  "type": "checkout.session.completed",
  "api_version": "2026-10-17",
  "created": "2026-10-17T14:02:11Z",
  "live_mode": false,
  "merchant_id": "mer_4F2A91",
  "data": {
    "session_id": "cs_...",
    "client_reference_id": "order-10432",
    "mode": "payment",
    "state": "completed",
    "session_version": 11,
    "payment_id": "0x...",
    "mandate_id": null,
    "failure_reason": null,
    "unknown_reason": null,
    "cancel_reason": null,
    "chain_id": 84532,
    "transaction_hash": "0x...",
    "finality_state": "final",
    "payer": "0x...",
    "initial_charge_settled": null,
    "metadata": { "cart": "c_8821" }
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string | **Stable event id**: the same on every retry; unique per event |
| `type` | string | One of the seven names |
| `api_version` | string | The version of this schema (a date) |
| `created` | string | RFC 3339 UTC time at which the event was created |
| `live_mode` | boolean | Test and live events never share an endpoint or a secret |
| `merchant_id` | string | The merchant of the session |
| `data.session_id` | string | |
| `data.client_reference_id`, `data.mode`, `data.metadata` | | Echoed to the merchant |
| `data.state` | string | The state entered, in lower case |
| `data.session_version` | integer | The version at which the event was created; the ordering key |
| `data.payment_id` | string or null | The `paymentId`, once the chain is chosen for a `payment` |
| `data.mandate_id` | string or null | The mandate of a `subscription` that reached activation |
| `data.failure_reason` | string or null | The `failure_code` for `failed` |
| `data.unknown_reason` | string or null | The `unknown_reason` for `unknown` |
| `data.cancel_reason` | string or null | The stable code for `cancelled` |
| `data.chain_id` | integer or null | Where relevant |
| `data.transaction_hash` | string or null | The latest hash, where relevant |
| `data.finality_state` | string | `not_submitted`, `pending`, `final` or `unresolved` |
| `data.payer` | string or null | For `processing`, `unknown`, `completed` and a `failed` after a submission; otherwise null |
| `data.initial_charge_settled` | boolean or null | For a `completed` `subscription` only |

An event never carries a signature, a secret, an email or a seed.

## 3. Fields by event

| Event | `state` | `payment_id` | `mandate_id` | reason | `chain_id` | `transaction_hash` | `finality_state` | `payer` |
|---|---|---|---|---|---|---|---|---|
| opened | `open` | null | null | none | null | null | `not_submitted` | null |
| processing | `processing` | set (`payment`) | null | none | set | set | `pending` | set |
| completed | `completed` | set (`payment`) | set (`subscription`) | none | set | set | `final` | set |
| failed | `failed` | set if the chain was chosen | null | `failure_reason` | set if chosen | set if a submission occurred | `final` after a submission; `not_submitted` if it ended before one | set after a submission |
| expired | `expired` | set if the chain was chosen | null | none | set if chosen | null | `not_submitted` | null |
| unknown | `unknown` | set | null | `unknown_reason` | set | set if known | `unresolved` | set |
| cancelled | `cancelled` | set if the chain was chosen | null | `cancel_reason` | set if chosen | null | `not_submitted` | null |

**`finality_state`.** `not_submitted`: no transaction was submitted. `pending`: submitted, not final. `final`: the outcome is final (`completed`, or a `failed` proven by a final revert or by proven non-settlement). `unresolved`: `unknown`. `completed` is emitted only when the receipt and the settlement event agree across at least two independent sources at the finality threshold of the chain. **No per-chain rule is approved today** (doc 19 OPN-15); a chain without one is not enabled for live mode.

## 4. Delivery

| Topic | Rule (all values proposed) |
|---|---|
| Transport | HTTPS `POST` to the merchant's endpoint, through the egress proxy with a deny-list of internal ranges (TB-12) |
| Signature | Header `FastPay-Signature: t=<unix seconds>,v1=<hex>`. `v1` is the HMAC-SHA-256, under the endpoint's secret, of `t`, a full stop and the raw body. The merchant verifies it on the raw body with a constant-time comparison |
| Replay window | The merchant rejects a request whose `t` is more than 5 minutes from its clock. FastPay re-signs every retry with a fresh `t` |
| Retry | A response other than 2xx within the timeout is retried with exponential backoff and jitter for up to 72 hours |
| Circuit breaker and dead letter | An endpoint that keeps failing trips a breaker; events wait in a dead letter that the merchant's dashboard shows and can replay |
| Deduplication | At least once. The merchant deduplicates by `id`; a retry has the same `id` and the same body apart from the signature timestamp |
| Ordering | **Not guaranteed.** Apply an event only if `data.session_version` is higher than the last one applied for the session. `completed`, `failed`, `expired` and `cancelled` are final. `unknown` can be followed by `completed` or `failed`. `processing` may arrive after `completed` and is then ignored |
| Secrets | One per endpoint, rotatable, with an overlap in which both are accepted |
| Live and test | Separate endpoints and secrets |
| Fulfilment | On `completed` only |

## 5. What the merchant must do

1. Verify the signature and the timestamp on the raw body.
2. Deduplicate by `id`.
3. Apply an event only if its `session_version` is higher than the last applied.
4. Fulfil on `completed` only; never on `unknown`, `processing` or a redirect.
5. For any doubt, read the session through `GET /v1/checkout/sessions/{id}` ([API catalog](api-catalog.md)).

## 6. Status of this catalog

Proposed, unreviewed, not implemented. The replay window, the retry schedule and every length are proposals (doc 19 OPN-17).
