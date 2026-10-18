// SPDX-License-Identifier: Apache-2.0
// A small, dependency-free client for the PayTrue checkout API (the proposed catalog in spec/checkout). It targets whatever base URL YOU give it:
// a PayTrue server you host, the development stub of this repository, or (optionally) a PayTrue Cloud endpoint. It has no default host.
import { randomUUID } from "node:crypto";

export const API_VERSION = "2026-10-17";

export class PayTrueApiError extends Error {
  /** @param {{status: number, type?: string, code?: string, message?: string, param?: string}} e */
  constructor({ status, type, code, message, param }) {
    super(message ?? `PayTrue API error ${status}`);
    this.name = "PayTrueApiError";
    this.status = status;
    this.type = type;
    this.code = code;
    this.param = param;
  }
}

export class PayTrueValidationError extends Error {
  /** @param {string[]} problems */
  constructor(problems) {
    super(`invalid request: ${problems.join("; ")}`);
    this.name = "PayTrueValidationError";
    this.problems = problems;
  }
}

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const LOCAL = new Set(["localhost", "127.0.0.1", "[::1]"]);

function urlProblem(name, value, problems) {
  if (typeof value !== "string" || value === "") return problems.push(`${name} is required`);
  if (value.length > 2048) return problems.push(`${name} is longer than 2048 characters`);
  let u;
  try {
    // the two documented placeholders are legal inside a URL template
    u = new URL(value.replaceAll("{CHECKOUT_SESSION_ID}", "cs_x").replaceAll("{CANCEL_REASON}", "no_wallet"));
  } catch {
    return problems.push(`${name} is not a URL`);
  }
  if (u.protocol !== "https:" && !(u.protocol === "http:" && LOCAL.has(u.hostname))) problems.push(`${name} must be https (http is allowed only on localhost)`);
  if (u.username || u.password) problems.push(`${name} must not carry credentials`);
  if (u.hash) problems.push(`${name} must not carry a fragment`);
  if (/^\d+\.\d+\.\d+\.\d+$/.test(u.hostname) && !LOCAL.has(u.hostname)) problems.push(`${name} must not be an IP literal`);
  const stray = value.replace(/\{CHECKOUT_SESSION_ID\}|\{CANCEL_REASON\}/g, "").match(/\{[^}]*\}/);
  if (stray) problems.push(`${name} has an unknown placeholder ${stray[0]} (only {CHECKOUT_SESSION_ID} and, for cancel_url, {CANCEL_REASON})`);
  if (name === "success_url" && value.includes("{CANCEL_REASON}")) problems.push("success_url must not use {CANCEL_REASON}");
}

/**
 * Check the parameters of `POST /v1/checkout/sessions` against the rules of the proposed catalog. The server decides; this only saves a round trip.
 * @returns {string[]} the problems found (empty when the parameters look valid)
 */
export function validateCreateSessionParams(p) {
  const problems = [];
  if (p === null || typeof p !== "object") return ["parameters are required"];
  if (!["payment", "subscription"].includes(p.mode)) problems.push("mode must be `payment` or `subscription` (`setup` is reserved)");
  if (!Number.isSafeInteger(p.amount) || p.amount < 0) problems.push("amount must be a non-negative integer in minor units (never a decimal)");
  else if (p.mode === "payment" && p.amount < 1) problems.push("amount must be at least 1 for a payment");
  else if (p.mode === "subscription" && p.amount > 0) problems.push("a subscription with an initial charge is not available yet: use amount 0");
  if (!/^[A-Z]{3}$/.test(p.currency ?? "")) problems.push("currency must be an ISO 4217 code in capitals");
  if (typeof p.client_reference_id !== "string" || p.client_reference_id === "") problems.push("client_reference_id is required");
  urlProblem("success_url", p.success_url, problems);
  urlProblem("cancel_url", p.cancel_url, problems);
  if (!["any_wallet", "expected_wallet"].includes(p.payer_policy)) problems.push("payer_policy must be `any_wallet` or `expected_wallet`");
  if (p.payer_policy === "expected_wallet" && !ADDRESS.test(p.expected_customer_wallet ?? "")) problems.push("expected_customer_wallet must be an address when payer_policy is expected_wallet");
  if (p.payer_policy === "any_wallet" && p.expected_customer_wallet !== undefined) problems.push("expected_customer_wallet must be absent when payer_policy is any_wallet");
  if (p.expires_in !== undefined && (!Number.isSafeInteger(p.expires_in) || p.expires_in < 1)) problems.push("expires_in must be a positive integer in seconds");
  if (p.allowed_chains !== undefined && (!Array.isArray(p.allowed_chains) || p.allowed_chains.length === 0 || !p.allowed_chains.every((c) => Number.isSafeInteger(c) && c > 0))) problems.push("allowed_chains must be a non-empty list of chain ids");
  if (p.allowed_tokens !== undefined && (!Array.isArray(p.allowed_tokens) || p.allowed_tokens.length === 0 || !p.allowed_tokens.every((t) => Number.isSafeInteger(t?.chain_id) && ADDRESS.test(t?.address ?? "")))) problems.push("allowed_tokens must be a non-empty list of {chain_id, address}");
  if (p.metadata !== undefined) {
    const m = p.metadata;
    if (m === null || typeof m !== "object" || Array.isArray(m)) problems.push("metadata must be an object of strings");
    else {
      const keys = Object.keys(m);
      let total = 0;
      if (keys.length > 20) problems.push("metadata has more than 20 keys");
      for (const k of keys) {
        if (typeof m[k] !== "string") problems.push(`metadata.${k} must be a string`);
        else {
          if (Buffer.byteLength(k) > 40) problems.push(`metadata key ${k} is longer than 40 bytes`);
          if (Buffer.byteLength(m[k]) > 500) problems.push(`metadata.${k} is longer than 500 bytes`);
          total += Buffer.byteLength(k) + Buffer.byteLength(m[k]);
        }
      }
      if (total > 4096) problems.push("metadata is larger than 4 KiB");
    }
  }
  if (p.display === null || typeof p.display !== "object" || typeof p.display.merchant_name !== "string" || typeof p.display.description !== "string") problems.push("display needs merchant_name and description");
  if (p.mode === "subscription" && (p.mandate_terms === null || typeof p.mandate_terms !== "object")) problems.push("mandate_terms is required for a subscription");
  return problems;
}

export class PayTrueClient {
  /**
   * @param {{ baseUrl: string, apiKey: string, fetch?: typeof fetch, timeoutMs?: number, apiVersion?: string }} options
   *   `baseUrl` is the API root WITHOUT `/v1`, for example `https://pay.example.com/paytrue`. There is no default.
   */
  constructor({ baseUrl, apiKey, fetch: fetchImpl = globalThis.fetch, timeoutMs = 30000, apiVersion = API_VERSION } = {}) {
    if (typeof baseUrl !== "string" || baseUrl === "") throw new Error("baseUrl is required: PayTrue has no default host (use your own deployment)");
    let u;
    try {
      u = new URL(baseUrl);
    } catch {
      throw new Error(`baseUrl is not a URL: ${baseUrl}`);
    }
    if (u.search || u.hash || u.username || u.password) throw new Error("baseUrl must not carry a query, fragment or credentials");
    if (!apiKey) throw new Error("apiKey is required");
    if (typeof fetchImpl !== "function") throw new Error("no fetch implementation: use Node 18 or later, or pass one");
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.apiVersion = apiVersion;
    this.timeoutMs = timeoutMs;
    this._key = apiKey;
    this._fetch = fetchImpl;
  }

  async _request(method, path, { body, idempotencyKey, query } = {}) {
    const url = new URL(`${this.baseUrl}/v1/${path}`);
    for (const [k, v] of Object.entries(query ?? {})) if (v !== undefined) url.searchParams.set(k, String(v));
    const headers = { Authorization: `Bearer ${this._key}`, "PayTrue-Version": this.apiVersion, Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    const res = await this._fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(this.timeoutMs) });
    const text = await res.text();
    let json;
    try {
      json = text ? JSON.parse(text) : undefined;
    } catch {
      json = undefined;
    }
    if (!res.ok) throw new PayTrueApiError({ status: res.status, ...(json?.error ?? { message: text.slice(0, 200) }) });
    return json;
  }

  /** `POST /v1/checkout/sessions`. A random idempotency key is generated when you give none; pass your own to make a retry safe. */
  createCheckoutSession(params, { idempotencyKey = randomUUID(), validate = true } = {}) {
    if (validate) {
      const problems = validateCreateSessionParams(params);
      if (problems.length) return Promise.reject(new PayTrueValidationError(problems));
    }
    return this._request("POST", "checkout/sessions", { body: params, idempotencyKey });
  }

  /** `GET /v1/checkout/sessions/{id}`: the authoritative state of a session. Fulfil from this or from a webhook, never from the success redirect. */
  retrieveCheckoutSession(id) {
    return this._request("GET", `checkout/sessions/${encodeURIComponent(id)}`);
  }

  /** `GET /v1/checkout/sessions`. Filters: client_reference_id, status, created_after, created_before, limit, starting_after. */
  listCheckoutSessions(query = {}) {
    return this._request("GET", "checkout/sessions", { query });
  }

  /** `POST /v1/checkout/sessions/{id}/cancel`. Fails with `session_already_submitted` once a transaction was submitted. */
  cancelCheckoutSession(id, { idempotencyKey = randomUUID() } = {}) {
    return this._request("POST", `checkout/sessions/${encodeURIComponent(id)}/cancel`, { body: {}, idempotencyKey });
  }
}
