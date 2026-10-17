# 12 — Router Lifecycle and Migration Protocol (mandate lineage)

| Field | Value |
|---|---|
| Artifact | FP-PRO-004 (completes ADR-001) |
| Version | 0.5.0 — **shared Permit2 allowance: normal and emergency migration defined separately, on-chain exposure index, sibling mandates**; (0.4: exact `activateSuccessor` predicates, migration snapshot and containment proof, atomic and legacy flows, router-independent cycle identity; 0.3: `rebindRouter` withdrawn, migration is **mandate lineage**) |
| Status | DRAFT — protocol decided by sponsor directive and corrections (2026-10-13); parameters are proposals (OD-026); **not frozen** ([16](16-freeze-decision-report.md)) |
| Owner | Principal Blockchain Architect (protocol), Principal PM (campaigns), Incident Ops Lead (communications) |
| Reviewers | Head of Security, Head of Compliance, Solidity Lead, Product Designer, Payments Core lead |
| Dependencies | [02](02-source-register.md) CLM-026, 050, 052; [04](04-context-and-trust-boundaries.md); [05](05-evm-authorization-decision-tree.md) §2.1; [06](06-initial-architecture.md) ADR-001, ADR-009, ADR-015; [11](11-dual-cap-model.md); [13](13-eip7702-delegation-inspection.md); [17](17-account-compatibility-policy.md); [tools/eip712_vectors.py](tools/eip712_vectors.py) |
| Labels | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` `PRIVACY-CRITICAL` `LEGAL-REVIEW-REQUIRED` (notice duties) |
| Definition of Done | Every predicate of §5.3 has a passing and a failing fork test; containment is fuzzed against the monotone-authority lemma (§5.3.3); every transition of the state machine in §5 has a guard, an event and a fork test; the partial states of §5.5 are reproduced; the revocation flows of [05 §2.1](05-evm-authorization-decision-tree.md) are verified for every supported token and wallet; a rehearsal on testnet and a canary drill are complete; communications are approved; the rehearsals show zero stranded mandates. |

## 0. What changed from v0.2

| v0.2 | v0.3 |
|---|---|
| One mandate id; `routerOf` changed in place by a customer-signed consent | **A mandate is bound to one router for life.** Migration creates a **successor mandate** with a new id in the same **lineage** |
| Counters and cycle records stayed on the same record | Counters, windows, totals and cycle records are keyed by **`lineageId`**, so they survive every successor |
| Consent was a "rebind" message | **A new router-specific customer authorization** (typed data naming the new router, its version, code hash and the predecessor) |
| Old-permission revocation was step S3 after the rebind, unverified | **Explicit revocation of the old router permission is a precondition**, checked on chain; the predecessor is revoked as `SUPERSEDED` in the same transaction |
| Zero-amount `permit` listed as a gasless revocation | **Experimental**; primary revocation flows are transactions ([05 §2.1](05-evm-authorization-decision-tree.md)) |
| `exportOut` / `importFrom` hooks in `MandateManager` | **Removed from v1** (no dormant code): a new manager is adopted with a new mandate carrying remaining-headroom caps (§5.7) |

### 0.1 What changed from v0.3 to v0.4

| v0.3 | v0.4 |
|---|---|
| `activateSuccessor` described in prose with a five-step check list | **Exact boolean predicates** A1…O1 with error names, effects, postconditions and a requirement-to-predicate table (§5.3) |
| Old permission "unusable" = `amount == 0 or expiration <= now` | Corrected to Permit2's rule: unusable iff `amount = 0 ∨ expiration < now` (usable in the block whose timestamp equals the expiration) |
| "Terms contained" without a definition | A **migration snapshot** computed on chain; containment clauses K.1…K.9 for expiry, merchant scope, token scope, caps and remaining caps, fee cap and slippage cap; a monotone-authority lemma (§5.3.2–5.3.3) |
| Consent covered terms and router | Consent also covers the **static terms snapshot hash**, the **account pin** and, for a revision, a **widened mask** |
| `lineageId` = id of generation 0; cycle identity implicit | `lineageId`, `mandateId`, `cycleId` and `paymentId` derived without any router input ([11 §3.1](11-dual-cap-model.md)); cycle identity bound to the lineage (§5.3.5) |
| Atomic and sequential transports described together | Separate **atomic flow** (§5.4.1) and **legacy flows** (§5.4.2) with state tables; the shared Permit2 allowance (sibling lineages) is explicit (§5.3.1) |
| No statement about overlapping authority | `AuthRouters(L)` and the no-overlap claim `I-MIG-8` (§5.5) |

### 0.2 What changed from v0.4 to v0.5

| v0.4 | v0.5 |
|---|---|
| Predicate O1 required the customer's Permit2 allowance to the old router to be zero or expired for every token of the predecessor, as if the allowance belonged to the mandate | A Permit2 allowance is keyed `(owner, token, spender)` ([§5.3.1](#531-the-shared-allowance-facts-modes-and-the-exposure-index)): **it is shared by every mandate of the customer on that router that uses the token**. O1 is split into **O1N** (normal migration: the allowance may remain while a sibling mandate relies on it, must be gone once none does) and **O1E** (emergency migration: every exposed token's allowance must be unusable) |
| One `kind` for every migration | `kind ∈ {MIGRATION_NORMAL, MIGRATION_EMERGENCY, REVISION}`; the mode is **derived from the router's registry state**, not chosen by the caller (R3) |
| Siblings of a lineage on the old router were unfunded by S2 and put on hold; a plan for a subset only warned | A normal plan **never unfunds a sibling**; the planner refuses a `lockdown` pair that a sibling still needs (NC-20); the contract keeps an **exposure index** (`liveCount[customer][router][token]`) so that "no sibling remains" and "every exposed token" are verified on chain |
| Account pin was one `bytes32` | A typed `AccountPin` struct ([17 §5](17-account-compatibility-policy.md)); K1 checks well-formedness, the live account and the pin version |
| Invariants I-MIG-1…9 | I-MIG-7 rewritten; **I-MIG-10** (exposure index is never an under-count) and **I-MIG-11** (activation does not touch Permit2 or any sibling) added; MIG-TV-30…45 |

## 1. Principles

1. **`PaymentRouter` is immutable and versioned** (ADR-001). A router version never changes; a new version is a new contract at a new address.
2. **A mandate is bound to exactly one router for its whole life.** The binding is part of what the customer signed.
3. **Migration is lineage, not mutation.** A successor mandate links to its predecessor (`predecessorId`, `generation`), shares its `lineageId`, and inherits its usage. Only the customer can create it, and only with an authorization that names the new router.
4. **Migration never widens anything.** For a migration the successor's terms are contained in a snapshot of the predecessor's, computed on chain: expiry, merchant scope, token scope, every remaining cap, the fee cap and the slippage cap cannot increase (§5.3.2–5.3.3). Changing terms is a *revision* (§5.6) and needs fresh consent for the new terms, with the widened dimensions signed.
5. **The old permission is cleaned up as far as it can be, and never at a sibling's expense.** A Permit2 allowance belongs to `(customer, token, router)`, not to a mandate. *Mandate-level* authority of the old router over the predecessor ends by revocation in the same transaction (Post2). *Allowance-level* exposure is handled in two modes: in **normal** migration (the old router is still trusted) the allowance may remain while a sibling mandate of the customer relies on it and must be zero or expired once none does (O1N); in **emergency** migration (the old router is disabled, sunset, retired or security-deprecated) every token the customer's mandates use on that router must be unusable first (O1E). FastPay cannot revoke an allowance for the customer; the contract verifies the result.
6. **Customers can always leave.** Revoke and pause of any mandate, and creation of a successor to a bindable router, are never blocked by router status, pause, sunset or governance (TM-14, `I-MIG-4`).
7. **Stranded mandates are prevented by design**: on-chain minimum notice, a migration path that is live and rehearsed before any deprecation, and a fail-safe (no charges) for unmigrated mandates.
8. **Migration is a prime phishing pretext.** Every message and screen assumes an attacker will imitate it (§11.4).

## 2. Components

| Component | Role in migration | Mutable? |
|---|---|---|
| `RouterRegistry` | Router versions, code hashes, audit commitments, lifecycle, immutable notice minimums, `isBindable`, shared `markSettled(paymentId)` for Pay Once | Immutable code; governance-timelocked state; guardian can only emergency-disable |
| `MandateManager` | Mandates, **lineages**, lineage counters and cycle records, `activateSuccessor`, pause bits | Immutable |
| `PaymentRouter` vN | Charges only for the **active mandate of a lineage that is bound to it**, while the registry says it is chargeable | Immutable |
| Permit2 | Per-token allowance to a specific router address (L2); the old one must be unusable | External, immutable |
| Migration orchestrator (Mandate module) | Campaigns, cohorts, notices, plans, holds, metrics | Deployable code |
| Flag `router.<n>.newMandates.enabled` | Backend gate; the registry lifecycle is the real boundary | Flag service |

## 3. Router lifecycle

```text
 CANDIDATE --(timelock + checks)--> ACTIVE --(deprecate, notice)--> DEPRECATED --(sunsetNotBefore reached)--> SUNSET --(retention)--> RETIRED
     |                                |                                  |
  CANCELLED                           +---------- emergencyDisable (guardian, immediate) ----------+--> DISABLED_EMERGENCY
                                                                                                      (governance can clear after timelock)
```

| State | New mandates may bind? | Charges? | Revoke / pause / create a successor **away** from it? | Successor **to** it? |
|---|---|---|---|---|
| CANDIDATE | No | No | n/a | No |
| ACTIVE | Yes | Yes | Yes | Yes |
| DEPRECATED | No | **Yes** | Yes | Only within the rollback window (§10) |
| SUNSET | No | **No** | **Yes** | No |
| DISABLED_EMERGENCY | No | **No** | **Yes** | No |
| RETIRED | No | No | **Yes** | No |

| Transition | Who | Guards | Event |
|---|---|---|---|
| propose → CANDIDATE | Governance (timelock) | Deployed code hash equals the supplied hash; `auditRefHash` non-zero; immutables read back; at most **2** routers in {ACTIVE, DEPRECATED} per chain after activation | `RouterProposed` |
| cancel → CANCELLED | Governance | Only from CANDIDATE | `RouterCancelled` |
| activate → ACTIVE | Governance | Timelock elapsed; release-gate evidence recorded off chain (RG-015 for non-first routers) | `RouterActivated` |
| deprecate → DEPRECATED | Governance (timelock) | Successor is ACTIVE; `sunsetNotBefore ≥ now + MIN_NOTICE_STANDARD` (180 days, PROPOSAL); notice commitment supplied | `RouterDeprecated(router, successor, sunsetNotBefore, noticeHash)` |
| deprecate (security) | Governance (timelock) | As above but `≥ MIN_NOTICE_SECURITY` (60 days, PROPOSAL) and a security-notice hash | `RouterDeprecated` with `reason = SECURITY` |
| extend sunset | Governance | Only later dates | `RouterSunsetExtended` |
| sunset → SUNSET | Governance | `now ≥ sunsetNotBefore` | `RouterSunset` |
| retire → RETIRED | Governance | In SUNSET for ≥ `RETENTION` (365 days, PROPOSAL) | `RouterRetired` |
| emergencyDisable | **Guardian** | Reason code mandatory; guardian cannot undo | `RouterEmergencyDisabled` |
| clearEmergency | Governance (timelock) | Restores the previous state; evidence recorded | `RouterEmergencyCleared` |

`MIN_NOTICE_STANDARD` and `MIN_NOTICE_SECURITY` are **immutable constants**: governance can lengthen notice, never shorten it. The only fast path is the guardian's emergency disable, which **stops** charges but never blocks exits.

## 4. The lineage model

```text
Lineage { lineageId, anchorStartsAt, periodSeconds, merchantId, subscriptionRef, recipientPolicy, currency,
          activeMandateId, generation, terminated,
          usage: windows (DAY, WEEK, THIRTY_DAYS, BILLING_PERIOD) x tokens + fiat, totals, cycleSettled[cycleIndex] -> (settledAt, quoteDigest) }
Mandate { mandateId, lineageId, predecessorId, generation, customer, router, terms..., termsHash, parentSnapshotHash,
          accountPinHash, pinVersion, maxFeeBps, extensionsHash (must be 0 in v1.0), pause bits {customer, risk, delegation}, status, revokedReason, retired }
ExposureIndex (MandateManager, keyed by customer) { live[router][token] : uint32, exposed[router] : enumerable set of tokens (<= MAX_EXPOSED_TOKENS_PER_ROUTER) }
```

The mandate stores the **hash** of its `AccountPin` and the pin version; the pin struct travels in events and in the calldata of `consume` ([17 §5](17-account-compatibility-policy.md)). The exposure index is the manager's own record of which routers and tokens each customer's live mandates rely on (§5.3.1); it is what makes the shared Permit2 allowance checkable on chain.

- **Identifiers** ([11 §3.1](11-dual-cap-model.md)): `lineageId = keccak256(abi.encode(LINEAGE_TAG, chainId, manager, customer, merchantId, subscriptionRef, creationNonce))`; `mandateId = keccak256(abi.encode(MANDATE_TAG, lineageId, generation))`; `cycleId` and `paymentId` contain no router input.
- **Lineage constants** (`merchantId`, `subscriptionRef`, `anchorStartsAt`, `periodSeconds`, `recipientPolicy`, `currency`) are fixed at creation and copied into every generation. A different merchant, subscription or billing period is a new lineage.
- **Counters live in the lineage.** Windows are anchored at the lineage's first `startsAt`, so successors keep the same window grid and cannot reset a cap. Totals carry over. This is what "preserve counters" means: one set of numbers, many mandates.
- **Cycle records live in the lineage**, keyed `(lineageId, cycleIndex)`: a cycle settled under generation *n* or under router A cannot settle again under *n+1* or router B (`I-ONCE`, ADR-009, §5.3.5).
- **History** is preserved by the chain of `predecessorId` pointers, `parentSnapshotHash` and the `MandateSuperseded` events (verifiable on chain), and by `mandate_lineages` and `mandate_generations` tables off chain.
- **Exactly one mandate in a lineage is active** at any time (`lineage.activeMandateId`); `consume` accepts only that mandate and only from the router it is bound to.

## 5. Migration state machine

### 5.1 Mandate and lineage states

On chain, a mandate has `status ∈ {ACTIVE, REVOKED(reason), EXPIRED, EXHAUSTED}` and three independent pause bits; derived names follow the prompt's state list plus one:

| Derived state | Condition |
|---|---|
| `ACTIVE` | status active, no pause bit, router chargeable, within time |
| `PAUSED_BY_CUSTOMER` | customer bit |
| `PAUSED_BY_RISK` | risk bit |
| `DELEGATION_UNVERIFIED` | delegation bit ([17](17-account-compatibility-policy.md), [13 §7](13-eip7702-delegation-inspection.md)) |
| `MIGRATION_REQUIRED` | router not chargeable (SUNSET or DISABLED_EMERGENCY) or an unhonorable token-policy change |
| `REVOKED` | reason `CUSTOMER`, `SUPERSEDED_MIGRATION`, `SUPERSEDED_REVISION`, `MANAGER_REPLACED` |
| `EXPIRED`, `EXHAUSTED` | time or total cap |

```text
                          router A DEPRECATED (notice)                  router A SUNSET / DISABLED_EMERGENCY
  [gen n ACTIVE on A] ---------------------------------> [gen n ACTIVE,                 ---------------------> [gen n MIGRATION_REQUIRED]
         |                                                  migration recommended]                                   |
         |   customer starts a migration plan (S1: grant L2 to B)                                                       |
         v                                                                                                              v
   [Q1 prepared: L2(B) granted, gen n still funded and charging] --- S2: revoke L2(A) for the pairs the mode needs ---> [Q2 old unfunded;
                                                                      (none at all if siblings share every token)         backend hold]
                                                                                                         |
          S3: activateSuccessor(B)  (SuccessorOK: O1N or O1E on the shared allowance, B bindable, terms contained, pin holds)  |
                                                          v                                              |
                [Q3 complete: gen n+1 ACTIVE on B;  gen n REVOKED(SUPERSEDED_MIGRATION);  lineage.active = gen n+1] <---+
```

Router A in **normal** mode (ACTIVE, or DEPRECATED for a standard reason) → kind `NORMAL`; router A in **emergency** mode (SECURITY deprecation, DISABLED_EMERGENCY, SUNSET, RETIRED) → kind `EMERGENCY` (§5.3.1).

### 5.2 Transitions

| # | From | To | Actor | Guard | On-chain event | Off-chain |
|---|---|---|---|---|---|---|
| T1 | gen n `ACTIVE` | gen n `ACTIVE`, router `DEPRECATED` | Governance | §3 guards | `RouterDeprecated` | Notices start; campaign created |
| T2 | gen n `ACTIVE`/`PAUSED_*` | gen n `MIGRATION_REQUIRED` | Governance / guardian | Router SUNSET or DISABLED_EMERGENCY | `RouterSunset` / `RouterEmergencyDisabled` | `mandate.migration_required` webhook |
| T3 | gen n | Q1 | Customer | Plan issued; new L2 granted | Permit2 `Approval`/`Permit` | Plan state `PREPARED` |
| T4 | Q1 | Q2 | Customer | The old L2 pairs the mode requires are revoked by a **primary flow** ([05 §2.1](05-evm-authorization-decision-tree.md)): all exposed tokens (`NORMAL_FULL`, `EMERGENCY`) or only the tokens no sibling uses (`NORMAL_PARTIAL`); skipped when there is none | Permit2 `Lockdown` or `Approval` | **Backend hold** `MIGRATION_IN_PROGRESS` for every lineage the lockdown unfunded (no charge attempts, no dunning) with a 24 h TTL |
| T5 | Q2 (or Q1 if the required old L2 pairs were already unusable, or none is required) | Q3 / Q3s | Customer (tx or signature) | `SuccessorOK` (§5.3), all predicates | `MandateSuperseded`, `MandateActivated` | Verification V1–V6 |
| T6 | Q3 gen n+1 | gen n+1 `PAUSED_*` bits inherited | — | Successor **inherits all pause bits** of the predecessor; the customer must resume explicitly | — | — |
| T7 | gen n+1 `ACTIVE` | gen n+2 on router A' (reverse or forward) | Customer | Same as T3–T5; target bindable (rollback window applies to DEPRECATED) | `MandateSuperseded` | Rollback or next migration |
| T8 | any gen | lineage `TERMINATED` | Customer / time / cap | Active mandate revoked, expired or exhausted | `MandateRevoked` / derived | Lineage closed |
| T9 | Q1/Q2 | back to gen n charging | Customer | Customer re-grants L2(A) (if revoked) and abandons | Permit2 `Approval` | Hold released; plan `ABANDONED` |

### 5.3 `activateSuccessor`: exact predicates

**Notation.** `now = block.timestamp`. `C` the customer. `L` the lineage. `P` the predecessor mandate, `Rold = P.router`, `T = P.tokens`. `N` the new mandate, `Rnew = N.router`, `TN = N.tokens`. `reg` the `RouterRegistry`, `p2` Permit2. `kind ∈ {NORMAL, EMERGENCY, REVISION}` (stored as `uint8` 0, 1, 2 in the typed data); `MIGRATION ≡ kind ∈ {NORMAL, EMERGENCY}`. `E(x) = ∞ if x = 0, else x` (a cap of 0 means "no cap in this family"). `Usable(C,t,R) ≡ let (a,e,·) = p2.allowance(C,t,R) in a > 0 ∧ now ≤ e` and `Unusable ≡ ¬Usable`, i.e. **`a = 0 ∨ e < now`** (Permit2's `transferFrom` reverts with `AllowanceExpired` only when `block.timestamp > expiration`, so an allowance stays usable in the block whose timestamp equals its expiration; `AllowanceTransfer.sol:79` at the pinned commit of [16 §5](16-freeze-decision-report.md); `uint160.max` is unlimited and counts as usable). `Bounded(C,t,R) ≡ a(C,t,R) < 2¹⁶⁰ − 1` (the allowance is not the unlimited sentinel).

**Exposure notation** (defined in §5.3.1): `live(C,R,t)` is the manager's own count of live mandates of `C` bound to router `R` that use token `t`; `Sib(t) ≡ live(C,Rold,t) − 1` for `t ∈ T` is the number of **other** live mandates of `C` (siblings, in this or any other lineage) that rely on the same Permit2 allowance `(C,t,Rold)`; `Exposed(C,R) = { t : live(C,R,t) > 0 }`. `Mode(R)` is the migration mode of router `R`, derived from the registry (§5.3.1).

**Typed data** (domain `"FastPay Mandates"`, version `"1"`, `chainId`, `verifyingContract` = `MandateManager`; `AccountPin` is the nested struct of [17 §5.1](17-account-compatibility-policy.md)):

```text
SuccessorAuthorization(address customer,bytes32 lineageId,bytes32 predecessorId,uint8 kind,bytes32 newTermsHash,
                       address newRouter,bytes32 newRouterCodeHash,uint32 newRouterVersion,bytes32 termsSnapshotHash,
                       uint32 widenedMask,AccountPin accountPin,uint64 deadline,uint256 nonce)
AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,
           bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)
```

**Predicates** (each reverts with the named error; the order is the order of evaluation):

| ID | Predicate | Error |
|---|---|---|
| A1 AUTH | `msg.sender = C ∨ AUTH(C, digest(auth), P.accountPin)`: a signature is accepted by the path and only on the conditions of [17 §5.4](17-account-compatibility-policy.md) (signature mode of the **predecessor's** pin; the ERC-1271 path also needs the predecessor's pin to hold on the live account) | `NotCustomer`, `SignatureModeNotPermitted` |
| A2 FRESH | `now ≤ auth.deadline ∧ ¬used[C][auth.nonce]`; sets `used` | `AuthorizationExpired`, `AuthorizationReplayed` |
| A3 BIND | `auth.lineageId = L ∧ auth.predecessorId = P.id ∧ auth.kind = kind ∧ auth.newTermsHash = hashStruct(N.terms) ∧ auth.newRouter = Rnew ∧ auth.newRouterCodeHash = reg.codeHash(Rnew) ∧ auth.newRouterVersion = reg.version(Rnew) ∧ hashStruct(auth.accountPin) = hashStruct(N.accountPin) ∧ auth.termsSnapshotHash = termsSnapshotHash(P) ∧ auth.customer = C` | `AuthorizationMismatch` |
| L1 LINEAGE | `L.activeMandateId = P.id ∧ P.lineageId = L ∧ P.customer = C ∧ ¬terminal(P) ∧ ¬L.terminated ∧ N.lineageId = L ∧ N.customer = C ∧ N.generation = P.generation + 1` | `WrongPredecessor` |
| R1 BINDABLE | `reg.isBindable(Rnew)` | `RouterNotBindable` |
| R2 KIND | `MIGRATION ⇒ Rnew ≠ Rold`; `kind = REVISION ⇒ Rnew = Rold` | `WrongKind` |
| R3 MODE *(MIGRATION)* | `Mode(Rold) = EMERGENCY ⇒ kind = EMERGENCY` (a customer may choose `EMERGENCY` while the router is still in normal mode: it is strictly more demanding, so it is allowed; the reverse is refused) | `ModeMismatch` |
| X1 EXT | `N.extensionsHash = 0 ∧ P.extensionsHash = 0` | `ExtensionsNotSupported` |
| K1 ACCOUNT | `PIN_WELLFORMED(N.accountPin) ∧ PIN_OK(C, N.accountPin) ∧ N.accountPin.pinVersion = nextPinVersion(L, N.accountPin)` ([17 §5](17-account-compatibility-policy.md)) | `AccountPinMalformed`, `AccountPinMismatch`, `PinVersionMismatch` |
| G1 NEWPERM | `∀ t ∈ TN: let (a,e,·) = p2.allowance(C,t,Rnew) in a ≥ N.perPaymentMax[t] ∧ now ≤ e` (the new router is funded for at least one payment; funding for the whole horizon and for siblings is a planner duty, §5.3.1) | `NewPermissionMissing(t)` |
| X2 EXPOSURE | `\|Exposed(C,Rnew) ∪ TN\| ≤ MAX_EXPOSED_TOKENS_PER_ROUTER` (PC-18) | `ExposureLimit` |
| C1 CONTAIN *(MIGRATION)* | `Contained(N, snapshot(P))` (§5.3.2) `∧ auth.widenedMask = 0` | `TermsNotContained` |
| C2 REVISE *(REVISION)* | lineage constants equal (`merchantId`, `subscriptionRef`, `periodSeconds`, `anchorStartsAt`, `recipientPolicy`, `currency`) `∧ auth.widenedMask = widened(N, snapshot(P))` (§5.6) | `LineageConstantsChanged`, `WidenedMaskMismatch` |
| O1N OLDPERM-NORMAL *(kind NORMAL)* | `∀ t ∈ T: ( Sib(t) = 0 ⇒ Unusable(C,t,Rold) ) ∧ ( Sib(t) > 0 ⇒ Bounded(C,t,Rold) )`: **the allowance may stay for a sibling, and must go once no sibling uses the token** | `OldPermissionNotRevoked(t)`, `ResidualAllowanceUnbounded(t)` |
| O1E OLDPERM-EMERGENCY *(kind EMERGENCY)* | `∀ t ∈ Exposed(C,Rold): Unusable(C,t,Rold)`: **every token any live mandate of `C` uses on the old router, not only the predecessor's tokens** | `OldPermissionNotRevoked(t)` |

```text
SuccessorOK(kind)  ≡  A1 ∧ A2 ∧ A3 ∧ L1 ∧ R1 ∧ R2 ∧ X1 ∧ K1 ∧ G1 ∧ X2
                      ∧ ( MIGRATION ⇒ R3 ∧ C1 )  ∧  ( kind = NORMAL ⇒ O1N )  ∧  ( kind = EMERGENCY ⇒ O1E )
                      ∧ ( kind = REVISION ⇒ C2 )
```

**Effects** (only if `SuccessorOK`, all in the same transaction): E1 `P.status := REVOKED(SUPERSEDED_MIGRATION | SUPERSEDED_REVISION)`; E2 `L.activeMandateId := N.id`; E3 create `N`: `ACTIVE`, `generation = P.generation + 1`, `predecessorId = P.id`, pause bits copied from `P`, `parentSnapshotHash = auth.termsSnapshotHash`, `bounds snapshot = intersection(current bounds, P's snapshot)`; E4 mark the authorization nonce used; E5 emit `MandateSuperseded(lineageId, predecessorId, newId, kind, Rold, Rnew, termsSnapshotHash, usageDigest, authorizationHash)` and `MandateActivated`; E6 **update the exposure index**: `live(C,Rold,t) −= 1` for `t ∈ T`, then `live(C,Rnew,t) += 1` for `t ∈ TN` (for a revision `Rold = Rnew` and the net change is the difference of the token sets). Lineage counters and cycle records are not touched (`I-MIG-3`). **No call to Permit2 other than `allowance` views is made, and no sibling mandate is read for writing** (`I-MIG-11`).

**Postconditions** (proved in §5.3.3 and §5.5; each is also an invariant test):

| ID | Postcondition |
|---|---|
| Post1 | `P.status = REVOKED ∧ L.activeMandateId = N.id`; exactly one `ACTIVE` mandate in `L` (`I-MIG-1`) |
| Post2 | `∀ r: ¬Consumable(r, P)` and `∀ r ≠ Rnew: ¬Consumable(r, N)`, where `Consumable(r,m) ≡ m.status = ACTIVE ∧ ¬m.retired ∧ now < m.expiresAt ∧ L.activeMandateId = m.id ∧ m.router = r ∧ no pause bit ∧ PIN_OK` — **the old router cannot execute the old mandate, and no router but the new one can execute the new one; this holds whatever the shared Permit2 allowance is** |
| Post3N | *(NORMAL)* `∀ t ∈ T: live(C,Rold,t) = 0 ⇒ Unusable(C,t,Rold)` and `live(C,Rold,t) > 0 ⇒ Bounded(C,t,Rold)` — **no usable old allowance remains for a token that no live mandate of the customer uses on the old router; a remaining one is bounded and serves only the siblings** |
| Post3E | *(EMERGENCY)* `∀ t ∈ Exposed(C,Rold) (before the call): Unusable(C,t,Rold)` — **the customer has no usable Permit2 allowance to the old router for any token any of their mandates uses there** |
| Post4 | Every lineage counter and cycle record equals its value before the call (`I-MIG-3`) |
| Post5 | *(MIGRATION)* `Auth(N) ⊆ Auth(P)`: no payment is acceptable under `N` that is not acceptable under `P` (§5.3.3, `I-MIG-9`) |
| Post6 | Every Permit2 allowance, every sibling mandate and every sibling lineage is unchanged; `live` changed exactly as E6 says (`I-MIG-11`) |

**How the predicates answer the requirements**

| Requirement | Predicates and effects |
|---|---|
| Revoke the old business mandate | E1 (same transaction as the activation) |
| Prove the old router cannot execute it | Post2: from E1/E2 and the single-active rule; independent of Permit2 |
| Prove what can be proved about the old Permit2 allowance, **given that it is shared** | O1N (last-lineage cleanup, bounded residual) and O1E (full revocation in emergencies), Post3N / Post3E; nothing is claimed per mandate |
| Never unfund a sibling in a normal migration | O1N allows the allowance to remain; Post6 (no Permit2 write); the planner refuses a `lockdown` that a sibling needs (NC-20) |
| Grant a new router-specific authorization | A3 (the typed data names `newRouter`, its code hash and version) and G1 (a usable Permit2 allowance to `Rnew`) |
| Create a successor mandate revision with lineage | E3, L1, R2, kind `NORMAL`, `EMERGENCY` or `REVISION` |
| Prevent overlapping authority | L1 with E1/E2 (one active mandate per lineage), O1N/O1E, §5.5 |
| Never widen | C1 and §5.3.3 |

#### 5.3.1 The shared allowance: facts, modes and the exposure index

**Facts about Permit2** (read at `Uniswap/permit2` commit `cc306b601f172c51bc04334a109e98340456620b`, the commit tagged `0x000000000022D473030F116dDEE9F6B43aC78BA3`; evidence **E1, pinned**: an automated read with file and line citations, human review at E2 still to be done; [16 §5](16-freeze-decision-report.md)). The design depends on each of these, and each has a fork test (RV-T, MIG-TV):

| Fact | Source at the pinned commit | Consequence |
|---|---|---|
| F1 The allowance is stored under `allowance[owner][token][spender]` | `AllowanceTransfer.sol:23` | **One allowance serves every mandate of the customer on that router for that token.** The router, not the mandate, is the spender |
| F2 `approve` **overwrites** amount and expiration of that slot | `AllowanceTransfer.sol:26-30`, `libraries/Allowance.sol:34-42` | Granting a new mandate (or a top-up) on the same router **changes the funding and expiry of every sibling**: a smaller amount or earlier expiry starves them; the planner must size from the sum (§5.3.1.5) |
| F3 `lockdown` sets only `amount` to 0, for each named `(token, spender)`; expiration and nonce stay | `AllowanceTransfer.sol:97-110` | A lockdown for one mandate's token **unfunds every sibling using that token** on that router |
| F4 `transferFrom` reverts `AllowanceExpired` iff `block.timestamp > expiration`; it decrements the amount unless it is `uint160.max` | `AllowanceTransfer.sol:76-94` | Boundary of `Usable`; siblings **share one decreasing budget**: a charge of one consumes the funding of the others |
| F5 `approve` and `permit` with `expiration = 0` store `block.timestamp` | `libraries/Allowance.sol:24, 39-41` | An allowance written with 0 is usable only in that block |
| F6 `permit` writes the same slot, checks `sigDeadline`, verifies the signature (ERC-1271 for any signer with code; no `ecrecover` fallback), then the nonce | `AllowanceTransfer.sol:33-40, 131-142`, `libraries/SignatureVerification.sol:21-46` | A stale signed permit can re-grant the allowance after S2 (Q2 → Q1, §5.5) |

**Router mode.** The registry derives the mode from the router state (`reason` is recorded by `deprecate`, §3):

| `reg.state(R)` | `Mode(R)` | Why |
|---|---|---|
| `ACTIVE` | `NORMAL` | The router is trusted and chargeable; siblings may rely on it |
| `DEPRECATED`, reason `STANDARD` | `NORMAL` | Still trusted and chargeable during the notice period |
| `DEPRECATED`, reason `SECURITY` | `EMERGENCY` | FastPay itself declared it unsafe; a retained allowance has exposure and, for a safe migration, no benefit |
| `DISABLED_EMERGENCY` | `EMERGENCY` | Charges stopped; the router may be defective |
| `SUNSET`, `RETIRED` | `EMERGENCY` | Not chargeable; a retained allowance serves nothing |

`Mode` is a function of registry state only; the caller cannot choose it (R3). The names are the sponsor's: *normal* migration moves a mandate off a router that is still trusted; *emergency* migration removes the customer's exposure to a router that is not.

**The exposure index.** `MandateManager` keeps, per `(customer, router, token)`, the count `live(C,R,t)` and an enumerable set `Exposed(C,R)`:

```text
live(C,R,t)  =  #{ m : m.customer = C ∧ m.router = R ∧ t ∈ m.tokens ∧ m.status = ACTIVE ∧ ¬m.retired }
```

It changes only in the same transaction as the transition that causes it: `activate*` (+1 per token), `activateSuccessor*` (E6), `revoke*` and any transition that removes a token from a live mandate (−1), and the permissionless `retire(mandateId)` for a mandate that has expired by time or is exhausted (−1; it exists because EXPIRED and EXHAUSTED are derived states that no transaction would otherwise record). `Exposed(C,R)` holds the tokens with a non-zero count and is bounded by `MAX_EXPOSED_TOKENS_PER_ROUTER` (PC-18, proposal 8): an activation that would exceed it reverts `ExposureLimit` (X2).

*Soundness.* The index is exact for statuses the contract records and **can over-count only** for mandates that expired or were exhausted and have not been retired (`I-MIG-10`). An over-count is safe: in normal mode it lets an allowance remain that no live mandate needs (residual exposure to an immutable, audited old router, bounded by Bounded and by the allowance's own expiry, ended by calling `retire`); in emergency mode it asks for one more `(token, router)` pair in the lockdown. An **under-count** would be unsafe (emergency mode could leave an allowance for a token a live sibling uses), so the index is updated before any check that reads it and is covered by an invariant test. The planner calls `retire` for expired siblings before building a plan so that the count is tight.

**5.3.1.1 Normal migration (`kind = NORMAL`)** — the old router is trusted and chargeable (ACTIVE, or DEPRECATED for a standard reason). Purpose: move one lineage without harming the customer's other lineages on the same router.

1. The predecessor is revoked in the same transaction (E1), so the old router cannot charge it (Post2) **whatever the allowance is**. This is the mandate-level guarantee.
2. For a token `t ∈ T` that **no sibling uses** (`Sib(t) = 0`) the allowance must be unusable (O1N, first half): the customer sends `Permit2.lockdown` for exactly those pairs. After the activation no live mandate of the customer uses `t` on the old router, so a usable allowance would be pure residue.
3. For a token that **a sibling still uses** (`Sib(t) > 0`) the allowance **stays**: the sibling keeps charging on the old router without interruption. The contract requires only that it is `Bounded` (not the unlimited sentinel; FastPay never asks for one, R-L2-NO-MAX). Its amount and expiry were sized by the customer for the siblings and, until now, for the predecessor; it may be larger than the siblings need. The planner offers to **right-size** it (S2′, below) but the contract does not require it.
4. When the **last** sibling migrates (or is revoked, or retired), the count reaches 0 for that token and step 2 applies: the lockdown is required. Last-lineage cleanup is therefore enforced exactly when it stops harming anyone.
5. The call writes nothing to Permit2 and touches no sibling (Post6). A sibling's status, pause bits, caps, lineage counters and funding are exactly as before; the only effect on its funding is the one the customer chooses in S1/S2/S2′.

Plan kinds produced by the planner for a normal migration:

| Plan kind | When | S1 (new router) | S2 (old router) | S3 |
|---|---|---|---|---|
| `NORMAL_FULL` | every lineage of the customer on `Rold` migrates in this plan (one plan, executed in steps of at most `MAX_BATCH` entries, ADR-022) | `approve`/`permit` on `Rnew` for each token, sized for **all** lineages that will be on `Rnew` | `lockdown` of every exposed token (no sibling remains) | `MigrationQueue.open`, then `step` until the plan is done |
| `NORMAL_PARTIAL` | some lineages stay on `Rold` | as above, sized for the sum of the lineages on `Rnew` after the plan | `lockdown` **only** the tokens with `Sib = 0`; **S2′** optional: `approve(t, Rold, siblingNeed(t), siblingExpiry(t))` for the others, computed from the siblings' needs and **never below them** (F2) | `activateSuccessor` |
| `NORMAL_PARTIAL` with no exclusive token | every token of the predecessor is shared | as above | **none** | `activateSuccessor` — there is no Q2 state and no hold |

**5.3.1.2 Emergency migration (`kind = EMERGENCY`)** — the old router is disabled, sunset, retired or security-deprecated. The question is no longer "does a sibling need the allowance" but "how does the customer stop being exposed to a router that must not be trusted". Purpose: remove the exposure **completely** and keep the customer able to leave (`I-MIG-4`).

1. The predecessor is revoked in the same transaction (E1), as before.
2. **Every** token any live mandate of the customer uses on the old router must be unusable (O1E): the exposure index supplies the complete list, so a caller cannot omit a sibling's token. One `Permit2.lockdown` call carries all `(token, Rold)` pairs.
3. Siblings stay `ACTIVE` mandates bound to the old router but are unfunded. When the router is disabled, sunset or retired they cannot charge anyway, so nothing is lost. When it is **security-deprecated** it can still charge, so the lockdown **does interrupt the siblings until their own successors exist**: this is the price of removing the exposure, it is why the default plan migrates every lineage in one plan (steps of at most `MAX_BATCH` entries, ADR-022), and the portal says so before the customer signs. Each sibling is migrated by its own `activateSuccessor` of kind `EMERGENCY`, in that plan or later; once the lockdown has been done, O1E holds for every later activation without further action, **unless the customer re-grants the old allowance** (then O1E fails again and the plan says why).
4. A customer with more than `MAX_BATCH` lineages on the router migrates them in several plan steps; a plan is a hash chain over the authorizations that the customer committed to in one transaction, anyone may execute its steps, a failed step changes nothing and the customer may skip, abort or let it expire (ADR-022); the lockdown covers all of them at once.
5. If an unsubmitted signed permit for the old router may exist (the orchestrator issued one within `sigTtlSeconds`, 900 s) the plan also calls `invalidateNonces` for each exposed token (S2″). The chain cannot see unsubmitted signatures, so this is an off-chain control.

**5.3.1.3 Siblings: what happens to each**

| Sibling situation | Normal migration of another lineage | Emergency migration of another lineage |
|---|---|---|
| Same router, shares a token with the migrating mandate | Keeps charging; its allowance is untouched (Post6); S1/S2′ for the migrating mandate are sized so that it is not starved | Unfunded by the lockdown (the router is not trusted); remains active-but-unfunded until its own successor |
| Same router, no shared token | Untouched | Unfunded if its token is exposed (it is: O1E covers every exposed token) |
| Already on another router | Untouched | Untouched |
| Expired or exhausted, not retired | Counted until `retire` (over-count, safe) | Counted until `retire` (one extra pair in the lockdown) |
| Customer-paused | Untouched; keeps its pause bit | As above |

**5.3.1.4 What the contract can and cannot verify about a shared allowance**

| The contract verifies (on chain) | Stays an off-chain control |
|---|---|
| `amount`, `expiration` of `(C, t, R)` at the activation block (view call), hence `Usable`, `Unusable`, `Bounded` | That an allowance **will stay** unusable after the activation: the customer or a stale signed permit can re-grant it (F6). For the migrated lineage this is inert (Post2); for siblings it is the customer's choice; in emergency mode it re-creates exposure and the monitor alerts (`migration.old_permission_remaining`) |
| `live(C,R,t)` and `Exposed(C,R)` (its own state) | That the allowance is **large enough for the siblings** (F2, F4): a liveness property. Raised pre-charge as `ALLOWANCE_SHORTFALL` and by the planner's sizing rule below; never a safety property because every charge is bounded by its mandate's caps |
| The router mode (registry state), so the caller cannot pick the weaker rule | That **no unsubmitted signed permit** exists for the old router (S2″) |
| The old router cannot execute the predecessor (Post2) | Allowances of spenders other than FastPay routers (out of scope) |

**5.3.1.5 Planner and orchestrator duties (R-L2-SHARED)** — implemented in both planners and checked by NC-20, NC-21 ([05](05-evm-authorization-decision-tree.md)):

1. Every `approve`/`permit` for `(C, t, R)` is computed from **all live lineages of `C` on `R` that use `t` after the plan**: `amount ≥ Σ remaining need` over the horizon (never `uint160.max`), `expiration ≥ max` of their needs; a step that would lower either below the siblings' need is refused (NC-21). This is the consequence of F2.
2. A normal plan never contains a `lockdown` or `approve(…,0,0)` for a pair that a sibling still uses (NC-20). The validator checks the plan against the on-chain `live` counts read at one block.
3. The orchestrator holds charge attempts of a lineage whose allowance is `Unusable` because of a plan in progress (`MIGRATION_IN_PROGRESS`, 24 h TTL) and raises `ALLOWANCE_SHORTFALL` instead of submitting a charge that would revert.
4. Before building a plan the planner calls `retire` for expired or exhausted siblings so that the exposure counts are exact.
5. The portal shows, before signing, **how many other subscriptions use the same router allowance** and what the plan does to them ("keeps working", "paused until migrated").

#### 5.3.2 The migration snapshot and containment

The **snapshot** is computed **on chain** from the predecessor's storage at the activation block; no field of it is supplied by the caller. It has two parts: the **terms** (static; hashed into `termsSnapshotHash`, which the customer signs) and the **usage** (volatile; logged as `usageDigest`, never signed, so a charge made while a plan is in flight does not invalidate the authorization).

```text
MigrationSnapshot.terms (static)                                                MigrationSnapshot.usage (audit only)
  lineageId, predecessorId, generation                                            per token: totalUsed, windowUsed[w] at the current index
  customer, merchantId, recipientPolicy, subscriptionRef,                         fiat: totalUsedMinor, windowUsedMinor[w]
  periodSeconds, anchorStartsAt                                                   cycles settled count, last charge time
  expiresAt
  tokens[] (sorted, unique)
  per token: perPaymentMax, dayMax, weekMax, thirtyDayMax, periodMax, totalMax
  fiat: currency, perPaymentMaxMinor, dayMaxMinor, weekMaxMinor, thirtyDayMaxMinor, periodMaxMinor, totalMaxMinor, maxQuoteAge
  boundsVersion  (the price band is not in the mandate: it is the registry's entry (token, currency, boundsVersion), ADR-020)
  maxChargesPerPeriod, minIntervalSeconds
  maxFeeBps
  extensionsHash (= 0; slippage cap does not exist in v1.0, which is the same as 0)
```

`termsSnapshotHash` is the keccak256 of the **26 words** of `snapshotEncoding` in [eip712/types.json](eip712/types.json): `SNAPSHOT_TAG`, `lineageId`, `predecessorId`, `generation`, `customer`, the lineage constants including `anchorStartsAt`, `expiresAt`, the token list and the cap table (digests of the ordered arrays), the fiat caps, `maxQuoteAge` and `boundsVersion`, the cadence, `maxFeeBps` and `extensionsHash` (reference encoding: [tools/eip712_vectors.py](tools/eip712_vectors.py); generated Solidity and TypeScript in [eip712/](eip712/)). `customer`, `anchorStartsAt` and `boundsVersion` were added by ADR-020 (findings F-06 and F-07). `newTermsHash` is a different value: `hashStruct(MandateTerms)` of the new terms.

**`Contained(N, snap)`** is the conjunction of:

| ID | Clause | Dimension |
|---|---|---|
| K.1 | `N.expiresAt ≤ snap.expiresAt` | **expiry** |
| K.2 | `N.merchantId = snap.merchantId ∧ N.recipientPolicy = snap.recipientPolicy ∧ N.subscriptionRef = snap.subscriptionRef ∧ N.periodSeconds = snap.periodSeconds ∧ N.anchorStartsAt = snap.anchorStartsAt` | **merchant scope** (and the window grid) |
| K.3 | `TN ⊆ snap.tokens` | **token scope** |
| K.4 | `∀ t ∈ TN, ∀ f ∈ {perPayment, day, week, thirtyDay, period, total}: E(N.cap[t][f]) ≤ E(snap.cap[t][f])` | **caps**, hence **remaining cap** (Lemma R below) |
| K.5 | `N.currency = snap.currency ∧ ∀ f: E(N.fiat[f]) ≤ E(snap.fiat[f]) ∧ N.maxQuoteAge ≤ snap.maxQuoteAge` | fiat caps |
| K.6 | `N.fiat.boundsVersion = snap.fiat.boundsVersion` (a mandate pins a version of the price-bounds registry, ADR-020; a different version is a different band, so a migration cannot choose one, and in a revision a different version is a widening: bit 6 of the widened mask) | price band |
| K.7 | `E(N.maxChargesPerPeriod) ≤ E(snap.maxChargesPerPeriod) ∧ N.minInterval ≥ snap.minInterval` | cadence |
| K.8 | `N.maxFeeBps ≤ snap.maxFeeBps` (and `≤ FEE_CEILING_BPS`) | **fee cap** |
| K.9 | `N.extensionsHash = 0 = snap.extensionsHash` (X1) | **slippage cap**: the field does not exist in v1.0, so it is identically 0 on both sides; a conversion consent cannot be carried by a v1.0 manager, so a conversion opt-in is never an `activateSuccessor` (§5.7) |

Lemma R (remaining caps). The counters (`used`) are preserved by the successor (Post4). For every counter family `x`: `remaining_N(x) = E(N.cap(x)) − used(x) ≤ E(snap.cap(x)) − used(x) = remaining_P(x)` by K.4/K.5. ∎

#### 5.3.3 Migration cannot widen authority

Let a payment `p` = (token `t`, gross amount `a`, time `τ`, cycle index `k`, fee `f`, fiat value `v` and price `π` if fiat-capped) and `S` the lineage state. `Acc(m, S, p)` is the conjunction of the guards of [11 §4.8](11-dual-cap-model.md) that depend on the mandate (G1…G10) and, when the mandate has fiat caps, the mandate-dependent parts of F.

**Lemma M (monotone authority).** If `Contained(N, snap(P))` and both mandates are evaluated in the same lineage state `S`, then `Acc(N, S, p) ⇒ Acc(P, S, p)` for every `p`.

*Proof, guard by guard:*

| Guard | `N` accepts means | Hence `P` accepts, because |
|---|---|---|
| Time | `τ < N.expiresAt` | `N.expiresAt ≤ P.expiresAt` (K.1) |
| Token membership | `t ∈ TN` | `TN ⊆ T` (K.3) |
| Merchant, recipient, grid | equal by definition | K.2 |
| Per-payment cap | `a ≤ E(N.perPaymentMax[t])` | K.4 |
| Window and total caps | `used + a ≤ E(N.cap)` | `E(N.cap) ≤ E(P.cap)` (K.4) with the same `used` (Post4) |
| Fiat caps, quote age | `used_fiat + v ≤ E(N.fiat)`, `age ≤ N.maxQuoteAge` | K.5 with the same counters |
| Price band | `π ∈ band(N.boundsVersion) ∩ band(current)` | K.6: `N` and `P` pin the same bounds version, so they read the same band; Q18 intersects it with the current one |
| Frequency | `count + 1 ≤ E(N.max)` and `τ − last ≥ N.minInterval` | K.7 |
| Fee | `f ≤ N.maxFee` | K.8 |
| Slippage, extensions | both 0 | K.9 |
| Cycle record | same lineage record | Post4 |

Every row is a comparison in which the successor's field is on the stricter side, so each acceptance by `N` implies the acceptance by `P`. ∎

**Consequence.** Expiry, merchant scope, token scope, every remaining cap, the fee cap and the slippage cap of a migration successor are each ≤ those of its predecessor; the executable counterpart is `contained()` in [tools/eip712_vectors.py](tools/eip712_vectors.py), whose vectors are in §5.3.4. **[tools/model_checks.py](tools/model_checks.py) exercises the lemma on a Python model of the guards:** in the default run 60,000 random predecessor and successor pairs (2,032 of them contained) are compared on 121,920 random payments with **zero** violations; each clause K.1…K.9 also has an explicit witness (a successor that violates only that clause and a payment it accepts and the predecessor rejects), so no clause is redundant; the model is a check on the argument, not a test of any contract. The lemma does not cover the router (it changes by definition), the account pin (K1) or pause bits (inherited). A `REVISION` is outside the lemma by design: it may widen, with fresh consent and a signed mask (§5.6).

#### 5.3.4 Reference vectors for the snapshot

<!-- BEGIN:VEC_SNAPSHOT -->
| Case | Result |
|---|---|
| `snapshotHash` of the predecessor snapshot below (26 words, `eip712/types.json` `snapshotEncoding`; `lineageId` `0x77…77`, `predecessorId` `0x78…78`, generation 0, customer `0x4444444444444444444444444444444444444444`) | `0x717e6c794e72d2bb7bd09f3904f69b0ed1aa1fa249a5beace858ce12e92f9256` |
| `hashStruct(MandateTerms)` of the same terms (the `newTermsHash` of a successor with these terms) | `0xbe1b1af38fd02087cfe4374e2d035b6fbb1d1e6020bbdb2400aba488205e2433` |
| contained(narrower) | contained |
| rejects longer expiry | rejected (expiry) |
| rejects other merchant | rejected (merchantId) |
| rejects higher fee cap | rejected (maxFeeBps) |
| rejects bounds version +1 | rejected (boundsVersion) |
| rejects bounds version -1 | rejected (boundsVersion) |
| rejects faster cadence | rejected (minInterval) |
| rejects non-zero extensions | rejected (extensionsHash) |
| rejects more charges per period | rejected (maxChargesPerPeriod) |
| rejects higher fiat total | rejected (fiatTotalMax) |
| rejects removed fiat total cap (0 = none) | rejected (fiatTotalMax) |
| rejects extra token | rejected (tokenScope) |
| rejects higher per-payment cap | rejected (cap:0x5555555555555555555555555555555555555555:perPaymentMax) |

Predecessor: two tokens (`0x5555…55`, `0x6666…66`), per-payment cap 51,020,409 and 30-day cap 51,020,409 each, total cap 612,244,908 each; fiat 5,000 per payment, 5,000 per 30 days, 60,000 total (USD); expiry 1,900,000,000; anchor 1,800,000,000; quote age 120 s; `boundsVersion` 1 (the band of a version is read from the registry and never changes, so a migration keeps the version: version +1 and version -1 are both rejected); one charge per period, minimum interval 86,400 s; fee cap 100 bps; `extensionsHash` 0. The narrower successor has one token, lower caps, an earlier expiry and a lower fee cap, and the same bounds version.
<!-- END:VEC_SNAPSHOT -->

#### 5.3.5 Cycle identity is independent of the router

`cycleId` and `paymentId` are functions of `(chainId, mandateManager, lineageId, cycleIndex)` only ([11 §3.1](11-dual-cap-model.md)); the settle-once record is `cycleSettled[lineageId][cycleIndex]` in the manager. Router address, router version, mandate id and generation do not appear. Therefore a cycle settled under any router and any generation cannot settle again under another (`I-ONCE`, MIG-TV-19). Across a manager replacement (§5.7) the new manager reads the previous manager's record through a constructor-fixed address (a view call; no hook in the old manager).

### 5.4 Migration plan: steps, order and transports

Order is forced by O1N/O1E and G1: **S1 grant the new router, S2 revoke the old allowance for the tokens the mode requires, S3 activate the successor.** S2 is a set of `(token, Rold)` pairs chosen by the plan kind (§5.3.1.1, §5.3.1.2); it can be empty.

| Step | Action | Primary flow | Notes |
|---|---|---|---|
| **S1** New authorization (L2) | `Permit2.approve(token, newRouter, amount, expiry)` for each token, or a signed `PermitBatch` | tx, or signed permit relayed | Inert until a mandate bound to `newRouter` exists (`I-MANDATE`). **The amount and expiry are those of the shared `(customer, token, newRouter)` allowance, sized for every lineage that will be on `newRouter` after the plan** (R-L2-SHARED, F2); R-L2-NO-MAX |
| **S2** Old allowance revocation | `Permit2.lockdown([(token, oldRouter) …])` (one call) for the pairs the plan kind requires: all exposed tokens (`NORMAL_FULL`, `EMERGENCY`), or only the tokens no sibling uses (`NORMAL_PARTIAL`) | **tx** (or in the batch) | Secondary: `Permit2.approve(token, oldRouter, 0, 0)`. **Experimental:** signed zero-amount `permit` — flag `revocation.zeroPermit.enabled`, default off, never primary |
| **S2′** Right-size the residual *(optional, `NORMAL_PARTIAL`)* | `Permit2.approve(token, oldRouter, siblingNeed, siblingExpiry)` for tokens a sibling still uses | tx | Computed from the siblings' needs, never below them (F2); reduces the exposure the contract only bounds (`Bounded`) |
| **S2″** Kill unsubmitted permits *(`EMERGENCY`; `NORMAL_FULL` if any is outstanding)* | `Permit2.invalidateNonces(token, oldRouter, newNonce)` | tx | Only if a signed permit for the old router could still be outstanding (FastPay's signed permits expire within `sigTtlSeconds`, 900 s); off-chain knowledge, the chain cannot see it |
| **S3** Successor (L3) | `activateSuccessor` for each lineage: by tx, by relayed signature (`MandateGateway.activateSuccessorBySig`) or as an entry of a `MigrationQueue` plan (ADR-022) | tx, or relayed signature | The authorization names the new router and the `kind`; its `termsSnapshotHash` covers static terms only, so a charge made in the meantime does not invalidate it |

#### 5.4.1 Atomic flow (`ATOMIC_BATCH`)

One `wallet_sendCalls` with `atomicRequired: true`. For `NORMAL_FULL` and `EMERGENCY`:

```text
call 0  (only if L1 is short)   token.approve(Permit2, l1)                         # ZERO_FIRST tokens: approve(0) first
call 1  S1   for each t in TN   Permit2.approve(t, Rnew, amount_t, expiry)          # amount_t from the sum over lineages on Rnew
call 2  S2                      Permit2.lockdown([(t, Rold) for t in Exposed(C,Rold)])
call 3  S2″  (if needed)        Permit2.invalidateNonces(t, Rold, n_t) for each exposed t
call 4  S3                      MigrationQueue.open(plan), then step(entries)       # A1: the customer opened the plan (ADR-022)
```

For `NORMAL_PARTIAL`: call 2 names **only the tokens with no sibling** (and is omitted when there are none); call 3 is omitted; the optional right-sizing S2′ is one `approve` per shared token placed after call 2.

| After | State (inside one transaction; not observable) | Predicates true |
|---|---|---|
| call 1 | Q1: both allowances usable; `P` active | G1 |
| call 2 | Q2: the old allowances the mode requires are gone; siblings under `NORMAL_PARTIAL` are untouched; under `NORMAL_FULL`/`EMERGENCY` every migrating lineage is unfunded until call 4 | G1, O1N or O1E |
| call 4 | Q3 | `SuccessorOK`; Post1…Post6 |

Properties: all or nothing (a revert in any call leaves state unchanged); no external observer sees Q1 or Q2; predicates are evaluated by the last call in the state left by the calls before it. Customer prompts: 1 (plus the wallet's own upgrade prompt where applicable). Verification V1–V6 follows.

#### 5.4.2 Legacy flows (`TX_SEQUENCE` and `MIXED`)

The sequence is S1, S2, S3. In `NORMAL_PARTIAL` with no exclusive token **there is no S2** and the sequence has no Q2 state at all. For the other plan kinds:

| Step | Action | State after | Charges possible? | `AuthRouters(L)` | Backend | If it stops here |
|---|---|---|---|---|---|---|
| 0 | — | Q0 | Old router | `{Rold}` | Normal | — |
| 1 | S1 (tx, or signature relayed) | Q1: new allowance granted, old still usable, `P` active | Old router | `{Rold}` | "Finish migration" prompt; no hold | Harmless: the new allowance is inert (no mandate bound to `Rnew`) |
| 2 | S2 (tx `lockdown`) | Q2: the required old allowances unusable, `P` still `ACTIVE`, no successor | **None** for the pairs locked down | `∅` | **Hold** `MIGRATION_IN_PROGRESS` for every lineage the lockdown unfunded (the migrating ones and, under `NORMAL_FULL`/`EMERGENCY`, the siblings): no attempts, no dunning, 24 h TTL | Re-plan S3 now; or re-grant the old allowance and abandon (T9) |
| 3 | S3 (tx, or relayed signature of `auth`) | Q3: `P` revoked, `N` active | New router | `{Rnew}` | Verification; hold released | Complete |

`MIXED` = S2 as a transaction and S1, S3 as customer signatures submitted by a relayer (S1 first, then S2, then S3; the customer signs S1 and S3 up front and sends S2). Because `termsSnapshotHash` excludes usage, a charge between signing and S3 does not break `auth`; a change of the predecessor's static terms (a `reduce`) does, and the plan is re-signed. A sibling created between signing and S3 **can** change the exposure counts: a `NORMAL` authorization remains valid (O1N is evaluated on the live counts at S3) but a `lockdown` computed before the sibling existed may now unfund it; the plan therefore re-reads the counts at one block immediately before S2 and the validator refuses a stale plan (NC-20). Interruption cases: Q2′ (S2 done, S1 expired or failed) re-grants S1 then S3, or re-grants the old allowance; Q1′ (customer left after S1, hold expired) shows a reminder.

### 5.5 Partial states and the authority proof

**Two layers, kept apart.** *Layer 3* is the mandate: a router holds **executable Layer 3 authority** for a lineage when a mandate of that lineage is consumable by it. *Layer 2* is the Permit2 allowance `(customer, token, router)`: it is a funding fact, shared by the customer's sibling lineages, and it never creates authority by itself (`I-MANDATE`: an allowance without an executable mandate is inert).

```text
Exec3(L)      = { r : ∃ m ∈ L, Consumable(r, m) }                                   # executable Layer 3 authority (mandate state only)
AuthRouters(L) = { r ∈ Exec3(L) : ∃ t ∈ m.tokens: Usable(C, t, r) }                  # routers that can pull for L right now (Layer 3 and Layer 2)
```

**Claim 1 (at most one router holds executable Layer 3 authority per lineage).** In every reachable state `|Exec3(L)| ≤ 1`, and therefore `|AuthRouters(L)| ≤ 1` (`I-MIG-8`). **Nothing in this claim limits Layer 2:** the customer's usable allowances may coexist on several routers (an old and a new router during a plan; the old router for sibling lineages that have not migrated), and a single allowance serves every sibling lineage on that router and token.

*Proof.* `Consumable(r, m)` requires `L.activeMandateId = m.id`, which holds for at most one mandate, and `m.router = r`, which fixes `r`. Hence `Exec3(L)` has at most one element, and `AuthRouters(L) ⊆ Exec3(L)`. The Permit2 side can only remove routers from the set; it cannot add one. ∎

**Claim 2 (shared allowance, residual).** After a successful `activateSuccessor` of kind `NORMAL`, for every `t ∈ T`: `live(C,Rold,t) = 0 ⇒ Unusable(C,t,Rold)` and `live(C,Rold,t) > 0 ⇒ Bounded(C,t,Rold)`; of kind `EMERGENCY`, `Unusable(C,t,Rold)` holds for every token that was exposed on `Rold` (Post3N, Post3E).

*Proof.* The predicates O1N and O1E are evaluated in the same transaction as the effects, against the live allowance (a view call) and the exposure index, and nothing between the evaluation and the end of the transaction writes Permit2 (Post6). The index counts the predecessor itself (it is live until E1), so `Sib(t) = live − 1` is the number of other live mandates; E6 then lowers `live(C,Rold,t)` by exactly one for `t ∈ T`, so `live_after = Sib(t)`. ∎

**Claim 3 (non-interference with siblings).** `activateSuccessor` writes only `P`, `N`, the lineage `L`, the nonce record and the exposure counts of `T` on `Rold` and `TN` on `Rnew`; it reads Permit2 only through `allowance`. Hence every sibling mandate, every sibling lineage and every Permit2 allowance is unchanged (Post6, `I-MIG-11`). ∎

**Claim 4 (no sibling starved by the contract).** In `NORMAL` mode the contract never causes a sibling to lose funding: if a sibling stops being funded after a plan, the cause is a customer transaction (S2/S2′ or an unrelated action) that the planner's validator should have refused (NC-20, NC-21), not the activation. This is a statement about what the contract does, not a guarantee about the customer's other transactions.

| State | New L2 | Old L2 (the token the lineage uses) | Successor | Meaning | Charges | `AuthRouters` | Action |
|---|---|---|---|---|---|---|---|
| Q0 | none | usable | none | Start | Old router | `{Rold}` | Prompt to migrate |
| Q1 | usable | usable | none | S1 done | Old router (works) | `{Rold}` | "Finish migration" prompt |
| Q2 | usable | **unusable** | none | S1 + S2 done | **None** | `∅` | Finish S3 now |
| Q2′ | **missing** | unusable | none | S2 done, S1 failed or expired | None | `∅` | Re-grant S1 then S3; or re-grant the old allowance (T9) |
| Q3 | usable | unusable **or** residual for siblings | **ACTIVE** | Complete | New router | `{Rnew}` | none |
| Q3s | usable | usable and bounded (siblings rely on it) | **ACTIVE** | `NORMAL_PARTIAL` complete | New router for the migrated lineage; **old router for the siblings** | `{Rnew}` for the migrated lineage, `{Rold}` for each sibling | Migrate the siblings when ready |
| Q1′ | usable | usable | none, hold expired | Customer left mid-way | Old router | `{Rold}` | Reminder; the new allowance sits inert |

A signed old permit submitted by anyone after S2 can make the old allowance usable again (Q2 → Q1); it cannot create a second router with authority, because the old mandate remains the only active one until S3, and after S3 it is revoked (Post2) so even a resurrected old allowance is inert **for that lineage**. For siblings a resurrected allowance simply funds them again; in emergency mode it is an exposure and is alerted.

**Executable model.** [tools/model_checks.py](tools/model_checks.py) explores the single-lineage state machine (grant, lockdown, re-grant, expiry, activation, revoke) and, new in 0.5, a **shared-allowance model**: two lineages of one customer on the same old router and the same token, two routers, `approve` that overwrites, `lockdown`, expiry, charges that consume the shared budget, the router's mode (normal, emergency), retire, and `activateSuccessor` of both kinds. It asserts Claim 1 per lineage, Claim 2, Claim 3, Claim 4 (a normal activation never changes any allowance), and that the exposure index is never an under-count. **Result of the 0.5 run (Python, `python -I tools/model_checks.py`):** the single-lineage machine has 12 states and 61 transitions; the shared-allowance explorations (one customer, two lineages, two routers, allowance values none / expired / bounded / unlimited; three configurations) reach **720 states and 9,078 transitions** with at most one router holding authority per lineage in every state and all of Claims 2…4 and `I-MIG-10`/`I-MIG-11` holding; 505 reverting instructions leave the model state unchanged; a mutation analysis of **151 named mutants** of the model shows that every one is killed by the exported vectors. The same states and scenarios are exported to Foundry ([foundry/](foundry/), `SharedAllowance.t.sol`, the generated tests); the Solidity has not been compiled or run. Every state is reachable in tests; every state has customer copy and a support playbook entry. The **Q2 window is deliberately short**: the plan sends S2 and S3 back to back, the orchestrator holds charges rather than failing them, and the atomic flow removes the window.

### 5.6 Revision (same router) versus migration (new router)

| | Migration | Revision |
|---|---|---|
| Router | Different (`Rnew ≠ Rold`) | Same |
| Terms | Contained in the predecessor's (`Contained`) | Any, except the lineage constants; the signed `widenedMask` lists which dimensions grow |
| Old permission check (O1N / O1E) | Required, by mode (§5.3.1) | Not applicable (same router; the shared allowance may need a top-up sized from all siblings, G1 and R-L2-SHARED) |
| Lineage counters | Preserved | Preserved (windows and totals are compared with the new caps) |
| Typical cause | Router deprecation, security fix | Price-change consent, plan change |

`widenedMask` bits (the contract computes them; the typed data carries them so that the wallet shows "increases …"): 0 expiry later, 1 token added, 2 per-payment cap higher, 3 a window cap higher or removed, 4 total cap higher or removed, 5 fiat cap higher or removed, 6 quote age or price band wider, 7 more charges per period or shorter interval, 8 higher fee cap. A migration must have mask 0. A different merchant, subscription or billing period is a **new lineage**, not a revision.

### 5.7 Replacing `MandateManager` (class M-M) without hooks, and how conversion is adopted

v1 `MandateManager` carries **no export or import code** (a dormant path would be unaudited attack surface). If a manager must be replaced (a defect, or to carry a new consent such as conversion):

1. The customer signs a **new mandate in the new manager** (a fresh authorization naming the new manager and router) whose caps equal the predecessor's **remaining headroom** (cap minus usage, computed by the backend and shown to the customer).
2. The customer **revokes the old mandate** (primary flows) and the old router permission.
3. History is linked off chain (`mandate_lineages` with a `manager` column). The new manager is deployed with the old manager's address as an immutable constructor argument and reads `cycleSettled(lineageId, cycleIndex)` from it (a view call on a fixed address; the old manager needs no hook), so the once-per-cycle record also holds across the replacement.

**Conversion adoption (v1.1)** follows this path, not `activateSuccessor`: conversion consent needs a mandate field that the v1.0 manager forces to zero (`extensionsHash`), so a v1.0 mandate can never authorize conversion, and migration containment (K.9) cannot be used to add it. The v1.1 manager and router are adopted by a new mandate with remaining-headroom caps and its own `Contained`-style rule against the old mandate's remaining headroom.

Residual risk: a cycle could be settled on both managers only if the old mandate were still live; step 2 prevents it and the previous-manager lookup rejects it on chain.

## 6. Revocation flows (summary; authoritative table in [05 §2.1](05-evm-authorization-decision-tree.md))

| Layer | Primary supported flow | Secondary | Experimental |
|---|---|---|---|
| L1 token → Permit2 | `token.approve(Permit2, 0)` (transaction) | — | `permit(owner, Permit2, 0, …)` for verified ERC-2612 tokens |
| L2 Permit2 → router | `Permit2.lockdown([(token, router)])` (transaction; one call covers every token; in a batch when available); fork-tested as RV-T01…RV-T12 ([05 §2.1](05-evm-authorization-decision-tree.md)) | `Permit2.approve(token, router, 0, 0)` | **Signed zero-amount `permit`** (ZP-T01…ZP-T08 and the wallet lab; flag off) |
| Unsubmitted signed permits | `Permit2.invalidateNonces` (AllowanceTransfer) or `invalidateUnorderedNonces` (SignatureTransfer) — transactions | — | — |
| L3 mandate | `MandateManager.revoke` (tx) or `revokeBySig` (EIP-712, relayed, gasless) | — | — |

## 7. Stranded mandate prevention

**Definition.** A mandate is *stranded* when the customer's intent is still live, the mandate can no longer be charged because its router is not chargeable, **and** FastPay failed to provide a working migration path and notice for at least the minimum notice period. Mandates left unmigrated because the customer did not respond are tracked separately as `UNMIGRATED_AT_SUNSET`.

| # | Control | Enforced by |
|---|---|---|
| M1 | The migration path (plan, successor, revocation) is live, tested and rehearsed before any router can be deprecated | RG-015; `EPIC-P3-MIGDRILL` |
| M2 | Sunset cannot occur before `deprecation + MIN_NOTICE` | On-chain constants (`I-MIG-6`) |
| M3 | Revoke, pause and creation of a successor are not subject to router status, router pause or sunset | `I-MIG-4`; fork test with the router sunset and disabled |
| M4 | One transaction opens a plan that migrates every mandate of a customer on the same router, in steps of at most `MAX_BATCH` (10, provisional) entries; a plan is resumable (ADR-022) | `MAX_BATCH`; the planner builds plans and the hash chain |
| M5 | Notices run on the §11 schedule with escalation for non-responders and per-mandate merchant visibility | Orchestrator; metrics |
| M6 | Prompts are timed before the customer's next scheduled charge, not only by calendar | Subscription service integration |
| M7 | Customers without a contact channel are reached through the merchant (webhook + merchant agreement duty) and through checkout/portal at next visit | Merchant agreement; orchestrator |
| M8 | At most **two** routers `ACTIVE` or `DEPRECATED` per chain at once | Registry guard |
| M9 | Sunset needs recorded metrics and risk acceptance by Head of Product and CISO | RG-015 |
| M10 | Unmigrated mandates at sunset become `MIGRATION_REQUIRED`; the subscription service applies the merchant's dunning/grace policy; the customer gets a pre-filled "reactivate with the same terms" plan | Subscription service; portal |
| M11 | Before deprecating, a dry-run report lists every mandate on the router, next charge date and prompt status | Orchestrator |
| M12 | The Q2 hold prevents a half-finished migration from producing failed charges or dunning | Orchestrator (§5.5) |

SLO: **zero stranded mandates** in rehearsals and in each campaign; `UNMIGRATED_AT_SUNSET` reported at the gate.

## 8. Events

| Layer | Event | Fields (selected) |
|---|---|---|
| On chain | `RouterProposed`, `RouterCancelled`, `RouterActivated`, `RouterDeprecated`, `RouterSunsetExtended`, `RouterSunset`, `RouterRetired`, `RouterEmergencyDisabled`, `RouterEmergencyCleared` | router, version, code hash, audit ref, successor, `sunsetNotBefore`, notice hash, reason |
| On chain | `MandateActivated`, `MandateSuperseded`, `MandateRevoked`, `MandateRetired(mandateId)`, `MandatePauseChanged(bit, reason)`, `AccountPinUpdated(mandateId, oldPinHash, newPin (all seven fields), pinVersion)` | mandateId, lineageId, predecessorId, generation, kind (`NORMAL`, `EMERGENCY`, `REVISION`), old/new router, `termsSnapshotHash`, `usageDigest`, authorization hash; `MandateActivated` also carries the full `AccountPin` |
| Webhook to merchants | `router.deprecated`, `mandate.migration_required`, `mandate.superseded`, `mandate.paused.account_change` (reason only, no personal detail), `migration.campaign.summary` | merchant-scoped; privacy-minimized |
| Customer notification keys | `migration.notice.deprecation`, `.reminder.{150,120,90,60,30,14,7,3,1}`, `.sunset`, `.reactivate`, `.cleanup`, `.emergency`, `.completed` | §11 |
| Internal | `migration.plan.created`, `.step.completed`, `.hold.started`, `.hold.expired`, `.verified`, `.old_permission_remaining`, `.halted` | planId, lineageId, correlation ids |

On-chain events are the source of truth for state; webhooks and notices derive from them.

## 9. Data and API additions

Tables (in addition to the 35 of prompt §15): `router_versions`, `mandate_lineages`, `mandate_generations` (replaces `mandate_router_bindings`), `migration_campaigns`, `migration_cohorts`, `migration_notices`, `migration_plans`, `router_exposure` (a read model of the on-chain `live` counts and the sibling lists per customer, router and token, reconciled against the chain at one block before every plan), `shared_allowance_ledger` (per customer, token and router: current amount, expiration, the lineages that rely on it and each one's remaining need), `account_delegation_observations`, `delegation_evidence`, `feature_flags`, `feature_flag_changes`. Append-only where they hold consent evidence.

Endpoints (illustrative): `POST /v1/mandates/{id}/migration-plans`, `GET /v1/lineages/{id}`, `GET /v1/migration-campaigns/{id}`, `POST /v1/migration-campaigns/{id}/halt`, `GET /v1/routers`.

## 10. Rollback

| Situation | Response | Notes |
|---|---|---|
| Proposed router found defective during the timelock | Governance cancels | Nothing changed for customers |
| New router ACTIVE, no mandates bound, defect found | Guardian `emergencyDisable`; fix; propose a new version | No customer impact |
| Defect found after a cohort migrated | Guardian disables the new router (charges of migrated lineages stop; exits unaffected). The old router is still DEPRECATED, so customers may create a **successor back to the old router** (T7) during the rollback window; this repeats §5.3 (grant old, revoke new, activate) with kind `EMERGENCY`, because the disabled router is in emergency mode (every token exposed on it must be unusable first), and preserves the lineage counters | `isBindable` allows a DEPRECATED router while `now < deprecatedAt + ROLLBACK_WINDOW` (30 days, PROPOSAL) |
| Campaign metrics bad (failure rate, support spike, phishing reports) | Orchestrator **halts** prompting; no on-chain action | Criteria in §11.3 |
| Wrong sunset date scheduled | Governance extends; cannot shorten below `deprecation + MIN_NOTICE` | |
| Emergency disable of the router customers are on | Charges stop; customers create successors at their pace; merchants offered Pay Once fallback | No deadline; lineages stay `MIGRATION_REQUIRED` until expiry |
| Transaction fails | Atomic: nothing applied. Non-atomic: §5.5 states | Re-plan from chain state |

Cohort strategy: staged **prompting** (internal accounts → 1% → 10% → 50% → all); the customer's authorization is always individual.

## 11. Customer and merchant communication

### 11.1 Timeline (standard migration; `S` = `sunsetNotBefore`, notice 180 days)

| When | Customers | Merchants | Channels |
|---|---|---|---|
| `T0` deprecation (S − 180d) | Announcement: what changes, what stays, what you do | Notice + per-lineage list; webhook `router.deprecated` | Status page, portal banner, consented notification channels |
| T0 + 7d | Migration prompt available | Dashboard campaign view | Portal, wallet-visible authorization |
| S − 150, −120, −90 | Reminders (not yet migrated) | Monthly digest | Portal at visit; consented channels |
| S − 60 | Second-level reminder with next charge date | Action list for high-value customers | + merchant outreach |
| S − 30, −14, −7, −3, −1 | Urgent reminders | Daily digest in the last week | All available |
| `S` sunset | "Subscription paused: migrate to resume" | `mandate.migration_required`; dunning/grace applies | All |
| S + 30 / 60 / 90 | Reactivation reminders with the pre-filled plan | Summary | |
| Retirement | "Remove leftover permissions" reminder | Summary | |

Security-driven migration compresses to T0, T0+3, S−30, −14, −7, −3, −1 (`MIN_NOTICE_SECURITY`). Emergency: status page and merchant notice within 1 hour, customers within 24 hours, no deadline for customers.

### 11.2 Message content requirements

Each message states: what is happening and why; what the customer must do; the deadline; **what happens if they do nothing**; how to verify authenticity (only the official portal domain; the new router address and code hash shown in the portal and in the wallet prompt); that FastPay will **never** ask for a seed phrase or private key; that the migration **includes revoking the old permission** and why — and, because the permission is shared by every subscription on the same router and token, **which other subscriptions use it** and what happens to them ("keeps working until you migrate it", or, in an emergency or security migration, "paused until migrated"); how to revoke everything; support link. Translation keys with parameters; localized including RTL; WCAG 2.2 AA; back-translated; counsel-reviewed (`LEGAL-REVIEW-REQUIRED`, RP-26).

### 11.3 Halting criteria (proposals)

Halt prompting if: migration failure rate > 2% over 200 attempts; any verification V1–V5 mismatch; a Q2 hold expiring in more than 1% of plans; support contact rate > 1% of prompted customers; any confirmed phishing imitation; any unexpected on-chain event from the new router.

### 11.4 Anti-phishing

Official channels only; no unsolicited direct messages; the authorization screen and wallet prompt both show `newRouter` and its explorer link; the portal never asks for anything except the typed data defined here; a published verification page lists current router addresses and code hashes; look-alike-domain detection; the support script teaches "only from the portal". Threat entry: TB-17, RISK-026.

## 12. Invariants and tests

| ID | Invariant |
|---|---|
| I-MIG-1 | A lineage has at most one active mandate; only that mandate can be charged, and only by the router it is bound to |
| I-MIG-2 | A migration successor's terms are contained in the predecessor's; a revision needs fresh consent for the new terms |
| I-MIG-3 | Lineage counters, windows, totals and cycle records are unchanged by any successor activation |
| I-MIG-4 | Revoke, pause and successor creation are not blockable by router status, pause, sunset, emergency disable or governance |
| I-MIG-5 | A successor binds only to a registered, hash-matching, bindable router named in the customer's authorization |
| I-MIG-6 | A router is never SUNSET before `deprecation + MIN_NOTICE`; `MIN_NOTICE` is immutable |
| I-MIG-7 | **Shared-allowance rule.** A migration successor activates only if the customer's Permit2 allowance to the old router satisfies O1N (kind `NORMAL`: for a predecessor token no sibling uses it is zero or expired, `a = 0 ∨ e < now`; for a token a sibling uses it is bounded) or O1E (kind `EMERGENCY`: zero or expired for **every** token any live mandate of the customer uses on that router); the mode is derived from the router's registry state; the predecessor is revoked as `SUPERSEDED` in the same transaction |
| I-MIG-8 | **No overlapping Layer 3 authority:** in every reachable state at most one router holds executable Layer 3 authority for a mandate lineage (`|Exec3(L)| ≤ 1`, hence `|AuthRouters(L)| ≤ 1`, §5.5). **Layer 2 Permit2 allowances may coexist** (several routers; shared by sibling lineages) and never create Layer 3 authority. Executable: `Exec3.t.sol` (two sibling lineages, a usable allowance to both routers, one executing router each) and the stateful invariants `invariant_I_MIG_8_Exec3AtMostOneRouterPerLineage` and `invariant_I_MIG_8_NoOverlappingAuthority` of `MigrationInvariant.t.sol` |
| I-MIG-9 | **Monotone authority:** a migration successor accepts no payment that its predecessor would not accept in the same lineage state (§5.3.3) |
| I-MIG-10 | **Exposure index is never an under-count:** for every `(customer, router, token)`, `live` is at least the number of live mandates (it equals the number of recorded-active mandates and exceeds the true number only by expired or exhausted mandates not yet retired); `Exposed` contains exactly the tokens with `live > 0` and never more than `MAX_EXPOSED_TOKENS_PER_ROUTER` |
| I-MIG-11 | **Non-interference:** `activateSuccessor` makes no write to Permit2 and changes no sibling mandate, sibling lineage or allowance; it changes only the predecessor, the successor, its lineage, the nonce record and the exposure counts |
| I-ONCE (extended) | A `(lineageId, cycleId)` and a Pay Once `paymentId` settle at most once across all routers and generations |

| MIG-TV | Scenario | Expected |
|---|---|---|
| MIG-TV-01 | Atomic batch S1+S2+S3, one token | Q3; V1–V6 pass; one prompt; counters unchanged |
| MIG-TV-02 | MIXED: lockdown tx, then relayed signatures for S1 and S3 | Q3; one transaction plus two signatures |
| MIG-TV-03 | TX_SEQUENCE interrupted after S1 | Q1; old router still charges; re-plan shows S2, S3 |
| MIG-TV-04 | Interrupted after S2 | Q2: backend hold; no charge attempt and no dunning; S3 completes it |
| MIG-TV-05 | `activateSuccessor` of kind `NORMAL` for the customer's **last** live mandate on the old router (no sibling) while the old allowance is still usable | Reverts `OldPermissionNotRevoked` |
| MIG-TV-06 | Router reaches SUNSET with the lineage unmigrated | `MIGRATION_REQUIRED`; no charge; a successor can still be created |
| MIG-TV-07 | Router emergency-disabled, then a successor to the new router | Succeeds; charges resume on the successor |
| MIG-TV-08 | Successor to an unregistered, CANDIDATE, SUNSET, or non-rollback DEPRECATED router | Reverts `RouterNotBindable` |
| MIG-TV-09 | Successor with a wider cap, an extra token, a longer expiry, or non-zero `extensionsHash` | Reverts `TermsNotContained` |
| MIG-TV-10 | Spend 40 of 50 under generation n; migrate; attempt 20 under n+1 | Second charge reverts: lineage cap |
| MIG-TV-11 | A cycle settled under generation n; same `cycleId` under n+1 | Reverts `PaymentAlreadySettled` |
| MIG-TV-12 | Old mandate charge attempt after the successor exists | Reverts: predecessor is `REVOKED(SUPERSEDED_MIGRATION)` even though its router is still chargeable |
| MIG-TV-13 | Reverse successor to the old router inside the rollback window; outside it | Succeeds; reverts |
| MIG-TV-14 | Predecessor is customer-paused; migrate | Successor inherits the pause bit; explicit resume required |
| MIG-TV-15 | Revision on the same router with higher caps and fresh consent; migration kind with the same router | Succeeds; reverts |
| MIG-TV-16 | Planner with the experimental flag off | Never emits a zero-amount permit step |
| MIG-TV-17 | Authorization signed for router B replayed against router C | Reverts: router is part of the typed data |
| MIG-TV-18 | A step of `MAX_BATCH` (10) successors succeeds; one more reverts (`BatchTooLarge` in the model, `StepTooLarge` in `MigrationQueue`) | `MAX_BATCH` |
| MIG-TV-19 | The same `(lineageId, cycleIndex)` charged under router A, then (after a migration) under router B | Both `paymentId`s are equal; the second reverts `PaymentAlreadySettled` |
| MIG-TV-20 | Containment boundary, one case per clause: expiry +1; other merchant; extra token; per-payment, window and total cap +1; a removed cap (0); fiat cap +1; quote age +1; bounds wider; one more charge per period; shorter interval; fee cap +1 | Each reverts `TermsNotContained`; each ≤ case is accepted |
| MIG-TV-21 | `kind ∈ {NORMAL, EMERGENCY}` with `widenedMask ≠ 0`; `kind = REVISION` with a mask that differs from the computed one | Reverts `TermsNotContained`; `WidenedMaskMismatch` |
| MIG-TV-22 | Old allowance (last lineage, kind `NORMAL`) with `expiration = now`; with `expiration = now − 1`; with `amount = 0` | Revert `OldPermissionNotRevoked`; accepted; accepted (restated with the boundary cases in MIG-TV-40) |
| MIG-TV-23 | Old allowance `uint160.max`, unexpired: last lineage; a sibling remains | Reverts `OldPermissionNotRevoked` (unlimited counts as usable); reverts `ResidualAllowanceUnbounded` |
| MIG-TV-24 | New allowance missing, below the per-payment cap, or expired | Reverts `NewPermissionMissing` |
| MIG-TV-25 | After S3 a stale signed permit re-grants the old allowance; the old router tries to charge | Reverts: predecessor `REVOKED`; `AuthRouters = {Rnew}` |
| MIG-TV-26 | Customer has two lineages on the old router sharing token `t`; **normal** migration of one | No lockdown is part of the plan; the sibling keeps charging, no hold (MIG-TV-30); a plan that does contain `lockdown(t, Rold)` is refused by the validator (NC-20) |
| MIG-TV-27 | MIXED flow: a charge settles on the old router after the customer signed `auth` and before S3 | `auth` is still valid (the snapshot hash covers static terms); counters include the charge |
| MIG-TV-28 | `MIGRATION` (either kind) to the same router; `REVISION` to a different router | Revert `WrongKind` |
| MIG-TV-29 | Successor with an `accountPin` that is malformed, that does not match `EXTCODEHASH(customer)` or the delegate's code hash, or whose `pinVersion` is not the next one | Reverts `AccountPinMalformed`; `AccountPinMismatch`; `PinVersionMismatch` |
| MIG-TV-30 | Two lineages A, B of one customer on an ACTIVE old router, same token `t`; allowance bounded and usable; **normal** migration of A with no lockdown | Succeeds; the Permit2 allowance is unchanged; B's charge on the old router still succeeds; `AuthRouters(A) = {Rnew}`, `AuthRouters(B) = {Rold}` |
| MIG-TV-31 | As 30 with the old allowance `uint160.max` | Reverts `ResidualAllowanceUnbounded(t)` |
| MIG-TV-32 | A migrated as in 30; then **normal** migration of B (now the last lineage) with the allowance still usable; then again after `lockdown(t, Rold)` | Reverts `OldPermissionNotRevoked(t)`; succeeds |
| MIG-TV-33 | Router `DISABLED_EMERGENCY`; **emergency** migration of A while `(t, Rold)` (shared with B) is usable; then after one `lockdown`; then B's emergency successor | Reverts `OldPermissionNotRevoked(t)`; succeeds, B stays `ACTIVE` and unfunded; B's successor succeeds with no further lockdown |
| MIG-TV-34 | Emergency; A uses `t1`, B uses `t2`; lockdown only `(t1, Rold)`, then both | Migrating A reverts `OldPermissionNotRevoked(t2)` (a sibling's exposed token); succeeds after `(t2, Rold)` is locked down too |
| MIG-TV-35 | Router modes: DEPRECATED with reason SECURITY, DISABLED, SUNSET, RETIRED; ACTIVE; DEPRECATED with reason STANDARD | `NORMAL` reverts `ModeMismatch` on the first four; `EMERGENCY` is accepted on all (strict mode is voluntary on the last two); `NORMAL` is accepted on the last two |
| MIG-TV-36 | Sibling B has expired (`τ ≥ expiresAt`) but is not retired; **normal** migration of A with a usable allowance; then after `retire(B)` | Succeeds (the index over-counts, which is safe); the same call reverts `OldPermissionNotRevoked` after `retire` |
| MIG-TV-37 | A customer has live mandates on one router using 8 distinct tokens; activating a mandate with a 9th; after revoking the only mandate that uses one of the 8 | Reverts `ExposureLimit`; succeeds |
| MIG-TV-38 | Emergency; one `lockdown` covering every exposed token; a step of `MAX_BATCH` (10) successors; one more | All 10 succeed (O1E holds for each without further action); the 11th reverts (`MAX_BATCH`) |
| MIG-TV-39 | Snapshot of every Permit2 allowance and of every sibling's storage before and after `activateSuccessor`, both kinds and `REVISION` | Identical, except `P`, `N`, `L`, the nonce record and the exposure counts (`I-MIG-11`) |
| MIG-TV-40 | Last-lineage cleanup boundary: `expiration = now`; `expiration = now − 1`; `amount = 0`; `amount > 0` with `expiration = now + 1` | Reverts; accepted; accepted; reverts |
| MIG-TV-41 | `approve(t, R, 50, T + 10)` for another lineage on a router whose shared allowance is 100 expiring at `T + 1000` and serves a sibling | The planner refuses the step (NC-21); on a fork its execution lowers the shared slot and the sibling's later charge reverts (`AllowanceExpired` or `InsufficientAllowance`) — a liveness effect, no cap exceeded |
| MIG-TV-42 | Two lineages share an allowance of 100 on one router; A charges 60, then B charges 60 | B's charge reverts `InsufficientAllowance(40)`; no mandate cap is exceeded; the orchestrator raises `ALLOWANCE_SHORTFALL` before submitting |
| MIG-TV-43 | A random sequence of activate, successor (both kinds), revoke, retire and token-removing `reduce` over several customers and routers | After every step `live(C,R,t)` equals the recomputed number of recorded-active mandates and is never below the true live number (`I-MIG-10`) |
| MIG-TV-44 | `NORMAL_PARTIAL` where every token of the predecessor is shared; the legacy flow S1 then S3 | No S2, no Q2, no hold; `AuthRouters` is `{Rnew}` for the migrated lineage and `{Rold}` for each sibling |
| MIG-TV-45 | Emergency: a stale signed permit re-grants `(t, Rold)` after the lockdown and before S3; then the plan re-locks; then after S3 another re-grant | `activateSuccessor` reverts `OldPermissionNotRevoked(t)`; succeeds; the later re-grant is inert for the migrated lineage (MIG-TV-25) and raises `migration.old_permission_remaining` |

**Executable suites (0.5).** Every vector above that a Python model can compute is exported to Solidity by [tools/export_foundry.py](tools/export_foundry.py) into [foundry/](foundry/): vector tests, stateful fuzz and invariant tests over the shared-allowance model (`I-MIG-1…11`), mutation tests (each predicate A1…O1E, each containment clause K.1…K.9 and each exposure update is removed or inverted in turn and the suite must fail), integer-width tests (`uint48` expirations, `uint160` amounts, `uint32` versions and counts, `uint256` caps), timestamp-boundary tests (the `=`, `+1` and `−1` second around every time comparison) and shared-allowance scenarios MIG-TV-30…45. The Solidity files target a reference model of the predicates today and the real `MandateManager` through the same interface when it exists; **they have not been compiled or run** (no Foundry toolchain in the authoring environment: see [16 §5](16-freeze-decision-report.md) and [foundry/README.md](foundry/README.md)).

Rehearsal program: fork tests for every vector; chaos tests killing the wallet at each step; testnet rehearsal of a full deprecate → migrate → sunset → retire cycle (PB-006, `EPIC-P2-DEPLOYPREP`); mainnet canary drill with internal accounts (`EPIC-P3-MIGDRILL`); consent comprehension test (`EPIC-P0-DESIGN`); communications drill (`EPIC-P4-MIGGAME`).

## 13. Parameters (OD-026; all PROPOSALS)

| Parameter | Value | Where enforced |
|---|---|---|
| `MIN_NOTICE_STANDARD` | 180 days | Immutable in `RouterRegistry` |
| `MIN_NOTICE_SECURITY` | 60 days | Immutable |
| Emergency notice | None possible; stop is immediate | Guardian |
| `RETENTION` before RETIRED | 365 days | Immutable |
| `ROLLBACK_WINDOW` | 30 days | Registry (governance may extend) |
| `MAX_BATCH` | 10 entries per plan step (provisional: a step of 50 would cost about 30 million gas, extrapolated from the measured marginal cost, ADR-022) | Compile-time constant |
| `MAX_EXPOSED_TOKENS_PER_ROUTER` (PC-18, new in 0.5) | 8 distinct tokens across one customer's live mandates on one router | Immutable in `MandateManager` (`ExposureLimit`) |
| Routers simultaneously ACTIVE or DEPRECATED | ≤ 2 per chain | Registry guard |
| Q2 hold TTL | 24 hours | Orchestrator |
| Timelock for propose/activate/deprecate | 72 hours | Timelock controller |
| Cohort schedule | internal → 1% → 10% → 50% → 100% | Orchestrator |

## 14. Runbooks

| RB | Runbook |
|---|---|
| RB-031 | Router migration campaign (start, cohorts, halt, resume, close) |
| RB-032 | Emergency router disablement and customer successor |
| RB-033 | Conversion rollout kill switch ([09 §5](09-capability-boundaries.md)); applies from v1.1 |

## 15. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Verify `lockdown` and `approve(…, 0, 0)` behavior per token and chain at a pinned commit, and the experimental zero-amount `permit` (EV-P08, EV-P11) | AA/Protocol Eng |
| 2 | Counsel view on notice duties by jurisdiction; whether FastPay or the merchant is the notifier of record (RP-26) | Head of Compliance |
| 3 | Gas cost of the containment check and of a 50-successor batch (RP-19) | Solidity Lead |
| 4 | Whether `activateSuccessor` should also accept the old router's `RETIRED` state for recovery outside the rollback window (current: no) | Principal Architect + Security |
| 5 | Whether the successor should inherit a customer pause or require explicit resume (current: inherit) — usability test | Product Designer |
| 6 | Whether a **normal** migration should also require a right-sized residual allowance (`amount ≤ Σ siblings' remaining need`) instead of only `Bounded`. Current: only `Bounded` on chain; right-sizing is a planner step (S2′) because the sum is not cheap to compute on chain (OD-035) | Principal Architect + Solidity Lead |
| 7 | Whether `SECURITY`-deprecated routers should be `NORMAL` for customers who prefer to keep siblings charging during the notice period (current: `EMERGENCY`, which interrupts siblings until their successors exist) | Head of Security + Product |
| 8 | Gas of the exposure index (`live` updates on every activation, successor, revoke and retire) and of the O1E enumeration at `MAX_EXPOSED_TOKENS_PER_ROUTER` tokens: not measured (RP-19) | Solidity Lead |
