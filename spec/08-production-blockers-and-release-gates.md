# 08 — Production Blockers, Release Gates, and External Verification

| Field | Value |
|---|---|
| Artifact | FP-REL-002 (Parts 0.9, I.6) |
| Version | 0.5.0 |
| Status | DRAFT — every item is `OPEN` |
| Owner | Technical Program Manager (register), Head of Security and Head of Compliance (gate vetoes) |
| Reviewers | VP Eng, Head of Product, Principal Architect, QA Lead |
| Dependencies | [02](02-source-register.md), [03](03-assumptions-decisions-risks.md), [07](07-delivery-plan.md), [09](09-capability-boundaries.md)–[17](17-account-compatibility-policy.md) |
| Definition of Done | Each blocker states what evidence closes it, which gate it blocks, and who owns it; each gate lists its blockers and its sign-offs; nothing here is marked closed without an `EV-` link. |

**Rule.** A `PRODUCTION-BLOCKER` is closed only by evidence at the level named in the "Closed when" column, recorded in the Evidence Register. Nobody closes a blocker by assertion. Generated work, including everything in this workspace, is **not** production-ready, audited, legally approved, or tested on any wallet or chain.

## 1. Production blockers

Gate abbreviations: RG-nnn as defined in §2.

### 1.1 Smart contracts and protocol

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-001 | Immutable core deployed from a signed manifest; bytecode verified against the audited build on every chain by two independent parties; contracts verified on explorers (ADR-001) | `SECURITY-CRITICAL` | Verification records (EV) for each chain; deployer privileges renounced and shown on chain | RG-010 | Principal Architect |
| PB-002 | Two independent audits complete; all critical and high findings fixed and re-reviewed by the finding firm | `SECURITY-CRITICAL` | Final reports; remediation log; firm re-review letters | RG-005 → RG-010 | Head of Security |
| PB-003 | All system invariants `I-*` ([06 §4.1](06-initial-architecture.md)) pass invariant/fuzz/fork suites; selected properties (`I-CAP-TOKEN`, `I-CAP-FIAT`, `I-ONCE`, `I-MINOUT`) formally verified or independently reviewed | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` | CI history ≥ 1,000,000 invariant calls without violation; formal-verification reports | RG-005 | Contract Security Eng |
| PB-004 | Permit2 present and unmodified on every enabled chain; continuous bytecode monitoring live (EV-P01) | `SECURITY-CRITICAL` | `eth_getCode` hash match from ≥2 RPCs plus explorer; monitor alert test | RG-004 | Solidity Lead |
| PB-005 | Permit2 behavior assumptions confirmed from source: ERC-1271 owners, witness transfers, spender binding, who may call `lockdown`/`invalidateNonces`, the allowance usability boundary (EV-P06; the pinned-commit review and fork tests are PB-053) | `SECURITY-CRITICAL` | Source review at E2 plus fork tests | RG-002 | AA/Protocol Eng |
| PB-006 | Router lifecycle and migration playbook rehearsed on testnet: deprecate, migrate (all partial states), sunset, retire, rollback ([12](12-router-lifecycle-and-migration.md)) | `SECURITY-CRITICAL` | Rehearsal record; customer-communication templates approved | RG-006 | Principal Architect |
| PB-007 | Governance multisig + timelock, guardian multisig, executor and charge-signer key classes constituted; no single individual controls production contracts, keys or emergency powers (OD-023) | `SECURITY-CRITICAL` | Ceremony records; signer roster review; access test | RG-006 | Head of Security |

### 1.2 Wallet, chain, and token evidence

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-008 | Wallet capability evidence at E3 for every wallet/version/account type/chain FastPay will claim as supported; Compatibility Register published and dated | `SECURITY-CRITICAL` | Register rows with raw outputs and evidence ids; retest dates in the future | RG-003 | QA Lead |
| PB-009 | Consent is not reliant on hardware-device display; typed-data readability established per wallet (ASM-006/007) | `SECURITY-CRITICAL` `PRIVACY-CRITICAL` | RP-21 study; UX decisions applied | RG-003 | Product Designer |
| PB-010 | Per-chain finality thresholds evidenced and implemented; multi-source quorum proven by chaos tests (TM-06) | `FINANCIAL-CONTROL` | RP-22 data; chaos report with zero false finalization | RG-004 | Chain Infra Lead |
| PB-011 | Token lab at E3 for every listed token; registry controls and drift watchers live (RISK-007) | `SECURITY-CRITICAL` | Token matrix; watcher test auto-blocks a simulated upgrade | RG-004 | Contract Security Eng |
| PB-012 | Wallet previews can decode FastPay calls: contracts verified on explorers and ABIs registered where wallets read them | `SECURITY-CRITICAL` | Screenshots of decoded prompts in lab wallets | RG-006 | Solidity Lead |
| PB-013 | Conversion scope decided by directive and corrected on 2026-10-13: v1.0 direct stablecoin settlement ON and **conversion code absent from Router v1**; v1.1 stable conversion in a separately audited router version, opt-in; v2.0 general conversion after audit and token-lab approval; reflected in code, copy, flags and manifest ([09](09-capability-boundaries.md)); native-asset policy (OD-009) recorded | | ADRs approved; capability matrix reviewed | RG-001 | Principal Architect |

### 1.3 Platform, finance, and operations

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-014 | No double charge: exactly-once per `(mandate, cycle)` enforced on chain; `UNKNOWN` handling prevents second-token charge; chaos tests pass (ADR-009) | `FINANCIAL-CONTROL` | Race and chaos reports | RG-007 | Payments Core lead |
| PB-015 | Immutable double-entry ledger with reorg reversal and daily reconciliation; 28 consecutive days of matched reconciliation on mainnet beta | `FINANCIAL-CONTROL` | Reconciliation history | RG-007 → RG-011 | Ledger Eng |
| PB-016 | Refund and dispute model implemented and legally reviewed (OD-007, OD-018) | `FINANCIAL-CONTROL` `LEGAL-REVIEW-REQUIRED` | Flows tested; counsel review | RG-007, RG-008 | Principal PM |
| PB-017 | Gas-sponsorship and fee economics validated on launch chains (OD-002, OD-016) | `FINANCIAL-CONTROL` | Unit-economics model with measured gas shows non-negative contribution at p90 gas | RG-007 | Principal PM |
| PB-018 | Beta limits and circuit breakers implemented and tested (per mandate, customer, merchant, global) | `FINANCIAL-CONTROL` | Limit test report | RG-010 | Risk Lead |
| PB-019 | Signer service enforces policy; executor-key compromise drill passed (RISK-005) | `SECURITY-CRITICAL` | Policy test; drill report | RG-006 | Chain Infra Lead |
| PB-020 | Tenant isolation proven (row-level security + tenant fuzz) | `SECURITY-CRITICAL` `PRIVACY-CRITICAL` | Fuzz report; pen-test result | RG-006 | Payments Core lead |
| PB-021 | Webhook signing, replay window, secret rotation and SSRF defenses verified | `SECURITY-CRITICAL` | Test and pen-test reports | RG-006 | Payments Core lead |

### 1.4 Security program

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-022 | Frontend integrity: strict CSP and SRI, no third-party scripts at checkout, typed-data-only lint, build provenance, DNS/CDN/certificate monitoring | `SECURITY-CRITICAL` | CI gates; DAST; monitoring test | RG-006 | Application Security |
| PB-023 | Penetration test and red-team exercises complete with no open critical or high findings | `SECURITY-CRITICAL` | Pen-test report; retest letter | RG-006 | Head of Security |
| PB-024 | Supply chain: pinned dependencies, SBOM, signed artifacts, provenance, hardened CI, no long-lived deploy credentials | `SECURITY-CRITICAL` | Attestation verification gate in deploy pipeline | RG-006 | SRE Lead |
| PB-025 | Detection rules for the prompt §23 list implemented with alert routing tested | `SECURITY-CRITICAL` | Detection test results | RG-009 | Detection Engineer |
| PB-026 | Bug bounty live (private for beta; public plus contest/extended review for public beta) (OD-019) | `SECURITY-CRITICAL` | Program pages; triage log | RG-010 (private), RG-011 (public) | Head of Security |

### 1.5 Legal, compliance, and privacy

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-027 | Regulatory perimeter memo(s) for every launch jurisdiction; licensing or partner path in place (OD-001, Q-01…Q-20) | `LEGAL-REVIEW-REQUIRED` | Counsel letters; licence or agreement copies | RG-008 | Head of Compliance |
| PB-028 | Merchant KYB/underwriting, sanctions and AML monitoring operational; Travel Rule applicability resolved | `LEGAL-REVIEW-REQUIRED` | Workflow tests; counsel opinion | RG-008 | Head of Compliance |
| PB-029 | Recurring-payment consent, disclosures, reminders and cancellation meet each market's rules; consent copy legally reviewed | `LEGAL-REVIEW-REQUIRED` `PRIVACY-CRITICAL` | Counsel sign-off on copy keys | RG-008 | Head of Compliance |
| PB-030 | DPIA complete; retention, data-subject requests, controller/processor roles, cross-border transfers settled (RP-12, OD-020) | `PRIVACY-CRITICAL` `LEGAL-REVIEW-REQUIRED` | DPIA; DSR test | RG-008 | Privacy Lead |
| PB-031 | Terms of service, merchant agreement, liability positions and prohibited-business policy reviewed | `LEGAL-REVIEW-REQUIRED` | Counsel sign-off | RG-008 | General Counsel |
| PB-032 | Product name cleared in launch markets (RISK-013, OD-021) | `LEGAL-REVIEW-REQUIRED` | Trademark report | RG-001 (decision), RG-010 (use in market) | General Counsel |

### 1.6 Operations and readiness

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-033 | Incident-response exercise: runbooks RB-001…RB-030 exist; Sev-1 runbooks exercised | | Exercise reports; post-mortems closed | RG-009 | Incident Ops Lead |
| PB-034 | Disaster-recovery exercise meets RPO/RTO (proposed ≤1 min / ≤30 min) | | Restore drill record | RG-009 | SRE Lead |
| PB-035 | On-call, status page, support playbooks (19 scenarios) and communication templates ready | | Role-play records; status page live | RG-009 | Support Lead |
| PB-036 | Accessibility (WCAG 2.2 AA) and localization testing complete for customer-facing flows including consent | | Independent audit report | RG-008 | Design Systems Lead |

### 1.7 Decisions and evidence that gate everything

| PB | Blocker | Labels | Closed when | Blocks | Owner |
|---|---|---|---|---|---|
| PB-037 | Blocking open decisions recorded as ADRs: OD-001, 003, 007, 017, 022, 023, 024, 025, 026, 027, 028. OD-004, 006, 012 were decided by the sponsor directive of 2026-10-13 and need their ADRs approved | `OPEN-DECISION` | ADR approval records | RG-001 (OD-003/024/025/026/027/028), RG-008 (OD-001), RG-007 (OD-007) | Principal PM |
| PB-038 | Every design-load-bearing claim at E2; every public support claim at E3 and within its retest window (README evidence levels, RISK-023) | | Source Register audit; Compatibility Register check | RG-001 (E2), RG-003/010 (E3) | Principal PM |
| PB-039 | Registry of unverified facts is empty for the release scope: no item in [02 §2](02-source-register.md) at E0 supports a shipped behavior | | Register audit | RG-010 | Principal PM |
| PB-040 | **Conversion code proven absent from v1.0**: on every chain the release pipeline shows that the ABI of every deployed v1.0 contract contains no conversion selector, the static call graph reaches only the external-call allowlist (Permit2, registry-listed tokens, `MandateManager`, `RouterRegistry`, fixed registries), and the signed manifest lists no adapter and no conversion registry; fork traces confirm the allowlist at runtime; a monitor re-checks continuously; `extensionsHash` must be zero ([09 §7](09-capability-boundaries.md)). *A feature flag is not evidence of absence.* | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` | Pipeline report; call-graph report; fork trace; monitor test | RG-005 (tests), RG-010 (manifest) | Principal Architect |
| PB-041 | **Dual cap model and signed quote schema proven**: every cap and limit has exactly one class ([11 §2.1](11-dual-cap-model.md)); `PriceQuote` v1 (fifteen fields) validity predicate Q1…Q20, bounds intersection, round-up valuation and blast-radius property tests (B2, B4); the quote-signer key class is separated from executor and charge-signer keys and policy-tested | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` | CAP-TV and property-test reports; signer policy report; ceremony record | RG-005, RG-007 | Risk Lead |
| PB-042 | **Router lifecycle and lineage migration implemented** with invariants `I-MIG-1…11` proven (the exact predicates of [12 §5.3](12-router-lifecycle-and-migration.md), including the on-chain check that the old Permit2 allowance is zero or expired before `activateSuccessor`, containment of the migration snapshot and no overlapping authority) and immutable minimum-notice constants ([12](12-router-lifecycle-and-migration.md)) | `SECURITY-CRITICAL` | MIG-TV-01…18 on forks; audit coverage statement | RG-005 | Principal Architect |
| PB-043 | **Delegation inspection and records live**; delegate allowlist governed at E3; Permit2 behavior for code-bearing signers verified on forks and in the wallet lab (EV-P07); wording lint passes ([13](13-eip7702-delegation-inspection.md)) | `SECURITY-CRITICAL` | EV-P07, EV-P09; fork tests; lint output | RG-003 | Wallet Protocol Eng |
| PB-044 | **Pay Once and recurring protocols separated** in code, tests and audit scope: S-1…S-4, `I-PO-NOSTANDING`, `I-PO-WITNESS` ([10](10-pay-once-protocol.md)) | `SECURITY-CRITICAL` | Static reference check; invariant runs; audit scope statement | RG-005 | Solidity Lead |
| PB-045 | **v1.1 stablecoin-conversion enablement evidence**: adapter independently audited; `labApprovalId` per pair; bands and peg monitoring drilled; MEV review; conversion ledger journals reconciled; counsel answer on Q-03; staged rollout plan ([09 §6.1](09-capability-boundaries.md)) | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` `LEGAL-REVIEW-REQUIRED` | RG-013 packet | RG-013 | Head of Security |
| PB-046 | **v2.0 general-token conversion evidence**: separate audit incl. general class and oracle integration; per-token approvals; oracle bounds live; manipulation-resistance analysis; legal ([09 §6.2](09-capability-boundaries.md)) | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` `LEGAL-REVIEW-REQUIRED` | RG-014 packet | RG-014 | Head of Security |
| PB-047 | **Rollout-switch governance tested** (from v1.1; in v1.0 no conversion flag exists): two-person enabling, audit trail, fail-closed evaluation, flags only narrow what the chain allows and are never counted as a protection, kill-switch latency drilled | `SECURITY-CRITICAL` | Test report; RB-033 drill (v1.1) | RG-010 (service), RG-013 (conversion flags) | Head of Security |
| PB-048 | **Router migration readiness**: lifecycle rehearsed on testnet with lineage successors, mainnet canary drill, communications game day, anti-phishing controls, approved notice templates, counsel view on notice duties | `PRIVACY-CRITICAL` `SECURITY-CRITICAL` `LEGAL-REVIEW-REQUIRED` | Drill reports; counsel letter | RG-015 | Principal PM |
| PB-049 | **Account changes stop unattended charges (layer B of the Account Compatibility Policy)**: the orchestrator revalidates before quoting and again before signing; signer policy refuses an unattended charge without an ACP stamp younger than 60 seconds for the mandate's current pin; a difference in delegate address, delegate code hash, proxy implementation, ERC-1271 behavior or account code pauses the mandate as `DELEGATION_UNVERIFIED` (backend and on-chain bit); DRV-01…25 pass in both implementations; hostile and swappable delegates pass fork tests; the false-positive rate is measured in the alpha (RP-28) ([13 §7](13-eip7702-delegation-inspection.md)) | `SECURITY-CRITICAL` | DRV report; signer policy test; fork tests; alpha metrics | RG-003 (design, tests), RG-005 (contract pause bit), RG-006 (signer policy) | Wallet Protocol Eng |
| PB-050 | **Primary revocation flows verified for every listed token and chain**: token `approve(Permit2, 0)` (including approve-zero-first and no-return tokens), `Permit2.lockdown`, `Permit2.approve(token, router, 0, 0)`, `invalidateNonces`, and `MandateManager.revoke`/`revokeBySig`; the plan validator rejects any zero-amount `permit` step while `revocation.zeroPermit.enabled` is off; customer wording is accurate about cost and gas ([05 §2.1](05-evm-authorization-decision-tree.md)) | `SECURITY-CRITICAL` | EV-P11 per token and chain; validator tests; lab-wallet evidence (WL-19) | RG-004 | Contract Security Eng |
| PB-051 | **Signed quote schema frozen and reproduced**: `PriceQuote` v1 typed data, domain, signer sets and rotation, Q1…Q20, the non-override proof, canonical JSON and the test vector are reproduced by the contract, the backend and `tools/eip712_vectors.py`; fingerprints recorded at the protocol freeze ([14 §2](14-protocol-freeze-pack.md)) | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` | FZ-13 and FZ-42 evidence | RG-016, RG-005 | Principal Architect |
| PB-052 | **Account Compatibility Policy implemented and proven**: accounts are classified into the five modes by the predicates of [17 §2](17-account-compatibility-policy.md); the seven-field `AccountPin` is enforced in `consume` (account code hash and, in mode 2, delegate code hash: `I-ACCT-PIN`) and `updateAccountPin(s)` changes nothing but the pin hash and the version (`I-ACCT-NOWIDEN`, `I-ACCT-VERSION`); the permission matrix is enforced by the planner, orchestrator and signer policy; ACP-TV-01…44 pass; a wallet-managed upgrade after activation stops charges and offers re-verification | `SECURITY-CRITICAL` | ACP-TV report; fork tests (EV-P13); lab runs (WL-05, WL-11, WL-14) | RG-003 (policy, lab), RG-005 (contract) | Wallet Protocol Eng |
| PB-053 | **Pinned Permit2 source review complete at E2 and its fork tests pass**: commit SHA recorded; checklist PR-01…PR-16 answered with file, function and line ([16 §5](16-freeze-decision-report.md)); the rebuild comparison (CREATE2 address check) is recorded; the freeze subset of fork tests (RV-T01, 02, 04, 05, 07, 11 and MIG-TV-22/40) passes before RG-016 (status in 0.5: commit pinned, answers recorded from an automated read, E2 sign-off, rebuild and fork tests not done); the full RV-T01…RV-T12 and the ZP-T01…ZP-T08 results (the zero-amount permit stays disabled) before RG-002 | `SECURITY-CRITICAL` | EV-P12 review record; fork reports | RG-016, RG-002 | AA/Protocol Eng |

| PB-054 | **Shared-allowance migration proven**: `activateSuccessor` has the two modes and the exposure index of [12 §5.3](12-router-lifecycle-and-migration.md); O1N and O1E are exact; the index is never an under-count (`I-MIG-10`); activation writes nothing to Permit2 and touches no sibling (`I-MIG-11`); R-L2-SHARED and NC-20/NC-21 hold in both planners; MIG-TV-30…45 pass on a fork; the Foundry suites (fuzz, invariant, mutation, integer-width, timestamp-boundary, shared-allowance) compile and pass; gas of the index and of the emergency enumeration is measured (PC-18) | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` | Suite report; fork reports; gas report; planner NC results | RG-002 (suites, planners), RG-005 (contract) | Solidity Lead |
| PB-055 | **`AccountPin` and signature-capability binding proven**: the seven-field struct, `PIN_WELLFORMED`, `PIN_OK` with the delegate code hash, `pinVersion`, `AUTH` and the signature mode ([17 §5](17-account-compatibility-policy.md)); the wallet shows the nested struct or is classified `opaque` (WL-36); the capability record is bound to the pin and the eleven triggers revoke it (ACP-TV-38…44); the delegate-code-hash stability fact (UX-18) is closed | `SECURITY-CRITICAL` | ACP-TV report; WL-36…39 runs; fork tests | RG-003, RG-005 | Wallet Protocol Eng + Solidity Lead |
| PB-056 | **Signer-set emergency removal proven**: a removed key is rejected in every set version with no grace; a retired set honors only quotes issued before retirement for at most `QUOTE_SET_GRACE`; tombstones are permanent; the guardian can remove and stop but never add; a removal drill and a rotation drill pass with measured latency; SR-1…SR-7 hold in the suites ([11 §4.7](11-dual-cap-model.md)) | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` | CAP-TV-23…32 report; drill reports | RG-005, RG-010 | Head of Security |

Summary: 56 blockers, all `OPEN`. The ones that could still change the frozen protocol are listed in [14 §3](14-protocol-freeze-pack.md).

## 2. Release Gate Register (seed)

Sign-offs: **HoP** Head of Product, **VPE** VP Engineering, **CISO**, **HoC** Head of Compliance, **PA** Principal Architect, **QA**. `V` marks a unilateral veto.

| RG | Gate | Entry for | Criteria (all required) | Blockers | Sign-offs |
|---|---|---|---|---|---|
| RG-001 | Phase 0 exit: architecture validation | P1 | **RG-016 (protocol freeze) closed**; ADRs 001–019 approved or amended; OD-003/024/025/026/027/028/029 decided and OD-004/006/011/012 recorded; OD-001 decided or deferred with date; claims for Parts C/D at E2; Compatibility Register v0 incl. delegate capture; threat model v1 reviewed; two planner implementations pass all vectors (recurring, Pay Once, caps, delegation revalidation); specification set for contracts reviewed; audit slots contracted and the Router v1.1 scope priced separately (ASM-027); critical roles filled; name decision | PB-013, PB-032 (decision), PB-037 (subset), PB-038 (E2) | HoP, VPE, CISO, PA |
| RG-002 | Phase 1 exit: feature complete, audit freeze | P2 / R3 testnet alpha | All `I-*` invariants have passing tests; core flows work on forks and testnets; Permit2 assumptions confirmed from source (EV-P06) and the pinned-commit review and fork tests passed (PB-053); audit package accepted by both firms; code freeze at the planned audit-freeze week ([07 §3](07-delivery-plan.md)); `freeze_fingerprints.py --verify` and `sync_vectors.py --verify` pass | PB-005, PB-053 | VPE, CISO, PA |
| RG-003 | Wallet and capability evidence | R3 (minimum), R6 (full) | Compatibility Register rows at E3 for every claimed wallet ([15](15-wallet-lab-matrix.md)) including the account mode, pin behavior and delegate of each; delegate address, code hash, ERC-1271 behavior and revert path recorded for every upgrading wallet; `sig1271` gate proven on hostile-delegate fixtures; revalidation vectors DRV-01…25 and ACP-TV-01…44 pass; hostile-wallet fixtures pass; consent display reviewed for hardware path | PB-008, PB-009, PB-043, PB-049, PB-052 | QA, PA, CISO |
| RG-004 | Chain, token and finality evidence | R6 | Chain fact sheets; finality thresholds; quorum chaos tests; Permit2 verification and monitoring; token lab complete; **primary revocation flows verified per token**; drift watchers live | PB-004, PB-010, PB-011, PB-050 | PA, CISO, QA |
| RG-005 | Contract audit | R6 (mainnet funds) | Two audits complete covering Router v1 (**no conversion code; absence checks green**), registries, `PriceQuote` v1 quote verification, lineage migration (`activateSuccessor` and the old-permission check) and the Pay Once / recurring separation; all critical/high fixed and re-reviewed; invariants and formal targets met; final reports archived; scope statement as in [14 §5](14-protocol-freeze-pack.md) | PB-002, PB-003, PB-040, PB-041, PB-042, PB-044, PB-049 (contract bit), PB-051 | **CISO (V)**, PA |
| RG-006 | Security testing and key management | R6 | Pen test and red team clear; key ceremonies done; signer policy proven (including the revalidation stamp and quote-signer separation); frontend integrity controls live; supply-chain gate enforced; contracts verified on explorers; tenant isolation and webhook controls proven | PB-001 (process), PB-006, PB-007, PB-012, PB-019–PB-024, PB-049 (signer policy) | **CISO (V)**, VPE |
| RG-007 | Financial controls | R6 | No-double-charge proven; ledger and reconciliation proven on testnet for 14 consecutive days; refund model implemented; unit economics non-negative | PB-014, PB-015 (testnet portion), PB-016, PB-017 | VPE, HoP |
| RG-008 | Legal, compliance and privacy | R6 | Counsel letters per jurisdiction; licence/partner path; KYB and sanctions operational; consent copy and disclosures approved; DPIA; terms; accessibility audit | PB-027–PB-031, PB-036, PB-037 (OD-001) | **HoC (V)**, HoP |
| RG-009 | Operational readiness | R6 | Observability, detections, on-call, status page, support playbooks; IR and DR exercises passed; load and chaos tests passed | PB-025, PB-033–PB-035 | VPE, CISO |
| RG-010 | **Private mainnet beta go** | R6 | RG-003, 004, 005, 006, 007, 008, 009 closed for the beta scope; limits and circuit breakers live; mainnet deployment verified **with the absence proof in the signed manifest**; rollout-switch service live and fail-closed; private bounty live; E0 facts absent from shipped behavior | PB-001, PB-018, PB-026 (private), PB-032 (use), PB-039, PB-040, PB-047 (service) | HoP, VPE, CISO, HoC |
| RG-011 | **Public beta go** | R7 | 4 consecutive weeks of 100% reconciliation; no Sev-1 in the period; beta feedback triaged; public bounty and contest or extended review complete; additional chains pass RG-003/004; T1 surfaces pass security review | PB-015 (mainnet), PB-026 (public) | HoP, VPE, CISO, HoC |
| RG-012 | **General availability go (v1.0)** | R8 | Every GA prerequisite from prompt §25 has evidence: independently audited contracts; critical and high resolved; capability and legacy paths tested; token registry controls; idempotency and reconciliation; signed webhooks; ledger; monitoring and alerts; key management; DR exercise; IR exercise; support readiness; legal and privacy reviews; status page; bug bounty; **RG-015 readiness evidence current; the absence proof is current (conversion arrives only as Router v1.1 through RG-013, by opt-in)** | all PB except PB-045, PB-046 | HoP, VPE, CISO, HoC |
| RG-013 | **v1.1 stablecoin conversion enablement** (per chain, pair and stage) | P6 | Router v1.1 and `ConversionPolicyRegistry` independently audited as a new router version (full review, not a diff) with no open critical/high; adapter independently audited; `labApprovalHash` for each pair; bounds and peg monitoring drilled; MEV and price-impact limits validated on forks; conversion journals reconciled for 14 days; counsel answer on Q-03 for the jurisdictions in use; opt-in migration rehearsed (RG-015); **C1 (customer router-specific authorization) and C2 (on-chain conversion policy) verified; the rollout switch R enabled by two approvers per stage and never counted as a protection**; kill switch drilled (RB-033) | PB-045, PB-047 (conversion flags) | **CISO (V)**, **HoC (V, legal items)**, HoP, VPE |
| RG-014 | **v2.0 general-token conversion enablement** (per token) | P7 | All RG-013 items for the general class plus: separate audit of the general route class and oracle integration; per-token approval with manipulation-resistance analysis and observation period; oracle-referenced bounds live and monitored; updated bounty scope | PB-046 | **CISO (V)**, **HoC (V)**, HoP, VPE |
| RG-015 | **Router migration readiness** (before any router deprecation, and again before Router v2) | P3 (first), P7 (v2) | Lifecycle rehearsed on testnet; mainnet canary drill passed; communications game day passed; zero stranded mandates in rehearsal; notice templates approved by counsel; anti-phishing controls and verification page live; `MIN_NOTICE` constants confirmed on chain; migration dry-run report for the live router; Head of Product and CISO risk acceptance for the unmigrated share | PB-006, PB-042, PB-048 | HoP, CISO, **HoC (notice duties, V)**, PA |
| RG-016 | **Protocol freeze** | P1 contract build | Every item of the checklist in [14 §1](14-protocol-freeze-pack.md) closed with evidence; **the freeze-decision report ([16](16-freeze-decision-report.md)) shows no open freeze-blocking decision, no unverified external fact marked freeze-blocking, every production-blocking constant approved as its own record ([18](18-configuration-records.md)), the required wallet-lab evidence (EVL) and the pinned Permit2 source review (PR, E2, rebuild, fork subset) complete, the shared-allowance migration and the account-pin semantics reviewed, and the Foundry suites passing — computed by `tools/freeze_readiness.py`, which must report READY**; fingerprints of [14 §2](14-protocol-freeze-pack.md) recorded; Freeze Change Request process in force | PB-005, PB-053, PB-037 (subset), PB-038 (E2 for frozen sections), PB-051, PB-052, PB-054, PB-055, PB-056 | PA (A), **CISO (V)**, VPE, QA |

Gate mechanics:

1. A gate review is a meeting plus a written packet: criteria, evidence ids, open exceptions with owner and date.
2. Exceptions are allowed only for items not marked `PRODUCTION-BLOCKER`, and need a named risk owner and expiry.
3. A veto holder's `no` stands until they withdraw it in writing.
4. Gate outcomes are recorded in this register with date and attendees; the register is append-only.

## 3. Everything that requires external verification

Nothing in this workspace has been audited, legally reviewed, tested on a wallet, or tested on a chain. The following must come from outside the document-writing process.

| Category | Needs | Why it cannot be generated | Items |
|---|---|---|---|
| **Smart-contract audit** | Two independent firms; possibly a public contest | Independent assurance is the control | PB-002, PB-003; RG-005 |
| **Penetration testing and red team** | External testers for app, API, cloud, signer, frontend | Independent attack simulation | PB-023; RG-006 |
| **Legal counsel** | Perimeter memo per jurisdiction; licensing; consent copy; terms; privacy; trademark; sanctions/Travel Rule applicability | Only qualified counsel can conclude (Q-01…Q-20) | PB-027–PB-032; RG-008 |
| **Wallet testing** | Hands-on matrix across wallets, versions, platforms, account types, chains; hardware paths | Vendor documents are not behavior (CLM-040/041); this pass found Trust Wallet undocumented | PB-008, PB-009; RP-05/06/21 |
| **Chain testing** | Permit2 bytecode by chain; finality and reorg data; EVM version; RPC behavior; gas measurements | Documents list addresses, not bytecode or behavior (CLM-022) | PB-004, PB-010; RP-03/04/19/22 |
| **Token testing** | Behavior lab on forks and testnets | Token behavior is code, not metadata | PB-011; RP-07 |
| **Source review by a human** | E1 → E2 for all load-bearing claims | The retrieval tool summarizes; it is not a verifier (G-03) | PB-038; RP-01/02 |
| **Cloud and HSM verification** | Key support, validation levels, regional availability, pricing | Not examined in this pass | RP-15; OD-015 |
| **Vendor due diligence** | KYB/AML/sanctions, RPC, audit firms, bounty platform | Not examined in this pass | RP-11/16/17 |
| **Wallet delegates and ERC-1271 behavior** | Per-wallet delegate address, code hash, `isValidSignature` behavior with real Permit2 signatures, persistence statement observed, revert path walked, behavior under delegate swaps | MetaMask's docs name no delegate and do not state persistence (CLM-043); Permit2 rejects signers with code unless ERC-1271 succeeds (CLM-050) | PB-043, PB-049; RP-25, RP-28; EV-P07/P09; [15](15-wallet-lab-matrix.md) |
| **Account modes per wallet** | For each target wallet and account mode: the mode produced, the pin value, the delegate or proxy, the upgrade behavior and whether the post-upgrade delegate can be named in advance | Wallet behavior is code that vendors change; documentation names no delegate (CLM-043) | PB-052; RP-29; EV-P13; [16 §9](16-freeze-decision-report.md) |
| **Router v1.1 and adapter audit, and legal view (v1.1)** | Independent audits of the conversion-capable router version and the adapter; counsel answer on whether routing a swap is an exchange service (Q-03) | Independent assurance and legal conclusions | PB-045; RG-013 |
| **Router migration notice duties** | Counsel view on notice obligations; comprehension tests of the consent | Legal and human-subject evidence | PB-048; RP-26 |
| **Revocation flows per token and wallet** | Fork and lab evidence that the primary revocation flows work for every listed token and wallet; whether the experimental zero-amount `permit` ever works | Token and wallet behavior is code | PB-050; RP-27; EV-P08, EV-P11 |
| **Usability and accessibility testing** | Participants, independent WCAG audit, native-language reviewers | Requires people | PB-036; EPIC-P0-DESIGN |
| **Merchant discovery** | 20 interviews | Primary research | RP-24 |
| **Financial and tax review** | Revenue recognition, VAT/sales-tax on crypto receipts, reserve policy | Requires accountants | Q-13; F.3 |


## 4. Facts verified, and their limits

**Verified by fetching the page (E1)** — first pass: EIP-5792 Final; EIP-7702 Final; Permit2's canonical address and its same-address statement with a zkSync exception; Permit2 listed at the canonical address for Ethereum, Optimism, Base, Arbitrum One, Polygon, Avalanche and BNB Smart Chain on Uniswap's v4 deployments page; the `IAllowanceTransfer` interface at the branch tip; ERC-2612 and ERC-1271 Final; ERC-3009 and ERC-7715 Draft; an incomplete third-party wallet list for EIP-5792.

**Verified by fetching the page (E1)** — revision 0.2:

- MetaMask's official docs (two pages): EIP-5792 batching with `atomic` `supported`/`ready` per account and chain, wallet-driven upgrade to a MetaMask smart account, atomic-only `wallet_sendCalls`, chains named (Ethereum, Gnosis, BNB Smart Chain, OP, Base, Polygon, Arbitrum, Unichain, Berachain), **Avalanche not listed**, no atomic batching for accounts already upgraded to a third-party smart account. The docs name no delegate and do not state persistence. **This upgrades MetaMask from "unconfirmed" to "documented"; runtime detection is still mandatory and the lab verdict is `UNTESTED`.**
- EIP-7702: the delegation is persistent, overwritten by a later authorization, cleared by delegating to the zero address, and not rolled back if a transaction fails (CLM-016).
- Pectra activation on 7 May 2025 including EIP-7702 (CLM-015), from the Ethereum Foundation announcement.
- Permit2 source at the branch tip: signature verification uses `ecrecover` only for signers without code and ERC-1271 only for signers with code (CLM-050); `SignatureTransfer` hashes `msg.sender` as spender and the destination is not signed (CLM-051); `AllowanceTransfer` caller scoping, `uint160.max` as an unlimited sentinel, zero-amount revocation via `permit` (inferred), `lockdown`, `invalidateNonces` limits (CLM-052).

**Verified by fetching the page (E1)** — revision 0.3: the EIP-7702 opcode behavior of delegated accounts (`EXTCODESIZE` returns 23; `EXTCODEHASH` works on the designator without following the delegation; `tx.origin == msg.sender` is no longer a guarantee) (CLM-053). No other new source was retrieved; the corrections of 2026-10-13 are design decisions, not new facts.

**Still not verified:** Trust Wallet (no documentation found; status `UNKNOWN` pending the wallet lab); any wallet's actual behavior; any chain's actual bytecode or finality; every regulation; every cloud or vendor capability; Permit2 audit reports and the pinned-commit text (RP-02); expiration-of-zero semantics and the exact `permit` nonce update (G-09); any token.

**Not claimed anywhere:** that any wallet supports any capability; that Permit2 is present on any chain; that any delegate implements ERC-1271 correctly; that any design here is secure, compliant, or complete.
