# Licensing

> Engineering due diligence recorded on 2026-10-17, not legal advice. The license choice below is a **default adopted by this change** and awaits the owner's confirmation; items marked
> **LEGAL REVIEW** need counsel.

## The license

PayTrue's own code and documentation are licensed under the **Apache License, Version 2.0** ([LICENSE](../LICENSE), [NOTICE](../NOTICE)).

| Why Apache-2.0 | |
|---|---|
| Permissive | Anyone, including a payment operator, can use, modify, host and sell services built on it, without publishing their changes |
| Express patent grant and termination | Relevant for payment and cryptography code |
| Compatible with the third-party code in the tree | MIT, Apache-2.0 and BSD are compatible; forge-std is MIT OR Apache-2.0 |
| Its full text was already in the tree | The file in `spec/foundry/lib/forge-std/LICENSE-APACHE` is the same text |

What changed in this repository: before this change the repository had **no license file** and all 90 of its own Solidity files said `SPDX-License-Identifier: UNLICENSED`, which means *nobody*
may reuse them. They now say `Apache-2.0`, and so do the generators that write them (`spec/tools/export_foundry.py`, `spec/tools/export_eip712.py`). The change is bytecode-neutral: every runtime size and
the full contract test suite are identical before and after.

## What the license covers

| Material | License |
|---|---|
| `contracts/`, `packages/`, `scripts/`, `deploy/`, `examples/`, `deployments/`, `docs/`, `spec/` (documents, tools, evidence, reference model) | Apache-2.0 |
| `spec/foundry/lib/forge-std` (the only third-party source still tracked) | MIT OR Apache-2.0, upstream's files and license texts unchanged |
| Foundry, solc, Permit2 and its dependency tree (solmate, ds-test, OpenZeppelin, ...) | Fetched by the pinned toolchain, **not tracked**; their licenses are in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) |
| The name and any logo | Not licensed: [TRADEMARK](../TRADEMARK.md) |

## Third-party licenses and compatibility

The full table is in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md). The short version:

- **No AGPL or GPL source is tracked or shipped.** Earlier commits tracked two copies of Permit2's dependency tree, which includes solmate (AGPL-3.0-only) and ds-test (GPL-3.0-or-later). They
  are now fetched on demand and ignored by Git; Git history still contains them, and history is not rewritten.
- **The contracts import no third-party source.** They call Permit2 through PayTrue's own interface.
- **LEGAL REVIEW (L-1).** The tests deploy a compiled copy of Permit2 as a fixture, and `spec/evidence/permit2/` holds its creation and runtime code as evidence of byte equality with the deployed
  Permit2. Permit2 is MIT, but its `AllowanceTransfer` links solmate's AGPL-3.0-only `SafeTransferLib` and `ERC20`, so the compiled code contains compiled AGPL code. It is used as a test fixture and as
  evidence only; it is in no PayTrue runtime, package or image. Counsel should confirm that tracking those files in a public repository is acceptable or choose to fetch the creation code at test time.

## Contributions

Contributions are accepted under the same license (Apache-2.0 section 5: *inbound = outbound*). There is no contributor license agreement. A source file you add carries
`SPDX-License-Identifier: Apache-2.0`; `scripts/repo_hygiene.py` fails on a Solidity file that does not, and on any copyleft or `UNLICENSED` identifier.

## Keeping it true

| Check | Where |
|---|---|
| Every own Solidity file says Apache-2.0; third-party files carry only MIT or Apache-2.0 | `scripts/repo_hygiene.py` (spdx) |
| No vendored or generated third-party tree is tracked | `scripts/repo_hygiene.py` (vendored) |
| A new dependency needs a row in THIRD_PARTY_NOTICES before it is merged | `CONTRIBUTING.md`, the pull-request template |
| Package manifests say Apache-2.0 and have no dependency | `scripts/repo_hygiene.py` (packages) |

## Owner actions

Confirm the license (or replace the `LICENSE`, the NOTICE copyright line, the SPDX headers and the `license` fields in one change), and decide L-1 with counsel.
