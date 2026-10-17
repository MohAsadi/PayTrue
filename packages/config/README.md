# @paytrue/config

Reads and validates the `PAYTRUE_*` environment of a self-hosted PayTrue deployment and derives its URLs for **a path on a domain you already serve, your own subdomain, or split hosts**.
No dependencies. It contacts no network, and no default points at a PayTrue-hosted service: PayTrue Cloud is off unless you enable it **and** give it an address.

> Pre-alpha. Not published to npm (`"private": true`). Status of the whole project: [open-source readiness](../../docs/open-source-readiness.md).

```js
import { loadConfig, checkoutSessionUrl, apiUrl, routeOf, cookieAttributes } from "@paytrue/config";

const cfg = loadConfig(process.env);           // throws ConfigError listing every problem
checkoutSessionUrl(cfg, "cs_...");             // https://pay.example.com/c/cs_...   (or .../paytrue/c/cs_...)
apiUrl(cfg, "checkout/sessions");              // https://pay.example.com/v1/checkout/sessions
routeOf(cfg, "/paytrue/v1/checkout/sessions"); // "/v1/checkout/sessions", or null outside the base path
cfg.cspFrameAncestors;                         // "'none'" unless you named origins that may embed the checkout
```

`PAYTRUE_ENV=production` is strict: https origins only, no local addresses, a required public origin, at least two RPC hosts per chain. Secrets are read with `cfg.secret("webhook")` and are
never serialised.

Reference: [docs/configuration.md](../../docs/configuration.md) (generated from `src/schema.js`). Layouts: [docs/domains.md](../../docs/domains.md).

```bash
node --test "test/*.test.mjs"
node scripts/generate-env-example.mjs --check      # .env.example matches the schema
node scripts/generate-config-doc.mjs --check       # docs/configuration.md matches the schema
```

License: Apache-2.0.
