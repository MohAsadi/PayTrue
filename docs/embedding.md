# Embedding PayTrue in another frontend

There are three ways to use the checkout from your own frontend. They differ in how much of the page you control and in how much is built.

| Way | What you do | State |
|---|---|---|
| **Redirect** (recommended) | Your server creates a session and sends the customer to its `url`; the customer returns to your `success_url` or `cancel_url` | Specified; the stub implements the API and a placeholder page |
| **Iframe** (experimental) | Your page frames the hosted checkout and listens for a small set of messages | Experimental. The specification gates embedded checkout separately (decision CSD-10); the message protocol is a proposal of this repository |
| **Your own payment UI** | You build the wallet connection and the signing screens yourself | **Not available.** There is no wallet-connection layer in the repository, and the specification keeps the signing UI in the hosted checkout |

## Redirect

```js
const session = await client.createCheckoutSession({ /* ... */ success_url: "https://shop.example/done?s={CHECKOUT_SESSION_ID}" });
// redirect the customer to session.url
```

The redirect proves nothing. Confirm the result from a **signed webhook** or an authenticated `retrieveCheckoutSession` ([headless use](headless.md)).

## Iframe (experimental)

1. **Your server** creates the session. The API key never reaches the browser; the browser receives the session id and the checkout origin.
2. **The checkout must allow your origin to frame it.** Set `PAYTRUE_ALLOWED_FRAME_ANCESTORS=https://shop.example.com` (named origins only: `*` is refused). The checkout answers with
   `Content-Security-Policy: frame-ancestors <your origins>`; with the setting empty it is `'none'` and no page can frame it.
3. **Your page** frames `buildFrameUrl({ checkoutBaseUrl, sessionId })` with the attributes in `FRAME_ATTRIBUTES` (`referrerpolicy="no-referrer"`, a restrictive `sandbox`).
4. **Your page listens** with `acceptEmbedMessage(event, { checkoutOrigin, frameWindow, sessionId })`, which accepts a message only if it comes from the **exact checkout origin**, from the
   **frame your page created**, for **that session**, with an **exact shape**. Anything else returns `null`.

The proposed protocol, version 1 (`@paytrue/sdk/embed`):

| Message | Fields | Meaning |
|---|---|---|
| `ready` | `source: "paytrue-checkout"`, `version: 1`, `sessionId` | The checkout loaded |
| `state` | as above, plus `state` (one of the 13 session states) | The state of the session at that moment |
| `resize` | as above, plus `height` (0 to 10000) | The content height |

Nothing else is accepted: no extra field, no other type, no other version. A message carries **no signature, no secret and no wallet address**.

### Rules for the embedding page

- **Never fulfil from a message.** A message is a hint for your user interface. Fulfil from a signed webhook or an authenticated read.
- Never put the API key, the webhook secret or a session's `metadata` in the page.
- Keep the origin check. A page that accepts messages from `*` can be told anything by any frame.

### What was verified

The example `examples/embed-iframe` runs two origins on two local ports. In a real browser (the Claude Browser pane, 2026-10-17):
the allowed origin received `ready` and `state` and `acceptEmbedMessage` accepted both; opening the same page from a different origin produced the browser error
*Framing ... violates the following Content Security Policy directive: "frame-ancestors ..."* and no message was accepted. The tests of `packages/sdk` and
`packages/devserver` cover the message parser, the origin and source checks, the nonce'd script and the policy header.

### What is not verified, and what is not solved

| Item | State |
|---|---|
| Wallet extensions inside a cross-origin iframe | **Unverified.** Some wallets inject their provider into top-level pages only; there is no wallet-lab test (gap GAP-02 of the specification). Expect to need a popup or a redirect for the signing step |
| Third-party cookies and storage partitioning | The checkout's control cookie is `SameSite=Strict` by default and a strict cookie is **not sent from a cross-site frame**. `SameSite=None; Secure` is needed for a cross-site embed and is allowed only in production over https. Browser behaviour differs and is **not verified** |
| Clickjacking | The default policy is `frame-ancestors 'none'`. An embed widens it to the origins you name; review that list like a CORS allow-list |
| A real hosted checkout | Does not exist yet; the example frames the development stub |

The specification's own gates for embedded checkout (frame policy, `postMessage` hardening, a separate review of the origin and content security policy) are in
`spec/19-checkout-session-and-wallet-connect-profile.md`, section 14.6.
