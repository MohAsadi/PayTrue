# Packages and releases

## Package boundaries

| Package | Purpose | Runtime dependencies | Runs on | Published |
|---|---|---|---|---|
| `@paytrue/config` | Environment validation and URL derivation for any layout | none | Node 20+ | **No** (`"private": true`) |
| `@paytrue/sdk` | API client, webhook verification and ordering, embedding helpers (`@paytrue/sdk/embed`, browser-safe) | none | Node 18+ (client and webhooks), any browser (embed) | **No** |
| `@paytrue/eip712` | The EIP-712 encoder, built from `spec/eip712`; the type definitions, golden vectors and wallet payloads | none | Node 18+; **building** it needs Node 22.13+ | **No** |
| `@paytrue/devserver` | The development stub | none (imports its sibling packages by path) | Node 20+ | **Never**: it is not a payment server |
| `contracts/` | The Solidity contracts | forge-std (tests and the deployment script) | Foundry, solc 0.8.24 | Not as a package |

**The rules of the boundary**

1. A package has **no runtime dependency**. Adding one needs a row in `THIRD_PARTY_NOTICES.md` and a change to the hygiene policy first (`scripts/repo_hygiene.py` fails otherwise).
2. A package names **no PayTrue-hosted service**, and its defaults point at nothing hosted.
3. `@paytrue/eip712` is **generated from one source** (`spec/eip712/types.json`): its build copies and strips types; it does not fork the code. A change to the types is made there, never in the package.
4. The SDK targets the **proposed** API of `spec/checkout/`. Until the API is approved, every release of the SDK is `0.x` and may change.
5. The development stub imports `@paytrue/config` and `@paytrue/sdk` by relative path; it is not meant to be installed.

## Versioning

| Thing | Version | Rule |
|---|---|---|
| Packages | `0.x.y` while the protocol is a proposal | Semantic versioning; before `1.0.0` any minor version may break |
| The protocol (types, domains) | The `version` of each EIP-712 domain (`"1"`) | A change to a type string, a domain name, the snapshot encoding or a tag is a **new domain version**, deployed as new contracts (`spec/eip712/types.json`, rules V1 to V6) |
| The API | A date (`2026-10-17`) in the `PayTrue-Version` header and in every event | Proposed; not frozen |
| The specification | `0.5.0` (draft) | Changes recorded in `spec/CHANGELOG.md` |
| Contract deployments | One manifest per deployment | A new bytecode is a new deployment |

## Publishing readiness

| Item | State |
|---|---|
| `license`, `repository`, `bugs`, `exports`, `files`, `engines`, `description` in every `package.json` | Done, checked by `scripts/repo_hygiene.py` |
| Type declarations | Hand-written for `config`, `sdk`, `eip712` |
| Package contents | `npm pack --dry-run` lists only `src` (or `dist`) and the README for each package |
| Tests | Node's built-in runner, no dependency; run by CI |
| Dependency-free policy | Enforced |
| **npm scope `@paytrue`** | **Not verified**: availability and ownership of the scope are unchecked |
| npm account, two-factor authentication, provenance | **Not set up.** Provenance (`npm publish --provenance`) needs a GitHub Actions publisher |
| `"private": true` | Present on every package as a guard; remove it, one package at a time, when a release is approved |
| Trademark | The name "PayTrue" has not been cleared ([TRADEMARK](../TRADEMARK.md)) |

**No package has been published and no container image has been published.** Nothing in the repository does it by itself.

## How a release is made

1. A maintainer opens a release pull request: version bumps, `spec/CHANGELOG.md` entry, and `python -I scripts/repo_hygiene.py --history` green.
2. After merge, a tag `vX.Y.Z` triggers `.github/workflows/release.yml`, which re-runs the checks, packs every package (`npm pack`) and attaches the tarballs and their SHA-256 sums to a **draft** GitHub release.
3. A maintainer reviews the draft and publishes it.
4. Publishing to npm is a separate, gated job that is **off** unless the repository variable `PAYTRUE_ENABLE_NPM_PUBLISH` is `true`, and it runs in the protected environment `npm-publish`
   (manual approval, the npm token as an environment secret). Because the packages are `private`, it would fail anyway until a maintainer removes the flag.

## Container images

`deploy/docker/` holds two Dockerfiles for local development. Neither is for production, neither is published, and both name a base image **by tag**: pin it by digest in your own build.
