// SPDX-License-Identifier: Apache-2.0
// The PayTrue DEVELOPMENT STUB. It implements a small part of the proposed checkout API in memory so that examples, SDK tests and reverse-proxy layouts
// can run on a laptop. It is NOT a payment server: it has no wallet, no chain access, no persistence, no real security, and it refuses to start in
// production. Every page and every event says so.
import { createServer } from "node:http";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { checkoutSessionUrl, cookieAttributes, routeOf } from "../../config/src/index.js";
import { validateCreateSessionParams } from "../../sdk/src/client.js";
import { SIGNATURE_HEADER, signWebhook } from "../../sdk/src/webhooks.js";

const BASE32 = "abcdefghijklmnopqrstuvwxyz234567";
const newSessionId = () => {
  const bytes = randomBytes(17); // 136 random bits
  let bits = "";
  for (const b of bytes) bits += b.toString(2).padStart(8, "0");
  let out = "";
  for (let i = 0; i + 5 <= bits.length; i += 5) out += BASE32[parseInt(bits.slice(i, i + 5), 2)];
  return "cs_" + out; // 27 base32 characters = 135 bits from a CSPRNG, at least the 128 the specification asks for
};
const newEventId = () => "evt_" + randomBytes(12).toString("hex");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const same = (a, b) => {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && timingSafeEqual(x, y);
};
const BEFORE_SUBMISSION = new Set(["open"]);
const SUBMITTED = new Set(["processing", "unknown"]);
const FINAL = new Set(["completed", "failed", "expired", "cancelled"]);

/**
 * @param {{ config: import("../../config/src/index.js").PayTrueConfig, apiKey: string, webhookUrl?: string, webhookSecret?: string,
 *           now?: () => number, fetchImpl?: typeof fetch }} options
 */
export function createDevServer({ config, apiKey, webhookUrl, webhookSecret, now = () => Date.now(), fetchImpl = globalThis.fetch }) {
  if (config.production) throw new Error("the PayTrue development stub never runs in production");
  if (!apiKey) throw new Error("apiKey is required");
  const sessions = new Map();
  const idem = new Map();
  const deliveries = [];

  const iso = (ms) => new Date(ms).toISOString();
  const merchantView = (s) => ({
    id: s.id, url: s.url, status: s.status, created_at: iso(s.created), expires_at: iso(s.expires), mode: s.mode, amount: s.amount, currency: s.currency,
    client_reference_id: s.client_reference_id, payer_policy: s.payer_policy, live_mode: false, session_version: s.version, metadata: s.metadata,
    cancel_reason: s.cancel_reason, failure_code: s.failure_code, unknown_reason: s.unknown_reason, dev_stub: true,
  });

  async function emit(s, type, extra = {}) {
    const event = {
      id: newEventId(), type: `checkout.session.${type}`, api_version: "2026-10-17", created: iso(now()), live_mode: false, merchant_id: "mer_devstub",
      data: {
        session_id: s.id, client_reference_id: s.client_reference_id, mode: s.mode, state: s.status, session_version: s.version, payment_id: null, mandate_id: null,
        failure_reason: s.failure_code, unknown_reason: s.unknown_reason, cancel_reason: s.cancel_reason, chain_id: s.chain_id, transaction_hash: s.tx_hash,
        finality_state: s.finality, payer: null, initial_charge_settled: null, metadata: s.metadata, dev_stub: true, ...extra,
      },
    };
    await deliver(event);
    return event;
  }

  async function deliver(event) {
    const body = JSON.stringify(event);
    const record = { event, body, status: undefined };
    deliveries.push(record);
    if (!webhookUrl) return record;
    const header = signWebhook({ payload: body, secret: webhookSecret ?? "dev-secret", timestamp: Math.floor(now() / 1000) });
    try {
      const res = await fetchImpl(webhookUrl, { method: "POST", headers: { "Content-Type": "application/json", [SIGNATURE_HEADER]: header }, body, signal: AbortSignal.timeout(5000) });
      record.status = res.status;
    } catch (e) {
      record.status = `error: ${e.message}`;
    }
    return record;
  }

  async function transition(s, status, patch = {}, eventType = status) {
    s.status = status;
    s.version += 1;
    Object.assign(s, patch);
    return emit(s, eventType);
  }

  async function refresh(s) {
    if (s.status === "open" && now() >= s.expires) await transition(s, "expired", { finality: "not_submitted" });
    return s;
  }

  const cancelUrlOf = (s, reason) => s.cancel_url.replaceAll("{CHECKOUT_SESSION_ID}", s.id).replaceAll("{CANCEL_REASON}", reason);
  const successUrlOf = (s) => s.success_url.replaceAll("{CHECKOUT_SESSION_ID}", s.id);

  // ------------------------------------------------------------------ HTTP helpers
  const send = (res, status, body, headers = {}) => {
    const isJson = typeof body !== "string";
    res.writeHead(status, { "Content-Type": isJson ? "application/json" : "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", ...headers });
    res.end(isJson ? JSON.stringify(body) : body);
  };
  const apiError = (res, status, code, message, param) => send(res, status, { error: { type: status >= 500 ? "api_error" : "invalid_request", code, message, ...(param ? { param } : {}) } });
  const readBody = (req) => new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > 65536) {
        reject(Object.assign(new Error("body too large"), { code: "body_too_large" }));
        req.destroy();
      } else chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });

  function page(s, note, nonce) {
    const banner = "DEVELOPMENT STUB: no wallet, no chain, no money. Not a payment page.";
    const submitted = SUBMITTED.has(s.status);
    const actionsFor = {
      open: [["pay", "Simulate: customer pays (processing)"], ["cancel", "Cancel"], ["expire", "Simulate: session expires"]],
      processing: [["complete", "Simulate: payment is final (completed)"], ["unknown", "Simulate: outcome unknown"], ["fail", "Simulate: payment failed (final revert)"]],
      unknown: [["complete", "Simulate: reconciled as completed"], ["fail", "Simulate: reconciled as failed"]],
    }[s.status] ?? [];
    const forms = actionsFor.map(([a, label]) => `<form method="post" action="${esc(config.checkout.baseUrl + config.checkout.route + "/" + s.id + "/simulate")}"><input type="hidden" name="action" value="${a}"><button>${esc(label)}</button></form>`).join("");
    let message = "";
    if (s.status === "unknown") message = "<p><strong>We are confirming your payment. Do not pay again.</strong></p>";
    if (submitted) message += "<p>A transaction was submitted. This session can no longer be cancelled.</p>";
    let exit = "";
    if (s.status === "completed" || submitted) exit = `<p><a href="${esc(successUrlOf(s))}">Return to the merchant</a></p>`;
    else if (FINAL.has(s.status)) exit = `<p><a href="${esc(cancelUrlOf(s, s.status === "expired" ? "session_expired" : "customer_cancelled"))}">Back to the merchant</a></p>`;
    return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PayTrue development stub</title></head><body>
<p><strong>${esc(banner)}</strong></p>
<h1>${esc(s.display.merchant_name)}</h1><p>${esc(s.display.description)}</p>
<p>${esc((s.amount / 100).toFixed(2))} ${esc(s.currency)} (minor units: ${esc(s.amount)})</p>
<p>Status: <code>${esc(s.status)}</code>${note ? " — " + esc(note) : ""}</p>${message}${forms}${exit}${embedScript(s, nonce)}</body></html>`;
  }

  // EXPERIMENTAL embed protocol (packages/sdk/src/embed.js): only when some origin may frame the page, tell exactly those origins the state of the session.
  const embedScript = (s, nonce) => {
    if (!nonce || config.frameAncestors.length === 0) return "";
    const safe = (v) => JSON.stringify(v).replace(/</g, "\\u003c");
    const messages = [{ source: "paytrue-checkout", version: 1, type: "ready", sessionId: s.id }, { source: "paytrue-checkout", version: 1, type: "state", sessionId: s.id, state: s.status }];
    return `<script nonce="${nonce}">(function(){if(window.parent===window)return;var o=${safe(config.frameAncestors)},m=${safe(messages)};o.forEach(function(t){m.forEach(function(x){window.parent.postMessage(x,t);});});})();</script>`;
  };

  const frameHeaders = (nonce) => ({
    "Content-Security-Policy": `default-src 'none'; style-src 'unsafe-inline'; ${nonce && config.frameAncestors.length ? `script-src 'nonce-${nonce}'; ` : ""}form-action 'self'; base-uri 'none'; frame-ancestors ${config.cspFrameAncestors}`,
    "Referrer-Policy": "no-referrer",
    "Set-Cookie": `paytrue_dev_ctl=1; ${cookieAttributes(config, { maxAgeSeconds: 600 })}`,
  });

  const checkoutOriginOk = (req) => {
    const origin = req.headers.origin;
    return origin === undefined || origin === config.checkout.origin;
  };

  async function handle(req, res) {
    const url = new URL(req.url, "http://stub");
    const apiRoute = routeOf(config, url.pathname, "api");
    const pageRoute = routeOf(config, url.pathname, "checkout");

    // ---- merchant API
    if (apiRoute && /^\/v1\//.test(apiRoute)) {
      const auth = req.headers.authorization ?? "";
      if (!auth.startsWith("Bearer ") || !same(auth.slice(7), apiKey)) return apiError(res, 401, "unauthorized", "missing or invalid API key");
      const parts = apiRoute.split("/").filter(Boolean); // v1, checkout, sessions, [id], [cancel]
      if (parts[1] !== "checkout" || parts[2] !== "sessions") return apiError(res, 404, "not_found", "unknown route");

      if (req.method === "POST" && parts.length === 3) {
        const key = req.headers["idempotency-key"];
        if (!key) return apiError(res, 400, "idempotency_key_required", "the Idempotency-Key header is required");
        let raw;
        try {
          raw = await readBody(req);
        } catch {
          return apiError(res, 413, "body_too_large", "the body is larger than 64 KiB");
        }
        const bodyHash = createHash("sha256").update(raw).digest("hex");
        const prior = idem.get(key);
        if (prior) return prior.bodyHash === bodyHash ? send(res, 201, prior.response) : apiError(res, 409, "idempotency_conflict", "this idempotency key was used with a different request");
        let params;
        try {
          params = JSON.parse(raw);
        } catch {
          return apiError(res, 400, "invalid_json", "the body is not JSON");
        }
        const problems = validateCreateSessionParams(params);
        if (problems.length) return apiError(res, 400, "validation_failed", problems.join("; "));
        const lifetime = params.expires_in ?? config.session.defaultSeconds;
        if (lifetime < config.session.minSeconds || lifetime > config.session.maxSeconds) {
          return apiError(res, 400, "invalid_expiry", `expires_in must be between ${config.session.minSeconds} and ${config.session.maxSeconds} seconds`, "expires_in");
        }
        const id = newSessionId();
        const created = now();
        const s = {
          id, url: checkoutSessionUrl(config, id), status: "open", version: 1, created, expires: created + lifetime * 1000, mode: params.mode, amount: params.amount, currency: params.currency,
          client_reference_id: params.client_reference_id, payer_policy: params.payer_policy, metadata: params.metadata ?? {}, display: params.display, success_url: params.success_url,
          cancel_url: params.cancel_url, cancel_reason: null, failure_code: null, unknown_reason: null, chain_id: null, tx_hash: null, finality: "not_submitted",
        };
        sessions.set(id, s);
        const response = merchantView(s);
        idem.set(key, { bodyHash, response });
        await emit(s, "opened");
        return send(res, 201, response);
      }
      if (req.method === "GET" && parts.length === 3) {
        for (const s of sessions.values()) await refresh(s);
        let rows = [...sessions.values()];
        const q = url.searchParams;
        if (q.get("client_reference_id")) rows = rows.filter((s) => s.client_reference_id === q.get("client_reference_id"));
        if (q.get("status")) rows = rows.filter((s) => s.status === q.get("status"));
        return send(res, 200, { data: rows.map(merchantView), has_more: false });
      }
      const s = sessions.get(parts[3]);
      if (!s) return apiError(res, 404, "session_not_found", "no such session");
      await refresh(s);
      if (req.method === "GET" && parts.length === 4) return send(res, 200, merchantView(s));
      if (req.method === "POST" && parts.length === 5 && parts[4] === "cancel") {
        if (!req.headers["idempotency-key"]) return apiError(res, 400, "idempotency_key_required", "the Idempotency-Key header is required");
        if (SUBMITTED.has(s.status) || FINAL.has(s.status) && s.status !== "cancelled") return apiError(res, 409, "session_already_submitted", "a transaction was submitted or the session is final");
        if (s.status !== "cancelled") await transition(s, "cancelled", { cancel_reason: "merchant_cancelled" });
        return send(res, 200, merchantView(s));
      }
      return apiError(res, 404, "not_found", "unknown route");
    }

    // ---- hosted page
    if (pageRoute && pageRoute.startsWith(config.checkout.route + "/")) {
      const parts = pageRoute.slice(config.checkout.route.length + 1).split("/");
      const s = sessions.get(parts[0]);
      if (!s) return send(res, 404, "<!doctype html><title>Not found</title><p>This checkout does not exist or has expired.</p>", frameHeaders());
      await refresh(s);
      if (req.method === "GET" && parts.length === 1) { const nonce = randomBytes(16).toString("base64url"); return send(res, 200, page(s, undefined, nonce), frameHeaders(nonce)); }
      if (req.method === "POST" && parts.length === 2 && parts[1] === "simulate") {
        if (!checkoutOriginOk(req)) return send(res, 403, "<!doctype html><title>Forbidden</title><p>Cross-origin request refused.</p>", frameHeaders());
        const form = new URLSearchParams(await readBody(req));
        const action = form.get("action");
        let note = "";
        if (action === "pay" && s.status === "open") await transition(s, "processing", { chain_id: config.chains[0].id, tx_hash: "0x" + randomBytes(32).toString("hex"), finality: "pending" });
        else if (action === "complete" && SUBMITTED.has(s.status)) await transition(s, "completed", { unknown_reason: null, finality: "final" });
        else if (action === "fail" && SUBMITTED.has(s.status)) await transition(s, "failed", { unknown_reason: null, failure_code: "reverted_on_chain", finality: "final" });
        else if (action === "unknown" && s.status === "processing") await transition(s, "unknown", { unknown_reason: "rpc_disagreement", finality: "unresolved" });
        else if (action === "cancel" && BEFORE_SUBMISSION.has(s.status)) await transition(s, "cancelled", { cancel_reason: "customer_cancelled" });
        else if (action === "expire" && s.status === "open") await transition(s, "expired", { finality: "not_submitted" });
        else note = `"${action}" is not possible from ${s.status}`;
        const nonce = randomBytes(16).toString("base64url"); return send(res, note ? 409 : 200, page(s, note, nonce), frameHeaders(nonce));
      }
    }
    return apiError(res, 404, "not_found", "unknown route");
  }

  const server = createServer((req, res) => {
    handle(req, res).catch((e) => {
      if (!res.headersSent) apiError(res, 500, "internal_error", e.message);
      else res.end();
    });
  });

  return {
    server,
    sessions,
    deliveries,
    /** Deliver an event again with a fresh timestamp: at-least-once delivery means a receiver must deduplicate. */
    redeliver: (eventId) => {
      const rec = deliveries.find((d) => d.event.id === eventId);
      if (!rec) throw new Error("no such event");
      return deliver(rec.event);
    },
    listen: (port = 0, host = "127.0.0.1") => new Promise((resolve) => server.listen(port, host, () => resolve(server.address()))),
    close: () => new Promise((resolve) => {
      server.closeAllConnections?.();
      server.close(resolve);
    }),
  };
}
