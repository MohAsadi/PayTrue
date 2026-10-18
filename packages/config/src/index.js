// SPDX-License-Identifier: Apache-2.0
// @paytrue/config: read and validate the PAYTRUE_* environment of a self-hosted PayTrue deployment and derive its public URLs.
// No dependencies. Nothing here contacts a network, and no default points at a PayTrue-hosted service.

export { ENV_SCHEMA, GROUPS } from "./schema.js";

export class ConfigError extends Error {
  /** @param {string[]} problems */
  constructor(problems) {
    super(`invalid PayTrue configuration:\n- ${problems.join("\n- ")}`);
    this.name = "ConfigError";
    this.problems = problems;
  }
}

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);
const SAFE_PATH = /^\/[A-Za-z0-9._~!$&'()*+,;=:@%/-]*$/;

/**
 * Normalise a mount path: `/` stays `/`; `paytrue`, `/paytrue/` and `/paytrue` all become `/paytrue`.
 * @param {string} input
 * @returns {string}
 */
export function normalizeBasePath(input) {
  let s = String(input ?? "").trim();
  if (s === "" || s === "/") return "/";
  if (!s.startsWith("/")) s = "/" + s;
  s = s.replace(/\/+$/, "");
  if (!SAFE_PATH.test(s) || s.includes("//") || s.split("/").some((seg) => seg === ".." || seg === ".")) {
    throw new Error(`not a usable path: ${JSON.stringify(input)}`);
  }
  return s;
}

/**
 * Join path segments with single slashes; the result always starts with `/` and has no trailing slash unless it is `/`.
 * @param {...string} parts
 */
export function joinPath(...parts) {
  const joined = "/" + parts.map((p) => String(p).replace(/^\/+|\/+$/g, "")).filter((p) => p !== "").join("/");
  return joined === "" ? "/" : joined;
}

/**
 * Parse an origin: scheme, host and optional port; nothing else.
 * @param {string} value
 * @returns {string} the normalised origin
 */
export function parseOrigin(value) {
  let u;
  try {
    u = new URL(String(value));
  } catch {
    throw new Error(`not a URL: ${JSON.stringify(value)}`);
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") throw new Error(`scheme must be http or https: ${JSON.stringify(value)}`);
  if (u.username || u.password) throw new Error(`an origin has no credentials: ${JSON.stringify(value)}`);
  if (u.pathname !== "/" || u.search || u.hash) throw new Error(`an origin has no path, query or fragment (use the base path setting for a path): ${JSON.stringify(value)}`);
  return u.origin;
}

const isLocal = (origin) => LOCAL_HOSTS.has(new URL(origin).hostname);
const intOf = (name, raw, def, problems, { min = 1 } = {}) => {
  if (raw === undefined || raw === "") return def;
  if (!/^\d+$/.test(raw) || Number(raw) < min) {
    problems.push(`${name} must be an integer of at least ${min}`);
    return def;
  }
  return Number(raw);
};
const list = (raw) => String(raw ?? "").split(/[\s,]+/).filter(Boolean);

/**
 * @param {Record<string, string | undefined>} [env]
 * @returns {Readonly<PayTrueConfig>}
 */
export function loadConfig(env = process.env) {
  const problems = [];
  const warnings = [];
  const get = (name) => (env[name] === undefined || env[name] === "" ? undefined : String(env[name]).trim());

  // ---- environment
  const envName = get("PAYTRUE_ENV") ?? "development";
  if (envName !== "development" && envName !== "production") problems.push("PAYTRUE_ENV must be `development` or `production`");
  const production = envName === "production";

  const tryOrigin = (name, fallback) => {
    const raw = get(name);
    if (raw === undefined) return fallback;
    try {
      const o = parseOrigin(raw);
      if (production) {
        if (!o.startsWith("https://")) problems.push(`${name} must be https in production`);
        if (isLocal(o)) problems.push(`${name} must not be a local address in production`);
      }
      return o;
    } catch (e) {
      problems.push(`${name}: ${e.message}`);
      return fallback;
    }
  };
  const tryPath = (name, fallback) => {
    const raw = get(name);
    if (raw === undefined) return fallback;
    try {
      return normalizeBasePath(raw);
    } catch (e) {
      problems.push(`${name}: ${e.message}`);
      return fallback;
    }
  };

  // ---- origins and paths
  let publicOrigin = tryOrigin("PAYTRUE_PUBLIC_ORIGIN", undefined);
  if (publicOrigin === undefined) {
    if (production) problems.push("PAYTRUE_PUBLIC_ORIGIN is required in production");
    publicOrigin = "http://localhost:8080";
  }
  const basePath = tryPath("PAYTRUE_BASE_PATH", "/");
  const checkoutOrigin = tryOrigin("PAYTRUE_CHECKOUT_ORIGIN", publicOrigin);
  const checkoutBasePath = tryPath("PAYTRUE_CHECKOUT_BASE_PATH", basePath);
  const checkoutRoute = tryPath("PAYTRUE_CHECKOUT_ROUTE", "/c");
  const apiOrigin = tryOrigin("PAYTRUE_API_ORIGIN", publicOrigin);
  const apiBasePath = tryPath("PAYTRUE_API_BASE_PATH", basePath);
  const proxyStrips = (get("PAYTRUE_PROXY_STRIPS_BASE_PATH") ?? "false") === "true";
  if (!["true", "false"].includes(get("PAYTRUE_PROXY_STRIPS_BASE_PATH") ?? "false")) problems.push("PAYTRUE_PROXY_STRIPS_BASE_PATH must be `true` or `false`");

  // ---- embedding
  const frameAncestors = [];
  for (const raw of list(get("PAYTRUE_ALLOWED_FRAME_ANCESTORS"))) {
    if (raw === "*") {
      problems.push("PAYTRUE_ALLOWED_FRAME_ANCESTORS must not contain `*`: name each origin that may embed the checkout");
      continue;
    }
    try {
      const o = parseOrigin(raw);
      if (production && !o.startsWith("https://")) problems.push(`PAYTRUE_ALLOWED_FRAME_ANCESTORS: ${o} must be https in production`);
      frameAncestors.push(o);
    } catch (e) {
      problems.push(`PAYTRUE_ALLOWED_FRAME_ANCESTORS: ${e.message}`);
    }
  }

  // ---- cookie
  const sameSite = (get("PAYTRUE_COOKIE_SAMESITE") ?? "strict").toLowerCase();
  if (!["strict", "lax", "none"].includes(sameSite)) problems.push("PAYTRUE_COOKIE_SAMESITE must be strict, lax or none");
  const cookieDomain = get("PAYTRUE_COOKIE_DOMAIN");
  if (cookieDomain !== undefined) {
    const host = new URL(checkoutOrigin).hostname;
    const d = cookieDomain.replace(/^\./, "").toLowerCase();
    if (!/^[a-z0-9.-]+$/.test(d) || !(host === d || host.endsWith("." + d))) problems.push("PAYTRUE_COOKIE_DOMAIN must be the checkout host or a parent domain of it");
  }
  const cookiePath = tryPath("PAYTRUE_COOKIE_PATH", checkoutBasePath);
  const secureCookie = checkoutOrigin.startsWith("https://");
  if (sameSite === "none" && !(production && secureCookie)) problems.push("PAYTRUE_COOKIE_SAMESITE=none needs production and an https checkout origin (the cookie must be Secure)");
  if (frameAncestors.length > 0 && sameSite === "strict") {
    warnings.push("PAYTRUE_ALLOWED_FRAME_ANCESTORS is set while the cookie is SameSite=strict: a browser will not send a strict cookie from inside a cross-site frame, so an embedded checkout cannot keep its control cookie. Embedded checkout is separately gated; see the README, section Embed the checkout");
  }

  // ---- chains
  const chainIds = list(get("PAYTRUE_CHAIN_IDS") ?? (production ? undefined : "31337"));
  if (production && chainIds.length === 0) problems.push("PAYTRUE_CHAIN_IDS is required in production");
  const chains = [];
  for (const id of chainIds) {
    if (!/^[1-9]\d*$/.test(id)) {
      problems.push(`PAYTRUE_CHAIN_IDS: ${JSON.stringify(id)} is not a chain id`);
      continue;
    }
    const varName = `PAYTRUE_RPC_URLS_${id}`;
    const raw = get(varName) ?? (!production && id === "31337" ? "http://127.0.0.1:8545" : undefined);
    const urls = [];
    if (raw === undefined) problems.push(`${varName} is required for chain ${id}`);
    for (const u of list(raw)) {
      try {
        const parsed = new URL(u);
        if (parsed.protocol !== "https:" && parsed.protocol !== "http:") throw new Error("scheme");
        if (production && parsed.protocol !== "https:") problems.push(`${varName}: ${parsed.host} must be https in production`);
        urls.push(parsed.toString());
      } catch {
        problems.push(`${varName}: ${JSON.stringify(u)} is not a URL`);
      }
    }
    const hosts = new Set(urls.map((u) => new URL(u).host));
    if (production && hosts.size < 2) problems.push(`${varName}: production needs at least two RPC URLs on distinct hosts (a money decision rests on two independent sources)`);
    chains.push(Object.freeze({ id: Number(id), rpcUrls: Object.freeze(urls) }));
  }
  const deploymentFile = get("PAYTRUE_DEPLOYMENT_FILE") ?? (production ? undefined : "deployments/local-31337.json");
  if (production && deploymentFile === undefined) problems.push("PAYTRUE_DEPLOYMENT_FILE is required in production");

  // ---- sessions and webhooks
  const lifeMin = intOf("PAYTRUE_SESSION_LIFETIME_MIN_SECONDS", get("PAYTRUE_SESSION_LIFETIME_MIN_SECONDS"), 600, problems);
  const lifeDef = intOf("PAYTRUE_SESSION_LIFETIME_DEFAULT_SECONDS", get("PAYTRUE_SESSION_LIFETIME_DEFAULT_SECONDS"), 1800, problems);
  const lifeMax = intOf("PAYTRUE_SESSION_LIFETIME_MAX_SECONDS", get("PAYTRUE_SESSION_LIFETIME_MAX_SECONDS"), 86400, problems);
  if (!(lifeMin <= lifeDef && lifeDef <= lifeMax)) problems.push("session lifetimes must satisfy MIN <= DEFAULT <= MAX");
  const tolerance = intOf("PAYTRUE_WEBHOOK_TOLERANCE_SECONDS", get("PAYTRUE_WEBHOOK_TOLERANCE_SECONDS"), 300, problems);

  // ---- optional Cloud: off by default; there is no default URL
  const cloudFlag = get("PAYTRUE_CLOUD_ENABLED") ?? "false";
  if (!["true", "false"].includes(cloudFlag)) problems.push("PAYTRUE_CLOUD_ENABLED must be `true` or `false`");
  const cloudEnabled = cloudFlag === "true";
  let cloudBaseUrl;
  if (cloudEnabled) {
    const raw = get("PAYTRUE_CLOUD_BASE_URL");
    if (raw === undefined) problems.push("PAYTRUE_CLOUD_BASE_URL is required when PAYTRUE_CLOUD_ENABLED=true (there is no default)");
    else {
      try {
        cloudBaseUrl = new URL(raw).toString().replace(/\/$/, "");
      } catch {
        problems.push("PAYTRUE_CLOUD_BASE_URL is not a URL");
      }
    }
  } else if (get("PAYTRUE_CLOUD_BASE_URL") !== undefined) {
    warnings.push("PAYTRUE_CLOUD_BASE_URL is set but PAYTRUE_CLOUD_ENABLED is not true: Cloud stays off");
  }

  if (problems.length > 0) throw new ConfigError(problems);

  const surface = (origin, base) => ({ origin, basePath: base, baseUrl: origin + (base === "/" ? "" : base) });
  const checkout = { ...surface(checkoutOrigin, checkoutBasePath), route: checkoutRoute };
  const api = surface(apiOrigin, apiBasePath);
  const secrets = { webhook: get("PAYTRUE_WEBHOOK_SECRET"), apiKey: get("PAYTRUE_API_KEY") };

  const cfg = {
    env: envName,
    production,
    publicOrigin,
    basePath,
    proxyStripsBasePath: proxyStrips,
    checkout: Object.freeze(checkout),
    api: Object.freeze(api),
    frameAncestors: Object.freeze(frameAncestors),
    /** The value of the `frame-ancestors` directive of the checkout's content security policy. */
    cspFrameAncestors: frameAncestors.length === 0 ? "'none'" : frameAncestors.join(" "),
    cookie: Object.freeze({ domain: cookieDomain?.replace(/^\./, ""), path: cookiePath, sameSite, secure: secureCookie }),
    chains: Object.freeze(chains),
    deploymentFile,
    session: Object.freeze({ minSeconds: lifeMin, defaultSeconds: lifeDef, maxSeconds: lifeMax }),
    webhook: Object.freeze({ toleranceSeconds: tolerance, secretConfigured: secrets.webhook !== undefined }),
    cloud: Object.freeze({ enabled: cloudEnabled, baseUrl: cloudBaseUrl }),
    warnings: Object.freeze(warnings),
    /** Secrets are read on demand and are not part of the serialised configuration. */
    secret: (name) => {
      if (name !== "webhook" && name !== "apiKey") throw new Error(`unknown secret ${name}`);
      return secrets[name];
    },
    toJSON() {
      const { secret, toJSON, ...rest } = cfg;
      return rest;
    },
  };
  Object.defineProperty(cfg, "secret", { enumerable: false });
  Object.defineProperty(cfg, "toJSON", { enumerable: false });
  return Object.freeze(cfg);
}

/** `<checkout base URL><route>/<session id>` for any layout: a path on an existing domain, a subdomain, or a dedicated host. */
export function checkoutSessionUrl(cfg, sessionId) {
  if (!/^cs_[A-Za-z0-9]{16,128}$/.test(sessionId)) throw new Error("not a checkout session id");
  return cfg.checkout.baseUrl + cfg.checkout.route + "/" + sessionId;
}

/** `<api base URL>/v1/<path>`. */
export function apiUrl(cfg, path) {
  return cfg.api.baseUrl + "/v1/" + String(path).replace(/^\/+/, "");
}

/**
 * Map a request path to the route inside PayTrue, for a server behind a proxy.
 * With `proxyStripsBasePath` the path arrives without the base path and is returned as it is; otherwise the base path must be the prefix.
 * @returns {string | null} the route (always starting with `/`), or null when the path is outside PayTrue
 */
export function routeOf(cfg, pathname, surface = "api") {
  const base = (surface === "checkout" ? cfg.checkout.basePath : cfg.api.basePath);
  if (cfg.proxyStripsBasePath) return pathname.startsWith("/") ? pathname : null;
  if (base === "/") return pathname;
  if (pathname === base) return "/";
  return pathname.startsWith(base + "/") ? pathname.slice(base.length) : null;
}

/** The `Set-Cookie` attribute string (without name and value) for the checkout control cookie. */
export function cookieAttributes(cfg, { maxAgeSeconds } = {}) {
  const parts = ["HttpOnly", `Path=${cfg.cookie.path}`, `SameSite=${cfg.cookie.sameSite[0].toUpperCase()}${cfg.cookie.sameSite.slice(1)}`];
  if (cfg.cookie.secure) parts.push("Secure");
  if (cfg.cookie.domain) parts.push(`Domain=${cfg.cookie.domain}`);
  if (maxAgeSeconds !== undefined) parts.push(`Max-Age=${maxAgeSeconds}`);
  return parts.join("; ");
}

/**
 * @typedef {Object} PayTrueConfig
 * @property {"development"|"production"} env
 * @property {boolean} production
 * @property {string} publicOrigin
 * @property {string} basePath
 * @property {boolean} proxyStripsBasePath
 * @property {{origin: string, basePath: string, baseUrl: string, route: string}} checkout
 * @property {{origin: string, basePath: string, baseUrl: string}} api
 * @property {readonly string[]} frameAncestors
 * @property {string} cspFrameAncestors
 * @property {{domain?: string, path: string, sameSite: string, secure: boolean}} cookie
 * @property {readonly {id: number, rpcUrls: readonly string[]}[]} chains
 * @property {string | undefined} deploymentFile
 * @property {{minSeconds: number, defaultSeconds: number, maxSeconds: number}} session
 * @property {{toleranceSeconds: number, secretConfigured: boolean}} webhook
 * @property {{enabled: boolean, baseUrl?: string}} cloud
 * @property {readonly string[]} warnings
 * @property {(name: "webhook" | "apiKey") => string | undefined} secret
 */
