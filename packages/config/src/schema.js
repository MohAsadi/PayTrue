// SPDX-License-Identifier: Apache-2.0
// The environment of a self-hosted PayTrue deployment, in one place. `.env.example` and docs/configuration.md are checked against this list.
//
// Every variable is read by code that exists in this repository: the configuration loader (group "runtime"), the development stub (group "devserver"),
// the contract deployment script (group "contracts") or a tool. Nothing is listed for a component that does not exist.

/**
 * @typedef {Object} EnvVar
 * @property {string} name
 * @property {string} group
 * @property {string} description
 * @property {string} [default]        The value used when the variable is unset. Absent means: no default, see `required`.
 * @property {string} [requiredWhen]   When the variable must be set.
 * @property {boolean} [secret]
 * @property {string} [example]
 */

/** @type {EnvVar[]} */
export const ENV_SCHEMA = [
  // ---- runtime: where and how PayTrue is served
  { name: "PAYTRUE_ENV", group: "runtime", default: "development", example: "production",
    description: "`development` or `production`. Production requires https origins, at least two RPC URLs per chain, and refuses the development stub." },
  { name: "PAYTRUE_PUBLIC_ORIGIN", group: "runtime", default: "http://localhost:8080 (development only)", requiredWhen: "production", example: "https://pay.example.com",
    description: "The origin (scheme, host, optional port) under which the operator serves PayTrue. Never a path." },
  { name: "PAYTRUE_BASE_PATH", group: "runtime", default: "/", example: "/paytrue",
    description: "The path under which PayTrue is mounted on that origin. `/` for a subdomain or a dedicated host, `/paytrue` for a path on an existing site." },
  { name: "PAYTRUE_CHECKOUT_ORIGIN", group: "runtime", default: "PAYTRUE_PUBLIC_ORIGIN", example: "https://checkout.example.com",
    description: "The origin that serves the hosted checkout pages. Give it its own origin (a subdomain) when you can: the checkout runs a strict content security policy and no merchant code." },
  { name: "PAYTRUE_CHECKOUT_BASE_PATH", group: "runtime", default: "PAYTRUE_BASE_PATH", example: "/",
    description: "The path under which the hosted checkout is mounted on its origin." },
  { name: "PAYTRUE_CHECKOUT_ROUTE", group: "runtime", default: "/c", example: "/c",
    description: "The route prefix of a hosted checkout session: `<origin><base path><route>/<session id>`." },
  { name: "PAYTRUE_API_ORIGIN", group: "runtime", default: "PAYTRUE_PUBLIC_ORIGIN", example: "https://api.example.com",
    description: "The origin of the merchant API, when it is not the public origin." },
  { name: "PAYTRUE_API_BASE_PATH", group: "runtime", default: "PAYTRUE_BASE_PATH", example: "/",
    description: "The path under which the merchant API (`/v1/...`) is mounted on its origin." },
  { name: "PAYTRUE_PROXY_STRIPS_BASE_PATH", group: "runtime", default: "false", example: "true",
    description: "`true` when your reverse proxy removes the base path before forwarding, `false` when it forwards the path unchanged." },
  { name: "PAYTRUE_ALLOWED_FRAME_ANCESTORS", group: "runtime", default: "(empty: nobody may embed the checkout)", example: "https://shop.example.com https://www.example.com",
    description: "Space- or comma-separated origins that may embed the hosted checkout in an iframe. Empty means `frame-ancestors 'none'`. Embedded checkout is separately gated in the specification." },
  { name: "PAYTRUE_COOKIE_DOMAIN", group: "runtime", default: "(unset: host-only cookie)", example: "example.com",
    description: "Cookie domain for the checkout control cookie. Leave unset for a host-only cookie. When set it must be the checkout host or a parent domain of it." },
  { name: "PAYTRUE_COOKIE_PATH", group: "runtime", default: "PAYTRUE_CHECKOUT_BASE_PATH", example: "/",
    description: "Cookie path of the checkout control cookie." },
  { name: "PAYTRUE_COOKIE_SAMESITE", group: "runtime", default: "strict", example: "strict",
    description: "`strict`, `lax` or `none`. `none` is needed only for a cross-site embed and requires production with https." },

  // ---- runtime: chains and contracts
  { name: "PAYTRUE_CHAIN_IDS", group: "runtime", default: "31337 (development only)", requiredWhen: "production", example: "8453,42161",
    description: "Comma-separated chain ids this deployment accepts payments on." },
  { name: "PAYTRUE_RPC_URLS_<chainId>", group: "runtime", default: "http://127.0.0.1:8545 for 31337 (development only)", requiredWhen: "production, for every chain id", example: "https://rpc-a.example.org,https://rpc-b.example.net",
    description: "Comma-separated RPC URLs of one chain. Production needs at least two distinct hosts: a money decision rests on two independent sources." },
  { name: "PAYTRUE_DEPLOYMENT_FILE", group: "runtime", default: "deployments/local-31337.json (development only)", requiredWhen: "production", example: "deployments/sovereign-8453.json",
    description: "The deployment manifest (docs/contracts-deployments.md) that names the contract addresses of your own deployment. PayTrue ships no canonical addresses." },

  // ---- runtime: sessions and webhooks
  { name: "PAYTRUE_SESSION_LIFETIME_MIN_SECONDS", group: "runtime", default: "600", example: "600",
    description: "Minimum session lifetime a merchant may request. A proposal (record CSR-01); not an approved constant." },
  { name: "PAYTRUE_SESSION_LIFETIME_DEFAULT_SECONDS", group: "runtime", default: "1800", example: "1800",
    description: "Session lifetime when a request gives none (30 minutes)." },
  { name: "PAYTRUE_SESSION_LIFETIME_MAX_SECONDS", group: "runtime", default: "86400", example: "86400",
    description: "Maximum session lifetime a merchant may request." },
  { name: "PAYTRUE_WEBHOOK_SECRET", group: "runtime", secret: true, example: "(a long random value)",
    description: "The signing secret of your webhook endpoint. Never commit it." },
  { name: "PAYTRUE_WEBHOOK_TOLERANCE_SECONDS", group: "runtime", default: "300", example: "300",
    description: "How far a webhook timestamp may differ from the receiver's clock before the event is rejected as a replay. A proposal." },
  { name: "PAYTRUE_API_KEY", group: "runtime", secret: true, example: "(your merchant API key)",
    description: "The merchant API key used by the SDK and the examples. Never commit it." },

  // ---- runtime: optional PayTrue Cloud
  { name: "PAYTRUE_CLOUD_ENABLED", group: "runtime", default: "false", example: "false",
    description: "PayTrue Cloud is optional and off by default. Nothing in this repository requires it." },
  { name: "PAYTRUE_CLOUD_BASE_URL", group: "runtime", requiredWhen: "PAYTRUE_CLOUD_ENABLED=true", example: "(only if you use Cloud)",
    description: "The base URL of a PayTrue Cloud API. There is no default: the repository never assumes a hosted service." },

  // ---- devserver
  { name: "PAYTRUE_LISTEN_HOST", group: "devserver", default: "127.0.0.1", example: "127.0.0.1",
    description: "Interface the development stub listens on." },
  { name: "PAYTRUE_LISTEN_PORT", group: "devserver", default: "8080", example: "8080",
    description: "Port the development stub listens on." },
  { name: "PAYTRUE_WEBHOOK_URL", group: "devserver", example: "http://127.0.0.1:9000/webhooks",
    description: "Where the development stub delivers signed webhook events (for the examples and tests)." },

  // ---- contracts: the Foundry deployment script (contracts/script/Deploy.s.sol). The legacy FASTPAY_* names are still read when the PAYTRUE_* one is unset.
  { name: "PAYTRUE_PERMIT2", group: "contracts", requiredWhen: "deploying", example: "0x000000000022D473030F116dDEE9F6B43aC78BA3", description: "The Permit2 contract of the chain." },
  { name: "PAYTRUE_GOVERNANCE", group: "contracts", requiredWhen: "deploying", example: "(a timelock address)", description: "The governance address. A timelock in production." },
  { name: "PAYTRUE_GUARDIAN", group: "contracts", requiredWhen: "deploying", example: "(a stop-only address)", description: "The guardian address (stop-only)." },
  { name: "PAYTRUE_RISK_AUTHORITY", group: "contracts", requiredWhen: "deploying", example: "(an address)", description: "The pause authority of the mandate manager." },
  { name: "PAYTRUE_MAX_QUOTE_TTL", group: "contracts", requiredWhen: "deploying", example: "300", description: "Immutable ceiling of a quote's life, in seconds (PC-06)." },
  { name: "PAYTRUE_MAX_BAND_WIDTH_BPS", group: "contracts", requiredWhen: "deploying", example: "500", description: "Immutable ceiling of a price band, in basis points (PC-07)." },
  { name: "PAYTRUE_QUOTE_SET_GRACE", group: "contracts", requiredWhen: "deploying", example: "300", description: "Grace of quotes issued before a signer-set rotation, in seconds (PC-08)." },
  { name: "PAYTRUE_FEE_CEILING_BPS", group: "contracts", requiredWhen: "deploying", example: "(your value)", description: "Immutable fee ceiling in basis points. No value is proposed (PC-05)." },
  { name: "PAYTRUE_FEE_BPS", group: "contracts", requiredWhen: "deploying", example: "(your value)", description: "The initial fee, at most the ceiling." },
  { name: "PAYTRUE_FEE_RECIPIENT", group: "contracts", requiredWhen: "deploying", example: "(an address)", description: "The fee recipient." },
];

export const GROUPS = {
  runtime: "Runtime: where PayTrue is served, which chains and contracts it uses, sessions and webhooks, optional Cloud",
  devserver: "Development stub (packages/devserver): never used in production",
  contracts: "Contract deployment (contracts/script/Deploy.s.sol); a legacy FASTPAY_* name is read when the PAYTRUE_* one is unset",
};
