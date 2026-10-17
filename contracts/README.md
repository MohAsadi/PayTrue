# FastPay contracts (the actual contracts)

**Status: implementation evidence, not a release.** These are the Solidity contracts that the specification (`../spec`, version 0.5.0, draft) describes.
They are compiled and tested with a pinned toolchain, but they are **not audited**, the constants they use are **proposals**
(`../spec/config/pc_records.json`: every record is PROPOSED), the EIP-712 types are **not frozen**, no wallet has displayed or signed any message,
and **protocol freeze (RG-016) is not approved**. `python -I ../spec/tools/freeze_readiness.py` says NOT READY, and this directory does not change that.

The reference model of the specification is a different thing: `../spec/foundry` models the logic in Solidity and Python to test the specification itself. Its
results and the results of this directory are **separate evidence** and are never added together (`../spec/evidence/implementation/REPORT.md` §0).

## Contracts

| Contract | Role | Writes mandate state? |
|---|---|---|
| `MandateManager` | The core. Mandates and lineages, the exposure index, nonces, the account pin, activation, successor activation, pause bits, revoke, retire, reduce, and the guards of `consume`. Keeps the terms as a hash plus the data that exits need. | **Yes: the only contract that does.** |
| `UsageLedger` | The usage counters of a lineage (token and fiat totals, the four windows, cadence, settled cycles). | Counters, and only when the manager calls it in `consume`. |
| `SuccessorValidator` | The predicates of `activateSuccessor` that read state and write none (A3, R1…R3, X1, K1, G1, X2, C1/C2, O1N/O1E). Called with STATICCALL. | No (a `view`). |
| `MandateGateway` | Verifies the customer's EIP-712 signatures (the signed domain names the **manager**), spends the nonce at the manager and relays the call; pin batches. | No state of its own. |
| `MigrationQueue` | A bounded, resumable migration plan: a hash chain over the successor authorizations that the customer committed to, executed in steps of at most `MAX_BATCH`; skip, abort, expire. May call `activateSuccessor` and nothing else. | Through the manager only. |
| `PaymentRouter` | `charge` (recurring, Permit2 AllowanceTransfer, quote verification Q1…Q18) and `payOnceWithSignature` (Permit2 SignatureTransfer with the `PayOnceIntent` witness). Holds no tokens. | No. |
| `RouterRegistry`, `TokenPolicyRegistry`, `SignerSetRegistry`, `MerchantRegistry`, `ExecutorRegistry`, `FeeController` | Router lifecycle and settle-once; token policy and the versioned price-bounds registry; versioned quote-signer sets; merchants; executors; the fee under an immutable ceiling. | No. |

There is **no `delegatecall`, no `callcode`, no generic call, no proxy and no upgrade path**. The links between the contracts are typed calls to addresses
fixed at deployment. The architecture decisions are ADR-020 (versioned bounds, snapshot), ADR-021 (the split), ADR-022 (the migration plan,
`MAX_BATCH`), ADR-023 (signer sets) in `../spec/06-initial-architecture.md`.

**Not built in this pass:** `chargeInitial`, `payOnceWithSignatureAndPermit`, `payOnceWithAuthorization`, `payOnce`, `RefundManager`, `EmergencyGuardian`, a plan
opened by relayed signature, the typed charge request (finding F-19), deployment scripts. The `recipientPolicy` of a mandate is opaque (F-18).

## Frozen compiler settings

`frozen-settings.json` records them and `foundry.toml` must equal it (`../spec/tools/contracts_report.py` checks): solc 0.8.24, EVM cancun, no via-IR,
optimizer on with 200 runs, no bytecode hash, no CBOR metadata, **no `code_size_limit` override**. Every runtime is at most 22,000 bytes (the largest is the
manager); EIP-170 allows 24,576. A runtime that does not fit is split into contracts, never tuned by changing these settings.

## Layout

```text
src/                    the contracts            src/generated/FastPayTypes.sol   generated from ../spec/eip712/types.json (never edited by hand)
src/lib/                PinLib, AuthLib, ContainLib      src/interfaces/          what the contracts see of each other
test/                   suites (see below)       test/helpers/            Base (the whole system on the rebuilt Permit2), builders, mocks
frozen-settings.json    the frozen compiler settings
```

## Running

The Foundry toolchain is pinned and fetched by `../spec/toolchain/fetch_toolchain.py` (see `../spec/toolchain/README.md`); use its wrapper:

```bash
python -I spec/toolchain/forge.py --project contracts build --sizes       # compile and print runtime sizes
python -I spec/toolchain/forge.py --project contracts test                # every suite (the fork variants skip without a fork)
python -I spec/tools/contracts_tests.py                                   # run and record (evidence/implementation/contracts-test-run.json)
python -I spec/tools/contracts_report.py                                  # settings, sizes, opcode scan, low-level calls, call targets
python -I spec/tools/loop_audit.py --project contracts                    # every loop is bounded and annotated
python -I spec/tools/contracts_mutation.py                                # mutation testing of these contracts (about an hour)
python -I spec/tools/fork_run.py --project contracts                      # the suites on forks of Ethereum, Base and Arbitrum One (needs network)
```

## Suites

| Suite | What it shows |
|---|---|
| `Deployment.t.sol` | every runtime under the target, the cyclic links of the five contracts that point at each other, the rebuilt Permit2 |
| `Mandates.t.sol`, `ManagerAlone.t.sol` | lifecycle, the exposure index, exits that are never gated, reductions that only narrow, pin updates; what the manager enforces when the validator says yes to everything |
| `Charge.t.sol`, `Quote.t.sol` | guards G1…G10, the dual caps and their windows, the fee, settle-once, atomicity of effects and pull; every quote check Q1…Q19 with its boundary, the bounds registry |
| `Successor.t.sol`, `Queue.t.sol` | every predicate A1…O1E with a passing and a failing case, the effects, counters across generations; the plan state machine |
| `Gateway.t.sol`, `PayOnce.t.sol`, `Registries.t.sol` | signatures, nonces, domains, ERC-1271 under the pin; Pay Once against the real Permit2 code; the registries, the O(1) signer check |
| `Differential.t.sol`, `generated/EIP712Golden.t.sol` | the contracts' libraries against the reference model's exported vectors (742 containment tuples, nine hash cases, the fiat vectors) and against Foundry's own EIP-712 cheat codes |
| `Invariants.t.sol` | stateful fuzz of the real contracts; every invariant is recomputed from a ghost list of all mandates; the handler prints what it actually did |
| `Gas.t.sol` | the gas of a worst-case plan step and the guard that `MAX_BATCH` fits the budget; activation, charge, revoke |
| `fork/ForkSuites.t.sol` | the suites above run against the REAL Permit2 of a forked chain |

## What this does not show

The gas figures are on the EVM gas schedule of the compiler's target, not on the chains' own accounting (Arbitrum's in particular), and the per-transaction cap of
EIP-7825 is an assumption about the launch chains. The fork tests read chains through public RPC providers. Every test was written by the people who wrote the contracts.
