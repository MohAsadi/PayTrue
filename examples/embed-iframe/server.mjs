// SPDX-License-Identifier: Apache-2.0
// EXPERIMENTAL: embedding the hosted checkout in another frontend. Two origins run here, as they would in real life, on two free ports that it prints:
//   YOUR site         the embedding page, plus the one server endpoint that holds the API key
//   the PayTrue stub  the hosted checkout, allowed to be framed by YOUR origin only
// Embedded checkout is separately gated in the specification; the message protocol used here is a proposal (packages/sdk/src/embed.js).
//
//   node examples/embed-iframe/server.mjs        then open the URL of your site that it prints
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { loadConfig } from "../../packages/config/src/index.js";
import { PayTrueClient } from "../../packages/sdk/src/index.js";
import { createDevServer } from "../../packages/devserver/src/server.mjs";

// two free ports, so the example does not collide with anything on your machine (some systems reserve 8080 or 5000)
async function freePort() {
  const s = createServer();
  await new Promise((r) => s.listen(0, "127.0.0.1", r));
  const { port } = s.address();
  await new Promise((r) => s.close(r));
  return port;
}
const SITE_PORT = await freePort();
const STUB_PORT = await freePort();
const SITE = `http://127.0.0.1:${SITE_PORT}`;
const API_KEY = "example_key_not_a_secret"; // hygiene: allow-secret (a dummy value)

const config = loadConfig({
  PAYTRUE_PUBLIC_ORIGIN: `http://127.0.0.1:${STUB_PORT}`,
  PAYTRUE_ALLOWED_FRAME_ANCESTORS: SITE, // the ONLY origin that may frame the checkout
  PAYTRUE_COOKIE_SAMESITE: "lax",
  PAYTRUE_API_KEY: API_KEY,
});
const stub = createDevServer({ config, apiKey: API_KEY });
await stub.listen(STUB_PORT);
const client = new PayTrueClient({ baseUrl: config.api.baseUrl, apiKey: API_KEY });

const file = (rel) => readFileSync(new URL(rel, import.meta.url));
const sdkEmbed = readFileSync(new URL("../../packages/sdk/src/embed.js", import.meta.url));

const site = createServer(async (req, res) => {
  const url = new URL(req.url, SITE);
  if (req.method === "GET" && url.pathname === "/") return res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }).end(file("./index.html"));
  if (req.method === "GET" && url.pathname === "/host.js") return res.writeHead(200, { "Content-Type": "text/javascript" }).end(file("./host.js"));
  if (req.method === "GET" && url.pathname === "/embed.js") return res.writeHead(200, { "Content-Type": "text/javascript" }).end(sdkEmbed);
  // the ONLY place that holds the API key: your server creates the session; the browser only ever receives the id and the origin
  if (req.method === "POST" && url.pathname === "/session") {
    const s = await client.createCheckoutSession({
      mode: "payment", amount: 4900, currency: "EUR", client_reference_id: `order-${Date.now()}`,
      success_url: `${SITE}/?done={CHECKOUT_SESSION_ID}`, cancel_url: `${SITE}/?cancelled={CHECKOUT_SESSION_ID}&reason={CANCEL_REASON}`,
      payer_policy: "any_wallet", display: { merchant_name: "Example Shop", description: "An embedded checkout" },
    });
    return res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify({ sessionId: s.id, checkoutBaseUrl: config.checkout.baseUrl, checkoutOrigin: config.checkout.origin }));
  }
  res.writeHead(404).end("not found");
});
await new Promise((r) => site.listen(SITE_PORT, "127.0.0.1", r));
console.log(`your site        ${SITE}\nhosted checkout  ${config.checkout.baseUrl} (a development stub: no wallet, no chain)\nOpen ${SITE} in a browser. Ctrl+C stops both.`);
process.on("SIGINT", async () => {
  await stub.close();
  site.close(() => process.exit(0));
});
