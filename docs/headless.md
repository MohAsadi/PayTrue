# Headless use: the API, the SDK and signed webhooks

"Headless" means your own server drives PayTrue and no PayTrue user interface is involved on your side. You create a checkout session, send the customer to its hosted page (or frame it,
see [embedding](embedding.md)), and learn the result from signed webhooks and from authenticated reads.

> **State.** The SDK implements the **proposed** checkout API (`spec/checkout/api-catalog.md`, `spec/checkout/event-catalog.md`). No production server implements that API yet; the
> **development stub** (`packages/devserver`) implements part of it in memory so that you can build and test your integration offline. The SDK has no default host: you give it a
> `baseUrl`, which is your own deployment, the stub, or a PayTrue Cloud endpoint if you choose to use one.

## The SDK

```js
import { PayTrueClient, verifyWebhook, signatureHeaderOf, createEventTracker } from "@paytrue/sdk";

const client = new PayTrueClient({
  baseUrl: process.env.PAYTRUE_BASE_URL,   // the API root without /v1, e.g. https://pay.example.com/paytrue
  apiKey: process.env.PAYTRUE_API_KEY,
});

const session = await client.createCheckoutSession({
  mode: "payment",
  amount: 4900,                            // minor units, an integer: 49.00
  currency: "EUR",
  client_reference_id: "order-10432",
  success_url: "https://shop.example/done?s={CHECKOUT_SESSION_ID}",
  cancel_url: "https://shop.example/cart?s={CHECKOUT_SESSION_ID}&reason={CANCEL_REASON}",
  payer_policy: "any_wallet",
  display: { merchant_name: "Example Shop", description: "Order 10432" },
}, { idempotencyKey: "order-10432-create" });   // make a retry safe
// send the customer to session.url
```

| Call | API | Notes |
|---|---|---|
| `createCheckoutSession(params, { idempotencyKey })` | `POST /v1/checkout/sessions` | Validates the parameters locally first (`PayTrueValidationError`). A random idempotency key is generated if you give none |
| `retrieveCheckoutSession(id)` | `GET /v1/checkout/sessions/{id}` | The authoritative state. Use it to confirm a result |
| `listCheckoutSessions({ client_reference_id, status, ... })` | `GET /v1/checkout/sessions` | Find sessions for an order, for example to detect two sessions for one order |
| `cancelCheckoutSession(id)` | `POST /v1/checkout/sessions/{id}/cancel` | Only before a transaction was submitted; afterwards `PayTrueApiError` with `session_already_submitted` |

An API error is a `PayTrueApiError` with `status`, `code`, `type` and `param`.

## The rules the API is built around

- **The redirect is not proof of payment.** `success_url` is reachable by anyone who types it. Fulfil from a signed webhook (`completed`) or from `retrieveCheckoutSession`.
- **Only `completed` is final success.** `processing` means a transaction was submitted; `unknown` means its outcome is not known and **you must not fulfil**; `failed`, `expired` and
  `cancelled` are final failures.
- **`unknown` is never `failed`.** Do not offer the customer a second payment while a session is `unknown`.
- **The only placeholders** in `success_url` and `cancel_url` are `{CHECKOUT_SESSION_ID}` (both) and `{CANCEL_REASON}` (cancel only). Nothing else is added to a redirect.
- **URLs are validated**: https (http only on localhost), no credentials, no fragment, no IP literal, at most 2,048 characters.

## Webhooks

```js
// the RAW body, before any JSON parsing
const event = verifyWebhook({
  payload: rawBody,
  header: signatureHeaderOf(request.headers),
  secret: process.env.PAYTRUE_WEBHOOK_SECRET,        // or [newSecret, oldSecret] during a rotation
  toleranceSeconds: 300,
});
const verdict = tracker.consider(event);            // createEventTracker(): in memory; keep the same rules in your database
if (verdict.apply && event.type === "checkout.session.completed") fulfil(event.data.client_reference_id);
```

| Property | Rule |
|---|---|
| Signature | Header `PayTrue-Signature: t=<unix seconds>,v1=<hex>`: HMAC-SHA-256, under your endpoint secret, of `<t>.<raw body>`. `FastPay-Signature`, the name in the unfrozen proposal, is also read |
| Replay window | You reject a timestamp more than `toleranceSeconds` (300 by default; a proposal) from your clock |
| Retries | At least once. Deduplicate by `id`; a retry has the same `id` |
| Ordering | **Not guaranteed.** Apply an event only if `data.session_version` is higher than the last one you applied for that session; `completed`, `failed`, `expired` and `cancelled` are final; `unknown` can be followed by `completed` or `failed` |
| Failure reasons | `verifyWebhook` throws `WebhookVerificationError` with a stable `reason`: `missing_header`, `malformed_header`, `timestamp_outside_tolerance`, `signature_mismatch`, `invalid_json` |

Return `2xx` only after you have processed (or safely stored) the event; anything else is retried.

## What the development stub does differently

| The proposed API | The stub |
|---|---|
| Specific error codes (`invalid_amount`, `unsupported_currency`, `url_not_registered`, ...) | One `validation_failed` with the list of problems in the message; `invalid_expiry`, `idempotency_conflict`, `session_already_submitted`, `unauthorized` as in the catalog |
| A hosted page where a customer connects a wallet and signs | A placeholder page with buttons that **simulate** the outcomes (`processing`, `completed`, `unknown`, `failed`, `expired`, `cancelled`) |
| Chain finality decides `completed` | You press a button |
| URLs registered per merchant | Not enforced |
| Persistence, retries with backoff, a dead letter | None: one delivery per event, `redeliver` to test deduplication |
| Production | **Refuses to start with `PAYTRUE_ENV=production`** |

## Try it

```bash
node examples/headless-node/index.mjs
```

The example starts the stub, creates a session, receives and verifies the webhooks, applies them in order and fulfils exactly once.
