// SPDX-License-Identifier: Apache-2.0

export const API_VERSION: string;

export type SessionState =
  | "open" | "connecting" | "wallet_connected" | "review_required" | "awaiting_signature" | "authorized"
  | "submitting" | "processing" | "completed" | "failed" | "unknown" | "expired" | "cancelled";

export interface CreateCheckoutSessionParams {
  mode: "payment" | "subscription";
  /** Minor units of `currency`: an integer, never a decimal. */
  amount: number;
  /** ISO 4217 code in capitals. */
  currency: string;
  client_reference_id: string;
  /** https (http only on localhost); may contain `{CHECKOUT_SESSION_ID}`. */
  success_url: string;
  /** May contain `{CHECKOUT_SESSION_ID}` and `{CANCEL_REASON}`. */
  cancel_url: string;
  payer_policy: "any_wallet" | "expected_wallet";
  expected_customer_wallet?: string;
  allowed_chains?: number[];
  allowed_tokens?: { chain_id: number; address: string }[];
  /** Seconds. */
  expires_in?: number;
  metadata?: Record<string, string>;
  display: { merchant_name: string; description: string; line_items?: unknown[] };
  mandate_terms?: Record<string, unknown>;
}

export interface CheckoutSession {
  id: string;
  url: string;
  status: SessionState;
  created_at: string;
  expires_at: string;
  mode: string;
  amount: number;
  currency: string;
  client_reference_id: string;
  payer_policy: string;
  live_mode: boolean;
  session_version: number;
  metadata?: Record<string, string>;
  /** Only for an approved embedded-checkout flow; absent for hosted checkout. */
  client_secret?: string;
  [key: string]: unknown;
}

export interface ClientOptions {
  /** The API root without `/v1`, for example `https://pay.example.com/paytrue`. There is no default. */
  baseUrl: string;
  apiKey: string;
  fetch?: typeof fetch;
  timeoutMs?: number;
  apiVersion?: string;
}

export class PayTrueApiError extends Error {
  status: number;
  type?: string;
  code?: string;
  param?: string;
}
export class PayTrueValidationError extends Error {
  problems: string[];
}
export function validateCreateSessionParams(params: unknown): string[];

export class PayTrueClient {
  constructor(options: ClientOptions);
  readonly baseUrl: string;
  createCheckoutSession(params: CreateCheckoutSessionParams, options?: { idempotencyKey?: string; validate?: boolean }): Promise<CheckoutSession>;
  retrieveCheckoutSession(id: string): Promise<CheckoutSession>;
  listCheckoutSessions(query?: { client_reference_id?: string; status?: string; created_after?: string; created_before?: string; limit?: number; starting_after?: string }): Promise<{ data: CheckoutSession[]; has_more: boolean }>;
  cancelCheckoutSession(id: string, options?: { idempotencyKey?: string }): Promise<CheckoutSession>;
}

export interface WebhookEvent {
  id: string;
  type: string;
  api_version: string;
  created: string;
  live_mode: boolean;
  merchant_id: string;
  data: {
    session_id: string;
    client_reference_id: string;
    mode: string;
    state: SessionState;
    session_version: number;
    payment_id: string | null;
    mandate_id: string | null;
    failure_reason: string | null;
    unknown_reason: string | null;
    cancel_reason: string | null;
    chain_id: number | null;
    transaction_hash: string | null;
    finality_state: "not_submitted" | "pending" | "final" | "unresolved";
    payer: string | null;
    initial_charge_settled: boolean | null;
    metadata: Record<string, string>;
  };
}

export const SIGNATURE_HEADER: string;
export const LEGACY_SIGNATURE_HEADER: string;
export class WebhookVerificationError extends Error {
  reason: "missing_header" | "malformed_header" | "timestamp_outside_tolerance" | "signature_mismatch" | "invalid_json";
}
export function signWebhook(args: { payload: string | Uint8Array; secret: string | string[]; timestamp?: number }): string;
export function signatureHeaderOf(headers: Record<string, string | string[] | undefined> | { get(name: string): string | null }): string | undefined;
export function verifyWebhook(args: { payload: string | Uint8Array; header: string | undefined; secret: string | string[]; toleranceSeconds?: number; now?: number }): WebhookEvent;
export function createEventTracker(): {
  consider(event: WebhookEvent): { apply: boolean; reason: "new" | "duplicate" | "stale" | "after_final" };
  stateOf(sessionId: string): SessionState | undefined;
};
