# 09 — Capability Boundaries: v1.0, v1.1, v2.0

| Field | Value |
|---|---|
| Artifact | FP-PRD-003 |
| Version | 0.4.0 (0.3: rewritten, conversion code **absent** from Router v1; 0.4: conversion adoption path clarified — a new manager and mandate, never `activateSuccessor`) |
| Status | DRAFT — boundaries decided by sponsor directive (2026-10-13) and corrections of the same date; enablement criteria are proposals |
| Owner | Head of Product (scope), Principal Blockchain Architect (boundaries) |
| Reviewers | Head of Security, Head of Compliance, VP Eng, QA Lead |
| Dependencies | [03](03-assumptions-decisions-risks.md) OD-009, OD-012, OD-024, OD-025; [06](06-initial-architecture.md) ADR-013; [11](11-dual-cap-model.md); [12](12-router-lifecycle-and-migration.md) |
| Definition of Done | Every capability has an exact status in each version; every `FLAG` capability names its rollout switch **and** its security conditions; every `ABSENT` capability has a mechanical absence check in the release pipeline; the document states which controls are security boundaries and which are only rollout controls. |

## 0. Decision: swap execution code is **absent** from Router v1

**Question (correction 1, 2026-10-13):** is swap execution code absent from Router v1, or fully included in the v1 audit scope? *A feature flag is not a security boundary.*

**Decision: absent.** Router v1, `MandateManager`, `RouterRegistry`, `TokenPolicyRegistry` and every other v1.0 contract contain **no swap or conversion execution code, no adapter interface call, no adapter or conversion registry, and no conversion state**. Conversion arrives as **Router v1.1** (a new, separately audited router version) together with a new `ConversionPolicyRegistry` and the first stable-pair adapter, and customers adopt it by **opt-in** through the lineage mechanism of [12](12-router-lifecycle-and-migration.md).

| Criterion | A — code absent from Router v1 (**chosen**) | B — fully included in the v1 audit scope |
|---|---|---|
| Attack surface at launch | Smallest: no path from the router to any DEX, adapter or arbitrary target | Larger: conversion entrypoints, adapter interface and registry audited and live on chain |
| What is the boundary? | **Code presence** per router version, plus the customer's router-specific authorization | Registry state and a flag over code that exists; if the gating logic has a bug the code is reachable |
| v1.0 audit scope | Sharper and smaller | Larger; premium unpriced (ASM-027 v0.2) |
| Customer consent | A customer who authorized Router v1 never gains swap exposure; conversion needs a new, explicit router-specific authorization | Enabling conversion changes what the already-authorized router can do |
| Cost of enabling conversion later | A second router audit and an opt-in lineage migration (built anyway, [12](12-router-lifecycle-and-migration.md)) | Registry changes only |
| Legal posture at launch | No conversion offered: Q-03 (is routing a swap an exchange service) is not on the v1.0 critical path | Q-03 must be answered before the code is audited and deployed |
| Failure if wrong | Conversion takes a router migration to add | A latent defect in audited-but-unused code |

**What stays "designed from the beginning" (the earlier directive):** boundaries are specified and, where cheap and inert, reserved — but nothing executable is deployed.

| Boundary element | v1.0 status |
|---|---|
| `ConversionRoute`, adapter interface, route classes, `PriceQuote` v2, conversion ledger journals, planner policy slots, enablement criteria | **Specified** (documents 05, 09, 11), **not implemented in contracts** |
| `Mandate.extensionsHash` (a `bytes32`, data only) | **Present and required to be zero** by the v1.0 `MandateManager`. A conversion consent would have to be carried here, so **a v1.0 mandate can never authorize conversion**; a later *manager* version may define what the field commits to. It carries no behavior in v1 |
| Router and quote domains | Router-specific (`verifyingContract` = router), so a v1.1 quote or witness can never validate on v1 |
| Planner: `router.capabilities.conversion` | Input is `false` for Router v1; every `SWAP_ONLY` token is dropped with `ROUTER_LACKS_CONVERSION` |
| Lineage and migration | **Implemented** in v1 ([12](12-router-lifecycle-and-migration.md)): the mechanism for moving to a new router **without widening anything** (Lemma M, 12 §5.3.3). Conversion adoption is not a migration in this sense: it is a **new `MandateManager` and a new mandate** with remaining-headroom caps and the customer's fresh conversion consent ([12 §5.7](12-router-lifecycle-and-migration.md)) |

## 1. Vocabulary

| Status | Meaning | Reachable by a customer or merchant? |
|---|---|---|
| **ON** | Built, deployed, enabled by default for the listed scope | Yes |
| **FLAG** | Built, deployed and audited code whose use is additionally controlled by a **rollout switch** (operational control only) | Only where the code's own security conditions and the switch are satisfied |
| **ABSENT** | Not present in the contracts or services of that version. It may be specified. A mechanical check proves absence | No |
| **SPEC-ONLY** | Designed and documented; no code | No |

## 2. Capability matrix

### 2.1 Authorization and wallets

| Capability | v1.0 | v1.1 | v2.0 | Notes |
|---|---|---|---|---|
| Pay Once via Permit2 `SignatureTransfer` with witness ([10](10-pay-once-protocol.md)) | ON | ON | ON | No standing allowance, no mandate |
| Pay Once alternates: atomic exact approval; ERC-2612 permit; direct transactions | ON | ON | ON | PO-2, PO-3, PO-5, PO-6 |
| Pay Once via ERC-3009 (Draft standard, CF-005) | FLAG | FLAG | FLAG | Rollout switch `signing.erc3009.enabled`; per-token verification |
| FastPay recurring: Permit2 `AllowanceTransfer` + scoped mandate ([05](05-evm-authorization-decision-tree.md)) | ON | ON | ON | Never uses `SignatureTransfer` |
| Activation paths A–D; capability discovery | ON | ON | ON | Runtime detection always required |
| Wallet-managed EIP-7702 upgrade, with inspection and recording ([13](13-eip7702-delegation-inspection.md)) | ON | ON | ON | Delegation is persistent state |
| **Delegation revalidation before every unattended charge**; `DELEGATION_UNVERIFIED` pause | ON | ON | ON | [13 §7](13-eip7702-delegation-inspection.md) |
| Signature flows for code-bearing accounts | FLAG | FLAG | ON per verified delegate | Permit2 needs ERC-1271 for signers with code (CLM-050) |
| Mandate lineage; successor activation; router lifecycle | ON | ON | ON | [12](12-router-lifecycle-and-migration.md) |
| Zero-amount signed `permit` as an old-permission revocation | **EXPERIMENTAL** (flag off) | EXPERIMENTAL | per EV-P08 | Primary flows are transactions ([05 §2.1](05-evm-authorization-decision-tree.md)) |
| FastPay's own EIP-7702 delegate | ABSENT | ABSENT | ABSENT | OD-011 |
| Smart-account permission adapters (ERC-7715 Draft, spend-permission modules) | ABSENT | evaluate (OD-010) | optional | CF-005 |

### 2.2 Settlement and conversion

| Capability | v1.0 | v1.1 | v2.0 | Notes |
|---|---|---|---|---|
| Direct settlement in the merchant's accepted stablecoin set (`amountIn == amountOut`) | **ON** | ON | ON | MVP settlement path |
| Token fallback across the accepted set (new attempt, pre-submission failures only) | ON | ON | ON | |
| Conversion execution code (swap, adapter calls, adapter registry, route classes, conversion entrypoints) | **ABSENT** | **Router v1.1 + `ConversionPolicyRegistry`** | in Router v1.1/v2 | Mechanical absence check at v1.0 (PB-040) |
| Stablecoin conversion (route class `STABLE`) | ABSENT | FLAG (rollout switch + conditions C1, C2) | ON for approved pairs | Needs RG-013 |
| General-token conversion (route class `GENERAL`) | ABSENT | ABSENT (not built) | FLAG per token after separate audit and token-lab approval | Needs RG-014 |
| Native-asset payments (wrap + general conversion) | ABSENT | ABSENT | FLAG | OD-009; recurring native pulls never |
| Cross-chain settlement / bridging | ABSENT | ABSENT | ABSENT | `NON-GOAL` |

### 2.3 Caps and quotes ([11](11-dual-cap-model.md))

| Capability | v1.0 | v1.1 | v2.0 |
|---|---|---|---|
| `ONCHAIN_HARD` caps (per-token atomic units, cadence, fee, time) | ON | ON | ON |
| `QUOTE_BOUND_ONCHAIN` fiat caps with `PriceQuote` v1 and static price bounds (stablecoins) | ON | ON | ON |
| `PriceQuote` v2 for conversion (route-bound), pair bands | ABSENT | ON with Router v1.1 | ON |
| Oracle-referenced bounds for volatile tokens | ABSENT | ABSENT | FLAG (new verifier version, OD-027) |
| `BACKEND_ONLY` risk controls | ON | ON | ON |

### 2.4 Billing, lifecycle, surfaces

| Capability | v1.0 | v1.1 | v2.0 |
|---|---|---|---|
| Fixed subscriptions (S07) | ON | ON | ON |
| Variable subscriptions (S08), repeat purchase (S06) | ABSENT | ON | ON |
| Usage billing (S09), auto top-up (S10) | ABSENT | ABSENT | ON |
| Marketplace splits (S11) — requires Router v2 | ABSENT | ABSENT | ON after migration |
| Surfaces | 18: S01 S02 S03 S04 S05 S07 S12 S13 S14 S15 S16 S17 S18 S19 S20 S21 S22 S23 | + S06 S08 | + S09 S10 S11 S24 S25 |

### 2.5 Chains, wallets, tokens (recommendations; each enablement needs its own evidence, OD-008)

| Dimension | v1.0 | v1.1 | v2.0 |
|---|---|---|---|
| Testnets | Sepolia, Base Sepolia, Arbitrum Sepolia | + as needed | |
| Mainnet chains | R6: Base, Arbitrum One. R7/GA: + Optimism, Polygon | + Ethereum L1, BNB Smart Chain | + Avalanche and other EVM chains |
| Caveats | MetaMask's docs list Base, Arbitrum, OP, Polygon, Ethereum, BNB (CLM-040, documentation only) | BNB moves earlier if the target market is Trust Wallet-heavy (`UNKNOWN`) | MetaMask's docs do not list Avalanche; non-batching paths unless lab evidence says otherwise |
| Wallets | Rows with E3 evidence ([15](15-wallet-lab-matrix.md)); **Trust Wallet `UNKNOWN`** | | |
| Tokens | R6: 2 stablecoins per chain; GA: ≤4; status `SETTLEMENT` / `DIRECT_PAYMENT` only | + `SWAP_ONLY`, class `STABLE`, approved pairs | + class `GENERAL` per approved token |

## 3. What changes how

| Change | Mechanism | Customer action? |
|---|---|---|
| Add or remove a settlement token | `TokenPolicyRegistry` (timelocked add; guardian block) | None |
| Change fee within the immutable ceiling; rotate executors, charge signers, quote signers | Registries | None |
| **Add conversion** (stable pairs) | **New router version** (Router v1.1) + `ConversionPolicyRegistry` + adapter + a **v1.1 `MandateManager`** that accepts the conversion consent, each audited ([12](12-router-lifecycle-and-migration.md)) | **Opt-in**: a new mandate in the new manager with the customer's router-specific and conversion-specific authorization, caps equal to the old mandate's remaining headroom, and the old mandate and old router permission revoked. Customers who do nothing stay on Router v1 with direct settlement |
| Add general-token conversion, oracle bounds, split settlement | Router v1.1 route class or Router v2, separate audit | Opt-in successor mandate |
| Change router logic or fix a router bug | New router version; deprecate the old per lifecycle | Successor mandate required before sunset |
| Change `MandateManager` logic | New manager; new mandates with remaining-headroom caps ([12 §5.7](12-router-lifecycle-and-migration.md)) | Fresh authorization and revocation of the old mandate |
| Mandate terms (price, cadence, caps up) | Mandate revision = successor on the same router | Fresh consent |

Consequence of decision 0: enabling conversion is **not** a configuration change. It is a release with an audit, an opt-in campaign and RG-013.

## 4. Conversion: security conditions and rollout switch

Conversion may execute for a payment only if **all** of these hold. They are listed by what they are:

| Item | Kind | What it is |
|---|---|---|
| **C1 Router capability and consent** | **Security boundary** | The payer's active mandate is bound to a router version that contains conversion code (v1.1+). The mandate carries the customer's router-specific authorization (successor or new mandate) |
| **C2 On-chain conversion policy** | **Security boundary** | In `ConversionPolicyRegistry`: the route class is open, an adapter with the audited code hash is registered, the token pair is approved with a non-zero `labApprovalHash`; timelocked to enable; guardian can close a class or disable an adapter at once |
| **Hard caps** | **Security boundary** | `ONCHAIN_HARD` caps and `QUOTE_BOUND_ONCHAIN` limits apply to conversion inputs ([11](11-dual-cap-model.md)); realized output versus the signed quote |
| **R Rollout switch** | **Operational control only** | A backend flag per chain × merchant × pair, two-person enabling, one-person disabling, kill switch. It can only **narrow** what C1 and C2 permit |

Rules:

1. A closed R never grants anything; an open R grants nothing without C1 and C2. **R is never counted as a protection** in a threat model or an audit scope.
2. In a v1.0 deployment C1 cannot hold for anyone: no router contains the code. R and C2 do not exist to be misconfigured.
3. Disabling is fast: close R (seconds), then C2 via the guardian if on-chain risk is suspected. Runbook RB-033.
4. The planner evaluates C1, C2 and R at plan time and again at execution time; a change in any of them blocks new attempts and lets in-flight attempts reconcile.

## 5. Rollout switches and experimental flags

Flags are **operational controls**. None of them is a security boundary (§4, correction 1).

| Flag | Scope | Default | Purpose | Notes |
|---|---|---|---|---|
| `conversion.rollout.stable` | chain × merchant × pair | off | Staged rollout and kill switch for stable conversion (v1.1) | Needs C1, C2, RG-013 |
| `conversion.rollout.general` | chain × token | off | Same for general conversion (v2.0) | Needs RG-014 |
| `signing.erc3009.enabled` | chain × token | off | Draft-standard adapter (CF-005) | Per-token verification |
| `activation.relayedSignatures.enabled` | wallet × version × account class | per Compatibility Register | Signature transports | Auto-off on `ATOMIC_VIOLATING` or signature-incompatible delegates |
| `activation.walletUpgrade.allowed` | wallet × version | per Compatibility Register | Whether the planner may use `ATOMIC_READY` | |
| `revocation.zeroPermit.enabled` | chain × token × wallet | **off** | **EXPERIMENTAL**: zero-amount signed `permit` as an old-permission revocation | Needs EV-P08 evidence; never the primary flow |
| `router.<n>.newMandates.enabled` | chain | per lifecycle | Backend gate on creating mandates on a router version | Registry lifecycle is the boundary |
| `merchant.<id>.paused` | merchant | false | Risk kill switch (stop-only) | |

Governance: changes only through the flag service; two-person enabling, one-person disabling; audited, evented, visible in the Incident Console; every flag has an owner, an expiry review date and a rollback.

## 6. Enablement criteria

### 6.1 v1.1 — stable conversion (RG-013)

1. **Router v1.1** (conversion-capable) and `ConversionPolicyRegistry` are independently audited as a **new router version** (full review of changed and new paths, not only a diff of v1), with no open critical or high findings.
2. The **stable adapter** is independently audited.
3. **Token-lab approval** per pair (12 behavior classes, issuer-power review, depeg history, liquidity depth at the maximum trade size, price-impact results) producing `labApprovalHash`.
4. Pair price bands, peg monitoring, `PriceQuote` v2 and depeg drills (RB-016).
5. MEV and price-impact limits validated on forks with adversarial ordering; private-submission decision.
6. Conversion ledger journals reconciled on testnet for 14 consecutive days.
7. Counsel's answer on Q-03 for the jurisdictions in use.
8. Router v1.1 and the v1.1 manager registered through the lifecycle; the **opt-in adoption** (new mandate, old mandate and permission revoked, previous-manager cycle lookup) rehearsed (RG-015); communications approved.
9. Staged rollout: internal → one design-partner merchant → cohort → general availability; each stage with exit metrics and rollback; R and C2 closable in a drill (RB-033).

### 6.2 v2.0 — general-token conversion (RG-014), per token

All of 6.1 for the general class plus: a separate audit of the general route class and oracle verifier; per-token approval with manipulation-resistance analysis and an observation period; oracle-referenced bounds live and monitored; updated bounty scope.

## 7. Mechanical absence and presence checks

| Check | Version | Method |
|---|---|---|
| **No conversion code in v1.0 bytecode** | v1.0 | Release pipeline: (a) ABI of every deployed v1.0 contract contains none of the conversion selectors; (b) static call-graph analysis shows **no external call targets beyond the allowlist**: Permit2, registry-listed tokens, `MandateManager`, `RouterRegistry`, and the fixed registries; (c) no `DEXAdapterRegistry`, `ConversionPolicyRegistry` or adapter appears in the deployment manifest; (d) `Mandate.extensionsHash` must be zero or the call reverts |
| External-call allowlist holds at runtime | v1.0 | Fork trace test of every entrypoint: all `CALL`/`STATICCALL` targets are in the allowlist |
| Router-specific domains | v1.0 | A v1.1-style signed quote or witness fails on Router v1 |
| Planner drops every `SWAP_ONLY` token on Router v1 | v1.0 | TV-12, TV-21 |
| Direct settlement independent of any conversion state | v1.0–v2.0 | Regression suite across combinations of C1, C2, R |
| C1, C2 and R each closed alone block conversion | v1.1 | Three tests per conversion entrypoint |
| Kill-switch latency | v1.1 | Drill: R closed within 60 seconds; C2 closed by the guardian; in-flight attempts reconcile |

## 8. Impact on the plan and the register

- Scope, estimates and schedule: [07](07-delivery-plan.md).
- Decisions: OD-012 (decided, refined by correction 1), OD-025 (conversion governance), OD-027 (quote and bounds design).
- Risks: RISK-024 now concerns the **cost and timing of Router v1.1**, not dormant code; RISK-028 (premature enablement) is reduced because the code does not exist before v1.1.
- Blockers and gates: PB-040 (absence proof), PB-045, PB-046, PB-047; RG-013, RG-014.
