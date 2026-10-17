// SPDX-License-Identifier: Apache-2.0
// HEADLESS use: your server creates a checkout session through the API, learns the result from a SIGNED WEBHOOK, and fulfils the order only on `completed`.
// It never fulfils from the success redirect, and it never trusts a webhook it has not verified, deduplicated and put in order.
//
// This example runs fully offline against the development stub of this repository (in memory, no wallet, no chain). To point it at your own deployment,
// set PAYTRUE_BASE_URL, PAYTRUE_API_KEY and PAYTRUE_WEBHOOK_SECRET and receive the webhooks on your own endpoint; the SDK calls are the same.
//
//   node examples/headless-node/index.mjs
import { createServer } from "node:http";
import { loadConfig } from "../../packages/config/src/index.js";
import { PayTrueClient, createEventTracker, signatureHeaderOf, verifyWebhook } from "../../packages/sdk/src/index.js";
import { createDevServer } from "../../packages/devserver/src/server.mjs";

const API_KEY = "example_key_not_a_secret"; // hygiene: allow-secret (a dummy value)
const WEBHOOK_SECRET = "example_whsec_not_a_secret"; // hygiene: allow-secret (a dummy value)

async function freePort() {
  const s = createServer();
  await new Promise((r) => s.listen(0, "127.0.0.1", r));
  const { port } = s.address();
  await new Promise((r) => s.close(r));
  return port;
}

// ---- 1. YOUR webhook endpoint: verify the signature on the RAW body, then deduplicate and order, then act
const tracker = createEventTracker();
const fulfilled = [];
const webhook = createServer((req, res) => {
  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    try {
      const event = verifyWebhook({ payload: Buffer.concat(chunks), header: signatureHeaderOf(req.headers), secret: WEBHOOK_SECRET });
      const verdict = tracker.consider(event);
      console.log(`  webhook ${event.type.padEnd(28)} v${event.data.session_version} -> ${verdict.apply ? "applied" : "ignored (" + verdict.reason + ")"}`);
      // fulfil on `completed` ONLY: never on opened, processing, unknown or a redirect
      if (verdict.apply && event.type === "checkout.session.completed") fulfilled.push(event.data.client_reference_id);
      res.writeHead(200).end("ok");
    } catch (e) {
      console.log(`  webhook rejected: ${e.reason ?? e.message}`);
      res.writeHead(400).end("rejected");
    }
  });
});
await new Promise((r) => webhook.listen(0, "127.0.0.1", r));
const webhookUrl = `http://127.0.0.1:${webhook.address().port}/webhooks`;

// ---- 2. the PayTrue side: the development stub on a free port (replace this block with your own deployment)
const port = await freePort();
const config = loadConfig({ PAYTRUE_PUBLIC_ORIGIN: `http://127.0.0.1:${port}`, PAYTRUE_API_KEY: API_KEY, PAYTRUE_WEBHOOK_SECRET: WEBHOOK_SECRET });
const stub = createDevServer({ config, apiKey: API_KEY, webhookSecret: WEBHOOK_SECRET, webhookUrl });
await stub.listen(port);
console.log(`development stub on ${config.api.baseUrl} (no wallet, no chain, no money)`);

// ---- 3. create the session from your server; the customer would be redirected to session.url
const client = new PayTrueClient({ baseUrl: process.env.PAYTRUE_BASE_URL ?? config.api.baseUrl, apiKey: process.env.PAYTRUE_API_KEY ?? API_KEY });
const session = await client.createCheckoutSession({
  mode: "payment",
  amount: 4900, // minor units: 49.00 EUR
  currency: "EUR",
  client_reference_id: "order-10432",
  success_url: "https://shop.example/done?session={CHECKOUT_SESSION_ID}",
  cancel_url: "https://shop.example/cart?session={CHECKOUT_SESSION_ID}&reason={CANCEL_REASON}",
  payer_policy: "any_wallet",
  display: { merchant_name: "Example Shop", description: "Order 10432" },
  metadata: { cart: "c_8821" },
});
console.log(`created ${session.id}\n  send the customer to ${session.url}`);

// ---- 4. the customer "pays" (stub only: a real customer signs in a wallet and the chain settles)
const act = (action) => fetch(`${session.url}/simulate`, { method: "POST", headers: { Origin: config.checkout.origin, "Content-Type": "application/x-www-form-urlencoded" }, body: `action=${action}` });
await act("pay");
await act("complete");

// ---- 5. confirm from the API as well: the redirect proves nothing, the authenticated read does
const final = await client.retrieveCheckoutSession(session.id);
console.log(`authenticated read: status=${final.status}`);
console.log(`fulfilled orders: ${JSON.stringify(fulfilled)}`);

await stub.close();
await new Promise((r) => webhook.close(r));
if (final.status !== "completed" || fulfilled.length !== 1) {
  console.error("unexpected result");
  process.exit(1);
}
console.log("ok: one order, fulfilled once, on `completed`");
