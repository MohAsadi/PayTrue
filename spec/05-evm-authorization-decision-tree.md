# 05 — Capability Discovery and Protocol B: FastPay Recurring Activation Planner

| Field | Value |
|---|---|
| Artifact | FP-PRO-001 (Parts C.2–C.6) |
| Version | 0.5.0 (planner 1.4.0: shared Permit2 allowance sizing R-L2-SHARED, sibling-aware revocation, the seven-field account pin; 0.4: planner 1.3.0, account modes and the account pin; revocation flows tied to fork tests) |
| Status | DRAFT |
| Owner | Wallet Protocol / Account-Abstraction Engineer (planner), Principal Architect (layers) |
| Reviewers | Head of Security, Solidity Lead, QA Lead, Product Designer |
| Dependencies | [02](02-source-register.md) CLM-001…008, 010…016, 020…033, 040…043, 050…053; [04](04-context-and-trust-boundaries.md) TM-01…TM-18; [09](09-capability-boundaries.md); [10](10-pay-once-protocol.md); [11](11-dual-cap-model.md); [12](12-router-lifecycle-and-migration.md); [13](13-eip7702-delegation-inspection.md); [17](17-account-compatibility-policy.md) |
| Labels | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` |
| Evidence floor | **E1.** No wallet-support statement here is E3. Wallet rows in §10 are `UNTESTED`. |
| Definition of Done | Two independent implementations pass all golden vectors (§9) byte-for-byte; the wallet lab (EV-P03, EV-P07…P09) has confirmed or corrected every capability assumption; Security has signed off the Layer 2/3 bounds. |

**Scope of this document.** Capability discovery (shared by both protocols) and **Protocol B — FastPay recurring authorization**: Permit2 `AllowanceTransfer` plus a scoped mandate. **Pay Once is a different protocol** (Permit2 `SignatureTransfer`, no mandate, no standing allowance) specified in [10](10-pay-once-protocol.md).

## 0. Changes since v0.1

| Change | Reason |
|---|---|
| Pay Once moved to [10](10-pay-once-protocol.md) and rebuilt on `SignatureTransfer` | Separate protocols (S-1…S-4) |
| EIP-7702 text corrected: delegation is persistent; inspection and recording added ([13](13-eip7702-delegation-inspection.md)) | CLM-016 |
| New `sig1271` gate: signature transports need a verified ERC-1271 path for code-bearing accounts | CLM-050 |
| R-L2-NO-MAX: never set a Layer 2 amount to `2^160−1` | CLM-052 (Permit2 treats it as unlimited and never decrements) |
| **Conversion code is absent from Router v1**: the planner input carries `router.capabilities.conversion` (false for Router v1) and every `SWAP_ONLY` token is dropped with `ROUTER_LACKS_CONVERSION`; the v0.2 gates G1–G3 are removed | [09](09-capability-boundaries.md) §0, §4 |
| Revocation flows specified: **transactions are primary**; the zero-amount signed `permit` is **experimental** | §2.1 |
| Migration is mandate lineage (a successor mandate), not a rebind | [12](12-router-lifecycle-and-migration.md) |
| Unattended charges revalidate the account before every attempt; `DELEGATION_UNVERIFIED` | [13 §7](13-eip7702-delegation-inspection.md) |
| Cap derivation uses the dual cap model | [11](11-dual-cap-model.md) |
| **v0.4:** account classes become the five **account modes** of the Account Compatibility Policy; the plan carries an **account pin** (planner 1.3.0, TV-27…TV-30, ACP-TV) | [17](17-account-compatibility-policy.md) |
| **v0.4:** the primary Permit2 revocation flow is defined by fork-tested primitives (RV-T01…RV-T12); the zero-amount signed permit stays disabled until ZP-T01…ZP-T08 and the wallet lab pass | §2.2 |
| **v0.5:** the L2 allowance is **shared** per `(owner, token, router)`; sizing is from the sum over a customer's live mandates on the router (R-L2-SHARED), a normal migration plan never revokes a pair a sibling uses (NC-20, NC-21); planner 1.4.0, TV-31…TV-36 | §2.1, §6.1, [12 §5.3.1](12-router-lifecycle-and-migration.md) |
| **v0.5:** the plan carries the seven-field `AccountPin` (mode, account code hash, delegate, delegate code hash, family, version, signature mode) | §5.1, [17 §5](17-account-compatibility-policy.md) |
| MetaMask evidence upgraded from "unconfirmed" to "documented" (E1); runtime detection still mandatory; Trust Wallet stays `UNKNOWN` | CLM-040, CLM-043 |

## 1. Fixed points from sources

| Fact | Ref | Consequence for the design |
|---|---|---|
| A standard ERC-20 needs a one-time approval **to Permit2** before Permit2 can move it. | CLM-025 | A one-confirmation activation exists **only** if the account can batch that approval with the rest. Otherwise the flow is truthfully multi-step. |
| A Permit2 `AllowanceTransfer` permit names token, `uint160` amount, `uint48` expiration and spender — **not** a merchant, cadence or recipient. | CLM-026 | Merchant, cadence, recipient and caps live in FastPay's contracts (Layer 3). |
| `AllowanceTransfer`: `approve`/`lockdown`/`invalidateNonces` act on the caller's own allowances; `permit` is open to any caller with a valid owner signature; `transferFrom` is spender-only; **`uint160.max` is "unlimited" and never decremented**. A zero-amount signed `permit` *should* revoke, but that is an inference (EV-P08) and is treated as **experimental**. | CLM-052 | R-L2-NO-MAX; revocation flows §2.1 (transactions are primary). |
| Permit2 verifies signers **with code** only via ERC-1271 and never falls back to `ecrecover`. | CLM-050 | A 7702-delegated EOA's signature flows depend on its delegate (§4, [13](13-eip7702-delegation-inspection.md)). |
| `atomic` capability is reported per chain as `supported`/`ready`/`unsupported`; absence means unsupported. `atomicRequired:true` makes the wallet execute atomically or upgrade first. | CLM-003/004 | Capability drives transport choice. |
| MetaMask's official docs describe `supported`/`ready`, a wallet-driven upgrade to a MetaMask smart account, atomic-only `wallet_sendCalls`, and an unlisted Avalanche; they do not name the delegate or state persistence. | CLM-040/043 | Documented, not proven: detect at runtime and **record the delegate** ([13](13-eip7702-delegation-inspection.md)). |
| `wallet_getCapabilities` errors with `4100` when the account is not authorized. | CLM-005 | `4100` ⇒ **UNKNOWN**, never "unsupported". |
| Batch status codes 100/200/400/500/600 and an `atomic` flag in `wallet_getCallsStatus`. | CLM-006 | The planner re-plans from **chain state**; wallet responses are hints (TM-06). |
| **7702 delegation is persistent state**, overwritten by a later authorization, cleared by delegating to the zero address, not rolled back if a transaction fails; `chain_id=0` is valid on every chain. | CLM-011/016 | FastPay never requests raw authorizations (ADR-007) and records the resulting delegation. |
| ERC-2612 permits are signature based and can be front-run or withheld; ERC-3009 and ERC-7715 are Drafts. | CLM-030/031/033 | Native permit is a verified-token optimization; Drafts are optional adapters (CF-005). |

## 2. Protocol B: the three authorization layers

| Layer | Object on chain | Who sets it | Bounded by | Gasless revoke? | How the customer revokes |
|---|---|---|---|---|---|
| **L1** | ERC-20 `allowance(owner, Permit2)` | Customer (tx, batch, or ERC-2612 signature) | Planner sizes it to the L2 need (OD-005) | No (tx) | `approve(Permit2, 0)` |
| **L2** | Permit2 `allowance(owner, token, router)` = `(amount, expiration, nonce)` | Customer (tx via `approve`, or signature via `permit`) | `amount ≤ maxInputOverHorizon` (never `uint160.max`), `expiration ≤ min(mandate end, horizon)` (OD-017) | **No** (transaction). A signed zero-amount `permit` is **experimental** (§2.1) | `lockdown`, `approve(token, router, 0, 0)` |
| **L3** | `MandateManager` record: merchant, tokens, **dual caps** ([11](11-dual-cap-model.md)), cadence, expiry, router binding, `termsHash` | Customer (tx via `activate`, or signature via `activateBySig`) | Everything in prompt §8 | **Yes**: `revokeBySig`, `pauseBySig` | `revoke`, `pause`, `reduce` |

Invariants tying the layers together:

- `I-MANDATE`: the router cannot pull a token for a customer unless an `ACTIVE` mandate bound to **that router** authorizes that token, merchant, amount and time. A dangling L2 grant without an active mandate is inert.
- `I-EXIT`: L3 revoke/pause/successor creation and Permit2 lockdown are never blocked by pause, governance or any FastPay component (TM-14).
- "Revoke all" in the portal is L3 revoke + L2 lockdown, in one batch when the wallet can; otherwise L3 first (stops charges), then L2.
- Protocol B never calls `SignatureTransfer`; Pay Once never calls `AllowanceTransfer` or creates a mandate (S-1, S-2).

### 2.1 Revocation flows (authoritative)

**Transactions are the primary supported flows. Any signature-based revocation of a Permit2 allowance is experimental until verified (EV-P08, EV-P11).**

| Layer | **Primary supported** | Secondary | **Experimental** (flag off) |
|---|---|---|---|
| L1 ERC-20 allowance to Permit2 | `token.approve(Permit2, 0)` — a customer transaction (or a batch call). For `ZERO_FIRST` tokens this is also the first half of any re-approval | — | A signed ERC-2612 `permit(owner, Permit2, 0, …)` for registry-verified tokens only |
| L2 Permit2 allowance to a router | `Permit2.lockdown([(token, router)…])` — a customer transaction, batched when the wallet can. Effect: amount set to 0; expiration and nonce unchanged (CLM-052) | `Permit2.approve(token, router, 0, 0)` (transaction) | **A signed `PermitSingle`/`PermitBatch` with amount 0** submitted by a relayer (needs the correct nonce, a signature that Permit2 accepts for the account, and EV-P08 evidence). Flag `revocation.zeroPermit.enabled`, default **off**, never the primary flow |
| Unsubmitted signed permits | `Permit2.invalidateNonces(token, router, newNonce)` (AllowanceTransfer; at most +65,535 per call) or `invalidateUnorderedNonces` (SignatureTransfer) — transactions | — | — |
| L3 mandate | `MandateManager.revoke` (transaction) **or** `revokeBySig` (EIP-712, relayed, gasless — FastPay's own contract, covered by the audit and invariants) | — | — |

Consequences for the plans:

- "Revoke all" in the portal is: L3 revoke (gasless via `revokeBySig`) **first**, which stops charges immediately, then L2 `lockdown` as a transaction (batched when possible), then optionally L1.
- A migration's old-permission revocation ([12](12-router-lifecycle-and-migration.md) S2) is a **transaction** (`lockdown`) for **the pairs the migration mode requires** (all exposed tokens in an emergency or a full migration; only the tokens no sibling uses in a partial normal migration; none when every token is shared); a plan that is otherwise signature-based becomes MIXED (one transaction plus signatures). **`lockdown` and `approve(…,0,0)` act on the `(token, router)` pair, which every mandate of the customer on that router and token shares** (`AllowanceTransfer.sol:97-110` at the pinned commit): the planner therefore never emits one for a pair a sibling still uses in a normal migration (NC-20). The planner never emits a zero-amount permit step unless the experimental flag is on for that wallet, token and chain.
- The planner never claims "gasless" for anything involving L1 or L2 revocation.
- Each primary flow needs evidence per supported token and chain: `lockdown` and `approve(…,0,0)` on a fork at the pinned commit; token `approve(0)` for each listed token including `ZERO_FIRST` and no-return tokens (EV-P11).

### 2.2 The primary Permit2 revocation flow, defined by tested primitives

**Primary flow (L2).** The customer, as the Permit2 owner, calls `Permit2.lockdown([(token₁, router), …, (tokenₙ, router)])` — **one transaction for every token of the mandate**, inside the activation or revocation batch where the wallet batches. Effect (CLM-052, E1 until the pinned-commit review): for each pair the stored `amount` becomes 0; `expiration` and `nonce` are unchanged; event `Lockdown`. A later `transferFrom` by the router reverts (`InsufficientAllowance`). Unsubmitted signed permits are killed separately with `invalidateNonces`. Alongside it FastPay's `revoke`/`revokeBySig` (L3) stops charges at once and gaslessly.

**Why lockdown is primary.** It is a single call that takes an array (cost grows with tokens, not with calls), it cannot be front-run into harm (it only acts on the caller's own allowances), and it does not depend on a signature scheme or on the account having working ERC-1271. `approve(token, router, 0, 0)` is the secondary flow for wallets that cannot send the array call.

**The tests that make these primitives "tested"** (fork tests at the pinned Permit2 commit; `EPIC-P1-REVOKE`; evidence EV-P11). All must pass for the token and chain before the flow is described as supported:

| RV-T | Setup | Action | Expected |
|---|---|---|---|
| 01 | Owner `O` has L1 allowance to Permit2 and `Permit2.approve(token, R, A, E)` with `E` in the future | `O: lockdown([(token, R)])` | `allowance(O, token, R).amount = 0`; `expiration`, `nonce` unchanged; `Lockdown` emitted; `R.transferFrom(O, to, 1, token)` reverts `InsufficientAllowance(0)` |
| 02 | As 01 with amount `uint160.max` | lockdown | amount becomes 0 (not unlimited); transfer reverts |
| 03 | Two tokens with allowances to `R` and one to another spender `R′` | one lockdown call with both `(t, R)` pairs | both `R` allowances 0; `R′` untouched |
| 04 | Allowance already expired | lockdown | no revert; amount 0 |
| 05 | No allowance exists | lockdown | no revert; amount 0 |
| 06 | An attacker calls lockdown naming `(token, R)` | — | only the attacker's own allowances change; `O`'s is unchanged |
| 07 | Allowance created by a signed `permit` (nonce consumed) | lockdown | as 01; replaying the old signature fails on the nonce |
| 08 | Secondary: `O: approve(token, R, 0, 0)` | — | amount 0; stored expiration = `block.timestamp`; `Approval` emitted; transfer reverts |
| 09 | A signed `PermitSingle` (nonce `n`) not yet submitted | `O: invalidateNonces(token, R, n+1)`; relayer submits the permit | Permit reverts (invalid nonce); allowance unchanged |
| 10 | `invalidateNonces` with a delta of 65,536 | — | Reverts `ExcessiveInvalidation` |
| 11 | RV-T01 repeated for: a plain EOA (transaction), a 7702-delegated EOA (call from the account) and a contract account (call from the account) | — | Same state; `msg.sender` seen by Permit2 is the account |
| 12 | L1: `token.approve(Permit2, 0)` for a standard token, a no-return token and an approve-zero-first token | — | L1 allowance 0; a Permit2 pull then fails |

**The zero-amount signed `permit` stays disabled** (`revocation.zeroPermit.enabled = off`). Enabling it for a chain, token and wallet needs all of ZP-T01…ZP-T08 on a fork **and** the wallet-lab run WL-31 for that wallet, recorded with evidence ids, plus two approvers in the flag service:

| ZP-T | Case | Expected if the flow is usable |
|---|---|---|
| 01 | Plain EOA signs `PermitSingle` with amount 0 and the current nonce; a relayer submits | Amount 0; nonce `n+1` |
| 02 | As 01 with expiration 0 | Stored expiration = `block.timestamp` (not 0 meaning "never") |
| 03 | Wrong nonce | Reverts |
| 04 | `sigDeadline` passed | Reverts |
| 05 | Contract account with a working `isValidSignature` signs | Accepted |
| 06 | 7702-delegated account whose delegate has no working `isValidSignature` | Rejected (CLM-050: no `ecrecover` fallback for signers with code) |
| 07 | An attacker front-runs by submitting the same signed permit first | Same effect, no harm |
| 08 | Interaction with a previously signed positive permit | Cannot resurrect the allowance after the nonce moved |

Until these pass the planner's validator rejects any plan step of this kind (NC-17).


## 3. Capability discovery

### 3.1 Normalized capability profile

Raw wallet output is reduced to a closed enum **before** it reaches the planner. The normalization is part of the specification so two implementations start from the same canonical input.

```text
CapabilityProfile {
  sendCalls:   YES | NO | UNKNOWN
  batch:       ATOMIC_SUPPORTED | ATOMIC_READY | NONE | UNKNOWN
  typedData:   V4 | NONE | UNKNOWN          # eth_signTypedData_v4
  paymaster:   PRESENT | ABSENT | UNKNOWN   # informative only (CLM-008)
  uncertain:   bool                         # true if any field is UNKNOWN after one retry
}
```

| Raw observation | Normalized |
|---|---|
| `wallet_getCapabilities` returns `atomic.status == "supported"` for the chain | `batch = ATOMIC_SUPPORTED`, `sendCalls = YES` |
| `atomic.status == "ready"` | `batch = ATOMIC_READY`, `sendCalls = YES` |
| `atomic.status == "unsupported"`, or no `atomic` entry for the chain (CLM-003; MetaMask omits such chains, CLM-040) | `batch = NONE` (`sendCalls = YES` only if the method exists) |
| Method not found (`-32601` or wallet-specific unsupported-method code) | `sendCalls = NO`, `batch = NONE` |
| Error `4100` (CLM-005), timeout, transport error | `UNKNOWN`; **re-query once after the account is authorized**; if still unknown → planned as `NONE` with `uncertain = true` |
| `eth_signTypedData_v4` available per provider or per Compatibility Register row | `typedData = V4`; absent → `NONE`; not determinable → `UNKNOWN` (planned as `NONE`) |

Rules:

1. `wallet_getCapabilities` is called only after `eth_requestAccounts` succeeds, with the connected account and the target chain.
2. Capabilities are re-read per session and per chain; never cached across accounts.
3. A capability claim is a **hint**: before relying on it for a money decision the plan carries a post-execution verification (§8). A wallet that returns `atomic:false` after being asked for `atomicRequired:true` is recorded `ATOMIC_VIOLATING` for that wallet version and demoted to `NONE` until retested. (MetaMask's docs say `atomic` is always `true` on success, CLM-043; FastPay still checks.)
4. Vendor documentation, however official, never substitutes for a lab row (§10).

### 3.2 `wallet_sendCalls` request profile

```json
{
  "method": "wallet_sendCalls",
  "params": [{
    "version": "2.0.0",
    "id": "<derived from planId; optional>",
    "from": "<account>",
    "chainId": "0x2105",
    "atomicRequired": true,
    "calls": [
      { "to": "<token>",   "data": "<approve(Permit2, l1Amount)>",            "value": "0x0" },
      { "to": "<Permit2>", "data": "<approve(token, router, l2Amount, exp)>", "value": "0x0" },
      { "to": "<MandateManager>", "data": "<activate(mandate)>",              "value": "0x0" }
    ]
  }]
}
```

- `version` follows the examples in SRC-001 and MetaMask's docs (`"2.0.0"`); confirm at pin time (RP-01).
- `chainId` is hex with no leading zeros (`0x2105` is shown only as an example format).
- `atomicRequired:true` is **always** set for the activation batch.
- A deterministic `id` makes a double-click a duplicate-ID error (`5720`, CLM-007): defense in depth; the session lock is the primary guard.
- `value` is always `0x0`. No call targets anything except the token, Permit2, or a FastPay contract at the verified address from the signed deployment manifest.
- `paymasterService` may be attached with `optional:true` only for FastPay-operated sponsors under OD-002.

### 3.3 EIP-7702: stance in one paragraph

Delegation is **persistent account state** set by a wallet-signed authorization; it is not scoped to a call, batch or session ([13](13-eip7702-delegation-inspection.md) §1). FastPay prefers wallet-managed upgrades through capability discovery: it requests `atomicRequired:true` and lets the wallet decide whether to offer an upgrade. FastPay never builds, requests or asks for a signature over an authorization, never uses `chain_id = 0`, and ships no delegate. FastPay **does** inspect and record, from chain state, the resulting delegation implementation, bytecode hash, account state, revocation path and compatibility evidence, and refuses or restricts flows according to the policy table in [13 §5](13-eip7702-delegation-inspection.md). A rejected upgrade surfaces as `5750` (CLM-007) and the planner re-plans without batch for the session. Because delegation persists and can change, **every unattended charge is checked by the Account Compatibility Policy: the chain refuses it unless the account's code still matches the customer's pin, and the backend revalidates the account against verified evidence and pauses the mandate as `DELEGATION_UNVERIFIED` on any difference** ([17](17-account-compatibility-policy.md), [13 §7](13-eip7702-delegation-inspection.md)).

## 4. Account modes, classes and the `sig1271` gate

**Modes** (authoritative; [17 §2–§3](17-account-compatibility-policy.md)): `PLAIN_EOA`, `EOA_7702_VERIFIED`, `SMART_4337`, `WALLET_1271`, `UNKNOWN_CODE`, or no mode (`INDETERMINATE`) when sources disagree. Recurring activation and unattended charges are permitted only in the first four, subject to the pin and the per-mode rules; `UNKNOWN_CODE` is refused for recurring (`ACCOUNT_MODE_UNKNOWN`). The planner takes `account.mode` from the Account Compatibility Policy engine and never computes it itself.

Classes (the delegation-inspection view, [13 §3](13-eip7702-delegation-inspection.md); mapped to modes in [13 §5](13-eip7702-delegation-inspection.md)):

| Class | Detection | Policy default |
|---|---|---|
| `EOA` | empty code | Allowed; signature flows allowed |
| `EOA_7702_KNOWN` | code is exactly 23 bytes `0xef0100 ‖ delegate` and delegate address **and** code hash are allowlisted at E3 | Allowed; **signature flows only if `sig1271 = VERIFIED`** |
| `EOA_7702_UNKNOWN` | 23-byte designator, delegate not allowlisted | **Refused** for FastPay mode; Pay Once allowed with warning (`msg.sender` flows only) |
| `SMART_ACCOUNT_KNOWN` | other code; implementation allowlisted | Allowed; signature flows only if `sig1271 = VERIFIED` |
| `SMART_ACCOUNT_UNKNOWN` | other code; not allowlisted | Refused for FastPay mode |
| `COUNTERFACTUAL` | no code but wallet declares a smart account | Refused in v1 |
| `UNKNOWN` | sources disagree | Refused |

`sig1271 ∈ {VERIFIED, UNVERIFIED, NA}`: `NA` for `EOA`; `VERIFIED` only when the Compatibility Register has an E3 row proving real Permit2 signatures validate for this delegate + code hash + wallet version **and** the per-signature pre-flight passes. `sigAllowed(account) = (class == EOA) OR (sig1271 == VERIFIED)`.

## 5. Canonical input and determinism

The planner is a **pure function**: no network, no clock, no randomness. Two independent implementations must produce identical output bytes for identical input bytes.

### 5.1 Input

```text
CanonicalInput {
  plannerVersion:   "1.4.0"
  now:              uint (unix seconds)                 # supplied, not read
  chain:            { id, enabled, registryVersion,
                      permit2: {address, verified},     # verified = code hash matched (EV-P01)
                      router:  {address, verified, version, lifecycle,    # lifecycle from RouterRegistry
                                capabilities: { conversion: false } },    # false for every Router v1 (code absent)
                      mandateManager: {address, verified} }
  account:          { address, class, observedAt, delegationRecordHash,
                      mode: PLAIN_EOA | EOA_7702_VERIFIED | SMART_4337 | WALLET_1271 | UNKNOWN_CODE,
                      codeHash,                              # observed EXTCODEHASH (0x0 for an empty account)
                      delegate, delegateCodeHash,            # mode EOA_7702_VERIFIED: the designator's delegate and EXTCODEHASH(delegate)
                      implementationFamily,                  # from the E3 Compatibility Register row ("0x0" for PLAIN_EOA)
                      pinVersion,                            # of the lineage (1 for a new lineage)
                      signatureMode: DIRECT_ONLY | ECDSA_KEY | ERC1271,    # chosen by policy; see 17 section 5.1
                      expectedDelegateAfterUpgrade | null,   # from an E3 Compatibility Register row; needed for ATOMIC_READY
                      sig1271: VERIFIED | UNVERIFIED | NA }
  caps:             CapabilityProfile                   # 3.1
  terms:            { merchantId, startsAt, expiresAt, termsHash, settlementToken, periodSeconds | null,
                      fiat: { currency, perPaymentMinor, windows{}, totalMinor } | null, boundsVersion }
  selected[]:       { address, priority, balance, erc20AllowanceToPermit2,
                      permit2: {amount, expiration, nonce},          # the SHARED slot (owner, token, router)
                      shared: { liveCount, siblingNeed, siblingExpiry },   # other live mandates of this customer on this router and token,
                                                                    # read from the exposure index at the same block (12 section 5.3.1)
                      maxInputOverHorizon }             # 6.1, derived with 11 section 7
  registry:         { version, tokens: { address -> { status, decimals, approveQuirk,
                      nativePermit: NONE|EIP2612_VERIFIED, bytecodeHashVerified,
                      bounds: { currency -> {min, max} } } } }       # no route class or lab approval in v1
  policy:           { maxTokensPerMandate, l2HorizonSeconds, sigTtlSeconds, relayedActivation,
                      allowWalletUpgrade, restrictedAccounts, delegationRecordTtlSeconds,
                      minMandateLifetimeSeconds, l1Mode: "BOUNDED" }
  gas:              { gasPriceWei, perStepGas: {...}, nativeBalanceWei, sponsorPolicy }
}
```

### 5.2 Normalization rules

1. JSON Canonicalization (RFC 8785). All integers as decimal strings. Addresses lowercase hex (EIP-55 is display only).
2. Arrays whose order is not semantic (`selected`, registry maps) are sorted by `address` ascending **before** hashing.
3. `planId = keccak256(JCS(CanonicalInput))`.
4. Output carries `plannerVersion` and `planId`. Equality of two implementations = equality of `JCS(output)`.
5. Ties in a sort are broken by address ascending. Prices and fiat values are **never** inputs to path choice; they appear only in display fields computed after planning.

## 6. Needs, sizing and token selection

### 6.1 Sizing rules

For each kept token `t` (integer arithmetic, atomic units):

```text
l2Expiry        = min(terms.expiresAt, now + policy.l2HorizonSeconds)                      # OD-017
maxInputOverHorizon[t]  (from the Mandate compiler, see 11 section 7) =
        min( tokenCaps.totalMax[t],
             tokenCaps.periodMax[t] * ceil(max(0, l2Expiry - startsAt) / periodSeconds) )   # fixed cadence; 0 if empty
l2Amount[t]     = maxInputOverHorizon[t] + shared[t].siblingNeed      # SHARED slot: the sum over live mandates (R-L2-SHARED)
                                                                    # must be 0 < l2Amount < 2^160 - 1  (R-L2-NO-MAX)
l2ExpiryT[t]    = max(l2Expiry, shared[t].siblingExpiry)             # never earlier than a sibling needs
l1Amount[t]     = l2Amount[t]                                                              # BOUNDED mode, OD-005
needL1[t]       = erc20AllowanceToPermit2[t] <  l1Amount[t]
needL2[t]       = !(permit2[t].amount >= l2Amount[t] && permit2[t].expiration >= l2ExpiryT[t])
```

Rules:

- **R-L2-NO-MAX**: if `l2Amount ≥ 2^160 − 1` the plan is refused (`L2_AMOUNT_UNREPRESENTABLE`). Permit2 stores `uint160.max` as an unlimited allowance that is never decremented (CLM-052); FastPay never creates one, and a pre-existing larger value on a different spender is irrelevant.
- **R-L1-NEVER-DECREASE**: the planner never lowers an existing L1 or L2 value in an activation or a revision. Larger existing values are left alone and surfaced as `W-UNLIMITED-EXISTING`: L1 is shared with other apps the customer uses. The only L2 decreases are the customer's own revocation steps (`lockdown`, `approve(…,0,0)`, the right-sizing S2′ of [12 §5.4](12-router-lifecycle-and-migration.md)), each computed so that no sibling is pushed below its need (R-L2-SHARED).
- **R-L2-SET-NOT-ADD**: Permit2 `approve`/`permit` set the allowance; they do not add. The planner emits the target value.
- **R-L2-SHARED**: the L2 slot `(owner, token, router)` is **shared by every live mandate of the customer on that router that uses the token** (Permit2 key; `AllowanceTransfer.sol:23`, and `approve` **overwrites** amount and expiration, `AllowanceTransfer.sol:26-30`). The target of every `approve`/`permit` is therefore `l2Amount` and `l2ExpiryT` above — the new mandate's need **plus** `siblingNeed` and the later of the two expiries — never the new mandate's need alone; a step whose value would leave a sibling short is refused (`NC-21`). `shared` is read from the on-chain exposure index and the `Approval`/`Permit` events at one block; if the index and the indexer disagree the plan is refused (`SHARED_STATE_INDETERMINATE`). Also refused: a plan that would take the customer past `MAX_EXPOSED_TOKENS_PER_ROUTER` tokens on the router (`EXPOSURE_LIMIT`).
- **R-ZERO-FIRST**: if `approveQuirk == ZERO_FIRST` and the current L1 is non-zero and below need, emit `approve(0)` then `approve(l1Amount)`.
- **R-DEADLINE**: every signature's deadline = `now + policy.sigTtlSeconds` (default proposal 900 s). An unsubmitted signed permit is a bearer instrument until it expires; `invalidateNonces` can kill it earlier (CLM-026/052).
- **R-CAP-INTEGRITY**: `l2Amount` never exceeds what the **live mandates'** on-chain caps on this router could consume over the horizon (the sum over the new mandate and its siblings), so L2 never exceeds the sum of the L3 caps it serves.
- **R-HORIZON-WARN**: if `l2Expiry < terms.expiresAt`, emit `W-RENEWAL` with the renewal date.

### 6.2 Token eligibility

A selected token is kept only if all hold; otherwise it is dropped with `TOKEN_DROPPED:<reason>`:

| Check | Reason code |
|---|---|
| In registry for `chain.id` at `registry.version` | `NOT_IN_REGISTRY` |
| `bytecodeHashVerified` | `BYTECODE_DRIFT` |
| Status `SETTLEMENT` or `DIRECT_PAYMENT` (direct settlement, no conversion) | `STATUS_<status>` |
| Status `SWAP_ONLY` is **never** eligible on a router whose `capabilities.conversion` is false (every Router v1) | `ROUTER_LACKS_CONVERSION` |
| Listed in the mandate's allowed tokens | `NOT_IN_MANDATE` |
| `maxInputOverHorizon > 0` | `ZERO_CAP` |
| If the mandate has fiat caps: the token has price bounds for `terms.fiat.currency` | `NO_PRICE_BOUNDS` |
| `balance > 0` or explicitly selected (warning `W-ZERO-BALANCE`) | `ZERO_BALANCE` |

Conversion tokens become eligible only in a future planner version that targets a conversion-capable router (Router v1.1, [09](09-capability-boundaries.md)); the conditions then are C1 (the mandate is bound to such a router), C2 (on-chain conversion policy) and the rollout switch R, which can only narrow. **No feature flag is a security boundary**: in this planner version there is nothing for a flag to enable.

Kept tokens are sorted by `(priority asc, tier asc [SETTLEMENT=0, DIRECT_PAYMENT=1], address asc)` and truncated to `policy.maxTokensPerMandate` (`OVER_LIMIT`). Default UI pre-selection is not part of the planner.

## 7. Decision tree for FastPay activation (Protocol B)

```text
START
 |
 +-- Gate fails? (chain disabled; Permit2/router/mandate manager unverified; router lifecycle not ACTIVE;
 |                registry mismatch; account class refused; delegation record stale;
 |                mandate window invalid)                        yes --> REFUSE(reason)   [no wallet prompt]
 |
 +-- Select tokens (6.2).  None eligible? --yes--> REFUSE(NO_ELIGIBLE_TOKENS)
 |
 +-- Compute needs per token (6.1): needL1, needL2
 |
 +-- Nothing to do at L1/L2?  (only L3 missing)
 |        yes --> relayed (typedData=V4, relayedActivation, sigAllowed)?
 |                 yes: SIGN_ONLY      path B   1 signature, 0 customer gas
 |                 no : DIRECT_TX      path B   1 transaction
 |
 +-- batch = ATOMIC_SUPPORTED?              yes --> ATOMIC_BATCH          path A   1 prompt
 |
 +-- batch = ATOMIC_READY and wallet upgrade allowed?
 |                                          yes --> ATOMIC_BATCH + W-UPGRADE   path A   1-2 prompts
 |
 +-- relayed (typedData=V4 and relayedActivation and sigAllowed)?
 |        yes --> RELAYED_SIGNATURES
 |                 path B: L1 already satisfied (L2 + L3 by signature, 0 gas)
 |                 path C: every missing L1 covered by a verified native permit (0 customer txs)
 |                 path D: some L1 needs an approve tx (n txs, then signatures)
 |
 +-- else --> TX_SEQUENCE                  path D   (nL1 + nL2 + 1 transactions)
```

Path labels (prompt §9 A–D):

```text
path = A  if transport == ATOMIC_BATCH
       B  if no L1 work is required (existing allowances; remaining steps are L2/L3 only)
       C  if transport == RELAYED_SIGNATURES and approveTxCount == 0 and nativePermitCount >= 1
       D  otherwise
```

The "existing allowances" reduction is applied **inside every transport**; flag `EXISTING_ALLOWANCES_APPLIED` records it.

### 7.1 Pseudocode (normative)

```python
def plan(inp):                                   # pure; inp is CanonicalInput
    c, a = inp.chain, inp.account
    # ---- Stage 0: gates. First failing gate wins; this order is normative.
    if not c.enabled:                                  return refuse("CHAIN_DISABLED")
    if not c.permit2.verified:                         return refuse("PERMIT2_UNVERIFIED")
    if not (c.router.verified and c.mandateManager.verified):
                                                       return refuse("CONTRACT_UNVERIFIED")
    if c.router.lifecycle != "ACTIVE":                 return refuse("ROUTER_NOT_ACTIVE")
    if inp.registry.version != c.registryVersion:      return refuse("REGISTRY_VERSION_MISMATCH")
    if a.class_ == "COUNTERFACTUAL":                   return refuse("ACCOUNT_COUNTERFACTUAL")
    if a.mode is None:                                 return refuse("ACCOUNT_INDETERMINATE")      # sources disagree (17 section 2)
    if a.mode == "UNKNOWN_CODE":                       return refuse("ACCOUNT_MODE_UNKNOWN")      # never planned for recurring
    if inp.now - a.observedAt > inp.policy.delegationRecordTtlSeconds:
                                                       return refuse("DELEGATION_RECORD_STALE")
    if inp.terms.expiresAt < inp.now + inp.policy.minMandateLifetimeSeconds:
                                                       return refuse("MANDATE_WINDOW_INVALID")

    # ---- Stage 1: tokens
    kept, warnings = [], []
    for t in sorted(inp.selected, key=lambda t: t.address):
        why = ineligible(t, inp)                       # 6.2; None if eligible
        if why: warnings.append(("TOKEN_DROPPED", t.address, why)); continue
        kept.append(t)
    kept.sort(key=lambda t: (t.priority, TIER[reg(t).status], t.address))
    for t in kept[inp.policy.maxTokensPerMandate:]:
        warnings.append(("TOKEN_DROPPED", t.address, "OVER_LIMIT"))
    kept = kept[:inp.policy.maxTokensPerMandate]
    if not kept:                                       return refuse("NO_ELIGIBLE_TOKENS")

    # ---- Stage 2: needs (6.1)
    l2_expiry = min(inp.terms.expiresAt, inp.now + inp.policy.l2HorizonSeconds)
    for t in kept:
        if t.maxInputOverHorizon >= UINT160_MAX:       return refuse("L2_AMOUNT_UNREPRESENTABLE")   # R-L2-NO-MAX
        t.l2_amount = t.maxInputOverHorizon
        t.l1_amount = t.l2_amount
        t.need_l1   = t.erc20AllowanceToPermit2 < t.l1_amount
        t.need_l2   = not (t.permit2.amount >= t.l2_amount and t.permit2.expiration >= l2_expiry)
        t.permit_l1 = t.need_l1 and reg(t).nativePermit == "EIP2612_VERIFIED"
        t.zero_first = t.need_l1 and reg(t).approveQuirk == "ZERO_FIRST" \
                       and t.erc20AllowanceToPermit2 > 0
    any_l1 = any(t.need_l1 for t in kept)
    any_l2 = any(t.need_l2 for t in kept)

    # ---- Stage 3: transport. First match wins; this order is normative.
    k, pol, flags = inp.caps, inp.policy, set()
    sig_ok  = (a.mode == "PLAIN_EOA") or (a.sig1271 == "VERIFIED")
    relayed = (k.typedData == "V4" and pol.relayedActivation and sig_ok)
    upgrade_possible = (k.batch == "ATOMIC_READY" and k.sendCalls == "YES" and pol.allowWalletUpgrade)
    if upgrade_possible and a.expectedDelegateAfterUpgrade is None:
        flags.add("ACCOUNT_PIN_UNPREDICTABLE")         # the pin after the wallet's upgrade cannot be named: do not request it
    if not any_l1 and not any_l2:
        transport = "SIGN_ONLY" if relayed else "DIRECT_TX"
    elif k.batch == "ATOMIC_SUPPORTED" and k.sendCalls == "YES":
        transport = "ATOMIC_BATCH"
    elif upgrade_possible and a.expectedDelegateAfterUpgrade is not None:
        transport = "ATOMIC_BATCH"; flags.add("WALLET_UPGRADE"); flags.add("WALLET_UPGRADE_PIN_PREDICTED")
    elif relayed:
        transport = "RELAYED_SIGNATURES"
    else:
        transport = "TX_SEQUENCE"

    # ---- Stage 3b: the account pin that the signed terms carry (17 section 5)
    pin = (keccak(0xef0100 + a.expectedDelegateAfterUpgrade) if "WALLET_UPGRADE" in flags       # the upgrade happens before the batch's calls
           else PIN_EOA if a.mode == "PLAIN_EOA"
           else a.codeHash)                                                                     # designator hash or contract (proxy) bytecode hash
    terms = inp.terms.with_pin(pin)

    # ---- Stage 4: steps (order is normative; token order = kept order)
    steps = []
    use_permit = (transport == "RELAYED_SIGNATURES")
    for t in kept:                                     # L1
        if not t.need_l1: continue
        if use_permit and t.permit_l1:
            steps.append(sig_token_permit(t, spender=c.permit2.address, deadline=inp.now+pol.sigTtlSeconds))
        else:
            if t.zero_first: steps.append(tx_approve(t, c.permit2.address, 0))
            steps.append(tx_approve(t, c.permit2.address, t.l1_amount))
    l2_missing = [t for t in kept if t.need_l2]        # L2
    if l2_missing:
        if transport in ("ATOMIC_BATCH", "TX_SEQUENCE"):
            for t in l2_missing: steps.append(tx_permit2_approve(t, c.router.address, t.l2_amount, l2_expiry))
        else:                                          # RELAYED_SIGNATURES
            steps.append(sig_permit2_batch(l2_missing, c.router.address, deadline=inp.now+pol.sigTtlSeconds))
    if transport in ("SIGN_ONLY", "RELAYED_SIGNATURES"):   # L3
        steps.append(sig_mandate(terms, deadline=inp.now+pol.sigTtlSeconds))
    else:
        steps.append(tx_activate(terms))               # msg.sender is the customer; the contract checks PIN_OK at execution

    approve_txs = count(s for s in steps if s.kind == "TX_APPROVE" and s.layer == 1)
    permits     = count(s for s in steps if s.kind == "SIG_TOKEN_PERMIT")
    path = ("A" if transport == "ATOMIC_BATCH" else
            "B" if not any_l1 else
            "C" if (transport == "RELAYED_SIGNATURES" and approve_txs == 0 and permits >= 1) else
            "D")
    if any((not t.need_l1) or (not t.need_l2) for t in kept):    # at least one L1/L2 step removed
        flags.add("EXISTING_ALLOWANCES_APPLIED")
    if k.uncertain:                  warnings.append(("W-UNKNOWN-CAPS",))
    if l2_expiry < inp.terms.expiresAt: warnings.append(("W-RENEWAL", l2_expiry))
    return Plan(planId=keccak(jcs(inp)), plannerVersion="1.3.0", transport=transport,
                path=path, atomic=(transport == "ATOMIC_BATCH"), flags=sorted(flags),
                tokens=kept, steps=steps, warnings=warnings, ...)  # 7.3
```

### 7.2 Bundling the first payment

`ATOMIC_BATCH` may append `PaymentRouter.chargeInitial(...)` (authenticated by `msg.sender == customer`) so activation and the first payment are one confirmation; selected by `terms.firstPaymentNow`. In `RELAYED_SIGNATURES` the first payment is a separate relayed charge after activation is verified.

### 7.3 Output: `ActivationPlan`

```json
{
  "plannerVersion": "1.3.0",
  "planId": "0x…",
  "outcome": "PLAN",
  "transport": "ATOMIC_BATCH",
  "path": "A",
  "atomic": true,
  "flags": ["EXISTING_ALLOWANCES_APPLIED"],
  "customerPrompts": { "min": 1, "max": 2 },
  "customerTxCount": 1,
  "account": { "class": "EOA_7702_KNOWN", "mode": "EOA_7702_VERIFIED", "pin": "0x…", "delegationRecordHash": "0x…", "sig1271": "UNVERIFIED" },
  "tokens": [
    { "address": "0x…", "l1Amount": "5000000000", "l2Amount": "5000000000",
      "l2Expiry": 1810000000, "needL1": false, "needL2": true }
  ],
  "steps": [
    { "index": 0, "kind": "TX_PERMIT2_APPROVE", "layer": 2, "to": "0x…", "dataHash": "0x…" },
    { "index": 1, "kind": "TX_ACTIVATE",        "layer": 3, "to": "0x…", "dataHash": "0x…" }
  ],
  "mandate": { "id": "0x…", "termsHash": "0x…", "routerVersion": 1, "accountPin": "0x…" },
  "gas": { "estimateWei": "…", "customerPaysWei": "…", "sponsoredWei": "0" },
  "prerequisites": ["NATIVE_GAS_AVAILABLE"],
  "warnings": [ { "code": "W-UNLIMITED-EXISTING", "token": "0x…" } ],
  "recovery": [ { "if": "STEP_1_FAILED", "do": "REPLAN" } ],
  "verification": ["V1", "V2", "V3", "V4"],
  "summary": { "key": "activation.atomic.v1", "params": { } }
}
```

**The pin** (`account.pin`, also in the signed terms) is `PIN_EOA` for `PLAIN_EOA`; `keccak256(0xef0100 ‖ delegate)` for `EOA_7702_VERIFIED` (and, for `ATOMIC_READY` with an upgrade, for the row's `expectedDelegateAfterUpgrade`); the observed `codeHash` for the contract modes. If a wallet will upgrade the account during the batch and no E3 row names the delegate, the pin cannot be predicted and the planner does not request the upgrade (`ACCOUNT_PIN_UNPREDICTABLE`, TV-30).

Refusal output: `{ "outcome": "REFUSE", "reason": "<code>", "plannerVersion", "planId" }`. `summary` is an i18n **key plus params**, never prose.

## 8. Execution, verification, resumability

1. **Session lock.** One activation session per `(account, chain, merchantId)`. While a step is pending, the same step cannot be issued again.
2. **State, not a script.** After every step and on every return visit the planner is re-run from chain state; completed steps vanish from the plan. This makes legacy flows resumable and prevents duplicate confirmations.
3. **Wallet status mapping** (CLM-006/007):

| Wallet says | Session action |
|---|---|
| `100` pending | `AWAITING_CHAIN`; poll; keep session lock |
| `200` confirmed | **Do not trust.** Run V1–V4; mandate becomes `ACTIVE` only after the chain shows it at the finality threshold |
| `400` offchain failure | Not submitted; re-plan; no state change |
| `500` complete revert | Nothing applied (atomic); show decoded reason; offer retry; after two reverts offer the next transport |
| `600` partial revert | Only possible if `atomic:false`; re-plan from chain state; if `atomicRequired` was `true`, record `ATOMIC_VIOLATING` |
| `4001` user rejected | `CANCELLED_BY_USER`; no retry loop |
| `5750` upgrade rejected | Re-plan with `batch = NONE` for this session |
| `5760` atomicity unsupported | Demote capability; re-plan |

4. **Verification (all required before `ACTIVE`):**
   - V1: ERC-20 `allowance(owner, Permit2) ≥ l1Amount` for each token that needed it.
   - V2: `Permit2.allowance(owner, token, router)` has `amount ≥ l2Amount` and `expiration ≥ l2Expiry`.
   - V3: `MandateManager` shows the mandate `ACTIVE`, bound to the intended router, with `termsHash` equal to the displayed terms, via `MandateActivated` at the finality threshold from ≥2 sources (TM-06).
   - **V4: a fresh delegation record** (if the wallet reported or performed an upgrade) is stored and compared with the pre-plan record ([13](13-eip7702-delegation-inspection.md)); an unexpected delegate demotes the account class for future plans.
5. **Recovery plan emitted with every plan:**
   - L2 granted but mandate not active → harmless (`I-MANDATE`); offer "finish activation" or "remove unused permission".
   - L1 granted but nothing else → leave; show in the portal with a one-tap revoke.
   - Signed but unsubmitted permits → expire at `sigDeadline`; the portal offers `invalidateNonces`.
6. **Pre-flight for signature transports**: the executor re-checks the account code hash and calls the account's `isValidSignature` on the actual signature before submitting ([13 §4](13-eip7702-delegation-inspection.md)).

## 9. Golden test vectors

Every implementation must pass these in CI, byte-for-byte on `JCS(output)`. Full JSON lives in `/planner/vectors/` (EPIC-P0-PLANNER). `Prompts` counts wallet confirmations.

| TV | Scenario (inputs that matter) | Transport | Path | Prompts | Customer txs | Notes |
|---|---|---|---|---|---|---|
| TV-01 | Fresh EOA. `batch=ATOMIC_SUPPORTED`. One token, L1=0, L2=0. | ATOMIC_BATCH | A | 1 | 1 batch | token approve, Permit2 approve, activate |
| TV-02 | As TV-01 but L1 already ≥ need | ATOMIC_BATCH | A | 1 | 1 batch | `EXISTING_ALLOWANCES_APPLIED`; `W-UNLIMITED-EXISTING` |
| TV-03 | `batch=NONE`, `typedData=V4`, EOA, token with verified ERC-2612, L1=0, L2=0 | RELAYED_SIGNATURES | C | 3 | 0 | sigs: token permit, Permit2 batch, mandate |
| TV-04 | As TV-03, no permit; `ZERO_FIRST`, existing L1 > 0 and < need | RELAYED_SIGNATURES | D | 4 | 2 | approve(0), approve(need), then 2 sigs |
| TV-05 | `batch=NONE`, `typedData=V4`, EOA, L1 satisfied, L2 missing | RELAYED_SIGNATURES | B | 2 | 0 | |
| TV-06 | Only L3 missing, EOA, `typedData=V4` | SIGN_ONLY | B | 1 | 0 | |
| TV-07 | `batch=ATOMIC_READY`, `allowWalletUpgrade=true` | ATOMIC_BATCH | A | 1–2 | 1 batch | `WALLET_UPGRADE`, `W-UPGRADE` |
| TV-08 | `batch=ATOMIC_READY`, `allowWalletUpgrade=false`, EOA, `typedData=V4` | RELAYED_SIGNATURES | C or D | n | m | Never requests an upgrade |
| TV-09 | Capabilities `UNKNOWN` after one retry | as `NONE` | | | | `W-UNKNOWN-CAPS` |
| TV-10 | `EOA_7702_UNKNOWN` (mode `UNKNOWN_CODE`), policy `REFUSE` | — | — | 0 | 0 | `REFUSE(ACCOUNT_MODE_UNKNOWN)` |
| TV-11 | `chain.permit2.verified=false` | — | — | 0 | 0 | `REFUSE(PERMIT2_UNVERIFIED)` |
| TV-12 | Three tokens: settlement stablecoin; `SWAP_ONLY` STABLE token; token not in registry (Router v1) | per remaining | | | | 1 token kept; `ROUTER_LACKS_CONVERSION`, `NOT_IN_REGISTRY` |
| TV-13 | `ZERO_FIRST` token inside an atomic batch | ATOMIC_BATCH | A | 1 | 1 batch | `approve(0)` precedes `approve(need)` |
| TV-14 | Mandate 24 months; `l2HorizonSeconds` = 13 months | per caps | | | | `l2Expiry = now + 13 months`; `W-RENEWAL` |
| TV-15 | Two tokens, equal `priority`, different tiers | any | | | | Order by tier then address |
| TV-16 | `now` one second either side of `expiresAt − minMandateLifetime` | — | | | | `PLAN` vs `REFUSE(MANDATE_WINDOW_INVALID)` |
| TV-17 | Same input, permuted `selected[]` | same | same | same | same | identical `planId` and output |
| TV-18 | `EOA_7702_KNOWN`, `sig1271=UNVERIFIED`, `batch=NONE`, `typedData=V4`, L1 missing | TX_SEQUENCE | D | n+m+1 | n+m+1 | signature transports refused for code-bearing accounts |
| TV-19 | As TV-18 with `sig1271=VERIFIED` | RELAYED_SIGNATURES | B/C/D | | | |
| TV-20 | `EOA_7702_KNOWN`, `batch=ATOMIC_SUPPORTED`, `sig1271=UNVERIFIED` | ATOMIC_BATCH | A | 1 | 1 batch | `msg.sender` flow works without ERC-1271 |
| TV-21 | `SWAP_ONLY` token with the rollout flag **on** and a registry lab approval present, on Router v1 | — | — | — | — | Still dropped: `ROUTER_LACKS_CONVERSION` (a flag cannot enable code that is absent) |
| TV-22 | `maxInputOverHorizon = 2^160 − 1` | — | — | 0 | 0 | `REFUSE(L2_AMOUNT_UNREPRESENTABLE)` |
| TV-23 | Delegation record older than the TTL | — | — | 0 | 0 | `REFUSE(DELEGATION_RECORD_STALE)` |
| TV-24 | Mandate has fiat caps; token has no bounds for the currency | | | | | `TOKEN_DROPPED(NO_PRICE_BOUNDS)` |
| TV-25 | Router lifecycle `DEPRECATED` | — | — | 0 | 0 | `REFUSE(ROUTER_NOT_ACTIVE)` for new mandates |
| TV-26 | Planner built for Router v1 receives `router.capabilities.conversion = true` | — | — | 0 | 0 | `REFUSE(PLANNER_VERSION_MISMATCH)`: a conversion-capable router needs the conversion-aware planner version |
| TV-27 | Fresh EOA, mode `PLAIN_EOA`, `codeHash = 0x0`; as TV-01 | ATOMIC_BATCH | A | 1 | 1 batch | `account.pin = PIN_EOA` in the signed terms |
| TV-28 | Mode `UNKNOWN_CODE` (code without an E3 row) | — | — | 0 | 0 | `REFUSE(ACCOUNT_MODE_UNKNOWN)` |
| TV-29 | `batch=ATOMIC_READY`, `allowWalletUpgrade=true`, `expectedDelegateAfterUpgrade = D1` | ATOMIC_BATCH | A | 1–2 | 1 batch | `WALLET_UPGRADE`; `account.pin = keccak256(0xef0100 ‖ D1)`; flag `WALLET_UPGRADE_PIN_PREDICTED` |
| TV-30 | As TV-29 with `expectedDelegateAfterUpgrade = null` | per remaining capability (never requests the upgrade, as TV-08) | | | | `ACCOUNT_PIN_UNPREDICTABLE`; pin `PIN_EOA`; the batch is planned as `NONE` |
| TV-31 | A second subscription on the same router and token; the shared slot holds 100 expiring at `T`; the new mandate needs 60 for a horizon ending at `T`, the sibling 100 | ATOMIC_BATCH or per capability | | | | `approve` target `l2Amount = 160` (not 60), `l2ExpiryT = max(T, sibling)`; flag `SHARED_ALLOWANCE_SIZED` |
| TV-32 | As TV-31 but the sum reaches `2^160 − 1` | — | — | 0 | 0 | `REFUSE(L2_AMOUNT_UNREPRESENTABLE)` |
| TV-33 | A new mandate would add a ninth distinct token on the router | — | — | 0 | 0 | `REFUSE(EXPOSURE_LIMIT)` |
| TV-34 | The exposure index and the indexer disagree on `siblingNeed` | — | — | 0 | 0 | `REFUSE(SHARED_STATE_INDETERMINATE)` |
| TV-35 | Mode `EOA_7702_VERIFIED`, delegate `D1`, `delegateCodeHash` and `implementationFamily` from the row | ATOMIC_BATCH or per capability | | | | The plan's `account.pin` has all seven fields with `accountCodeHash = H1`, `delegate = D1`, `pinVersion = 1`; `signatureMode = ERC1271` only if `sig1271 = VERIFIED`, else `DIRECT_ONLY` |
| TV-36 | `PLAIN_EOA` with `policy.signatureMode = ECDSA_KEY`; the same account after it became `EOA_7702_VERIFIED` (re-verification) | | | | | Pin 1: mode 1, `accountCodeHash = PIN_EOA`, `signatureMode = ECDSA_KEY`; pin 2: mode 2, `pinVersion = 2`; the planner never reuses a pin whose `PIN_OK` fails for the observed account |

Pay Once vectors are TV-PO-1…12 in [10 §7](10-pay-once-protocol.md). Cap-derivation, quote and signer-set vectors are CAP-TV-01…32 in [11 §9](11-dual-cap-model.md). Migration vectors are MIG-TV-01…45 in [12 §12](12-router-lifecycle-and-migration.md). Account-policy vectors are ACP-TV-01…44 in [17 §9](17-account-compatibility-policy.md).

**Session-level vectors** (exercise §8):

| SV | Event | Expected |
|---|---|---|
| SV-01 | `atomicRequired:true`, then `getCallsStatus` returns `atomic:false`, status 600 | Re-plan from chain state; wallet version marked `ATOMIC_VIOLATING`; metric incremented |
| SV-02 | Status 200 but V3 not observed within the finality threshold | Mandate stays `PENDING_ACTIVATION`; alert; no charge allowed |
| SV-03 | Customer closes the tab after step 1 of a TX_SEQUENCE and returns later | Re-plan removes step 1; no duplicate prompt |
| SV-04 | Two tabs for the same session | Second tab read-only |
| SV-05 | Permit signed, executor submission delayed past `sigDeadline` | Permit rejected by Permit2; new plan; no stale authority |
| SV-06 | Delegate code hash changes between plan and signature submission | Pre-flight aborts; re-plan (DRV-05, DRV-24) |
| SV-07 | Conversion flag turned off while an attempt is in flight (v1.1) | New attempts blocked; in-flight attempt reconciles |

## 10. Compatibility Register (schema and seed)

The register is **data**, versioned and dated. FastPay's own "supported" statement for a wallet is computed from it and shown to merchants and customers only for rows that are E3 and inside their retest window. Vendor documentation populates the "vendor says" column only.

```text
CompatRow {
  wallet, version, platform (ext|ios|android|web), accountType, chainId,
  testedOn, retestBy, evidenceIds[],
  rawGetCapabilities,                                 # verbatim JSON
  sendCalls: OK | MISSING | BROKEN,  atomicObserved: true|false|na,
  statusCodesObserved[], upgradePrompt: none|offered|forced, upgradeRejectCode,
  delegate { address, codeHash, proxy, erc1271Behavior, revocationPath }       # 13 section 8
  typedDataRenderable: fields-readable | opaque | unsupported,
  txPreview: simulation | decoded | raw,
  hardwarePath: ok|opaque|unsupported|na,
  verdict: SUPPORTED_ATOMIC | SUPPORTED_NON_ATOMIC | NO_BATCH | BROKEN | UNTESTED
}
```

Seed (all `UNTESTED`; "vendor says" is documentation, never a FastPay claim):

| Wallet | Vendor says (source, level) | FastPay verdict |
|---|---|---|
| MetaMask (extension, mobile) | **Documented (E1, CLM-040/043):** EIP-5792 with `atomic` `supported`/`ready` per account and chain; upgrade to a MetaMask smart account via EIP-7702 when `ready`; atomic-only `wallet_sendCalls`; listed networks include Ethereum, BNB Smart Chain, OP, Base, Polygon, Arbitrum (also Gnosis, Unichain, Berachain); **Avalanche not listed**; no atomic batching for accounts already upgraded to a third-party smart account; **delegate not named, persistence not stated** | UNTESTED — runtime detection and delegate recording required |
| Trust Wallet | No documentation found (G-04) | **UNKNOWN** — pending wallet-lab testing |
| Coinbase Smart Wallet / Base Account | Listed as EIP-5792 wallet (CLM-041, E1); spend-permission module exists (CLM-042, E0) | UNTESTED |
| Safe{Wallet} | Listed (CLM-041, E1) | UNTESTED |
| Ambire, TokenPocket, Openfort, thirdweb, Reown embedded | Listed (CLM-041, E1), atomic status not stated | UNTESTED |
| Rainbow, Rabby, Phantom (EVM), Ledger via host wallet | Not mentioned (CLM-041) | UNTESTED |
| WalletConnect-connected variants of the above | Capabilities may differ from the native connector | UNTESTED |

## 11. Negative cases (each is a required test)

| NC | Case | Required behavior |
|---|---|---|
| NC-01 | Wallet claims `atomic: supported` but returns two separate receipts with `atomic:false` | Violation (§3.1); verification by chain state; wallet demoted |
| NC-02 | `wallet_getCapabilities` before account authorization → `4100` | `UNKNOWN`, retry once after `eth_requestAccounts`; never "unsupported" |
| NC-03 | Token metadata claims `decimals = 6`, contract says `18` | Token dropped (`DECIMALS_MISMATCH`); registry is authoritative |
| NC-04 | Page requests `personal_sign` on an opaque hash | Blocked by the SDK; lint fails the build |
| NC-05 | Signed mandate reused on another chain | Fails: domain separator includes `chainId` and `verifyingContract` |
| NC-06 | Permit signed, but the customer's L2 nonce changed | Permit2 rejects the stale nonce; re-plan |
| NC-07 | Customer already delegated to an unrecognized contract | `REFUSE(ACCOUNT_MODE_UNKNOWN)` in FASTPAY mode |
| NC-08 | Executor submits a stale signed permit after `sigDeadline` | Reverts; no authority created |
| NC-09 | L1 allowance later reduced by another app below the mandate's need | Mandate stays `ACTIVE`; portal shows "funding not ready"; charges fail pre-submission with `INSUFFICIENT_ALLOWANCE` and may use another eligible token; merchant notified |
| NC-10 | Wallet adds a hidden extra call to the batch | Not preventable by the page; mitigated by the wallet's preview and by on-chain `I-MANDATE`: extra calls cannot create FastPay authority unless they call `activate` with matching `termsHash` |
| NC-11 | Double-click on "Activate" | Session lock + deterministic batch `id` (error `5720`) |
| NC-12 | RPC A says L1 satisfied, RPC B says not | Planner input must come from agreement (TM-06); disagreement → `UNKNOWN`, activation paused, RB-005 |
| NC-13 | Delegated EOA whose delegate has no `isValidSignature` | Signature transports refused; `msg.sender` flows only; no Permit2 revert reaches the customer |
| NC-14 | A wallet's delegate returns the ERC-1271 magic value for any signature | `ALWAYS_VALID_SUSPECT`; account refused; risk case opened |
| NC-15 | A planner variant sizes L2 at `2^160 − 1` | Caught by TV-22 and by `I-L2-NOMAX` check in the activation verifier (V2 fails if `amount == uint160.max`) |
| NC-16 | The account's delegate or code changes between two charges | The next unattended charge revalidates ([13 §7](13-eip7702-delegation-inspection.md)), is blocked, and the mandate is paused as `DELEGATION_UNVERIFIED` |
| NC-17 | A plan contains a zero-amount `permit` revocation step while `revocation.zeroPermit.enabled` is off | Rejected by the plan validator; transactions are the primary flow |
| NC-18 | The account gains a delegation (wallet upgrade or phishing authorization) after activation | The charge simulation reverts `AccountCodeChanged`; nothing is signed; the mandate is paused `DELEGATION_UNVERIFIED`; re-verification ([17 §7](17-account-compatibility-policy.md)) |
| NC-19 | The planner predicted a delegate for an `ATOMIC_READY` upgrade and the wallet delegates elsewhere | `activate` reverts atomically (`AccountPinMismatch`); nothing applied; the delegate is recorded for the Compatibility Register |
| NC-20 | A **normal** migration plan contains `lockdown` or `approve(…,0,0)` for a `(token, oldRouter)` pair that a sibling mandate of the customer still uses (including a stale plan computed before the sibling existed) | Rejected by the plan validator against the `live` counts read at one block; the plan is rebuilt without the pair (MIG-TV-26, MIG-TV-30) |
| NC-21 | A plan step `approve`/`permit` on `(token, router)` whose amount or expiration is below what the live siblings need (R-L2-SHARED), e.g. sized for the new mandate alone | Rejected; the target is recomputed from the sum (TV-31, MIG-TV-41) |

## 12. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Pin Permit2 at a commit; read `Permit2.sol` / `PackedAllowance` for expiration-of-zero and the `permit` nonce update (G-09); fork-test `lockdown` and `approve(…,0,0)` per token (EV-P11) and the **experimental** zero-amount `permit` revocation (EV-P08) | AA/Protocol Eng |
| 2 | `MandateManager.activateBySig` must call token `permit` and Permit2 `permit` atomically; this enlarges its external-call surface. Alternative: a dedicated, audited `ActivationHelper` with fixed call shapes (CF-002). Decide in the contract spec. | Principal Architect |
| 3 | Wallet previews decode batch calls only if our contracts are verified on explorers and ABIs registered; contract verification is a release gate (PB-012, RG-006) | Solidity Lead |
| 4 | Gas constants per step (`gas.perStepGas`) from fork measurements (RP-19) | Solidity Lead |
| 5 | `policy.sigTtlSeconds = 900` and `maxTokensPerMandate = 3` are proposals pending usability tests | Product Designer |
| 6 | Whether signature transports are worth their complexity for v1.0 if the wallet lab shows most target wallets batch atomically | Wallet Protocol Eng + Principal PM |
