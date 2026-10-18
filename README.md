# PayTrue

**Non-custodial crypto payments you run yourself.** PayTrue is an open-source toolkit: smart contracts for one-off and recurring payments, a typed-data (EIP-712) encoder, a client SDK with signed
webhooks, and the specification they follow. You deploy it on your own infrastructure, under your own domain, against your own chains. **PayTrue Cloud is optional; nothing here requires it.**

> **Status: pre-alpha. Do not use it with real funds.**
> The contracts are **not audited**. The protocol is **not frozen** (`python -I spec/tools/freeze_readiness.py` prints NOT READY). **No wallet has been tested.** There is **no production
> payment service** yet: what exists is the contracts, four packages, a development stub of the checkout API, deployment aids and the specification. Nothing is published to npm or to a container registry.

## What is in the repository

| Path | What | State |
|---|---|---|
| [`contracts/`](contracts/README.md) | The Solidity contracts (Foundry): mandate manager, payment router, registries, deployment script | Tested, **not audited**; constants are proposals |
| [`packages/config`](packages/config) | `@paytrue/config`: reads and validates the `PAYTRUE_*` environment, derives URLs for any layout | Tested |
| [`packages/sdk`](packages/sdk) | `@paytrue/sdk`: checkout API client, signed-webhook verification, embedding helpers. No dependencies, no default host | Tested; targets a **proposed** API |
| [`packages/eip712`](packages/eip712) | `@paytrue/eip712`: the typed-data encoder, built from `spec/eip712/types.json`. No dependencies | Tested against golden vectors; types are a proposal |
| [`packages/devserver`](packages/devserver) | A **development stub** of the checkout API: in memory, no wallet, no chain. **Not a payment server**; refuses `PAYTRUE_ENV=production` | For examples and tests only |
| [`deploy/`](deploy) | Caddy and nginx layouts, two development Dockerfiles, a compose file | Written; proxies and images **not run** by this repository's checks |
| [`deployments/`](deployments) | The manifest format of a contract deployment, and an example | Format validated by `scripts/validate_deployment.py` |
| [`examples/`](examples/headless-node) | Headless Node and embedded iframe (experimental); recipes for a same-domain path and a sovereign deployment are in [Use the packages](#examples) | The two examples were run |
| [`scripts/`](scripts) | Local devnet, repository checks, link check | |
| [`spec/`](spec/README.md) | The specification (19 documents), the checks, a reference model, the recorded evidence | Draft; uses the working name FastPay (see [Name](#license-third-party-code-and-the-name)) |

## Quick start

You need Git, Node.js (22.13+ builds every package; 18+ is enough for the SDK, the configuration package and the stub) and Python 3.10+. Docker is optional.

```bash
git clone https://github.com/MohAsadi/PayTrue.git && cd PayTrue
node examples/headless-node/index.mjs                 # an order, signed webhooks, fulfilled once: offline, no wallet, no chain
node --test "packages/config/test/*.test.mjs" "packages/sdk/test/*.test.mjs" "packages/eip712/test/*.test.mjs" "packages/devserver/test/*.test.mjs"
python -I spec/toolchain/fetch_toolchain.py           # the pinned Foundry and solc, verified by SHA-256 (about 150 MB)
python -I scripts/devnet.py --once                    # a throwaway local chain with Permit2 and the contracts deployed; writes deployments/local-31337.json
python -I spec/toolchain/forge.py --project contracts test      # the contract tests (about four minutes)
```

Optional: `docker compose -f deploy/compose/compose.yaml up --build` builds a local devnet and the stub on `127.0.0.1` (set `PAYTRUE_DEVSERVER_PORT` or `PAYTRUE_DEVNET_PORT` if a port is taken).
The compose file is validated offline; the images have not been built by this repository's checks. If `listen EACCES` appears on Windows, a port range is reserved: choose another port.

### Examples

Each runs offline against the development stub unless noted; none needs an account.

| Example | Run | Verified |
|---|---|---|
| [`examples/headless-node`](examples/headless-node) | `node examples/headless-node/index.mjs`: your server creates a session, verifies and orders signed webhooks, fulfils once | Runs |
| [`examples/embed-iframe`](examples/embed-iframe) | `node examples/embed-iframe/server.mjs` (experimental): two local origins; your page frames the checkout and accepts messages only from the exact origin, frame and shape | Run in a real browser, allowed and blocked case |
| Same-domain path (a recipe, no folder) | The stub under `/paytrue`: `PAYTRUE_PUBLIC_ORIGIN=https://example.com PAYTRUE_BASE_PATH=/paytrue PAYTRUE_LISTEN_PORT=8787 node packages/devserver/bin/paytrue-devserver.mjs`, then a proxy file from [Run it under your own domain](#run-it-under-your-own-domain) | Application side tested; proxy files not run |
| Sovereign deployment (a recipe, no folder) | `python -I scripts/devnet.py --once` (needs the toolchain fetch) | Run end to end with the pinned anvil and forge |

## Use the packages

The packages are **not on npm yet** (`"private": true`). Until they are, use them from a clone (a relative import, or `npm pack` in the package folder). Once published, the names are
`@paytrue/sdk`, `@paytrue/config`, `@paytrue/eip712`.

### SDK: create a session and verify webhooks (headless)

"Headless" means your server drives PayTrue and no PayTrue interface runs on your side. The SDK implements the **proposed** checkout API (`spec/checkout/`); no production server implements it yet,
the stub implements part of it in memory. The SDK has **no default host**: you pass the `baseUrl` of your own deployment or of the stub.

```js
import { PayTrueClient, verifyWebhook, signatureHeaderOf, createEventTracker } from "@paytrue/sdk";

const client = new PayTrueClient({ baseUrl: process.env.PAYTRUE_BASE_URL, apiKey: process.env.PAYTRUE_API_KEY });   // the API root without /v1

const session = await client.createCheckoutSession({
  mode: "payment",
  amount: 4900,                              // minor units, an integer: 49.00
  currency: "EUR",
  client_reference_id: "order-10432",
  success_url: "https://shop.example/done?s={CHECKOUT_SESSION_ID}",
  cancel_url: "https://shop.example/cart?s={CHECKOUT_SESSION_ID}&reason={CANCEL_REASON}",
  payer_policy: "any_wallet",
  display: { merchant_name: "Example Shop", description: "Order 10432" },
}, { idempotencyKey: "order-10432-create" });
// send the customer to session.url

// in your webhook endpoint, on the RAW body, before any JSON parsing:
const tracker = createEventTracker();
const event = verifyWebhook({ payload: rawBody, header: signatureHeaderOf(request.headers), secret: process.env.PAYTRUE_WEBHOOK_SECRET, toleranceSeconds: 300 });
const verdict = tracker.consider(event);
if (verdict.apply && event.type === "checkout.session.completed") fulfil(event.data.client_reference_id);
```

| Export | Purpose |
|---|---|
| `PayTrueClient` | `createCheckoutSession`, `retrieveCheckoutSession`, `listCheckoutSessions`, `cancelCheckoutSession`; idempotency keys; `PayTrueApiError`, `PayTrueValidationError` |
| `signWebhook`, `verifyWebhook`, `signatureHeaderOf` | HMAC-SHA-256 over `<t>.<raw body>`; secret rotation overlap; `WebhookVerificationError` with a stable `reason` |
| `createEventTracker` | Deduplicate by event id; apply an event only if its `session_version` is higher; `completed`, `failed`, `expired`, `cancelled` are final |
| `@paytrue/sdk/embed` | Browser-safe, **experimental**: `buildFrameUrl`, `acceptEmbedMessage`, `FRAME_ATTRIBUTES` |

**The rules the API is built around**

- The success redirect is **not proof of payment**: anyone can open that URL. Fulfil from a signed webhook (`completed`) or from `retrieveCheckoutSession`.
- Only `completed` is final success. `unknown` means the outcome is not known: **never fulfil, never treat it as `failed`, never offer a second payment.**
- Webhooks are delivered at least once and not in order: deduplicate by `id`, apply by `session_version`. The signature header is `PayTrue-Signature: t=<unix>,v1=<hex>` (the proposal's earlier name `FastPay-Signature` is also read); reject timestamps outside the tolerance (300 s is a proposal). Return `2xx` only after you stored the event.
- The only placeholders in `success_url` and `cancel_url` are `{CHECKOUT_SESSION_ID}` and (cancel only) `{CANCEL_REASON}`. URLs must be https (http on localhost only), without credentials or fragment.

### Configuration package

```js
import { loadConfig, checkoutSessionUrl, apiUrl, routeOf, cookieAttributes } from "@paytrue/config";

const cfg = loadConfig(process.env);            // throws ConfigError listing every problem
checkoutSessionUrl(cfg, "cs_...");              // https://pay.example.com/c/cs_...   (or .../paytrue/c/cs_...)
apiUrl(cfg, "checkout/sessions");               // https://pay.example.com/v1/checkout/sessions
routeOf(cfg, "/paytrue/v1/checkout/sessions");  // "/v1/checkout/sessions", or null outside the base path
cfg.cspFrameAncestors;                          // "'none'" unless you named origins that may embed the checkout
```

### EIP-712 package

Generated from the single source `spec/eip712/types.json` (`node packages/eip712/scripts/build.mjs`; needs Node 22.13+). **The type set is a proposal and no wallet has signed any of it.**

```js
import { hashStruct, domainSeparator, digest, hex, types } from "@paytrue/eip712";

const separator = domainSeparator("mandates", 8453n, "0x...");     // the verifying contract is your deployment's MandateManager
const structHash = hashStruct("RevokeMandate", { /* fields of types.STRUCTS.RevokeMandate */ });
console.log(hex(digest(separator, structHash)));
```

### Development stub

`packages/devserver` implements `POST/GET /v1/checkout/sessions`, cancel, a placeholder hosted page whose buttons **simulate** each outcome, signed webhooks, the framing policy, cookie attributes and the base path.
It has no wallet, no chain, no persistence and no real security; every page says so. It differs from the proposed API in error codes (one `validation_failed`), URL registration (not enforced) and delivery (no retries).

```bash
PAYTRUE_PUBLIC_ORIGIN=http://localhost:8787 PAYTRUE_LISTEN_PORT=8787 PAYTRUE_WEBHOOK_URL=http://127.0.0.1:9000/webhooks node packages/devserver/bin/paytrue-devserver.mjs
```

## Run it under your own domain

The layout is configuration, not code: `PAYTRUE_PUBLIC_ORIGIN` and `PAYTRUE_BASE_PATH` say where PayTrue is, and the helpers build every URL from them. The layouts are exercised by tests against the stub; the proxy files in
[`deploy/proxy/`](deploy/proxy) are **not run** by this repository's checks (run `caddy validate` or `nginx -t` first).

| Layout | Use it when | Settings | Proxy files |
|---|---|---|---|
| **Own subdomain** (recommended) | You can add `pay.example.com`; best isolation | `PAYTRUE_PUBLIC_ORIGIN=https://pay.example.com` `PAYTRUE_BASE_PATH=/` (leave `PAYTRUE_COOKIE_DOMAIN` unset) | [Caddy](deploy/proxy/caddy/subdomain.Caddyfile), [nginx](deploy/proxy/nginx/subdomain.conf) |
| **A path on your domain** | You must stay on `example.com` | `PAYTRUE_PUBLIC_ORIGIN=https://example.com` `PAYTRUE_BASE_PATH=/paytrue` `PAYTRUE_PROXY_STRIPS_BASE_PATH=` `true` if your proxy removes the prefix | [Caddy, prefix kept](deploy/proxy/caddy/same-domain-path.Caddyfile), [Caddy, prefix stripped](deploy/proxy/caddy/same-domain-path-stripped.Caddyfile), [nginx](deploy/proxy/nginx/same-domain-path.conf) |
| **Split hosts** | The merchant API must be private | `PAYTRUE_CHECKOUT_ORIGIN`, `PAYTRUE_CHECKOUT_BASE_PATH`, `PAYTRUE_API_ORIGIN`, `PAYTRUE_API_BASE_PATH` | [Caddy](deploy/proxy/caddy/split-checkout-api.Caddyfile) |
| **Embedded** | Your frontend frames the checkout | The layout above plus `PAYTRUE_ALLOWED_FRAME_ANCESTORS`, cookie settings; see [Embed the checkout](#embed-the-checkout) | |

**The trade-off of a path.** On `https://example.com/paytrue` the checkout shares an origin with everything else on `example.com`: a cross-site-scripting flaw anywhere on that origin can reach the checkout page and its
cookie. The cookie is scoped to the path and `HttpOnly`, but a path is not a security boundary. Use a subdomain when you can.

**Common mistakes.** A proxy that strips the prefix while `PAYTRUE_PROXY_STRIPS_BASE_PATH=false` (or the reverse) makes every request a 404. `PAYTRUE_PUBLIC_ORIGIN` must not contain a path (put it in `PAYTRUE_BASE_PATH`).
Behind a TLS-terminating proxy, give the public `https` origin, whatever the upstream speaks. Setting `PAYTRUE_COOKIE_DOMAIN` to a parent domain widens the cookie to every subdomain.

Guaranteed by the code and tests: URLs come from the origin and base path, never a hard-coded host; a request outside the base path is a 404; cookie `Path`, `Domain`, `SameSite` and `Secure` come from the configuration;
`frame-ancestors` is `'none'` unless you name origins; production refuses http origins, local addresses and a missing origin.

## Embed the checkout

| Way | What you do | State |
|---|---|---|
| **Redirect** (recommended) | Your server creates a session and sends the customer to `session.url`; confirm the result from a signed webhook | Specified; the stub implements a placeholder |
| **Iframe** (experimental) | Your page frames the hosted checkout and listens for a few messages | Experimental; the specification gates embedded checkout separately |
| **Your own payment UI** | You build wallet connection and signing | **Not available**: no wallet-connection layer exists |

Iframe, step by step: (1) **your server** creates the session; the API key never reaches the browser. (2) Set `PAYTRUE_ALLOWED_FRAME_ANCESTORS=https://shop.example.com` (named origins only, `*` is refused); the checkout then sends
`frame-ancestors <your origins>`, otherwise `'none'`. (3) **Your page** frames `buildFrameUrl({ checkoutBaseUrl, sessionId })` with `FRAME_ATTRIBUTES`. (4) It listens with
`acceptEmbedMessage(event, { checkoutOrigin, frameWindow, sessionId })`, which accepts a message only from the exact checkout origin, from the frame your page created, for that session and with an exact shape.

Protocol v1 (a proposal): `ready` (`source: "paytrue-checkout"`, `version: 1`, `sessionId`), `state` (plus the session state), `resize` (plus `height`, 0 to 10000). A message carries no signature, secret or wallet address.
**Never fulfil from a message**: use it for your interface only, and fulfil from a signed webhook.

Verified: `examples/embed-iframe` runs two local origins; in a real browser the allowed origin received `ready` and `state` and another origin was blocked by `frame-ancestors`. **Not verified:** wallet extensions inside a
cross-origin iframe (expect to need a popup or a redirect for signing); third-party cookie behaviour (a `SameSite=Strict` cookie is not sent from a cross-site frame, and `SameSite=None; Secure` is production-only);
a real hosted checkout (none exists).

## Deploy your own contracts

| | Sovereign | Canonical |
|---|---|---|
| Who deploys | **You**, from your account | The PayTrue project |
| Who holds the roles | You: governance (a timelock in production), guardian (stop-only), risk authority, executors, quote signers | The project |
| Exists today | **Yes**: anyone can make one | **No**: none exists and none can be declared before an approved protocol freeze and audits |

The contracts contain **no hard-coded address of a PayTrue party and no URL**: every link is a constructor argument, so a sovereign deployment is the same bytecode with your arguments.
`contracts/script/Deploy.s.sol` deploys one system on one chain and checks that the cyclic links are mutual. The parameters have **no defaults**:

```bash
export PAYTRUE_PERMIT2=0x...            # that chain's Permit2: verify it against spec/evidence/permit2/pin.json
export PAYTRUE_GOVERNANCE=0x...         # a timelock in production
export PAYTRUE_GUARDIAN=0x...           # stop-only
export PAYTRUE_RISK_AUTHORITY=0x...
export PAYTRUE_MAX_QUOTE_TTL=...        # PC-06, immutable ceiling
export PAYTRUE_MAX_BAND_WIDTH_BPS=...   # PC-07, immutable ceiling
export PAYTRUE_QUOTE_SET_GRACE=...      # PC-08
export PAYTRUE_FEE_CEILING_BPS=...      # PC-05: no value is proposed; yours to decide
export PAYTRUE_FEE_BPS=...
export PAYTRUE_FEE_RECIPIENT=0x...
python -I spec/toolchain/forge.py --project contracts script script/Deploy.s.sol:Deploy --sig "run()" --rpc-url "$RPC" --broadcast
```

The earlier `FASTPAY_*` names are still read when the `PAYTRUE_*` one is unset. The constants of PC-05 to PC-08 are **proposals nobody approved**. After the script runs the registries are empty: the router refuses payments until governance
registers a router version, an executor, a merchant, a token with its policy and (for quoted payments) a signer set.

Record what you deployed in a **manifest** and check it with `python -I scripts/validate_deployment.py <file>`; `PAYTRUE_DEPLOYMENT_FILE` points the configuration at it. One manifest is one deployment on one chain:
`schema` (`paytrue.deployment/1`), `kind` (`sovereign` or `canonical`), `label`, `chainId`, `deployedAt`, `permit2`, the 12 `contracts` of a system, the `roles` (`deployer`, `governance`, `guardian`, `riskAuthority`,
`feeRecipient`) and the frozen `compiler` settings. A `canonical` manifest also needs `freezeApproval` and `audits`, which cannot exist today, so the validator refuses it; a `sovereign` one must not claim them.
[`deployments/example-sovereign-31337.json`](deployments/example-sovereign-31337.json) is real output of the local devnet, committed as an example (its addresses mean nothing elsewhere); `deployments/local-*.json` is ignored by Git.

Verified locally only: `python -I scripts/devnet.py --once` starts the pinned anvil, installs Permit2 at its canonical address, runs the script and writes a validated manifest. **No public chain was used.**

Rules for a sovereign operator: use the frozen compiler settings (`contracts/frozen-settings.json`); verify your chain's Permit2 address; keep governance behind a timelock and the guardian stop-only; **there is no upgrade path** (a fix is a
new deployment and a migration, see `spec/12-router-lifecycle-and-migration.md`); the contracts are not audited, so do not put real funds behind a deployment made from this repository today.

## Configuration

Every variable is read by code in this repository (the loader, the stub or the deployment script). **No variable defaults to a PayTrue-hosted service.** `PAYTRUE_ENV=production` is strict: https origins only, no local addresses,
a required public origin, at least two RPC hosts per chain, and no development stub. `.env.example` is generated from the same schema.

<!-- config-reference:start -->
<details>
<summary>Every environment variable (generated from <code>packages/config/src/schema.js</code>; do not edit by hand)</summary>

#### Runtime: where PayTrue is served, which chains and contracts it uses, sessions and webhooks, optional Cloud

| Variable | Default | Required | Description |
|---|---|---|---|
| `PAYTRUE_ENV` | development | no | `development` or `production`. Production requires https origins, at least two RPC URLs per chain, and refuses the development stub. |
| `PAYTRUE_PUBLIC_ORIGIN` | http://localhost:8080 (development only) | production | The origin (scheme, host, optional port) under which the operator serves PayTrue. Never a path. |
| `PAYTRUE_BASE_PATH` | / | no | The path under which PayTrue is mounted on that origin. `/` for a subdomain or a dedicated host, `/paytrue` for a path on an existing site. |
| `PAYTRUE_CHECKOUT_ORIGIN` | PAYTRUE_PUBLIC_ORIGIN | no | The origin that serves the hosted checkout pages. Give it its own origin (a subdomain) when you can: the checkout runs a strict content security policy and no merchant code. |
| `PAYTRUE_CHECKOUT_BASE_PATH` | PAYTRUE_BASE_PATH | no | The path under which the hosted checkout is mounted on its origin. |
| `PAYTRUE_CHECKOUT_ROUTE` | /c | no | The route prefix of a hosted checkout session: `<origin><base path><route>/<session id>`. |
| `PAYTRUE_API_ORIGIN` | PAYTRUE_PUBLIC_ORIGIN | no | The origin of the merchant API, when it is not the public origin. |
| `PAYTRUE_API_BASE_PATH` | PAYTRUE_BASE_PATH | no | The path under which the merchant API (`/v1/...`) is mounted on its origin. |
| `PAYTRUE_PROXY_STRIPS_BASE_PATH` | false | no | `true` when your reverse proxy removes the base path before forwarding, `false` when it forwards the path unchanged. |
| `PAYTRUE_ALLOWED_FRAME_ANCESTORS` | (empty: nobody may embed the checkout) | no | Space- or comma-separated origins that may embed the hosted checkout in an iframe. Empty means `frame-ancestors 'none'`. Embedded checkout is separately gated in the specification. |
| `PAYTRUE_COOKIE_DOMAIN` | (unset: host-only cookie) | no | Cookie domain for the checkout control cookie. Leave unset for a host-only cookie. When set it must be the checkout host or a parent domain of it. |
| `PAYTRUE_COOKIE_PATH` | PAYTRUE_CHECKOUT_BASE_PATH | no | Cookie path of the checkout control cookie. |
| `PAYTRUE_COOKIE_SAMESITE` | strict | no | `strict`, `lax` or `none`. `none` is needed only for a cross-site embed and requires production with https. |
| `PAYTRUE_CHAIN_IDS` | 31337 (development only) | production | Comma-separated chain ids this deployment accepts payments on. |
| `PAYTRUE_RPC_URLS_<chainId>` | http://127.0.0.1:8545 for 31337 (development only) | production, for every chain id | Comma-separated RPC URLs of one chain. Production needs at least two distinct hosts: a money decision rests on two independent sources. |
| `PAYTRUE_DEPLOYMENT_FILE` | deployments/local-31337.json (development only) | production | The deployment manifest (README, section Deploy your own contracts) that names the contract addresses of your own deployment. PayTrue ships no canonical addresses. |
| `PAYTRUE_SESSION_LIFETIME_MIN_SECONDS` | 600 | no | Minimum session lifetime a merchant may request. A proposal (record CSR-01); not an approved constant. |
| `PAYTRUE_SESSION_LIFETIME_DEFAULT_SECONDS` | 1800 | no | Session lifetime when a request gives none (30 minutes). |
| `PAYTRUE_SESSION_LIFETIME_MAX_SECONDS` | 86400 | no | Maximum session lifetime a merchant may request. |
| `PAYTRUE_WEBHOOK_SECRET` (secret) | none | no | The signing secret of your webhook endpoint. Never commit it. |
| `PAYTRUE_WEBHOOK_TOLERANCE_SECONDS` | 300 | no | How far a webhook timestamp may differ from the receiver's clock before the event is rejected as a replay. A proposal. |
| `PAYTRUE_API_KEY` (secret) | none | no | The merchant API key used by the SDK and the examples. Never commit it. |
| `PAYTRUE_CLOUD_ENABLED` | false | no | PayTrue Cloud is optional and off by default. Nothing in this repository requires it. |
| `PAYTRUE_CLOUD_BASE_URL` | none | PAYTRUE_CLOUD_ENABLED=true | The base URL of a PayTrue Cloud API. There is no default: the repository never assumes a hosted service. |

#### Development stub (packages/devserver): never used in production

| Variable | Default | Required | Description |
|---|---|---|---|
| `PAYTRUE_LISTEN_HOST` | 127.0.0.1 | no | Interface the development stub listens on. |
| `PAYTRUE_LISTEN_PORT` | 8080 | no | Port the development stub listens on. |
| `PAYTRUE_WEBHOOK_URL` | none | no | Where the development stub delivers signed webhook events (for the examples and tests). |

#### Contract deployment (contracts/script/Deploy.s.sol); a legacy FASTPAY_* name is read when the PAYTRUE_* one is unset

| Variable | Default | Required | Description |
|---|---|---|---|
| `PAYTRUE_PERMIT2` | none | deploying | The Permit2 contract of the chain. |
| `PAYTRUE_GOVERNANCE` | none | deploying | The governance address. A timelock in production. |
| `PAYTRUE_GUARDIAN` | none | deploying | The guardian address (stop-only). |
| `PAYTRUE_RISK_AUTHORITY` | none | deploying | The pause authority of the mandate manager. |
| `PAYTRUE_MAX_QUOTE_TTL` | none | deploying | Immutable ceiling of a quote's life, in seconds (PC-06). |
| `PAYTRUE_MAX_BAND_WIDTH_BPS` | none | deploying | Immutable ceiling of a price band, in basis points (PC-07). |
| `PAYTRUE_QUOTE_SET_GRACE` | none | deploying | Grace of quotes issued before a signer-set rotation, in seconds (PC-08). |
| `PAYTRUE_FEE_CEILING_BPS` | none | deploying | Immutable fee ceiling in basis points. No value is proposed (PC-05). |
| `PAYTRUE_FEE_BPS` | none | deploying | The initial fee, at most the ceiling. |
| `PAYTRUE_FEE_RECIPIENT` | none | deploying | The fee recipient. |

</details>
<!-- config-reference:end -->

## PayTrue Cloud is optional

PayTrue Cloud, as a hosted service, **does not exist** in this repository: no Cloud code, no Cloud client with a built-in address, no Cloud-only feature. The boundary is enforced so that none can become a dependency by accident:
`PAYTRUE_CLOUD_ENABLED` defaults to `false`; with it on, `PAYTRUE_CLOUD_BASE_URL` is required and has no fallback; the SDK has no default `baseUrl`; the contracts name no PayTrue party; no telemetry exists; and
`scripts/repo_hygiene.py` fails if code, deployment files or examples name a PayTrue-hosted domain. A Cloud, if ever built, would be a separate component and the same SDK pointed at a different `baseUrl`. Pricing, availability
and parity with self-hosting are **not** promised.

## Production

**PayTrue is not ready for production**, and nothing here describes a deployment you can make today. `python -I spec/tools/freeze_readiness.py` prints **NOT READY, 1 of 11 conditions met**.

| Blocker | State |
|---|---|
| Protocol freeze | Not approved: wallet-lab evidence (0 of 10 run sets), Permit2 review, approval of the 19 production-blocking constants (0 of 19), planner implementations, audits and sign-offs are all open |
| Audits | None |
| Wallets | No wallet has been tested; every statement about a wallet or WalletConnect is unverified |
| Payment service | Does not exist: no hosted checkout with a wallet connection, no executor, reconciliation, ledger or risk engine |
| Chains | Gas figures use the compiler's EVM schedule, not each chain's accounting; the per-transaction gas cap is an assumption |
| Legal | Licensing of the operator, KYB, consumer-protection and sanctions questions are the operator's and open |

The shape the specification aims at, once the service exists: the checkout on its own subdomain and the merchant API on a private host; your TLS and a strict content security policy with no third-party script;
two or more independent RPC hosts per chain; a sovereign contract deployment with governance behind a timelock and separate executor and quote-signer keys in a key-management system; secrets in a secret store; webhooks through an
egress proxy; alerts on unresolved `unknown` sessions; runbooks, backups and an on-call owner. Before a first real deployment: freeze approved, two audits closed, wallet-lab evidence for every wallet you claim, the 19 constants
approved, a payment service that passed the acceptance criteria of `spec/19-checkout-session-and-wallet-connect-profile.md` on a testnet, a penetration test, a recovery drill, and counsel's review.

## Security

Do **not** open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md) for scope and for GitHub's private reporting.

## Contributing

Open an issue first for a large change: the specification (`spec/`) is the source of truth and a protocol rule changes there first. Contributions are accepted under Apache-2.0 (inbound = outbound, no CLA). Be respectful: harassment
and personal attacks are not tolerated, and the maintainer may remove content and contributors that break this. To report a conduct problem, open an issue titled "Conduct" with no details; the owner will arrange a private channel (no private contact is published yet).

Before a pull request (CI is provided in `.github/workflows` and has not run yet, so run them yourself):

```bash
python -I scripts/repo_hygiene.py --history             # sizes, secrets, SPDX headers, vendored trees, encodings, protected identifiers, packages
python -I scripts/test_repo_hygiene.py                  # the checker itself still fails on what it should catch
python -I scripts/check_docs.py                         # relative links in the Markdown files
node --test "packages/config/test/*.test.mjs" "packages/sdk/test/*.test.mjs" "packages/eip712/test/*.test.mjs" "packages/devserver/test/*.test.mjs"
node packages/config/scripts/generate-env-example.mjs --check       # .env.example matches the schema
node packages/config/scripts/generate-config-doc.mjs --check        # the configuration table in this README matches the schema
python -I spec/toolchain/forge.py --project contracts test          # when you touched contracts/
python -I spec/toolchain/forge.py --project contracts build         # check 18 compares this build with the recorded report, so build first
python -I spec/tools/check_all.py                                   # when you touched spec/, contracts/ or evidence (21 checks)
```

| Rule | Why |
|---|---|
| Generated files are never edited by hand: the EIP-712 outputs (`spec/eip712/types.json` is the one source, `python -I spec/tools/export_eip712.py --write`), `.env.example` and the configuration table above (from `packages/config/src/schema.js`), `spec/18-configuration-records.md` | The checks fail when one is stale |
| The EIP-712 domain names (`FastPay Mandates`, `FastPay Quote`), the hashed tags (`fastpay.*.v1`) and the wallet-lab signing prefix are **protected**: never rename them, not even to rename the product | Each is a new domain or tag version, regenerated everywhere and re-approved; the hygiene check fails if one disappears |
| Contract compiler settings are frozen; no `delegatecall`, `selfdestruct`, `tx.origin`, `create`, `create2` in a runtime; every loop has a stated bound; every Solidity file starts with `// SPDX-License-Identifier: Apache-2.0` | See `contracts/README.md` |
| No secret, `.env`, binary, archive, build output or file over 20 MiB; text is UTF-8 without a byte-order mark, stored with LF | The hygiene check and `.gitattributes` enforce it |
| Never add wallet-lab evidence yourself, and never claim a wallet works, a chain is supported, a component is audited or a constant approved without the evidence the specification requires | Approvals are given by named people in the records, never by a tool or an assistant |
| No new dependency in the packages (they have none); a copyleft or unlicensed dependency is refused | Keeps the license clean |

The toolchain is pinned in `spec/toolchain/toolchain.lock.json` and fetched with SHA-256 verification. Windows is where the checks were developed; Linux and macOS are expected to work but **the Linux path has not been verified**.

**Governance and support.** One owner and maintainer, [@MohAsadi](https://github.com/MohAsadi); no foundation, no commercial support, no service-level agreement. Code and documentation changes need a maintainer's approval and the checks above;
a protocol rule, a constant or an EIP-712 fingerprint is an approval that only a named human can give, in the record the specification defines; a passing check is never an approval. Report bugs and ask questions in issues; for a
vulnerability use [SECURITY.md](SECURITY.md).

## License, third-party code and the name

**Apache License 2.0** ([LICENSE](LICENSE)): you may use, modify, host and sell services built on this code without asking. This is a default chosen by the maintainer's tooling and **awaits the owner's confirmation**; this is
engineering due diligence, not legal advice.

| Third-party material | License | Relation to PayTrue |
|---|---|---|
| `spec/foundry/lib/forge-std` (the only third-party source tracked) | MIT OR Apache-2.0 | Test and script library; its license files are in the tree |
| Foundry, solc (GPL-3.0 compiler binary), Permit2, solmate (AGPL-3.0-only), ds-test (GPL-3.0-or-later), OpenZeppelin | Their own | Fetched by the pinned toolchain, **not tracked and not redistributed**; no copyleft source is part of a PayTrue runtime, package or image |
| Compiled Permit2 in `spec/evidence/permit2/` (test fixture and byte-equality evidence) | MIT, but its build links solmate (AGPL-3.0-only) | **Needs counsel's confirmation** that keeping it in a public repository is acceptable, or a decision to fetch it at test time |

The contracts import no third-party source and call Permit2 through PayTrue's own interface; the packages have no runtime dependencies. Earlier Git commits still contain the Permit2 dependency trees that are no longer tracked; history was not rewritten.

**The name.** "PayTrue" is not licensed by Apache-2.0 and **has not been cleared**: no trademark registration or search has been done. You may say your product is built on or compatible with PayTrue, refer to the project, and
distribute unmodified copies. Do not use the name (or "PayTrue Cloud") as the name of your own company, product, service, token or domain, do not distribute a modified version under it, and do not call a deployment of yours
official, canonical, audited or certified: no canonical deployment exists, and yours is a sovereign one. The specification and the EIP-712 identifiers still use the working name **FastPay**; renaming them is a decision for the
owner, and the protected identifiers above must not be renamed blindly.

## Known gaps

No production payment service; nothing audited; the protocol not frozen; no wallet tested. Not run: the Caddy and nginx files, the Dockerfiles, the GitHub workflows and the Linux toolchain path. Not done by the owner yet:
confirm the license; clear the name and the `@paytrue` npm scope; enable GitHub private vulnerability reporting, branch protection with code-owner review, secret scanning and push protection; pin Actions and base images by digest;
publish a contact for conduct and security reports.
