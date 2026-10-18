// SPDX-License-Identifier: Apache-2.0
// Webhook signing, verification and ordering for PayTrue events. Server side (uses node:crypto). No dependencies.
//
// The scheme is the one of the proposed event catalog (README, section Use the packages): header `t=<unix seconds>,v1=<hex>[,v1=<hex>]`, where v1 is the HMAC-SHA-256,
// under the endpoint's secret, of `<t>.<raw body>`. Several v1 values are accepted so that a secret can be rotated with an overlap.
import { createHmac, timingSafeEqual } from "node:crypto";

/** The header names this SDK reads and writes. `FastPay-Signature` is the name of the unfrozen proposal and is accepted for reading. */
export const SIGNATURE_HEADER = "PayTrue-Signature";
export const LEGACY_SIGNATURE_HEADER = "FastPay-Signature";

export class WebhookVerificationError extends Error {
  /** @param {string} reason a stable code: missing_header, malformed_header, timestamp_outside_tolerance, signature_mismatch, invalid_json */
  constructor(reason, message) {
    super(message ?? reason);
    this.name = "WebhookVerificationError";
    this.reason = reason;
  }
}

const hmac = (secret, timestamp, body) => createHmac("sha256", secret).update(`${timestamp}.`).update(body).digest("hex");

/**
 * @param {{ payload: string | Uint8Array, secret: string | string[], timestamp?: number }} args
 * @returns {string} the header value
 */
export function signWebhook({ payload, secret, timestamp = Math.floor(Date.now() / 1000) }) {
  const secrets = Array.isArray(secret) ? secret : [secret];
  const body = typeof payload === "string" ? Buffer.from(payload, "utf8") : Buffer.from(payload);
  return `t=${timestamp},` + secrets.map((s) => `v1=${hmac(s, timestamp, body)}`).join(",");
}

/** Read the signature header from a Node `IncomingHttpHeaders`-like or `Headers`-like object. */
export function signatureHeaderOf(headers) {
  const get = (name) => (typeof headers.get === "function" ? headers.get(name) : headers[name.toLowerCase()] ?? headers[name]);
  return get(SIGNATURE_HEADER) ?? get(LEGACY_SIGNATURE_HEADER) ?? undefined;
}

/**
 * Verify a webhook delivery on its RAW body and return the parsed event.
 * @param {{ payload: string | Uint8Array, header: string | undefined, secret: string | string[], toleranceSeconds?: number, now?: number }} args
 * @returns {any}
 */
export function verifyWebhook({ payload, header, secret, toleranceSeconds = 300, now = Math.floor(Date.now() / 1000) }) {
  if (!header) throw new WebhookVerificationError("missing_header", "no signature header");
  let timestamp;
  const signatures = [];
  for (const part of String(header).split(",")) {
    const eq = part.indexOf("=");
    if (eq < 0) throw new WebhookVerificationError("malformed_header");
    const key = part.slice(0, eq).trim();
    const value = part.slice(eq + 1).trim();
    if (key === "t") {
      if (!/^\d+$/.test(value)) throw new WebhookVerificationError("malformed_header", "timestamp is not an integer");
      timestamp = Number(value);
    } else if (key === "v1") {
      if (!/^[0-9a-f]{64}$/i.test(value)) throw new WebhookVerificationError("malformed_header", "a v1 signature is not 64 hex characters");
      signatures.push(value.toLowerCase());
    }
  }
  if (timestamp === undefined || signatures.length === 0) throw new WebhookVerificationError("malformed_header", "t and v1 are required");
  if (Math.abs(now - timestamp) > toleranceSeconds) throw new WebhookVerificationError("timestamp_outside_tolerance", "the timestamp is outside the replay window");
  const body = typeof payload === "string" ? Buffer.from(payload, "utf8") : Buffer.from(payload);
  const secrets = Array.isArray(secret) ? secret : [secret];
  const ok = secrets.some((s) => {
    const expected = Buffer.from(hmac(s, timestamp, body), "hex");
    return signatures.some((sig) => {
      const got = Buffer.from(sig, "hex");
      return got.length === expected.length && timingSafeEqual(got, expected);
    });
  });
  if (!ok) throw new WebhookVerificationError("signature_mismatch", "no signature matches");
  try {
    return JSON.parse(body.toString("utf8"));
  } catch {
    throw new WebhookVerificationError("invalid_json", "the body is not JSON");
  }
}

const FINAL_STATES = new Set(["completed", "failed", "expired", "cancelled"]);

/**
 * Deduplication and ordering of events for ONE receiver (in memory; keep the same rules in a database in production).
 * Rules of the event catalog: deduplicate by event id; apply an event only if its session_version is higher than the last applied for the session;
 * completed, failed, expired and cancelled are final; unknown can still be followed by completed or failed.
 */
export function createEventTracker() {
  const seen = new Set();
  const sessions = new Map();
  return {
    /**
     * @param {{ id: string, data: { session_id: string, session_version: number, state: string } }} event
     * @returns {{ apply: boolean, reason: "new" | "duplicate" | "stale" | "after_final" }}
     */
    consider(event) {
      if (seen.has(event.id)) return { apply: false, reason: "duplicate" };
      seen.add(event.id);
      const { session_id: sessionId, session_version: version, state } = event.data;
      const last = sessions.get(sessionId);
      if (last) {
        if (FINAL_STATES.has(last.state)) return { apply: false, reason: "after_final" };
        if (version <= last.version) return { apply: false, reason: "stale" };
      }
      sessions.set(sessionId, { version, state });
      return { apply: true, reason: "new" };
    },
    stateOf: (sessionId) => sessions.get(sessionId)?.state,
  };
}
