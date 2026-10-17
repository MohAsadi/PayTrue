# 19 — Checkout Session and Wallet-Connection Profile

| Field | Value |
|---|---|
| Artifact | FP-PRD-004 (new) |
| Version | 0.2.0 (revises 0.1.0, which was written from a text of the instruction that ended inside section 10) |
| Date | 2026-10-17 |
| Status | **PROPOSED. NOT PROTOCOL-FROZEN. REQUIRES SECURITY REVIEW. REQUIRES PRIVACY REVIEW. REQUIRES WALLET-LAB EVIDENCE.** A product and integration specification, **not protocol evidence.** Nothing here is implemented, tested on a wallet, reviewed or approved. It does not approve protocol freeze (RG-016 stays not approved, [16](16-freeze-decision-report.md)), alters no contract evidence, approves no configuration constant and changes no condition of `freeze_readiness.py` |
| Owner | Principal Product Manager (product decisions, session model), Wallet Protocol Engineer (connection profile) |
| Reviewers | Head of Security (required), Privacy Lead (required), Frontend / SDK Lead, Product Designer, QA Lead, Payments Core lead (sessions, webhooks), Merchant PM |
| Dependencies | [02](02-source-register.md) (the WalletConnect, EIP-1193 and EIP-6963 sources are **not retrieved**); [03](03-assumptions-decisions-risks.md) ASM-014, ASM-018, ASM-023, ASM-037…041, OD-013, OD-014, OD-022, OD-038…044, RISK-038…044; [04](04-context-and-trust-boundaries.md) TM-01, TM-02, TM-05, TM-06, TM-09, TM-11, TB-02, TB-03, TB-06, TB-12; [05](05-evm-authorization-decision-tree.md); [06](06-initial-architecture.md) §2.1 and §3.2; [08](08-production-blockers-and-release-gates.md) PB-021, PB-022, PB-024; [10](10-pay-once-protocol.md); [11](11-dual-cap-model.md) §4; [13](13-eip7702-delegation-inspection.md); [15](15-wallet-lab-matrix.md); [17](17-account-compatibility-policy.md); the proposed catalogs [checkout/api-catalog.md](checkout/api-catalog.md), [checkout/event-catalog.md](checkout/event-catalog.md) and [checkout/config-records.md](checkout/config-records.md) |
| Labels | `SECURITY-CRITICAL` `PRIVACY-CRITICAL` |
| Definition of Done | Every state transition has an identifier, a guard and an audit event, and every prohibited transition is listed; the session object, the connection profile, the API and the events are reviewed by Security and Privacy; every claim about WalletConnect or a wallet has moved from `UNVERIFIED` to a retrieved and pinned source and a wallet-lab run record; the configuration record CSR-01 is approved or replaced by its approvers; the acceptance criteria of section 20 pass; the open points of section 23 are closed or carried as recorded risks; nothing here contradicts documents 04, 06, 10, 11, 12 or 17 |

## 0. Scope, provenance and what this document does not do

**What it is.** The answer to one product question: *must an end customer install a wallet on the device that shows the checkout, or can FastPay work like a hosted checkout page?* It specifies the hosted, self-custody checkout, the `CheckoutSession` object and its state machine, the expiry rules, the quote lifecycle, the wallet-connection profile, the two QR codes, the customer experiences, the merchant integration, the redirect rules, the webhooks, the recovery rules, the security and privacy requirements and the acceptance criteria.

**Provenance.** Sections 1 to 21 follow the 21 sections of the sponsor's instruction of 2026-10-17, in their order. Version 0.1.0 of this document (commit `939dc9b`) was written from a copy of that instruction that ended in the middle of section 10 and added sections of its own; this version replaces it. Sections 22 and 23 (evidence and open points) are the author's. Where this document restricts something more than the instruction does, it says so and records the point in section 23.

**Evidence vocabulary.** `SPECIFIED` is a design position of this document, changeable by review. `UNVERIFIED` is any claim about a wallet, a wallet protocol or a third-party standard: it is E0 ([01](01-toc.md) evidence levels) until the official text is retrieved and pinned and a wallet-lab run record exists (E3). No wallet is called "supported" because of this document ([15 §2.1](15-wallet-lab-matrix.md)). Every value in a proposed API or event is a proposal.

**Identifiers local to this document** (new families, never reused): `CSD-` product decisions, `TR-` transitions, `PX-` prohibited transitions, `ER-` expiry rules, `QL-` quote-lifecycle rules, `CP-` connection-profile requirements, `CSU-` unverified claims, `FE-` evidence of failure, `UE-` causes of uncertainty, `MI-` merchant-integration requirements, `RD-` redirect rules, `WH-` webhook rules, `RC-` recovery rules, `SX-` security and privacy requirements, `AC-` acceptance criteria, `GAP-` wallet-lab gaps, `OPN-` open points, `CSR-` configuration record.

**What this document does not do.**

| It does not | Where that is kept |
|---|---|
| Approve protocol freeze, or change `freeze_readiness.py` or its result | [16](16-freeze-decision-report.md) |
| Alter any contract, test, mutation, fork, Permit2 or wallet-lab evidence, or any freeze fingerprint | [REPORT.md](evidence/implementation/REPORT.md), [14](14-protocol-freeze-pack.md) |
| Approve or add a production-blocking constant. CSR-01 is **not** a PC record (it is backend configuration, [18](18-configuration-records.md) R-9) and is not counted by condition C-4 | [checkout/config-records.md](checkout/config-records.md) |
| Define, implement or allow a per-invoice deposit address | CSD-05, section 13 |
| Put an embedded or passkey wallet in v1 | CSD-06 |
| Claim that WalletConnect, any browser wallet or any mobile wallet works | §8.3, §22 |
| Define a typed charge request or a customer confirmation for an existing mandate | OPN-01 |
| Edit documents 05, 06, 10, 11, 12, 15, 16, 17 or 18 | — |

## 1. Product decision

The decisions below were given by the sponsor in the conversation of 2026-10-17. They are recorded here, and in [03](03-assumptions-decisions-risks.md) as OD-038 to OD-044, as **proposed product decisions**. They are **not** approvals and not protocol evidence, and they close no open decision of [16](16-freeze-decision-report.md).

| ID | Decision |
|---|---|
| CSD-01 | **FastPay v1 uses a hosted, self-custody checkout.** FastPay hosts the checkout page. The customer's funds stay in the customer's own wallet until the router moves them to the merchant in one transaction; FastPay holds nothing in between (`I-ZEROBAL`, [10 §2.2](10-pay-once-protocol.md)) |
| CSD-02 | **A wallet is required, and it does not need to be installed on the device that shows the checkout.** The wallet may be a browser extension on the same computer, an app on a phone connected to a checkout on a computer, an app on the same phone, a wallet's in-app browser, or a hardware wallet behind one of those |
| CSD-03 | **Supported v1 connection classes:** browser wallets, WalletConnect, mobile deep links, wallet in-app browsers, and supported hardware-wallet paths (§8.1). All of them are `UNVERIFIED` until the wallet lab says otherwise |
| CSD-04 | **FastPay does not create, derive, recover, store or control customer keys.** No seed phrase, private key, keystore or recovery secret is requested, received, generated or held by any FastPay component. There is no "FastPay wallet" (TM-01, TM-05) |
| CSD-05 | **Per-invoice deposit addresses are excluded from v1** (section 13) |
| CSD-06 | **Embedded and passkey wallets are deferred** to v2 or a separately approved product track. Nothing in v1 (data model, SDK, copy, planner input) may assume one |
| CSD-07 | **Resume by checkout URL and by checkout QR is included in v1** (§9, code B) |
| CSD-08 | **Resume by email is excluded from v1** pending Privacy review. OD-013 allows an optional, consented, minimal-retention email in principle; v1 collects no customer email |
| CSD-09 | **Hosted Checkout (S01) is the first implementation** ([06 §2.1](06-initial-architecture.md)) |
| CSD-10 | **Embedded Checkout (S02) and Payment Links (S03) reuse the same session model** and are separately gated (§14.6). Neither may change the meaning of a state, a guard or a deadline defined here |
| CSD-11 | **The proposed default session lifetime is 30 minutes.** The minimum and maximum are proposals only and are not approved (CSR-01) |

**Consistency with what exists.** S01, S02, S03 and S15 are surfaces of v1.0 in [06 §2.1](06-initial-architecture.md). ASM-014: merchants integrate through hosted or embedded checkout and REST APIs and never handle customer keys or raw customer authorizations. TB-02: the browser reaches the FastPay API with a session bound to the origin, a strict CSP, SRI and no third-party scripts in checkout. TM-05: the page may only request signatures of typed, named-field data. The non-goals of [06 §8](06-initial-architecture.md) already list custodial wallets and fiat on-ramps; CSD-05 adds deposit addresses to them by decision, not yet by edit.

## 2. The `CheckoutSession` object

`CheckoutSession` is the customer-facing envelope of one payment or one mandate activation. It wraps an **intent** and its **attempts** ([06 §3.2](06-initial-architecture.md)): the session is what the customer and the merchant see, the attempt is one try to move money. The names below are the canonical model; the API writes them in `snake_case` and timestamps as RFC 3339 UTC strings ([checkout/api-catalog.md](checkout/api-catalog.md)). Names are proposals and not frozen.

### 2.1 Fields

Rows 1 to 27 are the 27 fields of the instruction. Rows 28 to 31 **add six fields** (`display`, `mandateTerms`, `authorizationPath`, `attemptId`, `controllerEpoch`, `cancelReason`) because a rule below needs them.

| # | Field | Type | Null | Set when | Mutable | Notes |
|---|---|---|---|---|---|---|
| 1 | `id` | string | no | creation | never | `cs_` followed by the unpadded base32 of at least 128 bits from a CSPRNG. Reveals no merchant, order, amount or time. **Never authentication and never spending authority** (§2.2) |
| 2 | `merchantId` | string | no | creation | never | The `merchantId` of the registry ([10 §2.1](10-pay-once-protocol.md)); taken from the API key, never from the request body |
| 3 | `clientReferenceId` | string | no | creation | never | The merchant's own reference (order number). Opaque to FastPay; never used as an on-chain value except through the hashed `paymentId` |
| 4 | `mode` | enum | no | creation | never | `PAYMENT`, `SUBSCRIPTION` or `SETUP` (§3) |
| 5 | `amount` | integer | no | creation | never | In minor units of `currency` (ADR-011). For `PAYMENT`: the amount to pay. For `SUBSCRIPTION`: the amount of an initial charge, 0 if none (§3.3) |
| 6 | `currency` | string | no | creation | never | ISO 4217 code accepted by `TokenPolicyRegistry`. It is the invoice currency a mandate pins (ADR-020) |
| 7 | `allowedChains` | list of chain ids | no | creation | never | Non-empty subset of the enabled chains. The test mode accepts testnets only, the live mode mainnets only |
| 8 | `allowedTokens` | list of (chain id, token address) | no | creation | never | Each token must have status `SETTLEMENT` or `DIRECT_PAYMENT` ([10 §2.2](10-pay-once-protocol.md)) on its chain. A request that omits the list gets the merchant's default list, copied in at creation; the stored list is never empty |
| 9 | `expectedCustomerWallet` | address | yes | creation | never | Required for `EXPECTED_WALLET`, must be null for `ANY_WALLET` (§4). **Never returned to the customer's browser** (SX-06) |
| 10 | `payerPolicy` | enum | no | creation | never | `ANY_WALLET` or `EXPECTED_WALLET` |
| 11 | `successUrl` | URL | no | creation | never | Validated against the merchant's registered domains (§14.3, RD-01) |
| 12 | `cancelUrl` | URL | no | creation | never | As above |
| 13 | `status` | enum | no | creation | by transition only | The 13 states of §5.1 |
| 14 | `createdAt` | unix seconds, UTC | no | creation | never | Server clock |
| 15 | `expiresAt` | unix seconds, UTC | no | creation | never | `createdAt` plus the lifetime; within the bounds of CSR-01 (§6) |
| 16 | `metadata` | map of strings | no (may be empty) | creation | never | **Merchant-private.** Never shown to the customer, never in a URL, never in typed data, never on chain. Returned to the merchant in the API and in webhooks. Limits: §14.2 |
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
| 30 | `authorizationPath` | string | yes | `REVIEW_REQUIRED` | until `AWAITING_SIGNATURE` | The path code chosen by the planner (§10.0) |
| 31 | `attemptId`, `controllerEpoch`, `cancelReason` | string, unsigned integer, enum | yes | see notes | — | `attemptId`: the current attempt. `controllerEpoch`: counts the browser contexts that have controlled the session (§9.3, SX-09). `cancelReason`: a stable code (§12) |

### 2.2 The session identifier and the checkout URL

- **CS-1 Public URL.** The hosted URL is `https://<checkout-origin>/c/<id>` and carries nothing else: no amount, no merchant, no order, no wallet address, no email, no token, no signature, no pairing URI, no secret. Everything the page shows is fetched by `id` from the API.
- **CS-2 Entropy.** `id` has at least 128 bits from a CSPRNG and is not derived from any other field. It is not sequential and not guessable; lookups of an unknown `id` return the same response as an expired one and are rate-limited (TB-02).
- **CS-3 Not authentication.** Possession of `id` identifies a session. It does not authenticate a customer, a merchant or a wallet.
- **CS-4 Not spending authority.** `id` cannot move funds, change a session field, read `metadata`, cancel through the merchant API, or create a signature. Only a signature by the payer's account can authorize a payment (TM-01).
- **CS-5 What `id` does allow.** Reading the customer-visible part of the session (`display`, amount, currency, expiry, status) and trying to pay it. A person who obtains the URL can therefore open the page and, under `ANY_WALLET`, pay it from their own wallet. That is accepted (§4).
- **CS-6 Secrets are separate.** Hosted Checkout needs no `client_secret` in the merchant's browser (§14.4). An embedded flow, if approved, uses a separate secret; it is never put in the hosted URL.
- **CS-7 Referrer.** The hosted page sets `Referrer-Policy: no-referrer`, so that the URL does not reach the merchant's or a third party's logs through a link on the page.

### 2.3 Initial vocabularies

These are the starting values for `failureCode` and `unknownReason`, written as the API writes them. They are proposals to be fixed with the API. The classes `FE-n` and `UE-n` are defined in section 17.

| `failure_code` | Evidence | Effect on the session |
|---|---|---|
| `user_rejected` | FE-1 | A new attempt may follow (§5.5) |
| `insufficient_balance`, `insufficient_allowance`, `insufficient_native_gas`, `quote_expired`, `deadline_passed`, `account_not_eligible`, `wallet_mismatch`, `signature_invalid`, `account_changed`, `token_disabled`, `chain_unsupported` | FE-2 | A new attempt may follow, with the fix or another wallet, token or chain |
| `simulation_reverted` | FE-3 | A new attempt may follow |
| `no_eligible_route`, `merchant_disabled`, `attempt_limit_reached` | FE-2 | **Ends the session** (`FAILED`, TR-21) |
| `reverted_on_chain` | FE-4 | **Ends the session** (`FAILED`, TR-17) |
| `not_executed` | FE-5 | **Ends the session** (`FAILED`, TR-17 or TR-20) |

`unknown_reason`: `broadcast_uncertain` and `wallet_result_lost` (UE-1), `rpc_timeout_after_submission` (UE-2), `rpc_disagreement` (UE-3), `receipt_unavailable` (UE-4), `reorg_uncertain` (UE-5), `finality_uncertain` (UE-6), `indexer_lag` (UE-7).

## 3. Checkout session modes

| Mode | v1 | Meaning |
|---|---|---|
| `PAYMENT` | yes | One payment of `amount` in `currency` to the merchant |
| `SUBSCRIPTION` | yes | The customer activates a mandate with `mandateTerms` |
| `SETUP` | **reserved, not in v1** | A session whose only purpose is to create or update an authorization without a payment and without subscription semantics. The API rejects it with `mode_not_available`; no behaviour is defined |

### 3.1 `PAYMENT`

A payment may be authorized in one of two ways, and the session implies neither:

1. **Pay Once.** The planner chooses among PO-1 to PO-6 ([10 §3](10-pay-once-protocol.md)) from the account's capabilities and the token's facts (§10.0).
2. **An existing compatible mandate.** A mandate that is active, belongs to the same merchant and the current router, covers the chain and token, pins the same currency and `boundsVersion` ([12 §5.3.2](12-router-lifecycle-and-migration.md)), whose caps hold for the amount, whose account pin is valid, and whose terms allow it. **Not enabled in v1:** it needs proof that the person on the page controls the account, a typed confirmation bound to the session, and a mandate term or cycle that allows a customer-present charge. None of the three exists (OPN-01, §11.A). Until OPN-01 is closed, a `PAYMENT` is a Pay Once payment.

**Implementation status.** Of the Pay Once paths, the contracts implement `payOnceWithSignature` (PO-1, and PO-5 which only adds a customer transaction before it). PO-2, PO-3, PO-4 and PO-6 are not built ([contracts/README.md](../contracts/README.md)). A session must never offer a path whose entrypoint does not exist on the chain.

### 3.2 `SUBSCRIPTION`

The session creates a mandate through the activation planner of [05](05-evm-authorization-decision-tree.md). `COMPLETED` means that the activation was finalized and the mandate is active on chain. It **does not** mean that the first billing cycle settled.

### 3.3 Initial charge

`amount` is the initial charge of a `SUBSCRIPTION`. It is 0 unless the merchant explicitly requests one.

- `amount = 0`: `COMPLETED` is reached when the activation is finalized. No payment is made in the session. The first cycle is charged later by the orchestrator and reported as its own payment event, not as a session event.
- `amount > 0`: the initial charge is part of the session, and `COMPLETED` requires both the activation and the initial charge to be finalized. `chargeInitial` is **not built** (contracts README), so the API rejects `amount > 0` for `SUBSCRIPTION` until it is. The completed event states `initial_charge_settled`.

## 4. Payer policy

| Policy | `expectedCustomerWallet` | Rule |
|---|---|---|
| `ANY_WALLET` | must be null | The first wallet that is connected **and verified** becomes the payer for this payment |
| `EXPECTED_WALLET` | required, EIP-55 checksummed on input | The connected wallet must equal the server-provided address (compared as 20 bytes) |

**EXPECTED_WALLET.** A mismatch is not a failure of the session: the connection is refused, the wallet is disconnected, `failureCode = wallet_mismatch` is recorded, and the session returns to `OPEN` (TR-04). **No address is shown before a wallet is connected, and none in the mismatch message** ("This checkout is for a different wallet. Connect the wallet the merchant named, or return to the merchant."). The URL is a bearer link and the address is personal data (ASM-023, SX-06).

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

A returning customer is recognised by a **public chain read** of mandates for the connected address (§11.A), not by a stored association. The browser may remember which connector the customer used last (a connector name, not an address) in its own local storage; that value never reaches FastPay.

A third party who has the URL can pay an `ANY_WALLET` session from their own wallet. The merchant sees the payer address in the completed event and reconciles by `clientReferenceId`. A merchant that wants one specific payer uses `EXPECTED_WALLET`.

## 5. State machine

### 5.1 States

| State | Terminal | Meaning | Attempt state of [06 §3.2](06-initial-architecture.md) |
|---|---|---|---|
| `OPEN` | no | Created; no connector in use | none |
| `CONNECTING` | no | A connection is in progress: an extension prompt, a pairing code on screen, a deep link opened | none |
| `WALLET_CONNECTED` | no | An account and chain were returned and the payer policy passed; nothing reviewed yet | none |
| `REVIEW_REQUIRED` | no | A fresh quote and plan exist and the review screen is shown; also the state after any recoverable failure before a submission | `SIMULATING` while checks run |
| `AWAITING_SIGNATURE` | no | The interactive authorization phase: signatures and prerequisite customer transactions of the plan. **At most one prompt outstanding** | none |
| `AUTHORIZED` | no | FastPay holds every signature the relayed path needs, verified and unexpired; nothing submitted | none |
| `SUBMITTING` | no | The final transaction is being handed to a broadcaster: FastPay's executor, or the customer's wallet (the request was sent to it) | `SUBMITTING` |
| `PROCESSING` | no | A transaction hash is recorded and the transaction is not yet final | `SUBMITTED`, `PENDING`, `CONFIRMED` |
| `COMPLETED` | **yes** | The payment (or the activation) is final | `FINALIZED` |
| `FAILED` | **yes** | FastPay has positive evidence that no successful payment occurred (§17) and no further attempt is allowed | `FAILED_PRE_SUBMISSION`, `FAILED_REVERTED` or proven non-execution |
| `UNKNOWN` | no | Submission may have occurred and authoritative resolution is unavailable or inconsistent (§17); being reconciled | `UNKNOWN`, `RECONCILIATION_REQUIRED` |
| `EXPIRED` | **yes** | `expiresAt` passed before any submission | none |
| `CANCELLED` | **yes** | Ended by the customer or the merchant before any submission | none |

A **submission** is the moment the final transaction is handed to a broadcaster. For a relayed path it is the executor's claim (TR-11). For a path in which the customer's wallet broadcasts it is the moment the transaction request is sent to the wallet (TR-12), because the customer may confirm it without FastPay learning of it. Prerequisite customer transactions of a plan (for example the exact approval of PO-5) are **steps of `AWAITING_SIGNATURE`**, not a submission; they change the customer's account state and remain after a cancellation or an expiry, and the page says so before it asks for them.

**After a submission the session has no second attempt.** `PROCESSING` and `UNKNOWN` end in `COMPLETED` or `FAILED` only, and `FAILED` is terminal: a customer who wants to try again starts a **new session** (OPN-02 records that [06 §3.2](06-initial-architecture.md) permits more at the attempt level). Refund states of the intent (`REFUND_PENDING` and later) are not session states.

### 5.2 Transitions

Every transition is a compare-and-set on `sessionVersion` (§5.4) and writes an audit event (§5.8). "Guard" is the condition that must hold when the transition is attempted. The event names are those of section 16.

| ID | From → to | Trigger and actor | Guard | Webhook |
|---|---|---|---|---|
| TR-01 | none → `OPEN` | Merchant creates the session | Authenticated merchant (TB-03); idempotency key; every validation of §14.2 passed; `expiresAt` within the bounds of CSR-01 | `checkout.session.opened` |
| TR-02 | `OPEN` → `CONNECTING` | Customer picks a connector | `now < expiresAt`; the context takes or holds the control lease (§9.3) | none |
| TR-03 | `CONNECTING` → `WALLET_CONNECTED` | Connector returns an account | Payer policy passed (§4); chain read agrees; `now < expiresAt` | none |
| TR-04 | `CONNECTING` → `OPEN` | Rejection, abandonment, pairing expiry, `wallet_mismatch` | None beyond the state; `failureCode` set if a mismatch | none |
| TR-05 | `WALLET_CONNECTED` → `REVIEW_REQUIRED` | System | A quote was issued (QL-01 to QL-03) and a plan was made; `selectedChain`, `selectedToken`, `authorizationPath` set; account mode allows the flow | none |
| TR-06 | `REVIEW_REQUIRED` → `REVIEW_REQUIRED` | Quote replacement, or the customer changes token or chain | The old quote is superseded in the same write (QL-02); `sessionVersion` increases; no signing request outstanding | none |
| TR-07 | `WALLET_CONNECTED` or `REVIEW_REQUIRED` → `CONNECTING` | Disconnect, or account change | Before any signing request; `connectedWallet`, quote and plan are discarded | none |
| TR-08 | `REVIEW_REQUIRED` → `AWAITING_SIGNATURE` | Customer presses the pay button | All ten checks of §7.3 passed in this revision; `now + MIN_SIGN_WINDOW ≤ expiresAt` and `≤ quote.validUntil`; no other request outstanding for the session on any chain (PX-07) | none |
| TR-09 | `AWAITING_SIGNATURE` → `AUTHORIZED` | Wallet returns the last required signature | Every signature validates for `connectedWallet` and the signed fields equal what the review screen showed; the ERC-1271 pre-flight `eth_call` passed where it applies ([10 §4](10-pay-once-protocol.md)); every deadline `≤ expiresAt` | none |
| TR-10 | `AWAITING_SIGNATURE` → `REVIEW_REQUIRED` | Rejection (`4001`), prompt timeout, account change, chain change, quote invalidation | The request is withdrawn; any signature that arrives later for it is discarded and never submitted; `failureCode` set; **a new review screen is shown** (QL-05) | none |
| TR-11 | `AUTHORIZED` → `SUBMITTING` | FastPay's executor claims the authorization | `now < expiresAt`; every deadline unexpired; the router and merchant still eligible; compare-and-set wins | none |
| TR-12 | `AWAITING_SIGNATURE` → `SUBMITTING` | The final transaction request is sent to the customer's wallet | As TR-11; the intent's `validUntil ≤ expiresAt` | none |
| TR-13 | `SUBMITTING` → `PROCESSING` | A transaction hash is recorded | The hash comes from the broadcaster or the wallet; `submittedTransactionHash` set | `checkout.session.processing` (first time only) |
| TR-14 | `SUBMITTING` → `REVIEW_REQUIRED` | **Proof that nothing was broadcast** | An explicit wallet rejection (FE-1), or an executor simulation failure before any broadcast (FE-3); `failureCode` set | none |
| TR-15 | `SUBMITTING` → `UNKNOWN` | Ambiguity after the transaction may have left the process | No hash and no proof of non-broadcast after the operational timeout; `unknownReason` set | `checkout.session.unknown` |
| TR-16 | `PROCESSING` → `COMPLETED` | Finality | Receipt and the settlement event for `paymentId` (or the activation event for the mandate) agree across at least two independent sources at the chain's finality threshold (TM-06, §16.3) | `checkout.session.completed` |
| TR-17 | `PROCESSING` → `FAILED` | Final revert (FE-4), or protocol state proves non-settlement (FE-5) | Evidence from at least two sources at the finality threshold | `checkout.session.failed` |
| TR-18 | `PROCESSING` → `UNKNOWN` | Reorg of a confirmed attempt, RPC disagreement, receipt not found, indexer lag beyond the threshold | `unknownReason` set | `checkout.session.unknown` |
| TR-19 | `UNKNOWN` → `COMPLETED` | Reconciliation proves settlement | As TR-16 | `checkout.session.completed` |
| TR-20 | `UNKNOWN` → `FAILED` | Reconciliation proves non-execution (FE-5) | The transaction was replaced or dropped **and** the account nonce was consumed by another transaction, or the chain shows no settlement for `paymentId` past the intent's deadline and the finality threshold ([06 §3.2](06-initial-architecture.md)) | `checkout.session.failed` |
| TR-21 | `REVIEW_REQUIRED` → `FAILED` | System | A failure with positive evidence (FE-1 to FE-3) whose code **ends the session** (§2.3), or the attempt limit is reached; no submission occurred | `checkout.session.failed` |
| TR-22 | any state before `SUBMITTING` → `CANCELLED` | Customer in the controlling context, or merchant through the API | Compare-and-set on `sessionVersion`; the status is one of `OPEN`, `CONNECTING`, `WALLET_CONNECTED`, `REVIEW_REQUIRED`, `AWAITING_SIGNATURE`, `AUTHORIZED`; `cancelReason` set; held signatures are discarded | `checkout.session.cancelled` |
| TR-23 | any state before `SUBMITTING` → `EXPIRED` | The clock reaches `expiresAt` | Compare-and-set; the status is one of the six of TR-22; held signatures are discarded. **From `AWAITING_SIGNATURE` with a final-transaction request outstanding, the state is `SUBMITTING`, not `AWAITING_SIGNATURE` (TR-12), so this transition does not apply** | `checkout.session.expired` |

**After a transaction is submitted, the customer may close the page.** The session stays `PROCESSING` or `UNKNOWN` until chain evidence resolves it; closing the page, losing the connection, the wallet disconnecting or the session reaching `expiresAt` change nothing.

### 5.3 Prohibited transitions

| ID | Prohibited | Why |
|---|---|---|
| PX-01 | Any transition out of `COMPLETED`, `FAILED`, `EXPIRED` or `CANCELLED` | Terminal. A new payment needs a new session; a webhook or a late event never reopens one |
| PX-02 | `EXPIRED` or `CANCELLED` from `SUBMITTING`, `PROCESSING` or `UNKNOWN` | `CANCELLED` is valid only before submission; expiry never ends a submitted transaction |
| PX-03 | `FAILED` from `PROCESSING` or `UNKNOWN` without the evidence of TR-17 or TR-20, or from a state before `SUBMITTING` other than through TR-21 | `FAILED` needs positive evidence (§17) |
| PX-04 | `COMPLETED` from any state but `PROCESSING` or `UNKNOWN`, or without the evidence of TR-16 | One source is a hint, not a money decision (TM-06) |
| PX-05 | `AWAITING_SIGNATURE` without the checks of §7.3 in the same revision | A stale quote or a stale account would be signed |
| PX-06 | A write with a stale `sessionVersion`, or any change that lowers or repeats it | Lost update, replay |
| PX-07 | Two outstanding signing or transaction requests for one session, on any chain | Duplicate signing-request prevention (CP-10) |
| PX-08 | A new attempt after a submission, whatever its outcome (the session is `SUBMITTING`, `PROCESSING`, `UNKNOWN` or `FAILED`), on this chain **or any other chain of the session**; changing `selectedChain`, `selectedToken`, `authorizationPath` or `paymentId` from `AWAITING_SIGNATURE` on | [06 §3.2](06-initial-architecture.md): no fallback while unknown. `markSettled` makes a payment settle at most once **per chain**; across chains only this rule prevents a second payment |
| PX-09 | Changing `mode`, `amount`, `currency`, `merchantId`, `payerPolicy`, `expectedCustomerWallet`, `allowedChains`, `allowedTokens`, `successUrl`, `cancelUrl`, `metadata`, `display`, `mandateTerms` or `expiresAt` after creation | Immutable. Extending the lifetime is not possible: the merchant creates a new session |
| PX-10 | `AUTHORIZED` back to `OPEN`, `CONNECTING` or `WALLET_CONNECTED` | A held signature must be discarded by TR-22 or TR-23, not left behind |
| PX-11 | Entering `SUBMITTING` at or after `expiresAt` | The executor refuses; every signature deadline is already `≤ expiresAt` |
| PX-12 | `UNKNOWN` displayed, sent or counted as `FAILED`, and `UNKNOWN` resolving to anything but `COMPLETED` or `FAILED` | Section 17 |

### 5.4 Idempotency and concurrency

- **Single writer.** Every transition runs under a lock on the session and is a compare-and-set on `sessionVersion`: the caller sends the version it read, and a mismatch returns a conflict and no change.
- **Replay.** Every transition carries an idempotency key (an event id). A replay returns the stored result and writes nothing.
- **Create.** `POST` of a session carries an idempotency key per merchant (TB-03). The same key with the same body returns the same session; the same key with a different body is an error (§14.2).
- **Webhooks.** At least once, deduplicated by event id (§16).
- **Chain.** `RouterRegistry.markSettled(paymentId)` makes the payment settle at most once on a chain, across router versions ([10 §2.2](10-pay-once-protocol.md)). The Pay Once nonce is `keccak256(paymentId, attemptNumber)` ([10 §2.3](10-pay-once-protocol.md)), so each attempt has its own nonce.

### 5.5 Retry rules

| Where the attempt stands | New attempt in the same session | Basis |
|---|---|---|
| Customer rejected the prompt (FE-1), nothing broadcast | Yes, only when the customer presses the pay button again. FastPay never re-prompts by itself | [10 §4](10-pay-once-protocol.md) "no retry loop" |
| Pre-submission validation or simulation failed (FE-2, FE-3) | Yes, with a new `attemptId` and a new nonce; another eligible token may be chosen | [06 §3.2](06-initial-architecture.md) |
| `SUBMITTING`, with proof that nothing was broadcast (TR-14) | Yes | as above |
| The attempt limit is reached, or the cause ends the session (§2.3) | No: `FAILED` (TR-21) | OPN-05 |
| **Any submission** (`SUBMITTING` without proof, `PROCESSING`, `UNKNOWN`, a final revert, proven non-settlement) | **No.** `FAILED` is terminal; the customer starts a **new session** | PX-08 |

A per-session limit on attempts exists and its value is not set here (OPN-05). `MIN_SIGN_WINDOW` is the value of [10 §3](10-pay-once-protocol.md) and [10 §9](10-pay-once-protocol.md) point 3; it is not set here either.

*Terminology.* [10 §4](10-pay-once-protocol.md) calls a user rejection `CANCELLED`. In this document that is an attempt-level event (FE-1); the session state `CANCELLED` is an end by the customer or the merchant. The two need reconciling (OPN-02).

### 5.6 Browser-visible behavior

| State | The page shows | Allowed actions | Must not |
|---|---|---|---|
| `OPEN` | Merchant, amount, currency, expiry countdown, wallet choices, "Continue this checkout on your phone" | Choose a connector, cancel | Auto-connect (CP-02); show any address or payment-destination QR code |
| `CONNECTING` | The connector's prompt, or code A with the label of §9 | Wait, choose another connector, cancel | Show other sessions' data |
| `WALLET_CONNECTED` | The abbreviated account, chain, a short wait while the quote is made | Disconnect | — |
| `REVIEW_REQUIRED` | The review screen of §10.0 and any blocker with its fix | Pay, change token or chain, refresh the quote, disconnect, cancel | Enable the pay button while a blocker or a stale quote exists |
| `AWAITING_SIGNATURE` | "Check your wallet", the step number, what the signature authorizes | Wait; "Send again" (CP-10); cancel before the final request | Ask for a second prompt at once |
| `AUTHORIZED` | "Authorized, submitting" | Cancel (until the executor claims) | — |
| `SUBMITTING` | "Sending your payment", no cancel | Wait | Offer another token or chain |
| `PROCESSING` | The hash with an explorer link, the confirmations, "You can close this page" | Close, return to the merchant (§15) | Offer a second payment; show "failed" |
| `COMPLETED` | Confirmation and a button that goes to `successUrl` | Leave | — |
| `FAILED` | What failed, whether funds moved (they did not), the hash if any | Back to the merchant (`cancelUrl`); start again from the merchant | Hide the hash; offer another attempt after a submission |
| `UNKNOWN` | "We are confirming your payment. **Do not pay again.**" the hash, the time of the last check | Close, reopen the URL, return to the merchant (§15) | Say "failed"; offer a second payment |
| `EXPIRED` | "This checkout expired", a button to the merchant | Leave | Offer to continue the same session |
| `CANCELLED` | "Cancelled", a button to the merchant | Leave | — |

After `expiresAt` the page for a session in `SUBMITTING`, `PROCESSING` or `UNKNOWN` stays available and keeps showing progress.

### 5.7 Webhook behavior

Seven events leave the session, each on the transitions of §5.2: `checkout.session.opened`, `.processing`, `.completed`, `.failed`, `.expired`, `.unknown`, `.cancelled`. Their fields, signature, replay window, retries, deduplication and ordering are in section 16 and in [checkout/event-catalog.md](checkout/event-catalog.md). **A merchant must not fulfil on `unknown`** and must not treat any event other than `completed` as proof of payment.

### 5.8 Audit events

Every audit record carries: `sessionId`, `from`, `to`, `sessionVersion`, `actor` (`customer`, `merchant`, `system`, `executor`, `reconciler`), the UTC time, and references to its evidence (hash, block, the sources that agreed). It never carries a signature, a secret or a seed. **Every `UNKNOWN` transition and every resolution is audited with the evidence that caused it** (section 17).

`session.created`, `connect.started`, `connect.rejected`, `wallet.connected`, `wallet.changed`, `chain.changed`, `lease.taken`, `quote.issued`, `quote.replaced`, `quote.invalidated`, `review.shown`, `signature.requested`, `signature.rejected`, `signature.received`, `signature.invalid`, `authorization.recorded`, `submission.claimed`, `tx.hash_recorded`, `tx.confirmed`, `tx.finalized`, `tx.reverted`, `unknown.entered`, `reconciliation.started`, `reconciliation.resolved`, `session.failed`, `session.cancelled`, `session.expired`, `webhook.queued`, `webhook.delivered`, `webhook.failed`.

## 6. Expiry and deadlines

### 6.1 Lifetime

The proposed default is **30 minutes** (1,800 s, CSD-11). The minimum, default and maximum lifetimes that a merchant may configure are the configuration record **CSR-01** ([checkout/config-records.md](checkout/config-records.md)): minimum 600 s (10 minutes), default 1,800 s (30 minutes), maximum 86,400 s (24 hours). **None of the three bounds is approved.** `expiresAt = createdAt + lifetime`, and the lifetime is chosen at creation inside the bounds (`expires_in`, §14.2).

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
| Finality | per chain | [06](06-initial-architecture.md) | **no per-chain rule approved** (OPN-15) |

The server clock decides `expiresAt`; the chain compares deadlines with `block.timestamp` (TM-09). The difference between the two clocks does not matter for safety, because the chain deadline is never later than `expiresAt` and the chain enforces it.

### 6.4 The configuration record

CSR-01 is the **configuration record for the session lifetime**: minimum, default and maximum merchant-configurable lifetime. It is kept, with its rationale, evidence, range, tests and an unsigned approval block, in [checkout/config-records.md](checkout/config-records.md). It is **not** a production-blocking constant: it has no PC number, is not in the register of [18](18-configuration-records.md), is not counted by condition C-4 of `freeze_readiness.py`, and does not change that tool's result. **Status: PROPOSED. Nothing in it is approved.**

## 7. Quote lifecycle

A **quote** is FastPay's proposal of the token amount that pays `amount` in `currency` on a chain and token, valid until `validUntil`. When a signed `PriceQuote` ([11 §4](11-dual-cap-model.md)) is needed, the quote record carries its `quoteHash`; when settlement is 1:1 the record is internal and the `quoteHash` of the intent is zero ([10 §2.1](10-pay-once-protocol.md)). Quotes are proposals, never trusted (TM-07): the chain verifies outcomes.

### 7.1 Rules

| ID | Rule |
|---|---|
| QL-01 | **Only one quote may be active for a given session revision.** A session revision is a value of `sessionVersion`. The service keeps at most one active quote per session; activating a new one supersedes the old one in the same write |
| QL-02 | **Creation and replacement.** A quote is created at TR-05 and replaced at TR-06. `validUntil = min(now + quote TTL, expiresAt)` and never more than `MAX_QUOTE_TTL`. A replaced quote is `superseded` and can never be used in a signing request |
| QL-03 | **Refresh.** The page refreshes the quote before showing a prompt if the remaining validity is shorter than `MIN_SIGN_WINDOW`, and when the customer asks. A refresh is a replacement; it never happens while a request is outstanding |
| QL-04 | **Expiry.** An expired quote cannot start TR-08. The session stays open and is re-quoted inside the same session (ER-06) |
| QL-05 | **Invalidation.** The active quote is invalidated and the plan is discarded when any of these changes: the connected account, the chain, the token, the amount (the token amount of the quote, the fee), the merchant recipient, the mandate state, the account pin or mode, the token policy, or a registry version used by the quote (bounds version, signer set). The unsigned request is withdrawn (TR-10), the session returns to `REVIEW_REQUIRED` (or `CONNECTING` for an account change, TR-07) and **a new review screen is required** before any new request. A late signature for the old quote is discarded |
| QL-06 | A quote is bound to the revision in which it was issued: a signature obtained for a superseded or invalidated quote is never submitted, whatever its deadline |

### 7.2 What the review screen is

The review screen is generated from the **same typed-data object** that will be sent to the wallet (TM-05): what the customer reads is what the wallet is asked to sign. A test compares the two (§22.3).

### 7.3 Checks immediately before the signature

All ten run in TR-08, in the revision that will be signed. Chain facts are read from at least two independent sources (TM-06). The balance and the allowance are advisory: the contract is the enforcement (TM-02).

| # | Check | Source of truth | On failure |
|---|---|---|---|
| 1 | Token balance covers the gross amount | Chain | `insufficient_balance`; stay in `REVIEW_REQUIRED` |
| 2 | Allowance suits the chosen path (to Permit2 for PO-1, to the router for PO-2 or PO-6, none for PO-3 or PO-4) | Chain | The planner re-plans (PO-5 adds the approval step); `insufficient_allowance` if no path remains |
| 3 | Price: the quote is signed by an active signer set, inside the registry band and the TTL ceiling | `TokenPolicyRegistry`, `SignerSetRegistry` | New quote (QL-02) |
| 4 | Quote deadline: `now + MIN_SIGN_WINDOW ≤ quote.validUntil` and `≤ expiresAt` | Clock | New quote, or no new authorization (ER-01) |
| 5 | Merchant recipient equals the registry's current recipient, and the merchant is active | `MerchantRegistry` | `merchant_disabled`, or a new quote ([10 §5](10-pay-once-protocol.md)) |
| 6 | Mandate state: for a `SUBSCRIPTION`, no existing mandate that the activation rules of [05](05-evm-authorization-decision-tree.md) and [12](12-router-lifecycle-and-migration.md) treat as conflicting; for a compatible mandate (OPN-01), active and not paused or revoked | `MandateManager` | Block, or fall back to Pay Once |
| 7 | Account pin and mode allow the flow | [17](17-account-compatibility-policy.md), `MandateManager` | `account_not_eligible` |
| 8 | Chain: the provider's chain id equals `selectedChain`, which is in `allowedChains` and enabled | Provider and two RPC sources | `chain_unsupported`; ask for a switch |
| 9 | Token policy: status `SETTLEMENT` or `DIRECT_PAYMENT`, not a blocked token class (ASM-022), bytecode hash as registered | `TokenPolicyRegistry` | `token_disabled` |
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
| CP-01 | Browser extension discovery, and EIP-6963 where available | The page lists the wallets it can discover and lets the customer choose. It never assumes there is exactly one wallet. Discovery uses the mechanism that the retrieved standard specifies, EIP-6963 where the wallet offers it; until then the only evidence is the lab (CSU-01) |
| CP-02 | No auto-connect | A connection starts only from a user gesture on this page. No connection is attempted on load, and no previously granted connection is used silently (UI-09 of [04](04-context-and-trust-boundaries.md) §6) |
| CP-03 | WalletConnect pairing QR | Code A (§9) shows a pairing code produced by the connector library. It is single-use, has its own lifetime (CSU-06), is refreshed when it expires, and is never reused across sessions |
| CP-04 | Mobile deep links | The page opens the wallet through the link the connector provides and shows the same pairing as a copyable fallback. It never assumes that a wallet is installed or that the return comes back to the same tab (CSU-07) |
| CP-05 | Wallet in-app browsers | When the page detects that it runs inside a wallet's browser, it uses the injected provider and does not show a pairing code. The same session and the same origin apply |
| CP-06 | Hardware wallets reached through supported connectors | A hardware wallet is reached through its host wallet. Consent does not rely on the device's own screen (WL-21, ASM-006, ASM-007). If the host wallet shows the typed data as opaque, Pay Once uses a transaction path (WL-27) |
| CP-07 | Reconnection | After a lost connection the page reconnects automatically for a short time, shows "reconnecting", then offers a new code A and the choice of another wallet. **Reconnecting never creates a new session and never re-sends a signing request** |
| CP-08 | Pairing expiration | An expired pairing returns the session to `OPEN` (TR-04) with a fresh code on request |
| CP-09 | Session expiration | A connector session that ends while the checkout session is `WALLET_CONNECTED` or `REVIEW_REQUIRED` is a disconnect (TR-07). While `AWAITING_SIGNATURE` it withdraws the request (TR-10). After a submission it changes nothing |
| CP-10 | Duplicate signing-request prevention | A request has an id: (session id, attempt id, step index, request kind). The server holds at most one outstanding request per session (PX-07). A page refresh or a second tab fetches the state and does **not** send the request again; it shows "check your wallet". "Send again" first withdraws the old request and issues a new attempt with a new nonce. The old signature, if the customer produced it, is discarded |
| CP-11 | Account changes | A different account than `connectedWallet` withdraws the request and discards the quote, plan and signatures not yet used (TR-07, TR-10, QL-05). For `EXPECTED_WALLET`, a different account is `wallet_mismatch` |
| CP-12 | Chain changes | A chain other than `selectedChain` withdraws the request and discards the quote. The page asks for a switch and, if the wallet refuses, offers another chain among `allowedChains` |
| CP-13 | Wallet rejection | An explicit rejection is `user_rejected` (FE-1): the session returns to `REVIEW_REQUIRED`, shows a neutral message and does not re-prompt |
| CP-14 | Connection loss | Nothing is assumed. For a signature request, the request stays outstanding until its deadline. For a final-transaction request sent to the wallet (TR-12), the session stays `SUBMITTING` until a hash appears or reconciliation resolves it (`wallet_result_lost`, UE-1) |
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
| Encodes | The pairing URI produced by the connector library (format `UNVERIFIED`, CSU-03). Not produced by FastPay's own encoder; contains no amount, no merchant, no session id, no address |
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
- Holding the control lease allows cancelling the session from the page (TR-22). It does not allow spending.

Anyone who has the URL can take the lease in those four states. That is a nuisance, not a loss of funds (CS-4); it is recorded for Security review (SX-09, OPN-04).

## 10. Customer experiences

All experiences are `SPECIFIED` and `UNVERIFIED`: no wallet has been tested for any of them.

### 10.0 Common rules, and the authorization planner

**The review screen** shows: the merchant's name from `display`, the fiat `amount` and `currency`, the token amount and chain, the recipient (abbreviated, with the registry name), the expiry time, and what the signature authorizes:
- For a payment: "One payment of exactly this amount to this merchant." Nothing remains authorized afterwards (`I-PO-NOSTANDING`).
- For a `SUBSCRIPTION`: the standing authorization in the terms of the mandate (caps, cadence, end), with the consent copy of [05](05-evm-authorization-decision-tree.md) and the distinct wording that separates it from a one-off payment.

It also shows the **number of prompts and transactions** of the chosen path. It does not show an internal path code, and it never says that a payment is "gasless" or "free" unless the planner's path guarantees it.

**Pay Once does not always use Permit2 `SignatureTransfer`.** The authorization planner chooses among the compatible paths from the account's capabilities, the token's facts and the policy; the session records the result in `authorizationPath` and never forces one. A path whose entrypoint is not deployed on the chain is not compatible.

| Named path | Path codes ([10 §3](10-pay-once-protocol.md), [05](05-evm-authorization-decision-tree.md)) | What the customer does | In the contracts today |
|---|---|---|---|
| Permit2 `SignatureTransfer` with witness | PO-1 (the allowance to Permit2 already exists); PO-5 (after a one-time exact approval of Permit2); PO-3 (after an ERC-2612 permit) | One typed-data signature (PO-1); an approval transaction and a signature (PO-5); two signatures (PO-3) | PO-1 and PO-5 built (`payOnceWithSignature`); PO-3 not built |
| Wallet-managed atomic batch | PO-2 for a payment; the activation batch of [05](05-evm-authorization-decision-tree.md) for a `SUBSCRIPTION` | One prompt that sends the batch | PO-2 not built |
| Existing Permit2 allowance | The precondition that makes PO-1 a one-prompt path. For a **mandate**, the standing `AllowanceTransfer` allowance to the router, usable only by a compatible mandate (§11.A) | One signature (PO-1); none for a mandate charge | PO-1 built; the mandate route is blocked (OPN-01) |
| Direct token transaction where supported | PO-4 (an ERC-3009 authorization, flag-gated, token-native); PO-6 (the customer sends the transactions; no typed data) | PO-4 one signature; PO-6 two transactions | not built |
| Legacy approval and payment path | PO-6 (`approve` to the router, then `payOnce`); PO-5 (`approve` to Permit2, then a signature) | Two transactions, or a transaction and a signature | PO-6 not built; PO-5 built |

A plain ERC-20 transfer to the merchant is **not** a FastPay path: the router must be in the path for the witness, the fee and `markSettled` to apply.

### 10.1 Desktop with a browser wallet

1. The page lists the discovered wallets (CP-01); the customer chooses the extension. `OPEN` → `CONNECTING`.
2. The extension asks to connect; on approval the page checks the chain and the payer policy (`WALLET_CONNECTED`), asks for a chain switch if needed.
3. Quote and plan (`REVIEW_REQUIRED`), the review screen, the pay button.
4. The planner's path runs (§10.0).
5. `AUTHORIZED`, `SUBMITTING`, `PROCESSING`, `COMPLETED`, then the redirect to `successUrl` (§15).

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

The customer opens the checkout URL inside the wallet's browser (by pasting it, or by scanning code B with the wallet's scanner). The page detects the injected provider and skips pairing (CP-05). From `CONNECTING` on, the flow is §10.1. The origin is the same hosted origin; the page makes the same security assertions (SX-03).

Evidence: GAP-02.

### 10.5 Hardware wallet

The customer connects a host wallet that fronts the device (CP-06) and the flow is §10.1 or §10.2. The device's own screen is not relied on for consent. If the host wallet or the device cannot sign the typed data, or shows it as opaque (WL-21), the planner uses a transaction path where one exists (WL-27); if none exists the page says so, and the customer may choose another wallet. A hardware wallet is mentioned in the product only where its row in the Compatibility Register is E3.

Evidence: WL-21, WL-27.

### 10.6 Customer without a wallet

Specified in section 12.

### 10.7 Wallet with insufficient funds

The check of §7.3 (1) fails: the page shows the required and the available amount of the token (chain data), `insufficient_balance`, and the options:
- another allowed token or chain on which the balance suffices;
- add funds to the customer's own wallet, then "Check again";
- cancel.

The session keeps running until `expiresAt`. The pay button stays disabled. FastPay offers no purchase of tokens in v1.

### 10.8 Wallet with insufficient native gas

Gas is needed by the paths in which the customer sends a transaction (PO-2, PO-5, PO-6, an activation batch or approval). PO-1 needs no customer gas for the payment itself, because the executor submits it ([10 §2.2](10-pay-once-protocol.md)). Who bears the executor's gas and how it is recovered is stated for recurring charges (ASM-012) and is not specified for Pay Once (OPN-07).

If the only eligible path needs gas and the estimate (advisory) exceeds the native balance, the session stays in `REVIEW_REQUIRED` with `insufficient_native_gas` and the options: add native token to the wallet, choose another chain or token, cancel. **No gas sponsorship is specified or implied** (ASM-018; OPN-07).

### 10.9 Returning customer with a compatible active mandate

Specified in section 11.A. **Not enabled in v1.**

### 10.10 Unattended recurring charge

Specified in section 11.B. It is **not a checkout session.**

### 10.11 Interrupted activation

For a `SUBSCRIPTION`, the customer closes the browser or loses the connection during the activation:

| Where it stopped | What happens |
|---|---|
| Before any signature (`CONNECTING` to `REVIEW_REQUIRED`) | The session continues until `expiresAt`; the customer reopens the URL or scans code B and resumes (CP-15, CP-16) |
| Signatures held, executor not yet claimed (`AUTHORIZED`) | The executor submits if the deadlines allow (TR-11); otherwise TR-23. The customer need not return |
| Final request sent to the customer's wallet, no result seen (`SUBMITTING`) | The session stays `SUBMITTING`; reconciliation looks for the activation of the mandate by the deterministic creation nonce of the session; a hash or the event moves it to `PROCESSING`, no evidence until the deadline moves it to `UNKNOWN` and then to `COMPLETED` or `FAILED` (CP-14) |
| Hash recorded (`PROCESSING`) | Nothing the customer does matters; the session is resolved by chain state (ER-09) |

The mandate and the creation nonce must be derivable from the session so that reconciliation can find the activation; that derivation is not yet specified (OPN-12).

### 10.12 Rejected signature

The customer rejects the prompt: `user_rejected` (FE-1), TR-10, the session returns to `REVIEW_REQUIRED` with a neutral message ("You did not sign. Nothing was sent. Pay when you are ready."). FastPay does not re-prompt. Each press of the pay button is a new attempt with a new nonce (§5.5), up to the attempt limit.

### 10.13 Account or chain changed during checkout

| Change | Before `AWAITING_SIGNATURE` | During `AWAITING_SIGNATURE` | After `AUTHORIZED` |
|---|---|---|---|
| Different account (`ANY_WALLET`) | `CONNECTING`, discard quote and plan (TR-07, QL-05) | Withdraw the request, discard signatures not used, then a new connection and a new review (TR-10, TR-07) | No effect: the payer is fixed |
| Different account (`EXPECTED_WALLET`) | `wallet_mismatch`, wallet disconnected, `OPEN` | As above, then the same | No effect |
| Different chain | Ask for a switch; quote discarded | Withdraw the request, discard the quote (QL-05); a new review | No effect |

No authorization obtained for the old account or chain is ever submitted (WL-24: "the plan is re-made from chain state; no stale authorization is submitted").

## 11. Returning customers

There are **two different flows.** They are not variants of one another: they differ in who is present, in what authorizes the money to move, in whether a checkout session exists, and in what can be checked before the transfer.

| | A. Interactive repeat purchase | B. Unattended recurring charge |
|---|---|---|
| Customer present | **Yes**, in a checkout session | **No** |
| Checkout session | Yes (`PAYMENT`) | **None**: no session, no page |
| What authorizes it | A mandate the customer already holds, **and** a fresh act of the customer in this session (proof of control, a typed confirmation) | The mandate alone (terms, caps, cadence), with no act of the customer |
| Who starts it | The customer, by pressing the pay button | The merchant's orchestrator, on the mandate's cadence |
| Entry point in the contracts | **None** (OPN-01) | `charge` (per mandate and cycle) |
| Available in v1 | **No** | Specified in [05](05-evm-authorization-decision-tree.md), [11](11-dual-cap-model.md), [13](13-eip7702-delegation-inspection.md), [17](17-account-compatibility-policy.md); the contract `charge` is built; the typed charge request is not (F-19) |

### 11.A Interactive repeat purchase

*What the product wants to do:* recognise a customer who already holds a compatible mandate with this merchant and let them select it in the checkout, without a new allowance prompt.

*The intended flow, if it is ever enabled:*
1. The customer connects a wallet (§10.1 to §10.4).
2. The page reads the mandates of the connected address on chain (a public read; no stored association, §4) and lists the **compatible** ones (§3.1).
3. The customer selects one. The page asks for a **typed confirmation** bound to the session id, merchant, amount, currency, `paymentId` and expiry. The signature proves control of the account.
4. The router charges under the mandate; the session follows TR-11 to TR-16.

*Why it is not enabled:* the connected address is only a claim until a signature proves control (§4). A charge under an existing mandate needs no signature from the customer today, so a person who types a victim's address into a checkout could cause a charge of the victim's mandate for the attacker's order. It would also consume the caps of a recurring mandate for a one-off payment, and `charge` is defined per mandate and cycle ([10 §1](10-pay-once-protocol.md)), not for an ad hoc purchase. Three things are missing: proof of control bound to the session, a typed confirmation, and a mandate term or cycle that allows a customer-present charge (OPN-01; finding F-19 of the implementation report). Enabling it changes `eip712/types.json` and therefore the C-11 fingerprint.

*What the product does in v1:* the page may show, from a public chain read, that a mandate exists ("You already have a FastPay authorization with this merchant. Manage it in your portal."). It does not offer to use it. A `PAYMENT` is a Pay Once payment. A `SUBSCRIPTION` is activated as a new mandate; whether a second mandate for the same merchant is accepted is decided by the activation rules of [05](05-evm-authorization-decision-tree.md) and [12](12-router-lifecycle-and-migration.md), which this document does not restate, and the page shows the existing mandate before it asks for a new one.

### 11.B Unattended recurring charge

The customer is not present and no session exists. The executor may charge **only when every one of these validations passes**; any failure refuses the charge and creates no payment (TM-11):

| Validation | What is checked | Enforced |
|---|---|---|
| Mandate | The mandate exists, is active, not paused, revoked or expired, and belongs to the router charging | Chain (`consume`) |
| Account pin | The account's code hash, delegate and signature mode still equal the pin ([17](17-account-compatibility-policy.md) §5) | Chain (`consume`), and the revalidation of [13](13-eip7702-delegation-inspection.md) before every unattended charge |
| Token | The token is one the mandate names and its status in `TokenPolicyRegistry` allows the charge | Chain and registry |
| Allowance | The Permit2 allowance from the account to the router covers the amount and has not expired ([12 §5.3.1](12-router-lifecycle-and-migration.md)) | Chain (Permit2) |
| Cycle | The charge falls in a cycle that has not been charged, in the cadence of the mandate (once per `(mandateId, cycleId)`) | Chain (`UsageLedger`) |
| Limit | The per-token hard caps and the fiat caps of the dual cap model hold ([11](11-dual-cap-model.md)) | Chain |
| Quote | The signed `PriceQuote` passes Q1 to Q18 and its age is within `maxQuoteAge` | Chain |
| Risk | No pause bit or risk hold is set on the mandate, the merchant, the router, the token or the executor; the signer policy accepts the request | Chain (pause bits) and backend (risk service, signer policy) |

The typed charge request that the merchant's signer authenticates is not specified (F-19, OPN-01). The customer sees the charges in the mandate portal and on chain and can revoke, pause or reduce at any time (TM-14). **How a customer is told of a charge or of a failed charge is not specified** (v1 collects no customer email, CSD-08; OPN-06). A failed charge is dealt with by the merchant, who may send the customer to a new checkout session.

## 12. No-wallet behavior

FastPay v1 requires a **funded wallet**. It does not create a wallet, offer an embedded wallet, use a deposit address or sell crypto.

When no wallet is available (none is discovered, the customer says so, or the customer's wallet is refused), the page shows, in this order:

| ID | Element | Content |
|---|---|---|
| NW-01 | Explanation | "To pay with FastPay you need a crypto wallet with funds. FastPay does not hold your money, create a wallet for you or sell crypto." |
| NW-02 | Vetted external-wallet options | A short, neutral list of wallet apps with links that open the wallet's own site. It is labelled "Examples. FastPay has not tested every wallet." The list is vetted for the identity of the publisher and the official download link (OPN-14); it says **nothing about support** for a wallet that is not at E3 in the Compatibility Register ([15 §2.1](15-wallet-lab-matrix.md)). The links carry no FastPay identifier and the page loads nothing from them |
| NW-03 | Use a phone wallet | The pairing flow with code A "Scan with your wallet" (§9.1), for a customer who has a wallet on another device |
| NW-04 | Copy checkout link | Copies the hosted URL (CS-1), so the customer can open it where the wallet is |
| NW-05 | Checkout continuation QR | Code B "Continue this checkout on your phone" (§9.2) |
| NW-06 | Return to merchant | Ends the session as `CANCELLED` (TR-22) with `cancelReason = no_wallet` and goes to `cancelUrl` |

The session stays open until `expiresAt` while the customer reads the page (CSD-07). There is no email resume (CSD-08).

**Cancel redirect and reason codes.** The cancel redirect may carry a stable reason code, and only through the documented template `{CANCEL_REASON}` of §15. The codes are: `no_wallet`, `wallet_unsupported`, `customer_cancelled`, `session_expired`. A reason code is a hint for the merchant's page; **it is not authoritative and not sensitive**: the merchant reads the real state through the API or a webhook. No wallet address, amount, hash, email or any other personal data is ever put in a redirect query parameter.

## 13. Deposit-address exclusion

**Per-invoice deposit addresses are excluded from v1** (CSD-05). There is no endpoint, field, page, QR code or copy that gives a customer an address to send funds to. A transfer to an address is not a FastPay payment.

| ID | Why, and what would be needed |
|---|---|
| DX-01 | **A FastPay-controlled address may create custody concerns.** FastPay would hold customer funds, even briefly, and the v1 scope excludes custody (CSD-04, [06 §8](06-initial-architecture.md)) |
| DX-02 | **A merchant-controlled address requires a separate reconciliation and refund model.** Matching a transfer to an order, handling over- and under-payment, wrong tokens and wrong chains, and refunding to an unproved sender are all outside this specification (ASM-024) |
| DX-03 | **A forwarding or escrow contract requires a separate ownership, recovery, security and legal design.** Who owns it, who can recover a mistaken transfer, what the audit scope is and what licence it needs are open and not specified |
| DX-04 | **Pay-from-exchange support is a future, independent product decision.** An exchange withdrawal comes from the exchange's address, cannot sign typed data and cannot create a mandate |
| DX-05 | **A transfer to a deposit address does not create a FastPay mandate.** A mandate exists only through a signature of the customer's own account (TM-01) |
| DX-06 | **Neither QR code is a deposit QR** (§9), and the acceptance criteria of section 20 include a check that no path returns a receiving address (AC-15) |

## 14. Merchant integration

The API names, paths and field spellings are proposals and are not frozen. The full catalog is [checkout/api-catalog.md](checkout/api-catalog.md).

### 14.1 Flow

1. The merchant's server creates a session (§14.2) with its API key.
2. The merchant sends the customer to the returned `url` (a redirect, §14.3). Embedded checkout is separately gated (§14.6).
3. The customer pays on the FastPay page.
4. FastPay delivers webhooks (§16).
5. The customer is sent to `success_url` or `cancel_url` (§15). **The merchant confirms the payment from the webhook or from an authenticated read of the session, never from the redirect.**

### 14.2 `POST /v1/checkout/sessions`

| Request field | Type | Required | Rule |
|---|---|---|---|
| `mode` | string | yes | `payment` or `subscription`; `setup` is rejected with `mode_not_available` |
| `amount` | integer | yes | Minor units; a positive integer (0 only for a `subscription` without an initial charge); never a decimal or a string with a decimal point; at most the merchant's configured maximum |
| `currency` | string | yes | ISO 4217; must be a currency of `TokenPolicyRegistry` |
| `client_reference_id` | string | yes | The merchant's order reference; length-limited |
| `success_url` | string | yes | RD-01 |
| `cancel_url` | string | yes | RD-01 |
| `allowed_chains` | list | no | Subset of the chains enabled for the mode; default: the merchant's enabled chains |
| `allowed_tokens` | list | no | Subset of the registry tokens of those chains; default: the merchant's default list |
| `expected_customer_wallet` | string | no | Required if `payer_policy` is `expected_wallet`; forbidden otherwise; EIP-55 checksummed |
| `payer_policy` | string | yes | `any_wallet` or `expected_wallet` |
| `expires_in` | integer, seconds | no | Default 1,800; inside the bounds of CSR-01 (proposed 600 to 86,400) |
| `metadata` | map | no | Limits below |
| `display` | object | yes | Merchant name, description, optional line items (no personal data) |
| `mandate_terms` | object | for `subscription` | The `MandateTerms` the merchant requests |

**Requirements.**

| ID | Requirement |
|---|---|
| MI-01 | **Merchant authentication.** A scoped, hashed, rotatable API key (OD-014, TB-03). `merchantId` and `liveMode` come from the key. A test key can never create a live session |
| MI-02 | **Idempotency key.** The `Idempotency-Key` header is required. The same key and body return the original response; the same key with a different body fails with `idempotency_conflict` |
| MI-03 | **Server-side validation.** Every field is validated on the server against the rules above; a failure returns a stable error code and creates nothing. Nothing the browser says is trusted |
| MI-04 | **URL allowlisting.** RD-01 |
| MI-05 | **Amount validation.** An integer in minor units (ADR-011), above zero, within the merchant's maximum and the token policy's limits for the chosen tokens; the currency's exponent comes from the registry |
| MI-06 | **Metadata limits** (proposed values, not approved): at most 20 keys, a key at most 40 bytes, a value at most 500 bytes, 4 KiB in total; string values only; no nesting. Over a limit: `metadata_too_large`. Metadata is merchant-private (§2.1) and must not carry personal data |
| MI-07 | **Rate limiting.** Per API key and per source address, on create, retrieve and cancel; an excess returns `rate_limited` with a retry hint. The values are an operational parameter and are not set here |
| MI-08 | **Audit logging.** Every create, retrieve, cancel and every refusal is logged with the key id, the idempotency key, the request hash, the result and the time; the body is redacted (SX-11) |

**Response.**

| Field | Notes |
|---|---|
| `id` | The session id (§2.2) |
| `url` | The hosted checkout URL (CS-1) |
| `status` | `open` |
| `created_at`, `expires_at` | RFC 3339 UTC |
| `client_secret` | **Only** for an approved embedded-checkout flow (§14.6). **Absent for Hosted Checkout v1**, which does not expose a client secret to the merchant's browser |

The response also echoes `mode`, `amount`, `currency`, `client_reference_id`, `payer_policy`, `live_mode` and `session_version`.

### 14.3 Redirect checkout

The merchant redirects the customer (HTTP 303) to `url`. The hosted page is served from a dedicated origin that no merchant script ever runs in (SX-03). The page works for a customer who arrives from a link, a QR code (code B) or a message the merchant sent.

### 14.4 Client secret

Hosted Checkout v1 does not need a client secret in the merchant's browser, and the API never returns one for it. A `client_secret` exists only for an approved embedded-checkout flow (§14.6): scoped to one session, expiring no later than it, never in a URL, never spending authority (CS-6).

### 14.5 Reading and cancelling a session

`GET /v1/checkout/sessions/{id}` (authenticated; includes `metadata`) and `GET /v1/checkout/sessions` (filter by `client_reference_id`, status, creation time) let the merchant verify a result and find duplicates (OPN-03). `POST /v1/checkout/sessions/{id}/cancel` ends a session that is not yet submitted (TR-22, `cancel_reason = merchant_cancelled`); after a submission it fails with `session_already_submitted`.

### 14.6 Embedded Checkout and Payment Links, separately gated

Both reuse the session of this document unchanged (CSD-10). Neither is part of the first implementation (CSD-09).

| | Embedded Checkout (S02) | Payment Links (S03) |
|---|---|---|
| What it is | The same page in an iframe on the merchant's page, driven by a `client_secret`, with a `postMessage` interface | A long-lived merchant link that **creates a new session per visit** |
| Extra gate | Hardening of the iframe and `postMessage` ([06 §2.1](06-initial-architecture.md)); clickjacking review; whether a wallet extension can reach a cross-origin frame (`UNVERIFIED`, not tested); a separate review of the origin and CSP; a frame policy that allows only the merchant's registered origins | Link-level controls (expiry, quantity, a per-link cap); abuse and spam review; the lifetime of a link is not the lifetime of a session |
| `client_secret` | A secret scoped to one session, expiring no later than it, never in a URL, never spending authority | Not used |
| What it must not do | Change a state, a guard or a deadline; expose `metadata` to the frame | Reuse one session for several payments |

## 15. Redirect rules

| ID | Rule |
|---|---|
| RD-01 | **Validation.** `success_url` and `cancel_url` must be HTTPS (the test mode also allows `http` on `localhost`), carry no credentials, no fragment and no IP literal, be at most 2,048 characters, and belong to a domain the merchant has registered. A URL outside the registered domains is rejected at creation. This closes the open-redirect risk of a hosted page that redirects to a URL given in a request |
| RD-02 | **The success redirect is not proof of payment.** A person can type the URL. Reaching `success_url` means the customer finished interacting with the page, nothing more |
| RD-03 | **What the redirect may carry.** Only a safe session identifier or a documented template substitution. The merchant writes the placeholder `{CHECKOUT_SESSION_ID}` in either URL and FastPay replaces it with the session id; the cancel URL may also contain `{CANCEL_REASON}`, replaced with a stable code of §12. **Nothing else is appended or substituted.** No amount, status, address, hash, signature, email or `metadata` ever appears in a redirect |
| RD-04 | **How the merchant learns the result.** Through a **signed webhook** (§16), or through an **authenticated retrieval** of the session (§14.5). A merchant that fulfils on the redirect alone is outside this specification |
| RD-05 | **The cancel URL is available only before transaction submission.** The cancel action exists in the states of TR-22 and in `EXPIRED`. After a submission it is not offered |
| RD-06 | **After submission** the page displays `PROCESSING` or `UNKNOWN`. It does not offer cancellation as if no transaction existed, and it does not say "failed" for `UNKNOWN` |
| RD-07 | **Return to the merchant after a submission.** A customer who wants to leave while the session is `PROCESSING` or `UNKNOWN` is sent to `success_url` with a page that says the payment is still being confirmed; the merchant reads the state (RD-04) and shows "pending". The cancel URL is not used for it (RD-05) |
| RD-08 | **From `FAILED`, `EXPIRED` and `CANCELLED`** the customer goes to `cancel_url`, with the reason code of §12 where the merchant asked for it |
| RD-09 | **No redirect before the state is known.** The page redirects only from a state the server has recorded; a client-side claim of success never triggers one |

## 16. Webhooks

The full catalog, with an example payload per event, is [checkout/event-catalog.md](checkout/event-catalog.md). All values below are proposals.

### 16.1 Events

| Event | State | Emitted at |
|---|---|---|
| `checkout.session.opened` | `open` | TR-01: the session was created and is open. It does not mean a customer has seen the page |
| `checkout.session.processing` | `processing` | TR-13, the first time only |
| `checkout.session.completed` | `completed` | TR-16, TR-19 |
| `checkout.session.failed` | `failed` | TR-17, TR-20, TR-21 |
| `checkout.session.expired` | `expired` | TR-23 |
| `checkout.session.unknown` | `unknown` | TR-15, TR-18 |
| `checkout.session.cancelled` | `cancelled` | TR-22 |

### 16.2 Fields of every event

| Field | Notes |
|---|---|
| `id` | **Stable event id.** The same on every retry of the same event; unique per event |
| `type` | The event name |
| `api_version` | The version of the event schema (a date, for example `2026-10-17`) |
| `created` | RFC 3339 UTC time at which the event was created |
| `live_mode` | Boolean |
| `merchant_id` | The merchant the session belongs to |
| `data.session_id` | The session id |
| `data.payment_id` | The `paymentId` where relevant (a `PAYMENT` after the chain is chosen); otherwise null |
| `data.mandate_id` | The mandate where relevant (a `SUBSCRIPTION` that reached activation); otherwise null |
| `data.state` | The state the session entered, in lower case |
| `data.session_version` | The `sessionVersion` at which the event was created |
| `data.failure_reason` | The `failure_code` (§2.3) for `failed`; otherwise null |
| `data.unknown_reason` | The `unknown_reason` (§2.3) for `unknown`; otherwise null |
| `data.cancel_reason` | The stable code of §12 for `cancelled`; otherwise null |
| `data.chain_id` | The chain where relevant; otherwise null |
| `data.transaction_hash` | The latest hash where relevant; otherwise null |
| `data.finality_state` | `not_submitted`, `pending`, `final` or `unresolved` (§16.3) |
| `data.payer` | The payer address for `processing`, `unknown`, `completed` and `failed` after a submission; otherwise null |
| `data.client_reference_id`, `data.mode`, `data.metadata` | Echoed to the merchant |

An event never carries a signature, a secret, an email or a seed (SX-10).

### 16.3 Finality

**`checkout.session.completed` is emitted only after the finality rule approved for the chain** (TR-16, TR-19): the receipt and the settlement event agree across at least two independent sources at the chain's finality threshold (TM-06). `finality_state = final` is set only then. **No per-chain finality rule is approved today** (OPN-15); a chain without an approved rule cannot be enabled for live mode, and this document sets no threshold.

| `finality_state` | Meaning |
|---|---|
| `not_submitted` | No transaction was submitted (`open`, `expired`, `cancelled`, and a `failed` that ended before a submission) |
| `pending` | A transaction was submitted and is not final (`processing`) |
| `final` | The outcome is final: `completed`, or a `failed` proven by a final revert or by proven non-settlement |
| `unresolved` | `unknown`: the outcome is not yet known |

### 16.4 Delivery

| ID | Rule |
|---|---|
| WH-01 | **HMAC signature.** Every request carries a header `FastPay-Signature: t=<unix seconds>,v1=<hex>`, where `v1` is the HMAC-SHA-256, under the endpoint's secret, of the string `t`, a full stop and the raw body (TB-12, PB-021). A merchant verifies it on the raw body with a constant-time comparison |
| WH-02 | **Replay window.** A merchant rejects a request whose `t` differs from its clock by more than 5 minutes (a proposal, not an approved value). FastPay re-signs every retry with a fresh `t`, so a retry is not a replay |
| WH-03 | **Retry behavior.** A response other than 2xx within the timeout is retried with exponential backoff and jitter for up to 72 hours (proposed). An endpoint that keeps failing trips a circuit breaker; events then wait in a dead letter that the merchant's dashboard shows and can replay |
| WH-04 | **Deduplication.** Delivery is at least once. The merchant deduplicates by `id`; a retry carries the same `id` and the same body apart from the signature timestamp |
| WH-05 | **Ordering limitations.** Order is **not guaranteed.** The merchant applies an event only if `data.session_version` is higher than the last one it applied for that session, and treats `completed`, `failed`, `expired` and `cancelled` as final. `unknown` can be followed by `completed` or `failed`. `processing` can arrive after `completed` and must then be ignored |
| WH-06 | **Egress.** Delivery goes through the egress proxy with a deny-list of internal ranges, to HTTPS endpoints only (TB-12) |
| WH-07 | **Secrets.** One secret per endpoint, rotatable, with an overlap in which both secrets are accepted |
| WH-08 | **Live and test** use separate endpoints and secrets |
| WH-09 | **Fulfilment rule.** A merchant fulfils on `completed` only. It never fulfils on `unknown`, `processing` or any redirect |

## 17. `FAILED` versus `UNKNOWN`

### 17.1 `FAILED`

`FAILED` is a state in which **FastPay has positive evidence that no successful payment occurred.** The evidence is one of these five classes:

| ID | Evidence |
|---|---|
| FE-1 | The customer rejected before submission: the wallet returned an explicit rejection and nothing was broadcast |
| FE-2 | A deterministic pre-submission validation failed (the checks of §7.3, the account's eligibility, a closed gate) |
| FE-3 | A simulation definitively failed (a deterministic revert, [06 §3.2](06-initial-architecture.md)) |
| FE-4 | The transaction reached a final reverted state: a revert seen from at least two independent sources at the finality threshold |
| FE-5 | Protocol state proves that the payment id was not settled and cannot settle: past the intent's deadline and the finality threshold, no settlement for `paymentId`, and every authorization issued for it expired or consumed |

**How the evidence becomes a session state.** The evidence classes define what may be called a failure. The **session** is `FAILED` only when, in addition, no further attempt is allowed: after a submission always (PX-08), and before a submission when the cause ends the session or the attempt limit is reached (TR-21, §2.3). When a new attempt is allowed, the attempt is recorded as failed with its `failureCode` and the session returns to `REVIEW_REQUIRED`; it is not `FAILED`. This is stricter than reading every failure as the end of the session; the sponsor should confirm it (OPN-16).

### 17.2 `UNKNOWN`

`UNKNOWN` is a state in which **a submission may have occurred and authoritative resolution is unavailable or inconsistent.** The causes are:

| ID | Cause |
|---|---|
| UE-1 | Broadcast uncertainty: the transaction may have left the process (including a wallet result that was lost) |
| UE-2 | An RPC timeout after submission |
| UE-3 | RPC providers disagree |
| UE-4 | The receipt is unavailable |
| UE-5 | Reorg uncertainty |
| UE-6 | Finality uncertainty |
| UE-7 | Indexer lag where direct chain evidence is not yet conclusive |

### 17.3 Rules

| ID | Rule |
|---|---|
| U-1 | `UNKNOWN` is **never displayed as `FAILED`**: not in the page, not in the API, not in a webhook (PX-12) |
| U-2 | `UNKNOWN` **does not permit payment fallback**: no other token, chain, wallet or path is offered (PX-08) |
| U-3 | `UNKNOWN` **does not permit a second payment for the same payment id**, on this chain or another |
| U-4 | **Merchants must not fulfil an `UNKNOWN` payment** (WH-09). The `unknown` event says so |
| U-5 | The hosted page says **not to pay again** ("We are confirming your payment. Do not pay again.") and shows no pay button |
| U-6 | **Reconciliation must resolve `UNKNOWN` to `COMPLETED` or `FAILED`** (TR-19, TR-20), and to nothing else |
| U-7 | Resolution relies on **authoritative chain and protocol state**: two independent sources at the finality threshold, the settlement event for `paymentId`, the account nonce, the router's settled record (TM-06, ER-09). An indexer alone, a single RPC, or the absence of a receipt is not enough |
| U-8 | **Every `UNKNOWN` transition and every resolution is audited** with its evidence (`unknown.entered`, `reconciliation.started`, `reconciliation.resolved`, §5.8) |
| U-9 | A session that has been `UNKNOWN` never has another attempt, even after it is resolved to `FAILED`: the customer starts a new session |

## 18. Session recovery

The page, the wallet and the connector are views and inputs; none of them is a source of truth for the state.

| ID | Event | What is recovered, and how |
|---|---|---|
| RC-01 | **Server-side session state is authoritative** | Every recovery below reads the state from the server by `id`; a client's memory of the state is never used |
| RC-02 | **Browser refresh** | The page reloads the state by `id`. A request still outstanding is not sent again (CP-10, CP-16); the customer sees "check your wallet" |
| RC-03 | **Tab closure** | Nothing is lost before a submission: the customer reopens the URL or scans code B. After a signature was recorded (`AUTHORIZED`) the executor submits without the customer. After a submission nothing depends on the page (§5.2) |
| RC-04 | **WalletConnect disconnection** | CP-07 to CP-09: automatic reconnection for a short time, then a new code A or another wallet. The session is the same; no request is re-sent |
| RC-05 | **Deep-link return failure** | CP-15: the same URL restores the session; the outstanding request, if any, is shown as outstanding; the page never assumes the return reached the same tab |
| RC-06 | **Mobile OS process termination** | As RC-05 and RC-02: the browser or the wallet app was killed; the session state on the server decides what the page shows when it comes back. A final-transaction request that was sent to the wallet keeps the session `SUBMITTING` (CP-14) |
| RC-07 | **Account change** | The unsigned request is invalidated; the quote and plan are discarded; **a new review screen is required** (TR-07, TR-10, QL-05) |
| RC-08 | **Chain change** | The unsigned request is invalidated; the quote is discarded; the page asks for a switch and shows a new review screen (CP-12, QL-05) |
| RC-09 | **Quote expiration** | The session stays open; a new quote replaces the old one (QL-04, TR-06); a new review screen is shown if the amount, token or recipient changed |
| RC-10 | **Duplicate browser tabs** | One controlling context at a time (§9.3). Another tab is a viewer. It cannot send a request (PX-07) |
| RC-11 | **Only one active signature request exists for a session revision** | PX-07, CP-10 |
| RC-12 | **Any account, chain, token, amount or recipient change invalidates the unsigned request and requires a new review screen** | QL-05 |
| RC-13 | **After a submission the recovery is reconciliation** | ER-09 and section 17; there is nothing for the customer to redo |

## 19. Security and privacy requirements

| ID | Requirement |
|---|---|
| SX-01 | **High-entropy session identifiers.** At least 128 bits from a CSPRNG (CS-2). **No session id is authentication** (CS-3, CS-4) |
| SX-02 | **No private keys or seed phrases.** The page, the API and every log never ask for, receive, generate or store one (CSD-04). A static scan of the checkout bundle finds no key-generation code |
| SX-03 | **CSP.** The hosted checkout is served from its own origin with a strict content security policy: scripts only from its own origin with SRI or nonces, no inline script, no third-party script, connections only to the FastPay API and the connector's relay, and violation reports (TB-02, PB-022). The wallet-connection library is a pinned, bundled dependency under PB-024, not a script loaded from a third party. No merchant code runs in the origin |
| SX-04 | **Frame policy.** Hosted checkout: `frame-ancestors 'none'` (and `X-Frame-Options: DENY`). Embedded checkout, if approved (§14.6): `frame-ancestors` limited to the origins the merchant registered, and a `postMessage` interface that checks the sender's origin |
| SX-05 | **Strict redirect validation.** RD-01, RD-03, RD-09 |
| SX-06 | **No wallet-address leakage before connection.** The customer-facing view of a session never contains `expectedCustomerWallet`, a payer, or any address; no address appears in a URL, a page title, an analytics event or a log line before the customer has connected a wallet; the mismatch message shows no address (§4) |
| SX-07 | **Referrer-Policy** `no-referrer` (CS-7) on every page |
| SX-08 | **No sensitive metadata in URLs.** The URL carries only the session id (CS-1); redirects carry only RD-03; `metadata` never leaves the merchant API and webhooks |
| SX-09 | **Session fixation protection.** The control token that binds a browser context to a session is generated by the server when the lease is taken, delivered in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie scoped to the checkout origin and the session, and **never accepted from the URL, a query parameter or a request body**. It is rotated at every connection and at `AUTHORIZED`. Taking the lease is evented and rate-limited (§9.3) |
| SX-10 | **No component can create or widen a customer's spending authority** (TM-01, TB-14). The checkout service requests signatures; it cannot sign for a customer. A held signature is stored encrypted, bound to its session and attempt, deleted once the session is terminal and the retention period has passed, never logged; an audit record holds only its hash. No event, log or audit record carries a signature, a secret or an email |
| SX-11 | **Log redaction.** Request bodies of the merchant API, wallet addresses, transaction payloads and `metadata` are redacted or hashed in operational logs; access logs do not record query strings |
| SX-12 | **CSRF protection where relevant.** Every state-changing call from the page requires the control token, an `Origin` header equal to the checkout origin and a custom header; the merchant API uses key authentication and no cookies, so it is not exposed to CSRF |
| SX-13 | **Origin binding for sign-in.** Any message the customer signs to prove control of an account (OPN-01) names the checkout origin, the session id, a server nonce and an expiry, and is verified for exactly those; a signature from another origin is rejected (TB-02). v1 has no other sign-in |
| SX-14 | **Rate limiting.** On session creation, session lookup, the lease, and the page's state-changing calls (MI-07); lookups of unknown ids are limited per source |
| SX-15 | **Abuse monitoring.** Alerts on scans of session ids, bursts of lease takeovers, bursts of cancels, creation of many sessions without a payment, redirect-validation failures, and webhook endpoints that return errors |
| SX-16 | **Retention policy.** Each class of data has a retention period set by the Privacy Lead (OPN-09); **no period is proposed here.** Held signatures are deleted first (SX-10) |
| SX-17 | **Optional analytics consent.** Analytics that go beyond what is necessary to operate and secure the checkout are **opt-in**, are off until the customer consents, and never identify a wallet across sessions (§4). Strictly necessary operational logs need no consent but follow SX-11 and SX-16 |
| SX-18 | **No email collection in v1** (CSD-08): the checkout has no email field, no "send me this link" and no customer contact data of any kind |
| SX-19 | **Failures are closed.** Ambiguity in authorization, quote validity, finality or transaction status creates no new payment (TM-11) |

**Data inventory.** The wallet address is treated as personal data (ASM-023).

| Data | Personal | Who sees it | Retention |
|---|---|---|---|
| `connectedWallet` and the payer in events | Yes | The session's merchant (in events), FastPay operations | Not set (OPN-09) |
| `metadata`, `clientReferenceId` | Merchant's own; may link to a person | Merchant | As the merchant's contract says; never shown to the customer |
| Network data of the page (IP, user agent) | Yes | FastPay security logs | Not set (OPN-09) |
| Signature (held until submitted) | Bearer until its deadline | The executor service | SX-10 |
| Transaction hash, token, amount, chain | Public chain data | Anyone | Chain |
| Pairing metadata at the relay | Yes (`UNVERIFIED`) | The relay operator | Unknown (OPN-08) |

**Excluded from v1:** collecting the customer's name, email, phone or postal address; any join of sessions across merchants; any profile built from a wallet address; any analytics that identifies a wallet across sessions.

## 20. Acceptance criteria

None of these criteria has been run, and no criterion that involves a wallet can pass without wallet-lab evidence. They are the conditions under which each behaviour of this specification counts as achieved. Unless stated otherwise they run in the test mode on a testnet, with a lab wallet, and each is checked against the audit log, the API and the chain.

| ID | Subject | Pass condition (all must hold) |
|---|---|---|
| AC-01 | Desktop browser-wallet payment (PO-1) | The audit log shows exactly the states `OPEN`, `CONNECTING`, `WALLET_CONNECTED`, `REVIEW_REQUIRED`, `AWAITING_SIGNATURE`, `AUTHORIZED`, `SUBMITTING`, `PROCESSING`, `COMPLETED`, with `sessionVersion` strictly increasing; exactly one signing request was issued; the chain shows exactly one `PayOnceSettled` for the `paymentId`; the merchant recipient received exactly `merchantAmount` and the fee recipient exactly `feeAmount`; the router's balance is unchanged; exactly one `completed` webhook with `finality_state = final` |
| AC-02 | Desktop-to-mobile WalletConnect payment | The checkout on a desktop shows code A labelled "Scan with your wallet"; the code contains no address and no session id; after the phone wallet connects and signs, the desktop session reaches `COMPLETED` with the same audit properties as AC-01; no key material or seed reached any FastPay component (a scan of logs and storage finds none) |
| AC-03 | Mobile deep-link payment | From a mobile browser, the wallet opens through the deep link and the customer returns; the session reaches `COMPLETED`; if the browser is killed once during the hop and reopened on the same URL, the session continues, **no second signing request** is sent for that revision, and `COMPLETED` is still reached |
| AC-04 | No-wallet exit | With no wallet available, the page shows NW-01 to NW-06; choosing "Return to merchant" ends the session as `CANCELLED` with `cancel_reason = no_wallet` and redirects to `cancel_url` with `{CANCEL_REASON}` replaced by `no_wallet` and nothing else added; exactly one `cancelled` webhook; no address, deposit QR, embedded wallet or on-ramp is offered |
| AC-05 | Expired quote refresh | With the quote past its `validUntil`, the pay button cannot start TR-08; a new quote replaces the old one in the same session (the old quote's status is `superseded`); there is never more than one active quote per `sessionVersion`; a new review screen is shown if any displayed value changed |
| AC-06 | Expired session rejection | After `expiresAt`, a new connection or a new signing request is refused (ER-01); the session is `EXPIRED`; exactly one `expired` webhook; no `completed` event can ever follow for it; held signatures are discarded |
| AC-07 | Submitted before expiry, finalized after | A transaction submitted before `expiresAt` and finalized after it ends as `COMPLETED`; the session is never `EXPIRED`, `CANCELLED` or `FAILED` in between; the audit log shows TR-13 before `expiresAt` and TR-16 after it; exactly one `completed` webhook is sent and no `expired` webhook |
| AC-08 | `UNKNOWN` handling | With an induced RPC disagreement or a missing receipt after submission, the session is `UNKNOWN`; the page says "Do not pay again" and shows no pay button; exactly one `unknown` webhook and no `failed` webhook; no second signing request is issued for the `paymentId` on any chain; every transition and the resolution are in the audit log; reconciliation ends in `COMPLETED` or `FAILED` and in nothing else |
| AC-09 | Duplicate payment prevention | (a) Two tabs on one session issue at most one signing request; (b) replaying the same authorization settles at most once (`markSettled` reverts the second); (c) after a submission, no new attempt can be created on any chain of the session (PX-08); (d) two sessions with the same `client_reference_id` are visible in the list endpoint (OPN-03 for the rest) |
| AC-10 | Browser refresh recovery | A refresh in every non-terminal state shows the same state, the same quote and the same outstanding request as before; no request is sent again; the state after the refresh equals the server's |
| AC-11 | Account-change invalidation | Changing the account in the wallet while `AWAITING_SIGNATURE` withdraws the request and discards the quote and plan; a signature for the old account that arrives later is never submitted; the session needs a new connection and a new review screen before any new request |
| AC-12 | Webhook completion | A `completed` event is emitted only after `finality_state = final` under the rule approved for the chain, carries a stable `id`, the `session_id`, the `payment_id`, the `chain_id` and the `transaction_hash`, and is signed per WH-01; before finality only `processing` was emitted |
| AC-13 | Webhook replay rejection | A reference verifier rejects an event whose `t` is outside the replay window, an event whose signature does not verify, and a second delivery with the same `id` as a duplicate |
| AC-14 | Merchant verification through the API | After the customer is redirected to `success_url`, an authenticated `GET` of the session returns the true state; a forged redirect to `success_url` for an unpaid session returns `open` or another non-complete state; the merchant's reference integration does not fulfil from the redirect |
| AC-15 | No deposit-address path | No endpoint, response field, page, QR code or string in the checkout returns or displays a receiving address for the session; code A decodes to the connector's pairing URI and code B decodes to the hosted URL only; a scan of the API and bundle finds no deposit-address feature |
| AC-16 | No embedded-wallet path | The connector list of v1 contains only the classes of §8.1; the API rejects any other connector; the bundle contains no wallet-creation, key-derivation or passkey-wallet code |

## 21. Required status updates

Only these artifacts are updated by this proposal. Each records the decisions as **proposed product decisions, not approved protocol evidence.**

| Artifact | Update |
|---|---|
| This document (19) | Rewritten to the 21 sections of the instruction (version 0.2.0) |
| Table of contents ([01](01-toc.md)) | Entries C.27 (this document), C.28 (API catalog), C.29 (event catalog), C.30 (configuration-record list), and a pointer from B.4 |
| Assumptions and decisions register ([03](03-assumptions-decisions-risks.md)) | ASM-037 to ASM-041; the proposed product decisions OD-038 to OD-044 |
| Risk register ([03](03-assumptions-decisions-risks.md) §5) | RISK-038 to RISK-044 |
| Proposed API catalog | [checkout/api-catalog.md](checkout/api-catalog.md) |
| Proposed event catalog | [checkout/event-catalog.md](checkout/event-catalog.md) |
| Configuration-record list for session lifetime | [checkout/config-records.md](checkout/config-records.md) (CSR-01) |
| Changelog ([CHANGELOG.md](CHANGELOG.md)) | The entry of 2026-10-17 |

**Not altered:** the Foundry evidence, the Permit2 evidence, the wallet-lab records and kit, the freeze-readiness status and its tool, every approved or proposed contract fingerprint (document 14 and `freeze_fingerprints.py`), the recorded test results, `eip712/types.json`, `config/pc_records.json`, documents 05, 06, 10, 11, 12, 13, 14, 15, 16, 17 and 18, and the README.

## 22. Evidence and status

### 22.1 What exists

This document adds **no** evidence. What exists is unchanged:

| Class | Status for the subject of this document |
|---|---|
| Reference model | No checkout session |
| FastPay contracts | `payOnceWithSignature` (PO-1, with PO-5's customer transaction before it), `markSettled`, the router and registries are built and tested ([REPORT.md](evidence/implementation/REPORT.md) §0a). PO-2, PO-3, PO-4, PO-6, `chargeInitial` and a typed charge request are not built |
| Permit2 rebuild and forks | The `SignatureTransfer` witness path passes on three chains |
| Wallet lab | **Nothing for this profile.** No run record exists for any wallet |
| Session service, connection layer, API, webhooks | Not specified in code; not built |

### 22.2 Wallet-lab coverage and gaps

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

### 22.3 Tests this specification requires (none exist)

State-machine tests for every transition of §5.2 and every prohibition of §5.3; a replay test for each idempotency rule; a clock test for ER-01 to ER-10; a cross-chain exclusivity test for PX-08; a test that the review screen equals the typed data (SX-03 and §7.2); a test that no URL carries data beyond the session id (CS-1); an open-redirect test on the URLs; a webhook signature, ordering and replay test (WH-01 to WH-05); the sixteen acceptance criteria of section 20. They are listed, not written, and no run result is recorded.

### 22.4 Reviews and sign-offs

| Review | Required by | State |
|---|---|---|
| Security review of the session, the lease, the webhook, the API and the connection layer | Head of Security | **NOT SIGNED** |
| Privacy review of section 19 and CSD-08 | Privacy Lead | **NOT SIGNED** |
| Wallet-lab evidence for section 8 | QA Lead | **none** |
| Source retrieval for CSU-01 to CSU-11 | Wallet Protocol Engineer | **not done** |
| Approval of CSR-01 | Payments PM, CISO, Privacy Lead | **NOT SIGNED** |

## 23. Conflicts and open points

| ID | Point | Why it matters | Owner |
|---|---|---|---|
| OPN-01 | **Using an existing mandate for a `PAYMENT`.** No typed confirmation or charge request exists (F-19), no mandate term or cycle allows a customer-present charge, and proof of control is missing. Without all three, an unproved address could trigger a charge of a victim's mandate | Blocks §11.A and GAP-08. If enabled later it changes `eip712/types.json` and the fingerprint of C-11 | Principal Architect, Wallet Protocol Engineer |
| OPN-02 | **State names and retry across documents.** [10 §4](10-pay-once-protocol.md) maps a user rejection to `CANCELLED`; [06 §3.2](06-initial-architecture.md) lists intent `CANCELLED`, has no `EXPIRED` or `FAILED` intent state, and allows a new attempt after a final revert, which this document does not (PX-08); its full tables (C.8) do not exist | The session states of §5.1 are the only complete model | Principal Architect |
| OPN-03 | **Two sessions for one order.** `markSettled` is per `paymentId` and per chain; a merchant that creates two sessions for the same `clientReferenceId` can be paid twice. The session prevents it only inside one session (PX-08) | Merchant-level uniqueness of `clientReferenceId` is not specified; the list endpoint helps detect it | Merchant PM, Payments Core lead |
| OPN-04 | **Control lease takeover** by a person who holds the URL (SX-09) | Griefing, not theft | Head of Security |
| OPN-05 | **No value** for `MIN_SIGN_WINDOW`, `sigTtl` of a payment, or the attempt limit per session ([10 §9](10-pay-once-protocol.md) point 3) | The guards of TR-08, TR-21 and §5.5 need them; each would be a constant needing its own record | Product Designer |
| OPN-06 | **Telling a customer about a charge or a failed charge** when v1 collects no email | §11.B | Product, Privacy Lead |
| OPN-07 | **Gas sponsorship** for customers without native gas (ASM-018), and who bears the executor's gas for Pay Once | §10.8 | Payments PM, Finance |
| OPN-08 | **Who operates the relay**, what it sees, and whether FastPay runs its own (UI-09 asks for its own project id) | Privacy and availability | Head of Security, Privacy Lead |
| OPN-09 | **Retention periods** of sessions, logs, held signatures | §19 | Privacy Lead |
| OPN-10 | **Approval of the three bounds** of CSR-01 | §6 | Payments PM, CISO, Privacy Lead |
| OPN-11 | **`SETUP` mode** (reserved): what it is for (a fix-payment page after a failed charge, a mandate update) and whether it is a session or something else | §3 | Product |
| OPN-12 | **Deterministic ids from the session** (`paymentId`, the activation's creation nonce) so that reconciliation can find a transaction whose result was lost | §10.11, CP-14 | Solidity Lead, Payments Core lead |
| OPN-13 | **Cross-chain choice.** A session that allows several chains lets the customer choose one; PX-08 forbids a second chain after a submission. Whether a multi-chain session is offered in v1 at all is a product decision | §2.1 | Merchant PM |
| OPN-14 | **Vetting of the external-wallet list** (§12 NW-02): the criteria, who maintains it, how it is kept apart from a support claim | Customers without a wallet | Product Designer, Head of Security |
| OPN-15 | **The finality rule per chain** that `completed` waits for. None is approved; a chain without one cannot be enabled for live mode | §16.3 | Principal Architect, Chain Infra Lead |
| OPN-16 | **When a failure ends the session.** This document ends it only when the evidence of §17.1 exists **and** no further attempt is allowed, so a rejected prompt or a failed simulation returns the session to `REVIEW_REQUIRED`; the sponsor should confirm that reading | §17.1 | Sponsor, Product |
| OPN-17 | **The numbers of the proposed API and events** (metadata limits, the replay window, the retry schedule, the idempotency window, the length limits) are proposals and approved by nobody | §14.2, §16.4 | Payments Core lead, Merchant PM |

If the sponsor accepts this proposal, the next steps are those of §22.4 (Security and Privacy review, source retrieval for CSU-01 to CSU-11, a decision on GAP-01 to GAP-08) and the closing of OPN-01. None of them is scheduled here.
