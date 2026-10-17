# 10 — Protocol A: Pay Once (Permit2 SignatureTransfer)

| Field | Value |
|---|---|
| Artifact | FP-PRO-002 (new in revision 0.2) |
| Version | 0.3.0 |
| Status | DRAFT |
| Owner | Principal Blockchain Architect; planner by Wallet Protocol Engineer |
| Reviewers | Head of Security, Solidity Lead, QA Lead, Product Designer |
| Dependencies | [02](02-source-register.md) CLM-024, 031, 050, 051, 052; [05](05-evm-authorization-decision-tree.md) §3–§4; [11](11-dual-cap-model.md); [13](13-eip7702-delegation-inspection.md) |
| Labels | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` |
| Definition of Done | Contract entrypoints, witness type, planner vectors TV-PO-1…12 and invariants `I-PO-NOSTANDING`, `I-PO-WITNESS`, `I-ONCE` are specified and tested; no code path in Pay Once reads or writes `MandateManager` or a Permit2 `AllowanceTransfer` allowance. |

## 1. Why a separate protocol

FastPay has two customer modes that differ in what they leave behind on chain. They are different protocols with different contract entrypoints, different tests, different consent copy and different failure modes.

| | **Protocol A — Pay Once** (this document) | **Protocol B — FastPay recurring** ([05](05-evm-authorization-decision-tree.md)) |
|---|---|---|
| Customer present at each payment | Yes | No |
| Permit2 primitive | **`SignatureTransfer`** (single-use signature, unordered nonce, deadline, witness) | **`AllowanceTransfer`** (standing, expiring allowance to the router) |
| Business scope | The signed `PayOnceIntent` (witness) | A scoped **mandate** in `MandateManager` (merchant, tokens, caps, cadence, expiry) |
| Standing authority after payment | **None** by construction | Bounded, visible, revocable |
| Contract entrypoints | `payOnce*` | `charge*` |
| Cap model | The signed exact amount is the hard cap | Dual cap model ([11](11-dual-cap-model.md)) |
| Once-only guarantee | Per `paymentId` (order) | Per `(mandateId, cycleId)` |

Separation rules (each is a test):

- **S-1.** Recurring flows never call `SignatureTransfer`.
- **S-2.** Pay Once never calls `AllowanceTransfer.permit`/`approve`/`transferFrom`, never creates or reads a mandate, and never sets a Permit2 allowance for the router.
- **S-3.** A bug or pause in `charge*` must not affect `payOnce*` and vice versa: separate entrypoints, separate pause switches in `EmergencyGuardian` (stop-only), shared libraries only for hashing and transfers.
- **S-4.** A Pay Once customer who later enables FastPay does so through an explicit activation ([05](05-evm-authorization-decision-tree.md)); Pay Once never silently upgrades to a mandate.

## 2. On-chain design

### 2.1 Spender binding and witness

Permit2's `SignatureTransfer` hashes `msg.sender` into the signed message as the spender, together with the token, amount, nonce and deadline; the witness variants additionally hash a caller-defined `witness` and `witnessTypeString` (CLM-051). The destination `transferDetails.to` is **not** part of the signature. Consequences:

- Only `PaymentRouter` can consume the signature, because the router is the signed spender.
- The recipient and every business term must be bound **through the witness**, and the router must compute the witness from the very parameters it then uses for the transfer. If the router deviates, Permit2 rejects the signature.

```text
PayOnceIntent (EIP-712 witness struct)
  bytes32 paymentId        keccak256(chainId, RouterRegistry, merchantId, orderId)
  bytes32 merchantId
  address recipient        registry recipient at quote time; router re-checks it equals the registry value now
  address feeRecipient
  address token            input token (v1.0: also the settlement token)
  uint256 grossAmountIn
  uint256 merchantAmount   amount delivered to recipient
  uint256 feeAmount        grossAmountIn == merchantAmount + feeAmount
  address payer
  uint64  validUntil       <= quote validity and <= signature deadline
  bytes32 termsHash        hash of the order terms the customer was shown
  bytes32 quoteHash        optional price attestation (11); zero when settlement is 1:1
```

`witnessTypeString` is generated from this struct definition by the contract build and checked by a golden test; the exact string is fixed in the contract spec (Part D) and verified on a fork.

### 2.2 Entrypoints

| Entrypoint | Caller | Authorization | Used by |
|---|---|---|---|
| `payOnceWithSignature(intent, permit, sig)` | Executor | `SignatureTransfer` signature, spender = router | PO-1, PO-5 |
| `payOnceWithSignatureAndPermit(intent, permit, sig, tokenPermit)` | Executor | `SignatureTransfer` + registry-verified ERC-2612 permit to Permit2 for the exact amount | PO-3 |
| `payOnceWithAuthorization(intent, auth)` | Executor | ERC-3009 `receiveWithAuthorization` (flag-gated adapter) | PO-4 |
| `payOnce(intent)` | The payer (`msg.sender == payer`) | Exact allowance to the router, set earlier or in the same atomic batch | PO-2, PO-6 |

All entrypoints: check router and merchant status, token status (`SETTLEMENT`/`DIRECT_PAYMENT` in v1.0), recipient and fee bounds, `validUntil`, `paymentId` unused (`RouterRegistry.markSettled`, shared across router versions so an order cannot settle twice across a migration), then move funds **directly** from payer to recipient and fee recipient in one batch witness transfer. The router holds no tokens at any point in v1.0 (`I-ZEROBAL`).

### 2.3 Nonces and deadlines

- Permit2 nonce is an unordered 256-bit value (CLM-051). FastPay derives it as `uint256(keccak256(paymentId, attemptNumber))` so each attempt has its own nonce and a targeted `invalidateUnorderedNonces` can cancel an attempt.
- Signature deadline = `min(quote.validUntil, now + sigTtl)`; default `sigTtl` 300 s (PROPOSAL, shorter than activation because the customer is present).
- A signature that reaches the executor but is never submitted is a bearer instrument until its deadline; the short TTL, the router-only spender binding, and the witness bound the exposure to "this exact payment to this exact recipient".

**Conversion.** Router v1 has no conversion entrypoints and the v1 witness carries no route field. A conversion-capable Pay Once (Router v1.1) uses a **different** witness type (`PayOnceIntentV2`, which adds the route and output terms) under a different router address, so a v1.1 signature can never validate on Router v1 and vice versa ([09](09-capability-boundaries.md)).

## 3. Authorization paths and decision tree

Ranking criteria, applied in order: (1) no standing permission left behind, (2) fewest customer prompts, (3) least customer gas, (4) most mature standard.

| Path | Mechanism | Customer prompts | Customer txs | Needs |
|---|---|---|---|---|
| **PO-1** SIG_TRANSFER | One signature; `SignatureTransfer` with witness | 1 | 0 | L1 allowance(owner→Permit2) ≥ amount; `sigOK` |
| **PO-4** TOKEN_AUTH_3009 | One signature; `receiveWithAuthorization` (Draft; flag `signing.erc3009.enabled`) | 1 | 0 | Token verified for 3009; `sigOK` |
| **PO-2** BATCH_EXACT_ROUTER | Atomic batch: `token.approve(router, exact)` + `router.payOnce`; allowance fully consumed in the same transaction | 1 | 1 batch | `batchOK`; **not a Permit2 path** |
| **PO-3** SIG_TRANSFER_PLUS_PERMIT | Two signatures: ERC-2612 permit to Permit2 (exact) + witness transfer | 2 | 0 | Token has verified ERC-2612; `sigOK` |
| **PO-5** APPROVE_PERMIT2_THEN_SIG | `approve(Permit2, exact)` tx, then one signature | 2 | 1 | `sigOK` |
| **PO-6** TX_SEQUENCE_ROUTER | `approve(router, exact)` tx, then `payOnce` tx; no typed data | 2 | 2 | none |

Evaluation order (normative): **PO-1, PO-4, PO-2, PO-3, PO-5, PO-6**. PO-4 is skipped unless its flag and token verification hold.

Definitions:

```text
sigOK   = caps.typedData == V4  AND  policy.relayedPayments
          AND ( account.class in {EOA}
                OR ( account has code AND account.sig1271 == VERIFIED ) )     # CLM-050, ADR-017
batchOK = caps.sendCalls == YES AND ( caps.batch == ATOMIC_SUPPORTED
          OR ( caps.batch == ATOMIC_READY AND policy.allowWalletUpgrade ) )
```

```python
def plan_pay_once(inp):                                   # pure, like the recurring planner
    if not gates_ok(inp):          return refuse(first_failed_gate(inp))
    # gates: chain enabled, Permit2 and router verified, merchant active, token status in
    # {SETTLEMENT, DIRECT_PAYMENT} (SWAP_ONLY -> REFUSE("ROUTER_LACKS_CONVERSION"): Router v1 has no conversion code),
    # balance >= grossAmountIn, quote.validUntil >= now + MIN_SIGN_WINDOW else REFUSE("QUOTE_EXPIRES_BEFORE_DEADLINE")
    t, k = inp.token, inp.caps
    sig  = sig_ok(inp);  bat = batch_ok(inp)
    if sig and t.erc20AllowanceToPermit2 >= inp.grossAmountIn:                    return PO1(inp)
    if sig and inp.policy.erc3009Enabled and t.erc3009 == "VERIFIED":             return PO4(inp)
    if bat:                                                                        return PO2(inp)   # approve(0) first if ZERO_FIRST and allowance != 0
    if sig and t.nativePermit == "EIP2612_VERIFIED":                               return PO3(inp)
    if sig:                                                                        return PO5(inp)
    return PO6(inp)
```

Never in Pay Once:

- A Permit2 `AllowanceTransfer` allowance to the router.
- A mandate, a recurring flag, or a "remember me" permission, unless the customer separately chooses to activate FastPay.
- An approval larger than `grossAmountIn` for the router or Permit2 that FastPay itself creates (rule R-PO-EXACT). If a larger approval to Permit2 already exists from another app, FastPay leaves it untouched and shows `W-UNLIMITED-EXISTING`.

## 4. Failure handling

| Situation | Behavior |
|---|---|
| Quote would expire during the wallet prompt | Refresh the quote before showing the prompt; never sign against a stale quote |
| User rejects (`4001`) | `CANCELLED`; no retry loop |
| Simulation reverts deterministically (balance, allowance, token disabled, policy) | `FAILED_PRE_SUBMISSION`; the customer may choose another eligible token; a **new attempt** and a **new nonce** are used |
| Broadcast/receipt timeout, indexer lag, mempool uncertainty | `UNKNOWN` → reconciliation; no second token is charged ([06 §3.2](06-initial-architecture.md)); on-chain `markSettled` prevents a second settlement of the same order regardless |
| Executor submits after `validUntil` | Reverts; nothing moves |
| Third party tries to use the signature | Cannot: spender is the router, witness binds recipient and amounts |
| Executor tries a different recipient or amount | Permit2 rejects: witness mismatch |
| Signature from a delegated EOA whose delegate lacks a valid `isValidSignature` | Permit2 verification fails (CLM-050); prevented earlier by `sigOK`, and by a pre-flight `eth_call` of the account's `isValidSignature` before submission |

## 5. Security analysis (Pay Once specific)

| Threat | Control |
|---|---|
| Replay of the signature on another chain or router | Permit2 domain includes chain id and Permit2 address; spender = router address; `paymentId` includes the chain id and registry |
| Recipient substitution | Witness binds `recipient`, `feeRecipient`, amounts; router recomputes witness from its transfer parameters |
| Executor griefing (withholding or delaying) | Short deadline; customer can retry with a new nonce; `invalidateUnorderedNonces` available to the customer |
| Phishing for a Pay Once signature that is later abused | The signed type is a named-field typed-data struct a wallet can render (TM-05); no `eth_sign`; no blind hashes |
| Merchant changes recipient mid-checkout | Recipient changes are delayed (OD-022); router re-checks equality with the registry at execution |
| Order paid twice across router versions | `RouterRegistry.markSettled` is shared across router versions ([12](12-router-lifecycle-and-migration.md)); the `paymentId` uses `abi.encode` ([11 §4.1](11-dual-cap-model.md)) |
| Leaving a large approval after payment | R-PO-EXACT; PO-2 consumes the approval in the same transaction and a post-condition check requires the remaining allowance to be 0 |

## 6. Ledger, events, observability

- Event: `PayOnceSettled(paymentId, merchantId, payer, token, grossAmountIn, merchantAmount, feeAmount, recipient, path)` where `path` is the PO-n code.
- Ledger: direct payment and platform-fee journals keyed by `(chainId, txHash, logIndex)` ([06 §6](06-initial-architecture.md)); no conversion journals in v1.0.
- Metrics: path distribution (PO-1…PO-6), prompts per payment, pre-flight 1271 failures, quote refresh rate, signature-to-submit latency, unknown-state rate, nonce invalidations.

## 7. Golden vectors (planner)

| TV | Scenario | Expected |
|---|---|---|
| TV-PO-1 | EOA, `typedData=V4`, relayed on, ERC-20 allowance to Permit2 ≥ amount | PO-1; 1 prompt; 0 txs |
| TV-PO-2 | `ATOMIC_SUPPORTED`, no Permit2 allowance, token without verified permit | PO-2; 1 prompt; 1 batch; post-allowance 0 |
| TV-PO-3 | `batch=NONE`, token has verified ERC-2612, no Permit2 allowance | PO-3; 2 prompts; 0 txs |
| TV-PO-4 | `batch=NONE`, 3009 flag on, token verified for 3009 | PO-4; 1 prompt; 0 txs |
| TV-PO-5 | `batch=NONE`, no permit/3009, `typedData=V4` | PO-5; 2 prompts; 1 tx |
| TV-PO-6 | `typedData=NONE`, `batch=NONE` | PO-6; 2 prompts; 2 txs |
| TV-PO-7 | 7702-delegated EOA, `sig1271=UNVERIFIED`, Permit2 allowance present, `batch=NONE` | PO-1 **not** allowed → PO-6 |
| TV-PO-8 | As TV-PO-7 but `sig1271=VERIFIED` | PO-1 |
| TV-PO-9 | Quote expires before the minimum signing window | `REFUSE(QUOTE_EXPIRES_BEFORE_DEADLINE)` (re-quote) |
| TV-PO-10 | Token status `SWAP_ONLY` on Router v1 | `REFUSE(ROUTER_LACKS_CONVERSION)` |
| TV-PO-11 | `ATOMIC_READY`, `allowWalletUpgrade=false`, Permit2 allowance present | PO-1 (never requests an upgrade) |
| TV-PO-12 | `ZERO_FIRST` token, existing router allowance > 0, `ATOMIC_SUPPORTED` | PO-2 with `approve(0)` before `approve(exact)` |

## 8. Invariants and tests

| ID | Invariant | Test type |
|---|---|---|
| I-PO-NOSTANDING | After any `payOnce*` call, the payer's allowance to the router is 0 and no Permit2 allowance for the router was created or changed by FastPay | Invariant + fork |
| I-PO-WITNESS | A transfer succeeds only if the witness recomputed from the router's actual parameters matches the signed witness | Fuzz |
| I-ONCE (shared) | At most one settlement per `paymentId`, across router versions | Invariant + migration fork test |
| I-ZEROBAL (shared) | Router balances unchanged by any entrypoint | Invariant |
| S-1, S-2 | Static check: `payOnce*` has no reference to `MandateManager` or `AllowanceTransfer`; `charge*` has no reference to `SignatureTransfer` | Static analysis in CI |

## 9. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Final `witnessTypeString` and batch-witness encoding; verify on a fork against `PermitHash` at the pinned commit | Solidity Lead |
| 2 | Whether to split the fee into a second `TransferDetails` entry (batch witness) or a separate transfer; gas comparison (RP-19) | Solidity Lead |
| 3 | Minimum signing window and `sigTtl` values from usability tests | Product Designer |
| 4 | ERC-3009 adapter: which launch tokens, and legal/standards risk of a Draft dependency (CF-005) | Contract Security Eng |
