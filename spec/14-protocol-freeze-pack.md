# 14 — Protocol Freeze Pack

| Field | Value |
|---|---|
| Artifact | FP-REL-003 |
| Version | 0.5.0 (0.3: new; 0.4: account policy, exact predicates, constants and evidence moved into the decision report; 0.5: shared-allowance migration, seven-field account pin, signer-set emergency removal, pinned Permit2 reference, configuration records, executable suites; freeze readiness computed by [tools/freeze_readiness.py](tools/freeze_readiness.py)) |
| Status | DRAFT — **no item is closed; the freeze is not approved ([16](16-freeze-decision-report.md))**; the freeze has not happened; nothing here has been audited, tested on a wallet or a chain, or legally reviewed |
| Owner | Principal Blockchain Architect (freeze), Technical Program Manager (register) |
| Reviewers | Head of Security, VP Eng, QA Lead, Solidity Lead, Head of Compliance |
| Dependencies | [03](03-assumptions-decisions-risks.md), [05](05-evm-authorization-decision-tree.md)–[13](13-eip7702-delegation-inspection.md), [08](08-production-blockers-and-release-gates.md) (RG-016), [15](15-wallet-lab-matrix.md), [16](16-freeze-decision-report.md), [17](17-account-compatibility-policy.md), [tools/freeze_fingerprints.py](tools/freeze_fingerprints.py), [tools/sync_vectors.py](tools/sync_vectors.py), [tools/eip712_vectors.py](tools/eip712_vectors.py) |
| Definition of Done | The checklist is complete enough that a reviewer can say "frozen" or "not frozen" for each item from evidence; the unresolved list says what each open fact could change; the testnet and audit scopes are exact enough to be contracted and built against; the deliverables the sponsor asked for are indexed to the documents that hold them. |

## 0. What "protocol freeze" means

**The freeze** is gate **RG-016**. It marks the point after which the contract interfaces, the typed-data schemas, the storage layouts, the event and error catalogues, the planner's input and output, and the test vectors are treated as fixed, and the contract build (`EPIC-P1-CONTRACTS`) starts. It is **not** a claim that the design is secure or correct; it is a decision to stop changing the design without a recorded reason.

| Frozen at RG-016 | Not frozen (tunable under normal change control) |
|---|---|
| Contract set, entry points, roles, events, errors, storage layout rules ([06 §4](06-initial-architecture.md)); the account pin and the Account Compatibility Policy ([17](17-account-compatibility-policy.md)) | UI copy and customer wording (copy **keys** are frozen) |
| `PriceQuote` v1, `PayOnceIntent`, `SuccessorAuthorization`, revoke/pause typed data, all EIP-712 domains ([11 §4](11-dual-cap-model.md), [10](10-pay-once-protocol.md), [12 §5.3](12-router-lifecycle-and-migration.md)) | Parameters marked **PROPOSAL** that are registry values or backend policy (price-band widths, quote TTL within the registry maximum, limits, retry policy, TTLs) |
| Mandate fields, cap classes, counters, lineage rules ([11 §2–3](11-dual-cap-model.md), [12 §4](12-router-lifecycle-and-migration.md)) | Backend internals, database schemas other than those named in the specs, dashboards |
| Router lifecycle states and transitions; the exact `activateSuccessor` predicates, the migration snapshot and containment ([12 §5](12-router-lifecycle-and-migration.md)); the **production-blocking constants** of [16 §7](16-freeze-decision-report.md) | Governance and guardian *membership* and thresholds (their roles are frozen; people are not) |
| Planner input, output, decision tree and determinism rules ([05](05-evm-authorization-decision-tree.md)) | Wallet allowlist contents and Compatibility Register rows (data) |
| Delegation record, evidence, probes and the revalidation rule ([13](13-eip7702-delegation-inspection.md)) | Thresholds that RP-28 will measure (`MAX_OBSERVATION_AGE`, `EVIDENCE_TTL`) — their *names and semantics* are frozen |
| The golden vectors of documents 05, 10, 11, 12, 13 | New vectors may be added; existing vectors change only through a Freeze Change Request |

**Rules.** (1) A checklist item closes only with evidence, at the level in the "Closed when" column. (2) The fingerprints in §2 are recorded when the freeze is approved; afterwards any change to a fingerprinted section is a Freeze Change Request (§7). (3) A defect found by the audit is fixed under the same rule. (4) The freeze can be withdrawn by the CISO or the Principal Architect with a written reason.

## 1. Protocol freeze checklist (RG-016)

Status of every row: `OPEN`. "PA" Principal Architect, "CISO", "VPE", "QA", "HoC" Head of Compliance, "HoP" Head of Product. Evidence levels E1…E3 as in the [README](README.md).

### 1.1 Decisions and scope

| FZ | Item | Closed when | Owner | Spec |
|---|---|---|---|---|
| FZ-01 | ADR-001…ADR-019 approved or amended; ADR-013 (conversion code absent from Router v1), ADR-015 (lineage), ADR-016 (quotes), ADR-018 (revalidation), ADR-019 (revocation flows) in particular | Approval records | PA | [06 §9](06-initial-architecture.md) |
| FZ-02 | Open decisions OD-003, 024, 025, 026, 027, 028, 029 decided; OD-004, 006, 011, 012 recorded | ADR or decision record per OD | PA, HoP | [03](03-assumptions-decisions-risks.md) |
| FZ-03 | **Production-blocking constants decided**: PC-01…PC-18 of [16 §7](16-freeze-decision-report.md), each as its own approved configuration record ([18](18-configuration-records.md)); testnet-safe constants separated (16 §6) | A signed approval block per record with an evidence id; counsel letter for notice periods or a documented risk acceptance | PA, HoC | [16 §6–§7](16-freeze-decision-report.md), [18](18-configuration-records.md) |
| FZ-04 | Version boundaries v1.0 / v1.1 / v2.0 approved by the sponsor, including "conversion code absent from Router v1" | Signed capability matrix | HoP | [09](09-capability-boundaries.md) |
| FZ-05 | No FastPay-owned EIP-7702 delegate (OD-011); the on-chain account pin is **adopted** (OD-029 reversed in 0.4, shape per OD-037); no oracle slot in the v1 quote (OD-027) | Recorded decisions | PA | [13](13-eip7702-delegation-inspection.md), [17](17-account-compatibility-policy.md) |
| FZ-06 | OD-031 decided: squad shape and contractors for the contract path, or the later schedule accepted by the sponsor | Decision record with the P50/P75/P90 of [07 §3](07-delivery-plan.md) | VPE, HoP | [07](07-delivery-plan.md) |

### 1.2 Specification completeness

| FZ | Item | Closed when | Owner | Spec |
|---|---|---|---|---|
| FZ-10 | Planner specification: canonical input, normalization, decision tree and pseudocode, determinism, Compatibility Register schema; vectors TV-01…TV-36 | Spec reviewed by two engineers; vectors listed with expected outputs | Wallet Protocol Eng | [05](05-evm-authorization-decision-tree.md) |
| FZ-11 | Pay Once specification (witness, entrypoints, nonces, paths PO-1…PO-6) and vectors TV-PO-1…TV-PO-12; separation rules S-1…S-4 | Same | Solidity Lead | [10](10-pay-once-protocol.md) |
| FZ-12 | **Every cap and limit is classified** `ONCHAIN_HARD`, `QUOTE_BOUND_ONCHAIN` or `BACKEND_ONLY`, exactly once; no backend-only control is described as a protection | Table of [11 §2.1](11-dual-cap-model.md) reviewed against the threat model | Risk Lead, PA | [11](11-dual-cap-model.md) |
| FZ-13 | **Signed quote schema**: fifteen fields, domain, signer sets and rotation, validity predicate Q1…Q20, errors, canonical JSON, versioning, the non-override proof, reproducible vector | Digest of [11 §4.6](11-dual-cap-model.md) reproduced by two independent implementations and by a contract prototype; `sync_vectors.py --verify` passes | PA, Backend lead | [11 §4](11-dual-cap-model.md) |
| FZ-14 | Mandate fields, lineage counters and windows, `extensionsHash` must be zero | Spec reviewed; CAP-TV-01…32 listed | PA | [11 §3](11-dual-cap-model.md), [12 §4](12-router-lifecycle-and-migration.md) |
| FZ-15 | **Router lifecycle and migration state machine**: states, transitions T1…T9, the exact `activateSuccessor` predicates A1…O1N/O1E, the snapshot and containment K.1…K.9 with Lemma M, atomic and legacy flows, the no-overlap claim, partial states Q0…Q3 and Q3s, revision versus migration; MIG-TV-01…45 | Reviewed by Solidity Lead and a contract-security engineer; containment oracle in the test plan | PA | [12 §3, §5](12-router-lifecycle-and-migration.md) |
| FZ-16 | **Delegation inspection and revalidation** (layer B): `DelegationRecord`, `DelegationEvidence`, probes, the revalidation rule, result types, diff codes, pause bit, clearing rules; pseudocode and DRV-01…DRV-25 | Reviewed; vectors executable | Wallet Protocol Eng | [13 §3, §7, §11](13-eip7702-delegation-inspection.md) |
| FZ-17 | Contract-by-contract specification (storage, roles, functions, events, errors, invariants, attack surface) for every v1.0 contract | `EPIC-P0-PROTOSPEC` acceptance met | Solidity Lead | [06 §4](06-initial-architecture.md) |
| FZ-18 | Event and error catalogue consistent across documents (lineage, lifecycle, quote, pause bits, Pay Once) | Cross-reference check passes; no duplicate or conflicting names | Solidity Lead | [12 §8](12-router-lifecycle-and-migration.md), [11 §4](11-dual-cap-model.md) |
| FZ-19 | **External-call allowlist and absence checks** final: Permit2, registry-listed tokens, `MandateManager`, `RouterRegistry`, fixed registries; no conversion selectors, no adapter or conversion registry | Check procedure agreed with the audit firms | PA | [09 §7](09-capability-boundaries.md) |
| FZ-20 | Role matrix and timelocks final: governance, guardian (stop-only, separate switches), `RiskPauser`, executors, charge signers, quote signers | Role-matrix test cases written | CISO, PA | [04 §5](04-context-and-trust-boundaries.md) |
| FZ-21 | **Revocation flows**: the primary flow is `Permit2.lockdown` by transaction (secondary `approve(…,0,0)`; `invalidateNonces`; token `approve(0)`) plus `revoke`/`revokeBySig`, defined by the fork tests RV-T01…RV-T12; the signed zero-amount `permit` is **disabled** until ZP-T01…ZP-T08 and the wallet lab pass | Table of [05 §2.1–§2.2](05-evm-authorization-decision-tree.md) approved; plan validator rule NC-17 specified | PA | [05 §2](05-evm-authorization-decision-tree.md), [12 §6](12-router-lifecycle-and-migration.md) |
| FZ-22 | All EIP-712 domains and type strings listed once: names, versions, `verifyingContract`, chain binding | One table, reviewed against the contract specs | Solidity Lead | [11 §4.1](11-dual-cap-model.md), [10 §2.1](10-pay-once-protocol.md), [12 §5.3](12-router-lifecycle-and-migration.md) |
| FZ-23 | Customer-facing copy **keys** exist for consent, delegation display and re-verification, migration and notices (wording is not frozen) | Key list reviewed by Product and Compliance | Product Designer | [11 §8](11-dual-cap-model.md), [13 §9](13-eip7702-delegation-inspection.md) |
| FZ-24 | **Account Compatibility Policy**: five account modes with boolean predicates, the permission matrix (unattended charges only in verified modes), the on-chain account pin and its update path, the three enforcement layers and their stated limits; ACP-TV-01…44 | Reviewed by Security and the Wallet Protocol Engineer; vectors executable in both planner implementations | Wallet Protocol Eng, PA | [17](17-account-compatibility-policy.md) |
| FZ-25 | **Router-independent identifiers**: `lineageId`, `mandateId`, `cycleId`, `paymentId` contain no router input; the cycle-index rule; settle-once per `(lineageId, cycleIndex)` | Vector of [11 §4.6](11-dual-cap-model.md); MIG-TV-19 | PA | [11 §3.1](11-dual-cap-model.md) |
| FZ-26 | **Shared-allowance migration**: Permit2 facts F1…F6, router mode from the registry, the on-chain exposure index, normal migration (O1N) and emergency migration (O1E), the sibling table, planner duties R-L2-SHARED, NC-20, NC-21; MIG-TV-30…45; OD-035 decided | Reviewed by the Solidity Lead and a contract-security engineer; model checks and Foundry shared-allowance suite pass | PA, Solidity Lead | [12 §5.3.1](12-router-lifecycle-and-migration.md), [05 §6.1](05-evm-authorization-decision-tree.md) |
| FZ-27 | **`AccountPin`**: the seven-field struct, `PIN_WELLFORMED`, `PIN_OK` with the delegate's code hash, `pinVersion`, `AUTH` and the signature mode, the field-by-field split between on-chain verification and off-chain control; ACP-TV-25…44; OD-037 decided | Reviewed by Security and the Solidity Lead; vectors executable | PA, Wallet Protocol Eng | [17 §5](17-account-compatibility-policy.md) |
| FZ-28 | **Signature-capability binding**: `SigCapabilityRecord` bound to the pin, the eleven revocation triggers, effects on planner, signer policy and contract | Reviewed; ACP-TV-41…44 executable | Wallet Protocol Eng | [17 §5.6](17-account-compatibility-policy.md), [13 §3.2](13-eip7702-delegation-inspection.md) |
| FZ-29 | **Signer-set emergency removal**: no grace for a compromised key, bounded grace for planned rotation of previously issued quotes, tombstones, set stop, the guardian never adds; SR-1…SR-7; CAP-TV-23…32; OD-036 decided | Reviewed; model checks and Foundry signer-set suite pass | PA, Head of Security | [11 §4.7](11-dual-cap-model.md) |

### 1.3 Evidence (the facts the design stands on)

| FZ | Item | Closed when | Owner | Source |
|---|---|---|---|---|
| FZ-30 | Every design-load-bearing claim in the specifications is at **E2** (human-read, pinned): EIPs 712, 1193, 1271, 2612, 5792, 7702; the pinned Permit2 commit | RP-01, RP-02; Source Register audit | Wallet Protocol Eng | [02](02-source-register.md) |
| FZ-31 | **Pinned Permit2 source review** PR-01…PR-16 of [16 §5](16-freeze-decision-report.md) at E2 with the commit SHA recorded (`cc306b601f172c51bc04334a109e98340456620b`; **recorded in 0.5**, answers recorded from an automated read; E2 sign-off by two named reviewers **not done**), the rebuild comparison (CREATE2 address check), and the freeze subset of its fork tests (RV-T01, 02, 04, 05, 07, 11, MIG-TV-22/40; **not run**); the full RV-T and ZP-T suites follow before RG-002 | EV-P12 closed; PB-053, PB-005 | AA/Protocol Eng | CLM-050…052, G-09, G-10 |
| FZ-32 | Primary revocation flows verified for the launch-candidate tokens on forks (token `approve(0)` including `ZERO_FIRST` and no-return tokens; `lockdown`; `approve(…,0,0)`; `invalidateNonces`) | EV-P11 rows for the candidate tokens | Contract Security Eng | RP-27 |
| FZ-33 | `EXTCODESIZE` and `EXTCODEHASH` of a delegated account on each launch chain behave as the specifications assume (23 bytes; designator hash) | EV-P10 | AA/Protocol Eng | CLM-053 |
| FZ-34 | **Wallet-lab evidence**: the freeze subset EVL-01…EVL-10 of [16 §9](16-freeze-decision-report.md) (MetaMask extension and iOS: capabilities, batching, upgrade, delegate, pin values, ERC-1271 under Permit2, change detection, revert path, revocation, typed-data display; Trust Wallet discovery; synthetic fixtures) | Run records and Compatibility Register v0 | QA Lead | EV-P03, EV-P09, EV-P13 |
| FZ-35 | ERC-1271 under Permit2 for delegated and smart accounts: the result decides the default of the `sig1271` gate and whether signature transports stay in v1.0 | WL-12, WL-30 run records; decision recorded | Wallet Protocol Eng | EV-P07 |
| FZ-36 | Chain facts for the first mainnets: Permit2 runtime code from two RPCs per chain (recorded in 0.5 for Ethereum, Base and Arbitrum One: 9,152 bytes, **per-chain hash differs by two immutables, masked hash equal**), the rebuild comparison, EVM version and opcodes, finality and reorg data | EV-P01, EV-P14; chain fact sheets for Base and Arbitrum One | Chain Infra Lead | RP-03, RP-04, RP-22 |
| FZ-37 | Gas per planner step measured on forks (inputs to `gas.perStepGas`, the fee ceiling and the cost model) | RP-19 table | Solidity Lead | RP-19 |

### 1.4 Verification by construction

| FZ | Item | Closed when | Owner |
|---|---|---|---|
| FZ-40 | **Two independent planner implementations** produce identical output on TV-01…36, TV-PO-1…12, CAP-TV-01…32, DRV-01…25, ACP-TV-01…44 and MIG-TV-01…45, and on a differential fuzz of 100,000 random inputs (zero divergences) | CI report | Wallet Protocol Eng, Backend lead |
| FZ-41 | Fork prototype (code tagged SPIKE, not production) demonstrates: activation by batch and by legacy path; a charge; gasless revoke; revoke while the router is paused; a normal successor with a sibling still on the old router (allowance retained, bounded) and an emergency successor (every exposed token's allowance unusable), lineage counters preserved; a quote-verified charge; a Pay Once witness transfer. Per-step gas recorded. **No conversion code written** | `EPIC-P0-PROTO` acceptance | Solidity Lead |
| FZ-42 | The quote digest and type hashes are equal in the contract prototype, the backend and `tools/eip712_vectors.py` | Three-way comparison | PA |
| FZ-43 | No open contradiction (`CF-`) affects a frozen section | CF register reviewed | Principal PM |
| FZ-44 | **Executable suites:** the Foundry project of [foundry/](foundry/) (exported vectors, fuzz, invariant, mutation, integer-width, timestamp-boundary, shared-allowance, signer-set, pin and configuration-range suites) compiles and passes against the reference model; every mutant is killed; the Permit2 fork tests pass; the run report is recorded in `evidence/freeze_register.json` (`foundryReport`) | `forge build` and `forge test` reports with the toolchain version; **written but not compiled or run in 0.5** | QA, Solidity Lead |
| FZ-45 | Every production-blocking constant has its own approved configuration record: owner, unit, rationale, evidence, safe range, test and release gate | `tools/build_config_records.py --verify` and `freeze_readiness.py` condition C-4 | PA |

### 1.5 Security

| FZ | Item | Closed when | Owner |
|---|---|---|---|
| FZ-50 | Threat model v1 (TM-01…TM-18 and the section-18 threats) reviewed by an external reviewer; every frozen interface maps to controls and named tests | Reviewer sign-off | CISO |
| FZ-51 | Design review of the frozen specifications by a reviewer outside the authoring squad: no open finding rated high or above | Review record | Head of Security |
| FZ-52 | Key classes defined and separated: executor, charge signer, **quote signer**, webhook signing, CI signing; compromise of one cannot produce another's output (TM-10) | Key-class table; signer policy tests listed | CISO |
| FZ-53 | The absence proof method (zero conversion selectors; call-graph within the allowlist; manifest lists no adapter) agreed with both audit firms | Auditor acknowledgements | PA |

### 1.6 Audit readiness and plan

| FZ | Item | Closed when | Owner |
|---|---|---|---|
| FZ-60 | Two audit firms contracted with slots from the planned audit start; the scope of §5 agreed with both; the Router v1.1 scope priced separately (ASM-027) | Engagement letters; two quotes per firm | Head of Security |
| FZ-61 | Audit package template ready: specifications, invariants, threat model, deployment scripts, vectors, absence-check report | `EPIC-P1-AUDITPREP` template accepted | Contract Security Eng |
| FZ-62 | Formal-verification or independent-review plan for `I-CAP-TOKEN`, `I-CAP-FIAT`, `I-ONCE`, `I-MINOUT` (PB-003) | Plan with owner and tool | PA |
| FZ-70 | Critical roles filled: Principal Blockchain Architect, two Contract Security Engineers, Wallet Protocol Engineer, Head of Compliance, Head of Security | Hiring records | VPE |
| FZ-71 | Backlog baseline imported and profile compliance check passes (`build_backlog.py --check`); schedule baseline recorded | Generator output; `schedule_results.json` hash | TPM |

### 1.7 Sign-off (RG-016)

| FZ | Item | Closed when |
|---|---|---|
| FZ-80 | Sign-offs recorded by the Principal Architect (accountable), CISO (veto), VP Engineering and QA Lead; Head of Product informed; fingerprints of §2 recorded in this document | Gate register entry with date and attendees |

## 2. Freeze fingerprints

Generated by [tools/freeze_fingerprints.py](tools/freeze_fingerprints.py) (`--write` records, `--verify` checks). Before the freeze these are **candidates** and change with each edit; when RG-016 is approved the values are recorded and `--verify` becomes a release-pipeline check.

<!-- BEGIN:FINGERPRINTS -->
| FG | Document and section | Fixes | SHA-256 (first 16 hex) | Full SHA-256 |
|---|---|---|---|---|
| FG-01 | 05-evm-authorization-decision-tree.md — 2. Protocol B | Three authorization layers; separation rules; revocation flows (§2.1) | `e17d3e16dce3a4f1` | `e17d3e16dce3a4f16e1ca6ef5cd8f4a6413635c86a82eee7fd6828932790b91e` |
| FG-02 | 05-evm-authorization-decision-tree.md — 5. Canonical input | Planner input and normalization (JCS canonical form) | `f6b3df78a35124a8` | `f6b3df78a35124a881664e4f941ac3beeddd289fe39731bb9ad6203b6b84cf68` |
| FG-03 | 05-evm-authorization-decision-tree.md — 7. Decision tree | Decision tree and normative pseudocode | `9bc3a1e1fe7eb259` | `9bc3a1e1fe7eb259d08d38b19852db7f301cdf82c2b8ab0058d351e6002f2594` |
| FG-04 | 05-evm-authorization-decision-tree.md — 9. Golden test vectors | Planner vectors TV-01…TV-36 | `a7c119ea03ac5f8c` | `a7c119ea03ac5f8c8c849b8c164ace8bc179bdf88dbc3ddf0038a8380e9cd2e6` |
| FG-05 | 06-initial-architecture.md — 4. Contract architecture | Contracts, entry points and system invariants | `3c142e8e7581f28c` | `3c142e8e7581f28cac5cbe5c6a7da5507afa4e77850c63e4b83a36a5dde3304f` |
| FG-06 | 09-capability-boundaries.md — 7. Mechanical absence | Absence and presence checks for conversion code | `b12f68d5ea190815` | `b12f68d5ea190815429120d02c9aff334c72e23fa05784520ea98db79444d399` |
| FG-07 | 10-pay-once-protocol.md — 2. On-chain design | Pay Once: spender binding, witness, entrypoints, nonces | `256160b9c0a2798a` | `256160b9c0a2798a43e8ab581ac67bc6108d3a58e078501129ec11537c175c26` |
| FG-08 | 10-pay-once-protocol.md — 7. Golden vectors | Pay Once planner vectors TV-PO-1…12 | `a832c83d23ca466f` | `a832c83d23ca466fc720277de85f8d65c1aa7f54847eee19ca5c59ed16daa302` |
| FG-09 | 11-dual-cap-model.md — 2. The three cap classes | Classification of every cap and limit | `a66fb0ce1b02a0b8` | `a66fb0ce1b02a0b836921a421263441d7f3aea407260487ea64c74742dbcca65` |
| FG-10 | 11-dual-cap-model.md — 3. Mandate fields | Mandate fields, counters, extensionsHash | `31c67d0917f98bc0` | `31c67d0917f98bc0e8efca0045756862e34fa2add85ea82f0cd6ab0e1d7b7e58` |
| FG-11 | 11-dual-cap-model.md — 4. The signed quote schema | PriceQuote v1: fifteen fields, domain, signer sets and rotation, validity predicate Q1–Q20, non-override proof, canonical JSON, versioning, test vector | `da14e399652d3602` | `da14e399652d36028ba6ea0c6be999f7fc152614dbda8de788df35ff4e1f99c5` |
| FG-12 | 11-dual-cap-model.md — 5. Charge-time algorithm | On-chain charge algorithm | `355aceb89666fac0` | `355aceb89666fac066f3a67f433de209a020abb070b189a7eb32dfcd35910ece` |
| FG-13 | 12-router-lifecycle-and-migration.md — 4. The lineage model | Mandate lineage | `b736e62fb909daff` | `b736e62fb909daff49de6d0e138ae8d4a62a351f4a1e24372ce752cda19bf7b5` |
| FG-14 | 12-router-lifecycle-and-migration.md — 5. Migration state machine | States, transitions, activateSuccessor predicates, router modes and the shared-allowance rules, exposure index, plan kinds, partial states, revision vs migration | `8106c2437660ab6a` | `8106c2437660ab6aba19f59121367880976c71458228d6327d311923dc19fe09` |
| FG-15 | 12-router-lifecycle-and-migration.md — 12. Invariants and tests | I-MIG-1…11 and MIG-TV-01…45 | `3c5eb8d498dd9e2b` | `3c5eb8d498dd9e2b01f2e50e60316516e7e1a7ce45ed6d3715b8bdb3f58a1f54` |
| FG-16 | 13-eip7702-delegation-inspection.md — 3. What is inspected | DelegationRecord, DelegationEvidence, probes, observation procedure | `519df0b8f7493c55` | `519df0b8f7493c5573f648786a761a01c6e38141226c06b9e5564cbbe588bac4` |
| FG-17 | 13-eip7702-delegation-inspection.md — 7. Revalidation before every unattended charge | Revalidation rule, results, pseudocode, pause state and clearing | `a0fb7ec20a0128b2` | `a0fb7ec20a0128b26c3ae3821ccf21285ea123884bfe76e941c8ef87d532118c` |
| FG-18 | 13-eip7702-delegation-inspection.md — 11. Golden vectors | DRV-01…DRV-25 | `e393ae3eb28d22f5` | `e393ae3eb28d22f52b7fdbcbde85cf691e6c1719ce56b1e7ab8afe5a0af6f569` |
| FG-19 | 17-account-compatibility-policy.md — 2. Account modes | Observation, allowlist row, mode predicates | `f0102749eba9909b` | `f0102749eba9909bf98f5f9179a9d7d144b4c2f8d82a9ef8c10c9ccc82b9ff83` |
| FG-20 | 17-account-compatibility-policy.md — 3. Permission matrix | Permission of each mode; UNATTENDED_OK predicate | `6ce49327a0d18024` | `6ce49327a0d18024021cfb6f0ce503b8546f9d30f4487fb3b89722dd6dfdb50c` |
| FG-21 | 17-account-compatibility-policy.md — 5. The on-chain account pin | AccountPin struct, PIN_WELLFORMED, PIN_OK, AUTH, what the contract verifies versus off chain, signature capability and its invalidation | `560fbbd49e741f7c` | `560fbbd49e741f7cf5d50aae212854977c7538791873455fe5a9f42d0d4ab8e8` |
| FG-22 | 17-account-compatibility-policy.md — 9. Test vectors ACP-TV | ACP-TV-01…44 and pin constants | `d84b08348c1e6f0e` | `d84b08348c1e6f0e8fbb07f1856ae450adce2cc85eae4ee979b930e33ef69899` |
| FG-23 | 11-dual-cap-model.md — 4.7 Signer sets | Signer-set planned rotation and emergency removal; SR-1…SR-7 | `878469f7b6398721` | `878469f7b63987212bccf934252edc42a3cf3219e3087c5bc4cc930926ac8766` |
| FG-24 | 12-router-lifecycle-and-migration.md — 5.3.1 The shared allowance | Permit2 facts F1…F6, router mode, exposure index, normal and emergency migration, sibling rules | `f7b5f199f70b97eb` | `f7b5f199f70b97eb9212f5366d92032cde56ee75915f000fd1f283c215748fed` |
<!-- END:FINGERPRINTS -->

## 3. Unresolved blockers, decisions and facts at the freeze

The full lists are in the freeze-decision report: **unresolved decisions** [16 §3](16-freeze-decision-report.md), **unverified external facts and what would change if each is adverse** [16 §4](16-freeze-decision-report.md), the **pinned Permit2 review** [16 §5](16-freeze-decision-report.md), **testnet-safe** and **production-blocking constants** [16 §6–§7](16-freeze-decision-report.md). All **56** production blockers in [08](08-production-blockers-and-release-gates.md) are `OPEN`; none can be closed by this workspace.

### 3.1 Largest blockers for later gates (status: all `OPEN`)

| Gate | What gates it | Blockers |
|---|---|---|
| RG-002 Phase 1 exit; testnet alpha | All `I-*` invariants pass; Permit2 assumptions confirmed from source and fork tests; audit package accepted | PB-005, PB-003 (tests), PB-053 |
| RG-003 Wallet and capability evidence | E3 rows for every claimed wallet including account mode and pin; delegate behavior; hostile fixtures | PB-008, PB-009, **PB-043**, **PB-049**, **PB-052** |
| RG-004 Chain, token and finality evidence | Permit2 verified; finality; token lab; **primary revocation flows verified per token** | PB-004, PB-010, PB-011, **PB-050** |
| RG-005 Contract audit | Two audits; invariants and formal targets; **absence proof**; lineage migration predicates; quote schema and non-override | PB-002, PB-003, PB-040, PB-041, PB-042, PB-044, **PB-051**, PB-052 (contract) |
| RG-006 Security testing and keys | Pen test and red team; ceremonies; signer policy including the ACP stamp; frontend integrity | PB-006, PB-007, PB-012, PB-019…PB-024 |
| RG-008 Legal, compliance, privacy | Counsel letters; licence or partner path; KYB; consent copy; DPIA | PB-027…PB-031, PB-036, PB-037 |
| RG-010 Private mainnet beta | RG-003…009 for the beta scope; limits live; **absence proof in the signed manifest**; flag service fail-closed | PB-001, PB-018, PB-026, PB-039, PB-040, PB-047 |
| RG-015 Router migration readiness | Lifecycle rehearsed; canary drill; communications game day; counsel on notice duties | PB-006, PB-042, PB-048 |

Production blockers that exist only from v1.1 (PB-045) and v2.0 (PB-046) are out of the v1.0 path.

## 4. Exact testnet implementation scope (release R3, public testnet alpha)

The scope is what must exist for RG-002 and for the alpha to be a meaningful test of the frozen protocol. Everything not listed is out of scope. **No mainnet deployment is started or implied.**

### 4.1 Chains and environments

| Item | Scope |
|---|---|
| Testnets | Sepolia, Base Sepolia, Arbitrum Sepolia ([09 §2.5](09-capability-boundaries.md)) |
| Permit2 | Use the canonical address only if `eth_getCode` from two RPCs equals the bytecode built from the pinned commit **with the two per-chain immutables (chain id, domain separator) masked** ([16 §5.2](16-freeze-decision-report.md)); otherwise deploy from the pinned commit (`cc306b601f172c51bc04334a109e98340456620b`, solc 0.8.17 settings recorded in `evidence/permit2/pin.json`) and record the address in the **testnet manifest**. Never treat a testnet address as evidence for a mainnet claim |
| Environments | local, CI, dev, testnet, staging. No canary mainnet and no production |
| Keys | Test keys only, from test KMS key classes that mimic the production classes (executor, charge signer, quote signer); no production secrets anywhere |
| Data | Synthetic and employee data only; no real customers |

### 4.2 Contracts to be built and deployed (version `0.9-alpha`, labeled UNAUDITED)

| Contract | In testnet scope | Notes |
|---|---|---|
| `MandateManager` | Yes: mandates, lineages, dual caps, `maxFeeBps`, the seven-field `AccountPin` (hash and version stored, struct in events and `consume` calldata), activation (tx and signature), `activateSuccessor` with the on-chain snapshot, the router mode and the exposure index and the predicates of [12 §5.3](12-router-lifecycle-and-migration.md), `retire`, `updateAccountPin(s)`, `AUTH`, three pause bits, `revoke`/`revokeBySig`, `reduce`, `consume` | No export/import hooks; `extensionsHash` must be zero |
| `PaymentRouter` v1 | Yes: Protocol B `charge`, `chargeInitial`; Protocol A `payOnceWithSignature`, `payOnceWithSignatureAndPermit`, `payOnce`; `payOnceWithAuthorization` only behind its flag | **No conversion entrypoints** |
| A second router build (`Router-test-B`) | Yes, testnet only | Differs from Router v1 only in version and identity, to exercise the lifecycle and lineage migration |
| `RouterRegistry` | Yes: propose, activate, deprecate, sunset, retire, emergency disable, `isChargeable`, `isBindable`, `markSettled` | Immutable constants compiled as **test constants** (see 4.5) |
| `MerchantRegistry`, `TokenPolicyRegistry`, `ExecutorRegistry`, `FeeController`, `RefundManager`, `EmergencyGuardian` | Yes | `TokenPolicyRegistry` rejects `SWAP_ONLY`; signer sets with rotation, tombstones and a set stop |
| `QuoteVerifier`, `SignatureVerifier` (libraries) | Yes | ECDSA quote signers only |
| Governance and guardian | Test multisigs and a timelock with shortened delays | Roles and separation as frozen; membership is test keys |
| Test-only: mock tokens | 12 behavior classes (fee-on-transfer, rebasing, no-return, approve-zero-first, blacklist, pausable, callbacks, permit variants, etc.) plus two well-behaved 6-decimal stablecoin mocks | Not deployed anywhere else |
| Test-only: synthetic delegates | Correct ERC-1271, none, always-valid, swappable, EIP-1967 and EIP-1167 proxies ([15 §7](15-wallet-lab-matrix.md)) | Never deployed on a mainnet |
| **Not built** | `ConversionPolicyRegistry`, any adapter, `DEXAdapterRegistry`, conversion entrypoints, `EIP7702Executor`, Router v1.1, Router v2 | Absence check runs on the testnet deployment |

### 4.3 Services and surfaces

| Area | In scope for the alpha | Stubbed or out |
|---|---|---|
| `fastpay-core` modules | identity-access, merchant, customer, wallet-capability, **delegation-inspector (inspection and revalidation)**, mandate, payment-orchestrator, quote, routing (**direct settlement only**), subscription, refund, token-registry, ledger, risk, migration-orchestrator, feature-flags, notifications (email and webhooks minimal), reporting (minimal) | admin-compliance: KYB, sanctions and AML stubbed with fixtures |
| Isolated deployables | `chain-gateway` (indexer, broadcaster, finality, reconciliation), `signer` (policy enforced, including the revalidation stamp), `quote-signer`, `webhook-dispatcher` | — |
| Planner | Two independent implementations; paths A–D; PO-1…PO-6; all vectors | Conversion policy slots present as inputs and always `false` |
| Surfaces | S01 Hosted Checkout, S04 Pay Once, S05 FastPay Activation, S07 Fixed Subscriptions, S12 Merchant Settlement, S14 Receipts, S15 Webhooks, S16 Merchant Dashboard (basic), **S17 Customer Mandate Portal** (limits, usage, pause, revoke, delegation status and re-verification, migration prompt), S18 Developer Portal (basic, sandbox keys), S20 Risk Console and S22 Incident Console (minimum to pause, set the delegation pause, read alerts) | S13 refunds: merchant-push path only; S19, S21: minimum to run the alpha; S02, S03, S23: later |
| Flags | `signing.erc3009.enabled` off; `revocation.zeroPermit.enabled` off (toggled only by the lab); `activation.relayedSignatures.enabled` per Compatibility Register; `activation.walletUpgrade.allowed` per register | No conversion flags exist |

### 4.4 Scenarios the alpha must demonstrate (each is a test with a recorded result)

| # | Scenario | Reference |
|---|---|---|
| 1 | Activation by atomic batch on a batching wallet and fixture; by legacy sequence; by relayed signature with a verified ERC-1271 delegate; refusal for an unknown delegate | [05](05-evm-authorization-decision-tree.md) TV-01…36 |
| 2 | First payment bundled with activation; six recurring cycles with fixed amounts; token fallback only after pre-submission failures | [06 §3](06-initial-architecture.md) |
| 3 | Token cap, window cap and total cap exhausted; fiat-capped charge with a valid quote; expired, out-of-bounds, wrong-signer and replayed quotes rejected; a signer rotation (bounded grace, earlier quotes only) and an emergency removal drill (no grace, tombstone, set stop, guardian cannot add) | CAP-TV-01…32, Q1…Q20 |
| 4 | Customer pause, resume, revoke (gasless); revoke while the router is paused; Permit2 lockdown after revoke | I-EXIT; [05 §2.1](05-evm-authorization-decision-tree.md) |
| 5 | Pay Once on every path PO-1…PO-6; witness mismatch rejected; no standing allowance remains | [10](10-pay-once-protocol.md) |
| 6 | Router lifecycle on testnet (candidate, active, deprecated, sunset, retired) and a lineage migration over ATOMIC_BATCH, MIXED and TX_SEQUENCE, including interruption at Q1, Q2 and the early-S3 rejection; a **normal** migration of one lineage with a sibling still on the old router (no lockdown, sibling keeps charging) and an **emergency** migration (every exposed token locked down first) | MIG-TV-01…18, 30…45 |
| 7 | Delegation revalidation before every unattended charge: delegate swap between two charges pauses the mandate as `DELEGATION_UNVERIFIED`; INDETERMINATE does not pause on the first occurrence; clearing by re-verification; no token fallback | DRV-01…25 |
| 8 | Chain-gateway chaos: lying RPC, lagging provider, simulated reorgs, stuck nonce; `UNKNOWN` never causes a second-token charge; on-chain once-per-cycle race | PB-014, PB-010 |
| 9 | Ledger: 14 consecutive days of reconciliation at 100% on testnet; refund via `RefundManager`; reorg reversal | RG-007 |
| 10 | Webhooks signed with replay window and rotation; idempotency keys honored | PB-021 |
| 11 | Key rotation drills for executor, charge-signer and quote-signer keys; signer refuses out-of-policy requests (including a charge intent without a fresh `OK` stamp) | PB-019, PB-007 |
| 12 | Absence checks pass on the testnet deployment: no conversion selectors, call targets within the allowlist, `extensionsHash` zero required | [09 §7](09-capability-boundaries.md) |
| 13 | Account pin: charge on a plain EOA, then the account gains a delegation (type-4 transaction) → `AccountCodeChanged`, pause, re-verification with one signature, charging resumes; the same for a delegate swap and for a revert to an EOA; a proxy implementation upgrade is caught by the backend only; a delegate **code-hash** change is caught on chain; the ERC-1271 path closes with the pin and the signature capability is revoked | ACP-TV-13…44, WL-35, WL-37…39, [17 §7](17-account-compatibility-policy.md) |
| 14 | Migration predicates: every predicate A1…O1N/O1E fails and passes in a fork test; containment fuzz against Lemma M; the no-overlap claim over Q0…Q3 and Q3s for atomic, TX_SEQUENCE and MIXED flows; the shared-allowance sibling cases; the exposure index under random sequences | MIG-TV-01…45 |
| 15 | Revocation primitives on forks: RV-T01…RV-T12; ZP-T01…ZP-T08 results recorded with the flag off | [05 §2.2](05-evm-authorization-decision-tree.md) |
| 16 | The Foundry suites of [foundry/](foundry/) run in CI: vectors exported from the Python models, fuzz, invariant, mutation (every mutant killed), integer-width, timestamp-boundary and shared-allowance suites; the reference model is replaced by the real contracts through the same interface | FZ-44; [12 §12](12-router-lifecycle-and-migration.md) |

### 4.5 Rules for the testnet build

1. **The testnet build must not differ from the audited source except in the testnet-safe constants of [16 §6](16-freeze-decision-report.md).** Those immutable constants are compile-time values; the testnet build uses short values and is tagged `-testconst`; the production-blocking constants of [16 §7](16-freeze-decision-report.md) keep their intended values on testnet unless they are listed in §6. A `-testconst` artifact is never promoted; the mainnet artifact is built from the audited commit with the production constants, and its bytecode hash is what the auditors and verifiers compare.
2. Testnet contracts are labeled UNAUDITED in the manifest, the explorer-verified source and every customer-visible screen.
3. The testnet manifest is separate from any future production manifest; **no production address appears in any document**.
4. Exit of R3: every scenario above has a passing, recorded run; RG-002 criteria are met; no open critical defect.

## 5. Contract audit scope (Router v1, registries, lineage migration, quote verification)

### 5.1 Principles

1. The audit covers **the exact bytecode that will be deployed**: one commit, one compiler version and settings, production constants. A change after the audit starts is a Freeze Change Request with the audit firms notified.
2. Router v1 contains **no swap or conversion code**; the audit scope states this and the firms verify the absence checks of [09 §7](09-capability-boundaries.md). Router v1.1 and `ConversionPolicyRegistry` are a **separate future audit**.
3. Two independent firms work in parallel (OD-019). A public contest or extended private review follows before public beta.
4. Properties, not just code: the firms receive the invariant list and are asked to attack each one.

### 5.2 Exact scope

The **function-level audit scope** (contracts, entry points, what the auditors must examine, out-of-scope items, properties to attack, specific questions, and what the auditors receive) is in [16 §8](16-freeze-decision-report.md). It is not duplicated here, so there is one place to change.

### 5.6 Process and exit

| Step | Rule |
|---|---|
| Findings | Rated critical, high, medium, low, informational; the firm that found an issue re-reviews its fix |
| Exit (RG-005) | Both reports complete; **no open critical or high**; medium and low triaged with written rationale; invariants and formal targets met; the absence tests green; final reports archived; the scope statement lists in-scope and out-of-scope contracts and states that no conversion code exists |
| After the audit | A deployed bytecode hash must equal the audited build (PB-001); any later change to a v1 contract is a new router version, audited again |

### 5.7 What the audit does not establish

It does not prove the design is secure, only that two firms examined the stated code and properties and what they found. It does not cover Permit2, tokens, wallets, the backend, legal compliance or operations. A clean report is evidence for RG-005, not a statement that the system is safe. The audited bytecode must equal the production build with the production constants of [16 §7](16-freeze-decision-report.md).

## 6. Index of the requested deliverables

| Requested | Where it is | Notes |
|---|---|---|
| Protocol freeze checklist | §1 of this document | RG-016 in [08](08-production-blockers-and-release-gates.md) |
| Unresolved production blockers, decisions and external facts | [16 §3–§4](16-freeze-decision-report.md), §3 of this document and [08](08-production-blockers-and-release-gates.md) | 56 blockers, all `OPEN` |
| Exact testnet implementation scope | §4 | |
| Contract audit scope | [16 §8](16-freeze-decision-report.md) (function level), §5 of this document (principles and process) | |
| Wallet-lab matrix and the exact evidence required | [15](15-wallet-lab-matrix.md), [16 §9](16-freeze-decision-report.md) | MetaMask `UNTESTED`/documented; Trust Wallet `UNKNOWN` |
| Signed quote schema | [11 §4](11-dual-cap-model.md) (typed data, validity predicate, canonical JSON, versioning, test vector) | Reproduce the vector with `python -I tools/eip712_vectors.py` |
| Router migration state machine | [12 §5](12-router-lifecycle-and-migration.md) (states, transitions, `activateSuccessor`, plan, partial states) | Vectors MIG-TV-01…18 in [12 §12](12-router-lifecycle-and-migration.md) |
| Delegation revalidation pseudocode and golden vectors | [13 §7.3](13-eip7702-delegation-inspection.md) (pseudocode), [13 §11](13-eip7702-delegation-inspection.md) (DRV-01…25) | |
| Cap classification | [11 §2.1](11-dual-cap-model.md) | Every cap and limit has exactly one class |
| Account Compatibility Policy | [17](17-account-compatibility-policy.md) | Modes, permissions, on-chain pin |
| Freeze-decision report | [16](16-freeze-decision-report.md) | Accepted and unresolved decisions, external facts, constants, evidence; **freeze not approved** |
| Revocation flows | [05 §2.1](05-evm-authorization-decision-tree.md) | Transactions are primary; zero-amount `permit` is experimental |
| Epic profiles and schedule (P50/P75/P90) | [07](07-delivery-plan.md) | |

## 7. Change control after the freeze

1. **Freeze Change Request (FCR):** reason, affected fingerprints (§2), affected contracts, vectors and documents, security impact, audit impact (before or after the audit starts), schedule impact, and the proposed new text.
2. **Approval:** the Principal Architect and CISO both approve; the Solidity Lead and QA Lead are consulted; the audit firms are told before any change after the audit starts.
3. **Execution:** documents change first, then vectors, then code; fingerprints are re-recorded in the same change; `freeze_fingerprints.py --verify` must pass in CI.
4. **Defect versus change:** correcting text that contradicts another frozen section (a typo, a wrong cross-reference) is an editorial FCR with the same trail; nothing is edited silently.
5. **A security finding** that requires a change follows the same path but may be approved by the CISO alone if time-critical, with the Principal Architect's after-the-fact confirmation.

## 8. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Whether the two audit firms split by contract set (money flow versus lifecycle and signatures) or both cover everything with different emphasis; trade-off between cost and independence | Head of Security |
| 2 | Tool choice for formal verification or property review of the four selected invariants | PA |
| 3 | Whether the freeze should wait for the first real-wallet delegate results (U-02, U-03) or proceed on synthetic delegates with a recorded risk; the schedule model shows the freeze is on the critical path | VPE, PA |
| 4 | Exact immutable maxima for quote TTL and band width (FZ-03, U-08) | Risk Lead, PA |
| 5 | **FZ-22 is written, not approved:** every type string, including `ActivationTerms`, the revoke, pause, resume and reduce messages and the Pay Once witness type string, is now in one source, [eip712/types.json](eip712/types.json), with the generated listing [eip712/TYPES.md](eip712/TYPES.md); the strings marked DERIVED were assembled from the field lists of 10, 11, 12 and 17 by the implementer and are a proposal. Four implementations reproduce the golden vectors (Python, generated Solidity, TypeScript, Foundry's own cheat codes) and the real Permit2 built from the pinned commit accepts the witness string (evidence report). Two points of the snapshot encoding are open decisions, not edits: the implemented encoding does not hash `customer`, `anchorStartsAt` and `boundsVersion` (finding F-06) and orders the cap table differently from the typed data (F-07). Condition C-11 of `freeze_readiness.py` stays unmet until the Wallet Protocol Engineer and the Solidity Lead approve the fingerprint | Solidity Lead |
| 6 | The cycle rule of PC-16 places no upper bound on how late a cycle may settle; whether a bound is wanted is a product decision (found with the configuration records) | Payments PM, PA |
