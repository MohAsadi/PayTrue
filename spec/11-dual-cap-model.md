# 11 — Dual Cap Model and the Signed Quote Schema

| Field | Value |
|---|---|
| Artifact | FP-PRO-003 |
| Version | 0.5.0 — **signer-set emergency removal formalized: no grace for a compromised key, bounded grace for planned rotation, tombstones, set stop (§4.7)**; (0.4: `PriceQuote` v1 completed (fifteen fields, signer sets, key rotation, non-override proof); router-independent identifiers; account pin and fee cap added to the mandate) |
| Status | DRAFT — model decided by sponsor directive (2026-10-13); the schema is a freeze candidate, **not frozen**; parameters are proposals |
| Owner | Principal Blockchain Architect (contract), Payments PM (product), Risk Lead (backend controls) |
| Reviewers | Head of Security, Solidity Lead, Ledger Engineer, Product Designer, Head of Compliance |
| Dependencies | [04](04-context-and-trust-boundaries.md) TM-02, TM-10, TM-15; [06](06-initial-architecture.md) ADR-004, ADR-016; [05](05-evm-authorization-decision-tree.md) §6; [12](12-router-lifecycle-and-migration.md); [17](17-account-compatibility-policy.md); [03](03-assumptions-decisions-risks.md) OD-006, OD-027; [spec/tools/eip712_vectors.py](tools/eip712_vectors.py) |
| Labels | `SECURITY-CRITICAL` `FINANCIAL-CONTROL` `PRIVACY-CRITICAL` (customer-facing limits) |
| Definition of Done | Every cap is in exactly one class; the schema's type hash, domain separator, struct hash and digest are reproduced by the Solidity implementation and the backend from the vector in §4.6; the non-override properties of §4.8 hold under an adversarial quote signer in stateful fuzz and are mutation-tested; a customer can read both numbers in the consent screen. |

## 0. Changes

| Since | Change |
|---|---|
| v0.4 → v0.5 | **Signer-set emergency removal** (§4.7): a compromised key gets **no grace period** (`removedAt`, tombstone, never re-registrable, effective in every set version from the block of removal); planned rotation honors **only previously issued quotes** for at most `QUOTE_SET_GRACE ∈ [MAX_QUOTE_TTL, 2·MAX_QUOTE_TTL]`; the guardian can also stop a whole set and can never add keys. Q1 and Q13 are restated, errors `QuoteSignerRemoved`, `QuoteSignerSetStopped`, `QuoteSignerTombstoned` added; the formal model SR-1…SR-7 and CAP-TV-23…32 |
| v0.3 → v0.4 | `PriceQuote` v1 now has **fifteen fields**: added `issuedAt`, `nonce`, `signerSetVersion`, `registryVersion`, `routeHash`, `priceSourceSetHash`; `sourcesCommit` is replaced by `priceSourceSetHash` (checked against the registry). Validity predicate Q1–Q20 (was Q1–Q16). Signer sets are versioned; **key-rotation behavior** (§4.7) and a **non-override proof** (§4.8) are specified |
| v0.3 → v0.4 | Identifiers (`lineageId`, `mandateId`, `cycleId`, `paymentId`) are defined once (§3.1) and contain **no router address, router version or generation**. `maxFeeBps` and `accountPin` are mandate fields. The account pin is listed as an on-chain control (row 23) |
| v0.2 → v0.3 | Four classes became three (`ONCHAIN_HARD`, `QUOTE_BOUND_ONCHAIN`, `BACKEND_ONLY`); counters per lineage; no oracle slot in v1; ECDSA-only quote signers |

## 1. Why two caps

| | Raw-token hard caps | Fiat-equivalent business caps |
|---|---|---|
| Unit | Atomic units of one token | Minor units of one fiat currency |
| Meaning to the customer | "At most this many USDC leave my wallet" | "At most $50 per 30 days" |
| Needs a price | **No** | **Yes** |
| Failure if alone | Cannot be reasoned about in fiat | Depends on a price attestation that could be wrong |

Both must pass on every charge. Token caps are the oracle-free bound of loss; fiat caps carry the business promise. Prices enter the chain only as **signed, expiring quotes** whose price must lie inside **registry bounds**.

## 2. The three cap classes

| Class | Meaning | Who can make it looser |
|---|---|---|
| **`ONCHAIN_HARD`** | A number the contracts enforce from the customer-signed mandate alone. Needs no price, no oracle, no quote, no backend | Nobody (existing mandates never widen) |
| **`QUOTE_BOUND_ONCHAIN`** | A number the contracts enforce **using a signed, expiring `PriceQuote` that passes the validity predicate in §4.2 and lies inside registry bounds**. Authoritative **only to the extent that a registered quote signer attested a price within those bounds** | Nobody on the backend; bounds are registry state behind a timelock and only narrow for existing mandates |
| **`BACKEND_ONLY`** | A control enforced by FastPay services before signing and in signer policy. The chain does not know it | Operators with two-approver loosening; it can only **tighten** what the chain allows and its failure cannot loosen anything |

Rule **C-1:** nothing in `BACKEND_ONLY` can make a charge succeed that the other two classes reject.
Rule **C-2:** the failure of a `BACKEND_ONLY` component may stop charges (fail closed); it must never cause an `ONCHAIN_HARD` or `QUOTE_BOUND_ONCHAIN` bound to be skipped.
Rule **C-3:** an `ONCHAIN_HARD` check never depends on a quote, so a quote-signer outage or compromise cannot raise any `ONCHAIN_HARD` number (proved in §4.8).

### 2.1 Classification of every cap and limit

| # | Limit | Class | Enforced where | Source of the number | If the enforcer is wrong or down |
|---|---|---|---|---|---|
| 1 | Per-payment cap, per token (atomic units, fee included) | `ONCHAIN_HARD` | `MandateManager.consume` | Mandate (customer-signed) | Cannot be exceeded |
| 2 | Daily cap per token (86,400 s window anchored at the lineage start) | `ONCHAIN_HARD` | same | Mandate | Same |
| 3 | Weekly cap per token (604,800 s) | `ONCHAIN_HARD` | same | Mandate | Same |
| 4 | "Monthly" cap per token (**30-day** window, 2,592,000 s; not calendar months) | `ONCHAIN_HARD` | same | Mandate | Same |
| 5 | Billing-period cap per token (lineage `periodSeconds`) | `ONCHAIN_HARD` | same | Mandate | Same |
| 6 | Total cap per token (lineage lifetime) | `ONCHAIN_HARD` | same | Mandate | Same |
| 7 | Maximum charges per period; minimum interval between charges | `ONCHAIN_HARD` | same | Mandate | Same |
| 8 | Start time and expiration | `ONCHAIN_HARD` | same | Mandate | Same |
| 9 | Allowed token set, merchant, recipient resolution, router binding | `ONCHAIN_HARD` | `MandateManager`, `MerchantRegistry`, `RouterRegistry` | Mandate; registries | Same |
| 10 | Maximum fee per payment (mandate `maxFeeBps`) and the fee ceiling | `ONCHAIN_HARD` | `PaymentRouter`, `FeeController` (ceiling immutable) | Mandate; constant | Same |
| 11 | Required settlement output (merchant receives at least the required amount) | `ONCHAIN_HARD` | `PaymentRouter` (`I-MINOUT`) | Charge request bound to the mandate | Same |
| 12 | Fiat per-payment cap | `QUOTE_BOUND_ONCHAIN` | `PaymentRouter` + `QuoteVerifier` | Mandate; quote price | Bounded by rows 1–6 and by B2 below |
| 13 | Fiat daily, weekly, 30-day and billing-period caps | `QUOTE_BOUND_ONCHAIN` | same | Mandate; quote price | Same |
| 14 | Fiat total cap | `QUOTE_BOUND_ONCHAIN` | same | Mandate; quote price | Same |
| 15 | Maximum slippage and maximum price impact | **Router v1.1 only** (`QUOTE_BOUND_ONCHAIN`: realized amounts versus a `PriceQuote` v2) | — | — | **Absent in v1.0**: no field, and `extensionsHash` must be zero |
| 16 | Maximum network cost policy | `BACKEND_ONLY` | Orchestrator refuses to submit above the ceiling; signer policy | Risk configuration | Chain unaffected; gas is paid by executors (OD-002) |
| 17 | Merchant daily/weekly volume; per-customer velocity; global beta limits and circuit breakers | `BACKEND_ONLY` | Risk service, orchestrator, signer policy | Risk configuration (two approvers to loosen) | Chain bounds still hold |
| 18 | Independent-source price deviation tighter than the on-chain band | `BACKEND_ONLY` | Quote service and orchestrator | Risk configuration | On-chain band still holds |
| 19 | Token concentration, venue health, depeg signals | `BACKEND_ONLY` (decision) | Risk service; may trigger an on-chain **block** by the guardian (stop-only) | Risk configuration | Chain bounds hold; a block is applied separately |
| 20 | Fraud, AML and sanctions decisions | `BACKEND_ONLY` | Risk service; may pause a mandate | Compliance policy | Pause is stop-only; never widens |
| 21 | Variable-billing notification threshold | `BACKEND_ONLY` | Subscription service | Merchant plan | Chain caps hold |
| 22 | Sponsorship budget per merchant; retry budgets; dunning schedule | `BACKEND_ONLY` | Orchestrator | Finance and product policy | Chain unaffected |
| 23 | Account pin: charges stop if the customer account's code no longer matches what the customer pinned ([17](17-account-compatibility-policy.md)) | `ONCHAIN_HARD` (stop-only; never grants) | `MandateManager.consume` | Mandate (customer-signed); updated only by the customer | Cannot be bypassed; the backend revalidation covers what the chain cannot see |

**Not caps (records only):** cancellation policy and refund policy fields in the mandate; they are evidence and process, not limits.

## 3. Mandate fields (extends prompt §8)

```text
TokenCaps[token]                                         # ONCHAIN_HARD, atomic units of the INPUT token, fee included
  perPaymentMax   uint256
  windowMax       { DAY, WEEK, THIRTY_DAYS, BILLING_PERIOD }  uint256 each, 0 = unused
  totalMax        uint256
Frequency                                                # ONCHAIN_HARD
  maxChargesPerPeriod uint16     minIntervalSeconds uint32
FiatCaps (required by the checkout product rule; the contract requires at least one cap family)   # QUOTE_BOUND_ONCHAIN
  currency        uint16    ISO 4217 numeric code; one currency per mandate
  perPaymentMaxMinor  uint64
  windowMaxMinor  { DAY, WEEK, THIRTY_DAYS, BILLING_PERIOD }  uint64 each, 0 = unused
  totalMaxMinor   uint64
  maxQuoteAgeSeconds  uint32      <= registry maximum
  boundsVersion   uint32          the version of the price-bounds registry that the mandate pins; the band of (token, currency, boundsVersion) is read from the registry (ADR-020); the mandate carries no price pair
maxFeeBps         uint16    ONCHAIN_HARD; <= FEE_CEILING_BPS (immutable); a fee is part of the gross input
accountPin        AccountPin  the seven-field typed struct of 17 section 5.1; the mandate stores hashStruct(accountPin) and pinVersion;
                              PIN_WELLFORMED and PIN_OK(customer, accountPin) at activation and on every charge (document 17)
extensionsHash    bytes32   MUST be zero in v1.0 (data only; no behavior). A conversion consent would have to be carried here,
                            and the v1.0 manager refuses a non-zero value: a v1.0 mandate can never authorize conversion
Lineage constants (set at lineage creation, copied unchanged into every generation)
  merchantId, subscriptionRef, anchorStartsAt, periodSeconds, recipientPolicy
```

Window semantics: fixed-length windows **anchored at the lineage's first `startsAt`**: `index = floor((t − anchor) / windowLength)`; counters reset lazily when the index changes; **counters live in the lineage**, so successors keep the same grid ([12 §4](12-router-lifecycle-and-migration.md)). `THIRTY_DAYS` is exactly 2,592,000 seconds; consent copy says "per 30 days". Caps measure the customer's **gross input** (fee included); refunds do not restore usage.

### 3.1 Identifiers (independent of router version and generation)

```text
lineageId  = keccak256(abi.encode(LINEAGE_TAG, chainId, mandateManager, customer, merchantId, subscriptionRef, creationNonce))
mandateId  = keccak256(abi.encode(MANDATE_TAG, lineageId, generation))
cycleIndex : uint64, chosen by the charge request; valid iff cycleIndex <= floor((t − anchorStartsAt) / periodSeconds)  (no future cycles)
cycleId    = keccak256(abi.encode(CYCLE_TAG, lineageId, cycleIndex))
paymentId  = keccak256(abi.encode(chainId, mandateManager, lineageId, cycleId))        # recurring; Pay Once: see 10 §2
TAG        = keccak256("fastpay.lineage.v1" | "fastpay.mandate.v1" | "fastpay.cycle.v1")
```

`abi.encode`, not packed; every item is a 32-byte word. **No router address, router version, mandate id or generation enters `cycleId` or `paymentId`.** A cycle settled under router A cannot settle again under router B or in a later generation: the record is `cycleSettled[lineageId][cycleIndex]` in the manager (`I-ONCE`). `subscriptionRef` is the stable subscription identity chosen when the lineage is created (the merchant's subscription id hashed with the plan reference); `periodSeconds` is the billing period for fixed subscriptions. A late retry of cycle `k` in a later calendar period is allowed (the cycle is still unsettled), subject to all caps and the minimum interval.

## 4. The signed quote schema (`PriceQuote` v1)

### 4.1 Typed data

```text
EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)
   name = "FastPay Quote"   version = "1"   chainId = the chain   verifyingContract = the PaymentRouter that will consume the quote

PriceQuote(bytes32 paymentId,address payer,address token,uint256 amountIn,uint16 currency,uint256 priceE18,
           uint64 issuedAt,uint64 validAfter,uint64 validUntil,uint256 nonce,uint32 signerSetVersion,
           uint64 registryVersion,uint32 boundsVersion,bytes32 routeHash,bytes32 priceSourceSetHash)
```

| # | Field | Type | Meaning and encoding |
|---|---|---|---|
| 1 | `paymentId` | `bytes32` | §3.1. Binds the quote to one lineage and cycle (recurring) or to one order (Pay Once). The router recomputes it from the charge |
| 2 | `payer` | `address` | The customer account; must equal the mandate's customer |
| 3 | `token` | `address` | The input token charged |
| 4 | `amountIn` | `uint256` | Atomic units; must equal the amount actually charged, exactly |
| 5 | `currency` | `uint16` | ISO 4217 numeric code (840 = USD) |
| 6 | `priceE18` | `uint256` | Fiat **minor units per one whole token**, scaled by 1e18 (USD 1.00 per token = 100 cents → `100e18`) |
| 7 | `issuedAt` | `uint64` | Unix seconds when the signer produced the quote; the TTL is measured from here |
| 8 | `validAfter` | `uint64` | First second at which the quote may be consumed; `issuedAt ≤ validAfter` |
| 9 | `validUntil` | `uint64` | Last second at which it may be consumed (inclusive) |
| 10 | `nonce` | `uint256` | Signer-chosen value, unique per quote. The contract keeps no nonce set (replay is prevented by `paymentId` settle-once); the nonce makes each digest distinct, identifies exactly one quote in events and disputes, and is stored with the cycle record |
| 11 | `signerSetVersion` | `uint32` | The registry signer-set version the signer belongs to (§4.7) |
| 12 | `registryVersion` | `uint64` | `TokenPolicyRegistry.tokenVersion(token)` when the quote was issued; any change to the token's policy (status, bounds, source set, decimals) increments it |
| 13 | `boundsVersion` | `uint32` | The price-bound version for `(token, currency)` |
| 14 | `routeHash` | `bytes32` | v1: `keccak256(abi.encode(ROUTE_DIRECT_TAG, chainId, token))`: direct settlement in `token`, no conversion. A conversion route hash is `PriceQuote` v2 |
| 15 | `priceSourceSetHash` | `bytes32` | Hash of the registered price-source set (identifiers and versions) the signer used. Compared with the registry's value for `(token, currency)`; the signer **attests** it used that set, the chain cannot verify the readings |

`hashStruct = keccak256(typeHash ‖ enc(field₁) ‖ … ‖ enc(field₁₅))` with every static type left-padded to 32 bytes; `domainSeparator = hashStruct(EIP712Domain)` with `name` and `version` hashed as strings; `digest = keccak256(0x1901 ‖ domainSeparator ‖ hashStruct)`.

Signature: **ECDSA over secp256k1 by a registered quote signer** (HSM key of class `quote`, TM-10): 65 bytes `r ‖ s ‖ v`, `v ∈ {27, 28}`, **low-`s` only**, recovered address non-zero. ERC-1271 quote signers are **not supported in v1**.

The fiat value is **derived by the contract**, never supplied by the signer:

```text
fiatValueMinor = ceil( amountIn * priceE18 / ( 10^tokenDecimals * 10^18 ) )          # round UP
```

`tokenDecimals` is fixed in the registry per listed token (never read from the token at charge time).

### 4.2 Validity predicate (all must hold, else revert)

| # | Check | Error |
|---|---|---|
| Q1 | The recovered signer is a member of signer set `signerSetVersion` **and `removedAt(signer) = 0`** (no tombstone: a removed key is rejected in every set version, with no grace, §4.7) | `QuoteSignerUnauthorized` (not a member), `QuoteSignerRemoved` (tombstoned) |
| Q2 | Signature is well formed: 65 bytes, low-`s`, valid `v`, recovered address non-zero | `QuoteSignatureInvalid` |
| Q3 | Domain matches: `chainId == block.chainid` and `verifyingContract == address(this)` | `QuoteDomainMismatch` |
| Q4 | `paymentId` equals the charge's `paymentId` | `QuoteBindingMismatch` |
| Q5 | `payer` equals the mandate's customer | `QuoteBindingMismatch` |
| Q6 | `token` equals the charged token | `QuoteBindingMismatch` |
| Q7 | `amountIn` equals the charged amount exactly | `QuoteBindingMismatch` |
| Q8 | `currency` equals the mandate's fiat currency | `QuoteBindingMismatch` |
| Q9 | `issuedAt ≤ validAfter` and `validAfter ≤ validUntil` | `QuoteTimesInvalid` |
| Q10 | `validAfter ≤ block.timestamp` | `QuoteNotYetValid` |
| Q11 | `block.timestamp ≤ validUntil` | `QuoteExpired` |
| Q12 | `validUntil − issuedAt ≤ min(mandate.maxQuoteAge, registry.maxQuoteTtl)` | `QuoteTtlTooLong` |
| Q13 | Signer set `signerSetVersion` exists, **is not stopped**, `activeFrom ≤ issuedAt`, and either `retiredAt = 0` or (`issuedAt < retiredAt` and `block.timestamp ≤ retiredAt + QUOTE_SET_GRACE`) | `QuoteSignerSetRetired`, `QuoteSignerSetStopped` |
| Q14 | `registryVersion` equals `tokenVersion(token)` | `RegistryVersionStale` |
| Q15 | `boundsVersion` equals the registry's current version for `(token, currency)` | `BoundsVersionStale` |
| Q16 | `routeHash == keccak256(abi.encode(ROUTE_DIRECT_TAG, chainId, token))` | `QuoteRouteMismatch` |
| Q17 | `priceSourceSetHash` equals the registry's source-set hash for `(token, currency)` | `QuoteSourceSetMismatch` |
| Q18 | `priceE18` lies in `[max(minPin, minCur), min(maxPin, maxCur)]` — the **intersection** of the band of the bounds version that the mandate pins and the current band (a pinned version that was never published is `BoundsNotPublished`) | `PriceOutOfBounds` |
| Q19 | `fiatValueMinor` fits `uint64` and the fiat caps hold (per payment, each window, total) | `FiatPerPaymentCapExceeded`, `FiatWindowCapExceeded`, `FiatTotalCapExceeded` |
| Q20 | The `paymentId` has not already settled (once-only, ADR-009); on success the cycle record stores the quote digest | `PaymentAlreadySettled` |

The mandate guard "`extensionsHash == 0`" (error `ExtensionsNotSupported`) is not a quote check; it is guard G10 of §4.8.

**Implementation note (Q3).** In the contracts Q3 is not an observable failure on its own: the digest is built from this chain's id and this router's address, so a quote signed for another domain recovers another address and fails Q1 (`QuoteSignerUnauthorized`). `QuoteDomainMismatch` is therefore not raised; the test `Quote.t.sol::test_Q3_AQuoteForAnotherRouterDoesNotVerify` shows the behaviour.

### 4.3 Registry state used by the verifier

```text
PriceBounds[token][currency][boundsVersion]   { minPriceE18, maxPriceE18 }   # append-only versions, width <= MAX_BAND_WIDTH_BPS; timelocked governance; guardian can only block
TokenPolicy[token]             { status, decimals, tokenVersion, priceSourceSetHash[currency], ... }
QuoteSignerSet[version]        { members[], activeFrom, retiredAt, stopped }       # timelocked governance; guardian can only remove a member or stop a set
SignerTombstone[key]           { removedAt (0 = never), reason, compromisedFrom }   # permanent; a tombstoned key can never join a set
maxQuoteTtl (<= MAX_QUOTE_TTL, immutable ceiling), QUOTE_SET_GRACE (immutable, in [MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL])
```

No oracle reference exists in v1. A volatile token cannot receive a fiat-capped mandate in v1.0 (it is not eligible at all; direct settlement is stablecoin only).

### 4.4 Canonical JSON (API and logs)

```json
{ "schemaVersion": 1,
  "domain": { "name": "FastPay Quote", "version": "1", "chainId": "84532", "verifyingContract": "0x…" },
  "message": { "paymentId": "0x…", "payer": "0x…", "token": "0x…", "amountIn": "49990000", "currency": "840",
               "priceE18": "100000000000000000000", "issuedAt": "1800000000", "validAfter": "1800000000",
               "validUntil": "1800000120", "nonce": "424242", "signerSetVersion": "3", "registryVersion": "12",
               "boundsVersion": "1", "routeHash": "0x…", "priceSourceSetHash": "0x…" },
  "signature": "0x…" }
```

All integers are decimal strings; addresses lowercase hex; hashes `0x` + 64 hex. Floating point never appears. Field order in `message` is the order of §4.1.

### 4.5 Versioning

`PriceQuote` v1 is frozen at protocol freeze (RG-016). Any added or changed field creates `PriceQuote` **v2** under domain `version = "2"` and a different type hash, consumed by a different router version. A conversion quote (route, output token, `amountOut`) is `PriceQuote` v2 and exists only with Router v1.1 ([09](09-capability-boundaries.md)). A v1 quote can never validate on v1.1 and vice versa: the domain differs and the router address differs.

### 4.6 Reproducible test vector

Generated by [tools/eip712_vectors.py](tools/eip712_vectors.py) (pure Python Keccak-256 and EIP-712, self-checked against known Keccak vectors and the standard `EIP712Domain` type hash) and synchronized into this table by [tools/sync_vectors.py](tools/sync_vectors.py). Addresses are illustrative. **The Solidity implementation and the backend must both reproduce these values** (CI check, `EPIC-P0-PLANNER` / `EPIC-P1-CONTRACTS`).

<!-- BEGIN:VEC_QUOTE -->
| Item | Value |
|---|---|
| `chainId` | 84532 |
| `verifyingContract` (router A) / router B | `0x1111111111111111111111111111111111111111` / `0x1212121212121212121212121212121212121212` |
| `mandateManager` | `0x2222222222222222222222222222222222222222` |
| `customer` = `payer` | `0x4444444444444444444444444444444444444444` |
| `merchantId` / `subscriptionRef` | `0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` / `0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` |
| `creationNonce` / `cycleIndex` | 7 / 1 |
| `token` / decimals | `0x5555555555555555555555555555555555555555` / 6 |
| `amountIn` / `currency` / `priceE18` | 49,990,000 / 840 / `100e18` |
| `issuedAt` / `validAfter` / `validUntil` | 1,800,000,000 / 1,800,000,000 / 1,800,000,120 |
| `nonce` / `signerSetVersion` / `registryVersion` / `boundsVersion` | 424242 / 3 / 12 / 1 |
| `priceSourceSetHash` = `keccak256("fastpay-test-source-set-v1")` | `0x1b7e9ef15cee6e37b6d59cbdb99f46a322e8a2109daa9e5c0c2a4a82c222d5d7` |
| `routeHash` = `keccak256(abi.encode(tag("fastpay.route.direct.v1"), chainId, token))` | `0xfdd8df3c220e58908ac7930433326b449ae46ddf928029a7fb6949364907d2d7` |
| `lineageId` | `0x6ad40af8ba8b2575c865f668a66e44bf4593949326bb0abd9347fb3867a8a7d7` |
| `mandateId` (generation 0) | `0x6be2553b584eafae19d0d8042907ddc82eb19554ad31473458e2ab0c0c2693ba` |
| `cycleId` | `0xfdd3ccb4b08ac939d2b360ea615ca69dd50d27a86f6f76b6b99b99f14ba6e5fb` |
| `paymentId` (recurring) | `0xce0a7f5ef5ed03bc11198df6b564080f5512104724ad5ffd89a1a7f5d1eb07e3` |
| **EIP712Domain type hash** | `0x8b73c3c69bb8fe3d512ecc4cf759cc79239f7b179b0ffacaa9a75d522b39400f` |
| **`PriceQuote` type hash** | `0x384641be814e75f4dce15c63df78fd013ed6055d9b4aeb1c855dc0ed3ec275c4` |
| **Domain separator** (router A) | `0xf57423e1f3b9586afce650d682c7a0588bd96ddf5d1adb019358d198664a61d4` |
| **Struct hash** | `0xad342b0681d76d0f3a825f0a2aa37e91345cde4a7373b562738492cf4f277986` |
| **Digest** (router A) | `0x0326193de0387563de812611b1308f36c257a9d97a9b8be8cee2151e65672220` |
| Digest for the same message on router B (must differ) | `0xbe9f3e114405cdcf58ac12a216c83876420cb6dd4f0fc70350caee545110c8bc` |
| `fiatValueMinor` | 4,999 (cents) |

`TAG(s)` is `keccak256(s)` as ASCII; the type string of `PriceQuote` is the one in §4.1 with no spaces after commas.
<!-- END:VEC_QUOTE -->

Signatures are produced by the test harness with a test key; no signature appears in this document.

### 4.7 Signer sets: planned rotation and emergency removal

Two different events have two different guarantees. **A key that is rotated out in the normal course keeps a bounded grace for quotes it already issued. A key that is believed compromised gets no grace at all.**

| | Planned rotation | Emergency removal |
|---|---|---|
| Who | Governance, behind the registry timelock | The **guardian**, immediately (stop-only); or governance |
| When | On the rotation schedule (90 days, PROPOSAL, OD-027), after a key ceremony, or on suspicion **without** evidence that a key was exposed | On evidence or reasonable suspicion that a key was exposed, copied, misused or signed outside policy |
| Effect | `retiredAt(v) = now` and set `v+1` becomes current; members of `v` stay valid **only for quotes issued before `retiredAt(v)`** | `removedAt(k) = now`: Q1 fails for key `k` in **every** set version, current or retired, from the block of the removal |
| Grace | **Yes, bounded:** `issuedAt < retiredAt(v)` and `now ≤ retiredAt(v) + QUOTE_SET_GRACE` (and before the quote's own `validUntil`); `QUOTE_SET_GRACE ∈ [MAX_QUOTE_TTL, 2 · MAX_QUOTE_TTL]` (PC-08) | **None. Zero seconds**, whatever the quote's `issuedAt` and `validUntil` |
| Re-registration | A retired key may appear in a later set only through governance | **Never.** The key is tombstoned: `proposeSignerSet` reverts `QuoteSignerTombstoned` for it, and not even governance can clear a tombstone |
| A whole set | — | `stopSignerSet(v)` by the guardian: Q13 fails for the whole set at once, no grace (suspected compromise of the ceremony, the HSM or the key custodian) |
| Replacement keys | Governance proposes set `v+1` | Governance only, behind the timelock. **The guardian cannot add a key or a set** (stop-only guardian, ADR-010) |
| While waiting for a replacement | — | If the current set has no unremoved member, fiat-capped charges **fail closed**; token-capped-only mandates are not affected (their guards do not read a quote, §4.8) |

| Rule | Behavior |
|---|---|
| **KR-1 Sets are versioned** | `QuoteSignerSet[v]` has members, `activeFrom`, `retiredAt` (0 while current) and a `stopped` flag. Exactly one set is current. A quote names its set in `signerSetVersion`; the verifier checks membership in **that** set (Q1) |
| **KR-2 Rotation (planned)** | Governance proposes set `v+1` (new HSM keys, optionally retaining old members, none of them tombstoned) behind the registry timelock; on activation `activeFrom(v+1) = now` and `retiredAt(v) = now`. The quote service switches to `v+1` at activation |
| **KR-3 In-flight quotes** | A quote of set `v` is valid iff it was issued before `retiredAt(v)`, is consumed no later than `retiredAt(v) + QUOTE_SET_GRACE` (Q13), and in any case before its own `validUntil`. `QUOTE_SET_GRACE` is an immutable constant at least as long as `MAX_QUOTE_TTL`, so no honest quote dies at a rotation, and at most twice as long, so a retired key does not linger |
| **KR-4 Emergency removal** | `removeQuoteSigner(key, reason, compromisedFrom)` (guardian or governance): sets `removedAt(key) = block.timestamp`; Q1 fails for that key everywhere from that block; the key is tombstoned forever. The guardian cannot add a key or a set. Event `QuoteSignerRemoved(key, reason, compromisedFrom, removedAt)` |
| **KR-4b Set stop** | `stopSignerSet(v)` (guardian or governance): `stopped(v) = true`; Q13 fails for every quote of `v`; irreversible for that version (a replacement is a new set) |
| **KR-5 Compromise window** | From compromise to removal a malicious signer can sign quotes **inside the bounds**; the loss is bounded by B2 and B4 of §6 and by the quotes consumed in that window. Target removal latency: 15 minutes from alert (PROPOSAL); alert on price skew against independent sources, nonce reuse, and quote volume off pattern. **After the removal no quote of that key validates.** Quotes already settled cannot be undone on chain; the incident commander sets `compromisedFrom`, and every settled payment whose `signer = key` and `issuedAt ≥ compromisedFrom` goes to a review queue (`quote.signer.compromise.review`) |
| **KR-6 Version counters** | `signerSetVersion` increments on every rotation; `tokenVersion(token)` (Q14) increments on any change to that token's policy; `boundsVersion` increments on bounds changes. A removal or a set stop changes a flag, **not** a version counter, so a quote's `signerSetVersion` stays meaningful for forensics. A change of one counter never changes another |
| **KR-7 Ceremony** | New keys are generated in the HSM under dual control, public keys registered through governance, old keys destroyed after `QUOTE_SET_GRACE` plus the log-retention period; planned rotation every 90 days and on any suspicion (PROPOSAL, OD-027). A key removed in an emergency is never reused, and its HSM slot is quarantined for forensics |
| **KR-8 Liveness** | A set of at least two keys held by independent custodians is required in production, so that one emergency removal leaves a working set; any single registered key suffices to sign (a k-of-n rule is an open point, UD-08) |
| **KR-9 Recovery** | When removals empty the current set, recovery is governance's proposal of a new set; its latency is the timelock (72 h minimum, PC-14). Whether the guardian may promote a **pre-registered standby set** to shorten this is an open decision (OD-036); the default is that it may not |

#### 4.7.1 The formal model

```text
Removed(k)               ≡ removedAt(k) ≠ 0                                    # permanent
SetUsable(v, q, now)     ≡ ¬stopped(v) ∧ activeFrom(v) ≤ q.issuedAt
                           ∧ ( retiredAt(v) = 0 ∨ ( q.issuedAt < retiredAt(v) ∧ now ≤ retiredAt(v) + QUOTE_SET_GRACE ) )
SignerValid(k, v, q, now) ≡ k ∈ members(v) ∧ ¬Removed(k) ∧ SetUsable(v, q, now)        # Q1 and Q13
```

| # | Property | Why it holds |
|---|---|---|
| SR-1 No grace after removal | If `Removed(k)` at the consumption time, no quote signed by `k` is accepted, for every set version, `issuedAt` and `validUntil` | `¬Removed(k)` is a conjunct of Q1 and nothing else relaxes it |
| SR-2 Bounded, earlier-quotes-only rotation | If a quote of a retired set is accepted, then `issuedAt < retiredAt(v)` and `now ≤ retiredAt(v) + QUOTE_SET_GRACE`; the last moment any quote of `v` can be consumed is `retiredAt(v) + QUOTE_SET_GRACE`, and a quote issued at or after `retiredAt(v)` never validates under `v` | The third conjunct of `SetUsable` |
| SR-3 Monotone | A removal or a set stop never makes a previously rejected quote acceptable: `Accept_after ⊆ Accept_before` for every fixed `(k, v, q, now)`. A rotation adds only quotes of the new set | Both transitions only set flags or shorten `retiredAt`-bounded windows |
| SR-4 Tombstone permanence | Once `Removed(k)`, `k` stays removed and is never a member of any set that becomes current afterwards | `proposeSignerSet` rejects tombstoned keys; no function clears `removedAt` |
| SR-5 Fail closed | If every member of the current set is removed, or the current set is stopped, no quote verifies under the current version: fiat-capped charges revert; charges under mandates without fiat caps are unaffected | Q1/Q13; the guards G1…G12 do not read the quote (§4.8) |
| SR-6 Non-interference | Removal, stop, rotation and tombstoning change no mandate, no counter and no guard of §4.8 | They write only registry state read by Q1, Q13 |
| SR-7 The guardian cannot add | `removeQuoteSigner` and `stopSignerSet` are the only guardian powers over signer sets | Access control; test CAP-TV-32 |

These properties are **executable**: [tools/model_checks.py](tools/model_checks.py) explores a small signer-set state machine (rotate, remove a key, stop a set, advance time, sign, consume) exhaustively and asserts SR-1…SR-5; the same transitions and the boundary vectors CAP-TV-23…32 are exported to Foundry ([foundry/](foundry/), `SignerSet.t.sol`, not yet compiled or run).

### 4.8 A quote signer cannot override a mandate

**Setting.** A charge is accepted iff `ACCEPT(m, c, q, S)`, where `m` is the customer-signed mandate (with the lineage state), `c` the charge request, `q` the quote and `S` the chain state (registries, time, balances). The router and manager evaluate these guards:

| Guard | Condition | Reads |
|---|---|---|
| G1 | Mandate `ACTIVE`, no pause bit, `startsAt ≤ now < expiresAt`, cadence and `maxChargesPerPeriod` hold | `m`, lineage, time |
| G2 | The caller is the router the mandate is bound to; the router is chargeable | `m`, `RouterRegistry` |
| G3 | `PIN_OK(EXTCODEHASH(customer), m.accountPin)` | `m`, account code hash |
| G4 | `token ∈ m.tokens` and the registry status allows it | `m`, `TokenPolicyRegistry` |
| G5 | Token caps: per payment, each window, lineage total (`I-CAP-TOKEN`) | `m`, lineage, `c.amountIn` |
| G6 | `fee ≤ min(m.maxFeeBps · amountIn / 10⁴, ceiling)` | `m`, `FeeController` |
| G7 | The recipient is the one `MerchantRegistry` resolves now | `MerchantRegistry` |
| G8 | The merchant receives at least the required output (`I-MINOUT`) | balances |
| G9 | `cycleIndex ≤ currentIndex(now)` and `cycleSettled[lineageId][cycleIndex] = false` | lineage, time |
| G10 | `m.extensionsHash = 0` | `m` |
| G11 | `c` is authenticated by the merchant's `chargeSigner` (default tier: FastPay's HSM) | `c`, signature |
| G12 | The submitting executor is registered | `ExecutorRegistry` |
| **F** | If `m` has fiat caps: Q1–Q20 hold (this is the **only** guard that reads `q`) | `q`, `m` fiat fields, registry |

```text
ACCEPT(m, c, q, S)  ≡  G1 ∧ G2 ∧ … ∧ G12 ∧ ( hasFiatCaps(m) ⇒ F(q, m, c, S) )
```

**Theorem (non-interference).** For every quote `q` (whatever its content and whoever signed it, provided only that Q1–Q3 pass), `ACCEPT(m, c, q, S) ⇒ G1 ∧ … ∧ G12`.

*Proof.* `ACCEPT` is a conjunction in which `q` occurs only in `F`. Every conjunct G1…G12 is a function of `m`, `c` and `S` only (column "Reads"); none has `q` as an input. A conjunction implies each of its conjuncts. ∎

**Corollaries (what a malicious or compromised signer cannot do).**

| # | Statement | Why |
|---|---|---|
| N1 | Cannot cause a payment while the mandate is not active, is paused, is expired or is bound to another router | G1, G2 do not read `q` |
| N2 | Cannot raise or bypass any token cap; the loss is bounded by the token caps (B4) | G5 does not read `q`; `amountIn` is fixed by `c` and Q7 requires the quote to equal it |
| N3 | Cannot change the token set, the merchant, the recipient, the fee or the cycle | G4, G6, G7, G9 and `paymentId` binding (Q4) |
| N4 | Cannot submit or authorize a charge | G11 and G12 authenticate the charge separately; the signer's key class is separate from executor and charge-signer keys (TM-10) |
| N5 | Cannot make a cycle settle twice | G9 and Q20 |
| N6 | Cannot widen the price bounds | Q18 uses the intersection of the pinned band and the current band; a successor pins the same bounds version (K.6), so it reads the same pinned band ([12 §5.3](12-router-lifecycle-and-migration.md), ADR-020) |
| N7 | Cannot make an account that changed code pay | G3 |

**What it can do.** (a) refuse to sign: fiat-capped charges fail closed (B3); (b) choose a price inside the intersection band: it can under-count the fiat counter by at most the factor `(true price − lowest in-band price) / true price` per charge; the total outflow stays within `min(Σ token caps, F / m_low)` (B2, B4); (c) over-state a price, which only makes the charge fail a cap.

**Obligations on the implementation.** `QuoteVerifier.verify(...)` returns only `(fiatValueMinor, quoteDigest)`; the router passes `fiatValueMinor` to the fiat counters and `quoteDigest` to the cycle record and event, and uses nothing else from the quote (static check: no other use of the returned or decoded quote fields). Tests: (i) stateful fuzz in which the signer picks arbitrary quote fields and signs, asserting `accepted ⇒ accepted-without-F`; (ii) mutation tests that remove each of G1–G12 and each of Q1–Q20 in turn and require a failing test; (iii) an executable oracle for `ACCEPT` in the test suite compared with the contract on random states; (iv) CAP-TV-14…22.

## 5. Charge-time algorithm (on chain)

```text
charge(request, quote?):                           # recurring; Pay Once uses only the exact signed amount
 1  G1, G2, G3, G10: lineage active mandate bound to this router, status ACTIVE, no pause bit, within time, cadence OK,
    account pin holds, extensionsHash zero                                                                      # I-TIME, I-MIG-1, I-ACCT-PIN
 2  G4: token allowed by mandate and registry status                                                           # I-MANDATE, I-SNAPSHOT
 3  G9: cycleIndex <= currentIndex(now); cycleSettled[lineageId][cycleIndex] is false                         # I-ONCE
 4  G5 ONCHAIN_HARD: amountIn <= perPaymentMax[token]
                     for each window w: used[w][idx][token] + amountIn <= windowMax[w][token]   (if set)
                     lineage totalUsed[token] + amountIn <= totalMax[token]                                   # I-CAP-TOKEN
 5  G6, G7: fee within mandate and ceiling; recipient resolved from MerchantRegistry now
 6  F QUOTE_BOUND_ONCHAIN (if the mandate has fiat caps): quote passes Q1–Q20                                  # I-QUOTE, I-CAP-FIAT
 7  effects: update lineage counters; write cycleSettled and the quote digest (checks-effects-interactions)
 8  interactions: pull via Permit2 AllowanceTransfer, pay recipient and fee, G8 minOut,
    emit PaymentSettled(... fiatValueMinor, priceE18, quoteDigest, quoteNonce, signer)
```

Custom errors for steps 4 and 7: `TokenPerPaymentCapExceeded`, `TokenWindowCapExceeded`, `TokenTotalCapExceeded`, `PaymentAlreadySettled`, `AccountCodeChanged`, `ExtensionsNotSupported`, plus those in §4.2.

## 6. Blast radius (what each failure can cost the customer)

Let `F` be the mandate's fiat total cap (minor units), `m = min over listed tokens of minPriceE18 / 1e18` the lowest in-band price, and `T_i` token `i`'s total token cap.

| Scenario | Maximum outflow under the mandate | Reason |
|---|---|---|
| B1 All components honest | `F` at true prices | As designed |
| B2 Quote signer malicious, inside bounds | `F / m` whole tokens (≈ `F` × (1 + band slack)) | Each charge consumes at least `amountIn × m` of the shared fiat counter |
| B3 Quote signer unavailable | 0 (no fiat-capped charges) | Fail closed |
| B4 Quote signer malicious **and** bounds too wide | `Σ T_i` (token total caps) | Only `ONCHAIN_HARD` remains binding (§4.8 N2) |
| B5 Executor, charge signer and quote signer all compromised | The smaller of B2/B4 per lineage | All bounds are on chain and customer-signed |
| B6 Backend risk service down or wrong | Unchanged | `BACKEND_ONLY` can only tighten |
| B7 Governance acts maliciously | Cannot widen existing mandates (`I-SNAPSHOT`, `I-BOUNDS-SNAPSHOT`); can only block | Timelocked widening applies to new mandates only |

## 7. Planner derivation of token caps from fiat caps

```text
tokenCapForFiat(fiatMinor, token) = ceil( fiatMinor * 10^decimals * 1e18 / minPriceE18 )
```

Applied to the per-payment, each window, and the total caps. Optional headroom (`policy.capHeadroomBps`, default 0) may be added by Risk but must not exceed the band slack.

**Worked example (USD, USDC with 6 decimals, band 0.98–1.02):** $50.00 per 30 days → `5000` minor units; `minPriceE18 = 98e18`; token cap = `ceil(5000 × 10^6 × 1e18 / 98e18)` = `ceil(51,020,408.16…)` = **51,020,409** units. A quote at `100e18` for `49,990,000` units gives **4,999** cents. `10,000,001` units at `100.1e18` gives `1001.0001001` → **1,002** cents (never 1,001).

## 8. What the customer sees

1. Two numbers, always together: the **business limit** ("up to $50.00 every 30 days") and the **hard limit on the blockchain** ("never more than 51.02 USDC every 30 days, even if prices move or our systems fail").
2. Per-payment, per-30-days and total limits, expiry date, one-tap revoke.
3. For fiat limits: "Prices come from signed quotes that expire in under two minutes and must stay within a safety band."
4. The account type the customer is binding (document 17) in plain words, and that charging stops if the account changes.
5. Copy is a translation key plus parameters, counsel-reviewed (`LEGAL-REVIEW-REQUIRED`), checked for comprehension (≥80% can state both numbers).
6. The portal shows current usage for both cap families and the time to the next window.

## 9. Invariants and tests

| ID | Invariant | Tests |
|---|---|---|
| I-CAP-TOKEN | Per-token per-payment, window and total never exceeded, across a lineage | Invariant + fuzz around window boundaries and successor activation |
| I-CAP-FIAT | Derived fiat consumption never exceeds fiat caps; value rounded up | Fuzz on `fiatValueMinor`; property: Σ consumption ≥ Σ true value at any in-band price |
| I-QUOTE | A fiat-capped charge succeeds only if Q1–Q20 hold | Fuzz over every field; replay across payments, payers, tokens, chains and routers |
| I-QUOTE-NI | **Non-interference:** no quote can make a charge succeed that G1…G12 reject (§4.8) | Stateful fuzz with an adversarial signer; mutation tests; oracle comparison |
| I-BOUNDS-SNAPSHOT | Effective bounds never wider than the mandate's snapshot | Invariant with governance actions interleaved |
| Blast radius | B2 and B4 upper bounds hold under an adversarial signer | Property test with a signer choosing prices at the band edge |
| Vector reproduction | Type hashes, domain separator, struct hash and digest equal §4.6 | CI in Solidity and backend |

| CAP-TV | Input | Expected |
|---|---|---|
| CAP-TV-01 | $50.00, USDC (6 dec), band 0.98–1.02 | token cap 51,020,409 |
| CAP-TV-02 | $0.01, USDC | token cap 10,205 |
| CAP-TV-03 | 18-decimal token, band 0.99–1.01, $1,000.00 | `ceil(100000 × 1e18 × 1e18 / 99e18)` |
| CAP-TV-04 | `priceE18` one unit below `minPriceE18` | `PriceOutOfBounds` |
| CAP-TV-05 | `validUntil − issuedAt` = TTL + 1 | `QuoteTtlTooLong` |
| CAP-TV-06 | Quote amount differs from charged amount by 1 unit | `QuoteBindingMismatch` |
| CAP-TV-07 | Two charges straddling a window boundary | Counters reset for the new window only; total still binds |
| CAP-TV-08 | Bounds narrowed after activation | Effective bounds = intersection |
| CAP-TV-09 | Quote signed for router A presented to router B | `QuoteDomainMismatch` |
| CAP-TV-10 | Quote with `s` in the upper half of the curve order | `QuoteSignatureInvalid` |
| CAP-TV-11 | Quote `boundsVersion` older than the registry's current | `BoundsVersionStale` |
| CAP-TV-12 | Mandate with non-zero `extensionsHash` on Router v1 | `ExtensionsNotSupported` |
| CAP-TV-13 | Successor generation continues the 30-day window of its predecessor | Counter not reset by the successor |
| CAP-TV-14 | Quote from signer set `v` consumed after `retiredAt(v) + QUOTE_SET_GRACE` | `QuoteSignerSetRetired` |
| CAP-TV-15 | Quote from set `v` issued before `retiredAt(v)` and consumed inside the grace | Accepted |
| CAP-TV-16 | Quote from a signer removed by the guardian, any set version | `QuoteSignerRemoved` from the removal block (no grace) |
| CAP-TV-17 | `registryVersion` older than `tokenVersion(token)` | `RegistryVersionStale` |
| CAP-TV-18 | `routeHash` computed for another token or chain | `QuoteRouteMismatch` |
| CAP-TV-19 | `priceSourceSetHash` differs from the registry's | `QuoteSourceSetMismatch` |
| CAP-TV-20 | `issuedAt > validAfter` | `QuoteTimesInvalid` |
| CAP-TV-21 | Same `(lineageId, cycleIndex)` charged under router A then router B | Second reverts `PaymentAlreadySettled`; both `paymentId`s are equal (§3.1) |
| CAP-TV-22 | Adversarial signer: any quote fields, mandate paused or account pin broken | Charge reverts for G1 or G3; no quote changes the result |
| CAP-TV-23 | Key `k` is a member of the retired set `v`; the guardian removes `k` **inside the grace**; a quote of `v` issued before `retiredAt(v)` is consumed one second after the removal | `QuoteSignerRemoved` (emergency removal has no grace); the same quote one second before the removal is accepted |
| CAP-TV-24 | Key removed in the **current** set; a quote with `issuedAt` before the removal and `validUntil` well after it, consumed in the removal block after the removal and later | `QuoteSignerRemoved` in every case |
| CAP-TV-25 | Retired set `v`, quote `issuedAt = retiredAt − 1`: consumed at `retiredAt + QUOTE_SET_GRACE`, then at `retiredAt + QUOTE_SET_GRACE + 1` | Accepted; `QuoteSignerSetRetired` |
| CAP-TV-26 | Retired set `v`, quote `issuedAt = retiredAt` (not strictly earlier) consumed at `retiredAt` | `QuoteSignerSetRetired` |
| CAP-TV-27 | `proposeSignerSet` naming a tombstoned key; the same set with the key replaced | Reverts `QuoteSignerTombstoned`; accepted |
| CAP-TV-28 | `stopSignerSet(v)` for the current set and for a retired set inside its grace | Quotes of `v` revert `QuoteSignerSetStopped` in both cases; members' quotes of another version are unaffected |
| CAP-TV-29 | Every member of the current set removed; a fiat-capped charge; a charge under a mandate with no fiat cap | The fiat-capped charge reverts (no valid signer); the other charge succeeds (the guards do not read a quote) |
| CAP-TV-30 | A key that belongs to both `v` and `v+1`: a quote of `v` inside the grace, then the key is removed | Accepted before the removal; rejected after it under both versions |
| CAP-TV-31 | The guardian calls `removeQuoteSigner` on a removed key again; governance calls any function that clears a tombstone | Idempotent no-op or revert; there is no such function (the tombstone is permanent) |
| CAP-TV-32 | The guardian calls `proposeSignerSet`, `activateSignerSet` or adds a member | Reverts `NotGovernance` (the guardian cannot add) |

## 10. `BACKEND_ONLY` controls — design requirements

- Each control has an owner, a threshold, a change process (two approvers to loosen) and a metric.
- Controls run in the orchestrator **before** signing and in the signer policy as a second check (TB-04). The chain does not depend on them.
- Every denial carries a reason code, is evented, and is visible to the merchant in aggregate and to the customer if it affects them.
- Controls can pause a mandate (`PAUSED_BY_RISK`) but resuming never restores more authority than the customer granted.

## 11. Interaction with other protocols

| Topic | Rule |
|---|---|
| Pay Once ([10](10-pay-once-protocol.md)) | The signed exact amount is the hard cap; a quote may be bound through `quoteHash`; fiat caps do not apply to a single payment |
| Conversion (Router v1.1+, [09](09-capability-boundaries.md)) | `PriceQuote` v2, route-bound; conversion needs a mandate extension that a v1.0 manager refuses, so adoption is a new manager and a new mandate ([12 §5.7](12-router-lifecycle-and-migration.md)) |
| Migration ([12](12-router-lifecycle-and-migration.md)) | Counters are in the lineage; a migration successor can never widen any cap, expiry, merchant or token scope, fee cap or bound (containment, §5.3 of document 12) |
| Account policy ([17](17-account-compatibility-policy.md)) | The account pin is guard G3 |
| Ledger | Fiat value stored in minor units beside atomic units; the quote digest and nonce are kept as evidence; no floating point |

## 12. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Band widths per stablecoin and per chain; who may change them and how fast (OD-027); the immutable maxima `MAX_QUOTE_TTL` and `MAX_BAND_WIDTH_BPS` are production-blocking constants ([16 §7](16-freeze-decision-report.md)) | Risk Lead + Principal Architect |
| 2 | `THIRTY_DAYS` windows versus calendar months for subscription copy | Payments PM + counsel |
| 3 | Quote TTL default (120 s) and `maxQuoteAge` per merchant tier | Payments PM |
| 4 | Whether a quote-signer *set* needs a threshold (k-of-n) rather than any single signer; current design: any registered signer, bounded by B2 | Principal Architect + Security |
| 5 | Oracle-referenced bounds arrive with a later verifier version; confirm that no v1 data layout blocks it | Principal Architect |
| 6 | Cycle model for plans that are not fixed-period (variable billing, v1.1): `cycleIndex` semantics beyond `periodSeconds` | Payments PM |
