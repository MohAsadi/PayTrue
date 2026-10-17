#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Starts the PayTrue DEVELOPMENT STUB from the PAYTRUE_* environment (see .env.example). Never for production.
import { randomBytes } from "node:crypto";
import { loadConfig } from "../../config/src/index.js";
import { createDevServer } from "../src/server.mjs";

let config;
try {
  config = loadConfig(process.env);
} catch (e) {
  console.error(e.message);
  process.exit(2);
}
if (config.production) {
  console.error("refusing to start: PAYTRUE_ENV=production. The development stub is not a payment server and never runs in production.");
  process.exit(2);
}
const dev = process.env.PAYTRUE_DEV_PRINT_SECRETS === "true";
const apiKey = config.secret("apiKey") ?? "dev_key_" + randomBytes(12).toString("hex");
const webhookSecret = config.secret("webhook") ?? "dev_whsec_" + randomBytes(16).toString("hex");
const host = process.env.PAYTRUE_LISTEN_HOST ?? "127.0.0.1";
const port = Number(process.env.PAYTRUE_LISTEN_PORT ?? "8080");
const stub = createDevServer({ config, apiKey, webhookSecret, webhookUrl: process.env.PAYTRUE_WEBHOOK_URL });
const addr = await stub.listen(port, host);
console.log(`PayTrue DEVELOPMENT STUB (no wallet, no chain, no money) listening on http://${addr.address}:${addr.port}`);
console.log(`  merchant API : ${config.api.baseUrl}/v1/checkout/sessions`);
console.log(`  hosted page  : ${config.checkout.baseUrl}${config.checkout.route}/<session id>`);
if (!config.secret("apiKey")) console.log("  no PAYTRUE_API_KEY set: a random key was generated for this run" + (dev ? `: ${apiKey}` : " (set PAYTRUE_DEV_PRINT_SECRETS=true to print it)"));
if (!config.secret("webhook")) console.log("  no PAYTRUE_WEBHOOK_SECRET set: a random secret was generated for this run" + (dev ? `: ${webhookSecret}` : ""));
process.on("SIGINT", () => stub.close().then(() => process.exit(0)));
process.on("SIGTERM", () => stub.close().then(() => process.exit(0)));
