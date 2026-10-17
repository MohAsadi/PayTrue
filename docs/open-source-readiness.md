# Open-source readiness

State of the repository as an open-source project on **2026-10-17**, on the branch `oss/productization`. It records the gap analysis made **before** any file was changed (the "Before" column),
what this change did, and what is left (the "After" column and the blockers). It is a status report, not a claim: nothing in this repository is audited, the protocol freeze is not approved,
no wallet has been tested and **no production payment service exists**.

Status words: **COMPLETE** (nothing left that an engineer can do), **PARTIAL** (works, with named gaps), **SPECIFIED_ONLY** (a document defines it, no code), **NOT_IMPLEMENTED**, **BLOCKED**
(needs a decision or an action that only the owner, counsel or a third party can give).

## The answer in six lines

| Question | Answer today |
|---|---|
| Can it be used from GitHub by other developers? | **Yes, as libraries and contracts**: a license (Apache-2.0, **to be confirmed by the owner**), three dependency-free packages, a deployment script and a local devnet. **Not** as a payment service |
| Can it be self-hosted? | **Partly.** Contracts: yes, on a chain you choose. Integration environment: yes (development stub). A payment service that takes customer money: **does not exist** |
| Does it need `paytrue.me`? | **No.** No code, deployment file or example names a PayTrue-hosted domain; a check fails if one appears |
| Under a path, a subdomain, embedded, headless? | Configuration, SDK and stub support all four and are tested; the proxy files are **not run**; embedding is **experimental** and was verified with the stub in one browser only |
| Is PayTrue Cloud optional? | **Yes**, trivially: no Cloud code exists, nothing needs it, and the configuration refuses to enable it without an explicit URL |
| Is it production-ready? | **No** ([production deployment](production-deployment.md)) |

## Gap analysis, category by category

| # | Category | Before | After | What changed, and what is left |
|---|---|---|---|---|
| 1 | Repository architecture | PARTIAL | PARTIAL | `packages/`, `deploy/`, `deployments/`, `examples/`, `docs/`, `scripts/` now exist and [architecture](architecture.md) maps them. **Left:** the contracts' tests read vectors, the Permit2 fixture and forge-std from `spec/`, so `contracts/` is not standalone |
| 2 | Self-hosting | NOT_IMPLEMENTED | PARTIAL | [Self-hosting](self-hosting.md) defines four levels. Levels 0 to 2 (libraries, sovereign contracts, integration environment) work and are tested. **Left (blocker):** level 3, a production checkout service, is specified and not built |
| 3 | Operator-controlled domains | NOT_IMPLEMENTED | PARTIAL | Origin, base path, cookie and frame settings in `@paytrue/config`; layouts in [domains](domains.md); Caddy and nginx files. **Left:** the proxy files are authored, not run; the application side is tested |
| 4 | Headless use | SPECIFIED_ONLY | PARTIAL | `@paytrue/sdk` client, signed-webhook verification, deduplication and ordering; runnable example ([headless](headless.md)). **Left:** it targets a *proposed* API, exercised only against the stub |
| 5 | Embedded checkout | SPECIFIED_ONLY | PARTIAL | Frame-ancestors handling, an origin-checked message protocol, an example that was run in a real browser with a positive and a negative case ([embedding](embedding.md)). **Left:** **experimental**; real wallets, WalletConnect and embedded wallets inside a cross-origin frame are unverified; the protocol is not frozen |
| 6 | Package boundaries | NOT_IMPLEMENTED | PARTIAL | Four packages with rules (no dependency, no hosted default, generated encoder), enforced by the hygiene check ([packages](packages-and-releases.md)). **Left:** the contracts are not consumable as a package (see 1) |
| 7 | Configuration and environment | PARTIAL | PARTIAL | One schema, a validating loader, a generated `.env.example` and [configuration reference](configuration.md), a deployment script that reads `PAYTRUE_*` and still accepts the legacy `FASTPAY_*`. **Left:** the fork-evidence tools read their public RPC providers from the Permit2 pin record and cannot be redirected by an environment variable |
| 8 | License and dependency compatibility | BLOCKED | PARTIAL | Apache-2.0 adopted as a **default**; 90 Solidity files relabelled (bytecode-neutral, 290 tests unchanged); AGPL and GPL trees untracked; [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) and [licensing](licensing.md). **Left:** the owner must confirm the license; **L-1** (compiled Permit2 fixture links AGPL code) needs counsel; history still contains the untracked trees |
| 9 | Trademark policy | NOT_IMPLEMENTED | PARTIAL | [TRADEMARK](../TRADEMARK.md): what is allowed, what is not. **Left (blocked):** clearance of the name "PayTrue" has not been done and cannot be done by an engineer |
| 10 | Canonical versus sovereign deployments | PARTIAL | PARTIAL | Manifest format `paytrue.deployment/1`, validator, example, [contract deployments](contracts-deployments.md), a deployment script free of PayTrue addresses, a local end-to-end run on anvil. **Left:** no public-chain deployment was tested; a canonical deployment is blocked by the freeze and two audits |
| 11 | Docker and local quickstart | NOT_IMPLEMENTED | PARTIAL | A compose file (validated offline), two Dockerfiles, and a devnet quickstart that was run end to end without Docker ([getting started](getting-started.md)). **Left:** no image was built or pulled; base images are named by tag, not by digest |
| 12 | Production deployment docs | NOT_IMPLEMENTED | PARTIAL | [Production deployment](production-deployment.md): what must be true before money moves, a reference topology, the known gaps. **Left:** it describes a service that does not exist, and says so |
| 13 | Public examples | NOT_IMPLEMENTED | PARTIAL | [Four examples](../examples/README.md); the headless and sovereign-deploy examples run; the embedding example was browser-verified. **Left:** the same-domain example is documentation only |
| 14 | GitHub community files | NOT_IMPLEMENTED | COMPLETE | Issue forms, template chooser, pull-request template, CODEOWNERS, Dependabot. **Owner actions:** turn on the settings listed below |
| 15 | SECURITY.md and vulnerability reporting | NOT_IMPLEMENTED | PARTIAL | [SECURITY](../SECURITY.md): scope, process, safe harbour wording, what is out of scope today. **Left (owner):** private vulnerability reporting must be enabled on GitHub, and a backup contact published |
| 16 | Public, private and generated evidence | PARTIAL | COMPLETE | [Evidence policy](evidence-policy.md): three classes, raw wallet-lab artifacts ignored by Git and refused by the hygiene check, generated runs untracked. The wallet-lab *record* stays public once signed |
| 17 | Large-file hygiene | PARTIAL | PARTIAL | A size guard (warns at 20 MiB, fails at 50 MiB) in the hygiene check and in CI; 21 MB of vendored copies untracked. **Left:** one generated log is 47.3 MiB and still tracked (it warns); shrinking it needs the evidence tools to read a compressed form |
| 18 | Secret scanning | PARTIAL | PARTIAL | A scanner for the tree and for the whole Git history (4 commits: clean), run in CI, with tests that it fails on what it should. **Left (owner):** GitHub secret scanning and push protection are repository settings; the scanner is a set of patterns, not a replacement for them |
| 19 | CI and release workflows | NOT_IMPLEMENTED | PARTIAL | `ci.yml` (hygiene, packages on Node 20 and 22, compose, contracts, specification) and `release.yml` (checks, pack, **draft** release, gated npm job). **Left:** no workflow has run on GitHub; the contracts and specification jobs use the Linux toolchain path the maintainers have not exercised and are marked advisory |
| 20 | README and public documentation | PARTIAL | COMPLETE | A new [README](../README.md), the [documentation index](README.md), 15 documents, a link checker run in CI. Every document states what is not done |
| 21 | Branding and rename impact | NOT_IMPLEMENTED | PARTIAL | [Rename impact](rename-impact.md) counts every use of "FastPay" and sorts it into seven classes (A to G), each with a rule and a "renamed now?" answer; environment variables, SDK headers and package names are renamed, cryptographic identifiers and specification prose are not. **Left:** the specification and the `spec/checkout` catalogs still use the working name `FastPay` (including the `FastPay-*` header names in the catalogs); that is a decision for the owner |
| 22 | Cryptographic identifiers not to be renamed | PARTIAL | COMPLETE | 11 protected identifiers (EIP-712 domain names, hashed tags, the wallet-lab signing prefix) are listed, and the hygiene check fails if one disappears; tests prove it |
| 23 | Optional PayTrue Cloud separation | NOT_IMPLEMENTED | COMPLETE | [Cloud boundary](cloud-boundary.md): nothing requires Cloud; the loader has no default Cloud URL and refuses to enable Cloud without one. *Cloud itself does not exist and is not simulated.* |
| 24 | Package publishing readiness | NOT_IMPLEMENTED | PARTIAL | Manifests, types, `files`, `exports`, `engines`, `npm pack --dry-run` in CI, a draft-only release path, `"private": true` as a guard. **Left (blocked):** the `@paytrue` npm scope, account, two-factor authentication and provenance publisher are unverified or not set up; the name is not cleared |
| 25 | External contributor readiness | PARTIAL | PARTIAL | [CONTRIBUTING](../CONTRIBUTING.md), [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md), [GOVERNANCE](../GOVERNANCE.md), [SUPPORT](../SUPPORT.md), one command list that CI also runs. A fresh Windows clone was run through every check (see below). **Left:** the Linux toolchain path is unverified; the toolchain download itself was not re-run in the clone; a conduct-reporting contact is not published |

Totals after this change: **5 COMPLETE, 20 PARTIAL, 0 BLOCKED as a whole, 0 SPECIFIED_ONLY, 0 NOT_IMPLEMENTED.** "PARTIAL" is the honest state of almost everything, because the one thing
that would make most of them COMPLETE, a production checkout service, is not built.

## Evidence of what was run

| Check | Result |
|---|---|
| Contracts, full suite (pinned Foundry 1.8.5, solc 0.8.24) | 290 passed, 0 failed, 7 fork tests skipped (no network in that run); runtime sizes unchanged (largest 21,357 B) |
| Specification consistency (`spec/tools/check_all.py`) | All 21 checks pass |
| Freeze readiness | **Unchanged: NOT READY, 1 of 11 conditions met** |
| Packages (Node's built-in runner) | 55 tests pass (config, SDK, EIP-712, development stub); generated files are current |
| Hygiene (`scripts/repo_hygiene.py --history`) | 0 failures; 1 warning (the 47.3 MiB log); no secret in the tree or in the Git history (4 commits before this change) |
| Hygiene checker's own tests | 11 pass |
| Documentation links | Checked by `scripts/check_docs.py` |
| Fresh clone of the branch (Windows, Git's default `core.autocrlf=true`, pinned toolchain archives restored from a local copy, no download) | Hygiene, link check, generated-file checks, 55 package tests, headless example, `npm pack --dry-run`, contracts build, **290 contract tests**, devnet and all 21 specification checks pass. The run **found a defect, now fixed**: a CRLF checkout changed the bytes the evidence tools hash and failed checks 17, 18 and 21, so `.gitattributes` now forces LF and the contracts report was re-recorded from LF sources (no bytecode or size changed). Check 18 also needs `forge build` first; CI and CONTRIBUTING now say so |
| Local devnet quickstart | Run end to end with the pinned anvil and forge |
| Embedding example | Run in a real browser, positive and negative case |
| Compose file | Validated with `docker compose config`; **nothing pulled or built** |
| GitHub workflows | **Not run**; checked structurally only |
| Caddy and nginx files | **Not run** |
| Linux path of the toolchain | **Not run** |

## Owner actions (an engineer cannot do these)

1. **Confirm the license** (Apache-2.0 is a proposed default) and decide L-1 with counsel.
2. **GitHub settings:** private vulnerability reporting; branch protection on `main` with required status checks and "Require review from Code Owners"; secret scanning and push protection;
   Dependabot alerts; restrict who can run release workflows; create the `npm-publish` environment if npm publishing is ever wanted.
3. **Clear the name** "PayTrue" and the `@paytrue` npm scope; publish a contact for conduct reports and a backup contact for security reports.
4. **Decide the branding** of the specification and catalogs (see [rename impact](rename-impact.md)); never rename an EIP-712 domain or tag without regenerating every dependent artifact.
5. **Pin** GitHub Actions and base images by digest once the workflows have run.
6. **Run the workflows once** on GitHub, then remove `continue-on-error` from the advisory jobs.
7. Conform the text of document 19 to the OPN-16 and OPN-01 decisions (recorded in `spec/03-assumptions-decisions-risks.md`; sections 5.1, PX-08, 5.5, 17, TR-17, 20 and 21 still say what they said before).

## Remaining blockers for "PayTrue can be self-hosted as a payment service"

| Blocker | Why |
|---|---|
| No production checkout service | Hosted checkout, wallet connection, executor, reconciliation and ledger are specified, not built |
| Protocol freeze not approved | 10 of 11 conditions unmet: wallet-lab evidence (0 of 10), Permit2 review, constants approval (0 of 19), planner implementations, audits, sign-offs |
| No audit | The contracts are tested, not audited |
| Interactive use of an existing mandate | Disabled in v1 (OPN-01, `RESOLVED_FOR_V1`); needs a typed interactive-charge request that does not exist |
| License, name and npm scope unconfirmed | Owner decisions |
