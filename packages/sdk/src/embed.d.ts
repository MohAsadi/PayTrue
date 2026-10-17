// SPDX-License-Identifier: Apache-2.0
// EXPERIMENTAL: embedded checkout is separately gated and its message protocol is a proposal of this repository.

export const EMBED_SOURCE: "paytrue-checkout";
export const EMBED_VERSION: 1;
export const EMBED_TYPES: readonly ["ready", "resize", "state"];

export interface EmbedMessage {
  type: "ready" | "resize" | "state";
  sessionId: string;
  height?: number;
  state?: string;
}

export function buildFrameUrl(args: { checkoutBaseUrl: string; route?: string; sessionId: string }): string;
export function parseEmbedMessage(data: unknown): EmbedMessage | null;
export function acceptEmbedMessage(
  event: { origin: string; source: unknown; data: unknown },
  expected: { checkoutOrigin: string; frameWindow: unknown; sessionId?: string },
): EmbedMessage | null;
export const FRAME_ATTRIBUTES: Readonly<{ sandbox: string; referrerpolicy: string; loading: string }>;
