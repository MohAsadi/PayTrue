# deploy

Deployment aids for **your own** infrastructure. Nothing here points at a PayTrue-hosted service, and nothing here is for production today: the payment service these files will front does not exist
yet ([production deployment](../docs/production-deployment.md)).

| Path | What | Verified |
|---|---|---|
| `proxy/caddy/*.Caddyfile` | A path on an existing domain (prefix kept or stripped), your own subdomain, split checkout and API hosts | **Not run** by this repository's checks: `caddy validate` before use |
| `proxy/nginx/*.conf` | The path and subdomain layouts for nginx | **Not run**: `nginx -t` before use |
| `docker/Dockerfile.devserver` | The development stub as a container (non-root, health check) | Not built by this repository's checks |
| `docker/Dockerfile.devnet` | A local devnet with the **pinned** toolchain fetched at build time | Not built by this repository's checks |
| `compose/compose.yaml` | The two services above, published on `127.0.0.1` only | `docker compose config` passes (validated offline) |

What the layouts mean and their trade-offs: [domains](../docs/domains.md). The settings each layout needs: [configuration](../docs/configuration.md).

**No image is published** by this repository, and the Dockerfiles name their base images by tag: pin them by digest in your own build. The compose file reads `PAYTRUE_DEVSERVER_PORT` and
`PAYTRUE_DEVNET_PORT` so that a reserved or busy host port is not a blocker.
