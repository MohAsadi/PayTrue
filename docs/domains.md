# Domains and layouts

The same software runs under a path of a domain you already serve, under your own subdomain, or split over several hosts. The layout is configuration, not code:
`PAYTRUE_PUBLIC_ORIGIN` and `PAYTRUE_BASE_PATH` say where it is, and the SDK's URL helpers build every link from them. Every layout below is **exercised by tests**
(`packages/devserver/test`, `packages/config/test`) against the development stub; the proxy files in `deploy/proxy/` are **not run** by this repository's checks.

## Choosing

| Layout | Use it when | Isolation | Settings |
|---|---|---|---|
| **B. Own subdomain** (recommended) | You can add `pay.example.com` | Best: the hosted checkout has an origin of its own | `PAYTRUE_PUBLIC_ORIGIN=https://pay.example.com`, `PAYTRUE_BASE_PATH=/` |
| **A. A path on your domain** | You must stay on `example.com` | Weaker: see below | `PAYTRUE_PUBLIC_ORIGIN=https://example.com`, `PAYTRUE_BASE_PATH=/paytrue`, `PAYTRUE_PROXY_STRIPS_BASE_PATH` as your proxy does |
| **C. Split hosts** | The merchant API must be private, or on a different network | Good: the browser never talks to the API | `PAYTRUE_CHECKOUT_ORIGIN`, `PAYTRUE_CHECKOUT_BASE_PATH`, `PAYTRUE_API_ORIGIN`, `PAYTRUE_API_BASE_PATH` |
| **D. Embedded** | Your frontend frames the hosted checkout | As the layout it is built on, plus the framing rules of [embedding](embedding.md) | `PAYTRUE_ALLOWED_FRAME_ANCESTORS`, cookie settings |

## Layout A: a path on a domain you already serve

```text
PAYTRUE_PUBLIC_ORIGIN=https://example.com
PAYTRUE_BASE_PATH=/paytrue
PAYTRUE_PROXY_STRIPS_BASE_PATH=false     # true when your proxy removes /paytrue before forwarding
```

URLs: `https://example.com/paytrue/c/<session id>` (hosted checkout) and `https://example.com/paytrue/v1/checkout/sessions` (merchant API). Proxy files:
[`same-domain-path.Caddyfile`](../deploy/proxy/caddy/same-domain-path.Caddyfile), [`same-domain-path-stripped.Caddyfile`](../deploy/proxy/caddy/same-domain-path-stripped.Caddyfile),
[`same-domain-path.conf`](../deploy/proxy/nginx/same-domain-path.conf) (nginx).

**The trade-off you accept.** The hosted checkout runs under a strict content security policy and no merchant code is meant to run in its origin. On a path of `example.com` it shares an
origin with everything else on `example.com`: a cross-site-scripting flaw anywhere on that origin can reach the checkout page and its cookie, and the cookies of your own site are sent to
`/paytrue`. The cookie is scoped to the base path (`PAYTRUE_COOKIE_PATH`) and is `HttpOnly`, but a path is not a security boundary. Use layout B when you can.

## Layout B: your own subdomain

```text
PAYTRUE_PUBLIC_ORIGIN=https://pay.example.com
PAYTRUE_BASE_PATH=/
```

URLs: `https://pay.example.com/c/<session id>` and `https://pay.example.com/v1/checkout/sessions`. Proxy files: [`subdomain.Caddyfile`](../deploy/proxy/caddy/subdomain.Caddyfile),
[`subdomain.conf`](../deploy/proxy/nginx/subdomain.conf). Leave `PAYTRUE_COOKIE_DOMAIN` unset so the cookie is host-only.

## Layout C: split hosts

```text
PAYTRUE_CHECKOUT_ORIGIN=https://checkout.example.com    PAYTRUE_CHECKOUT_BASE_PATH=/
PAYTRUE_API_ORIGIN=https://api.example.com              PAYTRUE_API_BASE_PATH=/payments
```

The hosted pages are reachable on the checkout host only; the merchant API on the API host only, ideally restricted to your own servers (it is called server to server, so it needs no CORS).
Proxy file: [`split-checkout-api.Caddyfile`](../deploy/proxy/caddy/split-checkout-api.Caddyfile). The SDK takes the API root as `baseUrl`:
`new PayTrueClient({ baseUrl: "https://api.example.com/payments", apiKey })`.

## What the code guarantees for every layout

| Property | Where it is tested |
|---|---|
| URLs are built from the origin and base path (`checkoutSessionUrl`, `apiUrl`), never from a hard-coded host | `packages/config/test`, `packages/devserver/test` ("path layout", "split layout") |
| A request outside the base path gets a 404, and a request without the prefix does too (unless the proxy strips it) | "path layout", "a proxy that strips the base path" |
| The control cookie's `Path`, `Domain`, `SameSite` and `Secure` come from the configuration | `packages/config/test` (cookie), `packages/devserver/test` ("the hosted page") |
| The checkout's `frame-ancestors` is `'none'` unless you name origins | "default frame policy forbids embedding" |
| Production refuses http origins, local addresses and a missing origin | `packages/config/test` |

## Common mistakes

| Mistake | Effect |
|---|---|
| `PAYTRUE_BASE_PATH=/paytrue/` | Harmless: the trailing slash is normalised to `/paytrue` |
| The proxy strips the prefix and `PAYTRUE_PROXY_STRIPS_BASE_PATH` is `false` | Every request is a 404 |
| The proxy keeps the prefix and `PAYTRUE_PROXY_STRIPS_BASE_PATH` is `true` | The prefix is not removed by the application: also a 404 |
| `PAYTRUE_PUBLIC_ORIGIN` includes a path | Refused at start: put the path in `PAYTRUE_BASE_PATH` |
| Terminating TLS in front of the application but giving it an `http` origin | Production refuses `http`: give the public `https` origin, whatever the upstream speaks |
| `PAYTRUE_COOKIE_DOMAIN` set to a parent domain "to be safe" | Widens the cookie to every subdomain: leave it unset |
