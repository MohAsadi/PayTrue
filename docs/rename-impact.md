# Branding and rename impact: PayTrue and the working name FastPay

The project is called **PayTrue**. The specification, the contracts' generated library, the EIP-712 domains and many identifiers still use the **working name FastPay**. This page classifies every
use of the old name, says what was renamed now, what must **never** be renamed blindly, and gives the procedure for a deliberate rename.

> **Do not run a find-and-replace of "FastPay" over this repository.** Some of those strings are hashed into domain separators, type tags and signed messages. Changing one changes the
> bytes that wallets sign and that contracts verify. `python -I scripts/repo_hygiene.py` fails if a protected identifier (section 2) disappears from the place where it is used.

## 1. What was counted (baseline: commit `77c0716`, 2026-10-17)

In the repository's own files (excluding vendored sources, the generated backlog and raw run logs): **"FastPay" 465 times in 128 files, "fastpay" 178 times in 47 files, "FASTPAY" 24 times in 7 files**,
and "PayTrue" only as the title of the root README. By type of the files that contain "FastPay": Solidity 44, JSON 35, Markdown 28, Python 18, TypeScript 2, TOML 1.

| Class | What | Examples | Rule | Renamed now? |
|---|---|---|---|---|
| **A. Cryptographic identifiers** | Strings that are hashed or signed | The EIP-712 domain names `FastPay Mandates` and `FastPay Quote`; the tags `fastpay.lineage.v1`, `fastpay.mandate.v1`, `fastpay.cycle.v1`, `fastpay.route.direct.v1`, `fastpay.migration.snapshot.v1`, `fastpay.pin.eoa.v1`, `fastpay.plan.v1`, `fastpay.plan.entry.v1`; the wallet-lab signing prefix `fastpay-wallet-lab-run-record:v1:` | **Never rename without the procedure of section 4.** Each is a new domain or tag version, regenerated everywhere, re-approved | **No** |
| **B. Code and artifact names** | Identifiers that carry no signed bytes | The library `FastPayTypes` (a generated Solidity library, 40 import sites, its ABI snapshot), the files `fastpay-eip712.ts` and `fastpay-types.generated.ts`, test labels such as `fastpay.test.customer.` | Rename only through the generator, in one change, with the checks green. The library name is not in any bytecode or hash, but the file and ABI names are referenced by tools | **No** (the `@paytrue/eip712` package renames its *output* files: `encoder.js`, `types.generated.js`) |
| **C. Environment variables** | Names read from the environment | `FASTPAY_PERMIT2` and nine more in the deployment script; `FASTPAY_TABLE_STRIDE` in a test | Add the new name, keep the old as a fallback, remove the old after a release | **Yes** for the deployment script: `PAYTRUE_*` is read first, `FASTPAY_*` is the fallback (tested). `FASTPAY_TABLE_STRIDE` is test-only and unchanged |
| **D. API surface names** | HTTP headers and event fields of the proposed API | `FastPay-Signature`, `FastPay-Version` in the unfrozen catalogs | The API is a proposal, not frozen | **Yes** in the SDK: it writes `PayTrue-Version` and `PayTrue-Signature` and **reads both** signature names. The catalogs in `spec/checkout/` still say `FastPay-*` and are to be conformed |
| **E. Specification prose** | Documents 01 to 19 | "FastPay v1", "the FastPay contracts" | A mechanical rename after the identifiers are decided. **It changes the freeze fingerprints** (sections of documents 05, 06, 09 to 13 and 17 are hashed): regenerate them with `freeze_fingerprints.py --write` and treat the approval of those sections as void | **No** |
| **F. Test seeds** | Strings that derive keys and addresses in tests | `fastpay-test-*`, `fastpay-eip712-golden-test-key-v1` | Changing one changes the derived address and every vector that contains it | **No** |
| **G. Repository, package and documentation names** | What a reader meets first | The repository `PayTrue`, `@paytrue/*`, `docs/`, the root README | Use PayTrue | **Yes** |

## 2. The protected identifiers

`scripts/hygiene.config.json` records each string and the first bytes of its Keccak-256; the check compares them with the files that use them.

| Id | String | Keccak-256 (first 6 bytes) | Used in |
|---|---|---|---|
| `EIP712-DOMAIN-MANDATES` | `FastPay Mandates` | `ed345e4b13fb` | `spec/eip712/types.json`, the generated Solidity library, the generated TypeScript, the golden vectors; every mandate signature |
| `EIP712-DOMAIN-QUOTE` | `FastPay Quote` | `d003b34a2da7` | the same files; every price quote signature |
| `TAG-LINEAGE_TAG` | `fastpay.lineage.v1` | `bf83254ba89a` | the lineage id of every mandate |
| `TAG-MANDATE_TAG` | `fastpay.mandate.v1` | `0945ea3d0f62` | the mandate id |
| `TAG-CYCLE_TAG` | `fastpay.cycle.v1` | `1b3b500f4535` | the cycle id of a recurring charge |
| `TAG-ROUTE_DIRECT_TAG` | `fastpay.route.direct.v1` | `48a89266632b` | the direct route hash in a charge |
| `TAG-SNAPSHOT_TAG` | `fastpay.migration.snapshot.v1` | `4aad20bbdc76` | the migration snapshot the customer signs |
| `TAG-PIN_EOA` | `fastpay.pin.eoa.v1` | `8b07c3b3a0bc` | the account pin of a plain account |
| `TAG-PLAN` | `fastpay.plan.v1` | `821a8610044e` | the migration plan hash chain |
| `TAG-PLAN-ENTRY` | `fastpay.plan.entry.v1` | `77f6d4673447` | an entry of that chain |
| `WALLET-LAB-SIGNING-PREFIX` | `fastpay-wallet-lab-run-record:v1:` | `58020e059693` | the message a tester and a reviewer sign over a run record |

The types are a **proposal**, not frozen, and no wallet has signed any of them, so a rename now costs only regeneration and re-approval. After freeze, or after any deployment that holds funds, it
would be a new domain version and a new deployment.

## 3. What a user of the repository sees today

| Surface | Name |
|---|---|
| Repository, packages, documentation, examples, deployment files | PayTrue |
| Environment variables (the deployment script) | `PAYTRUE_*` first, `FASTPAY_*` accepted |
| SDK headers | `PayTrue-*` written, `FastPay-Signature` also read |
| EIP-712 domains a wallet shows | **FastPay Mandates**, **FastPay Quote** (unchanged: class A) |
| The specification | FastPay (class E) |

A user sees "FastPay" in the wallet prompt of a mandate signature until the procedure below is run. This is a branding inconsistency, not a safety problem.

## 4. Procedure for a deliberate rename of the cryptographic identifiers

Do it **once, before protocol freeze**, as one reviewed change; never in pieces.

1. Decide the new strings (domain names, the tags, the signing prefix) and write the decision as an ADR in `spec/06-initial-architecture.md`. The decider is the Principal Architect with the Wallet Protocol Engineer and the Solidity Lead.
2. Change `spec/eip712/types.json` (domains, tags); change `contracts/src/MigrationQueue.sol` (plan tags) and `spec/tools/wallet_lab_verify.py` (the prefix) and the wallet-lab kit text.
3. Regenerate everything derived: `python -I spec/tools/export_eip712.py --write` (both Solidity libraries, the TypeScript, the golden vectors, the Foundry vectors, the wallet payloads in `spec/eip712/typed-data` and
   `spec/foundry/vectors/typed-data`, `spec/eip712/TYPES.md`), `export_foundry.py --write`, `build_config_records.py --write` (the type strings of record PC-09 are checked against `types.json`),
   `sync_vectors.py --write` (the vector blocks in the documents).
4. Re-run `eip712_crosscheck.py` (Python, TypeScript and both Solidity implementations must agree), the contract and model suites, `check_all.py`.
5. Regenerate the freeze fingerprints (`freeze_fingerprints.py --write`) and the C-11 fingerprint in `evidence/freeze_register.json`; any approval of the old fingerprint is void.
6. Update the entries of `scripts/hygiene.config.json` (`protectedIdentifiers`) in the same change; the check exists to make step 6 impossible to forget and step 1 impossible to skip.
7. Rename the code identifiers (class B) with the generator in the same change if you want them to match, then the prose (class E), then regenerate the fingerprints again.
8. Wallet-lab evidence recorded with the old signing prefix is **not** valid for the new one: the records must be redone (none exist today).

## 5. Open points

| Point | Owner |
|---|---|
| Whether to run the procedure before freeze (recommended) or keep FastPay as the protocol's name | The sponsor |
| Clearance of the name "PayTrue" (trademark and domain), which this repository cannot do | The sponsor and counsel |
| Conforming the catalogs in `spec/checkout/` to the `PayTrue-*` header names | Whoever next edits the API catalog |
