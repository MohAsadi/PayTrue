# Checkout API catalog (proposed)

| Field | Value |
|---|---|
| Artifact | FP-API-001 (new, proposed) |
| Version | 0.1.0 |
| Date | 2026-10-17 |
| Status | **PROPOSED. NOT PROTOCOL-FROZEN. REQUIRES SECURITY REVIEW. REQUIRES PRIVACY REVIEW.** Names, paths, fields, limits and error codes are proposals. Nothing here is implemented or approved, and it is not protocol evidence |
| Owner | Payments Core lead, Merchant PM |
| Governing document | [19 — Checkout session and wallet-connection profile](../19-checkout-session-and-wallet-connect-profile.md). On any difference, document 19 decides |

## 1. Conventions

| Topic | Convention (proposed) |
|---|---|
| Base path | `/v1` |
| Format | JSON, UTF-8; field names in `snake_case`; timestamps RFC 3339 UTC; money as integers in minor units (ADR-011) |
| Versioning | A date-based `FastPay-Version` request header; the response and every webhook state the version used |
| Merchant authentication | A scoped, hashed, rotatable API key in the `Authorization` header (OD-014, TB-03). `merchantId` and live or test mode come from the key. No cookies |
| Customer-page authentication | None. The hosted page proves nothing about the customer. It holds a server-issued **control token** in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie scoped to the checkout origin and the session (doc 19 SX-09); the token is never read from a URL, a query parameter or a body |
| Idempotency | The `Idempotency-Key` header is required on every merchant `POST`. Same key and body: the stored result. Same key, different body: `idempotency_conflict`. The length of the window in which keys are remembered is an API parameter, not set here (doc 19 OPN-17) |
| Concurrency | Every state-changing call of the hosted page carries `expected_session_version`; a mismatch returns `session_version_conflict` and changes nothing (doc 19 §5.4) |
| Errors | `{ "error": { "type", "code", "message", "param" } }`; `code` is stable and machine-readable; `message` is for humans and may change |
| Rate limiting | Per API key and per source address; an excess returns `429 rate_limited` with a retry hint. The numbers are an operational parameter, not set here (MI-07) |
| Audit | Every call and every refusal is logged with the key id or control-token id, the idempotency key, the request hash, the result and the time. Bodies are redacted (doc 19 SX-11, MI-08) |

**What no endpoint does.** No endpoint returns a receiving address for a session, creates a wallet, derives or stores a key, accepts a seed phrase or a private key, accepts a customer email, or returns `expected_customer_wallet` to the customer's browser (doc 19 CSD-04, CSD-05, CSD-08, SX-06).

## 2. Merchant API

| Method and path | Purpose | Idempotent | Transitions | Notes |
|---|---|---|---|---|
| `POST /v1/checkout/sessions` | Create a session | By `Idempotency-Key` | TR-01 | §3 |
| `GET /v1/checkout/sessions/{id}` | Read a session (includes `metadata`) | Yes | none | Authenticated; the merchant's own sessions only; returns the true state (doc 19 RD-04) |
| `GET /v1/checkout/sessions` | List sessions | Yes | none | Filters: `client_reference_id`, `status`, `created_after`, `created_before`; cursor pagination. Lets a merchant find two sessions for one order (doc 19 OPN-03) |
| `POST /v1/checkout/sessions/{id}/cancel` | Cancel a session that is not yet submitted | By `Idempotency-Key` | TR-22 | After a submission: `session_already_submitted`. Sets `cancel_reason = merchant_cancelled` |

Webhook endpoint registration, secret rotation and the dead-letter view belong to the merchant platform (surface S15) and are **not defined here**. Their delivery rules are in the [event catalog](event-catalog.md).

## 3. `POST /v1/checkout/sessions`

### 3.1 Request

| Field | Type | Required | Validation |
|---|---|---|---|
| `mode` | string | yes | `payment` or `subscription`. `setup` is reserved: `mode_not_available` |
| `amount` | integer | yes | Minor units. `payment`: at least 1. `subscription`: 0 for no initial charge; above 0 is rejected until `chargeInitial` exists (`initial_charge_not_available`). Never a decimal. At most the merchant's configured maximum |
| `currency` | string | yes | ISO 4217; a currency of `TokenPolicyRegistry` (`unsupported_currency`) |
| `client_reference_id` | string | yes | The merchant's order reference; length-limited |
| `success_url` | string | yes | §5 |
| `cancel_url` | string | yes | §5 |
| `allowed_chains` | list of integers | no | A subset of the chains enabled for the key's mode; default: the merchant's enabled chains (`chain_not_allowed`) |
| `allowed_tokens` | list of objects `{chain_id, address}` | no | A subset of the registry tokens of those chains with status `SETTLEMENT` or `DIRECT_PAYMENT`; default: the merchant's default list (`token_not_allowed`) |
| `expected_customer_wallet` | string | no | Required when `payer_policy` is `expected_wallet`, forbidden otherwise; EIP-55 checksummed (`invalid_wallet_address`, `payer_policy_mismatch`) |
| `payer_policy` | string | yes | `any_wallet` or `expected_wallet` |
| `expires_in` | integer, seconds | no | Default 1,800; inside the bounds of CSR-01 (proposed 600 to 86,400; `invalid_expiry`) |
| `metadata` | object of strings | no | §3.3 |
| `display` | object | yes | `merchant_name`, `description`, optional `line_items`; no personal data; length-limited |
| `mandate_terms` | object | for `subscription` | The `MandateTerms` the merchant requests; validated against the registry and the dual cap model |

### 3.2 Example

```json
{
  "mode": "payment",
  "amount": 4900,
  "currency": "EUR",
  "client_reference_id": "order-10432",
  "success_url": "https://shop.example/checkout/done?session={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://shop.example/cart?session={CHECKOUT_SESSION_ID}&reason={CANCEL_REASON}",
  "payer_policy": "any_wallet",
  "expires_in": 1800,
  "display": { "merchant_name": "Example Shop", "description": "Order 10432" },
  "metadata": { "cart": "c_8821" }
}
```

### 3.3 Limits (proposed values, not approved)

| Limit | Proposed |
|---|---|
| `metadata` keys | at most 20 |
| `metadata` key length | at most 40 bytes |
| `metadata` value length | at most 500 bytes |
| `metadata` total | at most 4 KiB; string values only; no nesting (`metadata_too_large`) |
| URL length | at most 2,048 characters |
| `client_reference_id`, `display` fields | length-limited; the values are set with the API review |

### 3.4 Response (`201`)

| Field | Notes |
|---|---|
| `id` | The session id: `cs_` and at least 128 bits of entropy (doc 19 §2.2) |
| `url` | `https://<checkout-origin>/c/<id>`: the id and nothing else |
| `status` | `open` |
| `created_at`, `expires_at` | RFC 3339 UTC |
| `client_secret` | **Only** for an approved embedded-checkout flow. **Absent for Hosted Checkout v1.** Hosted Checkout does not expose a client secret to the merchant's browser |
| `mode`, `amount`, `currency`, `client_reference_id`, `payer_policy`, `live_mode`, `session_version` | Echoed |

## 4. Errors of the merchant API

| HTTP | `code` | When |
|---|---|---|
| 400 | `invalid_amount`, `unsupported_currency`, `invalid_expiry`, `invalid_url`, `url_not_registered`, `invalid_wallet_address`, `payer_policy_mismatch`, `chain_not_allowed`, `token_not_allowed`, `metadata_too_large`, `invalid_display`, `invalid_mandate_terms`, `mode_not_available`, `initial_charge_not_available` | A field fails validation; nothing is created |
| 401 | `unauthorized` | Missing or invalid key |
| 403 | `live_mode_not_enabled`, `key_scope_insufficient` | The key may not do this |
| 404 | `session_not_found` | Unknown id, or a session of another merchant (the same answer) |
| 409 | `idempotency_conflict`, `session_already_submitted`, `session_version_conflict` | See the conventions and doc 19 §5 |
| 429 | `rate_limited` | Over a limit |

## 5. URL rules (doc 19 RD-01, RD-03)

- HTTPS only (the test mode also allows `http` on `localhost`); no credentials, no fragment, no IP literal; at most 2,048 characters.
- The host must belong to a domain the merchant has registered; otherwise `url_not_registered`.
- The only substitutions are `{CHECKOUT_SESSION_ID}` (either URL) and `{CANCEL_REASON}` (the cancel URL only). Nothing else is appended or substituted.
- `{CANCEL_REASON}` is one of `no_wallet`, `wallet_unsupported`, `customer_cancelled`, `session_expired`. It is a hint and is never authoritative.

## 6. Hosted-page API (internal; not for merchants)

The hosted checkout page calls these endpoints. Merchants never do. All are under `/v1/public/checkout/sessions/{id}` and every state-changing call carries the control token, an `Origin` equal to the checkout origin and `expected_session_version`.

| Method and path | Caller | Purpose | Transitions |
|---|---|---|---|
| `GET /` | Any browser holding the URL | The customer-visible view: `display`, amount, currency, status, `expires_at`, allowed chains and tokens, the page's own permitted actions. **Never** `metadata`, `expected_customer_wallet`, a payer or any address | none |
| `GET /status` | The controlling context or a viewer | Light state for polling or an event stream: status, `session_version`, outstanding request id | none |
| `POST /control` | A browser context | Take or hold the control lease; sets the control cookie; evented and rate-limited | audit `lease.taken` |
| `POST /connection` | The controlling context | Report that a connection started or ended, with the connector class, the account and the chain | TR-02, TR-03, TR-04, TR-07 |
| `POST /review` | The controlling context | Obtain the quote and plan for the current revision; idempotent per revision | TR-05, TR-06 |
| `POST /authorizations` | The controlling context | Start the signing request for the current revision after the ten checks | TR-08 |
| `POST /signatures` | The controlling context | Submit a signature, or report a rejection, for the outstanding request | TR-09, TR-10 |
| `POST /transactions` | The controlling context | Report the hash of a customer-sent final transaction | TR-12, TR-13 |
| `POST /cancel` | The controlling context | Cancel before a submission, with an optional customer reason | TR-22 |

No endpoint of this group accepts a seed, a key or an email, and none returns a signature.

## 7. Status of this catalog

Proposed, unreviewed, not implemented. The names are not frozen. Every numeric value is a proposal (doc 19 OPN-17). Embedded Checkout and Payment Links add endpoints that are **not** defined here and are separately gated (doc 19 §14.6).
