// SPDX-License-Identifier: Apache-2.0

export interface EnvVar {
  name: string;
  group: string;
  description: string;
  default?: string;
  requiredWhen?: string;
  secret?: boolean;
  example?: string;
}
export const ENV_SCHEMA: EnvVar[];
export const GROUPS: Record<string, string>;

export class ConfigError extends Error {
  constructor(problems: string[]);
  readonly problems: string[];
}

export interface PayTrueConfig {
  readonly env: "development" | "production";
  readonly production: boolean;
  readonly publicOrigin: string;
  readonly basePath: string;
  readonly proxyStripsBasePath: boolean;
  readonly checkout: { readonly origin: string; readonly basePath: string; readonly baseUrl: string; readonly route: string };
  readonly api: { readonly origin: string; readonly basePath: string; readonly baseUrl: string };
  readonly frameAncestors: readonly string[];
  /** The value of the `frame-ancestors` directive of the checkout's content security policy. */
  readonly cspFrameAncestors: string;
  readonly cookie: { readonly domain?: string; readonly path: string; readonly sameSite: string; readonly secure: boolean };
  readonly chains: readonly { readonly id: number; readonly rpcUrls: readonly string[] }[];
  readonly deploymentFile: string | undefined;
  readonly session: { readonly minSeconds: number; readonly defaultSeconds: number; readonly maxSeconds: number };
  readonly webhook: { readonly toleranceSeconds: number; readonly secretConfigured: boolean };
  readonly cloud: { readonly enabled: boolean; readonly baseUrl?: string };
  readonly warnings: readonly string[];
  /** Secrets are not part of the serialised configuration; read one on demand. */
  secret(name: "webhook" | "apiKey"): string | undefined;
}

export function loadConfig(env?: Record<string, string | undefined>): Readonly<PayTrueConfig>;
export function normalizeBasePath(input: string): string;
export function joinPath(...parts: string[]): string;
export function parseOrigin(value: string): string;
export function checkoutSessionUrl(cfg: PayTrueConfig, sessionId: string): string;
export function apiUrl(cfg: PayTrueConfig, path: string): string;
export function routeOf(cfg: PayTrueConfig, pathname: string, surface?: "api" | "checkout"): string | null;
export function cookieAttributes(cfg: PayTrueConfig, options?: { maxAgeSeconds?: number }): string;
