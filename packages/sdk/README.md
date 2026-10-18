# @paytrue/sdk

A dependency-free client for the PayTrue checkout API, **signed webhook verification** with replay window, deduplication and ordering, and **experimental** helpers for embedding the hosted
checkout. It has **no default host**: you pass the `baseUrl` of your own deployment, of the development stub, or of a PayTrue Cloud endpoint if you choose one.

> Pre-alpha. Not published to npm (`"private": true`). It implements the **proposed** API of `spec/checkout/`; no production server implements that API yet (the development stub in
> `packages/devserver` does, in memory). [Headless use](../../docs/headless.md) and [open-source readiness](../../docs/open-source-readiness.md).

```js
import { PayTrueClient, verifyWebhook, signatureHeaderOf, createEventTracker } from "@paytrue/sdk";

const client = new PayTrueClient({ baseUrl: "https://pay.example.com/paytrue", apiKey: process.env.PAYTRUE_API_KEY });
const session = await client.createCheckoutSession({ mode: "payment", amount: 4900, currency: "EUR", /* ... */ });

// in your webhook endpoint, on the RAW body:
const event = verifyWebhook({ payload: rawBody, header: signatureHeaderOf(req.headers), secret: process.env.PAYTRUE_WEBHOOK_SECRET });
```

| Export | Purpose |
|---|---|
| `PayTrueClient` | `createCheckoutSession`, `retrieveCheckoutSession`, `listCheckoutSessions`, `cancelCheckoutSession`; idempotency keys; `PayTrueApiError`, `PayTrueValidationError` |
| `validateCreateSessionParams` | The catalog's request rules, checked locally |
| `signWebhook`, `verifyWebhook`, `signatureHeaderOf`, `WebhookVerificationError` | HMAC-SHA-256 over `t.body`; rotation overlap; stable failure reasons |
| `createEventTracker` | Deduplicate by event id; apply an event only if its `session_version` is higher; `completed`, `failed`, `expired`, `cancelled` are final |
| `@paytrue/sdk/embed` | Browser-safe, **experimental**: `buildFrameUrl`, `acceptEmbedMessage` (exact origin, exact frame, exact shape), `FRAME_ATTRIBUTES` |

Rules the SDK is built around: **never fulfil from the success redirect**; fulfil on `completed` only; `unknown` is never `failed` and is never fulfilled.

```bash
node --test "test/*.test.mjs"
```

License: Apache-2.0.
