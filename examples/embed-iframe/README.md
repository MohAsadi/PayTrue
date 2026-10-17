# Embedding the hosted checkout in your own frontend (experimental)

```bash
node examples/embed-iframe/server.mjs        # prints two local URLs; open the one marked "your site"
```

Two origins run on two free ports, as they would in real life: **your site** (the embedding page and the one endpoint that holds the API key) and **the hosted checkout** (the development stub,
allowed to be framed by your origin only). Your page frames the checkout and shows the messages it believed.

What to look for:

- The **checkout** answers with `Content-Security-Policy: frame-ancestors <your origin>`. With the setting empty it is `'none'`.
- Your page accepts a message only if `acceptEmbedMessage` says so: **exact checkout origin**, **the frame your page created**, **this session**, **exact shape**. Everything else is ignored.
- Open the same page from a different origin (for example `localhost` instead of `127.0.0.1`) and the browser refuses to render the frame: *violates the following Content Security Policy directive:
  "frame-ancestors ..."*.
- The page never receives a signature, a secret or a wallet address, and **nothing it receives is proof of payment**: fulfil from a signed webhook or an authenticated read.

Embedded checkout is separately gated in the specification, the message protocol is a proposal, and wallets inside a cross-origin frame are unverified: [embedding](../../docs/embedding.md).
