# FastPay Specification Workspace

| Field | Value |
|---|---|
| Version | 0.5.0 (shared-allowance migration with normal and emergency modes, seven-field account pin and ERC-1271 evidence binding, signer-set emergency removal, Permit2 pinned commit, Foundry export of the Python models, three-tier roadmap, configuration records; see [CHANGELOG](CHANGELOG.md)) |
| Date | 2026-10-16 |
| Status | DRAFT — nothing in this workspace is approved, audited, or production-ready. **The v0.4 direction is accepted for testnet engineering; protocol freeze (RG-016) is not approved** ([16](16-freeze-decision-report.md); `python -I tools/freeze_readiness.py` prints NOT READY) |
| Owner | Principal Product Manager (spec), Principal Blockchain Architect (protocol) |
| Source prompt | `FASTPAY HIGH-SIGNAL MASTER PROMPT v1.0`, section 28 "Starting Task", plus the sponsor's mandatory corrections (revision 0.2), final pre-freeze corrections (revision 0.3), the 0.4 instructions and the final pre-freeze corrections of 2026-10-16 (revision 0.5) |

This is the Phase 0 package. It does **not** contain contracts, services, or mainnet addresses. It contains the structure, evidence base, decisions, protocols and plan that everything else is built on.

## Contents

| # | Document | What it is |
|---|---|---|
| 01 | [Specification table of contents](01-toc.md) | Multi-level TOC, artifact metadata schema, RTM schema, runbook index RB-001…033 |
| 02 | [Source register and research plan](02-source-register.md) | Sources, claims, evidence register, research plan RP-01…30 |
| 03 | [Assumptions, open decisions, conflicts, risks](03-assumptions-decisions-risks.md) | ASM-001…033, OD-001…034, CF-001…018, RISK-001…034, counsel questions |
| 04 | [Context diagram and trust boundaries](04-context-and-trust-boundaries.md) | Trust zones, TM-01…19, TB-01…18, authority matrix, untrusted inputs |
| 05 | [Capability discovery and recurring activation planner](05-evm-authorization-decision-tree.md) | Protocol B: Permit2 `AllowanceTransfer` + mandate; planner 1.4.0 with account modes, the seven-field account pin and shared-allowance sizing (R-L2-SHARED); revocation flows defined by fork tests; golden vectors |
| 06 | [Initial architecture](06-initial-architecture.md) | Surfaces by version, system and contract architecture, invariants, ADR-001…023 (020 to 023: versioned price bounds and the snapshot, the manager split, the migration plan, the signer-set registry) |
| 07 | [Delivery plan, 50-person org](07-delivery-plan.md) | **Exploratory** schedule in **three tiers** (testnet reference implementation, private mainnet beta, full GA platform) with FS/SS/FF dependencies and P50/P75/P90 for every milestone, squad load, epic profiles, generated epic tables, release phases |
| 08 | [Production blockers and release gates](08-production-blockers-and-release-gates.md) | PB-001…056, RG-001…016, external-verification list |
| 09 | [Capability boundaries v1.0 / v1.1 / v2.0](09-capability-boundaries.md) | Conversion code **absent** from Router v1; conditions C1, C2 and rollout switch R; enablement criteria; absence checks |
| 10 | [Protocol A: Pay Once](10-pay-once-protocol.md) | Permit2 `SignatureTransfer`, witness, PO-1…PO-6, vectors |
| 11 | [Dual cap model and signed quote schema](11-dual-cap-model.md) | Three cap classes, `PriceQuote` v1, validity predicate, blast radius |
| 12 | [Router lifecycle and migration (mandate lineage)](12-router-lifecycle-and-migration.md) | Lifecycle, lineage, **exact `activateSuccessor` predicates**, **the shared Permit2 allowance (normal and emergency migration, exposure index, siblings)**, migration snapshot and containment proof, atomic and legacy flows, no-overlap claim, stranded-mandate prevention, rollback, communications |
| 13 | [EIP-7702 delegation: semantics, inspection, revalidation](13-eip7702-delegation-inspection.md) | Persistent delegation, records and evidence, revalidation before every unattended charge (layer B), `DELEGATION_UNVERIFIED`, vectors DRV-01…25 |
| 14 | [Protocol freeze pack](14-protocol-freeze-pack.md) | Freeze checklist (RG-016), fingerprints, unresolved blockers by gate, exact testnet scope, audit process |
| 15 | [Wallet lab matrix](15-wallet-lab-matrix.md) | Wallets × account types and modes × tests WL-01…40, evidence format, verdict function; MetaMask `UNTESTED`, Trust Wallet `UNKNOWN` |
| 16 | [Protocol freeze decision report](16-freeze-decision-report.md) | **Freeze not approved.** Accepted and unresolved decisions, unverified external facts, testnet-safe and production-blocking constants, exact audit scope, exact wallet-lab evidence, pinned Permit2 review |
| 17 | [Account Compatibility Policy](17-account-compatibility-policy.md) | Five account modes, permission matrix, **the seven-field `AccountPin`, what the contract verifies and what stays off chain, signature capability bound to the pin**, scenarios, ACP-TV vectors |
| 18 | [Configuration records](18-configuration-records.md) | Each production-blocking constant (PC-01…PC-19) as its own record: owner, unit, rationale, evidence, safe range, test, release gate, approval block (none signed) |
| — | [evidence/](evidence/README.md) | Recorded evidence read by `tools/freeze_readiness.py`: the pinned Permit2 record ([permit2/pin.json](evidence/permit2/pin.json)), wallet-lab run records (none), the freeze register |
| — | [foundry/](foundry/) | Foundry project: reference model of the migration, pin and signer-set predicates; vectors exported from the Python models; fuzz, invariant, mutation, integer-width, timestamp-boundary, shared-allowance, loop-bound, reentrancy, EIP-712 and fork suites. **Compiled and run under the pinned toolchain** ([results](evidence/implementation/REPORT.md)); it tests a reference model, not contracts |
| — | [../contracts/](../contracts/README.md) | **The actual FastPay contracts** (not the reference model): manager, usage ledger, successor validator, signature gateway, migration queue, router, registries; frozen compiler settings; suites, mutation testing and fork variants. Not audited; the constants are proposals |
| — | [toolchain/](toolchain/toolchain.lock.json) | The pinned toolchain (Foundry v1.8.5, solc 0.8.24 and 0.8.17, forge-std, the Permit2 dependency graph) with URL, commit and SHA-256 of every artifact, the policy-enforced fetch and its records, and the tools that run forge and rebuild Permit2 |
| — | [eip712/](eip712/TYPES.md) | Every EIP-712 type string in one source (`types.json`, a **proposal**: not frozen), generated Solidity and TypeScript, golden vectors, `eth_signTypedData_v4` payloads for the wallet lab |
| — | [evidence/implementation/REPORT.md](evidence/implementation/REPORT.md) | **Implementation evidence report** (generated): the ten items of the implementation instruction, the Permit2 reproduction, the fork runs, the findings F-01…F-22, the five classes of evidence kept apart, the actual contracts, and what was not done |
| — | [jira/backlog.csv](jira/backlog.csv) | 118 epics and 966 stories (1,084 backlog issues); generated by [jira/build_backlog.py](jira/build_backlog.py) from the epic data, the v0.3 to v0.5 overlays and the schedule results |
| — | [jira/schedule_model.py](jira/schedule_model.py) | Critical-path Monte Carlo model; `--write` regenerates `schedule_results.json` |
| — | [tools/](tools/) | `eip712_vectors.py` (quote, identifier, pin and snapshot vectors), `protocol_model.py` and `model_checks.py` (Lemma M, shared-allowance, pin and signer-set models; mutation analysis), `export_foundry.py` and `solidity_lint.py` (Python vectors into Foundry tests), `sync_vectors.py` (writes vectors into the documents; `--verify` in CI), `freeze_fingerprints.py` (freeze fingerprints), `permit2_pin_check.py` (pinned Permit2 record, `--online` re-reads the chains), `build_config_records.py` (document 18), `freeze_readiness.py` (the ten freeze conditions from recorded evidence), `check_all.py` (every consistency check) |
| — | [jira/dependencies.csv](jira/dependencies.csv) | Every schedule dependency: predecessor, successor, FS/SS/FF, lag in weeks, rule |
| — | [CHANGELOG.md](CHANGELOG.md) | What changed in 0.2, 0.3, 0.4 and 0.5 and why |

The backlog is a **planning baseline**: every epic has a profile (feature, protocol, research, security, data, compliance, infrastructure, migration, program) that fixes which story types it must carry, but it is not implementation-complete; stories are refined at each phase planning gate. The schedule is a Monte Carlo over the epics' dependency network with squad queues and external waits, not an aggregate capacity check.

## Labels (used verbatim everywhere)

`ASSUMPTION` · `OPEN-DECISION` · `NON-GOAL` · `RISK` · `SECURITY-CRITICAL` · `PRIVACY-CRITICAL` · `FINANCIAL-CONTROL` · `LEGAL-REVIEW-REQUIRED` · `PRODUCTION-BLOCKER`

## Identifier scheme

| Prefix | Meaning | Prefix | Meaning |
|---|---|---|---|
| `SRC-` | Source | `ASM-` | Assumption |
| `CLM-` | Claim extracted from a source | `OD-` | Open decision |
| `EV-` | Evidence item | `CF-` | Conflict |
| `ADR-` | Architecture decision record | `RISK-` | Risk |
| `PB-` | Production blocker | `RG-` | Release gate |
| `RP-` | Research-plan task | `TB-` | Trust boundary |
| `FP-REQ-<SURF>-nnn` | Requirement | `EPIC-`, `STORY-` | Backlog items |
| `TV-`, `TV-PO-`, `CAP-TV-`, `MIG-TV-`, `DRV-`, `SV-` | Golden vectors (recurring planner, Pay Once, caps and signer sets, migration, delegation revalidation, session) | `RB-` | Runbook |
| `FZ-`, `FG-` | Freeze checklist item, freeze fingerprint ([14](14-protocol-freeze-pack.md)) | `WL-`, `EVL-` | Wallet-lab test ([15](15-wallet-lab-matrix.md)), required lab evidence ([16 §9](16-freeze-decision-report.md)) |
| `ACP-TV-`, `RV-T`, `ZP-T`, `PR-`, `PC-`, `UD-`, `UX-`, `DEC-` | Account-policy vector, revocation fork test, zero-amount-permit gate test, Permit2 review item, production-blocking constant (one configuration record each, [18](18-configuration-records.md)), unresolved decision, unverified fact, accepted decision ([16](16-freeze-decision-report.md), [17](17-account-compatibility-policy.md)) | `SR-n` (in 11) | Signer-set property; the migration and account invariants are `I-MIG-1…11` and `I-ACCT-PIN`, `I-ACCT-NOWIDEN`, `I-ACCT-SIG`, `I-ACCT-VERSION` |

IDs are never reused or renumbered. A withdrawn item keeps its ID with status `WITHDRAWN`.

## Evidence levels (applies to every factual claim)

| Level | Meaning | May a design depend on it? |
|---|---|---|
| **E0** | Stated by someone, recalled from model knowledge, or known only from a search-result summary (the page itself was not fetched) | No. Must be tagged `ASSUMPTION`. |
| **E1** | The primary or vendor page itself was fetched and read in an automated session (summarized by a tool). Not human-reviewed, not version-pinned. | Provisionally, for planning only. |
| **E2** | Primary text read by a named human reviewer and pinned (commit hash / document version / retrieval hash). | Yes, for design. |
| **E3** | Empirically confirmed: on-chain read, bytecode hash match, fork test, or wallet-lab run with recorded evidence. | Yes, for implementation and for any user-facing "supported" claim. |

Claims verified by direct page fetch on 2026-10-13 are **E1**; claims seen only in search summaries are **E0** and are flagged as such in [02](02-source-register.md). No support or deployment claim in these documents is E3 yet. The prompt's rule "do not fabricate current support or deployment information" is applied by never promoting a claim past the level its evidence earned.

## How to read the confidence of a statement

- **Confirmed (E1+)** is shown with a `CLM-` or `SRC-` reference.
- **Recommendation** is a design position with rationale; it can change via an ADR.
- **Assumption** carries an `ASM-` ID, a validation method, and an owner.
- Anything with none of these is a defect in the document; raise it.

## Change control

All documents are versioned. A change to a `SECURITY-CRITICAL`, `FINANCIAL-CONTROL`, or `PRIVACY-CRITICAL` item requires a named reviewer from Security plus the owning squad lead, and an ADR if it alters a trust boundary or an authority in [04 §5](04-context-and-trust-boundaries.md).
