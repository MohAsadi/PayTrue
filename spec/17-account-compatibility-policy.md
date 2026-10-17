# 17 — Account Compatibility Policy

| Field | Value |
|---|---|
| Artifact | FP-PRO-006 |
| Version | 0.5.0 — **`AccountPin` defined as a seven-field typed struct; what the contract verifies versus what stays off chain; ERC-1271 evidence bound to the pin and invalidated on any delegate, implementation, wallet-version or code-hash change**; (0.4: replaced the backend-only revalidation of v0.3 as the control for account changes) |
| Status | DRAFT — freeze candidate; **not frozen**; nothing here is tested on a wallet or chain; the permitted-mode defaults depend on lab evidence ([15](15-wallet-lab-matrix.md)) |
| Owner | Wallet Protocol / Account-Abstraction Engineer (policy), Principal Blockchain Architect (on-chain pin) |
| Reviewers | Head of Security, Solidity Lead, QA Lead, Product Designer, Detection Engineer |
| Dependencies | [02](02-source-register.md) CLM-016, 040, 043, 050, 052, 053; [05](05-evm-authorization-decision-tree.md) §4; [06](06-initial-architecture.md) ADR-007, ADR-017, ADR-018; [11](11-dual-cap-model.md) §3; [12](12-router-lifecycle-and-migration.md) §5.3; [13](13-eip7702-delegation-inspection.md); [tools/eip712_vectors.py](tools/eip712_vectors.py) |
| Labels | `SECURITY-CRITICAL` `PRIVACY-CRITICAL` |
| Definition of Done | Every account FastPay meets is classified into exactly one mode by a boolean predicate; each mode has a stated permission for each flow, including unattended charges; the on-chain pin predicate, its update path and its limits are specified and tested; the backend checks cover what the chain cannot see; ACP-TV-01…44 pass in the planner, the orchestrator, the signer policy and the contract tests. |

## 0. What changed from v0.3

| v0.3 | v0.4 |
|---|---|
| Account changes were handled by a **backend** revalidation before every unattended charge (document 13 §7) and a pause bit; no on-chain account check (OD-029) | An **Account Compatibility Policy (ACP)**: five account modes, a permission matrix, an **on-chain account pin** enforced in `consume`, and the backend revalidation for what the chain cannot observe. OD-029 is reversed (§5) |
| Account classes `EOA`, `EOA_7702_KNOWN`, … ([05 §4](05-evm-authorization-decision-tree.md)) described delegation only | Modes cover plain EOAs, verified 7702 delegation, ERC-4337 accounts, ERC-1271 wallets and unknown code, with the unattended-charge permission stated for each |
| The pause state was the only reaction to a mismatch | The chain **refuses the charge** (`AccountCodeChanged`) whatever the backend does; the pause bit remains as the signal and for non-observable differences. The state name `DELEGATION_UNVERIFIED` is kept for continuity and now covers any ACP mismatch in any mode |

### 0.1 What changed from v0.4 to v0.5

| v0.4 | v0.5 |
|---|---|
| The pin was one `bytes32` (the account's code hash or a sentinel) | A typed `AccountPin` with **seven fields**: account mode, account code hash (the delegation designator hash for a 7702 account), delegate address, delegate code hash, implementation family, pin version, signature mode (§5.1) |
| The contract saw the designator or proxy bytecode only; "the delegate contract's own code changes" was *not seen* by the chain | `consume` also reads `EXTCODEHASH(delegate)` and compares it with the pinned delegate code hash (mode 2); the implementation behind a proxy is still invisible to the chain (§5.5) |
| No statement of what is checked where | A field-by-field table of what the contract verifies and what remains an off-chain control (§5.5) |
| `updateAccountPin` replaced the pin | `pinVersion` is strictly monotonic, signed messages name it, a batch update serves every mandate of the customer (§5.3) |
| ERC-1271 evidence existed as register rows and probes | **Signature capability is a record bound to the pin** (`pinHash`, `pinVersion`) with eleven invalidation triggers; the ERC-1271 path of FastPay's own contracts is closed on chain when the account or delegate code changes (§5.4, §5.6) |

## 1. Principles

1. **Evidence decides the mode, not claims.** Documentation, wallet marketing and capability flags never set a mode; an observation of the chain plus an allowlist row at E3 do.
2. **Code without evidence is `UNKNOWN_CODE`.** Any account with code that no fresh E3 row explains is refused for recurring authority.
3. **Unattended charges need a verified account.** FastPay charges without the customer present, so it can only charge accounts whose behavior was verified and can be re-checked.
4. **Three layers, each fails closed:** the chain (pin), the data (allowlist rows), the backend (observation, probes, revalidation, signer policy). The chain layer does not depend on the other two.
5. **The pin only stops charges.** It never widens authority; changing it needs the customer.
6. **Fund safety never depends on the account's code.** A charge pulls with Permit2 `transferFrom` from the owner address; the owner's code does not run (ERC-20 hook tokens are excluded by the token policy, ASM-022). The policy protects the *assumptions* of the flows and detects takeover; the caps stay on chain.
7. **Wording:** delegation and smart-account code are persistent account state, never "temporary" ([13 §1](13-eip7702-delegation-inspection.md)).

## 2. Account modes

### 2.1 Observation and evidence

An **observation** `O` is read from at least two independent RPC providers at one block ([13 §3.4](13-eip7702-delegation-inspection.md)):
`sourcesAgreed`, `code`, `codeLen`, `h = EXTCODEHASH`, the designator and delegate `D` (if the code is a designator), the delegate's code hash, the proxy fingerprint `F` (kind, implementation address, implementation code hash), the three ERC-1271 probes `P` (fixed inputs; result classes `MAGIC`, `FAILURE_VALUE`, `REVERT`, `OUT_OF_GAS`, `NO_CODE`).

An **allowlist row** `r` is a Compatibility Register row ([15](15-wallet-lab-matrix.md)): `kind ∈ {EOA7702, ACCT4337, WALLET1271}`, wallet and version, the delegate address or account implementation fingerprint, the delegate code hash, `proxyFingerprint`, `probeFingerprint[3]`, `erc1271Verified` (real Permit2 signatures validate), `batchBehavior`, `expectedDelegate` (for wallets that upgrade an account on request), evidence level, `retestBy`, `revoked`.

### 2.2 Predicates

Let `KECCAK_EMPTY = keccak256("") = 0xc5d2…a470`. Constants: `RETEST_GRACE` (14 days, PROPOSAL).

```text
NO_CODE(O)          ≡ O.codeLen = 0  ∧  O.h ∈ { 0x00…00, KECCAK_EMPTY }
IS_DESIGNATOR(O)    ≡ O.codeLen = 23 ∧ O.code[0..2] = 0xef0100
ROW_FRESH(r, now)   ≡ r ≠ null ∧ ¬r.revoked ∧ r.evidence = E3 ∧ now ≤ r.retestBy + RETEST_GRACE
NO_MAGIC(O)         ≡ ∀ i ∈ {1,2,3}: O.P[i] ≠ MAGIC
MATCH_7702(O, r)    ≡ IS_DESIGNATOR(O) ∧ r.kind = EOA7702 ∧ O.D = r.delegate ∧ O.delegateCodeHash = r.delegateCodeHash
                      ∧ O.F = r.proxyFingerprint ∧ O.P = r.probeFingerprint ∧ NO_MAGIC(O)
MATCH_CONTRACT(O, r, k) ≡ O.codeLen > 0 ∧ ¬IS_DESIGNATOR(O) ∧ r.kind = k ∧ O.F = r.implFingerprint
                      ∧ O.P = r.probeFingerprint ∧ NO_MAGIC(O)
```

A bytecode hash of zero or `KECCAK_EMPTY` both mean "no code": `EXTCODEHASH` returns `0` for an account that does not exist or is empty (nonce 0, balance 0) and `keccak256("")` for an existing account without code (EIP-1052), so an externally owned account can show either value over its life.

| Mode | Predicate (with `O.sourcesAgreed`) |
|---|---|
| `PLAIN_EOA` | `NO_CODE(O)` |
| `EOA_7702_VERIFIED` | `∃ r: ROW_FRESH(r, now) ∧ MATCH_7702(O, r)` |
| `SMART_4337` | `∃ r: ROW_FRESH(r, now) ∧ MATCH_CONTRACT(O, r, ACCT4337)` |
| `WALLET_1271` | `∃ r: ROW_FRESH(r, now) ∧ MATCH_CONTRACT(O, r, WALLET1271) ∧ r.erc1271Verified` |
| `UNKNOWN_CODE` | `¬NO_CODE(O)` and none of the three verified modes holds (this includes a designator to an unlisted delegate, a stale or revoked row, a `MAGIC` probe, and contract code without a row) |
| *(no mode)* `INDETERMINATE` | `¬O.sourcesAgreed`: no plan and no charge until two sources agree |

The modes are mutually exclusive: `NO_CODE`, `IS_DESIGNATOR` and other code are disjoint, and a row has one `kind`.

**Counterfactual accounts.** An undeployed contract account has no code and is indistinguishable on chain from an unused EOA. It is therefore classified `PLAIN_EOA` if nothing else is known. It cannot validate Permit2 signatures (Permit2 treats a signer without code as an EOA and ERC-6492 is not supported), so signature transports fail for it; and if the account is deployed later, its code hash no longer satisfies the pin and charges stop (fail closed). The wallet connector's declaration that an account is a smart account makes the planner refuse recurring activation until the account is deployed.

## 3. Permission matrix

| Mode | Recurring activation | **Unattended charge** | Pay Once | Signature flows (`sigOK`) | Atomic batch | Status at v1.0 launch |
|---|---|---|---|---|---|---|
| `PLAIN_EOA` | Yes | **Yes**, while the pin holds | Yes | Yes (`ecrecover`) | If the wallet batches; an upgrade changes the mode (§7) | ON |
| `EOA_7702_VERIFIED` | Yes | **Yes**, while the pin holds, the evidence is fresh and the revalidation is `OK` | Yes | Only if `r.erc1271Verified` (`sig1271 = VERIFIED`) | As `r.batchBehavior` | ON per row at E3; **no row exists yet** (MetaMask `UNTESTED`) |
| `SMART_4337` | Yes, with a row | **Yes**, as above | Yes | Only if `r.erc1271Verified` | As `r.batchBehavior` | OFF until a row exists |
| `WALLET_1271` | Yes, with a row | **Yes**, as above | Yes | Yes (verified by definition) | Per row (for example a multisend) | OFF until a row exists |
| `UNKNOWN_CODE` | **Refused** (`ACCOUNT_MODE_UNKNOWN`) | **Never** | Allowed with a warning, `msg.sender` flows only; **refused** if a probe is `MAGIC` | Never | Never | Always |

The unattended-charge rule, as one predicate (`PIN_OK` reads `EXTCODEHASH` of the account and, in mode 2, of the delegate on chain, §5.2; the rest is read by the backend):

```text
UNATTENDED_OK(m, O, now) ≡
      O.sourcesAgreed
  ∧   mode(O) ≠ UNKNOWN_CODE
  ∧   mode(O) = m.evidence.mode
  ∧   PIN_OK(account, m.accountPin)                      # also enforced on chain, §5
  ∧   ¬m.pauseBits.delegation
  ∧   ( mode(O) = PLAIN_EOA
        ∨ ( now ≤ m.evidence.expiresAt  ∧  REVAL_EQ(O, m.evidence)  ∧  ROW_FRESH(m.evidence.row, now) ) )
```

`REVAL_EQ` compares the delegate address, delegate code hash, proxy implementation, ERC-1271 probe fingerprint and account code with the evidence ([13 §7.3](13-eip7702-delegation-inspection.md)). A failure of any conjunct blocks the attempt before signing; `PIN_OK` is checked again by the contract.

## 4. Enforcement layers and what each can see

| Change in the account | Layer C: chain pin | Layer B: backend revalidation |
|---|---|---|
| A plain EOA gains a delegation (wallet upgrade, phishing authorization) | **Detected**: `h` is a designator hash, not the EOA sentinel | Detected |
| The delegate address changes (new authorization) | **Detected**: the designator hash changes | Detected (`DELEGATE_ADDRESS`) |
| Delegation cleared (account returns to an EOA) | **Detected** unless the pin is `PIN_EOA` | Detected (`CLASS_CHANGED`) |
| The delegate contract's own bytecode changes (redeploy at the same address) | **Detected** in mode 2 (`EXTCODEHASH(delegate)` against the pinned `delegateCodeHash`); not for a delegate that is itself an upgradeable proxy (see next row) | Detected (`DELEGATE_CODEHASH`, `DELEGATE_PROXY_IMPL`) |
| A proxy delegate's or proxy account's implementation is upgraded (EIP-1967 slot) | Not seen (proxy bytecode unchanged; no external call in `consume`, UD-09) | Detected (`DELEGATE_PROXY_IMPL`) |
| A wallet version change that changes neither a code hash nor a proxy slot | Not seen | Detected only through the register's version field and the probes (`WALLET_VERSION`, limited) |
| ERC-1271 behavior changes without a code change | Not seen | Detected only through the three probes (limited) |
| A module is added to a contract wallet, or its owner set changes | Not seen | **Not detected** (residual, §4.1) |
| The account's code disappears or is replaced | **Detected** | Detected |
| RPC providers disagree or lie | Not affected (the contract reads its own chain) | `INDETERMINATE`: the attempt is blocked |

### 4.1 Residual risk, stated plainly

For contract-based modes the chain pin covers only the account's (proxy) bytecode, and for a 7702 account the designator and the delegate's bytecode (§5.5). Proxy-implementation upgrades and wallet-version changes that leave every code hash unchanged are seen by the backend alone, and module or owner changes are not seen at all. None of these can change what FastPay may pull: the mandate caps, the recipient and the once-per-cycle record are enforced by FastPay's contracts, and the customer can revoke from the account. What these changes can do is invalidate the assumptions behind a signature flow or make a charge unwanted by the true owner; the response is the pause and the customer re-verification, with detection limited as in the table.

## 5. The on-chain account pin (`AccountPin`)

### 5.1 The struct, exactly

The pin is a typed struct. It is signed by the customer as a nested EIP-712 type inside `ActivationTerms`, `SuccessorAuthorization` and `AccountPinUpdate`, so a wallet can show every field. The mandate stores only `accountPinHash = hashStruct(AccountPin)` and the `pinVersion`; the struct itself is emitted in `MandateActivated` and `AccountPinUpdated` and travels as calldata of `consume`, where its hash is compared with the stored one (`PinHashMismatch`).

```text
AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,
           bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)
```

| Field | Type | Meaning and value by mode |
|---|---|---|
| `accountMode` | `uint8` | `1 PLAIN_EOA`, `2 EOA_7702_VERIFIED`, `3 SMART_4337`, `4 WALLET_1271` (§2.2). `UNKNOWN_CODE` (0) is **not pinnable**: a mandate cannot be activated for it |
| `accountCodeHash` | `bytes32` | The expected `EXTCODEHASH(account)`. **For `EOA_7702_VERIFIED` this is the delegation designator hash `keccak256(0xef0100 ‖ delegate)`.** For `PLAIN_EOA` it is the sentinel `PIN_EOA` (the account must have no code; both `0` and `KECCAK_EMPTY` satisfy it). For `SMART_4337` and `WALLET_1271` it is the hash of the account's (proxy) runtime code |
| `delegate` | `address` | `EOA_7702_VERIFIED`: the delegate named in the designator. Other modes: `address(0)` |
| `delegateCodeHash` | `bytes32` | `EOA_7702_VERIFIED`: `EXTCODEHASH(delegate)` at pin time (non-zero, not `KECCAK_EMPTY`). Other modes: `0` |
| `implementationFamily` | `bytes32` | A label that identifies the wallet implementation family **and its major version** as classified by the Compatibility Register row the customer was verified against (for example `keccak256("<vendor>/<product>/<major>")`). `0` for `PLAIN_EOA`. It is signed and compared, never interpreted by the contract (§5.5) |
| `pinVersion` | `uint32` | A counter per lineage: `1` at the first activation; `+1` on every `updateAccountPin` (even if no other field changed: it is the customer's re-verification attestation); a successor keeps the version if its pin is field-for-field equal to the predecessor's, otherwise `+1`. Signed messages and signature-capability evidence name the version they were made under (§5.6) |
| `signatureMode` | `uint8` | How FastPay's own contracts may verify this customer's signed messages: `0 DIRECT_ONLY` (only `msg.sender`), `1 ECDSA_KEY` (the account key signs; allowed for `PLAIN_EOA` and `EOA_7702_VERIFIED`), `2 ERC1271` (the account validates through `isValidSignature`; allowed for `EOA_7702_VERIFIED`, `SMART_4337`, `WALLET_1271`). It does **not** describe Permit2: Permit2 verifies by its own rule (§5.6) |

Constants: `PIN_EOA = keccak256("fastpay.pin.eoa.v1")`; `KECCAK_EMPTY = keccak256("")`; `ACCOUNT_PIN_TYPEHASH = keccak256` of the type string above (vector in §9, produced by [tools/eip712_vectors.py](tools/eip712_vectors.py)). Changing the type string is a protocol change (PC-09, PC-15).

### 5.2 Predicates

`h = EXTCODEHASH(account)` and `hd = EXTCODEHASH(pin.delegate)` are read by the contract.

```text
PIN_WELLFORMED(pin) ≡ pin.pinVersion ≥ 1 ∧ pin.accountMode ∈ {1,2,3,4}
   ∧ ( pin.accountMode = 1 ⇒ pin.accountCodeHash = PIN_EOA ∧ pin.delegate = 0 ∧ pin.delegateCodeHash = 0 ∧ pin.implementationFamily = 0
                             ∧ pin.signatureMode ∈ {0,1} )
   ∧ ( pin.accountMode = 2 ⇒ pin.delegate ≠ 0 ∧ pin.accountCodeHash = keccak256(0xef0100 ‖ pin.delegate)
                             ∧ pin.delegateCodeHash ∉ {0, KECCAK_EMPTY} ∧ pin.implementationFamily ≠ 0 )
   ∧ ( pin.accountMode ∈ {3,4} ⇒ pin.delegate = 0 ∧ pin.delegateCodeHash = 0 ∧ pin.accountCodeHash ∉ {0, KECCAK_EMPTY, PIN_EOA}
                             ∧ pin.implementationFamily ≠ 0 ∧ pin.signatureMode ∈ {0,2} )

PIN_OK(account, pin) ≡
     ( pin.accountMode = 1 ⇒ h ∈ {0, KECCAK_EMPTY} )
   ∧ ( pin.accountMode = 2 ⇒ h = pin.accountCodeHash ∧ hd = pin.delegateCodeHash )
   ∧ ( pin.accountMode ∈ {3,4} ⇒ h = pin.accountCodeHash )

nextPinVersion(L, pin) ≡ 1                                  for the first activation of a lineage
                       = L.pinVersion + 1                   for updateAccountPin
                       = P.pinVersion + [pin differs from P.pin in any field other than pinVersion]   for a successor
```

For a 7702-delegated account `h = keccak256(0xef0100 ‖ delegate)` (the designator is the account's code; `EXTCODEHASH` does not follow the delegation, CLM-053). Mismatch errors: `AccountPinMalformed`, `AccountCodeChanged(customer, field)` with `field ∈ {ACCOUNT_CODE, DELEGATE_CODE}`, `PinVersionMismatch`, `PinHashMismatch`.

### 5.3 Where it is checked and signed

| Point | Rule |
|---|---|
| `activate`, `activateBySig` | `PIN_WELLFORMED(pin) ∧ PIN_OK(customer, pin) ∧ pin.pinVersion = 1` at the activation block; the pin is the nested struct of the signed `ActivationTerms`, so the wallet shows the account type, the delegate and the signature mode the customer is binding |
| `activateSuccessor` | Predicate K1 of [12 §5.3](12-router-lifecycle-and-migration.md): `PIN_WELLFORMED(N.pin) ∧ PIN_OK(customer, N.pin) ∧ N.pin.pinVersion = nextPinVersion`; the pin is part of `SuccessorAuthorization` |
| `consume` (every charge) | The executor supplies the pin struct; the contract checks `hashStruct(pin) = m.accountPinHash` and `PIN_OK(m.customer, pin)`; any failure reverts and changes no state; the executor sees it in simulation. Cost, **estimated and unmeasured**: `EXTCODEHASH` of the account (about 2,600 gas cold) and, for mode 2, of the delegate (another 2,600 gas cold), plus the calldata (about seven words) and one hash |
| `updateAccountPin(customer, mandateId, newPin)` on the manager (the customer, or the gateway relaying `MandateGateway.updateAccountPinBySig(update, currentPin, signature)`) and the batches `MandateGateway.updateAccountPins` and `updateAccountPinsBySig` (≤ `MAX_BATCH`, ADR-021) | Callable by the customer (`msg.sender`) or by anyone holding the customer's EIP-712 `AccountPinUpdate` (§5.4). Requires: mandate non-terminal; `PIN_WELLFORMED(newPin)`; `PIN_OK(customer, newPin)` now; `newPin.pinVersion = old.pinVersion + 1`; nonce unused; deadline not passed. Effect: `accountPinHash` and `pinVersion` updated; event `AccountPinUpdated(mandateId, oldPinHash, newPin, pinVersion)`. **It changes no other field** (`I-ACCT-NOWIDEN`). The batch exists because one account change affects every mandate of the customer (one signature, one transaction) |

**Typed data that carries the pin** (domain `"FastPay Mandates"`, version `"1"`; `AccountPin` is appended to each type string as the referenced struct, EIP-712 ordering):

```text
AccountPinUpdate(address customer,bytes32 mandateId,AccountPin newPin,uint64 deadline,uint256 nonce)
AccountPinsUpdate(address customer,bytes32[] mandateIds,AccountPin newPin,uint64 deadline,uint256 nonce)
ActivationTerms(…, AccountPin accountPin, …)        # the complete type string: eip712/TYPES.md (proposed, not frozen; FZ-22)
SuccessorAuthorization(…, AccountPin accountPin, …) # 12 §5.3
```

`AccountPinUpdate` needs no `oldPinVersion`: the contract compares `newPin.pinVersion` with the stored version plus one. `AccountPinsUpdate` applies to every named mandate whose stored version plus one equals `newPin.pinVersion` and reverts `PinVersionMismatch` for any other (mandates at different versions are updated in separate calls). Identifier `PIN_SCHEMA` does **not** exist: the layout of the struct is the type string, and changing it is a protocol change under PC-09.

### 5.4 Signed messages and the signature mode (`AUTH`)

A message the customer signs for FastPay's contracts (`activateBySig`, `activateSuccessorBySig`, `updateAccountPinBySig`, `reduceBySig`, `resumeBySig`) is accepted by `AUTH(customer, digest, pinCtx)`; `pinCtx` is the pin **already stored** in the mandate or lineage the message acts on (for a brand-new lineage, the pin in the message, which must itself satisfy `PIN_OK`):

```text
AUTH(C, digest, pinCtx) ≡  msg.sender = C
   ∨ ( pinCtx.signatureMode = ECDSA_KEY ∧ ecrecover(digest, sig) = C )                                   # the account key signed
   ∨ ( pinCtx.signatureMode = ERC1271  ∧ PIN_OK(C, pinCtx) ∧ isValidSignature(digest, sig) = 0x1626ba7e ) # STATICCALL, no artificial gas cap
```

Consequences: (1) with `DIRECT_ONLY` no signature is accepted for authority-creating messages; (2) a signature the account validates through ERC-1271 is accepted **only while the account still satisfies the stored pin** (same account code, same delegate code): if a delegate is swapped or redeployed, the ERC-1271 path is closed on chain at once, and the customer must act directly or, if the pin says `ECDSA_KEY`, with the account key; (3) the pin governing the check is the one the customer already approved, never the one in the message being checked; (4) **exits are never gated**: `revokeBySig`, `pauseBySig` and the pin-independent stop actions are accepted through either path whatever the mode (an attacker who can forge a signature can only stop charges). Permit2's own signature rule is separate (§5.6).

### 5.5 What the contract can verify, and what remains an off-chain control

| Field or property | The contract verifies | Stays off chain (layer B, data, process) |
|---|---|---|
| `accountMode` and the consistency of the other fields | `PIN_WELLFORMED`: the shape each mode must have; the mode is **not** derived from chain facts beyond the code-hash checks, it is what the customer signed | That the account really is the kind of wallet the mode names; the row and the E3 evidence behind the mode |
| `accountCodeHash` | Equality with `EXTCODEHASH(account)` on **every charge** and on every signed message through ERC-1271 | Nothing: this is the strongest check. It cannot see storage |
| `delegate` | Consistency with the designator hash at pin time; a different delegate changes `h` and is caught through `accountCodeHash` | Whether the delegate is a safe wallet (allowlist row, probes) |
| `delegateCodeHash` | `EXTCODEHASH(delegate)` equals the pinned value on every charge (mode 2). This closes the v0.4 gap "the delegate contract's own code changes" for delegates whose code can change only by redeployment at the same address | A delegate that is an upgradeable proxy: only the proxy bytecode is pinned; **the implementation behind it is not readable on chain without an external call** (UD-09 stays: no external call in `consume`) — detected by the backend (`DELEGATE_PROXY_IMPL`) |
| `implementationFamily` | Equality with what the customer signed; unchanged across charges | **Everything about its truth:** that the family label matches the code, that the family is safe, that its major version is the one verified. Checked against the Compatibility Register by the backend; the contract cannot interpret it |
| `pinVersion` | Strict `+1` on update, equality in signed messages, monotonic per lineage: a message signed under an older version cannot be replayed | Which off-chain evidence was bound to which version (§5.6) |
| `signatureMode` | Which verification path the contract accepts for the customer's messages (§5.4) | Whether Permit2 accepts the account's signatures (external contract) |
| Account storage: owners, modules, session keys, upgrade authority | Nothing | Nothing detectable in general: residual risk (§4.1) |
| RPC consensus, evidence freshness, register retest dates, probe results | Nothing (the contract reads its own chain) | Layer B: `INDETERMINATE`, `EVIDENCE_TTL`, `RETEST_GRACE`, three probes |

### 5.6 Signature capability: ERC-1271 evidence bound to the pin, and its invalidation

Two capabilities are kept apart because different contracts verify them:

* `fastpaySig`: FastPay's contracts accept the account's ERC-1271 signature for authority-creating messages. **Enforced on chain** by `AUTH` (needs `signatureMode = ERC1271` and `PIN_OK`).
* `permit2Sig`: **Permit2** accepts the account's signature on real `PermitSingle`/`PermitBatch`/witness messages. Permit2 is external: for an account **with code it calls `isValidSignature` and never falls back to `ecrecover`** (`SignatureVerification.sol:26-45` at the pinned commit, [16 §5](16-freeze-decision-report.md)), so a 7702-delegated account has no signature path unless its delegate implements ERC-1271. Not enforceable by the contract: decided by evidence and a pre-flight.

The evidence record is **bound to the pin**:

```text
SigCapabilityRecord {
  evidenceId, chainId, account, pinHash = hashStruct(AccountPin), pinVersion,
  basis { rowId, rowVersion, labRunIds[], walletVendor, walletVersion, implementationFamily,
          accountCodeHash, delegate, delegateCodeHash, proxyImplementation, proxyImplementationCodeHash, probeFingerprint[3] },
  fastpaySig  : VERIFIED | UNVERIFIED | REVOKED(reason)
  permit2Sig  : VERIFIED | UNVERIFIED | REVOKED(reason)        # needs a passing per-signature pre-flight on a real Permit2 digest
  verifiedAt, expiresAt = verifiedAt + EVIDENCE_TTL, lastPreflight { at, digestKind, ok }
}
```

`VERIFIED` requires: the record's `pinHash` and `pinVersion` equal the mandate's, an E3 row that `erc1271Verified` and is fresh (`ROW_FRESH`), **and** every element of `basis` equal to a fresh observation. **Any change of the delegate, the implementation, the wallet version or a code hash revokes the capability immediately** — it does not wait for the next scheduled check:

| Trigger (T-SIG) | Detected by | New state |
|---|---|---|
| 1 Account code hash changed (designator or proxy bytecode) | **Chain** (`PIN_OK`, ERC-1271 path closed) and backend | `REVOKED(ACCOUNT_CODE)` |
| 2 Delegate address changed | **Chain** (designator hash) and backend | `REVOKED(DELEGATE)` |
| 3 Delegate code hash changed | **Chain** (`EXTCODEHASH(delegate)`, mode 2) and backend | `REVOKED(DELEGATE_CODE)` |
| 4 Proxy implementation or its code hash changed (EIP-1967 or similar) | Backend only (storage read) | `REVOKED(IMPLEMENTATION)` |
| 5 Wallet version or implementation family differs from `basis` (wallet-reported version, register row version, family label) | Backend and register | `REVOKED(WALLET_VERSION)` |
| 6 Probe fingerprint changed | Backend | `REVOKED(PROBE)` |
| 7 Register row revoked, or retest overdue beyond `RETEST_GRACE` | Register | `REVOKED(ROW)` |
| 8 Three consecutive pre-flight failures (`isValidSignature` on the real digest is not the magic value) | Backend | `REVOKED(PREFLIGHT)`; a single failure only blocks that attempt |
| 9 Evidence expired | Backend | `UNVERIFIED` (not revoked) |
| 10 `pinVersion` moved (any `updateAccountPin`) | Chain event | `UNVERIFIED` until the evidence is re-bound to the new `pinHash` |
| 11 Family stopped by a risk case | Backend | `REVOKED(FAMILY)` |

Effects while `fastpaySig` or `permit2Sig` is not `VERIFIED`: the planner computes `sig1271 ≠ VERIFIED` and **emits no signature transport** for the account (`msg.sender` flows, or a refusal); the signer policy **relays no ERC-1271-validated authority-creating message** for the account (exits are still relayed); for triggers 1–3 the contract itself refuses the ERC-1271 path (`AUTH`). A mandate whose account no longer satisfies `UNATTENDED_OK` is blocked (§6). **Restoring** the capability needs the customer: a fresh observation, a permitted mode, a matching E3 row, a new `AccountPin` with `pinVersion + 1` signed **directly or with the account key (never with the invalidated ERC-1271 path)**, the evidence re-bound to the new pin, and a passing pre-flight. Never by time alone.

What this does **not** protect: a change that none of the eleven triggers observes (a module added to a contract wallet, a changed owner set, behavior that changes without a code change, a proxy whose implementation is not readable) — the residual of §4.1.

### 5.7 What the pin does not do

It does not prove the account is safe, does not see the account's storage or a proxy's implementation, and does not replace the backend checks for contract modes (§4). It cannot be updated by FastPay, a merchant or a relayer without the customer's authorization: the executor can only *submit* a signed update. It only stops charges and closes the ERC-1271 path; it never widens authority (`I-ACCT-NOWIDEN`).

## 6. Policy state per mandate

```text
 ACP_VERIFIED ──charge attempt: pin or revalidation mismatch──▶ ACP_BLOCKED(reason, diffs) ──customer re-verification──▶ ACP_VERIFIED
      │                                                              ▲
      └──charge attempt: INDETERMINATE (first time: attempt blocked, no pause; persistent: BLOCKED)
```

| Transition | Actor | Rule |
|---|---|---|
| VERIFIED → BLOCKED | Orchestrator on a failed simulation or revalidation; the pin check on chain even if the orchestrator is wrong | The attempt is not signed or reverts; `RiskPauser` sets the pause bit (`setDelegationPause`) with the reason code; webhook `mandate.paused.account_change` (reason only); no token fallback |
| INDETERMINATE | Orchestrator | The attempt fails pre-submission (`ACP_CHECK_INDETERMINATE`) and is retried with backoff; three consecutive indeterminate attempts over six hours block the mandate ([13 §7.3](13-eip7702-delegation-inspection.md)) |
| BLOCKED → VERIFIED | Customer | Re-verification (§7): fresh observation, mode computed; if the mode is permitted, new evidence, the customer signs `updateAccountPin` (one prompt) and the `AccountEvidenceAck`; `RiskPauser` clears the bit. Never by time alone |
| Mode becomes `UNKNOWN_CODE` | — | The mandate stays blocked; recurring cannot resume on this account; the customer may revert the delegation, change account, or use Pay Once |

## 7. Scenarios (each is a required test)

| # | Situation | What happens |
|---|---|---|
| S-A | A wallet reports `ATOMIC_READY` and the customer accepts its upgrade **during** activation | The upgrade takes effect before the batch's calls, so `activate` sees the designator hash. The planner may use this path **only** when the Compatibility Register row names the `expectedDelegate` (E3); the pin is then `keccak256(0xef0100 ‖ expectedDelegate)` and a different delegate makes the atomic batch revert (nothing applied). Without a row the planner does not request the upgrade (TV-30) |
| S-B | A customer with an active mandate accepts a wallet upgrade prompt later | The next charge fails `AccountCodeChanged` in simulation; bit set; portal shows "your account changed"; re-verification (new mode, new pin, one signature) resumes charging; merchant sees `ACCOUNT_REVERIFICATION_REQUIRED` |
| S-C | The wallet updates its delegate to a new, allowlisted version | Designator hash changes: same as S-B with a new pin |
| S-D | A proxy delegate's or account's implementation is upgraded | Chain pin silent; backend revalidation `MISMATCH(DELEGATE_PROXY_IMPL)`; bit set; re-verification |
| S-E | The customer reverts the delegation | Pin mismatch (designator → empty); re-verification as `PLAIN_EOA` with `PIN_EOA` |
| S-F | An attacker obtains a signed authorization to a malicious delegate | Pin mismatch stops charges; probes may flag `MAGIC`, opening a risk case; FastPay cannot tell the customer what the delegate does, only that the account changed |
| S-G | A contract wallet adds a module or changes owners | Not detected (§4.1); noted as residual |
| S-H | A counterfactual smart account is deployed after activation as `PLAIN_EOA` | Code appears: pin mismatch; charges stop; the customer re-verifies as a contract mode if a row exists |

## 8. How the rest of the specification uses the policy

| Where | Use |
|---|---|
| Planner ([05 §4–§7](05-evm-authorization-decision-tree.md)), version 1.3.0 | Inputs `account.mode`, `account.codeHash`, `account.expectedDelegate`; output `account.pin` in the signed terms; refusals `ACCOUNT_MODE_UNKNOWN`, `ACCOUNT_INDETERMINATE` and the flag `ACCOUNT_PIN_UNPREDICTABLE` (the upgrade is not requested); vectors TV-27…TV-30 |
| Contracts ([06 §4](06-initial-architecture.md)) | `accountPinHash` and `pinVersion` in the mandate; the pin struct in `consume` calldata; `updateAccountPin(s)`; `AUTH`; invariants `I-ACCT-PIN`, `I-ACCT-NOWIDEN`, `I-ACCT-SIG` |
| Migration ([12 §5.3](12-router-lifecycle-and-migration.md)) | Predicate K1 (`AccountPinMalformed`, `AccountPinMismatch`, `PinVersionMismatch`); the pin is the nested struct in `SuccessorAuthorization`; it is not part of containment because the account may legitimately change |
| Delegation records and evidence ([13](13-eip7702-delegation-inspection.md) §3.2, §3.5) | The observation, evidence, probes and revalidation of §2–§3; `DelegationEvidence` gains `mode`, `pinHash`, `pinVersion` and the `SigCapabilityRecord` of §5.6 |
| Signer policy | An unattended charge intent needs an ACP stamp younger than 60 seconds computed for the mandate's current pin **and pin version**; no ERC-1271-validated authority-creating message is relayed while `fastpaySig` or `permit2Sig` is not `VERIFIED` |
| Pay Once ([10](10-pay-once-protocol.md)) | No mandate and no pin; `UNKNOWN_CODE` accounts get the warning and `msg.sender` flows only |

## 9. Test vectors ACP-TV (executed by the planner, the orchestrator, the signer policy and the contract tests)

Constants are produced by [tools/eip712_vectors.py](tools/eip712_vectors.py) and synchronized by [tools/sync_vectors.py](tools/sync_vectors.py) (`D1 = 0xabab…ab`, `D2 = 0xcdcd…cd`):

<!-- BEGIN:VEC_PIN -->
| Constant | Value |
|---|---|
| `KECCAK_EMPTY` | `0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` |
| `PIN_EOA = keccak256("fastpay.pin.eoa.v1")` | `0x8b07c3b3a0bc8c34a9a1a11064f80e35587006d2afc562b5114a4d9071547ba5` |
| Designator code for `D1 = 0xabab…ab` | `0xef0100abababababababababababababababababababab` |
| `H1 = keccak256(0xef0100 ‖ D1)` | `0x4a37830a39af172052f51de869b4cdb29187b16a71da5457fca733c4db241364` |
| `H2 = keccak256(0xef0100 ‖ D2)`, `D2 = 0xcdcd…cd` | `0x8a642d7f1449eccbe45df15c4187cf981920a6fd94ca405c134f128f73c620d7` |
| **`ACCOUNT_PIN_TYPEHASH`** = `keccak256` of the type string of §5.1 (no spaces after commas) | `0xa080d57e052584c73c3f7c5069eb0bccf7ce7d0326916d81ecda5f8867f57ec4` |
| `keccak256("fastpay-test-delegate-code-v1")` (delegate code hash of the example 7702 pin) | `0x00e909366694deb1e4fbbd183b70356e899ca8dcca5ecf975177e3ec29c1e052` |
| `keccak256("fastpay-test-account-code-v1")` (account code hash of the example 4337 pin) | `0x49223014cf10cccde82f9b5ae5498e22f98e0eea663bca91a911e361add69e2e` |
| `keccak256("test-wallet/delegator/1")` (family of the example 7702 pin) | `0x41e7cea110e32333d68057a4496a860f2f362502e359b0971b6b6544c205e24c` |
| `keccak256("test-wallet/account/1")` (family of the example 4337 pin) | `0xb9a15d488bd9222804976115d8c2ff92815d777e252bf9aa3fe6341f4b613d15` |
| **Example pin 1** `pinEoa`: mode 1, `PIN_EOA`, delegate 0, delegate code hash 0, family 0, `pinVersion` 1, `signatureMode` 1: `hashStruct` | `0x73d9001f3d8c6f9c3f105e1db220f675da955b585359fe5745fe15de58f5e7f0` |
| **Example pin 2** `pin7702`: mode 2, `H1`, `D1`, the delegate code hash and family above, `pinVersion` 1, `signatureMode` 2: `hashStruct` | `0x63ee21ce79ca7fbcfd6bb2f823516ae5e92c24191b8a2a3f788a6497239a705c` |
| **Example pin 3** `pin4337`: mode 3, the account code hash and family above, delegate 0, delegate code hash 0, `pinVersion` 1, `signatureMode` 2: `hashStruct` | `0xd18faf6a27f9ff586ff4063f203c5072e5c5766efe213f8c10fc47935f023d08` |
<!-- END:VEC_PIN -->

| ACP-TV | Observation / state | Expected |
|---|---|---|
| 01 | No code, `h = 0` (unused account), sources agree | `PLAIN_EOA`; recurring and unattended permitted; pin `PIN_EOA` |
| 02 | No code, `h = KECCAK_EMPTY` (funded account) | `PLAIN_EOA`; `PIN_OK(h, PIN_EOA)` |
| 03 | Sources disagree | `INDETERMINATE`: no plan, no charge |
| 04 | Designator to `D1`; fresh E3 row (`EOA7702`, probes match, `erc1271Verified`) | `EOA_7702_VERIFIED`; unattended permitted with pin `H1`; `sigOK` |
| 05 | As 04, row `erc1271Verified = false` | `EOA_7702_VERIFIED`; unattended permitted; signature flows refused |
| 06 | Designator to `D1`, no row | `UNKNOWN_CODE`; recurring refused; Pay Once with warning |
| 07 | As 04 but probe 1 returns `MAGIC` | `UNKNOWN_CODE`; Pay Once refused; risk case |
| 08 | As 04, row `retestBy` passed by more than the grace | `UNKNOWN_CODE` |
| 09 | Contract code; fresh row `ACCT4337`, fingerprint and probes match | `SMART_4337`; unattended permitted; pin = proxy code hash |
| 10 | Contract code; fresh row `WALLET1271`, `erc1271Verified` | `WALLET_1271` |
| 11 | As 10, `erc1271Verified = false` | `UNKNOWN_CODE` |
| 12 | Contract code, no row | `UNKNOWN_CODE` |
| 13 | Pin `PIN_EOA`, `h = H1` | `PIN_OK` false; charge reverts `AccountCodeChanged` |
| 14 | Pin `H1`, `h = H2` | `PIN_OK` false |
| 15 | Pin `H1`, `h = H1` | `PIN_OK` true |
| 16 | Pin `H1`, `h = 0` (delegation cleared, empty account) | `PIN_OK` false |
| 17 | Pin `PIN_EOA`, `h = 0` and `h = KECCAK_EMPTY` | both true |
| 18 | Proxy account: pin = proxy hash, implementation slot changed | `PIN_OK` true; revalidation `MISMATCH(DELEGATE_PROXY_IMPL)`; blocked by the backend, bit set |
| 19 | Evidence mode `PLAIN_EOA`, observation now `EOA_7702_VERIFIED` (upgrade after activation) | Blocked by the pin; re-verification offered (S-B) |
| 20 | `updateAccountPin` to a pin that does not match the current `EXTCODEHASH` | Reverts `AccountPinMismatch` |
| 21 | `updateAccountPin` by a third party without a signature | Reverts `NotCustomer` |
| 22 | `ATOMIC_READY`, upgrade allowed, row names `expectedDelegate = D1` | Plan path A, pin mode 2 with `accountCodeHash = H1` and `delegate = D1`, flag `WALLET_UPGRADE_PIN_PREDICTED`; if the wallet delegates elsewhere the batch reverts atomically |
| 23 | `ATOMIC_READY`, upgrade allowed, no `expectedDelegate` | Upgrade not requested; legacy or signature path with pin mode 1 (`PIN_EOA`) (TV-30) |
| 24 | Successor whose new pin fails `PIN_OK` at activation | `activateSuccessor` reverts `AccountPinMismatch` |
| 25 | Well-formed pins: mode 1 with `PIN_EOA`, no delegate, family 0, `signatureMode` 1; mode 2 with `H1`, `D1`, non-empty delegate code hash, family, `signatureMode` 2; mode 3 with an account code hash, no delegate, family, `signatureMode` 2 | `PIN_WELLFORMED` true for all three; their `pinHash` values are in the block above |
| 26 | Mode 1 with a non-zero `delegate`, or a non-zero family, or `signatureMode` 2 | `AccountPinMalformed` |
| 27 | Mode 2 with `accountCodeHash ≠ keccak256(0xef0100 ‖ delegate)` | `AccountPinMalformed` |
| 28 | Mode 2 with `delegateCodeHash` 0 or `KECCAK_EMPTY`, or `delegate` 0, or family 0 | `AccountPinMalformed` |
| 29 | Mode 3 or 4 with a non-zero `delegate` or `delegateCodeHash`, or `accountCodeHash` in `{0, KECCAK_EMPTY, PIN_EOA}`, or `signatureMode` 1 | `AccountPinMalformed` |
| 30 | `pinVersion = 0`; `accountMode = 0` (`UNKNOWN_CODE`) or 5 | `AccountPinMalformed` |
| 31 | Mode 2, `h = H1`, `EXTCODEHASH(D1)` equals the pinned value; then the delegate's code hash changes (redeploy at `D1`) | `PIN_OK` true; then `AccountCodeChanged(DELEGATE_CODE)` on the next charge and on the ERC-1271 path |
| 32 | Mode 2, the delegate address has no code at all (`EXTCODEHASH = 0`) | `AccountCodeChanged(DELEGATE_CODE)` |
| 33 | Mode 3, `h` equal to the pinned account code hash; `h` different | `PIN_OK` true; `AccountCodeChanged(ACCOUNT_CODE)` |
| 34 | `consume` with a pin struct whose hash differs from `accountPinHash` in any one field (seven mutations) | `PinHashMismatch` each time |
| 35 | `updateAccountPin` with `pinVersion = old + 1`; `= old` (replay); `= old + 2` | Accepted; `PinVersionMismatch`; `PinVersionMismatch` |
| 36 | `updateAccountPin` with every field equal and `pinVersion = old + 1` (re-verification attestation) | Accepted; `AccountPinUpdated` emitted; evidence bound to the old version becomes `UNVERIFIED` (T-SIG 10) |
| 37 | Successor with a field-for-field equal pin; with a changed pin; with a changed pin and an unchanged version | Version unchanged; version `+1`; `PinVersionMismatch` |
| 38 | `AUTH` with pin `signatureMode = ECDSA_KEY`: an ECDSA signature by the account key; an ERC-1271 signature | Accepted; `SignatureModeNotPermitted` |
| 39 | `AUTH` with pin `signatureMode = ERC1271`, mode 2, the delegate's code hash has changed and the delegate returns the magic value for any signature; then `msg.sender = customer` | Rejected (`AccountCodeChanged`: the ERC-1271 path is closed on chain); accepted |
| 40 | `AUTH` with `signatureMode = DIRECT_ONLY`: any signature; then `revokeBySig` and `pauseBySig` by ECDSA and by ERC-1271 | `SignatureModeNotPermitted`; exits accepted through either path |
| 41 | Mode 3 account whose proxy implementation changes (proxy bytecode unchanged) | The pin holds on chain and the ERC-1271 path stays open (§4.1 residual); the backend revokes the capability (`REVOKED(IMPLEMENTATION)`), refuses signature transports and relays no ERC-1271 authority message; unattended charges are blocked (`DELEGATE_PROXY_IMPL`) |
| 42 | Wallet version label in the register changes while every code hash is unchanged | `REVOKED(WALLET_VERSION)`; planner `sig1271 ≠ VERIFIED`; re-verification with `pinVersion + 1` restores it |
| 43 | Evidence bound to `pinVersion = 3`; the pin is updated to 4 | `UNVERIFIED` until re-bound to the new `pinHash` and a pre-flight passes; the planner emits no signature transport meanwhile |
| 44 | Three consecutive pre-flight failures on real Permit2 digests; then one success | `REVOKED(PREFLIGHT)` after the third; a single failure only blocked its own attempt; the success does not restore it (re-verification only) |

## 10. Invariants and tests

| ID | Invariant | Test |
|---|---|---|
| I-ACCT-PIN | A charge executes only if `hashStruct(pin) = m.accountPinHash` and `PIN_OK(customer, pin)` (account code hash, and in mode 2 the delegate's code hash) | Fork tests with plain, delegated (type-4 transaction), contract and self-destructed accounts; fuzz over `h` and `hd`; mutation of each of the seven fields |
| I-ACCT-NOWIDEN | `updateAccountPin(s)` changes only `accountPinHash` and `pinVersion` and never makes a rejected payment acceptable | Storage-diff test; stateful fuzz of pin updates interleaved with charges |
| I-ACCT-SIG | A signature validated through ERC-1271 is accepted for an authority-creating message only if `signatureMode = ERC1271` **and** `PIN_OK` holds on the live account; with `DIRECT_ONLY` no signature is accepted; exits are accepted through either path | ACP-TV-38…40; fuzz over (mode, signature path, account state); mutation of `AUTH` |
| I-ACCT-VERSION | `pinVersion` of a lineage never decreases and never skips: it changes by at most +1 per pin change | ACP-TV-35…37; stateful fuzz |
| I-ACCT-MODE | The planner emits no recurring plan for `UNKNOWN_CODE` or `INDETERMINATE` | ACP-TV-03, 06, 07, 08, 11, 12 in both planner implementations |
| Pin predicate (model) | `PIN_OK` accepts both encodings of "no code" for `PIN_EOA` and nothing else; a designator or proxy hash only equals itself | [tools/model_checks.py](tools/model_checks.py) check [4] and `self_check()` in the vector tool |
| I-DELEG (v0.3, kept) | No unattended charge is signed without an `OK` stamp younger than 60 seconds | Signer-policy test; DRV-01…25 |

## 11. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Whether the pin of a contract wallet or of a proxy delegate should include the implementation address through a registry-listed `implementationOf(account)` reader (adds an external call to untrusted code inside `consume`) or stay at bytecode; current design: bytecode only, implementation changes are layer B (UD-09) | Principal Architect |
| 5 | Whether `delegateCodeHash` is worth its second cold `EXTCODEHASH` in `consume` (about 2,600 gas, unmeasured) or should be checked only at activation, pin update and signed messages (OD-037) | Principal Architect + Solidity Lead |
| 6 | Whether the pin should be **per customer** instead of per mandate (one update re-verifies every lineage; each mandate would store the version it was signed under). Current: per mandate with a batch update; the choice affects the audit scope and the typed data (OD-037) | Principal Architect |
| 7 | Whether `implementationFamily` should be attested on chain by a governance-curated `AccountFamilyRegistry` with a guardian stop bit, instead of being a signed label checked off chain. Current: label only (no new contract; a family-wide stop is done with the risk pause bit on each mandate) | Head of Security + Principal Architect |
| 2 | How a wallet that upgrades **after** `eth_requestAccounts` but before submission is handled in the atomic path (the pin is predicted; an unexpected delegate reverts) — confirm in the lab (WL-05, WL-11) | Wallet Protocol Eng |
| 3 | Whether a mandate on a `PLAIN_EOA` should offer an "allow wallet upgrades" opt-in that pins the sentinel *and* the expected designator set (not designed; would add code) | Product + Principal Architect |
| 4 | `RETEST_GRACE`, `EVIDENCE_TTL` and the probe budget are measured in the alpha (RP-28) | Wallet Protocol Eng |
