# FastPay Foundry suites (revision 0.5)

## Status: compiled and run with the pinned toolchain (revision 0.5.0 + implementation evidence)

The project compiles with **solc 0.8.24** (via-IR, 20 optimizer runs, EVM cancun) under **Foundry v1.8.5**, both pinned and checksum-verified by
`toolchain/` (see [../toolchain/toolchain.lock.json](../toolchain/toolchain.lock.json)); every suite except the fork suites runs and passes. The numbers, the
gas measurements, the fork runs and the findings are in [../evidence/implementation/REPORT.md](../evidence/implementation/REPORT.md) (generated from the run files;
this README states no result). **Nothing here is an approval** and what is tested is still a **reference model** of the predicates of documents 11, 12 and 17, not
the contracts, which do not exist yet.

Changes the first compile and the first runs forced (details: findings F-01 to F-05 of the report): tests read the clock with `vm.getBlockTimestamp()` (the via-IR
optimizer moves `block.timestamp` across `vm.warp`); the mutation suite runs in ten chunks and `memory_limit` is raised; the model gained `TermsShape` (canonical terms
and documented widths), an O(1) exposure index, an O(1) registry counter and a signer-set size bound, each with tests; every loop carries a `loop-bound` annotation
checked by `tools/loop_audit.py`.

## Setup

Use the wrapper, which refuses to run on a toolchain that is not the pinned one and never downloads a compiler:

```text
python -I spec/toolchain/fetch_toolchain.py              # once: fetch and verify Foundry, solc 0.8.24 and 0.8.17, forge-std v1.9.7 (HTTPS, github.com and codeload.github.com only)
python -I spec/toolchain/forge.py build                  # about five minutes (via-IR)
python -I spec/toolchain/forge.py test                   # every suite except the fork suites (they skip without ETH_RPC_URL)
python -I spec/toolchain/forge.py test --json            # the same, machine-readable (what tools/record_evidence.py reads)
```

Useful selections:

```text
forge test --match-path "test/generated/*"                                   # the vectors exported from the Python model and the EIP-712 golden vectors
forge test --match-contract MigrationMutationTest                            # mutation testing of the reference model (151 mutants)
forge test --match-contract MigrationInvariantTest                           # stateful invariants (256 runs x depth 64)
forge test --match-contract LoopBoundsTest -vv                               # loop bounds, early refusal, gas of the worst cases (the log lines are the numbers)
FASTPAY_TABLE_STRIDE=25 forge test --match-contract GenTablesTest            # replay every 25th table transition (the full replay is slow)
python -I spec/tools/fork_run.py                                             # the Permit2 fork suites on Ethereum, Base and Arbitrum at pinned blocks (needs network)
```

`foundry.toml`: `solc 0.8.24`, `via_ir = true`, `fs_permissions` read of `./vectors` only, `[fuzz] runs = 1000`, `[invariant] runs = 256, depth = 64`, `memory_limit` 2 GiB,
no network by default.

## Layout

```text
foundry.toml
lib/                   empty (forge-std is installed by you)
vectors/*.json         the exported vectors, canonical (sorted keys); manifest.json lists counts, errors, mutants, ops and coverage
src/                   the reference model, one file per concern, mirroring tools/protocol_model.py
  Errors.sol           GENERATED: every custom error of documents 11, 12, 17 (+ Permit2's)
  Mutants.sol          GENERATED: the numbers of the named mutants (same numbers as protocol_model.MUTANTS)
  Permit2Mock.sol      AllowanceTransfer ledger, exact semantics of the pinned commit (+ AllowanceMath)
  RegistryModel.sol    router lifecycle, isBindable, Mode(R)
  MigrationModel.sol   mandates, lineages, exposure index, activate, activateSuccessor (A1..O1E, E1..E6), revoke, retire, reduce, consume, updateAccountPin
  PinModel.sol         AccountPin, PIN_WELLFORMED, PIN_OK, nextPinVersion, AUTH
  ContainModel.sol     snapshot, containment K.1..K.9, widened mask, the charge guards (oracle of Lemma M), snapshot hash
  SignerSetModel.sol   signer sets, tombstones, Q1 and Q13
  HashModel.sol        EIP-712 encoding, identifiers, fiat rounding
  TimeModel.sol        quote times Q9..Q12, window and cycle grid, MAX_BATCH
  WidthLib.sol         narrowing that reverts instead of truncating
test/
  helpers/             ScenarioVM (the interpreter of the exported programs), VectorSuite (JSON loader and runners), Fixture, MockERC20
  generated/           GENERATED: op codes, error-selector table, one test per exported vector family or scenario
  *.t.sol              hand-written suites (they extend the generated ones; see the table below)
  fork/Permit2Freeze.t.sol
```

## What each suite covers

| Suite | Document section | Ids |
|---|---|---|
| `generated/GenHashVectors.t.sol` | 11 §4.6; 12 §4, §5.3.4; 17 §5.1, §9 | quote type hashes, domain separator, struct hash, digests on routers A and B, `lineageId`, `mandateId`, `cycleId`, `paymentId` (MIG-TV-19), route hash, fiat rounding (CAP-TV-01…03), designator hashes, `PIN_EOA`, `KECCAK_EMPTY`, `ACCOUNT_PIN_TYPEHASH`, the three example pins, the snapshot hash, Permit2 usability (MIG-TV-22, 40) |
| `generated/GenContainment.t.sol` | 12 §5.3.2, §5.3.3 | K.1…K.9 witnesses, MIG-TV-20 boundaries, the snapshot cases, a seeded sample of random (successor, predecessor, state, payment) tuples for Lemma M (I-MIG-9) |
| `generated/GenScenarios.t.sol` | 12 §12; 17 §9; 11 §9 | MIG-TV-05, 06…15, 17, 21…45 (35 split in six router states), ACP-TV-13…17, 24…40 and the on-chain half of 41, CAP-TV-14…16 and 23…32, registry and timestamp boundaries, integer widths |
| `generated/GenTables.t.sol` | 12 §5.5 | the reachable state and transition tables of the single-lineage and the two shared-allowance explorations (I-MIG-1, 8, 10, 11, Claim 4) |
| `generated/GenErrorSelectors.t.sol` | — | the selector table of the scenario machine against the compiler's selectors |
| `SharedAllowance.t.sol` | 12 §5.3.1 | MIG-TV-30…45 (executed by the generated scenarios) and ten extra scenarios E1…E10 |
| `MigrationFuzz.t.sol` | 12 §5.3, §5.3.2, §5.3.3 | Lemma M, containment against restated clauses, O1N/O1E over allowance states, router modes and sibling counts, the exposure index (MIG-TV-43) |
| `MigrationInvariant.t.sol` | 12 §12 | I-MIG-1, 3, 7, 8, 10, 11 and "the exposure index never under-counts" |
| `MigrationMutation.t.sol` | 12 §12 | every mutant 1…N of `src/Mutants.sol` is killed by the exported vectors; mutant 0 passes all |
| `IntegerWidth.t.sol` | 12 §5.3; 17 §5.1; PC-16 | `uint48` expirations at 2^48 − 1, `uint160` sentinel and cast hazard, `uint32` pin versions and counts, checked arithmetic near 2^256, E(0) = ∞, cycle arithmetic |
| `TimestampBoundary.t.sol` | 11 §4.2, §4.7; 12 §3, §5.3 | MIG-TV-22/40, RV-T04/T08, A2 deadline, mandate expiry, Q9…Q12, signer-set grace (CAP-TV-25, 26), notice, sunset, retention, rollback window, window grid, MAX_BATCH |
| `Pin.t.sol` | 17 §5, §9 | ACP-TV-25…44 (generated) extended by fuzz over account state, pin fields and the signature path; I-ACCT-PIN, I-ACCT-NOWIDEN, I-ACCT-SIG, I-ACCT-VERSION |
| `SignerSet.t.sol` | 11 §4.7.1, §9 | CAP-TV-23…32 (generated) extended by SR-1…SR-5, SR-7 as fuzz properties and as invariants |
| `ConfigRecords.t.sol` | 16 §7 | one `test_ConfigRange_<SYMBOL>` per production-blocking constant PC-01…PC-18 |
| `fork/Permit2Freeze.t.sol` | 16 §5; 05 §2.1; 12 §5.3.1 | RV-T01, 02, 03, 04, 05, 06, 07, 08, 10, 11 (plain EOA, delegated EOA and contract account), F2, F4, F5, MIG-TV-22/40, and the differential test of `Permit2Mock` against the real Permit2 |
| `generated/EIP712Golden.t.sol` | eip712/types.json | every EIP-712 type string, type hash, hashStruct and digest of the golden vectors, the Permit2 witness hashes, the tags, Python-made signatures recovered by `ecrecover`, and the same values from Foundry's own cheat codes (`eip712HashType`, `eip712HashStruct`, `eip712HashTypedData` on the wallet payload files) |
| `EIP712Permit2.t.sol` | 10 §2.1; 16 §5 | the Permit2 rebuilt from the pinned commit is deployed through the deterministic deployment proxy (CREATE2 address, runtime code and immutables checked), then the Pay Once witness suite: single and batch witness accepted; replay, spender, every field of the witness and seven variants of the type string rejected; the destination is shown NOT to be bound by Permit2 |
| `Exec3.t.sol` | 12 §5.5 | Claim 1: one executing router per lineage while Layer 2 allowances coexist on two routers; a chain of twelve successors |
| `Reentrancy.t.sol` | 11 §5 steps 7 and 8; 04 TB-08; 16 PR-14 | a callback during the Permit2 pull (the place where a token with hooks runs) cannot charge the same cycle twice or exceed the total cap, a failed pull leaves no effect; the same callbacks against the order the model had before finding F-16 (pull first) double-charge, which is what the test pins |
| `LoopBounds.t.sol` | 12 §5.3.1, §13; 11 §4.7 | exits cost the same whatever the exposure list, sibling count or lineage history; worst-case emergency migration at 8 and at 150 exposed tokens; a batch of 50 and of 100 successors; early refusal of terms with 0 or 4 tokens, of widths above the documented ones, of a signer set above its bound, of a batch of 51; registry counter and exposure position map after random operations |
| `fork/Permit2ThreeChains.t.sol` | 16 §5 | the code on the chain equals the rebuilt code byte for byte with the chain id and domain separator of the chain, the domain separator equals the golden library's, and the whole witness suite passes against the real Permit2 on Ethereum, Base and Arbitrum One |

Backend-only vectors (ACP-TV-41…44 evidence states, the planner halves of MIG-TV-26, 41, 42, 44) are in `vectors/backend.json`; no contract can execute them.

## How the generated tests work

`tools/export_foundry.py` writes **programs**: flat arrays of 8-word instructions `[op, a, b, c, d, e, expectSel, expectArg]` that the Python
model executed to produce every expectation. `test/helpers/ScenarioVM.sol` interprets the same words on the Solidity model; each instruction
runs in a self-call, so a revert undoes it, and the revert selector is compared with the expected error (and, for the errors that carry one,
its argument). Fresh customers and routers per run (an `instance` namespace) let one deployed model serve every scenario.
A transition table is replayed as BUILD (concretise a state key), ACT, OBSERVE (compare the next key). The mutation test runs the same
programs with a non-zero `mutant` argument.

Regenerate and check: `python -I tools/export_foundry.py --write` then `--verify` (deterministic: no timestamps, sorted keys, seeded samples).
Never edit `vectors/`, `src/Errors.sol`, `src/Mutants.sol` or `test/generated/` by hand.

## The reference model is replaced by the real contracts through the same interface

`ScenarioVM` and `Fixture` talk to the model through a small set of external functions: `MigrationModel.activate`, `buildAuth`,
`activateSuccessor`, `revoke`, `retire`, `reduceDropToken`, `updateAccountPin`, `consume`, `setPause`, and the views `live`, `exposedCount`,
`getMandate`, `mandateTerms`, `mandatePin`, `lineages`, `authRouter`, `lineageDigest`, `mandateDigest`, `wouldConsume`; `RegistryModel`
(`registerActive`, `deprecate`, `emergencyDisable`, `clearEmergency`, `sunset`, `retire`, `isBindable`, `mode`, `isChargeable`);
`SignerSetModel` (`proposeSignerSet`, `activateSignerSet`, `removeQuoteSigner`, `stopSignerSet`, `verify`); `Permit2Mock` (the real Permit2
interface plus the `*As` harness entry points). When the real `MandateManager`, `RouterRegistry` and verifier exist, write thin adapters with
these functions (the harness-only ones, `forceState`, `markSunset`, `setCodeHash`, `seedLive`, `*As`, become test hooks of the adapter), point
`ScenarioVM` and `Fixture` at the adapters, and run the unchanged vectors, fuzz and invariant tests; the `mutant` argument is then replaced by
mutation testing of the real source (each mutant of `src/Mutants.sol` names the predicate to break). Until then the suites check the
model, and the model checks the specification.

## Where the Solidity model deliberately simplifies the Python model (and both simplify the documents)

* The manager builds the successor mandate itself: its `lineageId`, `customer` and `generation` are not caller-supplied, so those conjuncts of L1 hold by construction. `L.activeMandateId = P.id` and `¬L.terminated` are checked but are implied by `¬terminal(P)` in every reachable state (no mutant is defined for them).
* `activate` checks the router, extensions, pin (well-formedness, `PIN_OK`, version 1) and exposure, not Permit2 funding. Bounds are not intersected with live registry bounds. Charges check the per-payment and total token caps and the Permit2 pull; window counters, fiat caps, fees and quotes are not modelled in `consume` (Lemma M covers them in `ContainModel.accepts`).
* Terms and pins are stored once by content hash (a storage-cost optimisation); `MigrationModel` otherwise follows `protocol_model.ManagerModel` line by line, including the order of the checks.
* Registry transitions inside the explorations use `forceState` and `markSunset` (the notice and retention guards have their own vectors); `MAX_BATCH` (now 10, measured on the contracts: ADR-022) is the pure check `TimeModel.batchCheck`; the model has no plan, no `MigrationQueue` and no `activateSuccessors`.
* `Permit2Mock` moves no tokens; `permit` exists only as `permitRegrantAs` (the write of a signed permit whose checks pass).
* `Consumable` and `AuthRouters` include `¬retired ∧ now < expiresAt` (the text of document 12 §5.3 defines `Consumable` without time; see the document issues in the report).
* Lineage usage in the digests covers tokens 1…10 (`0x7001…0x700a`), the tokens the scenarios use.
* The exploration domains are small by design (document 12 §5.5): one customer, two routers, two lineages, allowance values none / expired / bounded / unlimited; unlimited-then-expired and reverse-migration corners are scenarios, not table states.
* **Solidity-only additions of the implementation evidence** (the Python model has no counterpart, and no exported vector exercises them): `TermsShape` (token count 1..3, strictly ascending non-zero tokens, canonical empty slots, the documented widths) checked first by `activate` and `activateSuccessor`; the exposure position map (an O(1) replacement of the scan, same observable behavior); the registry's live counter (`liveCountScan` is the O(n) oracle); `MAX_SIGNERS_PER_SET` in the signer-set model. Each has its own tests (`LoopBounds.t.sol`, the invariants); none changes a vector or a mutant (all 151 are still killed).

## Known limits

The suites test a model: its gas is the model's gas. The contracts that would be deployed are in [`../../contracts`](../../contracts/README.md), with their own suites, gas measurements (`MAX_BATCH`, the storage design) and evidence, which are reported apart from this model's. The
terms record is stored as about twenty-five slots in the model, which dominates the cost of a successor and of a reduction (finding F-12). `forge lint` reports
findings on the model with a recorded disposition each (`tools/build_report.py`). The fork suites read public RPC providers and need `ETH_RPC_URL`, `FORK_BLOCK` and
`EXPECT_CHAIN_ID` (`tools/fork_run.py` sets them).
