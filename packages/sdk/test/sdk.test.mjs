// SPDX-License-Identifier: Apache-2.0
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  PayTrueApiError, PayTrueClient, PayTrueValidationError, WebhookVerificationError, createEventTracker, signWebhook, signatureHeaderOf, validateCreateSessionParams, verifyWebhook,
} from "../src/index.js";
import { FRAME_ATTRIBUTES, acceptEmbedMessage, buildFrameUrl, parseEmbedMessage } from "../src/embed.js";

const SESSION = "cs_abcdefghijklmnopqrstuvwxyz";
const GOOD = {
  mode: "payment",
  amount: 4900,
  currency: "EUR",
  client_reference_id: "order-10432",
  success_url: "https://shop.example/done?session={CHECKOUT_SESSION_ID}",
  cancel_url: "https://shop.example/cart?session={CHECKOUT_SESSION_ID}&reason={CANCEL_REASON}",
  payer_policy: "any_wallet",
  display: { merchant_name: "Example Shop", description: "Order 10432" },
};
const bodyOf = (o) => JSON.stringify(o);
const event = (id, version, state, session = SESSION) => ({ id, type: `checkout.session.${state}`, data: { session_id: session, session_version: version, state } });

// ------------------------------------------------------------------ webhooks
test("a signed webhook verifies and returns the parsed event", () => {
  const payload = bodyOf({ id: "evt_1", type: "checkout.session.completed" });
  const header = signWebhook({ payload, secret: "s3cret", timestamp: 1_000_000 });
  assert.match(header, /^t=1000000,v1=[0-9a-f]{64}$/);
  const ev = verifyWebhook({ payload, header, secret: "s3cret", now: 1_000_100 });
  assert.equal(ev.id, "evt_1");
});

test("every way of failing verification has a stable reason", () => {
  const payload = bodyOf({ id: "evt_1" });
  const header = signWebhook({ payload, secret: "s3cret", timestamp: 1_000_000 });
  const reason = (args) => {
    try {
      verifyWebhook({ now: 1_000_000, ...args });
      return "verified";
    } catch (e) {
      assert.ok(e instanceof WebhookVerificationError);
      return e.reason;
    }
  };
  assert.equal(reason({ payload, header: undefined, secret: "s3cret" }), "missing_header");
  assert.equal(reason({ payload, header: "garbage", secret: "s3cret" }), "malformed_header");
  assert.equal(reason({ payload, header: "t=abc,v1=" + "0".repeat(64), secret: "s3cret" }), "malformed_header");
  assert.equal(reason({ payload, header: "t=1000000,v1=zz", secret: "s3cret" }), "malformed_header");
  assert.equal(reason({ payload, header: "v1=" + "0".repeat(64), secret: "s3cret" }), "malformed_header");
  assert.equal(reason({ payload, header, secret: "s3cret", now: 1_000_000 + 301 }), "timestamp_outside_tolerance");
  assert.equal(reason({ payload, header, secret: "s3cret", now: 1_000_000 - 301 }), "timestamp_outside_tolerance");
  assert.equal(reason({ payload, header, secret: "s3cret", now: 1_000_000 + 300 }), "verified");
  assert.equal(reason({ payload, header, secret: "other" }), "signature_mismatch");
  assert.equal(reason({ payload: payload + " ", header, secret: "s3cret" }), "signature_mismatch");
  const notJson = "not json";
  assert.equal(reason({ payload: notJson, header: signWebhook({ payload: notJson, secret: "s3cret", timestamp: 1_000_000 }), secret: "s3cret" }), "invalid_json");
});

test("a rotated secret verifies during the overlap: any listed secret and any v1 signature may match", () => {
  const payload = bodyOf({ id: "evt_2" });
  const rotating = signWebhook({ payload, secret: ["old-secret", "new-secret"], timestamp: 1_000_000 });
  assert.equal((rotating.match(/v1=/g) ?? []).length, 2);
  assert.doesNotThrow(() => verifyWebhook({ payload, header: rotating, secret: "new-secret", now: 1_000_000 }));
  assert.doesNotThrow(() => verifyWebhook({ payload, header: rotating, secret: "old-secret", now: 1_000_000 }));
  const oldOnly = signWebhook({ payload, secret: "old-secret", timestamp: 1_000_000 });
  assert.doesNotThrow(() => verifyWebhook({ payload, header: oldOnly, secret: ["new-secret", "old-secret"], now: 1_000_000 }));
  assert.throws(() => verifyWebhook({ payload, header: oldOnly, secret: "new-secret", now: 1_000_000 }), WebhookVerificationError);
});

test("the body is verified byte for byte, so Buffers and strings agree", () => {
  const payload = bodyOf({ id: "evt_3", note: "é€" });
  const header = signWebhook({ payload, secret: "s", timestamp: 5 });
  assert.equal(verifyWebhook({ payload: Buffer.from(payload, "utf8"), header, secret: "s", now: 5 }).id, "evt_3");
});

test("both the PayTrue and the proposal's FastPay header names are read", () => {
  assert.equal(signatureHeaderOf({ "paytrue-signature": "a" }), "a");
  assert.equal(signatureHeaderOf({ "fastpay-signature": "b" }), "b");
  assert.equal(signatureHeaderOf(new Headers({ "PayTrue-Signature": "c" })), "c");
  assert.equal(signatureHeaderOf({}), undefined);
});

test("the event tracker deduplicates, orders by session_version and respects final states", () => {
  const t = createEventTracker();
  assert.deepEqual(t.consider(event("e1", 1, "opened")), { apply: true, reason: "new" });
  assert.deepEqual(t.consider(event("e1", 1, "opened")), { apply: false, reason: "duplicate" });
  assert.deepEqual(t.consider(event("e3", 5, "processing")), { apply: true, reason: "new" });
  assert.deepEqual(t.consider(event("e2", 3, "opened")), { apply: false, reason: "stale" });
  assert.deepEqual(t.consider(event("e4", 6, "unknown")), { apply: true, reason: "new" });
  assert.deepEqual(t.consider(event("e5", 7, "completed")), { apply: true, reason: "new" });
  assert.equal(t.stateOf(SESSION), "completed");
  assert.deepEqual(t.consider(event("e6", 8, "failed")), { apply: false, reason: "after_final" });
  assert.deepEqual(t.consider(event("e7", 4, "processing")), { apply: false, reason: "after_final" });
  assert.deepEqual(t.consider(event("e8", 1, "opened", "cs_other0123456789abcdef")), { apply: true, reason: "new" });
});

// ------------------------------------------------------------------ validation
test("valid parameters pass and each rule of the catalog is enforced", () => {
  assert.deepEqual(validateCreateSessionParams(GOOD), []);
  const bad = (patch) => validateCreateSessionParams({ ...GOOD, ...patch }).join("|");
  assert.match(bad({ mode: "setup" }), /mode/);
  assert.match(bad({ amount: 49.5 }), /integer/);
  assert.match(bad({ amount: 0 }), /at least 1/);
  assert.match(bad({ mode: "subscription", amount: 100, mandate_terms: {} }), /not available yet/);
  assert.match(bad({ mode: "subscription" }), /mandate_terms/);
  assert.match(bad({ currency: "eur" }), /currency/);
  assert.match(bad({ client_reference_id: "" }), /client_reference_id/);
  assert.match(bad({ success_url: "http://shop.example/x" }), /https/);
  assert.match(bad({ success_url: "https://u:p@shop.example/x" }), /credentials/);
  assert.match(bad({ success_url: "https://shop.example/x#frag" }), /fragment/);
  assert.match(bad({ success_url: "https://192.0.2.1/x" }), /IP literal/);
  assert.match(bad({ success_url: "https://shop.example/{ORDER}" }), /unknown placeholder/);
  assert.match(bad({ success_url: "https://shop.example/{CANCEL_REASON}" }), /success_url must not use/);
  assert.equal(bad({ success_url: "http://localhost:3000/ok" }), "");
  assert.match(bad({ payer_policy: "anyone" }), /payer_policy/);
  assert.match(bad({ payer_policy: "expected_wallet" }), /expected_customer_wallet/);
  assert.match(bad({ expected_customer_wallet: "0x" + "1".repeat(40) }), /absent/);
  assert.equal(bad({ payer_policy: "expected_wallet", expected_customer_wallet: "0x" + "1".repeat(40) }), "");
  assert.match(bad({ expires_in: 0 }), /expires_in/);
  assert.match(bad({ allowed_chains: [] }), /allowed_chains/);
  assert.match(bad({ allowed_tokens: [{ chain_id: 1, address: "x" }] }), /allowed_tokens/);
  assert.match(bad({ metadata: { a: 1 } }), /must be a string/);
  assert.match(bad({ metadata: Object.fromEntries(Array.from({ length: 21 }, (_, i) => [`k${i}`, "v"])) }), /more than 20 keys/);
  assert.match(bad({ metadata: { k: "x".repeat(501) } }), /500 bytes/);
  assert.match(bad({ metadata: { ["k".repeat(41)]: "v" } }), /40 bytes/);
  assert.match(bad({ display: { merchant_name: "x" } }), /display/);
});

// ------------------------------------------------------------------ client
function recordingFetch(respond) {
  const calls = [];
  const f = async (url, init) => {
    calls.push({ url: String(url), init });
    const { status = 200, json } = respond(String(url), init, calls.length);
    return new Response(JSON.stringify(json), { status, headers: { "content-type": "application/json" } });
  };
  return { f, calls };
}

test("the client requires an explicit base URL and key: there is no default host", () => {
  assert.throws(() => new PayTrueClient({ apiKey: "k" }), /no default host/);
  assert.throws(() => new PayTrueClient({ baseUrl: "https://pay.example.com" }), /apiKey/);
  assert.throws(() => new PayTrueClient({ baseUrl: "not a url", apiKey: "k" }), /not a URL/);
  assert.throws(() => new PayTrueClient({ baseUrl: "https://pay.example.com?x=1", apiKey: "k" }), /query/);
});

test("createCheckoutSession posts to <base>/v1/checkout/sessions with the key, the version and an idempotency key", async () => {
  const { f, calls } = recordingFetch(() => ({ status: 201, json: { id: SESSION, url: "https://pay.example.com/paytrue/c/" + SESSION, status: "open" } }));
  const client = new PayTrueClient({ baseUrl: "https://pay.example.com/paytrue/", apiKey: "key_1", fetch: f });
  const s = await client.createCheckoutSession(GOOD, { idempotencyKey: "idem-1" });
  assert.equal(s.id, SESSION);
  const { url, init } = calls[0];
  assert.equal(url, "https://pay.example.com/paytrue/v1/checkout/sessions");
  assert.equal(init.method, "POST");
  assert.equal(init.headers.Authorization, "Bearer key_1");
  assert.equal(init.headers["Idempotency-Key"], "idem-1");
  assert.match(init.headers["PayTrue-Version"], /^\d{4}-\d\d-\d\d$/);
  assert.deepEqual(JSON.parse(init.body), GOOD);
});

test("a random idempotency key is generated when none is given, and invalid parameters never leave the process", async () => {
  const { f, calls } = recordingFetch(() => ({ status: 201, json: { id: SESSION } }));
  const client = new PayTrueClient({ baseUrl: "https://pay.example.com", apiKey: "k", fetch: f });
  await client.createCheckoutSession(GOOD);
  await client.createCheckoutSession(GOOD);
  assert.notEqual(calls[0].init.headers["Idempotency-Key"], calls[1].init.headers["Idempotency-Key"]);
  await assert.rejects(client.createCheckoutSession({ ...GOOD, amount: 1.5 }), PayTrueValidationError);
  assert.equal(calls.length, 2);
  await client.createCheckoutSession({ ...GOOD, amount: 1.5 }, { validate: false });
  assert.equal(calls.length, 3);
});

test("retrieve, list and cancel use the documented paths and an API error becomes a PayTrueApiError", async () => {
  const { f, calls } = recordingFetch((url) => (url.endsWith("/cancel")
    ? { status: 409, json: { error: { type: "invalid_request", code: "session_already_submitted", message: "too late" } } }
    : { json: { id: SESSION, data: [] } }));
  const client = new PayTrueClient({ baseUrl: "https://pay.example.com", apiKey: "k", fetch: f });
  await client.retrieveCheckoutSession(SESSION);
  await client.listCheckoutSessions({ client_reference_id: "order-1", status: "open", limit: 5 });
  assert.equal(calls[0].url, `https://pay.example.com/v1/checkout/sessions/${SESSION}`);
  assert.equal(calls[1].url, "https://pay.example.com/v1/checkout/sessions?client_reference_id=order-1&status=open&limit=5");
  await assert.rejects(client.cancelCheckoutSession(SESSION), (e) => e instanceof PayTrueApiError && e.status === 409 && e.code === "session_already_submitted");
  assert.equal(calls[2].url, `https://pay.example.com/v1/checkout/sessions/${SESSION}/cancel`);
});

test("a session id is encoded in the path", async () => {
  const { f, calls } = recordingFetch(() => ({ json: {} }));
  const client = new PayTrueClient({ baseUrl: "https://pay.example.com", apiKey: "k", fetch: f });
  await client.retrieveCheckoutSession("../x?y");
  assert.equal(calls[0].url, "https://pay.example.com/v1/checkout/sessions/..%2Fx%3Fy");
});

// ------------------------------------------------------------------ embed helpers
test("buildFrameUrl keeps the base path and refuses odd input", () => {
  assert.equal(buildFrameUrl({ checkoutBaseUrl: "https://checkout.example.com", sessionId: SESSION }), `https://checkout.example.com/c/${SESSION}`);
  assert.equal(buildFrameUrl({ checkoutBaseUrl: "https://shop.example.com/paytrue/", sessionId: SESSION }), `https://shop.example.com/paytrue/c/${SESSION}`);
  assert.throws(() => buildFrameUrl({ checkoutBaseUrl: "https://shop.example.com", sessionId: "x" }));
  assert.throws(() => buildFrameUrl({ checkoutBaseUrl: "https://shop.example.com?a=1", sessionId: SESSION }));
});

test("an embed message is believed only from the exact origin, from our frame, with an exact shape", () => {
  const frame = {};
  const ok = { source: "paytrue-checkout", version: 1, type: "state", sessionId: SESSION, state: "processing" };
  const accept = (event, expected = {}) => acceptEmbedMessage(event, { checkoutOrigin: "https://checkout.example.com", frameWindow: frame, sessionId: SESSION, ...expected });
  assert.deepEqual(accept({ origin: "https://checkout.example.com", source: frame, data: ok }), { type: "state", sessionId: SESSION, state: "processing" });
  assert.equal(accept({ origin: "https://evil.example", source: frame, data: ok }), null);
  assert.equal(accept({ origin: "https://checkout.example.com.evil.example", source: frame, data: ok }), null);
  assert.equal(accept({ origin: "https://checkout.example.com", source: {}, data: ok }), null);
  assert.equal(accept({ origin: "https://checkout.example.com", source: frame, data: ok }, { sessionId: "cs_zzzzzzzzzzzzzzzzzzzzzzzz" }), null);
  assert.equal(accept({ origin: "https://checkout.example.com", source: frame, data: ok }, { frameWindow: undefined }), null);
  assert.equal(parseEmbedMessage({ ...ok, state: "paid" }), null);
  assert.equal(parseEmbedMessage({ ...ok, extra: 1 }), null);
  assert.equal(parseEmbedMessage({ ...ok, version: 2 }), null);
  assert.equal(parseEmbedMessage({ ...ok, source: "other" }), null);
  assert.equal(parseEmbedMessage({ source: "paytrue-checkout", version: 1, type: "resize", sessionId: SESSION, height: 480.4 }).height, 480);
  assert.equal(parseEmbedMessage({ source: "paytrue-checkout", version: 1, type: "resize", sessionId: SESSION, height: -1 }), null);
  assert.equal(parseEmbedMessage({ source: "paytrue-checkout", version: 1, type: "navigate", sessionId: SESSION }), null);
  assert.equal(parseEmbedMessage("text"), null);
  assert.equal(parseEmbedMessage(null), null);
  assert.equal(FRAME_ATTRIBUTES.referrerpolicy, "no-referrer");
});

test("the SDK source names no PayTrue-hosted service and declares no dependency", () => {
  for (const f of ["client.js", "webhooks.js", "embed.js", "index.js"]) {
    assert.ok(!/paytrue\.(me|com|io|app|dev|cloud)/i.test(readFileSync(new URL(`../src/${f}`, import.meta.url), "utf8")), f);
  }
  const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
  assert.equal(pkg.dependencies, undefined);
  assert.equal(pkg.devDependencies, undefined);
});
