// SPDX-License-Identifier: Apache-2.0
// EXPERIMENTAL helpers for embedding the hosted checkout in another frontend. Browser-safe: no DOM access at import and no Node modules.
//
// Status: the specification gates embedded checkout separately (decision CSD-10) and defines no postMessage protocol yet. The message shape below is a
// proposal of this repository, versioned (`version: 1`), and every check is strict on purpose: a message is trusted only when it comes from the exact
// checkout origin AND from the frame this page created AND has a known shape. The embedding page never receives a signature, a secret or a wallet address.

export const EMBED_SOURCE = "paytrue-checkout";
export const EMBED_VERSION = 1;
/** The message types of the proposal. */
export const EMBED_TYPES = Object.freeze(["ready", "resize", "state"]);
const STATES = new Set(["open", "connecting", "wallet_connected", "review_required", "awaiting_signature", "authorized", "submitting", "processing", "completed", "failed", "unknown", "expired", "cancelled"]);

/**
 * The URL of a hosted checkout session for an iframe.
 * @param {{ checkoutBaseUrl: string, route?: string, sessionId: string }} args  e.g. https://checkout.example.com (the checkout base URL of the configuration)
 */
export function buildFrameUrl({ checkoutBaseUrl, route = "/c", sessionId }) {
  if (!/^cs_[A-Za-z0-9]{16,128}$/.test(sessionId)) throw new Error("not a checkout session id");
  const base = new URL(checkoutBaseUrl);
  if (base.search || base.hash || base.username || base.password) throw new Error("checkoutBaseUrl must not carry a query, fragment or credentials");
  return base.origin + (base.pathname.replace(/\/+$/, "")) + route + "/" + sessionId;
}

/**
 * Parse and validate the data of a message from the checkout frame. Returns null for anything that is not exactly the proposal.
 * @returns {null | { type: "ready" | "resize" | "state", sessionId: string, height?: number, state?: string }}
 */
export function parseEmbedMessage(data) {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return null;
  if (data.source !== EMBED_SOURCE || data.version !== EMBED_VERSION) return null;
  if (!EMBED_TYPES.includes(data.type)) return null;
  if (typeof data.sessionId !== "string" || !/^cs_[A-Za-z0-9]{16,128}$/.test(data.sessionId)) return null;
  const out = { type: data.type, sessionId: data.sessionId };
  if (data.type === "resize") {
    if (!Number.isFinite(data.height) || data.height < 0 || data.height > 10000) return null;
    out.height = Math.round(data.height);
  }
  if (data.type === "state") {
    if (typeof data.state !== "string" || !STATES.has(data.state)) return null;
    out.state = data.state;
  }
  const extra = Object.keys(data).filter((k) => !["source", "version", "type", "sessionId", "height", "state"].includes(k));
  if (extra.length > 0) return null;
  return out;
}

/**
 * Decide whether a `message` event may be believed. Pass `window` events' fields: `{ origin, source, data }`.
 * @param {{ origin: string, source: unknown, data: unknown }} event
 * @param {{ checkoutOrigin: string, frameWindow: unknown, sessionId?: string }} expected
 */
export function acceptEmbedMessage(event, { checkoutOrigin, frameWindow, sessionId }) {
  if (event.origin !== checkoutOrigin) return null;
  if (frameWindow === undefined || frameWindow === null || event.source !== frameWindow) return null;
  const msg = parseEmbedMessage(event.data);
  if (msg === null) return null;
  if (sessionId !== undefined && msg.sessionId !== sessionId) return null;
  return msg;
}

/** The `allow` and `sandbox` attributes the embedding page should set on the iframe: nothing beyond what the checkout needs. */
export const FRAME_ATTRIBUTES = Object.freeze({
  sandbox: "allow-scripts allow-same-origin allow-forms allow-popups",
  referrerpolicy: "no-referrer",
  loading: "eager",
});
