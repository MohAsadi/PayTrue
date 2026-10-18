// SPDX-License-Identifier: Apache-2.0
// End-to-end tests of the SDK, the configuration package and the development stub together: layouts (root, path, subdomain-style split), the
// state transitions of the proposed event catalog, signed webhooks, deduplication, ordering, and the rules about what may be cancelled.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { loadConfig } from "../../config/src/index.js";
import { PayTrueApiError, PayTrueClient, createEventTracker, signatureHeaderOf, verifyWebhook } from "../../sdk/src/index.js";
import { createDevServer } from "../src/server.mjs";

const API_KEY = "test_key_1234567890"; // hygiene: allow-secret (a dummy value)
const SECRET = "whsec_test_1234567890"; // hygiene: allow-secret (a dummy value)

async function freePort() {
  const s = createServer();
  await new Promise((r) => s.listen(0, "127.0.0.1", r));
  const { port } = s.address();
  await new Promise((r) => s.close(r));
  return port;
}

async function receiver() {
  const received = [];
  const server = createServer((req, res) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      received.push({ body: Buffer.concat(chunks).toString("utf8"), header: signatureHeaderOf(req.headers) });
      res.writeHead(200).end("ok");
    });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return { received, url: `http://127.0.0.1:${server.address().port}/webhooks`, close: () => new Promise((r) => { server.closeAllConnections?.(); server.close(r); }) };
}

/** Start the stub on a free port with the given PAYTRUE_* settings (the origin is filled in with the real port). */
async function start(extra = {}, { clock } = {}) {
  const port = await freePort();
  const origin = `http://127.0.0.1:${port}`;
  const hook = await receiver();
  const env = { PAYTRUE_PUBLIC_ORIGIN: origin, PAYTRUE_API_KEY: API_KEY, PAYTRUE_WEBHOOK_SECRET: SECRET, ...extra };
  const config = loadConfig(env);
  const stub = createDevServer({ config, apiKey: API_KEY, webhookSecret: SECRET, webhookUrl: hook.url, now: clock });
  await stub.listen(port);
  const client = new PayTrueClient({ baseUrl: config.api.baseUrl, apiKey: API_KEY });
  return { config, stub, client, hook, origin, close: async () => { await stub.close(); await hook.close(); } };
}

const PARAMS = (extra = {}) => ({
  mode: "payment", amount: 4900, currency: "EUR", client_reference_id: "order-1",
  success_url: "https://shop.example/done?s={CHECKOUT_SESSION_ID}", cancel_url: "https://shop.example/cart?s={CHECKOUT_SESSION_ID}&r={CANCEL_REASON}",
  payer_policy: "any_wallet", display: { merchant_name: "Example Shop", description: "Order 1" }, metadata: { cart: "c_1" }, ...extra,
});
const simulate = (t, session, action) => fetch(`${t.config.checkout.baseUrl}${t.config.checkout.route}/${session.id}/simulate`, {
  method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded", Origin: t.config.checkout.origin }, body: `action=${action}`,
});
const events = (t, extra = {}) => t.hook.received.map((r) => verifyWebhook({ payload: r.body, header: r.header, secret: SECRET, ...extra }));

test("the stub refuses to run in production", () => {
  const config = loadConfig({
    PAYTRUE_ENV: "production", PAYTRUE_PUBLIC_ORIGIN: "https://pay.example.com", PAYTRUE_CHAIN_IDS: "8453",
    PAYTRUE_RPC_URLS_8453: "https://a.example.org,https://b.example.net", PAYTRUE_DEPLOYMENT_FILE: "d.json",
  });
  assert.throws(() => createDevServer({ config, apiKey: "k" }), /never runs in production/);
});

test("root layout: create, retrieve and list through the SDK; the id is not guessable and the URL carries only the id", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    assert.match(s.id, /^cs_[a-z2-7]{27}$/);
    assert.equal(s.url, `${t.origin}/c/${s.id}`);
    assert.equal(s.status, "open");
    assert.equal(s.metadata.cart, "c_1");
    assert.equal((await t.client.retrieveCheckoutSession(s.id)).id, s.id);
    const listed = await t.client.listCheckoutSessions({ client_reference_id: "order-1" });
    assert.equal(listed.data.length, 1);
    assert.equal((await t.client.listCheckoutSessions({ client_reference_id: "nope" })).data.length, 0);
    assert.equal(new URL(s.url).search, "");
  } finally {
    await t.close();
  }
});

test("path layout: everything lives under the base path and nothing answers outside it", async () => {
  const t = await start({ PAYTRUE_BASE_PATH: "/paytrue" });
  try {
    assert.equal(t.config.api.baseUrl, `${t.origin}/paytrue`);
    const s = await t.client.createCheckoutSession(PARAMS());
    assert.equal(s.url, `${t.origin}/paytrue/c/${s.id}`);
    assert.equal((await fetch(s.url)).status, 200);
    assert.equal((await fetch(`${t.origin}/v1/checkout/sessions`, { headers: { Authorization: `Bearer ${API_KEY}` } })).status, 404);
    assert.equal((await fetch(`${t.origin}/c/${s.id}`)).status, 404);
  } finally {
    await t.close();
  }
});

test("a proxy that strips the base path is supported by one setting", async () => {
  const t = await start({ PAYTRUE_BASE_PATH: "/paytrue", PAYTRUE_PROXY_STRIPS_BASE_PATH: "true" });
  try {
    const res = await fetch(`${t.origin}/v1/checkout/sessions`, { headers: { Authorization: `Bearer ${API_KEY}` } });
    assert.equal(res.status, 200);
  } finally {
    await t.close();
  }
});

test("split layout: the hosted page and the API have their own origins and paths in the URLs they hand out", async () => {
  const t = await start({ PAYTRUE_CHECKOUT_ORIGIN: "http://127.0.0.1:1", PAYTRUE_CHECKOUT_BASE_PATH: "/", PAYTRUE_BASE_PATH: "/payments" });
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    assert.equal(s.url, `http://127.0.0.1:1/c/${s.id}`);
    assert.equal(t.client.baseUrl, `${t.origin}/payments`);
  } finally {
    await t.close();
  }
});

test("authentication, validation, expiry bounds, idempotency", async () => {
  const t = await start();
  try {
    const noKey = await fetch(`${t.config.api.baseUrl}/v1/checkout/sessions`);
    assert.equal(noKey.status, 401);
    const wrong = new PayTrueClient({ baseUrl: t.config.api.baseUrl, apiKey: "wrong" });
    await assert.rejects(wrong.listCheckoutSessions(), (e) => e instanceof PayTrueApiError && e.status === 401);
    await assert.rejects(t.client.createCheckoutSession(PARAMS({ amount: 1.5 }), { validate: false }), (e) => e.status === 400 && e.code === "validation_failed");
    await assert.rejects(t.client.createCheckoutSession(PARAMS({ expires_in: 5 })), (e) => e.status === 400 && e.code === "invalid_expiry");
    await assert.rejects(t.client.createCheckoutSession(PARAMS({ expires_in: 10 ** 7 })), (e) => e.code === "invalid_expiry");
    const a = await t.client.createCheckoutSession(PARAMS(), { idempotencyKey: "k1" });
    const b = await t.client.createCheckoutSession(PARAMS(), { idempotencyKey: "k1" });
    assert.equal(a.id, b.id);
    assert.equal((await t.client.listCheckoutSessions()).data.length, 1);
    await assert.rejects(t.client.createCheckoutSession(PARAMS({ amount: 5000 }), { idempotencyKey: "k1" }), (e) => e.status === 409 && e.code === "idempotency_conflict");
  } finally {
    await t.close();
  }
});

test("the hosted page: security headers, no wallet data, the stub banner, and one answer for an unknown id", async () => {
  const t = await start({ PAYTRUE_ALLOWED_FRAME_ANCESTORS: "https://shop.example.com", PAYTRUE_COOKIE_SAMESITE: "lax" });
  try {
    const s = await t.client.createCheckoutSession(PARAMS({ payer_policy: "expected_wallet", expected_customer_wallet: "0x" + "ab".repeat(20) }));
    const res = await fetch(s.url);
    const html = await res.text();
    assert.equal(res.status, 200);
    assert.match(res.headers.get("content-security-policy"), /frame-ancestors https:\/\/shop\.example\.com/);
    assert.equal(res.headers.get("referrer-policy"), "no-referrer");
    assert.equal(res.headers.get("x-content-type-options"), "nosniff");
    assert.match(res.headers.get("set-cookie"), /HttpOnly; Path=\/; SameSite=Lax/);
    assert.match(html, /DEVELOPMENT STUB/);
    assert.ok(!html.toLowerCase().includes("ab".repeat(20)), "the expected wallet must never reach the page");
    assert.ok(!html.includes("c_1"), "metadata is merchant-private");
    const unknown = await fetch(`${t.origin}/c/cs_${"z".repeat(27)}`);
    assert.equal(unknown.status, 404);
  } finally {
    await t.close();
  }
});

test("with frame ancestors the page tells exactly those origins its state (experimental embed protocol); without them it carries no script", async () => {
  const withAncestors = await start({ PAYTRUE_ALLOWED_FRAME_ANCESTORS: "https://shop.example.com", PAYTRUE_COOKIE_SAMESITE: "lax" });
  try {
    const s = await withAncestors.client.createCheckoutSession(PARAMS());
    const res = await fetch(s.url);
    const html = await res.text();
    const csp = res.headers.get("content-security-policy");
    const nonce = html.match(/<script nonce="([A-Za-z0-9_-]+)">/)?.[1];
    assert.ok(nonce, "a nonce'd script is present");
    assert.ok(csp.includes(`script-src 'nonce-${nonce}'`), csp);
    assert.ok(!html.includes("postMessage(x,'*')") && !html.includes('postMessage(x,"*")'), "never a wildcard target origin");
    assert.ok(html.includes("https://shop.example.com"));
    const messages = JSON.parse(html.match(/m=(\[.*?\]);o\.forEach/)[1]);
    assert.deepEqual(messages.map((m) => m.type), ["ready", "state"]);
    const { parseEmbedMessage } = await import("../../sdk/src/embed.js");
    for (const m of messages) assert.ok(parseEmbedMessage(m), JSON.stringify(m));
    assert.equal(messages[1].state, "open");
  } finally {
    await withAncestors.close();
  }
  const without = await start();
  try {
    const s = await without.client.createCheckoutSession(PARAMS());
    const res = await fetch(s.url);
    assert.ok(!(await res.text()).includes("<script"));
    assert.ok(!res.headers.get("content-security-policy").includes("script-src"));
  } finally {
    await without.close();
  }
});

test("default frame policy forbids embedding", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    assert.match((await fetch(s.url)).headers.get("content-security-policy"), /frame-ancestors 'none'/);
  } finally {
    await t.close();
  }
});

test("a cross-origin POST to the hosted page is refused", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    const res = await fetch(`${s.url}/simulate`, { method: "POST", headers: { Origin: "https://evil.example", "Content-Type": "application/x-www-form-urlencoded" }, body: "action=pay" });
    assert.equal(res.status, 403);
    assert.equal((await t.client.retrieveCheckoutSession(s.id)).status, "open");
  } finally {
    await t.close();
  }
});

test("a payment: opened, processing, completed arrive signed, in order, and verify; the tracker applies each once", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    assert.equal((await simulate(t, s, "pay")).status, 200);
    assert.equal((await t.client.retrieveCheckoutSession(s.id)).status, "processing");
    assert.equal((await simulate(t, s, "complete")).status, 200);
    const got = events(t);
    assert.deepEqual(got.map((e) => e.type), ["checkout.session.opened", "checkout.session.processing", "checkout.session.completed"]);
    assert.deepEqual(got.map((e) => e.data.session_version), [1, 2, 3]);
    assert.equal(got[2].data.finality_state, "final");
    assert.equal(got[0].data.finality_state, "not_submitted");
    assert.equal(got[1].data.finality_state, "pending");
    assert.match(got[1].data.transaction_hash, /^0x[0-9a-f]{64}$/);
    assert.equal(got[2].data.metadata.cart, "c_1");
    const tracker = createEventTracker();
    assert.deepEqual(got.map((e) => tracker.consider(e).apply), [true, true, true]);
    // at-least-once delivery: a redelivery is a duplicate; a late older event is ignored
    await t.stub.redeliver(got[2].id);
    const again = events(t);
    assert.equal(again.length, 4);
    assert.equal(tracker.consider(again[3]).reason, "duplicate");
  } finally {
    await t.close();
  }
});

test("after a submission the session cannot be cancelled, by the customer or the merchant", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    await simulate(t, s, "pay");
    await assert.rejects(t.client.cancelCheckoutSession(s.id), (e) => e.status === 409 && e.code === "session_already_submitted");
    assert.equal((await simulate(t, s, "cancel")).status, 409);
    assert.equal((await t.client.retrieveCheckoutSession(s.id)).status, "processing");
    const page = await (await fetch(s.url)).text();
    assert.match(page, /can no longer be cancelled/);
    assert.ok(!/>Cancel</.test(page));
  } finally {
    await t.close();
  }
});

test("unknown is never shown as failed, says not to pay again, and resolves only to completed or failed", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    await simulate(t, s, "pay");
    await simulate(t, s, "unknown");
    const page = await (await fetch(s.url)).text();
    assert.match(page, /Do not pay again/);
    assert.ok(!/failed/i.test(page.replace(/Simulate: [^<]*/g, "")), "unknown must not read as failed");
    assert.equal((await simulate(t, s, "expire")).status, 409);
    assert.equal((await simulate(t, s, "cancel")).status, 409);
    await simulate(t, s, "fail");
    const got = events(t);
    assert.deepEqual(got.map((e) => e.type).slice(-3), ["checkout.session.processing", "checkout.session.unknown", "checkout.session.failed"]);
    assert.equal(got.at(-2).data.unknown_reason, "rpc_disagreement");
    assert.equal(got.at(-2).data.finality_state, "unresolved");
    assert.equal(got.at(-1).data.failure_reason, "reverted_on_chain");
    const tracker = createEventTracker();
    const applied = got.map((e) => tracker.consider(e).apply);
    assert.deepEqual(applied, [true, true, true, true]);
    assert.equal(tracker.stateOf(s.id), "failed");
  } finally {
    await t.close();
  }
});

test("before a submission a session expires on the clock and a merchant can cancel; both are final", async () => {
  let t0 = 1_700_000_000_000;
  const t = await start({}, { clock: () => t0 });
  try {
    const a = await t.client.createCheckoutSession(PARAMS({ client_reference_id: "a", expires_in: 600 }));
    const b = await t.client.createCheckoutSession(PARAMS({ client_reference_id: "b" }));
    const cancelled = await t.client.cancelCheckoutSession(b.id);
    assert.equal(cancelled.status, "cancelled");
    assert.equal(cancelled.cancel_reason, "merchant_cancelled");
    t0 += 601_000;
    assert.equal((await t.client.retrieveCheckoutSession(a.id)).status, "expired");
    assert.equal((await simulate(t, a, "pay")).status, 409);
    // the events were signed with the injected clock, so verify them against that clock
    const types = events(t, { now: Math.floor(t0 / 1000), toleranceSeconds: 10_000 }).map((e) => `${e.data.client_reference_id}:${e.type.split(".").pop()}`);
    assert.deepEqual(types, ["a:opened", "b:opened", "b:cancelled", "a:expired"]);
    const page = await (await fetch(a.url)).text();
    assert.match(page, /r=session_expired/);
  } finally {
    await t.close();
  }
});

test("the redirect links use only the documented placeholders and never carry data", async () => {
  const t = await start();
  try {
    const s = await t.client.createCheckoutSession(PARAMS());
    await simulate(t, s, "cancel");
    const page = await (await fetch(s.url)).text();
    assert.ok(page.includes(`https://shop.example/cart?s=${s.id}&amp;r=customer_cancelled`), page);
    assert.ok(!page.includes("4900") || page.includes("minor units"), "no amount in a redirect");
    assert.ok(!/(\?|&amp;)(amount|status|payer|hash)=/.test(page));
  } finally {
    await t.close();
  }
});

test("a delivery older than the tolerance is rejected as a replay and a tampered body is rejected", async () => {
  const t = await start();
  try {
    await t.client.createCheckoutSession(PARAMS());
    const r = t.hook.received[0];
    const future = Math.floor(Date.now() / 1000) + 3600;
    assert.throws(() => verifyWebhook({ payload: r.body, header: r.header, secret: SECRET, now: future }), (e) => e.reason === "timestamp_outside_tolerance");
    assert.throws(() => verifyWebhook({ payload: r.body.replace("order-1", "order-2"), header: r.header, secret: SECRET }), (e) => e.reason === "signature_mismatch");
  } finally {
    await t.close();
  }
});
