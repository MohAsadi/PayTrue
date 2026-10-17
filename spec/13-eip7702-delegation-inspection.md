# 13 — EIP-7702 Delegation: Semantics, Inspection, Records, and Revalidation Before Every Unattended Charge

| Field | Value |
|---|---|
| Artifact | FP-PRO-005 |
| Version | 0.5.0 — evidence is **bound to the account pin** and carries the wallet version and implementation family; a change of any of them revokes the signature capability at once ([17 §5.6](17-account-compatibility-policy.md)); (0.4: revalidation is **layer B of the Account Compatibility Policy** ([17](17-account-compatibility-policy.md)), which adds an on-chain account pin; 0.3: mandatory revalidation before every unattended charge, `DELEGATION_UNVERIFIED`, pseudocode, golden vectors) |
| Status | DRAFT |
| Owner | Wallet Protocol / Account-Abstraction Engineer |
| Reviewers | Head of Security, Principal Architect, QA Lead, Product Designer, Detection Engineer |
| Dependencies | [02](02-source-register.md) CLM-010…016, 040, 043, 050, 053; [04](04-context-and-trust-boundaries.md); [05](05-evm-authorization-decision-tree.md); [06](06-initial-architecture.md) ADR-007, ADR-017, ADR-018; [17](17-account-compatibility-policy.md); OD-011, OD-028, OD-029 |
| Labels | `SECURITY-CRITICAL` `PRIVACY-CRITICAL` |
| Definition of Done | Every unattended charge attempt passes the Account Compatibility Policy of [17](17-account-compatibility-policy.md) (the chain pin) and the revalidation of §7 or is blocked; the vectors DRV-01…DRV-24 pass in the orchestrator and signer-policy implementations; the policy table reproduces on synthetic hostile delegates; each supported wallet has its delegate, code hash, ERC-1271 behavior and revert path in the Compatibility Register at E3; no customer-facing string or document describes delegation as temporary. |

## 0. Changes since v0.2

| v0.2 | v0.3 |
|---|---|
| A cheap code-hash comparison before each charge was a drift **signal** that did not block | **Mandatory, blocking revalidation before every unattended charge** of the account code, delegate address, delegate bytecode hash, proxy implementation and ERC-1271 behavior against **verified evidence** |
| Drift to an unknown delegate: notify and restrict signature flows; charges continued | Any difference ⇒ the mandate is paused as **`DELEGATION_UNVERIFIED`** and the attempt is blocked |
| Evidence was a record | **`DelegationEvidence`**: immutable, versioned, allowlist-referenced, with an expiry and renewal rule |
| On-chain account-code pin undecided | v0.3 decided **not in v1** (OD-029). **Superseded in v0.4:** the pin is part of the Account Compatibility Policy ([17 §5](17-account-compatibility-policy.md)): one `EXTCODEHASH` comparison per charge and a customer-signed update path; it sees designator and proxy-bytecode changes, and this document's revalidation covers the rest |
| The backend revalidation was the only control for account changes | One of **three layers** (chain pin, allowlist rows, backend); the permission of each account mode is in [17 §3](17-account-compatibility-policy.md) |
| (v0.5) Evidence was a baseline row; a change was found by comparing fields | `DelegationEvidence` also holds `pinHash`, `pinVersion`, `walletVersion`, `implementationFamily` and a `SigCapabilityRecord`; the comparison adds `WALLET_VERSION` and `PIN_HASH`; every mismatch that touches the signature capability revokes it before the next scheduled check (§3.2, §7.3, [17 §5.6](17-account-compatibility-policy.md)) |

## 1. Correct semantics (what we say and what we never say)

Facts from the specification (CLM-016, E1; re-read at E2 by RP-01):

| Fact | Consequence for FastPay |
|---|---|
| A set-code transaction **permanently** sets the account's code to a delegation designator `0xef0100 ‖ delegate`. | Delegation is **persistent account state**, not scoped to a batch, session or transaction. |
| It is **not** reverted at the end of the transaction and **not** rolled back if the transaction later fails. | A failed or abandoned wallet flow can still leave the account delegated. |
| A later valid authorization **overwrites** it (last valid tuple wins within one transaction). | The delegate can change after FastPay observed it. Observations expire. |
| Delegating to the zero address **clears** it. | A protocol-level revocation exists, usable only by the account's key (usually through the wallet). |
| The protocol does not touch the account's storage when delegation changes. | Storage written by an earlier delegate remains; FastPay cannot clean it. |
| An authorization may carry `chain_id = 0`, valid on every chain. | Delegation on one chain may exist on others; discovery is a hint. |
| The delegated code "has unrestricted access to the account". | The delegate is the real controller of the account's behavior; which code it is matters. |
| `CALL`/`STATICCALL` to the account run the delegate's code; `EXTCODESIZE` returns 23 and `EXTCODEHASH` works on the **designator** without following the delegation (CLM-053). | An on-chain check of the account's code hash sees a delegate **address** change, never the delegate's own code or ERC-1271 behavior. FastPay therefore **pins it on chain** ([17 §5](17-account-compatibility-policy.md)) and revalidates the rest off chain (§7). |
| `tx.origin == msg.sender` can be true only in the topmost frame and no longer protects against atomic sandwiching or certain reentrancy patterns (CLM-053). | FastPay contracts never use `tx.origin` (static check). |

**Wording rules** (enforced by a copy lint over i18n keys and documents):

- Never: "temporary", "for this transaction only", "one-time upgrade", "automatically reverts".
- Say: "Your wallet has added smart-account features to this address using code from *{provider}*. This stays in place until you or your wallet change it."

## 2. FastPay's stance

1. **Prefer wallet-managed upgrades through capability discovery.** FastPay requests `atomicRequired:true`; if the wallet reports `ready`, the wallet may offer its own upgrade (CLM-004, CLM-040). FastPay never constructs, requests or asks for a signature over a raw authorization, and never uses `chain_id = 0` (CLM-013; ADR-007; OD-011).
2. **Inspect and record what actually happened.** Documentation does not identify the code (MetaMask's docs name no delegate and do not state persistence, CLM-043). FastPay records, from chain state, the delegation implementation, bytecode hash, account state, revocation path and compatibility evidence.
3. **Treat the delegate as a dependency of specific flows**: Permit2 signature flows depend on the delegate's `isValidSignature` (CLM-050, §5.1); atomic batching depends on the delegate's execution logic.
4. **Revalidate before every unattended charge** (§7) and let the chain refuse a charge when the account's code no longer matches the customer's pin ([17](17-account-compatibility-policy.md)). A charge is made without the customer present, so FastPay cannot ask the wallet what changed; it must prove, each time, that the account is still what the customer verified.
5. **Never rely on the delegate for fund safety.** Mandate authority, caps and once-per-cycle records are on chain in FastPay contracts; a charge pulls via Permit2 from the owner address and does not run the owner's code. The revalidation protects the *assumptions* of the flows and surfaces account takeover, not the on-chain bounds.

## 3. What is inspected and recorded

### 3.1 `DelegationRecord` (append-only; table `account_delegation_observations`)

```text
DelegationRecord {
  recordId, observedAt, chainId, account
  accountClass            EOA | EOA_7702_KNOWN | EOA_7702_UNKNOWN | SMART_ACCOUNT_KNOWN | SMART_ACCOUNT_UNKNOWN | COUNTERFACTUAL
  accountState {          # read from >= 2 independent RPCs at the same block
    blockNumber, blockHash, codeHash, codeLength, rawCodeIfShort, nonce, nativeBalanceWei }
  designator { present, prefix, delegate }              # present only if code is exactly 23 bytes starting 0xef0100
  delegate {              # null if no designator
    address, isContract, codeHash, codeLength,
    proxy { kind: NONE | EIP1967 | EIP1167 | OTHER_SUSPECTED, implementation, implementationCodeHash },
    explorerVerified: YES | NO | UNKNOWN, sourceRef,
    erc1271Probes[3] { probeId, resultClass: MAGIC | FAILURE_VALUE | REVERT | OUT_OF_GAS | NO_CODE },
    allowlistMatch { matched, walletVendor, walletVersion, compatRowId } }
  authorizationHistory {  # third-party indexer: a HINT, never a basis for a money decision
    source, setCodeTxs[], chainIdZeroSuspected }
  capabilitySnapshot, revocationPath { kind, instructionKey, tested, evidenceId },
  linkedTo { sessionId, planId, lineageIds[] },  sourcesAgreed: bool, evidenceIds[]
}
```

### 3.2 `DelegationEvidence` — the verified baseline used by the revalidation

Created **only** when a `DelegationRecord` passes the policy table of §5 (at activation, successor activation, or customer re-verification). Immutable; a change creates a new evidence row.

```text
DelegationEvidence {
  evidenceId, chainId, account, createdAt, expiresAt = createdAt + EVIDENCE_TTL (default 90 days; PROPOSAL)
  derivedFromRecordId
  accountClass
  accountCodeHash                       # hash of the raw account code (EOA: empty-code hash)
  designator { present, delegate }
  delegate { codeHash, proxy { kind, implementation, implementationCodeHash } }
  erc1271 { required: bool, probes[3] { probeId, resultClass } }       # the fingerprint to compare against
  allowlistRef { rowId, version, e3: true, retestBy }                   # null for class EOA
  walletVersion, implementationFamily                                   # as reported by the register row at verification time
  pinHash, pinVersion                                                   # the AccountPin this evidence is bound to (17 section 5.1)
  sigCapability { fastpaySig, permit2Sig, lastPreflight }               # SigCapabilityRecord of 17 section 5.6
  customerAck { typedDataHash, signature }                              # optional acknowledgement on re-verification
}
```

Evidence is **valid for a mandate only while `pinHash` and `pinVersion` equal the mandate's**: a customer-signed pin update (`pinVersion + 1`) makes the old evidence `UNVERIFIED` until a new row is created for the new pin.

### 3.3 The probe

Three fixed probes, `STATICCALL` on the **account** (so the delegate runs in the account's context) with a fixed gas budget (200,000 gas, PROPOSAL):

| Probe | `hash` | `signature` |
|---|---|---|
| P1 | `0x00…01` | 65 zero bytes |
| P2 | `0x00…02` | empty |
| P3 | `keccak256("fastpay-probe")` | 65 bytes of `0xff` |

Result classes: `MAGIC` (returned `0x1626ba7e`: an always-valid delegate, **hostile or broken**), `FAILURE_VALUE` (returned any other 4 bytes, interface plausibly present), `REVERT`, `OUT_OF_GAS`, `NO_CODE`. The probe shows interface behavior only; it does not prove a real signature will validate (the per-signature pre-flight does).

### 3.4 Observation procedure

1. `eth_getCode`, `eth_getTransactionCount`, `eth_getBalance` at one pinned block on ≥2 independent RPCs. Disagreement ⇒ `sourcesAgreed=false` (never a basis for a money decision, TM-06).
2. Exactly 23 bytes starting `0xef0100` ⇒ designator; extract the delegate. Longer code ⇒ smart account (allowlist by implementation). Empty ⇒ `EOA`.
3. For the delegate: `eth_getCode`, hash, EIP-1967/EIP-1167 proxy detection with the implementation and its hash; explorer verification status.
4. Run the three probes (§3.3).
5. Allowlist lookup by **(delegate address, delegate code hash)**; both must match.
6. Persist the record; link it to the session or attempt.

## 4. When inspection happens

| Trigger | Action |
|---|---|
| Wallet connect / account change | Full inspection |
| Before any plan (activation, Pay Once, migration) | Full inspection if the last record is stale (> 5 minutes) |
| After a plan whose wallet response indicated an upgrade | Full inspection; compare with the pre-plan record; allowlist check |
| Before submitting a signature-based transaction | Pre-flight: code hash unchanged **and** `eth_call` of the account's `isValidSignature(hash, actualSignature)` returns the magic value |
| **Before every unattended charge attempt** | **Revalidation (§7): blocking** |
| Daily sweep over accounts with `ACTIVE` mandates | Same observation and comparison as §7 (detects changes between charges so customers are told early) |
| Allowlist change | Re-evaluate affected accounts and evidence |

## 5. Classification and policy

**The authoritative account modes (`PLAIN_EOA`, `EOA_7702_VERIFIED`, `SMART_4337`, `WALLET_1271`, `UNKNOWN_CODE`) and the permission of each mode for recurring activation, unattended charges, Pay Once and signature flows are in [17 §2–§3](17-account-compatibility-policy.md).** Account classes are defined in [05 §4](05-evm-authorization-decision-tree.md); this table keeps the delegation-specific detail and maps as follows: `EOA` → `PLAIN_EOA`; `EOA_7702_KNOWN` → `EOA_7702_VERIFIED`; `SMART_ACCOUNT_KNOWN` → `SMART_4337` or `WALLET_1271` by the allowlist row's kind; `EOA_7702_UNKNOWN`, `SMART_ACCOUNT_UNKNOWN` → `UNKNOWN_CODE`; `COUNTERFACTUAL` → `PLAIN_EOA` with the caveats of 17 §2.2.

| Observation | Class | FastPay recurring activation | Pay Once | Signature flows (`sigOK`) |
|---|---|---|---|---|
| No code | `EOA` | Allowed | Allowed | Allowed |
| Delegate allowlisted at E3 **and** `erc1271` verified for this delegate/version | `EOA_7702_KNOWN` | Allowed | Allowed | **Allowed** |
| Delegate allowlisted at E3 but `erc1271` **not** verified | `EOA_7702_KNOWN` (restricted) | Allowed via `ATOMIC_BATCH` or `TX_SEQUENCE` only | Allowed (PO-2, PO-6) | **Refused** |
| Delegate unknown | `EOA_7702_UNKNOWN` | **Refused** (`policy.restrictedAccounts = REFUSE`) | Allowed with warning; `msg.sender` flows only | Refused |
| Probe `MAGIC` (always-valid) or delegate on a known-malicious list | `EOA_7702_UNKNOWN` | Refused | Refused (risk review) | Refused |
| Smart account (other code), allowlisted | `SMART_ACCOUNT_KNOWN` | Allowed | Allowed | Only if `erc1271` verified |
| Smart account, unknown | `SMART_ACCOUNT_UNKNOWN` | Refused | Allowed with warning | Refused |
| Disagreeing sources | `UNKNOWN` | Refused | Refused | Refused |

### 5.1 The Permit2 rule

Permit2 accepts a signature from an account **without code** only if it recovers with `ecrecover`; for an account **with code** it accepts only an ERC-1271 success and **never falls back to `ecrecover`** (CLM-050). A 7702-delegated EOA has code. Therefore `sigOK` for a code-bearing account requires `sig1271 = VERIFIED` (an E3 Compatibility Register row proving real Permit2 signatures validate for this delegate + code hash + wallet version, **and** a passing per-signature pre-flight). Otherwise the planner uses `msg.sender` flows or refuses. This is why the delegate must be inspected: the same address can be a plain EOA today and signature-incompatible after a wallet's upgrade.

## 6. Revocation path

| Kind | Description | FastPay's role |
|---|---|---|
| `WALLET_NATIVE` | The wallet offers an in-product way to switch back to a regular account (MetaMask's docs link to end-user instructions, CLM-043) | Show the wallet's instructions; verify afterwards by re-reading the code |
| `PROTOCOL_ZERO_ADDRESS` | A new authorization to the zero address, signed by the account's key | **Never requested by FastPay**; documented for completeness |
| `UNKNOWN` | No tested path for this delegate | Warn; route support to the wallet vendor |

After a revert FastPay reclassifies the account. **Existing mandates remain valid on chain**, but the next unattended charge will find the account differs from its evidence and pause as `DELEGATION_UNVERIFIED` until re-verification (§7.6); returning to a plain `EOA` verifies trivially. Residual storage from the old delegate stays (CLM-016).

## 7. Revalidation before every unattended charge

### 7.1 Scope and rule

An **unattended charge** is any recurring-cycle charge attempt (including retries) made without the customer present. Before **each attempt** FastPay observes the account again and compares it with the mandate's verified evidence. **If the delegate address, delegate bytecode hash, proxy implementation, ERC-1271 behavior or the account code differs from the verified evidence, the charge is blocked and the mandate is paused as `DELEGATION_UNVERIFIED`.** Attended flows (activation, Pay Once, migration) use §4's inspection and pre-flight. This revalidation is **layer B** of the Account Compatibility Policy; **layer C** (the contract's `PIN_OK(EXTCODEHASH(customer), accountPin)` check in `consume`) refuses the charge on chain whatever the backend concludes, and the unattended-charge predicate that combines both is `UNATTENDED_OK` in [17 §3](17-account-compatibility-policy.md).

### 7.2 Result types

| Result | Meaning | Effect |
|---|---|---|
| `OK` | Observation equals the evidence on every compared field; sources agree; observation fresh | Proceed; stamp `evidenceId` and `observationId` on the attempt |
| `INDETERMINATE(reason)` | The comparison could not be made reliably (`RPC_DISAGREEMENT`, `STALE_OBSERVATION`, `PROBE_FAILURE_INFRA`) | **Block this attempt** (`FAILED_PRE_SUBMISSION`, reason `DELEGATION_CHECK_INDETERMINATE`); retry with backoff; **no pause** on the first occurrence |
| `MISMATCH(diffs)` | A definite difference from the evidence | **Block the attempt; pause `DELEGATION_UNVERIFIED`**; notify; record a new `DelegationRecord` |

Diff codes: `EVIDENCE_MISSING`, `EVIDENCE_EXPIRED`, `ALLOWLIST_REVOKED`, `ALLOWLIST_EXPIRED`, `ACCOUNT_CODE`, `DELEGATE_ADDRESS`, `DELEGATE_CODEHASH`, `DELEGATE_PROXY_IMPL`, `ERC1271_BEHAVIOR`, `CLASS_CHANGED`, `WALLET_VERSION`, `PIN_HASH`. Each of `ACCOUNT_CODE`, `DELEGATE_ADDRESS`, `DELEGATE_CODEHASH`, `DELEGATE_PROXY_IMPL`, `WALLET_VERSION`, `ERC1271_BEHAVIOR`, `ALLOWLIST_REVOKED` and `ALLOWLIST_EXPIRED` also **revokes the signature capability** (triggers 1–7 of [17 §5.6](17-account-compatibility-policy.md)); the first four of them are also refused on chain for the ERC-1271 path.

A delegation failure is **account-level, never token-level**: the orchestrator does **not** try another token (it would hit the same account).

### 7.3 Pseudocode (normative)

```python
EVIDENCE_TTL          = 90 * DAY          # PROPOSAL
MAX_OBSERVATION_AGE   = 60                # seconds; observation older than this is re-read
RECHECK_BEFORE_SIGN   = 30                # seconds; re-run if the last check is older than this at signing time
RETEST_GRACE          = 14 * DAY          # allowlist retest overdue by <= this is tolerated with an alert
PERSISTENT_INDET_N    = 3                 # consecutive INDETERMINATE attempts ...
PERSISTENT_INDET_T    = 6 * HOUR          # ... spanning at least this long => pause

def revalidate(m, now, rpc):                       # m: mandate (lineage active generation); returns Result
    ev = load_evidence(m.lineageId, m.customer, m.chainId)            # latest immutable evidence row
    if ev is None:
        return MISMATCH(["EVIDENCE_MISSING"])

    obs = observe(m.customer, m.chainId, sources=2)                   # 3.4: same block, >=2 independent RPCs
    if not obs.sources_agreed:
        return INDETERMINATE("RPC_DISAGREEMENT")
    if now - obs.observed_at > MAX_OBSERVATION_AGE:
        obs = observe(m.customer, m.chainId, sources=2)               # one re-read; then judge
        if not obs.sources_agreed or now - obs.observed_at > MAX_OBSERVATION_AGE:
            return INDETERMINATE("STALE_OBSERVATION")
    if obs.probe_infra_failed:                                         # our own probe call failed to run (not the delegate's result)
        return INDETERMINATE("PROBE_FAILURE_INFRA")

    diffs = []
    if obs.class_ != ev.accountClass:                                  diffs.append("CLASS_CHANGED")
    if obs.accountCodeHash != ev.accountCodeHash:                      diffs.append("ACCOUNT_CODE")
    if obs.designator.present != ev.designator.present \
       or obs.designator.delegate != ev.designator.delegate:           diffs.append("DELEGATE_ADDRESS")
    if ev.designator.present:
        if obs.delegate.codeHash != ev.delegate.codeHash:              diffs.append("DELEGATE_CODEHASH")
        if (obs.delegate.proxy.kind, obs.delegate.proxy.implementation, obs.delegate.proxy.implementationCodeHash) \
           != (ev.delegate.proxy.kind, ev.delegate.proxy.implementation, ev.delegate.proxy.implementationCodeHash):
                                                                       diffs.append("DELEGATE_PROXY_IMPL")
        if [p.resultClass for p in obs.erc1271Probes] != [p.resultClass for p in ev.erc1271.probes]:
                                                                       diffs.append("ERC1271_BEHAVIOR")
    elif ev.accountClass.startswith("SMART_ACCOUNT"):                  # smart account: implementation is the proxy target
        if obs.account_impl_fingerprint != ev.account_impl_fingerprint: diffs.append("DELEGATE_PROXY_IMPL")

    if ev.allowlistRef is not None:                                    # not for plain EOAs
        row = allowlist_row(ev.allowlistRef.rowId)
        if row is None or row.revoked:                                 diffs.append("ALLOWLIST_REVOKED")
        elif now > row.retestBy + RETEST_GRACE:                        diffs.append("ALLOWLIST_EXPIRED")
        elif now > row.retestBy:                                       alert("ALLOWLIST_RETEST_OVERDUE", row)   # tolerated

    if (obs.walletVersion, obs.implementationFamily) != (ev.walletVersion, ev.implementationFamily):
                                                                       diffs.append("WALLET_VERSION")        # register-reported version or family changed
    if (ev.pinHash, ev.pinVersion) != chain_pin(m):                    diffs.append("PIN_HASH")              # evidence not bound to the mandate's current pin

    if now > ev.expiresAt:
        if not diffs and (ev.allowlistRef is None or allowlist_row_valid(ev.allowlistRef)):
            ev = renew_evidence_silently(ev, obs, now)                 # identical observation: new row, same content; no customer action
        else:
            diffs.append("EVIDENCE_EXPIRED")

    if diffs:
        return MISMATCH(diffs)
    return OK(evidenceId=ev.evidenceId, observationId=obs.id)


def attempt_unattended_charge(intent, now):
    m = active_mandate(intent.lineageId)
    r = revalidate(m, now, rpc)                                        # BEFORE quoting and token selection
    if isinstance(r, OK):
        stamp(intent, r)
    elif isinstance(r, INDETERMINATE):
        fail_pre_submission(intent, "DELEGATION_CHECK_INDETERMINATE", retry=backoff())
        n, span = indeterminate_streak(m)
        if n >= PERSISTENT_INDET_N and span >= PERSISTENT_INDET_T:
            pause_delegation_unverified(m, reason="INDETERMINATE_PERSISTENT")
        return
    else:                                                              # MISMATCH
        fail_pre_submission(intent, "DELEGATION_UNVERIFIED")           # no token fallback
        pause_delegation_unverified(m, reason=r.diffs)                 # backend state + on-chain pause bit
        revoke_sig_capability(m, r.diffs)                              # 17 section 5.6: planner sigOK false, no ERC-1271 relay, immediately
        record_new_observation(m); notify_customer(m, r.diffs); notify_merchant_aggregate(m)
        if "ERC1271_BEHAVIOR" in r.diffs and probe_magic(obs): open_risk_case(m)
        return
    ... select token, quote, simulate ...
    if now_after_prep - r.checked_at > RECHECK_BEFORE_SIGN:            # re-run immediately before signing
        r2 = revalidate(m, now_after_prep, rpc)
        if not isinstance(r2, OK):
            abort_attempt_and_handle(r2)                               # same handling as above
            return
    sign_and_submit(...)
```

### 7.4 State: `DELEGATION_UNVERIFIED`

- A **third, independent pause bit** in `MandateManager` (alongside customer and risk bits), set and cleared only by the `RiskPauser` role through `setDelegationPause(mandateId, reasonHash, on/off)`; the router refuses `consume` while it is set. It is defense in depth: the backend blocks before signing regardless of the chain bit.
- The bit does not change any cap and never widens authority; it only stops charges. Reason codes include `ACCOUNT_CODE_CHANGED` (the simulation reverted with `AccountCodeChanged`) besides the diff codes of §7.2. The state name is kept from v0.3 and covers every ACP mismatch in every mode.
- A successor inherits all pause bits ([12 §5.2](12-router-lifecycle-and-migration.md), T6).

### 7.5 Clearing the pause

| Cause | How it clears |
|---|---|
| Transient infrastructure (INDETERMINATE-persistent) | Two consecutive `OK` observations at least 10 minutes apart that equal the existing evidence → automatic clear |
| The account returned exactly to the verified state | Same as above |
| Account legitimately changed (new delegate, upgraded smart account, delegation removed) | **Customer re-verification**: a fresh `DelegationRecord` passes the §5 policy (E3 allowlist, `erc1271` verified where signatures are needed); a new `DelegationEvidence` row is created; the customer acknowledges in the portal (typed `AccountEvidenceAck`, ECDSA/ERC-1271); `RiskPauser` clears the bit. Returning to a plain `EOA` verifies trivially |
| Hostile signals (`MAGIC` probe, malicious list) | Risk case; clears only after review and customer re-verification |
| Never | By the passage of time alone |

Merchant effect: webhook `mandate.paused.account_change` (reason code only, no personal detail); the subscription service applies the merchant's grace/dunning policy under reason `ACCOUNT_REVERIFICATION_REQUIRED`.

### 7.6 Performance, cost and privacy

- Budget per attempt: at most 8 RPC calls per provider (code, nonce, balance, delegate code, proxy slots, 3 probes); p95 latency target 1.5 s (PROPOSAL); no caching across attempts beyond `MAX_OBSERVATION_AGE`.
- Evidence and observations are tied to the account for operational purposes, retained per F.6, and never shared with merchants beyond the pause reason code.

### 7.7 What this does and does not protect

| Protects | Does not protect |
|---|---|
| Detects an account that changed since the customer verified it (takeover, wallet change, hostile delegate, behavior change of a proxy delegate) before the next unattended charge | The on-chain bounds are unaffected by it either way; a charge never depends on the delegate's code |
| Surfaces ERC-1271 incompatibility before a signature flow fails | A delegate that behaves identically on the probes but differently on real signatures; mitigated by per-signature pre-flight in attended flows |
| Gives support and merchants a clear reason code | An attacker who controls the account key can still revoke or move funds; nothing here changes that |

## 8. Compatibility evidence and allowlist governance

Extension of the Compatibility Register ([05 §10](05-evm-authorization-decision-tree.md), [15](15-wallet-lab-matrix.md)):

```text
delegateAddress, delegateCodeHash, proxy/implementation, explorerVerified,
erc1271Behavior { realPermit2SignatureValidates: bool, probeFingerprint[3], evidenceId },
batchBehavior { atomic, receiptShape }, upgradePrompt { text/screenshot, persistence statement observed },
revocationPath { kind, steps, tested, evidenceId }, walletVersion, platform, chainIds[], testedOn, retestBy
```

Allowlist governance (OD-028): entries need E3 evidence for every field used by policy; two approvers (Wallet Protocol Eng + Security); the entry pins the code hash and the probe fingerprint; every wallet release opens a retest ticket and a demotion to "restricted" on a code-hash change; removal is immediate and triggers revalidation of every affected account at its next charge; entries expire at `retestBy` with the grace rule of §7.3.

## 9. Customer-facing requirements

- The portal shows, per connected account: whether smart-account code is present, **who provides it** (allowlist match or "unrecognized"), that it **stays until changed**, how to revert, what it means for FastPay, and — when a mandate is paused as `DELEGATION_UNVERIFIED` — what changed (in plain words: "the smart-account code on your address changed") and how to re-verify.
- Consent copy for activation explains the wallet's possible upgrade prompt before the wallet shows it (`W-UPGRADE`).
- No privacy-invasive linking; records are not shared with merchants.

## 10. Observability and runbooks

Metrics: account-class distribution; unknown-delegate rate; probe outcomes; **revalidation results per attempt (OK / INDETERMINATE / MISMATCH by diff code)**; pause counts and time-to-clear; false-positive rate (customer re-verifies with an identical delegate); revalidation latency. Alerts: spike of one unknown delegate; any `MAGIC` probe; allowlisted delegate code-hash change; INDETERMINATE rate above threshold (infrastructure). Runbook RB-014 (EIP-7702 delegation defect): flag off signature flows for the delegate, expect `DELEGATION_UNVERIFIED` pauses if a wallet changes delegates en masse, notify affected customers, rely on on-chain bounds.

## 11. Golden vectors

Inputs: `E_EOA` = evidence for a plain EOA; `E_D` = evidence for an `EOA_7702_KNOWN` account with delegate `D1` (code hash `H1`, no proxy, probes `FAILURE_VALUE ×3`, allowlist row valid, retest in the future, evidence unexpired). Sources agree and the observation is fresh unless stated.

| DRV | Evidence | Observation | Result | Mandate effect |
|---|---|---|---|---|
| DRV-01 | `E_EOA` | EOA, unchanged | `OK` | none |
| DRV-02 | `E_EOA` | now delegated to `D1` | `MISMATCH {CLASS_CHANGED, ACCOUNT_CODE, DELEGATE_ADDRESS}` | pause `DELEGATION_UNVERIFIED` |
| DRV-03 | `E_D` | identical (designator, `H1`, probes) | `OK` | none |
| DRV-04 | `E_D` | designator now `D2` (a different contract, code hash `H2 ≠ H1`, also allowlisted at E3, probes `FAILURE_VALUE ×3`) | `MISMATCH {ACCOUNT_CODE, DELEGATE_ADDRESS, DELEGATE_CODEHASH}` | pause (re-verification creates new evidence) |
| DRV-05 | `E_D` | same designator, delegate code hash `H1′` | `MISMATCH {DELEGATE_CODEHASH}` | pause |
| DRV-06 | `E_D` (proxy delegate, impl `I1`) | implementation changed to `I2` | `MISMATCH {DELEGATE_PROXY_IMPL}` | pause |
| DRV-07 | `E_D` | probe P1 now `MAGIC` | `MISMATCH {ERC1271_BEHAVIOR}` + hostile signal | pause; risk case |
| DRV-08 | `E_D` | probes now `REVERT` | `MISMATCH {ERC1271_BEHAVIOR}` | pause |
| DRV-09 | `E_D` | probe `OUT_OF_GAS` | `MISMATCH {ERC1271_BEHAVIOR}` | pause |
| DRV-10 | `E_D` | delegation cleared; account is an EOA | `MISMATCH {CLASS_CHANGED, ACCOUNT_CODE, DELEGATE_ADDRESS}` | pause; quick re-verification as `EOA` |
| DRV-11 | `E_D` | RPC A shows the designator, RPC B none | `INDETERMINATE(RPC_DISAGREEMENT)` | attempt blocked; retry; no pause |
| DRV-12 | `E_D` | `INDETERMINATE` on 3 attempts over ≥ 6 h | pause `DELEGATION_UNVERIFIED(INDETERMINATE_PERSISTENT)` | pause |
| DRV-13 | `E_D` | first observation 61 s old | one re-read, then judged on the new observation | `OK` if equal |
| DRV-14 | none (evidence missing) | any | `MISMATCH {EVIDENCE_MISSING}` | pause until verification |
| DRV-15a | `E_D`, expired by 1 day | identical | `OK`, evidence silently renewed | none |
| DRV-15b | `E_D`, expired | differs | `MISMATCH {EVIDENCE_EXPIRED, plus the field differences}` | pause |
| DRV-16 | `E_D`, allowlist row revoked | identical | `MISMATCH {ALLOWLIST_REVOKED}` | pause |
| DRV-17 | smart-account evidence | proxy implementation upgraded | `MISMATCH {DELEGATE_PROXY_IMPL}` | pause |
| DRV-18 | `E_D` | only nonce and balance changed | `OK` | none |
| DRV-19 | `E_D` | identical; indexer hints a `chain_id=0` authorization | `OK` + low-severity alert | none |
| DRV-20a | `E_D`, allowlist `retestBy` passed by 5 days | identical | `OK` + alert `ALLOWLIST_RETEST_OVERDUE` | none |
| DRV-20b | `E_D`, `retestBy` passed by 15 days | identical | `MISMATCH {ALLOWLIST_EXPIRED}` | pause |
| DRV-21 | paused for DRV-11-style cause | two consecutive `OK` ≥ 10 min apart, equal to evidence | automatic clear | `ACTIVE` |
| DRV-22 | paused after DRV-04 | customer re-verifies with `D2` (E3, ERC-1271 verified) and acknowledges | new evidence; `RiskPauser` clears | next charge `OK` |
| DRV-23 | paused after DRV-04 | customer re-verifies but `D2` is unknown | stays paused; Pay Once still possible | `DELEGATION_UNVERIFIED` |
| DRV-24 | `E_D` | code changes between the first check and signing (gap > 30 s) | second revalidation → `MISMATCH` | attempt aborted before signing; pause |
| DRV-25 | `E_D` | mismatch on attempt with token A | **no** fallback to token B | attempt `FAILED_PRE_SUBMISSION` |

`diffs` is an **unordered set**; implementations compare it as a sorted list. Every row's diff set is exact: an implementation that emits an extra or a missing code fails the vector.

## 12. Tests

| Test | Method |
|---|---|
| Vectors DRV-01…25 in the orchestrator and in signer policy (the signer refuses a charge intent with no `OK` stamp younger than 60 s) | Table-driven unit tests; both implementations must agree |
| Classification of each observation row in §5 | Table-driven |
| Hostile delegates: correct, absent, always-valid, reverting, gas-guzzling `isValidSignature`; proxy implementation swaps | Fork tests (EV-P07) |
| Delegate swapped between plan and submission; between revalidation and signing | Pre-flight and re-check abort tests |
| Disagreeing RPC sources; stale observation | Indeterminate handling |
| No token fallback after a delegation failure | Orchestrator test (DRV-25) |
| Wording lint | Fails the build on "temporary" family phrases |
| Real wallet delegates | Wallet lab ([15](15-wallet-lab-matrix.md); RP-25, EV-P09) |
| False-positive measurement | Alpha analytics: mismatches where the customer re-verifies an identical delegate |

## 13. Open points

| # | Point | Owner |
|---|---|---|
| 1 | OD-028: default policy for unknown delegates and allowlist governance | Principal Architect + Head of Security |
| 2 | **OD-029 (decided here): no on-chain account-code pin in v1.** If reconsidered, `EXTCODEHASH` of a delegated account returns the designator hash (CLM-053; confirm on a fork, EV-P10) and a pin would need a customer-signed update path | Principal Architect |
| 3 | `EVIDENCE_TTL` (90 days) and the silent-renewal rule: revisit after alpha false-positive data | Wallet Protocol Eng |
| 4 | Probe gas budget (200,000) and whether three probes are enough to fingerprint behavior | Wallet Protocol Eng |
| 5 | Revalidation cost at scale (batching reads per provider) | Chain Infra Lead |
| 6 | Whether L3-only signatures for code-bearing accounts may use an ECDSA-first verifier in `MandateManager` (not adopted before freeze to avoid changing vectors) | Principal Architect |
