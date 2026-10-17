# Third-party notices

PayTrue's own code and documentation are licensed under the **Apache License 2.0** (see [LICENSE](LICENSE)). This file lists the third-party material that
the repository contains, fetches or depends on, the licenses those components are under, and how they relate to PayTrue's own artifacts.

> This is engineering due diligence recorded on 2026-10-17 from the license files and SPDX headers in the repository and from the pinned dependency
> lock. It is **not legal advice**. Items marked **LEGAL REVIEW** should be confirmed by counsel before a release is described as license-clean.

## 1. What PayTrue's own artifacts contain

| Artifact | Contains third-party code? |
|---|---|
| `contracts/src` (the contracts) | **No.** They import only PayTrue's own files. The part of Permit2 they call is described by PayTrue's own interface (`contracts/src/interfaces/IPermit2.sol`); no Permit2, solmate or OpenZeppelin source is imported |
| `contracts/test`, `contracts/script` | `forge-std` (MIT OR Apache-2.0), imported as a test and script library. The tests also deploy a compiled copy of Uniswap Permit2 as a fixture (section 3) |
| `packages/*` (SDK, configuration, EIP-712 encoder) | **No runtime dependencies.** The EIP-712 encoder carries its own Keccak implementation |
| `deploy/*`, `examples/*`, `docs/*` | No third-party code. Container base images named in `deploy/` are **not** distributed by this repository |

## 2. Third-party source that is tracked in this repository

| Component | Where | License | Notes |
|---|---|---|---|
| forge-std v1.9.7 (`foundry-rs/forge-std`, commit `77041d2ce690e692d6e03cc812b57d1ddaa4d505`) | `spec/foundry/lib/forge-std` | **MIT OR Apache-2.0** (`LICENSE-MIT`, `LICENSE-APACHE` are in the tree; copyright "Contributors to Forge Standard Library") | Test and script library only. It contains public default RPC URLs, including an Infura demo key, which secret scanners may flag; they are upstream constants and are allow-listed in `scripts/repo_hygiene.py` |

## 3. Third-party material fetched or embedded, not redistributed as source

The following are **pinned by URL, commit and SHA-256** in `spec/toolchain/toolchain.lock.json` and fetched by `spec/toolchain/fetch_toolchain.py`. Their source
trees are **not tracked** in this repository (they were tracked in earlier commits; Git history is unchanged).

| Component | License (as recorded from its license files and SPDX headers) | Use |
|---|---|---|
| Foundry v1.8.5 (`foundry-rs/foundry`) | MIT OR Apache-2.0 (per upstream) | Build and test toolchain, fetched as a binary |
| solc 0.8.24, 0.8.17 | GPL-3.0 (compiler binary; fetched, never redistributed here) | Compiler. PayTrue does not redistribute it |
| Uniswap Permit2 at `cc306b601f172c51bc04334a109e98340456620b` | MIT (Copyright 2022 Uniswap Labs) | Reference for the deployed Permit2 that PayTrue calls; rebuilt and compared byte-for-byte |
| solmate at `8d910d876f51c3b2585c9109409d601f600e68e1` | **AGPL-3.0-only** (license file AGPL-3.0; 50 per-file AGPL-3.0-only headers and one AGPL-3.0-or-later) | Permit2's own dependency; **linked into the compiled Permit2** (see below) |
| ds-test at `9310e879db8ba3ea6d5c6489a579118fd264a3f5` | **GPL-3.0-or-later** | Permit2's test dependency |
| OpenZeppelin Contracts at `d3ff81b37f3c773b44dcaf5fda212c7176eef0e2` | MIT (with vendored Compound and Optimism files under their own MIT-style notices) | Permit2's test dependency |
| forge-gas-snapshot, a second forge-std commit (`27e14b7f2448e5f5ac32719f51fe652aa0b0733e`) | See their repositories | Permit2's build and test dependencies |

**Compiled Permit2 as a test fixture (LEGAL REVIEW, item L-1).** `spec/evidence/permit2/` holds the creation code and the runtime code of Permit2 as rebuilt from
the pinned commit, and the contract tests deploy that code locally. Permit2's `AllowanceTransfer` imports solmate's `SafeTransferLib` and `ERC20`, which are
AGPL-3.0-only, so the compiled code contains compiled AGPL code. PayTrue uses it only as a **test fixture and as evidence of byte equality with the chains' deployed
Permit2**; it does not ship in any PayTrue runtime, package or image, and no PayTrue contract is built from it. The deployed Permit2 on public chains is a public
contract that PayTrue calls through an interface. Counsel should confirm that keeping the fixture and the evidence files in a public repository is acceptable, or
decide to fetch the creation code at test time instead of tracking it.

**Audit documents.** The Permit2 tree includes third-party audit PDFs (ABDK, ChainSecurity, OpenZeppelin 2018, solmate). They are **not** tracked any more and
are not redistributed by PayTrue.

## 4. Compatibility summary

| Question | Answer |
|---|---|
| Can PayTrue's Apache-2.0 code combine with MIT, Apache-2.0 and BSD components? | Yes. forge-std is the only third-party source in the tree |
| Is any AGPL or GPL source part of a PayTrue runtime, package or image? | **No**, by construction of the dependency list in section 1. AGPL/GPL material appears only as fetched build inputs and as the compiled Permit2 fixture in section 3 |
| Do the GPL compiler and toolchain affect the license of compiled PayTrue contracts? | Not as far as this review goes; confirm under **LEGAL REVIEW** if the question matters for a release |
| Are there copyleft files in the repository today? | No tracked file carries a copyleft license header after the third-party trees were untracked. The compiled Permit2 fixture is the one item to review |

## 5. Keeping this file true

`scripts/repo_hygiene.py` fails when a tracked source file carries an SPDX identifier other than the ones allowed here, when a license file appears that is not
listed in this document, or when a vendored tree reappears. A new dependency needs a row in section 2 or 3 before it is merged.
