# @paytrue/devserver: the development stub

> **This is NOT a payment server.** It is an in-memory stand-in for part of the proposed checkout API, so that you can build and test an integration, run the examples and try reverse-proxy
> layouts on a laptop. It has **no wallet, no chain access, no persistence and no real security**, every page says so, and it **refuses to start with `PAYTRUE_ENV=production`**.

What it implements: `POST/GET /v1/checkout/sessions`, `GET .../{id}`, `POST .../{id}/cancel` with an API key and idempotency keys; a placeholder hosted page at `<route>/<session id>` with buttons that
**simulate** `processing`, `completed`, `unknown`, `failed`, `expired` and `cancelled`; signed webhooks for every transition; the framing policy (`frame-ancestors`), the cookie attributes and the
base path from `@paytrue/config`; and the experimental embed messages when you name an allowed frame ancestor.

```bash
PAYTRUE_PUBLIC_ORIGIN=http://localhost:8787 PAYTRUE_LISTEN_PORT=8787 PAYTRUE_WEBHOOK_URL=http://127.0.0.1:9000/webhooks node bin/paytrue-devserver.mjs
```

The command prints the merchant API root and the hosted URL; a random API key and webhook secret are generated unless you set `PAYTRUE_API_KEY` and `PAYTRUE_WEBHOOK_SECRET`.

What it does not do, and how it differs from the proposed API, is listed in [headless use](../../docs/headless.md). Its tests (`node --test "test/*.test.mjs"`) exercise the SDK, the configuration package
and every layout end to end.

Not published, never to be published. License: Apache-2.0.
