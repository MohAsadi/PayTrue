# PayTrue Cloud: the optional boundary

**PayTrue Cloud is optional. Nothing in this repository requires it, calls it, or defaults to it.** This page defines what "optional" means and how the repository enforces it.

## State

PayTrue Cloud, as a hosted service, **does not exist** in this repository. There is no Cloud code, no Cloud API client with a built-in address, no Cloud account flow and no Cloud-only feature.
The specification describes a "control plane" for a hosted deployment; it is a design, not an offering. This page defines the boundary so that, if a Cloud is ever built, it cannot become a dependency
by accident. **Nothing here describes Cloud functionality that exists.**

## The rules

| # | Rule | How it is enforced today |
|---|---|---|
| 1 | The open-source code runs with Cloud off, and off is the default | `PAYTRUE_CLOUD_ENABLED` defaults to `false` (`packages/config`, tested) |
| 2 | There is **no default Cloud address** anywhere | The loader requires `PAYTRUE_CLOUD_BASE_URL` when Cloud is enabled and has no fallback; the SDK has no default `baseUrl` (tested) |
| 3 | No code, deployment file or example names a PayTrue-hosted domain | `scripts/repo_hygiene.py` (hosts) fails on `paytrue.(me|com|io|app|dev|cloud)` in `packages/`, `deploy/`, `examples/`, `contracts/`, `scripts/`; the package tests check their own sources |
| 4 | Turning Cloud on is an explicit, reversible configuration choice | Two variables; unset them and Cloud is off |
| 5 | The contracts know nothing about Cloud | No address, URL or role in the contracts names a PayTrue party ([contract deployments](contracts-deployments.md)) |
| 6 | No telemetry | None exists in the packages; none may be added without a documented opt-in |
| 7 | A Cloud service, if built, is a **separate component** with its own license decision, kept outside `contracts/`, `packages/` and `spec/` (a dedicated directory or repository) | Convention; the hygiene check on hosted domains protects the open-source directories |
| 8 | A merchant can leave Cloud for self-hosting without changing the contracts or the types | Same API, same SDK, same manifests: only `baseUrl` and the secrets change |

## What using Cloud would look like

```js
const client = new PayTrueClient({ baseUrl: "<the Cloud API root your account gives you>", apiKey: process.env.PAYTRUE_API_KEY });
```

and, in configuration, `PAYTRUE_CLOUD_ENABLED=true` with `PAYTRUE_CLOUD_BASE_URL=<that address>`. It is the same SDK pointed at a different `baseUrl`.

## Not promised

Feature parity between Cloud and a self-hosted deployment, pricing, availability, support terms and data-processing terms are **not** defined here. They would belong to the terms of a Cloud service, which
does not exist. The trademark policy ([TRADEMARK](../TRADEMARK.md)) reserves the name "PayTrue Cloud" for a service operated by the project.
