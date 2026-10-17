# 01 — FastPay Specification: Table of Contents

| Field | Value |
|---|---|
| Version | 0.5.0 |
| Status | DRAFT |
| Owner | Principal Product Manager |
| Reviewers | Principal Blockchain Architect, Head of Security, TPM |
| Depends on | Master prompt v1.0 |
| Definition of Done | Every entry has an ID, owner, target phase, and delivery status; no entry is orphaned from a prompt section; reviewers signed off on structure. |

**Status key:** `D0.1` delivered in this pass (draft) · `P0-Wn` planned in Phase 0 week n · `P1`/`P2`… planned in that phase · `DEP` depends on an open decision (shown).

## 0. Artifact metadata schema (applies to every artifact below)

Every artifact carries this header (checked by a lint script added in EPIC-P0-DOCS):

```yaml
artifact_id: FP-<DOMAIN>-<NNN>
title: ""
version: 0.1.0            # semver; major bump = changes a security-critical or financial-control rule
status: DRAFT | IN_REVIEW | APPROVED | SUPERSEDED
owner: <role>             # accountable single role
reviewers: [<role>, ...]  # >=2, at least one from a different squad; Security for SECURITY-CRITICAL
dependencies: [<artifact_id>, ...]
approval_state: NOT_REQUESTED | REQUESTED | APPROVED(<name>,<date>) | REJECTED(<reason>)
definition_of_done: ""    # testable sentence(s)
labels: []                # from the label list in README
evidence_level_floor: E0|E1|E2|E3   # lowest evidence level of any claim it relies on
```

Domains: `PRD` product · `DES` design · `PRO` protocol · `SC` contracts · `BE` backend · `API` · `DAT` data · `LED` ledger · `SEC` security · `CMP` compliance · `INF` infrastructure · `QA` · `REL` release · `OPS` operations.

## 1. Requirement template (applies to every `FP-REQ-*`)

```text
ID:              FP-REQ-<SURFACE>-<NNN>        Labels: [...]
Objective:       one sentence, measurable
Rationale:       why; link to ADR / risk / source
Actors:          primary, secondary
Preconditions:   state that must hold (checkable)
Trigger:         event or action
Main flow:       numbered steps
Alternative:     numbered, each with its own condition
Failure flows:   numbered, each with detection + customer-visible result + recovery
Data in/out:     schema refs (atomic integer units; decimal strings in JSON)
Events:          domain events + webhooks emitted
Security:        SECURITY-CRITICAL controls, threat IDs mitigated
Privacy:         data classes touched, retention, lawful basis
Observability:   metrics, logs (redaction), traces, alerts
Test method:     unit / fork / invariant / e2e / wallet-lab / token-lab; test IDs
Acceptance:      measurable criteria (number, threshold, time window)
Owner / Reviewer / Dependencies
Rollback:        how the change is reverted or the effect compensated
```

A requirement missing any field is not "ready" and cannot enter a sprint (enforced by the Jira workflow in EPIC-P0-DOCS).

## 2. Requirements Traceability Matrix (schema; empty until Phase 0 week 6)

| Req ID | Source (prompt § / SRC / ADR) | Design artifact | Contract / service | Test IDs | Evidence IDs | Release gate | Status |
|---|---|---|---|---|---|---|---|
| *(example)* FP-REQ-MND-001 | §8 mandate model | FP-PRO-004 | MandateManager.activate | TST-SC-MND-001..012 | EV-… | RG-005 | DRAFT |

Rule: a requirement with no test ID, or a test with no requirement, fails the weekly traceability check.

## 3. Master table of contents

### Part 0 — Governance of the specification
| Ref | Title | Prompt § | Owner | Status |
|---|---|---|---|---|
| 0.1 | Source Register + research plan | 5, 26.1 | Principal PM | D0.1 → [02](02-source-register.md) |
| 0.2 | Assumptions Register | 5 | Principal PM | D0.1 → [03](03-assumptions-decisions-risks.md) |
| 0.3 | Open Decisions Register | 5 | Principal PM | D0.1 → [03](03-assumptions-decisions-risks.md) |
| 0.4 | Conflict Register | 5 | Principal Architect | D0.1 seed → [03](03-assumptions-decisions-risks.md) |
| 0.5 | Risk Register | 5 | Head of Security | D0.1 seed → [03](03-assumptions-decisions-risks.md) |
| 0.6 | Architecture Decision Records | 5 | Principal Architect | D0.1 ADR-001…012 → [06](06-initial-architecture.md) |
| 0.7 | Requirements Traceability Matrix | 5 | TPM | schema D0.1; populated P0-W6 |
| 0.8 | Evidence Register | 5 | QA lead | D0.1 seed → [02](02-source-register.md) |
| 0.9 | Release Gate Register | 5 | TPM | D0.1 seed → [08](08-production-blockers-and-release-gates.md) |
| 0.10 | Compatibility Register (wallet × chain × capability, dated) | 3, 26.16 | Wallet Protocol Eng | schema D0.1 → [05 §9](05-evm-authorization-decision-tree.md); data P0-W4 |

### Part A — Product and Business (prompt 6.A)
| Ref | Title | Owner | Status |
|---|---|---|---|
| A.1 | Product vision and principles | Head of Product | P0-W3 |
| A.2 | Problem statement | Head of Product | P0-W3 |
| A.3 | Market segmentation | Payments PM | P0-W5 |
| A.4 | Merchant and customer personas | UX Researcher | P0-W5 |
| A.5 | Jobs to Be Done | UX Researcher | P0-W5 |
| A.6 | Product requirements document (25 surfaces, §7) | Payments PM | P0-W8 (MVP surfaces), P1+ (rest) |
| A.7 | Feature inventory + MVP cut | Head of Product | D0.1 draft cut → [06 §2](06-initial-architecture.md) |
| A.8 | Product roadmap | Head of Product | D0.1 → [07](07-delivery-plan.md) |
| A.9 | Pricing and unit economics | Payments PM + Finance | DEP OD-002, OD-016; P0-W8 |
| A.10 | Merchant lifecycle | Merchant PM | P0-W7 |
| A.11 | Customer lifecycle | Customer PM | P0-W7 |
| A.12 | Marketplace operating model | Merchant PM | P2 |
| A.13 | Partner strategy | Head of Product | P2 |
| A.14 | KPI tree and analytics definitions | Payments PM + Data | P0-W8 |
| A.15 | Team topology and RACI | VP Eng | D0.1 → [07 §2](07-delivery-plan.md) |

### Part B — Product Design (6.B)
| Ref | Title | Owner | Status |
|---|---|---|---|
| B.1 | Brand foundation (incl. name clearance, RISK-013) | Design Systems Lead | P0-W4 |
| B.2 | Design tokens, typography, color, spacing/layout, motion | Design Systems Lead | P0-W6 |
| B.3 | Component library + Storybook conventions | Design Systems Lead | P1 |
| B.4 | Checkout user flows (a **proposed** session and wallet-connection profile is in [19](19-checkout-session-and-wallet-connect-profile.md); not frozen, not reviewed) | Product Designer | P0-W6 |
| B.5 | FastPay activation flows (one per planner outcome, [05](05-evm-authorization-decision-tree.md)) | Product Designer | P0-W8 |
| B.6 | Merchant dashboard | Product Designer | P1 |
| B.7 | Customer mandate portal | Product Designer | P1 |
| B.8 | Admin and risk consoles | Product Designer | P1 |
| B.9 | Exact content and microcopy (consent copy is `LEGAL-REVIEW-REQUIRED`) | Content Designer | P0-W8 (activation), P1 |
| B.10 | Accessibility specification (WCAG 2.2 AA target — ASM-020) | Design Systems Lead | P0-W6 |
| B.11 | Localization and RTL specification | Content Designer | P0-W8 |
| B.12 | Figma/Storybook delivery conventions | Design Systems Lead | P0-W4 |

### Part C — Protocol and Blockchain (6.C)
| Ref | Title | Owner | Status |
|---|---|---|---|
| C.1 | Trust model | Principal Architect | D0.1 → [04](04-context-and-trust-boundaries.md) |
| C.2 | EVM capability negotiation | Wallet Protocol Eng | D0.1 → [05](05-evm-authorization-decision-tree.md) |
| C.3 | EIP-5792 behavior profile (MetaMask documented at E1; runtime detection mandatory) | Wallet Protocol Eng | D0.2 (§ in 05); P0-W4 lab |
| C.4 | EIP-7702 and account behavior profile (wallet-managed, persistent, inspected and recorded; governed by the Account Compatibility Policy) | Wallet Protocol Eng | D0.4 → [13](13-eip7702-delegation-inspection.md), [17](17-account-compatibility-policy.md); DEP OD-011 |
| C.5 | Permit2 integration | AA/Protocol Eng | P0-W5 |
| C.6 | Activation planner | Wallet Protocol Eng | D0.1 → [05](05-evm-authorization-decision-tree.md) |
| C.7 | Mandate specification (§8, state machine, guards, events) | Principal Architect | P0-W6 |
| C.8 | Payment protocol (§11 states and transitions) | Principal Architect | P0-W7 |
| C.9 | Fallback protocol | Principal Architect | P0-W7 |
| C.10 | Subscription protocol | Principal Architect | P1 |
| C.11 | Refund protocol | Principal Architect | DEP OD-007; P1 |
| C.12 | Native asset policy | Principal Architect | DEP OD-009; P0-W8 |
| C.13 | Chain adapter interfaces (family-agnostic; EVM first) | Principal Architect | P1 |
| C.14 | Protocol versioning and migration | Principal Architect | P1 |
| C.15 | Protocol A — Pay Once on Permit2 `SignatureTransfer` (witness, entrypoints, PO-1…PO-6) | Wallet Protocol Eng | D0.2 → [10](10-pay-once-protocol.md) |
| C.16 | Dual cap model: three cap classes (on-chain hard, quote-bound on-chain, backend-only), signed quote schema `PriceQuote` v1, bounded price inputs, blast radius | Principal Architect | D0.3 → [11](11-dual-cap-model.md) |
| C.17 | Router lifecycle and mandate-lineage migration protocol (state machine, exact `activateSuccessor` predicates, migration snapshot and containment, atomic and legacy flows) | Principal Architect | D0.4 → [12](12-router-lifecycle-and-migration.md) |
| C.18 | EIP-7702 delegation semantics, inspection, records and per-charge revalidation (layer B of the Account Compatibility Policy) | Wallet Protocol Eng | D0.4 → [13](13-eip7702-delegation-inspection.md) |
| C.19 | Capability boundaries v1.0 / v1.1 / v2.0: conversion code absent from Router v1; conditions C1, C2 and rollout switch R | Head of Product + Principal Architect | D0.3 → [09](09-capability-boundaries.md) |
| C.20 | Protocol freeze pack: freeze checklist (RG-016), fingerprints, testnet scope, audit-scope principles | Principal Architect | D0.4 → [14](14-protocol-freeze-pack.md) |
| C.21 | Wallet lab matrix: wallets, account types and modes, tests WL-01…WL-40, evidence format, verdict function | QA Lead | D0.5 → [15](15-wallet-lab-matrix.md) |
| C.22 | Protocol freeze decision report: accepted and unresolved decisions, unverified external facts, testnet-safe and production-blocking constants, exact audit scope, exact wallet-lab evidence, pinned Permit2 review (commit pinned, answers recorded, E2 pending); **freeze not approved** | Principal Architect | D0.5 → [16](16-freeze-decision-report.md) |
| C.23 | Account Compatibility Policy: account modes, permissions, the seven-field account pin, the contract-versus-off-chain split, signature-capability binding, scenarios, vectors ACP-TV | Wallet Protocol Eng | D0.5 → [17](17-account-compatibility-policy.md) |
| C.24 | Configuration records: each production-blocking constant as its own record (owner, unit, rationale, evidence, safe range, test, release gate, approval block) | Principal Architect | D0.5 → [18](18-configuration-records.md) |
| C.25 | Recorded evidence and freeze readiness: pinned Permit2 record, wallet-lab run records, freeze register, `freeze_readiness.py` | TPM, QA Lead | D0.5 → [evidence/](evidence/README.md) |
| C.26 | Executable suites: Foundry reference model, exported vectors, fuzz, invariant, mutation, integer-width, timestamp-boundary, shared-allowance and fork tests | Solidity Lead, QA Lead | D0.5 → [foundry/](foundry/) |
| C.27 | Checkout session and wallet-connection profile: hosted self-custody checkout, the `CheckoutSession` object and its state machine, expiry and quote rules, the wallet-connection profile (every wallet claim `UNVERIFIED`), the two QR codes, customer experiences, merchant integration (**PROPOSED**; needs Security and Privacy review and wallet-lab evidence) | Principal Product Manager, Wallet Protocol Eng | PROPOSED → [19](19-checkout-session-and-wallet-connect-profile.md) |

### Part D — Smart Contracts (6.D, §12)
| Ref | Title | Owner | Status |
|---|---|---|---|
| D.1 | Contract-by-contract specification (responsibility, trust boundary, storage, roles, functions, events, errors, invariants, …) for PaymentRouter, MandateManager, MerchantRegistry, TokenPolicyRegistry, ExecutorRegistry, FeeController, RefundManager, EmergencyGuardian, DEXAdapterRegistry, EIP7702Executor (DEP OD-011), SignatureVerifier | Principal Architect | outline D0.1 ([06 §4](06-initial-architecture.md)); full P1 |
| D.2 | Events, custom errors, storage layouts | Solidity Lead | P1 |
| D.3 | Access control matrix | Principal Architect | D0.1 → [04 §5](04-context-and-trust-boundaries.md) |
| D.4 | Upgradeability decision | Principal Architect | D0.1 → ADR-001 (DEP OD-004) |
| D.5 | Deployment scripts (Foundry) | Solidity Lead | P1 |
| D.6 | Foundry unit, fuzz, invariant tests | Contract Security Eng | P1 |
| D.7 | Audit package | Contract Security Eng | P2 |

### Part E — Backend and Developer Platform (6.E, §13–14)
| Ref | Title | Owner | Status |
|---|---|---|---|
| E.1 | Service architecture (modular monolith + isolated services) | Backend Tech Lead | D0.1 → [06 §5](06-initial-architecture.md) |
| E.2 | Per-service spec (21 services, §13 template) | Backend Tech Lead | P0-W8 (outline), P1 |
| E.3 | REST API reference (25 resource groups, §14 template) | Backend Tech Lead | P1 |
| E.4 | Webhook specification | Backend Tech Lead | P1 |
| E.5 | SDKs (JS/TS first) | Frontend/SDK Lead | P1 |
| E.6 | Developer documentation | Technical Writer | P1 |

### Part F — Data and Finance (6.F, §15–16)
| Ref | Title | Owner | Status |
|---|---|---|---|
| F.1 | PostgreSQL model (35 tables, §15 template) | Data/Ledger Eng | P1 |
| F.2 | ER model, event schemas, outbox/inbox | Data/Ledger Eng | P1 |
| F.3 | Double-entry ledger + chart of accounts (§16, 20 scenarios) | Ledger Eng | P0-W8 (CoA + 6 core scenarios), P1 |
| F.4 | Reconciliation model, settlement reporting, refund accounting | Ledger Eng | P1 |
| F.5 | Data warehouse, product & financial analytics | Data Eng | P2 |
| F.6 | Retention, privacy model, backup and recovery | Privacy Lead + SRE | P1 |

### Part G — Security and Compliance (6.G, §18–20)
| Ref | Title | Owner | Status |
|---|---|---|---|
| G.1 | Threat model (30+ threats, §18 template) | Head of Security | v0 trust model D0.1; full P0-W8 |
| G.2 | Abuse cases, security requirements | Head of Security | P1 |
| G.3 | Key management & administration (§19) | Head of Security | P1 |
| G.4 | Supply-chain, frontend, API, smart-contract security standards | AppSec | P1 |
| G.5 | Detection engineering (§23 rules) | Detection Eng | P2 |
| G.6 | Incident response + audit strategy + bug bounty | Head of Security | P1 / P2 |
| G.7 | Regulatory perimeter questions | Head of Compliance + counsel | D0.1 questions → OD-001; memo P0-W8 |
| G.8 | KYB, underwriting, KYC triggers, AML/sanctions, Travel Rule, fraud engine, case mgmt | Head of Compliance | P1 |
| G.9 | Consumer protection, recurring-payment consent, privacy/GDPR/DPIA | Compliance + Privacy | P1 |

### Part H — Infrastructure and Operations (6.H, §21, §24)
| Ref | Title | Owner | Status |
|---|---|---|---|
| H.1 | Cloud decision (AWS/Azure/GCP) | SRE Lead | DEP OD-015; ADR P0-W6 |
| H.2 | Environments, networks, compute, DB, cache, messaging, RPC routing | SRE Lead | P1 |
| H.3 | CI/CD, IaC, KMS/HSM, secrets | SRE Lead + AppSec | P1 |
| H.4 | Observability, SLOs, on-call, DR, cost | SRE Lead | P1 |
| H.5 | Runbooks RB-001…RB-033 (§24 list plus three additions) and support playbooks | Incident Ops Lead | stubs P2; full P3+ |
| H.6 | Status page | SRE Lead | P2 |

### Part I — Quality and Launch (6.I, §22, §25)
| Ref | Title | Owner | Status |
|---|---|---|---|
| I.1 | Master test plan | QA Lead | P0-W8 |
| I.2 | Wallet compatibility laboratory | QA Lead + Wallet Protocol Eng | lab design P0-W3; running P0-W4+ |
| I.3 | Token compatibility laboratory | QA Lead + Contract Security | P0-W6 |
| I.4 | Fork, fuzz, invariant, e2e, load, soak, chaos, a11y, l10n, security, DR tests | QA Lead | P1+ |
| I.5 | Release management, migration, rollback | TPM | P1 |
| I.6 | Rollout phases 1–8 (§25), GA checklist and the critical-path schedule (P50/P75/P90) | TPM | D0.3 → [07](07-delivery-plan.md), [08](08-production-blockers-and-release-gates.md) |
| I.7 | Support readiness | Support Lead | P2 |

### Part J — Product surface specifications (§7: 25 surfaces × 25 fields each)

Each surface gets one document `FP-PRD-S<nn>` using the §7 field list (business objective … acceptance criteria). Versions come from [09 §2](09-capability-boundaries.md): **v1.0** = 18 surfaces (14 MVP for private beta + 4 by public beta), **v1.1** = 2, **v2.0** = 5.

| ID | Surface | Version | Spec target |
|---|---|---|---|
| S01 | Hosted Checkout | v1.0 (MVP) | P0-W10 |
| S02 | Embedded Checkout | v1.0 (public beta) | P1 |
| S03 | Payment Links | v1.0 (public beta) | P1 |
| S04 | Pay Once | v1.0 (MVP) | P0-W10 |
| S05 | FastPay Activation | v1.0 (MVP) | P0-W10 |
| S06 | One-Click Repeat Purchase | v1.1 | P4 |
| S07 | Fixed Subscriptions | v1.0 (MVP) | P0-W10 |
| S08 | Variable Subscriptions | v1.1 | P4 |
| S09 | Usage-Based Billing | v2.0 | P6 |
| S10 | Auto Top-Up | v2.0 | P6 |
| S11 | Marketplace Split Payments | v2.0 (needs Router v2) | P6 |
| S12 | Merchant Settlement | v1.0 (MVP) | P0-W10 |
| S13 | Refunds | v1.0 (merchant-push in beta, full by GA; DEP OD-007) | P1 |
| S14 | Customer Receipts | v1.0 (MVP) | P0-W10 |
| S15 | Merchant Webhooks | v1.0 (MVP) | P0-W10 |
| S16 | Merchant Dashboard | v1.0 (MVP, basic) | P1 |
| S17 | Customer Mandate Portal (incl. delegation status, migration prompts) | v1.0 (MVP) | P1 |
| S18 | Developer Portal | v1.0 (MVP, basic) | P1 |
| S19 | Admin Console | v1.0 (MVP, basic) | P1 |
| S20 | Risk Console | v1.0 (MVP, basic) | P1 |
| S21 | Token Registry Console | v1.0 (MVP) | P1 |
| S22 | Incident Console (incl. flag state and kill switches) | v1.0 (MVP, basic) | P1 |
| S23 | Reporting and Exports | v1.0 (public beta) | P1 |
| S24 | White-Label Checkout | v2.0 | P6 |
| S25 | Partner Platform API | v2.0 | P6 |

### Part K — Backlog
| Ref | Title | Status |
|---|---|---|
| K.1 | Jira-importable backlog: 118 epics, 966 stories; **every epic has a profile (feature, protocol, research, security, data, compliance, infrastructure, migration, program) that fixes which story types it must carry**; planning baseline, not implementation-complete | D0.3 → [jira/backlog.csv](jira/backlog.csv) |
| K.2 | Story refinement | split, re-estimated and re-sequenced at each phase planning gate; thresholds marked PROPOSAL reviewed by owners |

## 4. Runbook index (fixes the numbering used across the workspace)

Order follows prompt §24. Each runbook needs: trigger, detection, severity, incident commander, containment, financial safeguards, customer impact, customer communication, merchant communication, regulatory escalation, evidence preservation, recovery, validation, postmortem.

| RB | Runbook | RB | Runbook |
|---|---|---|---|
| RB-001 | API outage | RB-016 | Token depeg |
| RB-002 | Database failover | RB-017 | DEX outage |
| RB-003 | Queue backlog | RB-018 | Oracle divergence |
| RB-004 | RPC outage | RB-019 | Double-charge allegation |
| RB-005 | RPC disagreement | RB-020 | Unknown-payment spike |
| RB-006 | Chain halt | RB-021 | Webhook backlog |
| RB-007 | Deep reorg | RB-022 | Data breach |
| RB-008 | Stuck executor nonce | RB-023 | Merchant compromise |
| RB-009 | Executor key compromise | RB-024 | Fraud surge |
| RB-010 | Deployer key compromise | RB-025 | Bad contract deployment |
| RB-011 | Malicious frontend | RB-026 | Bad registry release |
| RB-012 | DNS compromise | RB-027 | Kubernetes / compute-platform outage |
| RB-013 | Permit2 integration defect | RB-028 | Regional outage |
| RB-014 | EIP-7702 delegation defect | RB-029 | Backup restore failure |
| RB-015 | Token exploit | RB-030 | Sanctions alert surge |


Additions in revision 0.2 (beyond prompt §24):

| RB | Runbook |
|---|---|
| RB-031 | Router migration campaign ([12](12-router-lifecycle-and-migration.md)) |
| RB-032 | Emergency router disablement and customer re-bind |
| RB-033 | Conversion emergency-off ([09 §5](09-capability-boundaries.md)) |

## 5. Coverage check against the master prompt

| Prompt § | Where it lands |
|---|---|
| 1 Role | Team topology [07 §2](07-delivery-plan.md) |
| 2 Product | Parts A, J |
| 3 Authorization architecture | [04](04-context-and-trust-boundaries.md), [05](05-evm-authorization-decision-tree.md), [10](10-pay-once-protocol.md), [13](13-eip7702-delegation-inspection.md), Part C |
| 4 Security principles | [04 §3](04-context-and-trust-boundaries.md) (TM-01…TM-18), Part G |
| 5 Delivery method | Part 0 |
| 6 Artifact package | Parts A–I |
| 7 Surfaces | Part J |
| 8 Mandate model | C.7, [11](11-dual-cap-model.md), [12](12-router-lifecycle-and-migration.md) |
| 9 Planner | [05](05-evm-authorization-decision-tree.md) |
| 10 Token registry | C.12, I.3, Part D (TokenPolicyRegistry), [09](09-capability-boundaries.md) §6 (token-lab approval) |
| 11 Payment execution | C.8, C.9 |
| 12 Contracts | Part D |
| 13–14 Backend/API | Part E |
| 15–16 Data/Ledger | Part F |
| 17 Subscriptions | C.10, S07–S10 |
| 18–20 Security/Compliance | Part G |
| 21, 24 Infra/IR | Part H |
| 22, 25 Test/Release | Part I, [08](08-production-blockers-and-release-gates.md), [14](14-protocol-freeze-pack.md), [15](15-wallet-lab-matrix.md) |
| 23 Observability | H.4, G.5 |
| 26 Execution order | [07](07-delivery-plan.md) |
