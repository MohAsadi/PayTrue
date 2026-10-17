# Changelog

## Unreleased (specification stays 0.5.0) — 2026-10-17 — proposed checkout session and wallet-connection profile

**Protocol freeze is not approved and nothing here changes that.** A product question (must a customer install a wallet on the device that shows the checkout?) was answered with a hosted, self-custody checkout, and the sponsor decided four open points: no per-invoice deposit address in v1, a 30-minute default session, resume by email deferred, embedded and passkey wallets deferred. The result is a **proposed** product and integration specification, [19](19-checkout-session-and-wallet-connect-profile.md), **not protocol evidence**. It is marked PROPOSED, NOT PROTOCOL-FROZEN, REQUIRES SECURITY REVIEW, REQUIRES PRIVACY REVIEW and REQUIRES WALLET-LAB EVIDENCE. The first version of document 19 was written from a copy of the instruction that ended inside its section 10; this entry describes the revision (0.2.0) written from the complete 21 sections.

| What | Where |
|---|---|
| Document 19, version 0.2.0, in the 21 sections of the instruction: the product decisions CSD-01 to CSD-11; the `CheckoutSession` object (the 27 fields of the instruction and six added); the modes `PAYMENT`, `SUBSCRIPTION` and the reserved `SETUP`; the payer policies, with no wallet address shown before a connection; a 13-state machine with 23 transitions and 12 prohibited transitions; retry rules (no second attempt after a submission); the expiry rules ER-01 to ER-10; the quote lifecycle QL-01 to QL-06 and the ten checks before a signature; the wallet-connection profile CP-01 to CP-19 with an `UNVERIFIED` register of 11 claims; the two QR codes; 13 customer experiences; returning customers as two separate flows; the no-wallet behavior; the deposit-address exclusion; the merchant integration (`POST /v1/checkout/sessions`); the redirect rules; the seven webhook events; `FAILED` versus `UNKNOWN`; session recovery; security and privacy requirements SX-01 to SX-19; the acceptance criteria AC-01 to AC-16 | [19](19-checkout-session-and-wallet-connect-profile.md) |
| Proposed API catalog | [checkout/api-catalog.md](checkout/api-catalog.md) |
| Proposed event catalog | [checkout/event-catalog.md](checkout/event-catalog.md) |
| Configuration-record list for the session lifetime: **CSR-01** (proposed 10 minutes, 30 minutes, 24 hours). Backend configuration, **not** a PC record: it is outside [18](18-configuration-records.md), is not counted by condition C-4 and approves nothing | [checkout/config-records.md](checkout/config-records.md) |
| Assumptions ASM-037 to ASM-041, the proposed product decisions OD-038 to OD-044, and the risks RISK-038 to RISK-044 | [03](03-assumptions-decisions-risks.md) |
| Index entries | [01](01-toc.md) (B.4, C.27 to C.30) |

**Not done, not changed.** The instruction named the artifacts to update and the README was not among them, so the README does not list document 19 and its description of document 03 was not touched. No contract, test, mutation run, fork run, Permit2 record, wallet-lab record, fingerprint or evidence file was touched, and documents 05, 06, 10, 11, 12, 13, 14, 15, 16, 17 and 18, `eip712/types.json` and `config/pc_records.json` were not edited. `python -I spec/tools/freeze_readiness.py` prints the same result as before (NOT READY, 1 of 11; C-4 still reads 0 of 19). No constant is approved. Every claim about WalletConnect, EIP-1193, EIP-6963 and any wallet is `UNVERIFIED` (the sources are not retrieved and no wallet-lab run exists). No deposit address is specified or implemented, and no embedded or passkey wallet is part of v1.

**Raised and not decided** (17 open points, [19 §23](19-checkout-session-and-wallet-connect-profile.md)). OPN-01: an existing mandate cannot be used for a customer-present payment, because no typed confirmation or charge request exists (finding F-19), no mandate term or cycle allows it, and the address on the page is only a claim until a signature proves control. OPN-16: the document ends a session as `FAILED` only when positive evidence exists **and** no further attempt is allowed, so a rejected prompt returns the session to review; the sponsor should confirm that reading. OPN-02: [06 §3.2](06-initial-architecture.md) allows a new attempt after a final revert and document 19 does not.

## Unreleased (specification stays 0.5.0) — 2026-10-16 — corrective implementation: the actual contracts

**Protocol freeze is not approved.** The implementation evidence of the first pass was accepted as progress and freeze stayed blocked; the instruction of this pass was to resolve the findings it raised, split the oversized manager, bound the migration and test **the actual contracts**, not only the reference model. The specification was not expanded: the changes below are the ones that implementation forced (ADR-020 to ADR-023). `python -I spec/tools/freeze_readiness.py` still prints NOT READY and reports every unmet condition (C-9 now also needs the contracts' run, and C-11 is five parts, none waived). Numbers live in [REPORT.md](evidence/implementation/REPORT.md) §0a and §14, generated from the run files.

| Instruction | What was done | Where |
|---|---|---|
| 1 F-06, F-07, F-09; `types.json` the single source; regenerate everything | The snapshot is the 26 words of `snapshotEncoding`; `FiatTerms` lost the price pair; `newTermsHash` is `hashStruct(MandateTerms)`; one file generates the Solidity library (the model and the contracts), the TypeScript, the golden vectors, the Foundry golden tests (the contracts' too), the wallet payloads and `TYPES.md`; the shared loop bounds `MAX_EXPOSED_TOKENS_PER_ROUTER` and `MAX_SIGNERS_PER_SET` are in the same file; the strings of PC-09 are checked against it (new check [9] of the records) | [eip712/types.json](eip712/types.json), ADR-020, F-06/F-07/F-09 |
| 2 `customer`, `anchorStartsAt`, `boundsVersion` in the snapshot | Done; no ADR showed any of them unnecessary | [12 §5.3.2](12-router-lifecycle-and-migration.md), ADR-020 |
| 3 Versioned token-currency bounds registry | `TokenPolicyRegistry.publishBounds` (append-only versions, width ceiling PC-07); the mandate pins currency and bounds version; Q18 intersects the pinned and the current band; K.6 is "same version"; a version change is a widening in a revision | [11 §4.2](11-dual-cap-model.md), [12 §5.3.2](12-router-lifecycle-and-migration.md), ADR-020 |
| 4 Split the manager, at most 22,000 bytes, optimizer frozen, no generic delegatecall | The first complete manager was 34,067 bytes; it is now `MandateManager` (the only writer of mandate state), `UsageLedger`, `SuccessorValidator` (stateless, STATICCALL), `MandateGateway` (signatures) and `MigrationQueue`; every runtime is under the target with 0.8.24, cancun, 200 runs, no via-IR (`contracts/frozen-settings.json`); no DELEGATECALL, CALLCODE, SELFDESTRUCT, ORIGIN, CREATE or CREATE2 in any runtime; a manager with a validator that accepts everything still refuses what it owns | [contracts/](../contracts/README.md), ADR-021, `contracts_report.py`, `ManagerAlone.t.sol` |
| 5 A bounded, resumable migration; a conservative provisional `MAX_BATCH`; re-measure | `MigrationQueue`: a plan is a hash chain over the authorizations the customer committed to; anyone executes steps of at most `MAX_BATCH`; skip, abort, expire. A worst-case successor costs about 545,000 to 605,000 gas and 4,000 bytes of calldata, so 50 (about 30 million gas) does not fit: **PC-04 is now 10** (range 4 to 20). Measured on the compiler's EVM schedule and on forks of the three chains; the chains' own gas accounting and per-transaction caps are **not** measured (RP-19 open) | ADR-022, PC-04, `Gas.t.sol`, `Queue.t.sol`, `contracts-fork-runs.json` |
| 6 A record for `MAX_SIGNERS_PER_SET`; O(1) verification | **PC-19** (16, range 2 to 64, PROPOSED); `SignerSetRegistry` is its own contract; `verifySigner` costs the same gas for sets of 1, 2, 8 and 16 | ADR-023, PC-19, `Registries.t.sol` |
| 7 Compile and test the actual contracts; report five classes apart | Suites, a stateful fuzz that recomputes its invariants from a ghost list, a differential test against the model's exported vectors, a mutation campaign of the contracts, fork variants against each chain's real Permit2; the report keeps the reference model, the contracts, the Permit2 rebuild, the Permit2 forks and the wallet lab apart | [REPORT.md](evidence/implementation/REPORT.md) §0, §14 |
| 8 The ten wallet-lab run sets | **Not done**: they need real wallets and named reviewers. No record was created or simulated | [evidence/wallet-lab-kit/](evidence/wallet-lab-kit/README.md) |
| 9 C-11 unmet until canonical types, cross-language hashes, wallet signatures, a versioning policy and two approvals | C-11 is now five parts (TYPES, HASHES, SIGNATURES, VERSIONING, APPROVALS), each reported and none waived; HASHES is a recorded run of the Python, TypeScript and both Solidity implementations (`tools/eip712_crosscheck.py`) | [tools/freeze_readiness.py](tools/freeze_readiness.py) |
| 10 Re-run `freeze_readiness` and report every unmet condition | Done after all of the above; the result is in the report | REPORT §10 |

**Decisions the implementation raised and did not take** (findings F-18 to F-21): `recipientPolicy` has no defined meaning (F-18); the typed charge request and the merchant's charge signer are not specified (F-19); no rule requires a future expiry at activation (F-21). F-20 (Q3 cannot fail on its own) and F-22 (the signed domain names the manager while the gateway verifies) are resolved in the documents and the ADR. **Not built:** `chargeInitial`, `payOnceWithSignatureAndPermit`, `payOnceWithAuthorization`, `payOnce`, `RefundManager`, `EmergencyGuardian`, a plan opened by relayed signature.

**Documents touched:** [06](06-initial-architecture.md) (§4 contract table, ADR-020…023), [11](11-dual-cap-model.md) (bounds, Q18, the note on Q3), [12](12-router-lifecycle-and-migration.md) (snapshot, K.6, the plan instead of `activateSuccessors`, `MAX_BATCH`), [16](16-freeze-decision-report.md) (PC-04, the new PC-19 row, §8.1 audit scope), [17](17-account-compatibility-policy.md) (function names of the pin updates), [18](18-configuration-records.md) (regenerated: PC-04, PC-19, PC-18 range, PC-09 strings), the generated vector blocks, and the fingerprints.

## Unreleased (specification stays 0.5.0) — 2026-10-16 — implementation evidence

**Protocol freeze is not approved.** v0.5.0 was accepted as the basis of implementation; the specification was not expanded. This entry records the implementation evidence (toolchain, compile, tests, fork runs, Permit2 rebuild) and the few places where implementation showed a conflict. The numbers are in [evidence/implementation/REPORT.md](evidence/implementation/REPORT.md), generated from the run files. `python -I spec/tools/freeze_readiness.py` still prints **NOT READY**; it now has eleven conditions (C-11: the EIP-712 type strings are frozen by an approval of their fingerprint).

| Instruction | What was done | Where |
|---|---|---|
| 1 Reproducible Foundry toolchain | Foundry v1.8.5, solc 0.8.24 and 0.8.17, forge-std v1.9.7 and the Permit2 dependency graph pinned by URL, commit and SHA-256; policy-enforced fetch (HTTPS, github.com and codeload.github.com only, no other redirect, nothing executed), tree verification against GitHub | [toolchain/](toolchain/toolchain.lock.json) |
| 2 Compile and resolve every issue | The project compiles under the pinned toolchain; ABI and storage-layout snapshots, a lint disposition table; harness findings F-01…F-03, width finding F-04 | [build_report.py](tools/build_report.py), [foundry/](foundry/README.md) |
| 3 EIP-712 type strings, hashes, vectors | One source (`eip712/types.json`) for every type string including `ActivationTerms`, the revoke, pause, resume and reduce messages and the Pay Once witness; generated Solidity and TypeScript; golden vectors reproduced by four implementations and accepted by the real Permit2; wallet payloads. **Proposal, not frozen** | [eip712/](eip712/TYPES.md), [14 §8](14-protocol-freeze-pack.md) point 5 |
| 4 O(1) or bounded; no unbounded loop on an exit | Exposure index O(1); registry live count O(1); signer sets bounded (a new constant, `MAX_SIGNERS_PER_SET`, that needs its own configuration record); a loop audit that every loop of the sources must pass; gas tests of the worst cases | [loop_audit.py](tools/loop_audit.py), `LoopBounds.t.sol`, F-05, F-11, F-12 |
| 5 Layer 3 exclusivity, Layer 2 coexistence | Claim 1 and I-MIG-8 worded as `|Exec3(L)| ≤ 1` with Layer 2 outside it; tests and a stateful invariant | [12 §5.5, §12](12-router-lifecycle-and-migration.md), `Exec3.t.sol` |
| 6 Suites | Unit, fuzz, invariant, mutation (151 of 151 killed), integer width, timestamp, signer set, pin, shared allowance, migration, reentrancy (finding F-16: the model's charge pulled through Permit2 before writing its effects, the opposite of the order of [11 §5](11-dual-cap-model.md); corrected, the specification was right) | [REPORT §6](evidence/implementation/REPORT.md) |
| 7 Fork tests on three chains | The freeze subset and the witness suite against the real Permit2 on Ethereum, Base and Arbitrum One at pinned blocks | [REPORT §7](evidence/implementation/REPORT.md) |
| 8 Permit2 rebuild and CREATE2 comparison | Reproduced: the canonical address, the creation code and every byte of the deployed code except the two immutables, which the compiler's artifact names; software-level isolation only | [evidence/permit2/rebuild.json](evidence/permit2/rebuild.json), [REPORT §8](evidence/implementation/REPORT.md) |
| 9 Wallet lab and signed run records | **Not done** (real wallets and named people are needed). A kit, the wallet payloads and a signature verifier exist; no record was created or simulated | [evidence/wallet-lab-kit/](evidence/wallet-lab-kit/README.md) |
| 10 freeze_readiness | Stays NOT READY; C-9 (Foundry) is now recorded from a run file; C-11 added | [tools/freeze_readiness.py](tools/freeze_readiness.py) |

**Documents touched (conflicts and statuses only):** [11 §3](11-dual-cap-model.md) (the stale `accountPin bytes32`, F-08), [12 §5.5 and §12](12-router-lifecycle-and-migration.md) (Claim 1 and I-MIG-8 wording, test pointers), [14 §8](14-protocol-freeze-pack.md) point 5 and [16](16-freeze-decision-report.md) (FZ-22 written as a proposal; the rebuild and fork statuses), [17 §5.3](17-account-compatibility-policy.md) (the pointer for `ActivationTerms`), [18](18-configuration-records.md) PC-09 (regenerated: the new type strings as DERIVED, the open points). **Open decisions the implementation raised and did not take:** F-06 and F-07 (the implemented snapshot hash differs from document 12), F-09 (price bounds per mandate or per token), a configuration record for `MAX_SIGNERS_PER_SET` (none exists), F-12 (the storage design and `MAX_BATCH` must be re-measured on the real contracts).

## 0.5.0 — 2026-10-16 — shared-allowance migration, account-pin semantics, signer-set emergency removal, pinned Permit2, executable suites, three-tier roadmap

**Protocol freeze is not approved.** The v0.4 direction is accepted for testnet engineering (DEC-16). `python -I spec/tools/freeze_readiness.py` prints **NOT READY (0 of 10 conditions met)**. The four things the sponsor named as preconditions are each still open or unreviewed: the shared-allowance migration rework and the account-pin semantics are specified but not reviewed, compiled, tested or audited; the Permit2 commit is pinned and answered from an automated read, but the E2 human review, the rebuild comparison and the fork tests are not done; the wallet-lab evidence is 0 of 10 run sets. See [16](16-freeze-decision-report.md).

### Where each instruction landed

| # | Instruction | What was done | Where | Status |
|---|---|---|---|---|
| 1 | Rework `activateSuccessor` for Permit2's shared owner-token-spender allowance; define normal and emergency migration separately, including siblings that still rely on RouterV1 | Read at the pinned commit: **the allowance is keyed `(owner, token, spender)`, `approve` overwrites amount and expiration, `lockdown` zeroes only the amount** (F1…F6). O1 of 0.4 is split into **O1N** (normal: the allowance may remain, bounded, while a sibling mandate uses the token; zero or expired once none does) and **O1E** (emergency: every token any live mandate of the customer uses on that router). The mode is derived from the router's registry state (`SECURITY` deprecation, disabled, sunset, retired are `EMERGENCY`). An **on-chain exposure index** (`live(customer, router, token)`, bounded by PC-18) makes both rules checkable; activation writes nothing to Permit2 and touches no sibling. Plan kinds `NORMAL_FULL`, `NORMAL_PARTIAL`, `EMERGENCY`; planner rule R-L2-SHARED; validators NC-20, NC-21; MIG-TV-30…45; invariants I-MIG-7 (rewritten), I-MIG-10, I-MIG-11 | [12 §5.3–§5.5, §12](12-router-lifecycle-and-migration.md), [05 §2.1, §6.1, §9, §11](05-evm-authorization-decision-tree.md), ADR-015, CF-019, RISK-035, RISK-036, PB-054 | Specified; **not reviewed, not run in any test** |
| 2 | Define `AccountPin` precisely (account mode, delegation designator hash, delegate address, delegate code hash, implementation family, pin version, signature mode); say what the contract verifies and what stays off chain | A seven-field typed struct (the designator hash is the `accountCodeHash` of a 7702 account); `PIN_WELLFORMED`, `PIN_OK` (now also `EXTCODEHASH(delegate)` in `consume`), `nextPinVersion`; the mandate stores the hash and the version, the struct travels in events and `consume` calldata; a field-by-field table of **verified on chain** versus **off-chain control** | [17 §5.1–§5.5](17-account-compatibility-policy.md), ADR-018, OD-037, PB-055 | Specified; review pending |
| 3 | Bind ERC-1271 evidence to the pin; invalidate signature capability when delegate, implementation, wallet version or code hash changes | `AUTH` (signature mode of the stored pin; the ERC-1271 path is open only while `PIN_OK` holds, so a delegate or account code change closes it **on chain**); `SigCapabilityRecord` bound to `pinHash` and `pinVersion`; **eleven invalidation triggers** with effects on planner, signer policy and contract; two capabilities kept apart (`fastpaySig`, enforced on chain; `permit2Sig`, Permit2 is external); ACP-TV-25…44; WL-36…40 | [17 §5.4, §5.6, §9](17-account-compatibility-policy.md), [13 §3.2, §7.3](13-eip7702-delegation-inspection.md), [15 §3.5](15-wallet-lab-matrix.md) | Specified; the lab runs are not done |
| 4 | Export all Python migration-model vectors into Foundry tests; add fuzz, invariant, mutation, integer-width, timestamp-boundary and shared-allowance tests | `tools/protocol_model.py` (executable model), `tools/export_foundry.py` (deterministic export, `--verify` in `check_all`), `tools/solidity_lint.py`, and the Foundry project [foundry/](foundry/) with the suites named in the instruction plus signer-set, pin, configuration-range and **Permit2 fork** tests; model checks [5]…[8] (shared-allowance exploration, signer-set exploration, pin/AUTH truth table, Python mutation analysis) | [12 §12](12-router-lifecycle-and-migration.md), [foundry/README.md](foundry/README.md) | Python side runs (see below). **The Solidity has not been compiled or run: there is no Foundry or solc on the authoring machine and none was downloaded** |
| 5 | Formalize signer-set emergency removal: no grace for a compromised signer; normal rotation honors only previously issued quotes for a bounded period | Two transitions with two guarantees (table), key tombstones that nothing can clear, `stopSignerSet`, the guardian never adds; Q1 and Q13 restated; `QUOTE_SET_GRACE ∈ [MAX_QUOTE_TTL, 2·MAX_QUOTE_TTL]`; SR-1…SR-7; CAP-TV-23…32 | [11 §4.2, §4.7](11-dual-cap-model.md), OD-034, OD-036, PB-056 | Specified; model-checked in Python |
| 6 | Split the roadmap into testnet reference implementation, private mainnet beta, full GA platform with P50/P75/P90 per milestone | Three tiers, each simulated as **its own network**: tier 1 TRI (66 nodes, 451 pw, fractions `TRI_SCOPE`), tier 2 PMB (the ancestors of RG-010, 183 nodes, 1,394 pw), tier 3 GA (349 nodes, 3,435 pw). P50 / P75 / P90 for **every milestone** (TRI-1…4, PMB-1…12, GA-1…16) in three scenarios (six for tier 3) in 07 §3.2. Last milestone, recommended squads, P50 / P75 / P90: TRI-4 testnet reference exit **W76 / W82 / W88**; PMB-12 private beta go **W134 / W148 / W158**; GA-14 GA go **W181 / W198 / W213** (as organized: W84 / W90 / W96; W149 / W162 / W173; W211 / W228 / W245). Protocol freeze W32 / W34 / W36 (v0.4: W27 / W29 / W31) after three new explicit waits. The v0.5 estimate overlay adds **68 pw** (shared allowance 17, account pin 20, Foundry export 14, signer sets 8, constants 3, Permit2 pin 6) and 25 stories (966 stories, 1,084 backlog issues). **Finding:** part of the later dates is queueing in the model, not added work — a sensitivity that serves Phase 0 packages first gives PMB-12 W119 / W129 / W137 and GA-14 W167 / W180 / W192 (the v0.4 values); which queue rule applies is a staffing decision that has not been taken (07 §3.5) | [07 §3](07-delivery-plan.md) | Exploratory |
| 7 | Convert the 17 production-blocking constants into individually approved configuration records | 18 records (PC-01…PC-18) in `config/pc_records.json`, document 18 generated from them, each with accountable owner and required approvers, unit, rationale (the parts that are my proposal are marked), evidence required (existing ids or `none yet`), safe range with the direction of failure, the test (existing ids and planned Foundry names), release gate, change control and an **approval block that is NOT SIGNED for every approver**; 23 cross-constraints are executable and checked by `tools/build_config_records.py --verify` (0 errors; 22 mutations of the data are all rejected). Found while building them: the EIP-712 type strings of `ActivationTerms` and of the revoke, pause, reduce and resume messages are written in no document (FZ-22, 14 §8 point 5); the cycle rule of PC-16 has no bound on lateness (14 §8 point 6); PC-05 is `VALUE_PENDING` (Finance) | [18](18-configuration-records.md), [config/pc_records.json](config/pc_records.json) | **0 of 18 approved** |
| 8 | Pin the Permit2 source commit and complete the wallet-lab evidence before requesting protocol freeze | **Commit pinned** (`cc306b601f172c51bc04334a109e98340456620b`, the commit of the repository tag named for the canonical address); 17 source files read and their Git blob hashes verified; **PR-01…PR-16 answered with file and line citations** (E1 pinned); the deployed code read from Ethereum, Base and Arbitrum One (2 to 5 providers each): 9,152 bytes, differing only in two immutables, masked hash `0x4633…b546`; the deployed dispatcher exposes exactly the 15 external functions of the source. **Not done:** E2 sign-off by two named reviewers, the rebuild comparison (CREATE2 address check), the fork tests, and **the wallet-lab runs (0 of 10 sets)** — they need real wallets and people; the run-record format, directory, checker and template are in place | [16 §5, §9](16-freeze-decision-report.md), [evidence/](evidence/README.md), [tools/permit2_pin_check.py](tools/permit2_pin_check.py), [tools/freeze_readiness.py](tools/freeze_readiness.py) | **Freeze blocked** |

### Findings of the Permit2 read that changed or sharpened the design

1. **The allowance is shared and `approve` overwrites it** (PR-02, PR-05): the whole item-1 rework rests on this; the 0.4 predicate O1 treated the allowance as the mandate's.
2. **Permit2 emits no event on a pull** (PR-13): confirmation is the token `Transfer` event plus an `allowance` read.
3. **The per-chain code hash is not a constant** (two immutables, §5.2 of 16): PC-13 and EV-P01 compare a masked hash or a rebuild.
4. The 0.4 correction of the expiry boundary (`e < now`) is confirmed at source level (PR-07), still pending E2 and the fork test.
5. No earlier E1 claim was contradicted; RISK-034 is not triggered by this read.

### Corrections to my own earlier text (v0.4 → v0.5)

| Item | Was (v0.4) | Now |
|---|---|---|
| Old-permission predicate | O1: allowance zero or expired for every token of the predecessor, as if mandate-specific; siblings were unfunded and held | O1N / O1E on the shared allowance; a normal migration never unfunds a sibling |
| Pin | One `bytes32`; "the delegate contract's own code changes" was not seen by the chain | Seven-field struct; the delegate's code hash is checked on chain (mode 2); the implementation behind a proxy is still not seen |
| Signature authority | ERC-1271 evidence was a register row | Bound to the pin and `pinVersion`; ERC-1271 path closed on chain when the account or delegate code changes |
| Signer-set removal | "Immediately", but grace and removal were not separated | No grace after removal, permanent tombstone, set stop; planned rotation bounded and earlier-quotes-only |
| Production-blocking constants | 17, a table | 18 records (PC-18 added by the exposure index); none approved |
| Permit2 | "commit not pinned"; bytecode "equals the pinned build" | Pinned; the code hash is per chain; the rebuild is open |
| Freeze conditions | Nine, in prose | Ten, computed from evidence by a tool (adds the executable suites) |

### New identifiers

ASM-034…036 · OD-035…037 (OD-034 revised) · CF-019 · RISK-035…037 · PB-054…056 · ACP-TV-25…44 · MIG-TV-30…45 (05, 21…23, 26, 28, 29 revised) · CAP-TV-23…32 · TV-31…36 · NC-20, 21 · WL-36…40 · EVL-15 · UX-17, 18 · UD-17…19 · DEC-16…21 · PC-18 · FZ-26…29, 44, 45 · FG-23, 24 · EV-P14, 15 · SR-1…SR-7 · I-MIG-10, 11 · I-ACCT-SIG, I-ACCT-VERSION · document 18 · directories `evidence/`, `foundry/`, `config/` · tools `protocol_model.py`, `export_foundry.py`, `solidity_lint.py`, `permit2_pin_check.py`, `freeze_readiness.py`, `build_config_records.py` · `jira/revisions_v05.py`.

### Changes of my own that need approval

- The mode boundary: `SECURITY` deprecation is `EMERGENCY` (it interrupts siblings until their successors exist) and a normal migration requires only a **bounded** residual allowance (OD-035).
- The exposure index and its bound `MAX_EXPOSED_TOKENS_PER_ROUTER = 8` (PC-18), and the permissionless `retire`.
- The `delegateCodeHash` check in `consume` (about 2,600 gas, unmeasured), the per-mandate pin with a batch update, and `implementationFamily` as a signed label without an on-chain registry (OD-037).
- The eleven signature-capability triggers and the choice to keep `fastpaySig` (enforced) and `permit2Sig` (evidence only) apart.
- Tombstones that not even governance can clear; the guardian cannot add keys or sets; recovery waits for the 72 h timelock (OD-036).
- Pinning `cc306b6` (the deployment tag) rather than the branch head, and the ten freeze conditions of [16 §1](16-freeze-decision-report.md).
- The tier-1 scope fractions, the three new waits before the freeze (`L_COUNSEL_NOTICE`, `L_PERMIT2_E2`, `L_PC_APPROVAL`), the +68 pw overlay and its 25 stories, and the fact that the recommended squad sizes were **not** re-searched for the v0.5 estimates (07 §3.4)

### Verification status, stated plainly

| Item | Status |
|---|---|
| Python models, vectors, mutation analysis, document consistency | **Run** (`python -I spec/tools/check_all.py`): shared-allowance explorations 720 states / 9,078 transitions, signer-set exploration 17,636 states / 85,452 transitions, pin and `AUTH` truth table 648 cases, 151 mutants of the model all killed by the exported vectors, 505 atomicity cases, Lemma M 60,000 random pairs with no violation |
| Solidity reference model and all Foundry suites (33 files, 226 test functions, 10 invariants) | **Written, not compiled, not run.** Only a structural lint ran (`solidity_lint.py`) plus one review read by a second reader, which found and fixed an arithmetic-overflow hazard in the fuzz seeds. Expect compile errors on the first `forge build` ([foundry/README.md](foundry/README.md)) |
| Permit2 deployed code and selector audit | Read on three chains; re-runnable with `permit2_pin_check.py --online` |
| Permit2 source-to-bytecode match, E2 review, fork tests | **Not done** |
| Wallet lab (EVL-01…10) | **Not done (0 of 10)** |
| Constants | **0 of 18 approved** |
| Audit, legal review, any wallet or chain test | **None** |

### Still open

Everything in [16](16-freeze-decision-report.md) §1: the ten conditions. Nothing in this workspace is audited, legally reviewed, or tested on any wallet or chain.

## 0.4.0 — 2026-10-15 — Account Compatibility Policy, exact migration predicates, complete quote schema, work-package schedule

**Protocol freeze is not approved.** The wallet-lab evidence and the pinned Permit2 source review have not produced evidence; see [16](16-freeze-decision-report.md).

### Where each instruction landed

| # | Instruction | What was done | Where |
|---|---|---|---|
| 1 | Replace backend-only delegation revalidation with an Account Compatibility Policy; define account modes; say which permit unattended charges | Five modes by boolean predicates (`PLAIN_EOA`, `EOA_7702_VERIFIED`, `SMART_4337`, `WALLET_1271`, `UNKNOWN_CODE`); permission matrix; the unattended-charge predicate `UNATTENDED_OK`; an **on-chain account pin** enforced in `consume` (`AccountCodeChanged`) and updated only by the customer; the backend revalidation kept as layer B for what the chain cannot see; limits stated (§4.1); 24 vectors ACP-TV. **OD-029 is reversed** | [17](17-account-compatibility-policy.md), [13](13-eip7702-delegation-inspection.md), ADR-018, [05 §4](05-evm-authorization-decision-tree.md) |
| 2 | Clarify `activateSuccessor` with exact boolean predicates and atomic and legacy flows | Predicates A1…O1 with errors, effects and postconditions; a requirement-to-predicate table; the atomic flow and the legacy flows with state tables; the shared-allowance (sibling lineage) rule; the no-overlap claim `AuthRouters(L) ≤ 1` | [12 §5.3–5.5](12-router-lifecycle-and-migration.md) |
| 3 | Formalize the migration snapshot; prove no increase of expiry, merchant scope, token scope, remaining cap, fee cap or slippage cap; bind cycle identity independently of the router | On-chain snapshot (static terms signed, usage logged); containment clauses K.1…K.9; Lemma M (monotone authority) with a guard-by-guard proof; executable `contained()` with vectors; `lineageId`, `mandateId`, `cycleId`, `paymentId` derived without any router input; conversion adoption moved to a new manager and mandate so that nothing widens through `activateSuccessor` | [12 §5.3.2–5.3.5, §5.7](12-router-lifecycle-and-migration.md), [11 §3.1](11-dual-cap-model.md), [tools/eip712_vectors.py](tools/eip712_vectors.py) |
| 4 | Complete `PriceQuote` v1; prove a quote signer cannot override a mandate | Fifteen fields (added `issuedAt`, `nonce`, `signerSetVersion`, `registryVersion`, `routeHash`, `priceSourceSetHash`), domain, Q1…Q20, versioned signer sets with rotation, grace and emergency removal; non-interference theorem and corollaries N1…N7 with test obligations; vector regenerated by code | [11 §4](11-dual-cap-model.md) |
| 5 | Explicit FS/SS/FF dependencies with lags; Monte Carlo at work-package level; exploratory; milestone P50/P75/P90 | 305 work packages, 969 typed dependencies, the rule for each in [jira/dependencies.csv](jira/dependencies.csv); results labeled **EXPLORATORY** | [07 §3](07-delivery-plan.md), [jira/schedule_model.py](jira/schedule_model.py) |
| 6 | Keep `program`; prohibit delivery work in it | `program` limited to four coordination epics; eleven epics reclassified with reasons; the generator fails on an unlisted program epic or on delivery vocabulary | [07 §6.2](07-delivery-plan.md), [jira/revisions_v04.py](jira/revisions_v04.py) |
| 7 | Primary Permit2 revocation flow from tested primitives; zero-amount permit disabled until fork and lab | `Permit2.lockdown` by transaction defined by fork tests RV-T01…RV-T12; gate tests ZP-T01…ZP-T08 and WL-31 for the experimental flow, still off | [05 §2.2](05-evm-authorization-decision-tree.md) |
| 8 | Formal freeze-decision report | Accepted decisions, unresolved decisions, unverified external facts (with what changes if adverse), testnet-safe and production-blocking constants, exact audit scope, exact wallet-lab evidence, the pinned Permit2 review checklist; **not approved** | [16](16-freeze-decision-report.md) |

### Schedule (EXPLORATORY; weeks from the start of Phase 0)

| Milestone | As organized P50 / P75 / P90 | Recommended squads P50 / P75 / P90 | Recommended + 7 contractors P50 / P75 / P90 |
|---|---|---|---|
| Protocol freeze (RG-016) | W28 / W30 / W32 | W27 / W29 / W31 | W25 / W27 / W29 |
| Contract audit freeze (audits start) | W65 / W70 / W74 | W60 / W64 / W68 | W52 / W56 / W60 |
| Phase 1 exit; testnet alpha (RG-002, R3) | W85 / W95 / W102 | W66 / W77 / W86 | W55 / W59 / W63 |
| Audits complete (RG-005) | W100 / W106 / W112 | W93 / W99 / W103 | W83 / W88 / W92 |
| Private beta go (RG-010) | W137 / W150 / W163 | W118 / W131 / W145 | W106 / W114 / W122 |
| Public beta go (RG-011) | W154 / W168 / W181 | W136 / W149 / W161 | W129 / W139 / W148 |
| GA go (RG-012) | W198 / W217 / W234 | W167 / W183 / W198 | W159 / W172 / W184 |
| v1.1 conversion enablement (RG-013) | W214 / W234 / W251 | W191 / W209 / W226 | W177 / W190 / W202 |

The v0.3 schedule used a uniform 50% overlap rule and gave GA P50 W173 (recommended) and W192 (as organized). The change comes from the typed dependencies at work-package level and about 50 pw of added work; the squad-bound conclusion is unchanged: Protocol and Contracts and Payments Core bind the dates, and the heavy upper tail of Phase 0 exit (both shapes) comes from small readiness packages queuing behind contract-path work, not from the GA critical path. In the recommended shape the dates after the private beta are bound by the operations chain CANARY → TUNE → SCALE → OPSMAT → RELREADY (Platform, Product and DevEx work), not by the contract path.

### Corrections to my own earlier text (v0.3 → v0.4)

| Item | Was (v0.3) | Now |
|---|---|---|
| Account-change control | Backend revalidation only; no on-chain pin (OD-029 (a)) | Account Compatibility Policy with an on-chain pin (OD-029 (b)); revalidation is layer B |
| Old-permission predicate | `amount = 0 ∨ expiration ≤ now` | `amount = 0 ∨ expiration < now`: Permit2 reverts only when `block.timestamp > expiration`, so an allowance is usable in the block whose timestamp equals its expiration (flagged E1; PR-07, MIG-TV-22) |
| `lineageId` | The id of generation 0 | Derived from chain, manager, customer, merchant, subscription reference and a creation nonce; no router input |
| `activateSuccessor` signature | Covered the predecessor's terms **and counters** implicitly | Covers the static terms snapshot only (usage is logged), so a charge in flight does not invalidate a relayed authorization |
| Conversion adoption | Opt-in successor via `activateSuccessor` | New manager and new mandate with remaining-headroom caps; a v1.0 mandate can never carry a conversion consent (`extensionsHash` must be zero) |
| Quote | Ten fields, Q1…Q16, `sourcesCommit` | Fifteen fields, Q1…Q20, `priceSourceSetHash` checked against the registry |
| Guardian row of document 04 §1.1 | The authority-matrix row had overwritten the principals row (an editing error in 0.3) | Restored |
| Planner | 1.2.0 | 1.3.0 (account mode, pin, `ACCOUNT_MODE_UNKNOWN`, TV-27…TV-30) |

### New identifiers

ASM-031…033 · OD-032…034 (OD-029 reversed) · CF-017, 018 · RISK-032…034 · TM-19 · PB-052, 053 · G-10, 11 · EV-P12, 13 · RP-29, 30 · ACP-TV-01…24 · MIG-TV-19…29 · CAP-TV-14…22 · TV-27…30 · NC-18, 19 · RV-T01…12, ZP-T01…08 · WL-32…35 · FZ-24, 25 · FG-19…22 · DEC-01…15, UD-01…16, UX-01…16, PR-01…16, PC-01…17, EVL-01…14 (document 16) · documents 16 and 17 · tools `sync_vectors.py`, `check_all.py` · `jira/dependencies.csv`, `jira/stories.py`, `jira/revisions_v04.py`.

### Changes of my own that need approval

- The recommended squad shape was recomputed under the work-package model (OD-031).
- The queue discipline (longest remaining path first), the dependency rules and lags, the split of cross-squad epics, the hiring ramp and every wait range (all in [07 §3.4](07-delivery-plan.md)).
- The proposals for the production-blocking constants ([16 §7](16-freeze-decision-report.md)).
- The reclassification of eleven epics out of `program` and the banned-vocabulary lint.
- Which account modes are ON at launch (OD-032): recommended `PLAIN_EOA` plus rows as the lab produces them.

### Still open

Everything in [16](16-freeze-decision-report.md) §1: the wallet-lab evidence (0 of the 10 freeze run sets), the pinned Permit2 review (not started), the constants (0 of 17), the open decisions and facts. Nothing in this workspace is audited, legally reviewed, or tested on any wallet or chain.

## 0.3.0 — 2026-10-14 — final corrections before protocol freeze

(Documents 03–13 refer to the correction set as "of 2026-10-13"; it is the same set.)

### Where each correction landed

| # | Correction | Decision | Where | Status |
|---|---|---|---|---|
| 1 | Is swap execution code absent from Router v1, or fully in the v1 audit scope? A feature flag is not a security boundary | **Absent.** No conversion code, adapter call, adapter or conversion registry in any v1.0 contract; conversion arrives as Router v1.1 + `ConversionPolicyRegistry`, separately audited, adopted by opt-in. `Mandate.extensionsHash` is reserved and must be zero. Mechanical absence checks in the release pipeline | [09](09-capability-boundaries.md) (§0, §4 conditions C1/C2, §7 checks), [06](06-initial-architecture.md) ADR-013, [03](03-assumptions-decisions-risks.md) OD-012, CF-011, [08](08-production-blockers-and-release-gates.md) PB-040 | Done in the specification |
| 2 | Router migration as mandate lineage; new router-specific authorization; explicit revocation of the old permission | One router per mandate for life; counters and history keyed by lineage; `activateSuccessor` requires the router-specific authorization and checks **on chain** that the old Permit2 allowance is unusable; plan order S1 grant new, S2 revoke old, S3 activate; partial states Q0…Q3; revision versus migration | [12](12-router-lifecycle-and-migration.md) (state machine §5), [06](06-initial-architecture.md) ADR-015, I-MIG-1…7, MIG-TV-01…18, PB-042, RG-015 | Done in the specification |
| 3 | Revalidate EIP-7702 delegation before every unattended charge; mismatch pauses `DELEGATION_UNVERIFIED` | `DelegationEvidence` baseline; revalidation compares delegate address, delegate code hash, proxy implementation, ERC-1271 probes and account code; `OK` / `INDETERMINATE` / `MISMATCH(diffs)`; a third on-chain pause bit; no token fallback; pseudocode and DRV-01…25 | [13](13-eip7702-delegation-inspection.md) (§7, §11), ADR-018, PB-049, OD-029 (no on-chain code pin) | Done in the specification |
| 4 | Formalize the signed quote schema; classify every cap | `PriceQuote` v1 (EIP-712) with validity predicate Q1…Q16; each cap or limit is `ONCHAIN_HARD`, `QUOTE_BOUND_ONCHAIN` or `BACKEND_ONLY` (22 rows); blast radius; reproducible digest vector | [11](11-dual-cap-model.md) (§2.1, §4), [tools/eip712_vectors.py](tools/eip712_vectors.py), ADR-016, PB-041, PB-051 | Done; the vector was produced by code and checked against the document |
| 5 | Replace the universal six-story-type rule with epic profiles | Nine profiles (the eight requested plus `program`, OD-030) with required / optional / not-applicable story types; per-profile definitions of done; the generator enforces it | [07 §6.2](07-delivery-plan.md), [jira/model.py](jira/model.py), [jira/build_backlog.py](jira/build_backlog.py) | Done; 118 epics, 903 stories |
| 6 | P50, P75, P90 schedules from critical-path constraints | Monte Carlo over the epics' dependency network with per-squad capacity curves and queues and external waits; scenarios; sensitivity; the aggregate view is shown for contrast | [07 §3](07-delivery-plan.md), [jira/schedule_model.py](jira/schedule_model.py) | Done; **the v0.2 GA date is withdrawn** |
| 7 | Zero-amount permit revocation experimental; specify the primary flows | Primary flows are transactions (token `approve(0)`, `Permit2.lockdown`, `approve(…,0,0)`, `invalidateNonces`) plus `revoke`/`revokeBySig`; the signed zero-amount `permit` is behind `revocation.zeroPermit.enabled` (off) pending EV-P08; the plan validator rejects it | [05 §2.1](05-evm-authorization-decision-tree.md), [12 §6](12-router-lifecycle-and-migration.md), ADR-019, PB-050, NC-17, WL-19/WL-31 | Done in the specification |

### New deliverables (the eight requested)

| Requested | Where |
|---|---|
| Protocol freeze checklist | [14 §1](14-protocol-freeze-pack.md) (FZ-01…FZ-80; gate RG-016 in [08](08-production-blockers-and-release-gates.md)) |
| Unresolved production blockers | [14 §3](14-protocol-freeze-pack.md) and [08](08-production-blockers-and-release-gates.md) (51 blockers, all `OPEN`) |
| Exact testnet implementation scope | [14 §4](14-protocol-freeze-pack.md) |
| Contract audit scope | [14 §5](14-protocol-freeze-pack.md) |
| Wallet-lab matrix | [15](15-wallet-lab-matrix.md) |
| Signed quote schema | [11 §4](11-dual-cap-model.md) |
| Router migration state machine | [12 §5](12-router-lifecycle-and-migration.md) |
| Delegation revalidation pseudocode and golden vectors | [13 §7.3 and §11](13-eip7702-delegation-inspection.md) |

### Schedule: what changed and how to read it

- v0.2 compared aggregate capacity with demand per phase and reported GA at W108. On the same scope the aggregate view still gives about W90. The critical-path model gives, for GA (P50 / P75 / P90): **W192 / W207 / W222 as organized** and **W173 / W186 / W200 with squad sizes rebalanced** (W163 / W175 / W188 with seven more people on the contract and core path). Contract audit freeze, P50: W64 as organized, W53 rebalanced.
- The reason is structural, not a re-estimate: the Protocol and Contracts and Payments Core squads carry far more work than their size allows; audits, pen test, observation periods and counsel add elapsed time that people cannot compress. W108 is roughly the dependency-and-wait floor with unlimited staffing.
- Person-week demand for v1.0 GA changed from 2,665 to 2,601 (−2.4%): conversion plumbing and non-applicable story types out; lineage, revalidation, quote schema and revocation work in. Post-GA scope grew by 130 pw (Router v1.1 epics).
- All of the above depends on the inputs listed in [07 §3.4](07-delivery-plan.md); none is a measurement.

### Changes of my own that need approval

- A ninth profile, `program` (OD-030).
- The "recommended" squad shape (OD-031), produced by a greedy search over a model that ignores non-gating work.
- OD-029: no on-chain code pin (revalidation is the control).
- The 50% start-to-start overlap, the split of cross-squad epics, the hiring ramp and every external wait range in the schedule model.
- Fingerprints (FG-01…18) and the Freeze Change Request process in [14](14-protocol-freeze-pack.md).

### Corrections to my own earlier text (v0.2 → v0.3)

| Item | Was (v0.2) | Now |
|---|---|---|
| Conversion boundary | "Dormant" code in Router v1 behind flags G1/G2/G3 | Code **absent** from Router v1; conditions C1 (consent and router capability) and C2 (on-chain policy) are the boundary; the rollout switch R is only operational |
| Router migration | In-place `rebindRouter`; `exportOut`/`importFrom` hooks | Lineage with `activateSuccessor`; no hooks; the old permission must be unusable first |
| Delegation | Inspected and recorded at activation | Revalidated before every unattended charge |
| Revocation | Signed zero-amount `permit` listed as a gasless option | Experimental and off; transactions are primary |
| Planner version | 1.1.x | 1.2.0 (router capability `conversion`, `ROUTER_LACKS_CONVERSION`, TV-26) |
| Schedule | Aggregate capacity; GA W108 | Critical path; GA P50 W173 (recommended) / W192 (as organized) |
| Backlog rule | Six story types in every epic | Profiles |

### New identifiers

ASM-029, 030 · OD-029, 030, 031 · CF-014…016 · RISK-029…031 · ADR-018, 019 · TM-17, 18 · PB-049…051 · RG-016 · CLM-053 · EV-P07…P11 (EV-P06 revised) · RP-25…28 · DRV-01…25 · MIG-TV-01…18 · CAP-TV-01…13 · TV-26 · NC-16, 17 · FZ-xx, FG-xx (document 14) · WL-01…31 (document 15) · `EPIC-P1-REVOKE`, `EPIC-P6-ROUTERV11`, `EPIC-P6-AUDITV11`, `EPIC-P6-OPTIN` (new); `EPIC-P1-CONVBOUND` (dropped).

### Still open after this revision

- Everything in [08 §3](08-production-blockers-and-release-gates.md); nothing in this workspace is audited, legally reviewed, or tested on any wallet or chain.
- The facts in [14 §3.1](14-protocol-freeze-pack.md) that could still change the frozen protocol (Permit2 behavior at a pinned commit, real wallet delegates under ERC-1271, MetaMask's actual delegate, revocation per token, chain facts, immutable constants).
- Every E1 claim still needs a human read (E2); Trust Wallet is `UNKNOWN`; MetaMask is `documented`, lab verdict `UNTESTED`.

## 0.2.0 — 2026-10-13 — mandatory corrections from the sponsor directive

### Where each correction landed

| # | Directive | Where | Status |
|---|---|---|---|
| 1 | FastPay v1 is **not** permanently swap-free; design swap and DEX-adapter boundaries from the beginning; direct stablecoin settlement ON for MVP; stablecoin conversion behind a feature flag; general-token conversion disabled until audit and token-lab approval | [09](09-capability-boundaries.md) (matrix, gates G1–G3, flags, enablement criteria), [06](06-initial-architecture.md) §2.2/§4 + ADR-013, OD-012 (decided), PB-040/045/046/047, RG-013/014 | Done in the specification; contracts and services still to be built |
| 2 | EIP-7702: prefer wallet-managed upgrades via capability discovery; inspect and record the resulting delegation implementation, bytecode hash, account state, revocation path and compatibility evidence; never describe delegation as transaction-temporary | [13](13-eip7702-delegation-inspection.md), [05](05-evm-authorization-decision-tree.md) §3.3/§4/§8, ADR-007/017, CLM-016, CLM-050, TM-16, PB-043; a wording lint is a test | Done in the specification |
| 3 | PaymentRouter immutable and versioned, with a **complete migration protocol**: new authorization, old permission revocation, sunset periods, customer consent, stranded-mandate prevention, events, rollback, customer communication | [12](12-router-lifecycle-and-migration.md), ADR-001/009/015, OD-004 (decided) and OD-026, PB-042/048, RG-015, RB-031/032 | Done in the specification; parameters are proposals |
| 4 | Dual cap model: on-chain per-token atomic-unit hard caps and fiat-equivalent business caps through signed expiring quotes with bounded price inputs; define what is authoritative on chain and what is backend-only | [11](11-dual-cap-model.md) (classification table §2.1, blast radius §6), ADR-004/016, OD-006 (decided) and OD-027, PB-041 | Done in the specification |
| 5 | Backlog: every epic has implementation, security, observability, test, migration and operational-readiness stories plus acceptance criteria; do not call it implementation-complete | [jira/](jira/) (generator enforces it), [07](07-delivery-plan.md) §6 | Done; 115 epics, 848 stories; described as a planning baseline |
| — | MetaMask EIP-5792 evidence: unconfirmed → documented, runtime detection still required | [02](02-source-register.md) CLM-040/043 (E1), [05](05-evm-authorization-decision-tree.md) §10 | Done |
| — | Trust Wallet stays `UNKNOWN` pending wallet-lab testing | [05](05-evm-authorization-decision-tree.md) §10, [08](08-production-blockers-and-release-gates.md) §4 | Unchanged |
| — | Separate Pay Once (`SignatureTransfer`) from FastPay recurring (`AllowanceTransfer` + mandate) | [10](10-pay-once-protocol.md), [05](05-evm-authorization-decision-tree.md) §2, ADR-014, rules S-1…S-4 | Done |
| — | Exact v1, v1.1, v2 capability boundaries | [09](09-capability-boundaries.md) §2 | Done |
| — | Re-estimate delivery | [07](07-delivery-plan.md) §5 (generated, reconciled by cause) | Done |

### New evidence gathered (all by direct page fetch, E1)

- MetaMask's official docs (two pages): atomic batching, `supported`/`ready`, upgrade to a MetaMask smart account, chain list (Avalanche not listed), no delegate named, persistence not stated.
- EIP-7702 text: delegation is persistent; overwritten by a later authorization; cleared by delegating to the zero address; not rolled back on failure.
- Pectra announcement: activation 2025-05-07, includes EIP-7702.
- Permit2 source (branch tip): ERC-1271-only verification for signers with code (**no `ecrecover` fallback**), spender bound into `SignatureTransfer` hashes, destination not signed, `uint160.max` treated as unlimited and never decremented, caller scoping of `lockdown`/`invalidateNonces`.

### Corrections to my own earlier text

| Item | Was | Now |
|---|---|---|
| Swap scope | "No swaps in v1" recommended (OD-012) | Boundary designed in; dormant at v1.0 |
| Cap model | Token-denominated caps only (ADR-004) | Dual cap model |
| Router upgrades | Immutable, migration sketched | Full lifecycle and migration protocol |
| Layer 2 sizing | Clamped to `2^160 − 1` | Refused: Permit2 treats `uint160.max` as unlimited (R-L2-NO-MAX) |
| ERC-1271 gas | "Bounded gas" (misapplied CLM-032) | `STATICCALL` without an artificial cap; executor pre-flight bounds cost |
| Signature flows for delegated EOAs | Assumed to work | Allowed only with a verified ERC-1271 path (Permit2 never falls back to `ecrecover`) |
| Idempotency key | Included the router address | Excludes it, so settlement is once-only across router versions (ADR-009) |
| Surfaces | MVP / T1 / T2 tiers | v1.0 (18) / v1.1 (2) / v2.0 (5) |
| MetaMask evidence | E0 (search summary) | E1 documented (not a lab result) |
| Backlog | Epics for all phases; stories for Phase 0 only | Every epic decomposed into six story types |

### Superseded identifiers

Nothing was renumbered. Superseded text keeps its ID and is marked **Revised** or **DECIDED**: ADR-001, 004, 005, 007, 009; OD-004, 006, 008, 009, 011, 012, 024; CF-002, CF-004; RISK-014, 018, 019; PB-006, 013, 037. Epics that moved phase carry their v0.1 ID in `old_id` (for example `EPIC-P1-ORCH` → `EPIC-P2-ORCH`).

### Still open after this revision

- Everything in [08 §3](08-production-blockers-and-release-gates.md): audits, pen tests, counsel, wallet-lab and chain testing, token testing, vendor due diligence.
- OD-001, 003, 007, 017, 022, 023, 025, 026, 027, 028 (proposals exist; deciders have not signed).
- Items needing a human read at E2: all E1 claims; Permit2 at a pinned commit (expiration-of-zero, nonce update).
- The audit-cost premium of the dormant boundary (ASM-027) and the response-rate assumption for migration (ASM-028) are unmeasured.

## 0.1.0 — 2026-10-13 — starting-task pass

Initial TOC, source register, assumptions and decisions, trust boundaries, planner, architecture, delivery plan, blockers and gates.
