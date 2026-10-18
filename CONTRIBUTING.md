# Contributing to PayTrue

Thank you for helping. PayTrue is a payment toolkit, so the bar for changes is higher than for most projects: a small mistake can lose money. This page tells you how to set up, what to run, and
what a good change looks like. By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- **Security issues**: do not open an issue or a pull request; see [SECURITY](SECURITY.md).
- **Large changes**: open an issue first. The specification (`spec/`) is the source of truth; code follows it, and a change to a protocol rule starts as a change to the specification.
- **What the project is not**: it is not audited, not frozen and not production-ready. Do not describe it as supported, compatible or audited anywhere ([open-source readiness](docs/open-source-readiness.md)).

## Set up

You need Git, Node 22.13+ (18+ for most packages), Python 3.10+ and, for the contracts, the pinned toolchain:

```bash
git clone https://github.com/<you>/PayTrue.git && cd PayTrue
python -I spec/toolchain/fetch_toolchain.py        # pinned Foundry, solc and the Permit2 sources; verifies every SHA-256
```

Nothing is installed with a package manager: the packages have no dependencies. Windows is where the checks were developed and run; Linux and macOS are expected to work (the toolchain lock pins
Linux binaries) but **the Linux path has not been verified by the maintainers**: please report what you find.

## What to run before you open a pull request

```bash
python -I scripts/repo_hygiene.py                       # sizes, secrets, SPDX headers, vendored trees, protected identifiers, packages
python -I scripts/test_repo_hygiene.py                  # the checker itself still fails on what it should catch
python -I scripts/check_docs.py                         # relative links in the public documents
node --test "packages/config/test/*.test.mjs" "packages/sdk/test/*.test.mjs" "packages/eip712/test/*.test.mjs" "packages/devserver/test/*.test.mjs"
node packages/config/scripts/generate-env-example.mjs --check
node packages/config/scripts/generate-config-doc.mjs --check
python -I spec/toolchain/forge.py --project contracts test      # when you touched contracts/ (about four minutes)
python -I spec/toolchain/forge.py --project contracts build     # check 18 compares this build with the recorded report, so build first
python -I spec/tools/check_all.py                                # when you touched spec/, contracts/ or evidence (21 checks)
```

CI runs the same checks. A check that fails is fixed, never skipped or weakened to make a change pass.

## Rules

| Area | Rule |
|---|---|
| Licenses | Your contribution is under Apache-2.0 (inbound = outbound, no CLA). Every Solidity file starts with `// SPDX-License-Identifier: Apache-2.0`. No GPL, AGPL, `UNLICENSED` or unlicensed code; a new dependency needs a row in `THIRD_PARTY_NOTICES.md` first, and the packages stay dependency-free |
| Generated files | Never edit one by hand. `spec/eip712/types.json` is the single source of the EIP-712 types; `export_eip712.py` writes everything derived. `.env.example` and `docs/configuration.md` come from `packages/config/src/schema.js`. `spec/18-configuration-records.md` comes from `spec/config/pc_records.json`. The checks fail when one is stale |
| Cryptographic identifiers | The EIP-712 domain names, the hashed tags and the wallet-lab signing prefix are **protected**: do not rename them, even to rename the product ([rename impact](docs/rename-impact.md)). The hygiene check fails if one disappears |
| Contracts | The compiler settings are frozen (`contracts/frozen-settings.json`); a runtime that does not fit is split, never tuned. No `delegatecall`, `callcode`, `selfdestruct`, `tx.origin`, `create` or `create2` in a runtime. Every loop has a stated bound. Add a test that fails without your change |
| Evidence | Evidence is recorded by its tool and committed with the change that caused it. Do not edit a recorded file. Never add wallet-lab evidence yourself: it needs real wallets and named, signed reviewers. Raw wallet-lab artifacts are private ([evidence policy](docs/evidence-policy.md)) |
| Secrets and files | No secret, key, `.env`, binary, archive, build output or file over 20 MiB. The hygiene check enforces it |
| Claims | Do not claim a wallet works, a chain is supported, a component is audited or a constant is approved without the evidence the specification requires |
| Specification | A change to a `SECURITY-CRITICAL`, `FINANCIAL-CONTROL` or `PRIVACY-CRITICAL` item needs a named reviewer from Security, as `spec/01-toc.md` says. Approvals are given by named people in the records, never by a tool or by an assistant |
| Documentation | Plain, accurate, no marketing. State what is *not* done. Relative links must resolve |

## Commit and pull-request style

- One logical change per pull request; a clear title in the imperative ("Refuse a wildcard frame ancestor"), a body that says **why**.
- Mention the issue, the specification section, and the evidence you ran.
- If you used an AI assistant, you are responsible for every line; say so in the description if it matters to review.
- Maintainers merge; contributors do not push to `main`.

## Tests you can add easily

The packages use Node's built-in test runner (`node:test`) with no dependency. The development stub makes it cheap to test an SDK behaviour end to end (`packages/devserver/test`). For contracts, copy the
nearest suite in `contracts/test` and keep the mutation tests in mind: `spec/tools/contracts_mutation.py` shows which bugs the suite is expected to notice.

## Getting help

See [SUPPORT](SUPPORT.md). Governance and who decides what: [GOVERNANCE](GOVERNANCE.md).
