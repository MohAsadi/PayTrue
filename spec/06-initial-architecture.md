# 06 — Initial Product and Technical Architecture

| Field | Value |
|---|---|
| Artifact | FP-PRD-002 / FP-BE-001 / FP-SC-001 (outline level) |
| Version | 0.5.0 |
| Status | DRAFT — proposals pending the decisions in [03](03-assumptions-decisions-risks.md); **not frozen** |
| Owner | Principal Blockchain Architect (protocol), Principal Backend Architect (platform), Head of Product (surfaces) |
| Reviewers | Head of Security, SRE Lead, Head of Compliance, VP Eng |
| Dependencies | [04](04-context-and-trust-boundaries.md), [05](05-evm-authorization-decision-tree.md), [09](09-capability-boundaries.md)–[17](17-account-compatibility-policy.md), OD-003/007/008/015/024/025/026/027/028 |
| Definition of Done | Each component has a responsibility, owner, trust zone, and the ADR that fixed its shape; every invariant has a test type; no component exists without a requirement ancestor; every `ABSENT` capability has a mechanical absence check. |

## 0. Changes since v0.1

| Change | Where |
|---|---|
| **Conversion execution code is ABSENT from Router v1** (correction 1: a flag is not a security boundary); not permanently swap-free — conversion arrives as Router v1.1 by opt-in, with its own audit | §2.2, §4, ADR-013, [09](09-capability-boundaries.md) |
| Migration is **mandate lineage**: a successor mandate with a router-specific authorization, shared counters, and an on-chain check that the old Permit2 permission is unusable | §3.3, §4, ADR-015, [12](12-router-lifecycle-and-migration.md) |
| Delegation revalidated before **every unattended charge**; new pause state `DELEGATION_UNVERIFIED` | §3.3, ADR-018, [13 §7](13-eip7702-delegation-inspection.md) |
| Quote schema formalized; every cap classified as `ONCHAIN_HARD`, `QUOTE_BOUND_ONCHAIN` or `BACKEND_ONLY` | ADR-016, [11](11-dual-cap-model.md) |
| Revocation: transactions are primary; zero-amount signed `permit` is experimental | ADR-019, [05 §2.1](05-evm-authorization-decision-tree.md) |
| Backlog uses **epic profiles**, not one universal story rule | [07 §6.2](07-delivery-plan.md) |
| **v0.4:** Account Compatibility Policy with an **on-chain account pin** replaces backend-only revalidation (OD-029 reversed) | §4, ADR-018, [17](17-account-compatibility-policy.md) |
| **v0.4:** `activateSuccessor` has exact predicates, an on-chain migration snapshot and a containment proof; identifiers are router-independent | §4, ADR-015, [12 §5.3](12-router-lifecycle-and-migration.md), [11 §3.1](11-dual-cap-model.md) |
| **v0.4:** `PriceQuote` v1 has fifteen fields, versioned signer sets, rotation rules and a non-override proof | §4, ADR-016, [11 §4](11-dual-cap-model.md) |
| **v0.5:** the old Permit2 allowance is **shared** by a customer's mandates on a router and token; `activateSuccessor` has normal and emergency modes and an on-chain exposure index (O1 split into O1N/O1E) | §4, ADR-015, [12 §5.3.1](12-router-lifecycle-and-migration.md) |
| **v0.5:** `AccountPin` is a seven-field typed struct; the contract also checks the delegate's code hash; ERC-1271 evidence is bound to the pin and revoked by eleven triggers | §4, ADR-018, [17 §5](17-account-compatibility-policy.md) |
| **v0.5:** signer-set emergency removal has no grace and permanent tombstones; planned rotation honors only earlier quotes for a bounded period | §4, ADR-016, [11 §4.7](11-dual-cap-model.md) |
| Surface tiers replaced by version boundaries v1.0 / v1.1 / v2.0 | §2.1 |
| Pay Once (`SignatureTransfer`) and FastPay recurring (`AllowanceTransfer` + mandate) are separate protocols | §4, ADR-014, [10](10-pay-once-protocol.md) |
| Router lifecycle, `RouterRegistry`, migration protocol | §4, ADR-001/015, [12](12-router-lifecycle-and-migration.md) |
| Dual cap model with signed expiring quotes and bounded price inputs | §4, ADR-004/016, [11](11-dual-cap-model.md) |
| EIP-7702 delegation inspection and records; `sig1271` gate | ADR-007/017, [13](13-eip7702-delegation-inspection.md) |
| Four isolated deployables (adds `quote-signer`); feature-flag service | §5 |

## 1. Architectural stance

1. **Chain is the enforcement point; the platform is the convenience layer** (TM-02). The platform can go down and customers remain safe and in control (TM-14).
2. **Smallest fund-moving code.** One immutable router with typed entry points; no generic call; no admin sweep (CF-006); **no swap or conversion execution code at all in Router v1** — a feature flag is not a security boundary, so what is not needed at launch is not deployed (ADR-013). Extension points are *specified* and, where inert, reserved as data (`extensionsHash`), never as dormant code.
3. **Two customer protocols, not one with options**: Pay Once leaves nothing behind; FastPay recurring leaves a bounded, visible, revocable mandate (ADR-014).
4. **Capability-driven authorization** (ADR-007, [05](05-evm-authorization-decision-tree.md)). Every claim about what a wallet can do is a dated, evidenced register row, and the delegate behind an upgraded account is inspected and recorded.
5. **Modular monolith until a boundary earns its deployment** (ADR-005). Four components are isolated from day one because their failure and secret profiles differ: chain gateway, signer, quote signer, webhook dispatcher.
6. **Money is integers.** Atomic units in contracts and database; decimal strings in JSON; fiat in minor units (ADR-011).
7. **Idempotency everywhere.** API calls, payments, cycles, ledger postings, webhook deliveries, migration steps.
8. **Change is a first-class concern.** Immutable contracts only work if replacement is designed: router lifecycle and migration are part of the base design (ADR-015).

## 2. Product architecture

### 2.1 Surfaces by version (OD-024; replaces the MVP/T1/T2 tiers of v0.1)

"MVP" below means the 14 surfaces required for private mainnet beta (R6). **v1.0** is the GA scope: the MVP plus four surfaces that ship by public beta.

| Surface | Version | Why |
|---|---|---|
| S01 Hosted Checkout | v1.0 (MVP) | First user-visible product; smallest trust surface |
| S04 Pay Once | v1.0 (MVP) | Tests the wallet matrix without standing authority |
| S05 FastPay Activation | v1.0 (MVP) | The differentiator; planner + mandate |
| S07 Fixed Subscriptions | v1.0 (MVP) | Fixed amount, fixed cadence |
| S12 Merchant Settlement | v1.0 (MVP) | Direct to registered recipient on chain |
| S14 Customer Receipts | v1.0 (MVP) | Consent evidence and support load reducer |
| S15 Merchant Webhooks | v1.0 (MVP) | Signed events are required to integrate |
| S16 Merchant Dashboard (basic) | v1.0 (MVP) | Payments, mandates, keys, webhook logs |
| S17 Customer Mandate Portal | v1.0 (MVP) | "Visible, bounded, revocable" lives here; migration prompts live here |
| S18 Developer Portal (basic) | v1.0 (MVP) | Docs, keys, sandbox |
| S19 Admin Console (basic) | v1.0 (MVP) | Merchant approval, support lookups; no fund powers (TB-14) |
| S20 Risk Console (basic) | v1.0 (MVP) | Pause, review queues, alerts, limits |
| S21 Token Registry Console | v1.0 (MVP) | Listing and conversion approvals are security controls |
| S22 Incident Console (basic) | v1.0 (MVP) | Status, kill switches, flag changes |
| S13 Refunds | v1.0 (merchant-push in beta; full by GA) | Consumer remedy (OD-018) |
| S02 Embedded Checkout | v1.0 (by public beta) | iframe/postMessage hardening after hosted |
| S03 Payment Links | v1.0 (by public beta) | Thin layer over hosted checkout |
| S23 Reporting and Exports | v1.0 (by public beta) | Basic export in dashboard from MVP |
| S06 One-Click Repeat Purchase | **v1.1** | Mandate with merchant scope and per-purchase caps |
| S08 Variable Subscriptions | **v1.1** | Price-change consent and variance rules |
| S09 Usage-Based Billing | **v2.0** | Metering integrity and disputes |
| S10 Auto Top-Up | **v2.0** | Balance-triggered rules; loop and abuse risk |
| S11 Marketplace Split Payments | **v2.0** | Multi-recipient settlement changes the router → Router v2 + migration |
| S24 White-Label Checkout | **v2.0** | Brand isolation and domain/CSP complexity |
| S25 Partner Platform API | **v2.0** | Platform/tenant hierarchy |

Counts: v1.0 = 18, v1.1 = 2, v2.0 = 5.

### 2.2 The payment model by version

| | v1.0 | v1.1 | v2.0 |
|---|---|---|---|
| Direct settlement in the merchant's accepted stablecoin set (`amountIn == amountOut`) | **ON** | ON | ON |
| Token fallback across the accepted set (new attempt) | ON | ON | ON |
| Conversion execution code (swap, adapter calls, adapter registry, route classes) | **ABSENT** | Router v1.1 + `ConversionPolicyRegistry`, separately audited | in Router v1.1/v2 |
| Stablecoin conversion | **ABSENT** | FLAG (rollout switch) with conditions C1, C2; opt-in by successor mandate | ON for approved pairs |
| General-token conversion | **ABSENT** | ABSENT | Per token after separate audit and token-lab approval |

Conversion requires **C1** (the mandate is bound to a conversion-capable router version, i.e. the customer gave a router-specific authorization) and **C2** (on-chain conversion policy: class open, adapter and pair approved); the rollout switch **R** is an operational control that can only narrow ([09 §4](09-capability-boundaries.md)). **R is not a security boundary.** Direct stablecoin settlement is unaffected by any conversion state.

### 2.3 Journeys that drive the architecture

| Journey | Steps | Key components |
|---|---|---|
| Merchant onboarding | Sign-up → KYB → keys → recipient registration (delayed, OD-022) → sandbox → live review | Merchant, Risk, Compliance, MerchantRegistry |
| **Pay Once** | Intent → quote → Pay Once planner (PO-n) → wallet → tx or relayed → finality → webhook → receipt | Checkout, Quote, Orchestrator, Router `payOnce*` |
| **FastPay activation** | Terms → delegation inspection → planner → wallet → verify V1–V4 → `ACTIVE` | Delegation inspector, Planner, Mandate, MandateManager |
| Recurring charge | Scheduler → cycle → intent → token choice → quote → simulate → sign (policy) → submit → finalize → ledger → webhook | Subscription, Quote, Orchestrator, Signer, Broadcaster, Router `charge*` |
| Customer exit | Portal → revoke/pause (gasless) → optional L2 lockdown | Mandate portal, MandateManager, Permit2 |
| Refund | Merchant request → RefundManager (OD-007) → customer wallet → ledger | Refund, RefundManager, Ledger |
| **Router migration (lineage)** | Deprecate → notices → plan (S1 grant new, S2 revoke old, S3 activate successor) → verify → sunset | Migration orchestrator, RouterRegistry, MandateManager |
| Conversion adoption (v1.1) | Router v1.1 audited and registered → conditions C1, C2 → rollout switch R by stage → customer opt-in successor | Flag service, ConversionPolicyRegistry, Token registry, Migration orchestrator |

## 3. System architecture

```text
 Edge:   CDN + WAF  ->  API gateway                                   (managed services)
 Web:    checkout app, mandate portal, merchant dashboard, admin/risk/incident consoles, developer portal
 Core:   fastpay-core (modular monolith, one deployable, one primary database)
           identity-access | merchant | customer | wallet-capability | delegation-inspector | mandate
           payment-orchestrator | quote | routing | subscription | refund | token-registry | ledger | risk
           migration-orchestrator | feature-flags | notifications | admin-compliance | reporting
 Isolated deployables:
           chain-gateway       indexer + broadcaster + finality/reconciliation, owns chain_* data
           signer              policy-enforcing; executor and charge-signer key classes
           quote-signer        signs PriceQuotes only; its own key class and policy (TM-10)
           webhook-dispatcher  egress-isolated, SSRF-hardened
 Data:   PostgreSQL (core), PostgreSQL (chain-gateway), Redis (rate limits/caches only), object storage (evidence),
         message broker fed by transactional outbox, warehouse (later)
 Chain:  per-chain contract set (section 4) + external Permit2/tokens
```

### 3.1 Recurring charge — sequence

```text
Scheduler    Subscription   Orchestrator       Quote / Registry     quote-signer   Signer(HSM)   Chain Gateway   Router (chain)
   | cycle due     |             |                    |                  |             |             |              |
   |-------------->| create intent (key=mandate:cycle)|                  |             |             |              |
   |               |------------>| select token (priority, balance, allowance, hard caps, risk) via 2 RPC          |
   |               |             | account revalidation (13 s7); direct settlement only (no conversion code)       |
   |               |             |------------------->| price bounds, TTL |             |             |              |
   |               |             |---------------------------------------->| PriceQuote  |             |              |
   |               |             | simulate (eth_call, multi-RPC) incl. caps and quote checks                       |
   |               |             | build typed ChargeRequest + quote                                                |
   |               |             |---------------------------------------------------->| policy check, sign          |
   |               |             |                                                      |------------>| nonce, submit |
   |               |             |                                                                    |-------------->| charge(...)
   |               |             |<------------- events (outbox/inbox): SUBMITTED, PENDING, CONFIRMED, FINALIZED
   |               |             | ledger postings (idempotent by chainId,txHash,logIndex) -> webhook: payment.settled
```

Failure branches: deterministic pre-submission failure → new attempt with the next eligible token (new `attemptId`, same `cycleId`). Any ambiguity after the tx may have left the process → `UNKNOWN` → reconciliation; **no second token charge**, and the chain enforces once-per-cycle regardless (ADR-009).

### 3.2 Payment state model (summary; full tables in C.8)

Two levels: the **intent** (one per order or cycle) and the **attempt** (one per transaction try).

| Level | States |
|---|---|
| Intent | `CREATED`, `QUOTING`, `READY`, `AUTHORIZED`, `SETTLED`, `REFUND_PENDING`, `PARTIALLY_REFUNDED`, `REFUNDED`, `CANCELLED` |
| Attempt | `SIMULATING`, `SUBMITTING`, `SUBMITTED`, `PENDING`, `CONFIRMED`, `FINALIZED`, `FAILED_PRE_SUBMISSION`, `FAILED_REVERTED`, `UNKNOWN`, `RECONCILIATION_REQUIRED` |

Fallback permissibility (the safety-critical rule):

| Attempt ended in | New attempt (another token) allowed? | Condition |
|---|---|---|
| `FAILED_PRE_SUBMISSION` | **Yes** | Deterministic cause: insufficient balance or allowance, token disabled, no valid route, invalid quote, policy limit, deterministic simulation revert, **gate closed** |
| `FAILED_REVERTED` | Yes | Revert observed at the finality threshold from ≥2 sources |
| `SUBMITTING`, `SUBMITTED`, `PENDING` | **No** | Includes RPC, broadcast and receipt timeouts, indexer lag, mempool uncertainty |
| `UNKNOWN`, `RECONCILIATION_REQUIRED` | **No** | Until reconciliation proves non-execution: tx replaced or dropped **and** account nonce consumed by a different tx, or chain state shows no settlement for `paymentId` past the finality threshold |
| `CONFIRMED`, `FINALIZED` | No | Already settled; goes to ledger |
| Reorg of a `CONFIRMED` attempt | No | → `RECONCILIATION_REQUIRED`; ledger reversal entry if the settlement vanished |

### 3.3 Mandate state model (summary; full guards in C.7 and [12 §5](12-router-lifecycle-and-migration.md))

A mandate is bound to **one router for life** and belongs to a **lineage**. On chain, pause is a **set of three independent bits** (customer, risk, **delegation**) plus terminal states; the state name is derived. `MIGRATION_REQUIRED` is **derived** from the router lifecycle (`!RouterRegistry.isChargeable(router)`) or from an unhonorable token-policy change. It is cleared by a **successor mandate** in the same lineage, never by mutating the old one.

| From | To | Actor | Guard |
|---|---|---|---|
| `DRAFT` | `PENDING_ACTIVATION` | Platform | Plan issued ([05](05-evm-authorization-decision-tree.md)); `termsHash` fixed |
| `PENDING_ACTIVATION` | `ACTIVE` | Chain observation | Verification V1–V4 at finality; `startsAt` ≤ now (else waits) |
| `PENDING_ACTIVATION` | dropped | Platform | Plan TTL elapsed with no on-chain effect |
| `ACTIVE` | `PAUSED_BY_CUSTOMER` | Customer | Any time; gasless via `pauseBySig`; never pausable (TM-14) |
| `PAUSED_BY_CUSTOMER` | `ACTIVE` | Customer | Only if the other pause bits are clear |
| `ACTIVE` | `PAUSED_BY_RISK` | `RiskPauser` | Any time; evented |
| `PAUSED_BY_RISK` | `ACTIVE` | `RiskPauser` | Only if the other pause bits are clear |
| `ACTIVE` | **`DELEGATION_UNVERIFIED`** | `RiskPauser` (set by the Account Compatibility Policy: a failed pin simulation or a revalidation difference, [17](17-account-compatibility-policy.md), [13 §7](13-eip7702-delegation-inspection.md)) | Any difference from verified evidence, a pin mismatch, or persistent indeterminacy; the backend blocks before signing and the chain refuses a charge whose pin fails |
| **`DELEGATION_UNVERIFIED`** | `ACTIVE` | `RiskPauser` | Automatic when the account returns to the verified state, or after customer re-verification with new evidence ([13 §7.5](13-eip7702-delegation-inspection.md)); never by time alone; other bits clear |
| `ACTIVE`/`PAUSED_*`/`DELEGATION_UNVERIFIED`/`MIGRATION_REQUIRED` | `REVOKED(reason)` | Customer, or `activateSuccessor` | Reasons `CUSTOMER`, `SUPERSEDED_MIGRATION`, `SUPERSEDED_REVISION`, `MANAGER_REPLACED`; terminal; customer revoke is gasless via `revokeBySig` |
| `ACTIVE` | `EXPIRED` | Time | `block.timestamp ≥ expiresAt`; terminal |
| `ACTIVE` | `EXHAUSTED` | Router | Lineage total cap (token or fiat) or max cycles consumed; terminal |
| `ACTIVE` | `MIGRATION_REQUIRED` (derived) | Registry lifecycle | Router `SUNSET` / `DISABLED_EMERGENCY`, or unhonorable policy change; **no new charges** |
| `MIGRATION_REQUIRED`, or `ACTIVE` on a `DEPRECATED` router | successor `ACTIVE` | Customer | `activateSuccessor`: router-specific authorization, containment of terms, **old Router permission unusable** ([12 §5.3](12-router-lifecycle-and-migration.md)); the predecessor becomes `REVOKED(SUPERSEDED_MIGRATION)` in the same transaction |

## 4. Contract architecture (outline; full spec in Part D)

| Contract | Responsibility | Trust zone | Mutable? | Key entry points (names only) |
|---|---|---|---|---|
| `MandateManager` | The **core** of the mandate system and the only contract that writes mandate state: mandates and **lineages**, the **exposure index**, the nonces, **`accountPin`**, activation, successor activation (the structural checks and the effects E1…E6; the predicates that only read state are in `SuccessorValidator`), three pause bits, revoke/reduce, the guards of `consume`, `extensionsHash` (must be zero); the terms are kept as a hash plus the data that exits need (ADR-021) | Z5 | Immutable | `activate`, `activateSuccessor`, `updateAccountPin`, `revoke`, `retire`, `pause`, `resume`, `reduce` (narrowing only), `setPauseBit` (risk and delegation, by the pause authority), `spendNonce` (gateway only), `consume` (the lineage's active mandate, from its bound router only; takes the seven-field `AccountPin` as calldata and checks its hash and `PIN_OK`); a function that takes `customer` first accepts the customer or the gateway (and, for `activateSuccessor`, the queue). **No export/import hooks, no rebind, no delegatecall** |
| `UsageLedger` | The usage counters of a lineage: per-token and fiat totals and the four windows (lazy reset), the cadence, the settled cycles and their quote digests (ADR-021) | Z5 | Immutable | `charge` (the manager only), views `tokenUsage`, `fiatUsage`, `cycleRecord`, `cadence` |
| `SuccessorValidator` | The predicates of `activateSuccessor` that read state and write none: A3, R1…R3, X1, K1, G1, X2, C1/C2, O1N/O1E (ADR-021); stateless; called with STATICCALL | Z5 | Immutable | `validate` (view) |
| `MandateGateway` | Verifies the customer's EIP-712 signatures (domain: the **manager**), spends the nonce at the manager and relays the call as the customer; pin batches (ADR-021); holds no state | Z5 | Immutable | `activateBySig`, `activateSuccessorBySig`, `revokeBySig`, `pauseBySig`, `resumeBySig`, `reduceBySig`, `updateAccountPinBySig`, `updateAccountPinsBySig`, `updateAccountPins` (≤ `MAX_BATCH`) |
| `MigrationQueue` | A bounded, resumable migration plan: a hash chain over the successor authorizations that the customer committed to, executed in steps of at most `MAX_BATCH`; skip, abort, expire (ADR-022) | Z5 | Immutable | `open`, `step`, `skip`, `abort`, `expire` |
| `PaymentRouter` | Verifies request and quote, pulls via Permit2, pays merchant and fee, retains nothing; **separate entrypoint families for the two protocols; no conversion entrypoints** | Z5 | Immutable; versioned | **Protocol B:** `charge`, `chargeInitial` · **Protocol A:** `payOnceWithSignature`, `payOnceWithSignatureAndPermit`, `payOnceWithAuthorization` (flag), `payOnce`. External calls only to Permit2, registry-listed tokens, `MandateManager`, `RouterRegistry` and the fixed registries (`I-EXTCALL`) |
| `RouterRegistry` | Router versions, code hashes, audit commitments, lifecycle states, immutable notice minimums, shared `markSettled(paymentId)` for Pay Once | Z5 | Immutable code; governance-timelocked state; guardian emergency-disable | `propose`, `activate`, `deprecate`, `sunset`, `retire`, `emergencyDisable`, `isChargeable`, `isBindable` |
| `MerchantRegistry` | Merchant id → recipient (delayed change), accepted tokens, `chargeSigner`, status, merchant-level pause | Z5 | Governance-timelocked config | `register`, `proposeRecipient`, `acceptRecipient`, `setChargeSigner`, `pauseMerchant` |
| `TokenPolicyRegistry` | Token status (`SWAP_ONLY` cannot be listed in v1), decimals (at most 36), per-token `tokenVersion`, the **price-bounds registry** (append-only versions per (token, currency), width at most `MAX_BAND_WIDTH_BPS`, ADR-020) and the **price-source-set hash** per (token, currency) (no oracle reference in v1); the **versioned quote-signer sets are a separate contract** (`SignerSetRegistry`, ADR-023) | Z5 | Governance-timelocked; guardian can only block a token, never list | `list`, `setStatus`, `publishBounds`, `setPriceSourceSet`, `block_` (guardian), views `quoteContext`, `bandOf` |
| `SignerSetRegistry` | **Versioned quote-signer sets** with rotation, a bounded grace for previously issued quotes, and emergency removal with **no grace** and permanent tombstones ([11 §4.7](11-dual-cap-model.md)); at most `MAX_SIGNERS_PER_SET` members (PC-19); the check is O(1) (ADR-023) | Z5 | Governance-timelocked; guardian can only remove a signer or stop a set, never add | `proposeSignerSet`, `activateSignerSet`, `removeQuoteSigner`, `stopSignerSet`, view `verifySigner` |
| `QuoteVerifier` (library) | EIP-712 `PriceQuote` v1 verification (fifteen fields, Q1–Q20, [11 §4.2](11-dual-cap-model.md)), bounds intersection, round-up fiat valuation; ECDSA quote signers only; returns only `(fiatValueMinor, quoteDigest)` | Z5 | n/a | — |
| `ExecutorRegistry` | Authorized executors | Z5 | Timelocked add; guardian remove | `add`, `remove` |
| `FeeController` | Fee bounds and recipient; immutable ceiling | Z5 | Bounded config | `setFee` (≤ ceiling) |
| `RefundManager` | Merchant-funded refunds (OD-007) | Z5 | Immutable | `refund` |
| `EmergencyGuardian` | Stop-only actions with **separate switches** for recurring and Pay Once | Z5 | Immutable | `pauseCharge`, `pausePayOnce`, `blockToken`, `removeExecutor`, `removeQuoteSigner`, `stopSignerSet`, `emergencyDisableRouter` |
| *(v1.1 only)* `ConversionPolicyRegistry`, adapters, Router v1.1 | Route classes, approved pairs with `labApprovalHash`, adapters with code hash; typed adapter interface; conversion entrypoints | Z5/Z6 | — | **ABSENT in v1.0** (no contract, no address in the manifest); audited as a new router version in v1.1 ([09](09-capability-boundaries.md)) |
| `SignatureVerifier` (library) | EIP-712 hashing; ECDSA with low-`s`; ERC-1271 via `STATICCALL` without an artificial gas cap (CLM-032), used for contract-account customers | Z5 | n/a | — |

`EIP7702Executor` is **not** built (OD-011). No contract uses `tx.origin` (static check; CLM-053). `PayOnce` code paths do not reference `MandateManager` or `AllowanceTransfer`; recurring code paths do not reference `SignatureTransfer` (S-1, S-2).

### 4.1 System invariants (each has fuzz/invariant tests and appears in the audit scope)

| ID | Invariant | Test type |
|---|---|---|
| I-MANDATE | A pull happens only under an `ACTIVE` mandate bound to the calling router and matching token, merchant, amount, time and cadence | Invariant + fork |
| I-CAP-TOKEN | Per-token per-payment, window and total caps never exceeded ([11](11-dual-cap-model.md)) | Invariant + fuzz |
| I-CAP-FIAT | Quote-derived fiat consumption never exceeds fiat caps; value rounded up | Fuzz + property |
| I-QUOTE | Fiat-capped charges need a valid, bound, unexpired, in-bounds quote from a registered signer (Q1–Q20, [11 §4.2](11-dual-cap-model.md)) | Fuzz |
| I-QUOTE-NI | **Non-interference:** no quote can make a charge succeed that guards G1…G12 reject ([11 §4.8](11-dual-cap-model.md)) | Stateful fuzz with an adversarial signer; mutation tests |
| I-BOUNDS-SNAPSHOT | Effective price bounds never wider than the mandate's snapshot | Invariant |
| I-ONCE | At most one settled payment per `(lineageId, cycleIndex)` and per Pay Once `paymentId`, **across all router versions and mandate generations** (identifiers contain no router input, [11 §3.1](11-dual-cap-model.md)) | Invariant + migration fork |
| I-MINOUT | Merchant recipient receives at least the required output; fee ≤ min(`maxFee`, ceiling) | Invariant |
| I-RECIPIENT | Settlement goes only to the registry recipient valid at charge time | Unit + fork |
| I-ZEROBAL | Router token balances before and after any entry point are equal | Invariant |
| I-NOARB | No external call with caller-supplied target or calldata (CF-002) | Static + review |
| I-EXTCALL | The set of external call targets reachable from Router v1 is fixed (Permit2, registry-listed tokens, `MandateManager`, `RouterRegistry`, fixed registries); **no conversion code exists** (absence check, [09 §7](09-capability-boundaries.md)) | Static call-graph analysis + fork trace |
| I-EXIT | Customer revoke, pause and successor creation are never blocked by pause, governance or registry state (TM-14) | Fork with paused router |
| I-ADMIN | No role path moves customer tokens (TM-03) | Role-matrix test |
| I-REPLAY | Signatures are single-use and bound to `chainId` and contract (TM-04) | Fuzz |
| I-TIME | No charge before `startsAt`, after `expiresAt`, or inside `minInterval` | Fuzz |
| I-SNAPSHOT | A registry change can narrow but never widen an existing mandate's token set | Invariant |
| I-PO-NOSTANDING | Pay Once leaves no allowance to the router and creates no Permit2 allowance or mandate | Invariant + fork |
| I-PO-WITNESS | A Pay Once transfer succeeds only if the recomputed witness equals the signed witness | Fuzz |
| I-MIG-1…11 | One active mandate per lineage; terms contained; counters preserved; exits unblockable; registered-target only; minimum notice; **shared-allowance rule** (normal: the old allowance may stay while a sibling uses the token and is zero or expired when none does; emergency: zero or expired for every exposed token); **no overlapping authority** (`AuthRouters(L)` has at most one element); **monotone authority** (a successor accepts nothing its predecessor would not); **the exposure index is never an under-count**; **activation does not touch Permit2 or any sibling** | See [12 §12](12-router-lifecycle-and-migration.md) |
| I-ACCT-PIN | A charge executes only if `hashStruct(pin) = accountPinHash` and `PIN_OK(customer, pin)`: the account's code hash and, for a 7702 account, the delegate's code hash ([17 §5](17-account-compatibility-policy.md)) | Fork tests on plain, delegated and contract accounts; fuzz over the code hashes; mutation of each field |
| I-ACCT-NOWIDEN | `updateAccountPin(s)` changes no field other than `accountPinHash` and `pinVersion` | Storage-diff and stateful fuzz |
| I-ACCT-SIG, I-ACCT-VERSION | An ERC-1271 signature is accepted for an authority-creating message only under `signatureMode = ERC1271` and `PIN_OK`; `pinVersion` never skips or decreases | ACP-TV-35…40; fuzz; mutation |
| SR-1…SR-7 | Signer sets: no grace after emergency removal; bounded earlier-quotes-only rotation; monotone; tombstones permanent; fail closed; non-interference; the guardian cannot add ([11 §4.7.1](11-dual-cap-model.md)) | CAP-TV-23…32; model checks; fuzz |
| I-L2-NOMAX | FastPay never creates a Permit2 allowance of `uint160.max` (verified by the activation verifier V2) | Planner vector + verifier test |
| I-DELEG | No unattended charge is signed without an Account Compatibility Policy stamp younger than 60 seconds for the mandate's current pin, and the delegation pause bit stops `consume` | Signer-policy test + contract test; DRV-01…25, ACP-TV-01…44 |
| I-LEDGER | Debits equal credits per journal and asset (off-chain) | DB constraint + property test |

## 5. Backend architecture (initial)

### 5.1 Deployables and data ownership

| Deployable | Owns (data) | Exposes | Consumes | Why separate |
|---|---|---|---|---|
| `fastpay-core` | Core DB: merchants, customers, wallets, capabilities, delegation observations, mandates, plans, subscriptions, cycles, intents, attempts, quotes, ledger, risk, migration, flags, audit, outbox/inbox, idempotency | REST API; events | chain events | Cohesive business logic, one transaction boundary |
| `chain-gateway` | chain_transactions, confirmations, logs, nonces, RPC health | Internal API + events | Chain RPCs | RPC credentials, long-lived subscriptions, different scaling and failure behavior |
| `signer` | Audit log only | Sign API accepting **structured intents** (TB-04) | Core intents | Only component allowed to use the executor and charge-signer keys |
| `quote-signer` | Audit log only | Sign API for `PriceQuote` only | Quote service requests | Distinct key class and policy; compromise of executors must not yield quotes (TM-10) |
| `webhook-dispatcher` | Delivery state | — | Outbox events | Egress isolation (TB-12) |

Bounded contexts from prompt §13 map into `fastpay-core` modules with enforced dependency rules. A module is extracted only when a written criterion is met: independent scaling need, different secret/compliance profile, or team boundary that blocks delivery.

### 5.2 Consistency, retries, backpressure

- Transactional outbox in each DB; broker for fan-out; inbox with event-id dedupe.
- No distributed transactions. The payment orchestrator and the migration orchestrator are sagas with persisted state; every step is idempotent by `(intentId, attemptId, stepKey)` or `(planId, stepIndex)`.
- Retries: bounded exponential backoff with jitter; circuit breakers on RPC, quote, vendor calls; a retry budget per merchant.
- Backpressure: bounded queues; per-chain submission rate and per-merchant concurrency.
- Degradation order when impaired: stop new activations → stop conversion (if on) → stop non-essential charges → keep **revocation, successor creation and read paths** alive longest.

### 5.3 Feature-flag service

Two-person enabling, one-person disabling, audited, evented, fail-closed, evaluated at plan and at execution time ([09 §5](09-capability-boundaries.md)). Flags can only narrow what the chain allows.

### 5.4 Observability baseline

Correlation identifiers end to end: `requestId`, `intentId`, `attemptId`, `mandateId`, `planId`, `chainId`, `txHash`, `campaignId`, `delegationRecordId`. Structured JSON logs with redaction (signatures, permit payloads, quote signatures, API keys, KYB documents; wallet addresses hashed for analytics). Proposed SLOs (PROPOSAL): API and checkout availability 99.9%; `AUTHORIZED`→`SUBMITTED` p95 < 10 s; webhook first attempt p95 < 5 s after `FINALIZED`; quote issuance p95 < 500 ms; control-plane RPO ≤ 1 min, RTO ≤ 30 min. Contracts have no RTO for customer safety because customers can exit without us.

## 6. Data and ledger architecture (outline)

Table groups (35 tables of prompt §15 plus the additions below): identity/tenancy; authorization (wallet capabilities, mandates, mandate revisions, token authorizations); billing; payments (intents, attempts, quotes, routes, chain transactions, confirmations, settlements, refunds); integration (webhook endpoints/events, idempotency, outbox, inbox); risk and operations (alerts, cases, incidents, support, audit logs); registries (token policies, chain configurations); finance (ledger accounts, journals, postings); analytics.

**Additions in v0.2:** `account_delegation_observations`, `router_versions`, `mandate_router_bindings`, `migration_campaigns`, `migration_cohorts`, `migration_notices`, `migration_plans`, `feature_flags`, `feature_flag_changes`. Quotes carry `priceE18`, `fiatValueMinor`, `sourcesCommit`, signer id, TTL and the resulting hard-cap usage.

Ledger principles (F.3 specifies all 20 scenarios):

1. Two views. **Movement ledger**: mirrors on-chain transfers keyed by `(chainId, txHash, logIndex)`. **Financial ledger**: FastPay's receivables, fee revenue, gas expense, reserves, refunds, credits, tax.
2. Immutable postings; corrections by reversal; a reorg creates a linked reversal journal.
3. Per-asset balancing; no implicit conversion. **Conversion (v1.1+)** is an explicit two-leg journal through a conversion account, with residue return and a price-impact memo; the scenario set exists and is tested in v1.0 against mock conversions.
4. `PENDING` and `FINAL` states are explicit; revenue is recognized only at `FINAL`.
5. Fiat valuation is stored in minor units next to atomic units; no floating point.
6. FastPay holds no customer or merchant principal (ASM-001); if OD-001 changes this, safeguarded-funds accounts are added.

## 7. Infrastructure baseline (provisional; ADR-012)

| Area | Starting position | Closes with |
|---|---|---|
| Cloud | Single provider, multi-account. Provisionally AWS (OD-015) | RP-15 |
| Compute | Managed containers first; Kubernetes only on written need | ADR-012 |
| Database | Managed PostgreSQL, Multi-AZ, PITR, row-level security | H.2 |
| Keys | KMS/HSM non-exportable secp256k1 keys, **one class each**: executor, charge-signer, **quote-signer**, webhook signing, CI signing (TM-10) | RP-15 |
| RPC | ≥2 independent providers plus a self-hosted node per launch chain for critical reads | RP-04 |
| Edge | CDN + WAF + DDoS; DNSSEC, registrar lock, CAA; certificate-change monitoring | H.2 |
| CI/CD | Pinned deps, SBOM, signed artifacts, provenance, OIDC deploy credentials, policy as code | G.4 |
| Environments | local, CI, dev, testnet, staging, canary mainnet, production, DR | H.2 |

## 8. Non-goals for v1.0 (`NON-GOAL`)

Cross-chain settlement and bridging; custodial wallets or any key custody; fiat on/off ramps and card payments; NFT payments; non-EVM chains; native-asset recurring pulls (OD-009); fee-on-transfer, rebasing and callback tokens (ASM-022); own EIP-7702 delegate (OD-011); merchant-of-record services; conversion of any kind in v1.0 (the code is absent; Router v1.1 and v2.0 add it in stages, by opt-in).

## 9. Architecture Decision Records

Format: Context · Decision · Alternatives · Consequences · Verification. Status of all: **Proposed**. "Revised" marks decisions changed by the 2026-10-13 sponsor directive.

### ADR-001 — Immutable core, versioned deployments, with a complete lifecycle (Revised)
- **Context.** A Permit2 permit names only the spender (CLM-026). An upgradeable router could widen authority over every existing allowance. Immutability is only safe if replacement is designed.
- **Decision.** `PaymentRouter` and `MandateManager` are immutable. Router versions are registered in `RouterRegistry` with a lifecycle (CANDIDATE → ACTIVE → DEPRECATED → SUNSET → RETIRED, plus emergency disable) and immutable minimum notice periods. A mandate is bound to one router for life; moving to another router creates a **successor mandate** in the same lineage with a router-specific customer authorization, and counters are preserved at lineage level. The complete protocol is [12](12-router-lifecycle-and-migration.md).
- **Alternatives.** Proxy + timelock (rejected: upgrade authority is custodial-equivalent); immutable without a migration design (rejected: unfixable bugs, stranded mandates).
- **Consequences.** Bug fixes need migration campaigns; costlier ops, much smaller trust surface. Guardian can stop a flawed version immediately without blocking exits.
- **Verification.** Bytecode verification per chain; `I-MIG-1…11`; rehearsal on testnet and a mainnet canary drill; no `delegatecall` to mutable targets.

### ADR-002 — Spending authority originates only from the customer
- **Decision.** Authority is created only by customer-originated transactions or customer EIP-712 signatures verified on chain (ECDSA or ERC-1271). No server-held key can create, widen or restore authority.
- **Verification.** Role-matrix test `I-ADMIN`; forged-activation threat tests.

### ADR-003 — Three-layer authorization with bounded Layer 2 (Protocol B)
- **Decision.** L1 token→Permit2, L2 Permit2→router (amount and expiry sized to the mandate horizon, never `uint160.max`), L3 mandate. L1 sizing is bounded (OD-005).
- **Alternatives.** Direct token approval to the router (rejected: no standardized revoke surface, unbounded in time); smart-account-only permissions (kept as optional adapter, OD-010).
- **Verification.** Planner golden vectors; `I-MANDATE`; `I-L2-NOMAX`.

### ADR-004 — Dual cap model (Revised; supersedes the v0.1 single-cap decision)
- **Context.** Fiat-equivalent caps are what customers understand; raw token caps are oracle-free. The v0.1 record used token caps only.
- **Decision.** Two cap classes enforced together on chain: **hard per-token atomic-unit caps** (authoritative, oracle-free) and **fiat-equivalent caps** verified through **signed, expiring quotes** whose price must lie inside **bounded price inputs** held in the token registry, with fiat values derived on chain and rounded up. Backend risk controls can only tighten. Which limits are authoritative where is fixed in [11 §2](11-dual-cap-model.md).
- **Alternatives.** Token caps only (rejected: not meaningful to customers); oracle-attested caps only (rejected: puts an oracle on the sole enforcement path); off-chain fiat caps (rejected: violates TM-02).
- **Consequences.** A quote-signer key class and service; quote-signer outage means no charges (fail closed); blast radius bounded as in [11 §6](11-dual-cap-model.md).
- **Verification.** `I-CAP-TOKEN`, `I-CAP-FIAT`, `I-QUOTE`, `I-BOUNDS-SNAPSHOT`; malicious-signer property tests; CAP-TV-01…32.

### ADR-005 — Modular monolith with four isolated services (Revised)
- **Decision.** One `fastpay-core` plus `chain-gateway`, `signer`, `quote-signer`, `webhook-dispatcher`. Extraction needs a written criterion.
- **Alternatives.** Full microservices (rejected); single monolith including signing (rejected: key blast radius).
- **Verification.** Dependency-rule lint; architecture fitness tests.

### ADR-006 — Own chain observation; third-party indexers for discovery only
- **Decision.** Money decisions use our indexer fed by ≥2 independent RPC sources at the per-chain finality threshold. Third-party indexer APIs may list tokens and balances and hint at authorization history; every figure that matters is re-read on chain.
- **Verification.** Chaos tests with lying RPC and lagging indexer.

### ADR-007 — Capability-driven planner; wallet-managed 7702 preferred; delegation inspected and recorded (Revised)
- **Decision.** The planner chooses a transport from normalized capabilities. FastPay prefers wallet-managed upgrades requested through `atomicRequired:true`; it never requests a raw EIP-7702 authorization, never uses `chain_id=0`, and ships no delegate (CLM-013; OD-011). Because **delegation is persistent account state** (CLM-016), FastPay inspects and records the resulting delegation implementation, bytecode hash, account state, revocation path and compatibility evidence for every plan ([13](13-eip7702-delegation-inspection.md)). Delegation is never described as temporary.
- **Alternatives.** Own delegate (rejected: authority over entire accounts); trust vendor documentation (rejected: MetaMask's docs name no delegate and do not state persistence, CLM-043).
- **Verification.** Golden vectors; hostile-delegate fork tests; wording lint.

### ADR-008 — Tiered charge authentication
- **Decision.** Executors submit; each charge carries a `ChargeRequest` signed by the merchant's registered `chargeSigner` (HSM by default; merchant-held opt-in, OD-003).
- **Consequences.** In the default tier FastPay's control plane is a trusted charge originator; on-chain caps are the real bound; the opt-in tier removes that trust.
- **Verification.** Signer-policy tests; compromised-backend red team.

### ADR-009 — Exactly-once is enforced on chain, across router versions and mandate generations (Revised)
- **Decision.** Recurring settlements are recorded in `MandateManager` keyed `(lineageId, cycleId)`; Pay Once settlements in `RouterRegistry` keyed `paymentId = keccak256(abi.encode(chainId, RouterRegistry, merchantId, orderId))`. Neither key includes a router address or a mandate id, so a settlement under one router or generation blocks a second under another.
- **Consequences.** A wrong off-chain retry with a different token after an `UNKNOWN` attempt still yields at most one settlement; the off-chain "no fallback while unknown" rule remains to avoid surprising token choice and wasted gas.
- **Verification.** `I-ONCE`; MIG-TV-11; race tests on a fork.

### ADR-010 — Exit is never pausable; guardian is stop-only
- **Decision.** Pause blocks new pulls only. Customer revoke/pause/successor creation and Permit2 lockdown are unaffected. Guardian cannot unpause, enable, or move.
- **Verification.** `I-EXIT`, `I-MIG-4`; role-matrix test.

### ADR-011 — Money as atomic integers
- **Decision.** `uint256` on chain, `numeric(78,0)` in PostgreSQL, decimal strings in JSON, fiat as `uint64` minor units, no floating point in any financial path, decimals fixed in the registry.
- **Verification.** Lint banning float types in financial packages; property tests on conversions.

### ADR-012 — Provisional infrastructure baseline
- **Decision.** Single cloud, managed containers, managed PostgreSQL, KMS/HSM with one key class per role, ≥2 RPC providers + own node. Provisionally AWS pending RP-15 and team skills (OD-015).
- **Status.** Explicitly provisional.

### ADR-013 — Conversion execution code is ABSENT from Router v1; conversion is a later router version (Revised; supersedes the v0.2 "dormant boundary")
- **Context.** The sponsor directive: FastPay must not be permanently swap-free; direct stablecoin settlement is ON for MVP; conversion is staged; general-token conversion stays off until audit and token-lab approval. Correction 1: *a feature flag is not a security boundary* — decide whether swap code is absent from Router v1 or fully in the v1 audit scope.
- **Decision.** **Absent.** No swap or conversion execution code, adapter call, adapter registry or conversion state exists in any v1.0 contract. Conversion is delivered as **Router v1.1** with a new `ConversionPolicyRegistry` and the first adapter, each independently audited, and adopted by customers as an **opt-in successor mandate** ([12](12-router-lifecycle-and-migration.md)). The boundary is *designed* now (specifications, `PriceQuote` v2, ledger journals, planner policy, `Mandate.extensionsHash` reserved as zero data) but nothing executable is deployed. The security boundary is **code presence per router version plus the customer's router-specific authorization**; rollout switches only narrow.
- **Alternatives.** Compile the boundary into Router v1, dormant behind gates (rejected: unaudited-in-practice code that a customer authorized without consent to its capabilities, a larger v1 audit, and gating logic that becomes the boundary); omit all design (rejected: contradicts the directive).
- **Consequences.** Smaller, sharper v1 audit; Q-03 (is routing a swap an exchange service) is off the v1.0 critical path; enabling conversion costs a second router audit and an opt-in campaign (RISK-024 reframed).
- **Verification.** Mechanical absence check in the release pipeline (ABI selectors, call-graph allowlist, manifest contains no conversion contract, `extensionsHash == 0`; PB-040); `I-EXTCALL`; TV-12, TV-21; router-specific domains reject v1.1 signatures on v1.

### ADR-014 — Two protocols: Pay Once on `SignatureTransfer`, recurring on `AllowanceTransfer` plus a mandate (New)
- **Decision.** Separate entrypoint families, separate planners, separate pause switches, separate tests and consent copy. Pay Once never creates a standing allowance or a mandate; recurring never uses `SignatureTransfer` (S-1…S-4, [10](10-pay-once-protocol.md)).
- **Alternatives.** One entrypoint with a mode flag (rejected: shared failure modes and a larger audit surface per path).
- **Verification.** Static reference checks; `I-PO-NOSTANDING`; `I-PO-WITNESS`.

### ADR-015 — Router lifecycle and mandate lineage (Revised; replaces in-place rebinding)
- **Decision.** `RouterRegistry` lifecycle with immutable minimum notice. A mandate is bound to one router for life. Migration creates a **successor mandate** (`activateSuccessor`) in the same **lineage** with a **router-specific customer authorization**; counters, windows, totals and cycle records are keyed by `lineageId`; the successor's terms are contained in an **on-chain snapshot** of the predecessor's (expiry, merchant scope, token scope, every remaining cap, fee cap and slippage cap cannot increase; Lemma M in [12 §5.3.3](12-router-lifecycle-and-migration.md)); the **old router's Permit2 allowance is handled according to the fact that it is shared by every mandate of the customer on that router and token** (Permit2 keys it `(owner, token, spender)`): in a **normal** migration (router still trusted) it may remain while a sibling relies on it, bounded, and must be zero or expired (`a = 0 ∨ e < now`) once no sibling does; in an **emergency** migration (router disabled, sunset, retired or security-deprecated) it must be unusable for **every token the customer's mandates use on that router**; the mode comes from the registry, an on-chain exposure index makes both rules checkable, and the predecessor is revoked as `SUPERSEDED_MIGRATION` in the same transaction; the exact predicates, atomic and legacy flows, the sibling rules and the no-overlap proof are in [12 §5](12-router-lifecycle-and-migration.md). Cycle identity is bound to the lineage, not to a router. Communications and rollback per [12](12-router-lifecycle-and-migration.md).
- **Alternatives.** In-place `rebindRouter` (rejected: changes what an existing authorization means, weaker evidence of consent, no verifiable revocation); a new mandate with reset counters (rejected: lets caps reset).
- **Consequences (0.5).** One more piece of manager state (the exposure index, bounded by `MAX_EXPOSED_TOKENS_PER_ROUTER`, PC-18) and one more permissionless function (`retire`); a normal migration never unfunds a sibling; a security-driven migration interrupts siblings until their successors exist (OD-035).
- **Verification.** MIG-TV-01…45; `I-MIG-1…11`; containment fuzz against the monotone-authority lemma; the Foundry suites of [foundry/](foundry/) (vectors, fuzz, invariant, mutation, integer-width, timestamp-boundary, shared-allowance; written, not yet compiled or run); rehearsal and canary drill.

### ADR-016 — Signed, expiring quotes with bounded price inputs; a dedicated quote-signer key class (New)
- **Decision.** `PriceQuote` EIP-712 with fifteen fields, bound to `paymentId`, token, exact `amountIn`, route and the registry's version, signer-set version and price-source-set hash; the contract derives fiat value (round up); bounds in the registry with intersection semantics; ECDSA quote signers in versioned sets with **bounded-grace rotation for previously issued quotes only and no-grace emergency removal with permanent tombstones (SR-1…SR-7)**; no oracle slot in v1 (a later verifier version adds it, OD-027); a **non-interference proof** shows no quote can override a mandate ([11 §4.8](11-dual-cap-model.md)); schema frozen at RG-016 and reproduced by a test vector ([11 §4.6](11-dual-cap-model.md)).
- **Verification.** CAP-TV-01…32; non-interference fuzz and mutation tests; signer-set model checks and Foundry suite (`SignerSet.t.sol`).

### ADR-017 — Code-bearing accounts: signature flows gated on a verified ERC-1271 path (New)
- **Context.** Permit2 verifies signers with code only via ERC-1271 and never falls back to `ecrecover` (CLM-050); 7702-delegated EOAs have code.
- **Decision.** Signature transports require `sigAllowed = (class == EOA) or (sig1271 == VERIFIED)`, backed by an E3 Compatibility Register row and a per-signature pre-flight. Otherwise `msg.sender` flows (batch/transactions) or refusal.
- **Verification.** TV-18…20; EV-P07; hostile-delegate fork tests.

### ADR-018 — Account Compatibility Policy: an on-chain pin plus backend revalidation (Revised; replaces backend-only revalidation and reverses OD-029)
- **Context.** Delegation and smart-account code are persistent and can change after the customer verified an account (CLM-016); charges are made without the customer present. v0.3 relied on a backend revalidation and a pause bit and rejected an on-chain pin because `EXTCODEHASH` sees only the designator.
- **Decision.** An **Account Compatibility Policy** ([17](17-account-compatibility-policy.md)): five account modes (`PLAIN_EOA`, `EOA_7702_VERIFIED`, `SMART_4337`, `WALLET_1271`, `UNKNOWN_CODE`) with a permission matrix; unattended charges only in the first four and only while the account still matches. Three layers, each fail-closed: (C) the mandate carries the hash of a customer-signed seven-field **`AccountPin`** (account mode, account code hash = the delegation designator hash for a 7702 account, delegate, delegate code hash, implementation family, pin version, signature mode) and `consume` reverts `AccountCodeChanged` unless `PIN_OK(customer, pin)` (`EXTCODEHASH` of the account and, for a 7702 account, of the delegate); the pin is updated only by the customer (`updateAccountPin`) with a strictly consecutive version and never changes a cap; the ERC-1271 signature path of FastPay's contracts is open only while the pin holds (`AUTH`); (R) allowlist rows at E3 decide whether code is known; (B) the backend observes, probes and revalidates what the chain cannot see (delegate code, proxy implementation, ERC-1271 behavior) and pauses through the third on-chain pause bit. No token fallback. A code-bearing account without an E3 row is `UNKNOWN_CODE` and refused for recurring.
- **Alternatives.** Backend-only revalidation (rejected by the sponsor: the chain would charge whatever the backend concluded); a pin of the delegate's own code (impossible: `EXTCODEHASH` does not follow the delegation); a registry of allowed code hashes on chain (rejected: more code, no gain over customer pinning).
- **Consequences.** One or two `EXTCODEHASH` per charge (about 2,600 gas each cold, unmeasured) plus the pin calldata; some false positives when customers change wallets or accept wallet upgrades (each resolved by a one-signature re-verification); residual risk where the implementation behind a proxy, a module or an owner set changes ([17 §4.1, §5.5](17-account-compatibility-policy.md)). The field-by-field split of what the contract verifies and what stays off chain is in [17 §5.5](17-account-compatibility-policy.md); ERC-1271 evidence is bound to the pin and revoked by eleven triggers ([17 §5.6](17-account-compatibility-policy.md)).
- **Verification.** ACP-TV-01…44; DRV-01…25 ([13 §11](13-eip7702-delegation-inspection.md)); `I-ACCT-PIN`, `I-ACCT-NOWIDEN`, `I-ACCT-SIG`, `I-ACCT-VERSION`, `I-DELEG`.

### ADR-019 — Revocation: transactions are primary; signed zero-amount `permit` is experimental (New)
- **Decision.** Primary flows: token `approve(Permit2, 0)`, `Permit2.lockdown`, `Permit2.approve(token, router, 0, 0)`, `invalidateNonces`, and FastPay's own `revoke`/`revokeBySig`. The signed zero-amount `permit` stays behind `revocation.zeroPermit.enabled` (off) until EV-P08 evidence exists per wallet, token and chain. Plans never claim gasless L1 or L2 revocation ([05 §2.1](05-evm-authorization-decision-tree.md)).
- **Verification.** RV-T01…RV-T12 and ZP-T01…ZP-T08 ([05 §2.2](05-evm-authorization-decision-tree.md)); EV-P08, EV-P11; plan-validator test NC-17; MIG-TV-16.

### ADR-020 — Price bounds are a versioned token-currency registry; a mandate pins the currency and the bounds version; the migration snapshot covers the customer, the anchor and the bounds version (New; closes F-06, F-07, F-09)
- **Context.** Until 0.5 a mandate carried its own price pair (`minPriceE18`, `maxPriceE18`) next to the registry's bounds, and `I-BOUNDS-SNAPSHOT` asked that the effective band never be wider than the mandate's. The implementation evidence found that a pair the customer signs is a number the customer cannot judge (F-09), and that the snapshot hash that the model implemented differed from the one of [12 §5.3.4](12-router-lifecycle-and-migration.md): it left out the customer, `anchorStartsAt` and the bounds (F-06, F-07).
- **Decision.** (1) Bounds are published per `(token, currency)` in `TokenPolicyRegistry` as **append-only versions** (`publishBounds`), each at most `MAX_BAND_WIDTH_BPS` wide (PC-07); a published version is never changed or removed (rule V5 of [eip712/types.json](eip712/types.json)). (2) A mandate pins the invoice **currency** and a **`boundsVersion`**; it carries no price pair. (3) Q15: the quote names the registry's current version; Q18: the price lies in the **intersection** of the band of the pinned version and the band of the current version, so a later tighter band narrows an existing mandate at once and a later wider band never widens it; a pinned version that was never published can never be charged against a fiat cap (`BoundsNotPublished`). (4) Containment clause K.6 asks for the **same** bounds version; in a revision a different version, like a longer `maxQuoteAge`, is a widening (bit 6 of the widened mask). (5) The migration snapshot is the 26 words of `snapshotEncoding` in types.json: it adds **`customer`, `anchorStartsAt` and `boundsVersion`**; no ADR shows that any of the three is unnecessary, and each is needed (the customer binds the authorization to one account, `anchorStartsAt` is a lineage constant of the window grid, `boundsVersion` is K.6). (6) `newTermsHash` is `hashStruct(MandateTerms)` of the generated library; `eip712/types.json` is the single source of the structs, the encodings, the tags and the versioning rules, and everything else (Solidity, TypeScript, Python vectors, Foundry tests, wallet-lab payloads, the type listing) is generated from it.
- **Alternatives.** A pair per mandate (rejected: F-09); mutable bounds with a snapshot copy in each mandate (rejected: the snapshot is what the pair was, and it makes K.6 a comparison of two numbers that a stale wide band can satisfy); leaving the customer out of the snapshot because `lineageId` contains it (rejected: `lineageId` does not bind the authorization to an account that later changes pin or code).
- **Consequences.** A new bounds version invalidates quotes in flight (Q15); history grows by three slots per version; the planner must tell the customer which bounds version the consent pins; `FiatTerms` lost two fields, so every type hash that includes it changed (PC-09 regenerated).
- **Verification.** `model_checks` [10] (473 checks), `BoundsVersion.t.sol`, `TermsHashParity.t.sol`, the golden snapshot vector (nine words-sensitivity checks in Python, TypeScript and Solidity), `contracts/test/Quote.t.sol` (Q15, Q18 and the registry), `contracts/test/Successor.t.sol` (A3 and K.6), `contracts/test/Differential.t.sol`.

### ADR-021 — The MandateManager is split into a manager, a usage ledger, a successor validator and a signature gateway; there is no delegatecall (New; closes F-12 for the size)
- **Context.** The first complete manager measured **34,067 bytes** of runtime code; EIP-170 allows 24,576 and the target of this revision is 22,000 with the optimizer settings frozen (0.8.24, cancun, optimizer 200 runs, no via-IR; `contracts/frozen-settings.json`).
- **Decision.** Four contracts, joined by typed calls to addresses fixed at deployment (predicted CREATE addresses, asserted by the deployment test); **no `delegatecall`, no `callcode`, no generic call, no proxy, no upgrade path**. `MandateManager` (21,357 bytes) is the only contract that writes mandate state: mandates, lineages, the exposure index, the nonces, the pause bits, and the structural checks and effects of `activate`, `activateSuccessor`, `reduce`, `updateAccountPin`, `revoke`, `retire`, `pause` and `resume`; it keeps the terms as a hash plus the data that exits need. `UsageLedger` (4,511) holds the usage counters, the windows, the cadence and the settled cycles; only the manager can write there, in `consume`. `SuccessorValidator` (13,059) holds the predicates of `activateSuccessor` that read state and write none and is called with STATICCALL. `MandateGateway` (16,399) verifies the customer's EIP-712 signatures (the signed domain still names the **manager** as the verifying contract), spends the nonce at the manager and calls it as the customer's relay; it holds no state. `MigrationQueue` (ADR-022) may call `activateSuccessor` and nothing else. A function of the manager that takes `customer` first accepts the customer or the gateway as caller; the exits (`revoke`, `pause`) work for the customer directly and never depend on another contract.
- **Cross-contract invariants** stay where the write is: one active mandate per lineage and the continuation of the lineage constants (in `_applySuccessor`, whatever the validator said); the exposure index changes only with the mandates that it counts, with a hard `ExposureLimit` guard in the index itself; a nonce is spent in the same transaction that uses it; a counter moves only if the manager authorized the charge in the same transaction; `consume` runs only for the bound router and moves no tokens.
- **Alternatives.** More optimizer runs or via-IR (rejected: the settings are frozen and via-IR changes the code that is audited); proxies or delegatecall libraries (rejected: generic delegatecall); fewer features (rejected: the exits, the pin updates and the revision are required).
- **Consequences.** More contracts in the audit scope ([16 §8.1](16-freeze-decision-report.md)); one cross-contract call more on a charge (about 3,000 gas) and on a signed message; the gateway is trusted exactly as much as the signature code was when it was inside the manager.
- **Verification.** `contracts/test/Deployment.t.sol` (every runtime at most 22,000 bytes and far under EIP-170), `Invariants.t.sol` (stateful fuzz of the real contracts), the role and exit tests, `tools/contracts_report.py` (opcode scan: no DELEGATECALL, CALLCODE or SELFDESTRUCT in any runtime).

### ADR-022 — A bounded, resumable migration plan replaces the single large batch; `MAX_BATCH` is provisionally 10 (New; closes F-12 for the gas)
- **Context.** The model measured a batch of 50 successors at 28.7 million gas (F-12); on the real contracts a worst-case successor costs 545,000 to 605,000 gas and about 4,000 bytes of calldata, so 50 would cost about 30 million gas, more than the per-transaction cap that EIP-7825 sets (16,777,216; an assumption about the launch chains).
- **Decision.** `MigrationQueue` is a state machine (`OPEN → DONE | ABORTED | EXPIRED`). The customer opens a **plan** with one transaction: the plan commits to the ordered list of `SuccessorAuthorization`s as a hash chain (`head(i) = keccak256(PLAN_ENTRY_TAG, hashStruct(auth(i)), head(i+1))`, `head(count) = 0`), one word of storage whatever the length. **Anyone** may then execute the plan in **steps of at most `MAX_BATCH` entries**, in any number of transactions; a step that fails changes nothing; the customer may **skip** an entry that can never execute, **abort** the plan, and the plan **expires** at the customer's deadline. Each entry goes through `activateSuccessor` with every predicate of [12 §5.3](12-router-lifecycle-and-migration.md) (A2, A3, L1, R1 to R3, X1, K1, G1, X2, C1 or C2, O1N or O1E): the queue relaxes none and writes no mandate state. The customer authorizes the plan by sending `open`; each entry binds its lineage, predecessor, terms, router, pin and snapshot, so a stepper chooses when, never what. **`MAX_BATCH` is provisionally 10** (PC-04, range [4, 20]): a step of ten worst-case entries costs about 6.5 million gas, 39% of the cap and 78% of the half-cap that the guard test enforces. A plan opened by relayed signature would need a typed plan message that types.json does not have and is **not** built; a relayer that holds per-entry signatures uses `MandateGateway.activateSuccessorBySig`.
- **Alternatives.** A fixed batch function with a lower bound (rejected: a customer with 30 lineages would sign three batches, and a failed entry would revert the others); one signed message per entry (kept for relayers, rejected as the only path); a plan signed by typed data (deferred: it expands the specification).
- **Consequences.** An emergency migration of more than ten lineages takes several steps, during which the unmigrated siblings are unfunded (the lockdown already removed their allowance): the planner must say so before the customer signs ([12 §5.3.1.2](12-router-lifecycle-and-migration.md)); the same constant bounds the pin batches of the gateway.
- **Verification.** `contracts/test/Queue.t.sol` (order, tampering, resumption, skip, abort, expiry, authority), `contracts/test/Gas.t.sol` (the measurement and the guard), MIG-TV-18 and MIG-TV-38 on the model with the new constant. **Not measured:** the chains themselves (RP-19).

### ADR-023 — The quote-signer sets are a registry of their own, with a bounded size (PC-19) and an O(1) check (New)
- **Context.** The members of a set are looped over when a set is proposed and when it is activated; no document bounded them (F-04), and the registry of tokens already carries the bounds history.
- **Decision.** `SignerSetRegistry` is separate from `TokenPolicyRegistry`; a set has at most **`MAX_SIGNERS_PER_SET` = 16** members (PC-19, proposal; range [2, 64]), refused before any loop runs, so that the activation of a replacement set (the emergency rotation) cannot run out of gas. The check that runs on every charge, `verifySigner` (Q1 and Q13), reads the tombstone, the set and the membership flag and **never loops**: its gas is the same for a set of 1, 2, 8 and 16 members. The guardian can remove a key (no grace, permanent tombstone) and stop a set, never add one; a key removed after a proposal cannot join at activation.
- **Consequences.** [06 §4](#4-contract-architecture-outline-full-spec-in-part-d) lists the signer sets under `TokenPolicyRegistry`: the implementation separates them; the audit scope changes accordingly.
- **Verification.** `contracts/test/Registries.t.sol` (the bound, rotation, tombstones, O(1) asserted by equal cold gas for four sizes), `SignerSet.t.sol` and CAP-TV-23…32 on the model.
