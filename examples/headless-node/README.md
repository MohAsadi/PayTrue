# Headless: create a session, verify webhooks, fulfil once

```bash
node examples/headless-node/index.mjs
```

What it does, in order:

1. Starts **your webhook endpoint**. It verifies the signature on the raw body, deduplicates and orders events with `createEventTracker`, and fulfils an order only on `checkout.session.completed`.
2. Starts the **development stub** on a free port (replace this block with your own deployment).
3. Creates a session through `PayTrueClient`.
4. "Pays" through the stub's simulate buttons (a real customer signs in a wallet and the chain settles).
5. Confirms with an authenticated read as well, because the redirect proves nothing.

Expected end of the output: `ok: one order, fulfilled once, on completed`.

To use your own deployment instead of the stub, set `PAYTRUE_BASE_URL`, `PAYTRUE_API_KEY` and `PAYTRUE_WEBHOOK_SECRET` and receive the webhooks on your own endpoint; the SDK calls do not change.
Read [headless use](../../docs/headless.md) first.
