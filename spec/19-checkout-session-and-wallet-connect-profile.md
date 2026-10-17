# 19 — Checkout Session and Wallet-Connection Profile

| Field | Value |
|---|---|
| Artifact | FP-PRD-004 (new) |
| Version | 0.1.0 |
| Date | 2026-10-17 |
| Status | **PROPOSED. NOT PROTOCOL-FROZEN. REQUIRES SECURITY REVIEW. REQUIRES PRIVACY REVIEW. REQUIRES WALLET-LAB EVIDENCE.** A product and integration specification, **not protocol evidence.** Nothing here is implemented, tested on a wallet, reviewed or approved. It does not approve protocol freeze (RG-016 stays not approved, [16](16-freeze-decision-report.md)), alters no contract evidence, approves no configuration constant and changes no condition of `freeze_readiness.py` |
| Owner | Principal Product Manager (product decisions, session model), Wallet Protocol Engineer (connection profile) |
| Reviewers | Head of Security (required), Privacy Lead (required), Frontend / SDK Lead, Product Designer, QA Lead, Payments Core lead (sessions, webhooks), Merchant PM |
| Dependencies | [02](02-source-register.md) (the WalletConnect, EIP-1193 and EIP-6963 sources are **not retrieved**); [03](03-assumptions-decisions-risks.md) ASM-014, ASM-018, ASM-023, OD-013, OD-014, OD-022; [04](04-context-and-trust-boundaries.md) TM-02, TM-05, TM-06, TM-11, TB-02, TB-03, TB-06, TB-12; [05](05-evm-authorization-decision-tree.md) (recurring planner); [06](06-initial-architecture.md) §2.1 (S01, S02, S03, S15) and §3.2 (intent and attempt states); [08](08-production-blockers-and-release-gates.md) PB-021, PB-022, PB-024; [10](10-pay-once-protocol.md); [11](11-dual-cap-model.md) §4; [15](15-wallet-lab-matrix.md); [17](17-account-compatibility-policy.md) |
| Labels | `SECURITY-CRITICAL` `PRIVACY-CRITICAL` |
| Definition of Done | Every state transition has an identifier, a guard and an audit event, and every prohibited transition is listed; the session object and the connection profile are reviewed by Security and Privacy; every claim about WalletConnect or a wallet has moved from `UNVERIFIED` to a retrieved and pinned source and a wallet-lab run record; the configuration record CSR-01 is approved or replaced by its approvers; the open points of section 14 are closed or carried as recorded risks; nothing here contradicts documents 04, 06, 10, 11, 12 or 17 |

## 0. Scope, provenance and what this document does not do

**What it is.** The answer to one product question: *must an end customer install a wallet on the device that shows the checkout, or can FastPay work like a hosted checkout page?* It specifies the hosted, self-custody checkout, the `CheckoutSession` object and its state machine, the expiry rules, the quote lifecycle, the wallet-connection profile, the two QR codes, the customer experiences, and the merchant integration around them.

**Provenance.** Sections 1 to 10 follow the section list of the sponsor's instruction of 2026-10-17. The text of that instruction ended in the middle of section 10 (after "The authorization planner must choose among compatible"). The sentence is completed here as: *the authorization planner chooses among the compatible authorization paths (PO-1 to PO-6 of [10 §3](10-pay-once-protocol.md) for a payment, the paths of [05](05-evm-authorization-decision-tree.md) for a recurring activation) and no path is implied by the session.* Sections 11 to 15 (merchant integration, security and privacy requirements, evidence, open points, what is unchanged) were added by the author to cover what the original question asked for and what the analysis showed was needed. The sponsor should confirm or reject them.

**Evidence vocabulary.** `SPECIFIED` is a design position of this document, changeable by review. `UNVERIFIED` is any claim about a wallet, a wallet protocol or a third-party standard: it is E0 ([01](01-toc.md) evidence levels) until the official text is retrieved and pinned and a wallet-lab run record exists (E3). No wallet is called "supported" because of this document ([15 §2.1](15-wallet-lab-matrix.md)).

**Identifiers local to this document** (new families; they are not in the register of [README](README.md), and they are never reused): `CSD-` product decisions, `TR-` transitions, `PX-` prohibited transitions, `ER-` expiry rules, `QL-` quote-lifecycle rules, `CP-` connection-profile requirements, `CSU-` unverified claims, `SX-` security and privacy requirements, `GAP-` wallet-lab gaps, `OPN-` open points, `CSR-` configuration record.

**What this document does not do.**

| It does not | Where that is kept |
|---|---|
| Approve protocol freeze, or change `freeze_readiness.py` or its result | [16](16-freeze-decision-report.md) |
| Alter any contract, test, mutation or fork evidence | [REPORT.md](evidence/implementation/REPORT.md) |
| Approve or add a production-blocking constant. CSR-01 is **not** a PC record (it is backend configuration, [18](18-configuration-records.md) R-9) and is not counted by condition C-4 | CSR-01, §6.4 |
| Define, implement or allow a per-invoice deposit address | CSD-05 |
| Put an embedded or passkey wallet in v1 | CSD-06 |
| Claim that WalletConnect, any browser wallet or any mobile wallet works | §8.3, §13 |
| Define a typed charge request or a customer confirmation for an existing mandate | OPN-01 |
| Edit documents 05, 06, 10, 11, 12, 15, 16, 17 or 18 (so no freeze fingerprint of [14](14-protocol-freeze-pack.md) changes) | — |

## 1. Product decision

The decisions below were given by the sponsor in the conversation of 2026-10-17 (the answers to the four open questions of the architecture recommendation are CSD-05, CSD-11, CSD-08 and CSD-06). They are recorded here as product decisions. They are **not** approvals under [03](03-assumptions-decisions-risks.md) or [16](16-freeze-decision-report.md) and close no open decision there.

| ID | Decision |
|---|---|
| CSD-01 | **FastPay v1 uses a hosted, self-custody checkout.** FastPay hosts the checkout page. The customer's funds stay in the customer's own wallet until the router moves them to the merchant in one transaction; FastPay holds nothing in between (`I-ZEROBAL`, [10 §2.2](10-pay-once-protocol.md)) |
| CSD-02 | **A wallet is required, and it does not need to be installed on the device that shows the checkout.** The wallet may be a browser extension on the same computer, an app on a phone connected to a checkout on a computer, an app on the same phone, a wallet's in-app browser, or a hardware wallet behind one of those |
| CSD-03 | **Supported v1 connection classes:** browser wallets, WalletConnect, mobile deep links, wallet in-app browsers, and supported hardware-wallet paths (§8.1). All of them are `UNVERIFIED` until the wallet lab says otherwise |
| CSD-04 | **FastPay does not create, derive, recover, store or control customer keys.** No seed phrase, private key, keystore or recovery secret is requested, received, generated or held by any FastPay component. There is no "FastPay wallet" (TM-01, TM-05) |
| CSD-05 | **Per-invoice deposit addresses are excluded from v1.** There is no FastPay-controlled receiving address, no "send to this address" flow, and no QR code that encodes a payment destination. The merchant's settlement address stays the recipient registered in `MerchantRegistry` (OD-022) |
| CSD-06 | **Embedded and passkey wallets are deferred** to v2 or a separately approved product track. Nothing in v1 (data model, SDK, copy, planner input) may assume one |
| CSD-07 | **Resume by checkout URL and by checkout QR is included in v1** (§9, code B) |
| CSD-08 | **Resume by email is excluded from v1** pending Privacy review. OD-013 allows an optional, consented, minimal-retention email in principle; v1 collects no customer email |
| CSD-09 | **Hosted Checkout (S01) is the first implementation** ([06 §2.1](06-initial-architecture.md)) |
| CSD-10 | **Embedded Checkout (S02) and Payment Links (S03) reuse the same session model** and are separately gated (§11.5). Neither may change the meaning of a state, a guard or a deadline defined here |
| CSD-11 | **The proposed default session lifetime is 30 minutes.** The minimum and maximum are proposals only and are not approved (CSR-01) |

**Consistency with what exists.** S01, S02, S03 and S15 are surfaces of v1.0 in [06 §2.1](06-initial-architecture.md). ASM-014: merchants integrate through hosted or embedded checkout and REST APIs and never handle customer keys or raw customer authorizations. TB-02: the browser reaches the FastPay API with a session bound to the origin, a strict CSP, SRI and no third-party scripts in checkout. TM-05: the page may only request signatures of typed, named-field data. The non-goals of [06 §8](06-initial-architecture.md) already list custodial wallets and fiat on-ramps; CSD-05 adds deposit addresses to them by decision, not yet by edit.

## 2. The `CheckoutSession` object

`CheckoutSession` is the customer-facing envelope of one payment or one mandate activation. It wraps an **intent** and its **attempts** ([06 §3.2](06-initial-architecture.md)): the session is what the customer and the merchant see, the attempt is one try to move money. Field names are proposals for the API; they are not frozen.

### 2.1 Fields

Rows 1 to 27 are the 27 fields of the instruction. Rows 28 to 31 **add six fields** (`display`, `mandateTerms`, `authorizationPath`, `attemptId`, `controllerEpoch`, `cancelReason`) because a rule below needs them.

| # | Field | Type | Null | Set when | Mutable | Notes |
|---|---|---|---|---|---|---|
| 1 | `id` | string | no | creation | never | `cs_` followed by the unpadded base32 of at least 128 bits from a CSPRNG. Reveals no merchant, order, amount or time. **Never authentication and never spending authority** (§2.2) |
| 2 | `merchantId` | string | no | creation | never | The `merchantId` of the registry ([10 §2.1](10-pay-once-protocol.md)); taken from the API key, never from the request body |
| 3 | `clientReferenceId` | string | no | creation | never | The merchant's own reference (order number). Opaque to FastPay; never used as an on-chain value except through the hashed `paymentId` |
| 4 | `mode` | enum | no | creation | never | `PAYMENT`, `SUBSCRIPTION` or `SETUP` (§3) |
| 5 | `amount` | integer | no | creation | never | In minor units of `currency`. For `PAYMENT`: the amount to pay. For `SUBSCRIPTION`: the amount of an initial charge, 0 if none (§3.3) |
| 6 | `currency` | string | no | creation | never | ISO 4217 code accepted by `TokenPolicyRegistry`. It is the invoice currency a mandate pins (ADR-020) |
| 7 | `allowedChains` | list of chain ids | no | creation | never | Non-empty subset of the enabled chains. The test mode accepts testnets only, the live mode mainnets only |
| 8 | `allowedTokens` | list of (chain id, token address) | no | creation | never | Non-empty; each token must have status `SETTLEMENT` or `DIRECT_PAYMENT` ([10 §2.2](10-pay-once-protocol.md)) on its chain. A request that omits the list gets the merchant's default list, copied in at creation; the stored list is never empty |
| 9 | `expectedCustomerWallet` | address | yes | creation | never | Required for `EXPECTED_WALLET`, must be null for `ANY_WALLET` (§4) |
| 10 | `payerPolicy` | enum | no | creation | never | `ANY_WALLET` or `EXPECTED_WALLET` |
| 11 | `successUrl` | URL | no | creation | never | Validated against the merchant's registered domains (§11.4) |
| 12 | `cancelUrl` | URL | no | creation | never | As above |
| 13 | `status` | enum | no | creation | by transition only | The 13 states of §5.1 |
| 14 | `createdAt` | unix seconds, UTC | no | creation | never | Server clock |
| 15 | `expiresAt` | unix seconds, UTC | no | creation | never | `createdAt` plus the lifetime; within the bounds of CSR-01 (§6) |
| 16 | `metadata` | map of strings | no (may be empty) | creation | never | **Merchant-private.** Never shown to the customer, never in a URL, never in typed data, never on chain. Returned to the merchant in the API and in webhooks. Size limit: an API value, not set here |
| 17 | `liveMode` | boolean | no | creation | never | Test and live sessions never share a record, an API key or a webhook endpoint |
| 18 | `sessionVersion` | unsigned integer | no | creation (1) | +1 on every change | The compare-and-set counter of §5.4. Also the "session revision" of QL-01 |
| 19 | `selectedChain` | chain id | yes | `REVIEW_REQUIRED` | until `AWAITING_SIGNATURE` | Frozen from `AWAITING_SIGNATURE` on (PX-08) |
| 20 | `selectedToken` | address | yes | `REVIEW_REQUIRED` | until `AWAITING_SIGNATURE` | As above |
| 21 | `connectedWallet` | address | yes | `WALLET_CONNECTED` | until `AUTHORIZED` | Cleared on disconnect or account change. **Personal data** (ASM-023). Frozen as the payer at `AUTHORIZED` |
| 22 | `paymentId` | bytes32 | yes | chain selected (`PAYMENT`) | until `AWAITING_SIGNATURE` | The Pay Once `paymentId` of [10 §2.1](10-pay-once-protocol.md), derived from the chain id, the registry, `merchantId` and an order id that is a hash of `id` |
| 23 | `mandateId` | bytes32 | yes | activation observed, or a mandate used | once | Null for a Pay Once payment |
| 24 | `activeQuoteId` | string | yes | `REVIEW_REQUIRED` | by quote replacement only | At most one (QL-01). Carries `quoteHash` when a signed `PriceQuote` ([11 §4](11-dual-cap-model.md)) exists, otherwise an internal id |
| 25 | `submittedTransactionHash` | bytes32 | yes | hash recorded | by attempt | The hash of the **latest** attempt. Every hash ever submitted for the session is kept in the attempt log, and reconciliation reads all of them |
| 26 | `failureCode` | enum | yes | an attempt fails | by attempt | Last failure (vocabulary in §2.3). Kept on `FAILED` |
| 27 | `unknownReason` | enum | yes | `UNKNOWN` entered | cleared when resolved | Vocabulary in §2.3 |
| 28 | `display` | object | no | creation | never | Merchant-supplied text the customer is shown: merchant name, a short description, optional line items. **No personal data.** `termsHash` of the `PayOnceIntent` commits to it |
| 29 | `mandateTerms` | object | yes | creation | never | Required for `SUBSCRIPTION`: the `MandateTerms` of `eip712/types.json` the merchant requests. Null otherwise |
| 30 | `authorizationPath` | string | yes | `REVIEW_REQUIRED` | until `AWAITING_SIGNATURE` | The path code chosen by the planner: PO-1 to PO-6, or the activation path of [05](05-evm-authorization-decision-tree.md) |
| 31 | `attemptId`, `controllerEpoch`, `cancelReason` | string, unsigned integer, enum | yes | see notes | — | `attemptId`: the current attempt. `controllerEpoch`: counts the browser contexts that have controlled the session (§9.3, SX-08). `cancelReason`: `CUSTOMER`, `MERCHANT`, or one of `NO_WALLET`, `WALLET_UNSUPPORTED` given by the customer on leaving |

### 2.2 The session identifier and the checkout URL

- **CS-1 Public URL.** The hosted URL is `https://<checkout-origin>/c/<id>` and carries nothing else: no amount, no merchant, no order, no wallet address, no email, no token, no signature, no pairing URI, no secret. Everything the page shows is fetched by `id` from the API.
- **CS-2 Entropy.** `id` has at least 128 bits from a CSPRNG and is not derived from any other field. It is not sequential and not guessable; lookups of an unknown `id` return the same response as an expired one and are rate-limited (TB-02).
- **CS-3 Not authentication.** Possession of `id` identifies a session. It does not authenticate a customer, a merchant or a wallet.
- **CS-4 Not spending authority.** `id` cannot move funds, change a session field, read `metadata`, cancel through the API, or create a signature. Only a signature by the payer's account can authorize a payment (TM-01).
- **CS-5 What `id` does allow.** Reading the customer-visible part of the session (`display`, amount, currency, expiry, status) and trying to pay it. A person who obtains the URL can therefore open the page and, under `ANY_WALLET`, pay it from their own wallet. That is accepted (§4).
- **CS-6 Secrets are separate.** The embedded checkout uses a separate `client_secret` ([11.5](#115-embedded-checkout-and-payment-links-separately-gated)); it is never put in the hosted URL.
- **CS-7 Referrer.** The hosted page sets `Referrer-Policy: no-referrer`, so that the URL does not reach the merchant's or a third party's logs through a link on the page.

### 2.3 Initial vocabularies

These are the starting values for `failureCode` and `unknownReason`. They are proposals to be fixed with the API.

| `failureCode` | Retryable inside the session | Source |
|---|---|---|
| `USER_REJECTED` | yes, by pressing Pay again | wallet error `4001` ([10 §4](10-pay-once-protocol.md), WL-25) |
| `SIMULATION_REVERTED` | yes | `FAILED_PRE_SUBMISSION` ([06 §3.2](06-initial-architecture.md)) |
| `INSUFFICIENT_BALANCE`, `INSUFFICIENT_ALLOWANCE`, `INSUFFICIENT_NATIVE_GAS` | yes, after the customer acts | pre-signature checks (§7.3) |
| `QUOTE_EXPIRED`, `DEADLINE_PASSED` | yes, with a new quote | §6, §7 |
| `ACCOUNT_NOT_ELIGIBLE` | only with another wallet | [17](17-account-compatibility-policy.md) modes |
| `TOKEN_DISABLED`, `MERCHANT_DISABLED`, `CHAIN_UNSUPPORTED` | only with another token or chain, if allowed | registries |
| `SIGNATURE_INVALID`, `ACCOUNT_CHANGED`, `WALLET_MISMATCH` | yes | §4, §8 |
| `REVERTED_ON_CHAIN` | yes if the session is open | `FAILED_REVERTED` |
| `NOT_EXECUTED` | yes if the session is open | reconciliation proved non-execution |

`unknownReason`: `BROADCAST_AMBIGUOUS` (the transaction may have left the process), `NO_RECEIPT`, `RPC_DISAGREEMENT`, `INDEXER_LAG`, `REORG`, `WALLET_RESULT_LOST` (the customer may have confirmed in the wallet and the page lost the result).

## 3. Checkout session modes

| Mode | v1 | Meaning |
|---|---|---|
| `PAYMENT` | yes | One payment of `amount` in `currency` to the merchant |
| `SUBSCRIPTION` | yes | The customer activates a mandate with `mandateTerms` |
| `SETUP` | **reserved, not in v1** | A session whose only purpose is to create or update an authorization without a payment and without subscription semantics. The API rejects it with `mode_not_available`; no behaviour is defined |

### 3.1 `PAYMENT`

A payment may be authorized in one of two ways, and the session does not imply either:

1. **Pay Once.** The planner chooses among PO-1 to PO-6 ([10 §3](10-pay-once-protocol.md)) from the account's capabilities and the token's facts. **Pay Once does not always use Permit2 `SignatureTransfer`:** PO-1 needs an existing allowance to Permit2; PO-2 and PO-6 use transactions and no signature; PO-3 adds an ERC-2612 permit; PO-4 uses ERC-3009 behind a flag; PO-5 first sends an exact approval. The review screen shows the chosen path's number of prompts and transactions, never a path name.
2. **An existing compatible mandate.** **Not enabled in v1.** It would need proof that the person on the page controls the account, a typed confirmation bound to the session, and a mandate term that allows an ad hoc charge. None of the three exists (OPN-01). Until OPN-01 is closed, a returning customer is treated as a new customer for a `PAYMENT` (§10.9).

A compatible mandate, when it is eventually allowed, is one that is active, belongs to the same merchant and the current router, covers the chain and token, pins the same currency and `boundsVersion` ([12 §5.3.2](12-router-lifecycle-and-migration.md)), whose caps hold for the amount, whose account pin is valid, and whose terms allow it.

**Implementation status.** Of the Pay Once paths, the contracts implement `payOnceWithSignature` (PO-1, and PO-5 which only adds a customer transaction before it). PO-2, PO-3, PO-4 and PO-6 are not built ([contracts/README.md](../contracts/README.md)). A session must never offer a path whose entrypoint does not exist on the chain.

### 3.2 `SUBSCRIPTION`

The session creates a mandate through the activation planner of [05](05-evm-authorization-decision-tree.md). `COMPLETED` means that the activation was finalized and the mandate is active on chain. It **does not** mean that the first billing cycle settled.

### 3.3 Initial charge

`amount` is the initial charge of a `SUBSCRIPTION`. It is 0 unless the merchant explicitly requests one.

- `amount = 0`: `COMPLETED` is reached when the activation is finalized. No payment is made in the session. The first cycle is charged later by the orchestrator and reported as its own payment event, not as a session event.
- `amount > 0`: the initial charge is part of the session, and `COMPLETED` requires both the activation and the initial charge to be finalized. `chargeInitial` is **not built** (contracts README), so the API rejects `amount > 0` for `SUBSCRIPTION` until it is. The completed event states `initialChargeSettled`.

## 4. Payer policy

| Policy | `expectedCustomerWallet` | Rule |
|---|---|---|
| `ANY_WALLET` | must be null | The first wallet that is connected **and verified** becomes the payer for this payment |
| `EXPECTED_WALLET` | required, EIP-55 checksummed on input | The connected wallet must equal the server-provided address (compared as 20 bytes) |

**EXPECTED_WALLET.** A mismatch is not a failure of the session: the connection is refused, the wallet is disconnected, `failureCode = WALLET_MISMATCH` is recorded, and the session returns to `OPEN` (TR-04). The page shows only an abbreviated form of the expected address (the first six and last four characters): the URL is a bearer link and the address is personal data (ASM-023).

**ANY_WALLET.** "Verified" has four parts, and control of the account is proven only by the last one:
1. the connector returned an account that the customer approved in the wallet;
2. the chain of the connection equals `selectedChain`, read from the provider and from two independent RPC sources (TB-06);
3. the account was classified under [17](17-account-compatibility-policy.md) and is not refused for the chosen flow;
4. the authorization signature, once received, validates for that address (ECDSA recovery, or ERC-1271 for an account with code, [10 §3](10-pay-once-protocol.md) `sigOK`).

Until part 4 the address is a claim of the connector. At `AUTHORIZED` the payer is fixed; a later account change in the wallet changes nothing.

**No reusable identity.** The payer is a property of **this session**. FastPay must not:
- link two sessions through a cookie, a local-storage value, a fingerprint or a server-side join on the wallet address;
- create a customer profile, a customer id or a "remembered wallet" from a payment;
- send the address to a merchant other than the session's own merchant.

A returning customer is recognised by a **public chain read** of mandates for the connected address (§10.9), not by a stored association. The browser may remember which connector the customer used last (a connector name, not an address) in its own local storage; that value never reaches FastPay.

A third party who has the URL can pay an `ANY_WALLET` session from their own wallet. The merchant sees the payer address in the completed event and reconciles by `clientReferenceId`. A merchant that wants one specific payer uses `EXPECTED_WALLET`.

## 5. State machine

### 5.1 States

| State | Terminal | Meaning | Attempt state of [06 §3.2](06-initial-architecture.md) |
|---|---|---|---|
| `OPEN` | no | Created; no connector in use | none |
| `CONNECTING` | no | A connection is in progress: an extension prompt, a pairing code on screen, a deep link opened | none |
| `WALLET_CONNECTED` | no | An account and chain were returned and the payer policy passed; nothing reviewed yet | none |
| `REVIEW_REQUIRED` | no | A fresh quote and plan exist and the review screen is shown; also the state after any recoverable failure | `SIMULATING` while checks run |
| `AWAITING_SIGNATURE` | no | The interactive authorization phase: signatures and prerequisite customer transactions of the plan. **At most one prompt outstanding** | none |
| `AUTHORIZED` | no | FastPay holds every signature the relayed path needs, verified and unexpired; nothing submitted | none |
| `SUBMITTING` | no | The final transaction is being handed to a broadcaster: FastPay's executor, or the customer's wallet (the request was sent to it) | `SUBMITTING` |
| `PROCESSING` | no | A transaction hash is recorded and the transaction is not yet final | `SUBMITTED`, `PENDING`, `CONFIRMED` |
| `COMPLETED` | **yes** | The payment (or the activation) is final | `FINALIZED` |
| `FAILED` | **yes** | A submitted attempt is **proven** to have failed and no retry is possible | `FAILED_REVERTED` or proven non-execution |
| `UNKNOWN` | no | The fate of a submitted transaction is not known; being reconciled | `UNKNOWN`, `RECONCILIATION_REQUIRED` |
| `EXPIRED` | **yes** | `expiresAt` passed before any submission | none |
| `CANCELLED` | **yes** | Ended by the customer or the merchant before any submission | none |

A **submission** is the moment the final transaction is handed to a broadcaster. For a relayed path it is the executor's claim (TR-11). For a path in which the customer's wallet broadcasts it is the moment the transaction request is sent to the wallet (TR-12), because the customer may confirm it without FastPay learning of it. Prerequisite customer transactions of a plan (for example the exact approval of PO-5) are **steps of `AWAITING_SIGNATURE`**, not a submission; they change the customer's account state and remain after a cancellation or an expiry, and the page says so before it asks for them.

`UNKNOWN` is not terminal: it ends in `COMPLETED`, back in `REVIEW_REQUIRED`, or in `FAILED`, by chain evidence only. Refund states of the intent (`REFUND_PENDING` and later) are not session states.

### 5.2 Transitions

Every transition is a compare-and-set on `sessionVersion` (§5.4) and writes an audit event (§5.8). "Guard" is the condition that must hold when the transition is attempted.

| ID | From → to | Trigger and actor | Guard | Webhook |
|---|---|---|---|---|
| TR-01 | none → `OPEN` | Merchant creates the session | Authenticated merchant (TB-03); idempotency key; amount > 0 (or 0 for a `SUBSCRIPTION` with no initial charge); `currency`, chains and tokens valid; `expiresAt` within the bounds of CSR-01; `mode` available; payer policy consistent; URLs valid (§11.4) | none |
| TR-02 | `OPEN` → `CONNECTING` | Customer picks a connector | `now < expiresAt`; the context takes or holds the control lease (§9.3) | none |
| TR-03 | `CONNECTING` → `WALLET_CONNECTED` | Connector returns an account | Payer policy passed (§4); chain read agrees; `now < expiresAt` | none |
| TR-04 | `CONNECTING` → `OPEN` | Rejection, abandonment, pairing expiry, `WALLET_MISMATCH` | None beyond the state; `failureCode` set if a mismatch | none |
| TR-05 | `WALLET_CONNECTED` → `REVIEW_REQUIRED` | System | A quote was issued (QL-01 to QL-03) and a plan was made; `selectedChain`, `selectedToken`, `authorizationPath` set; account mode allows the flow | none |
| TR-06 | `REVIEW_REQUIRED` → `REVIEW_REQUIRED` | Quote replacement, or the customer changes token or chain | The old quote is superseded in the same write (QL-02); `sessionVersion` increases; no signing request outstanding | none |
| TR-07 | `WALLET_CONNECTED` or `REVIEW_REQUIRED` → `CONNECTING` | Disconnect, or account change | Before any signing request; `connectedWallet`, quote and plan are discarded | none |
| TR-08 | `REVIEW_REQUIRED` → `AWAITING_SIGNATURE` | Customer presses the pay button | All ten checks of §7.3 passed in this revision; `now + MIN_SIGN_WINDOW ≤ expiresAt` and `≤ quote.validUntil`; no other request outstanding for the session on any chain (PX-07) | none |
| TR-09 | `AWAITING_SIGNATURE` → `AUTHORIZED` | Wallet returns the last required signature | Every signature validates for `connectedWallet` and the signed fields equal what the review screen showed; ERC-1271 pre-flight `eth_call` passed where it applies ([10 §4](10-pay-once-protocol.md)); every deadline `≤ expiresAt` | none |
| TR-10 | `AWAITING_SIGNATURE` → `REVIEW_REQUIRED` | Rejection (`4001`), prompt timeout, account change, chain change, quote invalidation | The request is withdrawn; any signature that arrives later for it is discarded and never submitted; `failureCode` set | none |
| TR-11 | `AUTHORIZED` → `SUBMITTING` | FastPay's executor claims the authorization | `now < expiresAt`; every deadline unexpired; the router and merchant still eligible; compare-and-set wins | none |
| TR-12 | `AWAITING_SIGNATURE` → `SUBMITTING` | The final transaction request is sent to the customer's wallet | As TR-11; the intent's `validUntil ≤ expiresAt` | none |
| TR-13 | `SUBMITTING` → `PROCESSING` | A transaction hash is recorded | The hash comes from the broadcaster or the wallet; `submittedTransactionHash` set | `checkout.session.processing` (first time only) |
| TR-14 | `SUBMITTING` → `REVIEW_REQUIRED` | **Proof that nothing was broadcast** | An explicit wallet rejection, or an executor simulation failure before any broadcast; `failureCode` set | none |
| TR-15 | `SUBMITTING` → `UNKNOWN` | Ambiguity after the transaction may have left the process | No hash and no proof of non-broadcast after the operational timeout; `unknownReason` set | `checkout.session.unknown` |
| TR-16 | `PROCESSING` → `COMPLETED` | Finality | Receipt and the settlement event for `paymentId` (or the activation event for the mandate) agree across at least two independent sources at the chain's finality threshold (TM-06) | `checkout.session.completed` |
| TR-17 | `PROCESSING` → `REVIEW_REQUIRED` | The attempt reverted at finality | Revert seen from at least two sources; the retry rules of §5.5 allow a new attempt | none |
| TR-18 | `PROCESSING` → `FAILED` | The attempt reverted at finality | As TR-17, and the retry rules do not allow a new attempt | `checkout.session.failed` |
| TR-19 | `PROCESSING` → `UNKNOWN` | Reorg of a confirmed attempt, RPC disagreement, receipt not found, indexer lag beyond the threshold | `unknownReason` set | `checkout.session.unknown` |
| TR-20 | `UNKNOWN` → `COMPLETED` | Reconciliation proves settlement | As TR-16 | `checkout.session.completed` |
| TR-21 | `UNKNOWN` → `REVIEW_REQUIRED` | Reconciliation proves non-execution | The transaction was replaced or dropped **and** the account nonce was consumed by another transaction, or the chain shows no settlement for `paymentId` past the intent's deadline and the finality threshold ([06 §3.2](06-initial-architecture.md)); the retry rules allow a new attempt | none |
| TR-22 | `UNKNOWN` → `FAILED` | Reconciliation proves non-execution | As TR-21, and the retry rules do not allow a new attempt | `checkout.session.failed` |
| TR-23 | any state before `SUBMITTING` → `CANCELLED` | Customer in the controlling context, or merchant through the API | Compare-and-set on `sessionVersion`; the status is one of `OPEN`, `CONNECTING`, `WALLET_CONNECTED`, `REVIEW_REQUIRED`, `AWAITING_SIGNATURE`, `AUTHORIZED`; `cancelReason` set; held signatures are discarded | `checkout.session.cancelled` |
| TR-24 | any state before `SUBMITTING` → `EXPIRED` | The clock reaches `expiresAt` | Compare-and-set; the status is one of the six of TR-23; held signatures are discarded. **From `AWAITING_SIGNATURE` with a final-transaction request outstanding, the state is `SUBMITTING`, not `AWAITING_SIGNATURE` (TR-12), so this transition does not apply** | `checkout.session.expired` |

**After a transaction is submitted, the customer may close the page.** The session stays `PROCESSING` or `UNKNOWN` until chain evidence resolves it; closing the page, losing the connection, the wallet disconnecting or the session reaching `expiresAt` change nothing.

### 5.3 Prohibited transitions

| ID | Prohibited | Why |
|---|---|---|
| PX-01 | Any transition out of `COMPLETED`, `FAILED`, `EXPIRED` or `CANCELLED` | Terminal. A new payment needs a new session; a webhook or a late event never reopens one |
| PX-02 | `EXPIRED` or `CANCELLED` from `SUBMITTING`, `PROCESSING` or `UNKNOWN` | `CANCELLED` is valid only before submission; expiry never ends a submitted transaction |
| PX-03 | `FAILED` from any state before `SUBMITTING`, or from `UNKNOWN` or `PROCESSING` without proof | A pre-submission failure returns the session to `REVIEW_REQUIRED` or lets it expire; `FAILED` needs a final revert or proven non-execution |
| PX-04 | `COMPLETED` from any state but `PROCESSING` or `UNKNOWN`, or without the evidence of TR-16 | One source is a hint, not a money decision (TM-06) |
| PX-05 | `AWAITING_SIGNATURE` without the checks of §7.3 in the same revision | A stale quote or a stale account would be signed |
| PX-06 | A write with a stale `sessionVersion`, or any change that lowers or repeats it | Lost update, replay |
| PX-07 | Two outstanding signing or transaction requests for one session, on any chain | Duplicate signing-request prevention (CP-10) |
| PX-08 | A new attempt while the previous one is `SUBMITTING`, `PROCESSING` or `UNKNOWN`, on this chain **or any other chain of the session**; changing `selectedChain`, `selectedToken`, `authorizationPath` or `paymentId` from `AWAITING_SIGNATURE` on | [06 §3.2](06-initial-architecture.md): no fallback while unknown. `markSettled` makes a payment settle at most once **per chain**; across chains only this rule prevents a second payment |
| PX-09 | Changing `mode`, `amount`, `currency`, `merchantId`, `payerPolicy`, `expectedCustomerWallet`, `allowedChains`, `allowedTokens`, `successUrl`, `cancelUrl`, `metadata`, `display`, `mandateTerms` or `expiresAt` after creation | Immutable. Extending the lifetime is not possible: the merchant creates a new session |
| PX-10 | `AUTHORIZED` back to `OPEN`, `CONNECTING` or `WALLET_CONNECTED` | A held signature must be discarded by TR-23 or TR-24, not left behind |
| PX-11 | Entering `SUBMITTING` at or after `expiresAt` | The executor refuses; every signature deadline is already `≤ expiresAt` |

### 5.4 Idempotency and concurrency

- **Single writer.** Every transition runs under a lock on the session and is a compare-and-set on `sessionVersion`: the caller sends the version it read, and a mismatch returns a conflict and no change.
- **Replay.** Every transition carries an idempotency key (an event id). A replay returns the stored result and writes nothing.
- **Create.** `POST` of a session carries an idempotency key per merchant (TB-03). The same key with the same body returns the same session; the same key with a different body is an error.
- **Webhooks.** At least once, deduplicated by event id (§11.6).
- **Chain.** `RouterRegistry.markSettled(paymentId)` makes the payment settle at most once on a chain, across router versions ([10 §2.2](10-pay-once-protocol.md)). The Pay Once nonce is `keccak256(paymentId, attemptNumber)` ([10 §2.3](10-pay-once-protocol.md)), so each attempt has its own nonce.

### 5.5 Retry rules

| Attempt ended in | New attempt in the same session | Basis |
|---|---|---|
| `USER_REJECTED` | Yes, only when the customer presses the pay button again. FastPay never re-prompts by itself | [10 §4](10-pay-once-protocol.md) "no retry loop" |
| `FAILED_PRE_SUBMISSION` (simulation, balance, allowance, token, quote, policy) | Yes, with a new `attemptId` and a new nonce; another eligible token may be chosen | [06 §3.2](06-initial-architecture.md) |
| `FAILED_REVERTED` at finality from two sources | Yes if `now + MIN_SIGN_WINDOW < expiresAt` and the cause is retryable (§2.3); otherwise `FAILED` | [06 §3.2](06-initial-architecture.md) |
| `SUBMITTING`, `PROCESSING`, `UNKNOWN` | **No**, until reconciliation proves non-execution | [06 §3.2](06-initial-architecture.md) |
| `CONFIRMED`, `FINALIZED` | No: settled | |

A per-session limit on attempts exists and its value is not set here (OPN-05). `MIN_SIGN_WINDOW` is the value of [10 §3](10-pay-once-protocol.md) and [10 §9](10-pay-once-protocol.md) point 3; it is not set here either.

*Terminology.* [10 §4](10-pay-once-protocol.md) calls a user rejection `CANCELLED`. In this document that is an attempt-level event; the session state `CANCELLED` is an end by the customer or the merchant. The two need reconciling (OPN-02).

### 5.6 Browser-visible behavior

| State | The page shows | Allowed actions | Must not |
|---|---|---|---|
| `OPEN` | Merchant, amount, currency, expiry countdown, wallet choices, "Continue this checkout on your phone" | Choose a connector, cancel | Auto-connect (CP-02); show payment destination QR codes |
| `CONNECTING` | The connector's prompt, or code A with the label of §9 | Wait, choose another connector, cancel | Show other sessions' data |
| `WALLET_CONNECTED` | The abbreviated account, chain, a short wait while the quote is made | Disconnect | — |
| `REVIEW_REQUIRED` | The review screen of §10.0 and any blocker with its fix | Pay, change token or chain, refresh the quote, disconnect, cancel | Enable the pay button while a blocker or a stale quote exists |
| `AWAITING_SIGNATURE` | "Check your wallet", the step number, what the signature authorizes | Wait; "Send again" (QL-03 and CP-10 rules); cancel before the final request | Ask for a second prompt at once |
| `AUTHORIZED` | "Authorized, submitting" | Cancel (until the executor claims) | — |
| `SUBMITTING` | "Sending your payment", no cancel | Wait | Offer another token or chain |
| `PROCESSING` | The hash with an explorer link, the confirmations, "You can close this page" | Close | Offer a second payment; show "failed" |
| `COMPLETED` | Confirmation and a button that goes to `successUrl` | Leave | — |
| `FAILED` | What failed, whether funds moved (no, for a proven non-execution or a revert), the hash | Back to the merchant (`cancelUrl`) | Hide the hash |
| `UNKNOWN` | "We are confirming your payment. **Do not pay again.**" the hash, the time of the last check | Close, reopen the URL | Say "failed"; offer a second payment |
| `EXPIRED` | "This checkout expired", a button to the merchant | Leave | Offer to continue the same session |
| `CANCELLED` | "Cancelled", a button to the merchant | Leave | — |

After `expiresAt` the page for a session in `SUBMITTING`, `PROCESSING` or `UNKNOWN` stays available and keeps showing progress.

### 5.7 Webhook behavior

Six events leave the session, each on the transitions of §5.2: `checkout.session.processing`, `.unknown`, `.completed`, `.failed`, `.expired`, `.cancelled`. Every event carries the event id, the `sessionId`, `clientReferenceId`, `mode`, the new `status`, `sessionVersion`, `liveMode`, `metadata`, and, for `processing`, `unknown`, `completed` and `failed`, the chain, the token, the payer address, `paymentId` or `mandateId`, and the hash. `completed` for a `SUBSCRIPTION` carries `mandateId` and `initialChargeSettled`. `unknown` carries `unknownReason`; **a merchant must not fulfil on `unknown`.** Delivery rules are those of §11.6.

### 5.8 Audit events

Every audit record carries: `sessionId`, `from`, `to`, `sessionVersion`, `actor` (`customer`, `merchant`, `system`, `executor`, `reconciler`), the UTC time, and references to its evidence (hash, block, the sources that agreed). It never carries a signature, a secret or a seed.

`session.created`, `connect.started`, `connect.rejected`, `wallet.connected`, `wallet.changed`, `chain.changed`, `lease.taken`, `quote.issued`, `quote.replaced`, `quote.invalidated`, `review.shown`, `signature.requested`, `signature.rejected`, `signature.received`, `signature.invalid`, `authorization.recorded`, `submission.claimed`, `tx.hash_recorded`, `tx.confirmed`, `tx.finalized`, `tx.reverted`, `reconciliation.started`, `reconciliation.resolved`, `session.cancelled`, `session.expired`, `webhook.queued`, `webhook.delivered`, `webhook.failed`.

## 6. Expiry and deadlines

### 6.1 Lifetime

The proposed default is **30 minutes** (1,800 s, CSD-11). The minimum, default and maximum lifetimes that a merchant may configure are the configuration record CSR-01 (§6.4). **None of the three bounds is approved.** `expiresAt = createdAt + lifetime`, and the lifetime is chosen at creation inside the bounds.

### 6.2 Rules

| ID | Rule |
|---|---|
| ER-01 | A new authorization must not begin after session expiry: TR-08 requires `now + MIN_SIGN_WINDOW ≤ expiresAt` |
| ER-02 | A charge request's `validUntil` must not exceed session expiry. This covers `PayOnceIntent.validUntil` ([10 §2.1](10-pay-once-protocol.md)), which is already `≤` the quote validity and the signature deadline, and any typed request that OPN-01 may define |
| ER-03 | A signature deadline must not exceed session expiry: `signatureDeadline = min(quote.validUntil, now + sigTtl, expiresAt)` ([10 §2.3](10-pay-once-protocol.md), [05](05-evm-authorization-decision-tree.md) R-DEADLINE) |
| ER-04 | A quote must expire no later than session expiry: `quote.validUntil ≤ expiresAt` |
| ER-05 | Quote validity is substantially shorter than session validity. The default quote TTL is 120 s (OD-027) against a 30 minute session; the ceiling `MAX_QUOTE_TTL` is 300 s (PC-06, proposed). CSR-01 keeps the minimum session lifetime at least twice that ceiling |
| ER-06 | An expired quote may be replaced inside the same open session (TR-06, QL-02) |
| ER-07 | A transaction validly submitted before session expiry may confirm and finalize after it |
| ER-08 | Session expiry must never convert a submitted transaction into `FAILED`, `EXPIRED` or `CANCELLED` (PX-02, PX-03) |
| ER-09 | A submitted transaction is resolved with chain state and reconciliation: two independent sources at the finality threshold (TM-06), the settlement event for `paymentId`, the nonce of the account |
| ER-10 | The executor never starts a submission at or after `expiresAt` (PX-11); a transaction that was already broadcast and is mined later than its intent's `validUntil` reverts and moves nothing ([10 §4](10-pay-once-protocol.md)) |

Because every deadline is at most `expiresAt` (ER-02 to ER-04), **no payment can settle after the session expired through a signature or a request issued by this session.** What can happen after expiry is only the finalization of a transaction that was submitted before it (ER-07).

### 6.3 The clocks

| Clock | Value | Source | Status |
|---|---|---|---|
| Session `expiresAt` | 30 min default | CSR-01 | proposed |
| Quote validity | 120 s default, at most `MAX_QUOTE_TTL` 300 s | OD-027, PC-06 | proposed |
| Pay Once signature | `sigTtl` 300 s | [10 §2.3](10-pay-once-protocol.md) | proposal, backend configuration |
| Activation signature | `sigTtlSeconds` 900 s | [05](05-evm-authorization-decision-tree.md) R-DEADLINE | proposal, backend configuration |
| Minimum signing window | `MIN_SIGN_WINDOW` | [10 §3](10-pay-once-protocol.md) | **no value set** |
| Pairing and WalletConnect session | — | WalletConnect specifications | `UNVERIFIED` (CSU-06) |
| Finality | per chain | [06](06-initial-architecture.md) | per chain |

The server clock decides `expiresAt`; the chain compares deadlines with `block.timestamp` (TM-09). The difference between the two clocks does not matter for safety, because the chain deadline is never later than `expiresAt` and the chain enforces it.

### 6.4 CSR-01 — configuration record: checkout session lifetime

This record is **not** a production-blocking constant. It is backend configuration with no contract effect ([18](18-configuration-records.md) R-9), so it has no PC number, is not in the register of [18](18-configuration-records.md), is not counted by condition C-4 of `freeze_readiness.py`, and does not change that tool's result. If the product later makes it production-blocking, it becomes a PC record through [16](16-freeze-decision-report.md) §7. **Status: PROPOSED. Nothing in it is approved.**

| Field | Value |
|---|---|
| Symbols | `SESSION_LIFETIME_MIN`, `SESSION_LIFETIME_DEFAULT`, `SESSION_LIFETIME_MAX` (proposed identifiers: no document names them) |
| Kind | Backend-configured policy bound; off chain; no contract effect |
| Enforced in | The checkout-session service: validation at session creation (TR-01) and the timer of TR-24 |
| Proposed values | `SESSION_LIFETIME_MIN` 600 s (10 minutes); `SESSION_LIFETIME_DEFAULT` 1,800 s (30 minutes, CSD-11); `SESSION_LIFETIME_MAX` 86,400 s (24 hours) |
| Unit | Seconds |
| Hard minimum and maximum (the author's proposal) | MIN: 600 to 1,800. DEFAULT: `SESSION_LIFETIME_MIN` to `SESSION_LIFETIME_MAX`. MAX: 1,800 to 604,800 (7 days) |
| Testnet value | Same as the proposal; no shorter test value is proposed |
| Accountable owner | Payments PM |
| Consulted | Product Designer, Head of Security, Privacy Lead, Payments Core lead, Merchant PM |
| Required approvers | Payments PM; Head of Security (CISO); Privacy Lead |
| Release gate | None assigned. It must be approved before the first release that exposes hosted checkout beyond internal testnet use; the TPM assigns the gate (RG-006 covers the webhook and frontend controls of the same release) |
| Change control | A configuration change with notice to the CISO. A change applies to **new** sessions only: an existing session keeps its `expiresAt` (PX-09). No redeploy, no re-audit |
| Status | **PROPOSED** |

**Rationale.** A session must outlive several quotes and a human signing step, including the time to open a phone wallet and scan a code, and must not outlive the facts it displays (price, recipient, terms) for long. The default of 30 minutes was chosen by the sponsor (CSD-11). The minimum of 10 minutes is twice `MAX_QUOTE_TTL` (ER-05): a 5 minute minimum, which equals the ceiling, would leave no room to replace an expired quote and then sign. The maximum of 24 hours is long enough for a merchant that wants a customer to return later and short enough that the displayed terms do not go stale; a link that must live longer is a Payment Link (S03), which creates a new session per visit.

**Failure it prevents.** Too short: customers on a phone wallet cannot finish; every quote expires before signing. Too long: stale terms and a stale merchant recipient are shown for a long time, and a leaked URL stays useful.

**Mine, not a decision.** The three numbers, the hard ranges, the choice of 10 minutes over the 5 minutes mentioned earlier in the conversation, the 7-day hard maximum, and the owner and approvers. The only number that comes from the sponsor is the default of 30 minutes.

**Cross-constraints.** `SESSION_LIFETIME_MIN ≥ 2 · MAX_QUOTE_TTL` (600 ≥ 2 · 300 holds on the proposals); `SESSION_LIFETIME_MIN ≤ SESSION_LIFETIME_DEFAULT ≤ SESSION_LIFETIME_MAX` (holds); informative: the default quote TTL of 120 s is at most one tenth of the default lifetime (holds).

**Evidence required to decide.** None exists. To be produced: usability tests with a phone wallet and a hardware wallet (time from the first screen to the signature), the distribution of signing times from the testnet alpha, and a Privacy and Security view on stale-link exposure.

**Tests.** None yet. The creation validation and the timer need unit tests; the rules ER-01 to ER-10 need state-machine tests (§13).

**Open points.** The three bounds are not approved (OPN-10). `MIN_SIGN_WINDOW` and `sigTtl` have no approved value (OPN-05).

**Approval block**

| Required approver | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|
| Payments PM | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | **NOT SIGNED** | — | — | — |
| Privacy Lead | **NOT SIGNED** | — | — | — |

## 7. Quote lifecycle

A **quote** is FastPay's proposal of the token amount that pays `amount` in `currency` on a chain and token, valid until `validUntil`. When a signed `PriceQuote` ([11 §4](11-dual-cap-model.md)) is needed, the quote record carries its `quoteHash`; when settlement is 1:1 the record is internal and the `quoteHash` of the intent is zero ([10 §2.1](10-pay-once-protocol.md)). Quotes are proposals, never trusted (TM-07): the chain verifies outcomes.

### 7.1 Rules

| ID | Rule |
|---|---|
| QL-01 | **Only one quote may be active for a given session revision.** A session revision is a value of `sessionVersion`. The service keeps at most one active quote per session; activating a new one supersedes the old one in the same write |
| QL-02 | **Creation and replacement.** A quote is created at TR-05 and replaced at TR-06. `validUntil = min(now + quote TTL, expiresAt)` and never more than `MAX_QUOTE_TTL`. A replaced quote is `superseded` and can never be used in a signing request |
| QL-03 | **Refresh.** The page refreshes the quote before showing a prompt if the remaining validity is shorter than `MIN_SIGN_WINDOW`, and when the customer asks. A refresh is a replacement; it never happens while a request is outstanding |
| QL-04 | **Expiry.** An expired quote cannot start TR-08. The session stays open and is re-quoted inside the same session (ER-06) |
| QL-05 | **Invalidation.** The active quote is invalidated, the plan is discarded and the session returns to `REVIEW_REQUIRED` (or `CONNECTING` for an account change) when any of these changes: the connected account, the chain, the token, the amount or fee (the fee controller moved), the merchant recipient, the mandate state, the account pin or mode, the token policy, or a registry version used by the quote (bounds version, signer set). While `AWAITING_SIGNATURE`, the request is withdrawn (TR-10) and a late signature for the old quote is discarded |
| QL-06 | A quote is bound to the revision in which it was issued: a signature obtained for a superseded or invalidated quote is never submitted, whatever its deadline |

### 7.2 What the review screen is

The review screen is generated from the **same typed-data object** that will be sent to the wallet (TM-05): what the customer reads is what the wallet is asked to sign. A test compares the two (§13).

### 7.3 Checks immediately before the signature

All ten run in TR-08, in the revision that will be signed. Chain facts are read from at least two independent sources (TM-06). The balance and the allowance are advisory: the contract is the enforcement (TM-02).

| # | Check | Source of truth | On failure |
|---|---|---|---|
| 1 | Token balance covers the gross amount | Chain | `INSUFFICIENT_BALANCE`; stay in `REVIEW_REQUIRED` |
| 2 | Allowance suits the chosen path (to Permit2 for PO-1, to the router for PO-2 or PO-6, none for PO-3 or PO-4) | Chain | The planner re-plans (PO-5 adds the approval step); `INSUFFICIENT_ALLOWANCE` if no path remains |
| 3 | Price: the quote is signed by an active signer set, inside the registry band and the TTL ceiling | `TokenPolicyRegistry`, `SignerSetRegistry` | New quote (QL-02) |
| 4 | Quote deadline: `now + MIN_SIGN_WINDOW ≤ quote.validUntil` and `≤ expiresAt` | Clock | New quote, or no new authorization (ER-01) |
| 5 | Merchant recipient equals the registry's current recipient, and the merchant is active | `MerchantRegistry` | `MERCHANT_DISABLED`, or a new quote ([10 §5](10-pay-once-protocol.md)) |
| 6 | Mandate state: for a `SUBSCRIPTION`, no existing mandate that the activation rules of [05](05-evm-authorization-decision-tree.md) and [12](12-router-lifecycle-and-migration.md) treat as conflicting; for a compatible mandate (OPN-01), active and not paused or revoked | `MandateManager` | Block, or fall back to Pay Once |
| 7 | Account pin and mode allow the flow | [17](17-account-compatibility-policy.md), `MandateManager` | `ACCOUNT_NOT_ELIGIBLE` |
| 8 | Chain: the provider's chain id equals `selectedChain`, which is in `allowedChains` and enabled | Provider and two RPC sources | `CHAIN_UNSUPPORTED`; ask for a switch |
| 9 | Token policy: status `SETTLEMENT` or `DIRECT_PAYMENT`, not a blocked token class (ASM-022), bytecode hash as registered | `TokenPolicyRegistry` | `TOKEN_DISABLED` |
| 10 | Registry versions: the bounds version, router registry version and signer set used by the quote are current or inside their grace | Registries | New quote |

## 8. Wallet-connection profile

**Every claim in this section about WalletConnect, EIP-1193, EIP-6963 or a wallet is `UNVERIFIED`** (§8.3). The requirements below are what FastPay demands of any connector. They are `SPECIFIED`; whether a given connector can meet them is what the wallet lab must show.

### 8.1 Connection classes (v1)

| Class | What it is | Used for | v1 | Wallet-lab coverage |
|---|---|---|---|---|
| Browser wallet | An extension in the browser that shows the checkout | Desktop with MetaMask or similar (§10.1) | specified | CORE tests; no test for discovery (GAP-01) |
| WalletConnect | A session between the hosted page and a wallet app on another device | Desktop with a phone wallet (§10.2) | specified, `UNVERIFIED` | WL-22, WL-23 |
| Mobile deep link | The checkout in a mobile browser opens the wallet app and returns | Mobile with a wallet app (§10.3) | specified, `UNVERIFIED` | WL-23 |
| Wallet in-app browser | The checkout is opened inside the wallet's own browser | Mobile (§10.4) | specified, `UNVERIFIED` | none (GAP-02) |
| Hardware wallet | A device behind one of the above | §10.5 | specified only where the host wallet supports it | WL-21 |

Out of v1: embedded and passkey wallets (CSD-06), and any custodial wallet operated by FastPay (CSD-04).

### 8.2 Requirements

| ID | Topic | Requirement |
|---|---|---|
| CP-01 | Browser extension discovery | The page lists the wallets it can discover and lets the customer choose. It never assumes there is exactly one wallet. Discovery uses the mechanism that the retrieved standard specifies; until then the only evidence is the lab (CSU-01) |
| CP-02 | No auto-connect | A connection starts only from a user gesture on this page. No connection is attempted on load, and no previously granted connection is used silently (UI-09 of [04](04-context-and-trust-boundaries.md) §6) |
| CP-03 | Pairing code | Code A (§9) shows a pairing code produced by the connector library. It is single-use, has its own lifetime (CSU-06), is refreshed when it expires, and is never reused across sessions |
| CP-04 | Mobile deep links | The page opens the wallet through the link the connector provides and shows the same pairing as a copyable fallback. It never assumes that a wallet is installed or that the return comes back to the same tab (CSU-07) |
| CP-05 | In-app browsers | When the page detects that it runs inside a wallet's browser, it uses the injected provider and does not show a pairing code. The same session and the same origin apply |
| CP-06 | Hardware wallets | A hardware wallet is reached through its host wallet. Consent does not rely on the device's own screen (WL-21, ASM-006, ASM-007). If the host wallet shows the typed data as opaque, Pay Once uses a transaction path (WL-27) |
| CP-07 | Reconnection | After a lost connection the page reconnects automatically for a short time, shows "reconnecting", then offers a new code A and the choice of another wallet. **Reconnecting never creates a new session and never re-sends a signing request** |
| CP-08 | Pairing expiry | An expired pairing returns the session to `OPEN` (TR-04) with a fresh code on request |
| CP-09 | Session expiry | A connector session that ends while the checkout session is `WALLET_CONNECTED` or `REVIEW_REQUIRED` is a disconnect (TR-07). While `AWAITING_SIGNATURE` it withdraws the request (TR-10). After a submission it changes nothing |
| CP-10 | Duplicate signing-request prevention | A request has an id: (session id, attempt id, step index, request kind). The server holds at most one outstanding request per session (PX-07). A page refresh or a second tab fetches the state and does **not** send the request again; it shows "check your wallet". "Send again" first withdraws the old request and issues a new attempt with a new nonce. The old signature, if the customer produced it, is discarded |
| CP-11 | Account change | A different account than `connectedWallet` withdraws the request and discards the quote, plan and signatures not yet used (TR-07, TR-10, QL-05). For `EXPECTED_WALLET`, a different account is `WALLET_MISMATCH` |
| CP-12 | Chain change | A chain other than `selectedChain` withdraws the request and discards the quote. The page asks for a switch and, if the wallet refuses, offers another chain among `allowedChains` |
| CP-13 | Wallet rejection | An explicit rejection is `USER_REJECTED`: the session returns to `REVIEW_REQUIRED`, shows a neutral message and does not re-prompt |
| CP-14 | Connection loss while a request is outstanding | Nothing is assumed. For a signature request, the request stays outstanding until its deadline. For a final-transaction request sent to the wallet (TR-12), the session stays `SUBMITTING` until a hash appears or reconciliation resolves it (`WALLET_RESULT_LOST`) |
| CP-15 | Mobile return failure | When the browser was killed during the wallet hop, the same URL restores the session from the server: state, quote, outstanding request. A request that is still outstanding is not duplicated (CP-10); one that is not is offered again by the customer's action |
| CP-16 | Browser refresh | As CP-15: the page is a view of the server state; no state lives only in the browser |
| CP-17 | Capability discovery | A capability that is absent, or a method that errors, is never read as "unsupported" (NC-02, WL-01); the planner falls back to the paths that do not need it |
| CP-18 | Self-reported wallet identity | The wallet's name, icon and version are what the wallet says about itself. They are shown for convenience, recorded in the audit, and never used to authorize anything or to claim compatibility |
| CP-19 | Typed data only | The page requests `eth_signTypedData_v4` of named-field structs. It never requests `eth_sign`, never `personal_sign` over an opaque hash, never an unlimited approval to a spender other than Permit2 (TM-05) |

### 8.3 `UNVERIFIED` claims register

None of these has been retrieved or tested. They are statements from general knowledge (E0). The WalletConnect specifications and EIP-1193 are on the "not yet retrieved" list of [02](02-source-register.md); EIP-6963 is not in the register at all.

| ID | Claim | Level | To close |
|---|---|---|---|
| CSU-01 | A browser can discover several installed wallets through a standard event mechanism (EIP-6963) | E0 | Retrieve and pin the standard; add a lab test (GAP-01) |
| CSU-02 | Injected providers expose `accountsChanged` and `chainChanged` events and a chain-switching request (EIP-1193 and related) | E0 | Retrieve and pin; WL-24 |
| CSU-03 | WalletConnect pairs a wallet with a page through a URI shown as a QR code or opened as a link | E0 | Retrieve and pin the specification; WL-22 |
| CSU-04 | A WalletConnect session carries `eth_signTypedData_v4`, `eth_sendTransaction` and `wallet_*` requests to the wallet, subject to the namespaces the wallet approves | E0 | Specification; WL-22 compares with the native connector |
| CSU-05 | A relay operated by a third party sits between the page and the wallet and sees connection metadata | E0 | Specification; Privacy review (OPN-08) |
| CSU-06 | Pairings and sessions have a lifetime and either side can end them | E0 | Specification; WL-23, GAP-04 |
| CSU-07 | Mobile wallets offer a URI scheme or a universal link to be opened from a browser, and the return to the browser is not guaranteed | E0 | WL-23 |
| CSU-08 | Wallets with an in-app browser inject a provider into the pages they open | E0 | GAP-02 |
| CSU-09 | A hardware wallet signs typed data only through a host wallet, possibly with blind signing | E0 | WL-21 |
| CSU-10 | A wallet may refuse to switch or add a chain | E0 | WL-24 |
| CSU-11 | Capabilities and supported methods can differ through WalletConnect from the native connector | E0 (already stated as a risk in [15 §2.1](15-wallet-lab-matrix.md)) | WL-22 |

## 9. Two distinct QR codes

The two codes serve different purposes. **Neither is a payment address. Neither is a deposit QR, and no identifier, label or copy in the product uses the words "deposit" or "payment address" for either** (CSD-05).

### 9.1 Code A — wallet pairing

| | |
|---|---|
| Label (exact) | **"Scan with your wallet"** |
| Purpose | Connect a mobile wallet to the checkout that is running on **another device** |
| Encodes | The pairing URI produced by the connector library (format `UNVERIFIED`, CSU-03). Not produced by FastPay's own encoder; contains no amount, no merchant, no session id |
| Lifetime | Single use; its own expiry (CSU-06); a new code on expiry or on request |
| Where it is scanned | In the wallet app's own scanner. The page says so: "Open your wallet app and scan this code. Do not scan it with a camera app that opens a website." |
| After scanning | The wallet shows who is asking and which chain; the customer approves; the page moves to `WALLET_CONNECTED` (TR-03) |

### 9.2 Code B — checkout continuation

| | |
|---|---|
| Label (exact) | **"Continue this checkout on your phone"** |
| Purpose | Open the **hosted checkout URL** on another device (CSD-07) |
| Encodes | `https://<checkout-origin>/c/<id>` and nothing else (CS-1): no pairing URI, no payment address, no amount, no signature, no secret |
| Lifetime | The life of the session |
| After scanning | The phone loads the same session (§9.3). It then follows §10.3 or §10.4 |

### 9.3 Two devices, one session

The session has **one controlling browser context** at a time, recorded as `controllerEpoch`.
- The first context that performs TR-02 takes control. Another context that opens the URL is a **viewer**: it shows the status and nothing else.
- A viewer takes control, and the old context becomes a viewer ("Continued on another device"), only while the status is `OPEN`, `CONNECTING`, `WALLET_CONNECTED` or `REVIEW_REQUIRED`, and never while a request is outstanding or after authorization. A takeover writes the audit event `lease.taken`.
- Holding the control lease allows cancelling the session from the page (TR-23). It does not allow spending.

Anyone who has the URL can take the lease in those four states. That is a nuisance, not a loss of funds (CS-4); it is recorded for Security review (SX-08).

## 10. Customer experiences

All experiences are `SPECIFIED` and `UNVERIFIED`: no wallet has been tested for any of them.

### 10.0 Common rules

**The review screen** shows: the merchant's name from `display`, the fiat `amount` and `currency`, the token amount and chain, the recipient (abbreviated, with the registry name), the expiry time, and what the signature authorizes:
- For a payment: "One payment of exactly this amount to this merchant." Nothing remains authorized afterwards (`I-PO-NOSTANDING`).
- For a `SUBSCRIPTION`: the standing authorization in the terms of the mandate (caps, cadence, end), with the consent copy of [05](05-evm-authorization-decision-tree.md) and the distinct wording that separates it from a one-off payment.

It also shows the **number of prompts and transactions** of the chosen path. It does not show the name of an internal path code, and it never says that a payment is "gasless" or "free" unless the planner's path guarantees it.

### 10.1 Desktop with a browser wallet

1. The page lists the discovered wallets (CP-01); the customer chooses the extension. `OPEN` → `CONNECTING`.
2. The extension asks to connect; on approval the page checks the chain and the payer policy (`WALLET_CONNECTED`), asks for a chain switch if needed.
3. Quote and plan (`REVIEW_REQUIRED`), the review screen, the pay button.
4. The planner's path runs: for example PO-1, one typed-data signature; or PO-5, an exact approval transaction and then the signature.
5. `AUTHORIZED`, `SUBMITTING`, `PROCESSING`, `COMPLETED`, then the redirect to `successUrl`.

Evidence: CORE, SIG sets of [15](15-wallet-lab-matrix.md); WL-16 or WL-27 for the display of the typed data.

### 10.2 Desktop with a wallet only on a phone

1. The customer chooses "Use a phone wallet". The page shows code A "Scan with your wallet" (`CONNECTING`).
2. The customer scans it in the wallet app, approves the connection and later each request **on the phone**. The desktop page follows the same session and shows "Check your phone".
3. If the customer would rather finish on the phone, the page offers code B (§9.2) and the flow continues as §10.3 or §10.4. The desktop becomes a viewer.
4. Nothing is installed on the desktop. If the pairing expires, the page shows a new code; if the connection drops, CP-07 applies.

Evidence: WL-22, WL-23; GAP-03 for the two-device lease.

### 10.3 Mobile with a wallet app

1. The checkout opens in the phone's browser. The customer chooses "Open my wallet" and the page opens the wallet through the connector's link (CP-04).
2. The wallet app asks to connect, then to sign. The customer returns to the browser.
3. If the browser was killed during the hop, the same URL restores the session (CP-15) and does not send the request twice (CP-10).
4. If no wallet opens, the page shows the copyable pairing and "Choose another wallet".

Evidence: WL-22, WL-23, WL-25.

### 10.4 Mobile wallet in-app browser

The customer opens the checkout URL inside the wallet's browser (by pasting it, or by scanning code B with the wallet's scanner). The page detects the injected provider and skips pairing (CP-05). From `CONNECTING` on, the flow is §10.1. The origin is the same hosted origin; the page makes the same security assertions (SX-01).

Evidence: GAP-02.

### 10.5 Hardware wallet

The customer connects a host wallet that fronts the device (CP-06) and the flow is §10.1 or §10.2. The device's own screen is not relied on for consent. If the host wallet or the device cannot sign the typed data, or shows it as opaque (WL-21), the planner uses a transaction path where one exists (WL-27); if none exists the page says so, and the customer may choose another wallet. A hardware wallet is mentioned in the product only where its row in the Compatibility Register is E3.

Evidence: WL-21, WL-27.

### 10.6 Customer without a wallet

FastPay v1 does not create a wallet and does not offer an on-ramp (CSD-04, non-goals of [06 §8](06-initial-architecture.md)). The page says plainly:

> "To pay with FastPay you need a crypto wallet. FastPay does not hold your money or create a wallet for you."

It then offers three things:
1. **Ways to get a wallet:** a short, neutral list of wallet apps with links that open the wallet's own site. The list is labelled "Examples. FastPay has not tested every wallet." It says nothing about support for a wallet that is not at E3 in the Compatibility Register ([15 §2.1](15-wallet-lab-matrix.md)). The links carry no FastPay identifier and the page loads nothing from them.
2. **Come back later:** copy the link or show code B. The session stays open until `expiresAt` (CSD-07). There is no email resume in v1 (CSD-08).
3. **Back to the merchant:** the customer chooses a reason or none (`NO_WALLET`, `WALLET_UNSUPPORTED`) and the session becomes `CANCELLED` (TR-23); the redirect goes to `cancelUrl`, so the merchant can offer another payment method.

### 10.7 Wallet with insufficient funds

The check of §7.3 (1) fails: the page shows the required and the available amount of the token (chain data), `INSUFFICIENT_BALANCE`, and the options:
- another allowed token or chain on which the balance suffices;
- add funds to the customer's own wallet, then "Check again";
- cancel.

The session keeps running until `expiresAt`. The pay button stays disabled. FastPay offers no purchase of tokens in v1.

### 10.8 Wallet with insufficient native gas

Gas is needed by the paths in which the customer sends a transaction (PO-2, PO-5, PO-6, an activation batch or approval). PO-1 needs no customer gas for the payment itself, because the executor submits it ([10 §2.2](10-pay-once-protocol.md)). Who bears the executor's gas and how it is recovered is stated for recurring charges (ASM-012) and is not specified for Pay Once (OPN-07).

If the only eligible path needs gas and the estimate (advisory) exceeds the native balance, the session stays in `REVIEW_REQUIRED` with `INSUFFICIENT_NATIVE_GAS` and the options: add native token to the wallet, choose another chain or token, cancel. **No gas sponsorship is specified or implied** (ASM-018; OPN-07).

### 10.9 Returning customer with a compatible active mandate

*What the product wants to do:* recognise a customer who already has a FastPay mandate with this merchant and offer "use your existing authorization" without a new allowance prompt.

*What the specification allows today:* **nothing.** The connected address is only a claim until a signature proves control (§4). A charge under an existing mandate needs no signature from the customer today, so a person who types a victim's address into a checkout could cause a charge of the victim's mandate for the attacker's order. It also would consume the caps of a recurring mandate for a one-off payment. Three things are missing: proof of control bound to the session, a typed confirmation, and a mandate term that allows an ad hoc charge (OPN-01; findings F-19 of the implementation report).

*What the product does in v1:* the page may show, from a public chain read, that a mandate exists ("You already have a FastPay authorization with this merchant. Manage it in your portal."). It does not offer to use it. A `PAYMENT` is a Pay Once payment (§3.1). A `SUBSCRIPTION` is activated as a new mandate; whether a second mandate for the same merchant is accepted is decided by the activation rules of [05](05-evm-authorization-decision-tree.md) and [12](12-router-lifecycle-and-migration.md), which this document does not restate, and the page shows the existing mandate before it asks for a new one.

### 10.10 Unattended recurring charge

This is **not a checkout session.** The executor charges under the mandate with no customer present, subject to the caps, the account pin and the revalidation of [13](13-eip7702-delegation-inspection.md) and [17](17-account-compatibility-policy.md). No session is created and no page is shown.

The customer sees the charges in the mandate portal and on chain, and can revoke, pause or reduce at any time (TM-14); exits are never gated. **How a customer is told of a charge or of a failed charge is not specified** (v1 collects no customer email, CSD-08; OPN-06). A failed charge is dealt with by the merchant, who may send the customer to a new checkout session. The typed charge request of an unattended charge is itself not specified (F-19, OPN-01).

### 10.11 Interrupted activation

For a `SUBSCRIPTION`, the customer closes the browser or loses the connection during the activation:

| Where it stopped | What happens |
|---|---|
| Before any signature (`CONNECTING` to `REVIEW_REQUIRED`) | The session continues until `expiresAt`; the customer reopens the URL or scans code B and resumes (CP-15, CP-16) |
| Signatures held, executor not yet claimed (`AUTHORIZED`) | The executor submits if the deadlines allow (TR-11); otherwise TR-24. The customer need not return |
| Final request sent to the customer's wallet, no result seen (`SUBMITTING`) | The session stays `SUBMITTING`; reconciliation looks for the activation of the mandate by the deterministic creation nonce of the session; a hash or the event moves it to `PROCESSING`, no evidence until the deadline moves it to `UNKNOWN` and then to a proven outcome (CP-14) |
| Hash recorded (`PROCESSING`) | Nothing the customer does matters; the session is resolved by chain state (ER-09) |

The mandate and the creation nonce must be derivable from the session so that reconciliation can find the activation; that derivation is not yet specified (OPN-12).

### 10.12 Rejected signature

The customer rejects the prompt: `USER_REJECTED`, TR-10, the session returns to `REVIEW_REQUIRED` with a neutral message ("You did not sign. Nothing was sent. Pay when you are ready."). FastPay does not re-prompt. Each press of the pay button is a new attempt with a new nonce (§5.5).

### 10.13 Account or chain changed during checkout

| Change | Before `AWAITING_SIGNATURE` | During `AWAITING_SIGNATURE` | After `AUTHORIZED` |
|---|---|---|---|
| Different account (`ANY_WALLET`) | `CONNECTING`, discard quote and plan (TR-07, QL-05) | Withdraw the request, discard signatures not used, `REVIEW_REQUIRED` for the new account after a new connection (TR-10, TR-07) | No effect: the payer is fixed |
| Different account (`EXPECTED_WALLET`) | `WALLET_MISMATCH`, wallet disconnected, `OPEN` | As above, then the same | No effect |
| Different chain | Ask for a switch; quote discarded | Withdraw the request, discard the quote (QL-05) | No effect |

No authorization obtained for the old account or chain is ever submitted (WL-24: "the plan is re-made from chain state; no stale authorization is submitted").

## 11. Merchant integration

The API names, paths and field spellings below are proposals and are not frozen.

### 11.1 Flow

1. The merchant's server creates a session (§11.2) with its API key.
2. The merchant sends the customer to the returned `url` (redirect), or mounts embedded checkout with the `client_secret` (separately gated, §11.5).
3. The customer pays on the FastPay page.
4. FastPay delivers webhooks (§11.6).
5. The customer is sent to `successUrl` or `cancelUrl`. **The merchant confirms the payment from the webhook or from the API, never from the redirect.**

### 11.2 Create a session

`POST /v1/checkout/sessions`, authenticated by a scoped, hashed, rotatable API key (OD-014, TB-03), with an idempotency key. The body carries the fields 3 to 12, 16, 28 and 29 of §2.1 and a lifetime within the bounds of CSR-01 (default 30 minutes). `merchantId` and `liveMode` come from the key.

The response carries `id`, `url`, `expiresAt`, `status` (`OPEN`) and, for embedded checkout, a `client_secret`. A merchant reads a session with `GET /v1/checkout/sessions/{id}` (API key; includes `metadata`), and may cancel one that is not yet submitted with `POST .../cancel` (TR-23, `cancelReason = MERCHANT`).

### 11.3 Redirect checkout

The merchant redirects (HTTP 303) to `url`. The hosted page is served from a dedicated origin that no merchant script ever runs in (SX-01). The page works for a customer who arrives from a link, a QR code (code B) or an email the merchant sent.

### 11.4 Success and cancellation URLs

- **Validation.** Both URLs must be HTTPS (test mode: `http` on `localhost` only), must carry no credentials, and must belong to a domain registered by the merchant. A URL outside the registered domains is rejected at creation. This closes the open-redirect risk of a hosted page that redirects to a URL given in a request.
- **Content.** The redirect adds only `session_id` (a `{CHECKOUT_SESSION_ID}` placeholder in the merchant's template). It never adds an amount, a status, a payer, a hash or a signature.
- **Meaning.** Reaching `successUrl` means the customer saw a completed page. **It is not proof of payment**; a person can type the URL. The merchant fulfils on `checkout.session.completed` or after reading the session.
- **`cancelUrl`.** Reached when the customer leaves before a submission (TR-23) or on `EXPIRED`. It does not mean the customer did not pay: a customer may leave while the session is `PROCESSING`, in which case the page says so and sends them to `successUrl` or shows progress.

### 11.5 Embedded Checkout and Payment Links, separately gated

Both reuse the session of this document unchanged (CSD-10). Neither is part of the first implementation (CSD-09).

| | Embedded Checkout (S02) | Payment Links (S03) |
|---|---|---|
| What it is | The same page in an iframe on the merchant's page, driven by a `client_secret`, with a `postMessage` interface | A long-lived merchant link that **creates a new session per visit** |
| Extra gate | Hardening of the iframe and `postMessage` ([06 §2.1](06-initial-architecture.md)); clickjacking review; whether a wallet extension can reach a cross-origin frame (`UNVERIFIED`, not tested); a separate review of the origin and CSP | Link-level controls (expiry, quantity, a per-link cap); abuse and spam review; the lifetime of a link is not the lifetime of a session |
| `client_secret` | A secret scoped to one session, expiring no later than it, never in a URL, never spending authority | Not used |
| What it must not do | Change a state, a guard or a deadline; expose `metadata` to the frame | Reuse one session for several payments |

### 11.6 Webhook delivery

Signed events, at least once, as in TB-12 and PB-021:
- the payload is signed with an HMAC and carries a timestamp; the merchant rejects an old timestamp (replay window);
- each event has a unique id; a merchant deduplicates by it;
- retries use backoff; an endpoint with repeated failures trips a circuit breaker and events go to a dead letter that the dashboard shows;
- delivery goes through the egress proxy with the deny-list of internal ranges (SSRF);
- the secret is rotatable per endpoint, with an overlap period;
- **ordering is not guaranteed.** Each event carries `sessionVersion`. The merchant applies an event only if its `sessionVersion` is higher than the last one applied for the session, and treats `completed`, `failed`, `expired` and `cancelled` as final;
- test and live endpoints are separate (`liveMode`).

## 12. Security and privacy requirements

### 12.1 Security

| ID | Requirement |
|---|---|
| SX-01 | The hosted checkout is served from its own origin with a strict CSP, SRI, no third-party scripts, `frame-ancestors 'none'` (the embedded checkout has its own policy, §11.5), and no merchant code (TB-02, PB-022) |
| SX-02 | The wallet-connection library is a pinned, bundled dependency under the supply-chain controls of PB-024. It is not loaded from a third-party host at checkout. The relay it talks to is a third-party **service**, not a script (OPN-08) |
| SX-03 | The review screen and the typed data come from the same object, and a test compares them (§7.2) |
| SX-04 | A signature held for submission is stored encrypted, bound to its session and attempt, and deleted once the session is terminal and the retention period has passed. It is never logged, and an audit record holds only its hash |
| SX-05 | `successUrl` and `cancelUrl` are validated against the merchant's registered domains (§11.4) |
| SX-06 | Webhook egress follows TB-12 and PB-021 (§11.6) |
| SX-07 | The session `id` is never a credential (§2.2); the `client_secret` and the API key are separate secrets with their own scopes |
| SX-08 | Control of the session is a lease with the rules of §9.3. Taking it is evented and rate-limited; the nuisance of a takeover by a person who holds the URL is accepted and reviewed |
| SX-09 | Browser-side session data is limited to the URL and the connector's own storage. FastPay stores no address, token, signature or secret in the browser |
| SX-10 | No component, console or API can create or widen a customer's spending authority (TM-01, TB-14). The checkout service requests signatures; it cannot sign for a customer |
| SX-11 | Every failure is closed: ambiguity in authorization, quote validity, finality or transaction status creates no new payment (TM-11) |

### 12.2 Privacy

The wallet address is treated as personal data (ASM-023).

| Data | Personal | Who sees it | Retention |
|---|---|---|---|
| `connectedWallet` and the payer in events | Yes | The session's merchant (in events), FastPay operations | Not set here; to be set by the Privacy Lead |
| `metadata`, `clientReferenceId` | Merchant's own; may link to a person | Merchant | As the merchant's contract says; never shown to the customer |
| Network data of the page (IP, user agent) | Yes | FastPay security logs | Not set here |
| Signature (held until submitted) | Bearer until its deadline | The executor service | SX-04 |
| Transaction hash, token, amount, chain | Public chain data | Anyone | Chain |
| Pairing metadata at the relay | Yes (`UNVERIFIED`) | The relay operator | Unknown; OPN-08 |

**Excluded from v1:** collecting the customer's name, email, phone or postal address; any join of sessions across merchants; any profile built from a wallet address; any analytics that identifies a wallet across sessions (§4). **Needs Privacy review before any release:** the relay (CSU-05), the logs, the exposure of an expected address (abbreviated, §4), the leakage through code B, and every retention period.

## 13. Evidence and status

### 13.1 What exists

This document adds **no** evidence. What exists is unchanged:

| Class | Status for the subject of this document |
|---|---|
| Reference model | No checkout session |
| FastPay contracts | `payOnceWithSignature` (PO-1, with PO-5's customer transaction before it), `markSettled`, the router and registries are built and tested ([REPORT.md](evidence/implementation/REPORT.md) §0a). PO-2, PO-3, PO-4, PO-6, `chargeInitial` and a typed charge request are not built |
| Permit2 rebuild and forks | The `SignatureTransfer` witness path passes on three chains |
| Wallet lab | **Nothing for this profile.** No run record exists for any wallet |
| Session service, connection layer, API, webhooks | Not specified in code; not built |

### 13.2 Wallet-lab coverage and gaps

| Subject | Existing tests of [15](15-wallet-lab-matrix.md) | Gap |
|---|---|---|
| WalletConnect session | WL-22 (repeat WL-02, WL-04, WL-16 through WalletConnect) | none beyond running it |
| Mobile hand-off and return | WL-23 | GAP-04: pairing and session expiry, reconnection |
| Account or network switch | WL-24 | — |
| Rejection and timeout | WL-25 | — |
| Hardware | WL-21 | — |
| Pay Once witness display, alternates | WL-27, WL-28 | — |
| Mandate typed-data display | WL-16 | — |
| Browser extension discovery with several wallets | none | **GAP-01** |
| Wallet in-app browser | none | **GAP-02** |
| Checkout continuation (code B) and the two-device lease | none | **GAP-03** |
| Pairing expiry and reconnection of a connector session | none | **GAP-04** |
| Insufficient native gas on a path that needs customer gas | none | **GAP-05** |
| Duplicate-request prevention across a refresh with a request still in the wallet | WL-23 partly | **GAP-06** |
| Loss of the result of a customer-sent final transaction | WL-28 covers path support only | **GAP-07** |
| Existing mandate used for a payment | none | **GAP-08** (blocked by OPN-01) |

**The gaps.** Each is a test that does not exist and that this profile needs.

| ID | What is not covered | What a test would have to show |
|---|---|---|
| GAP-01 | Several wallets installed in one browser | The page lists each discoverable wallet, uses the one the customer chose, and never picks one silently (CP-01) |
| GAP-02 | A wallet's in-app browser | The injected provider is used, no pairing code is shown, and the same session works (CP-05) |
| GAP-03 | Code B and the two-device control lease | The phone takes control, the desktop becomes a viewer, and no signing request is duplicated (§9.3, CP-10) |
| GAP-04 | Pairing expiry, connector-session expiry and reconnection | CP-07 to CP-09 hold: no new session, no re-sent request, a fresh code on request |
| GAP-05 | Insufficient native gas on a path that needs customer gas | The blocker is shown and no prompt is sent that the customer cannot pay (§10.8) |
| GAP-06 | A page refresh or a second tab while a request is still in the wallet | No second prompt (CP-10, CP-16) |
| GAP-07 | The result of a customer-sent final transaction is lost | The session stays `SUBMITTING`, then reaches `PROCESSING` or `UNKNOWN` and is resolved by chain state (TR-12, TR-15, CP-14) |
| GAP-08 | An existing mandate used for a payment | Blocked by OPN-01; nothing to test until it is decided |

These are **proposed additions to [15](15-wallet-lab-matrix.md)**. They are not made: they would extend the required lab evidence of [16](16-freeze-decision-report.md) §9, which is a decision for the QA Lead and the Principal Architect.

### 13.3 Tests this specification requires (none exist)

State-machine tests for every transition of §5.2 and every prohibition of §5.3; a replay test for each idempotency rule; a clock test for ER-01 to ER-10; a cross-chain exclusivity test for PX-08; a test that the review screen equals the typed data (SX-03); a test that no URL carries data beyond the session id (CS-1); an open-redirect test on the URLs; a webhook ordering and replay test. They are listed, not written, and no run result is recorded.

### 13.4 Reviews and sign-offs

| Review | Required by | State |
|---|---|---|
| Security review of the session, the lease, the webhook and the connection layer | Head of Security | **NOT SIGNED** |
| Privacy review of §12.2 and CSD-08 | Privacy Lead | **NOT SIGNED** |
| Wallet-lab evidence for §8 | QA Lead | **none** |
| Source retrieval for CSU-01 to CSU-11 | Wallet Protocol Engineer | **not done** |
| Approval of CSR-01 | Payments PM, CISO, Privacy Lead | **NOT SIGNED** |

## 14. Conflicts and open points

| ID | Point | Why it matters | Owner |
|---|---|---|---|
| OPN-01 | **Using an existing mandate for a `PAYMENT`.** No typed confirmation or charge request exists (F-19), no mandate term allows an ad hoc charge, and proof of control is missing. Without all three, an unproved address could trigger a charge of a victim's mandate | Blocks §10.9 and GAP-08. If enabled later it changes `eip712/types.json` and the fingerprint of C-11 | Principal Architect, Wallet Protocol Engineer |
| OPN-02 | **State names across documents.** [10 §4](10-pay-once-protocol.md) maps a user rejection to `CANCELLED`; [06 §3.2](06-initial-architecture.md) lists intent `CANCELLED` and has no `EXPIRED` or `FAILED` intent state; its full tables (C.8) do not exist | The session states of §5.1 are the only complete model | Principal Architect |
| OPN-03 | **Two sessions for one order.** `markSettled` is per `paymentId` and per chain; a merchant that creates two sessions for the same `clientReferenceId` can be paid twice. The session prevents it only inside one session (PX-08) | Merchant-level uniqueness of `clientReferenceId` is not specified | Merchant PM, Payments Core lead |
| OPN-04 | **Control lease takeover** by a person who holds the URL (SX-08) | Griefing, not theft | Head of Security |
| OPN-05 | **No value** for `MIN_SIGN_WINDOW`, `sigTtl` of a payment, or the attempt limit per session ([10 §9](10-pay-once-protocol.md) point 3) | The guards of TR-08 and §5.5 need them; each would be a constant needing its own record | Product Designer |
| OPN-06 | **Telling a customer about a charge or a failed charge** when v1 collects no email | §10.10 | Product, Privacy Lead |
| OPN-07 | **Gas sponsorship** for customers without native gas (ASM-018) | §10.8 | Payments PM, Finance |
| OPN-08 | **Who operates the relay**, what it sees, and whether FastPay runs its own (UI-09 asks for its own project id) | Privacy and availability | Head of Security, Privacy Lead |
| OPN-09 | **Retention periods** of sessions, logs, held signatures | §12.2 | Privacy Lead |
| OPN-10 | **Approval of the three bounds** of CSR-01 | §6.4 | Payments PM, CISO, Privacy Lead |
| OPN-11 | **`SETUP` mode** (reserved): what it is for (a fix-payment page after a failed charge, a mandate update) and whether it is a session or something else | §3 | Product |
| OPN-12 | **Deterministic ids from the session** (`paymentId`, the activation's creation nonce) so that reconciliation can find a transaction whose result was lost | §10.11, CP-14 | Solidity Lead, Payments Core lead |
| OPN-13 | **Cross-chain choice.** A session that allows several chains lets the customer choose one; PX-08 forbids a second chain after a submission. Whether a multi-chain session is offered in v1 at all is a product decision | §2.1 | Merchant PM |

## 15. What this document leaves unchanged

| Item | State |
|---|---|
| Protocol freeze | **Not approved**; `python -I tools/freeze_readiness.py` prints its own result and this document changes none of its inputs |
| Documents 05, 06, 10, 11, 12, 13, 14, 15, 16, 17, 18 | Not edited. Documents 01 (table of contents), README and CHANGELOG list this document |
| Configuration register | PC-01 to PC-19 only; CSR-01 is outside it |
| Contracts, tests, evidence, fingerprints | Not touched |
| `eip712/types.json` | Not touched; OPN-01 is the only point that could change it |
| Wallet-lab evidence | None |

If the sponsor accepts this proposal, the next steps are those of §13.4 (Security and Privacy review, source retrieval for CSU-01 to CSU-11, a decision on GAP-01 to GAP-08) and the closing of OPN-01. None of them is scheduled here.
