# PayTrue under a path of a site you already serve

Goal: `https://example.com/paytrue/...` serves PayTrue while the rest of `example.com` stays yours. **Read the trade-off first** ([domains](../../docs/domains.md), layout A): the checkout then shares an origin
with your site. Your own subdomain is safer.

1. Run the service. For a trial, the development stub:
   ```bash
   PAYTRUE_PUBLIC_ORIGIN=https://example.com PAYTRUE_BASE_PATH=/paytrue PAYTRUE_LISTEN_PORT=8787 node packages/devserver/bin/paytrue-devserver.mjs
   ```
   (Use a free port; some systems reserve 8080.)
2. Put a reverse proxy in front. Choose the variant that matches how it forwards the prefix:
   - keeps `/paytrue`: [`same-domain-path.Caddyfile`](../../deploy/proxy/caddy/same-domain-path.Caddyfile) or the first block of [`same-domain-path.conf`](../../deploy/proxy/nginx/same-domain-path.conf), with `PAYTRUE_PROXY_STRIPS_BASE_PATH=false`;
   - strips `/paytrue`: [`same-domain-path-stripped.Caddyfile`](../../deploy/proxy/caddy/same-domain-path-stripped.Caddyfile), with `PAYTRUE_PROXY_STRIPS_BASE_PATH=true`.
3. Point your SDK at the API root:
   ```js
   new PayTrueClient({ baseUrl: "https://example.com/paytrue", apiKey: process.env.PAYTRUE_API_KEY });
   ```
   Sessions come back with `url` values such as `https://example.com/paytrue/c/cs_...`.

What is verified: the application side, with and without a stripping proxy (`packages/devserver/test`: "path layout", "a proxy that strips the base path"). What is **not**: the Caddy and nginx files, which this
repository's checks do not run. Validate them with `caddy validate` or `nginx -t` before use.
