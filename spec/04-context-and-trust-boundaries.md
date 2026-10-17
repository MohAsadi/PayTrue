# 04 — Context Diagram and Trust-Boundary Model

| Field | Value |
|---|---|
| Artifact | FP-SEC-001 (Part C.1, G.1 v0) |
| Version | 0.4.0 |
| Status | DRAFT |
| Owner | Principal Blockchain Architect |
| Reviewers | Head of Security, Wallet Protocol Eng, Principal Backend Architect |
| Dependencies | [02](02-source-register.md) CLM-005/006/011/013/016/025/026/050/051/052; [03](03-assumptions-decisions-risks.md); [09](09-capability-boundaries.md)–[13](13-eip7702-delegation-inspection.md) |
| Labels | `SECURITY-CRITICAL` |
| Definition of Done | Every boundary has threats, controls, failure behavior, and a test; every principal has an authority-matrix row; Security signs that no row grants customer-fund movement outside the bounded charge path. |

## 1. Context diagram

```text
                            +----------------------------------------------------------------+
                            | Z8  GOVERNANCE AND KEY CUSTODY                                  |
                            |  Governance multisig + timelock    Guardian multisig (stop only)|
                            |  HSM/KMS: executor, charge, QUOTE, webhook, CI signing keys      |
                            +----------+----------------------------------+------------------+
                       timelocked txs  |                                  | signing policy
                                       v                                  v
+--------------------+ EIP-1193 / WalletConnect  +--------------------------------------------+
| Z0 CUSTOMER        |<------------------------->| Z1 FASTPAY WEB                              |
|  Wallet: EOA,      |  typed data, wallet_*     |  hosted checkout, embedded SDK, mandate     |
|  7702-delegated,   |  calls, tx prompts        |  portal.  UNTRUSTED FOR INTEGRITY:          |
|  smart account     |                           |  the wallet is the consent surface          |
|  (+ hardware dev.) |                           +----------------------+---------------------+
+----------+---------+                                                  | HTTPS, SIWE session
           | customer-signed txs                                        v
           | and signatures        +---------------------------------------------------------------+
           |                       | Z3 FASTPAY CONTROL PLANE                                      |
           |                       |  API gateway                                                  |
           |                       |  Core (modular): merchant, customer, mandate, payment         |
           |                       |    orchestrator, subscription, quote/routing, token registry, |
           |                       |    ledger, risk, refunds, notifications, reporting, admin,    |
           |                       |    delegation inspector, migration orchestrator, flags        |
           |                       |  Chain Gateway: indexer, broadcaster, finality/reconciliation |
           |                       |  Signer | Quote-signer (own key class) | Webhook dispatcher |
           |                       +---+-----------+------------+-------------+--------------------+
           |                           |           |            |             |
           |              API keys,    |  sign     |  RPC,      |  KYB,       | signed webhooks
           |              webhooks in  |  requests |  quotes    |  sanctions  | (egress)
           |                           v           v            v             v
           |               +---------------+ +----------+ +-----------------+ +---------------+
           |               | Z2 MERCHANT   | | Z4       | | Z7 THIRD-PARTY  | | Z9 COMPLIANCE |
           |               |  backend,     | | EXECUTOR | |  RPC providers, | |  VENDORS      |
           |               |  dashboard    | | hot keys | |  indexers, quote| |  KYB, AML,    |
           |               +---------------+ | (via Z3  | |  and oracle     | |  sanctions    |
           |                                 |  signer) | |  providers      | +---------------+
           |                                 +----+-----+ +--------+--------+
           v                                      v                v
+------------------------------------------------------------------------------------------+
| CHAIN  (one deployment per chain id; contract set identical in behavior across EVM chains)|
|                                                                                          |
|  Z6 EXTERNAL ON-CHAIN (untrusted code)       Z5 FASTPAY CONTRACTS (trust root)           |
|   ERC-20 tokens                              PaymentRouter (immutable)                   |
|   Permit2                                    MandateManager      MerchantRegistry        |
|   DEX routers (ABSENT in v1.0)              TokenPolicyRegistry ExecutorRegistry        |
|   7702-delegated account code (persistent)   FeeController       RefundManager           |
|                                              EmergencyGuardian   DEXAdapterRegistry      |
|                                              RouterRegistry (lifecycle, shared settled)  |
+------------------------------------------------------------------------------------------+
```

### 1.1 Principals

| Principal | Zone | Holds | Can be compromised by |
|---|---|---|---|
| Customer | Z0 | Wallet keys; tokens | Phishing, malicious page, malware, delegation scams |
| Merchant user | Z2 | Dashboard session, API keys | Credential theft, insider |
| Merchant `chargeSigner` | Z3/HSM or Z2 (OD-003) | Key authenticating charge requests | Backend compromise, merchant compromise |
| Executor | Z4 | Hot key that pays gas and submits txs | Signer-service compromise, key exfiltration |
| Quote signer (key class `quote`) | Z3/HSM | Signs `PriceQuote` only; cannot move funds | Service compromise, price-source manipulation |
| Quote/route provider | Z7 | Nothing on-chain | Malicious or manipulated quotes |
| Risk service (`RiskPauser` role) | Z3 | Can pause mandates, never widen | Service compromise |
| Guardian (multisig, stop-only) | Z8 | Stop-only powers: pause recurring or Pay Once, disable a token, executor or quote signer, emergency-disable a router (from v1.1 also close a conversion class); it cannot unpause, enable or move funds | Signer collusion or coercion; use of the stop powers as a denial of service |
| Governance | Z8 | Multisig behind timelock | Signer collusion or coercion |
| FastPay staff | Z3 consoles | JIT roles, no on-chain fund powers | Insider, phishing |
| Token issuer | Z6 | May freeze, pause, upgrade a token | Issuer decision or compromise |
| Permit2 | Z6 | Immutable singleton the customer already trusts | Latent bug (low likelihood, high impact) |
| Wallet-installed EIP-7702 delegate | Z0/Z6 | Code the wallet installed in the customer's account; **persistent** until replaced or cleared | Wallet defect, hostile delegate, drift ([13](13-eip7702-delegation-inspection.md)) |

## 2. Trust zones

| Zone | Trusted for | Not trusted for |
|---|---|---|
| Z0 Customer wallet | Authoritative statement of customer intent (after the customer reads the wallet prompt) | Capability self-reports (CLM-005 unauthorized → unknown), UI fidelity on hardware devices (ASM-007), **the identity of the code behind an upgraded account (inspect and record, never infer)** |
| Z1 FastPay web | Convenience, orchestration | **Integrity**: a compromised or spoofed page must not be able to obtain a harmful approval that the wallet displays as harmless |
| Z2 Merchant | Authentication of the merchant's own business intent | Anything touching customer funds beyond the active mandate |
| Z3 Control plane | Scheduling, quoting, risk, bookkeeping, orchestration | Being the **only** enforcement point of any financial limit |
| Z4 Executor | Liveness (submits transactions) | Choosing amounts, recipients, or tokens outside a signed request |
| Z5 FastPay contracts | Enforcement of mandate, caps, recipient, once-per-cycle, min output | Nothing beyond what is audited and immutable |
| Z6 External contracts | Their documented standard behavior, as measured | Metadata, callbacks, upgrade behavior, fee/rebase behavior unless registry-vetted |
| Z7 Third-party infrastructure | Hints and convenience | Correctness of any single response |
| Z8 Governance and keys | Slow, deliberate, widening changes | Fast changes, single-person action |
| Z9 Compliance vendors | Screening signals | Final decisions without human review for high-impact actions |

## 3. Trust model statements

Each statement is a testable invariant of the design. IDs are cited by requirements and tests.

| ID | Statement | Why |
|---|---|---|
| TM-01 | Only a customer-originated transaction, or a customer EIP-712 signature verified on-chain (ECDSA or ERC-1271, CLM-032), can create or widen spending authority. | A server or role that can create authority is a custodian. |
| TM-02 | The chain is the sole authoritative enforcement point for limits. Off-chain checks can only be stricter, never looser. | Prompt §17: the scheduler must not be the sole enforcement point. |
| TM-03 | No role has a function that moves customer tokens other than the router's charge path, which requires an active mandate. No sweep, rescue, or arbitrary-call exists (CF-002, CF-006). | Prompt §4. |
| TM-04 | Every signature binds `chainId`, `verifyingContract`, spender or agent, nonce or id, amount, deadline and, for FastPay data, `termsHash`. | Replay and phishing resistance (RISK-021). |
| TM-05 | Security does not depend on the FastPay page being honest. The page may only request signatures of **typed, named-field data** a wallet can render; it never requests `eth_sign`, `personal_sign` over opaque hashes, or unlimited approvals to non-Permit2 spenders. | Z1 is untrusted for integrity. |
| TM-06 | A chain fact used for a money decision (balance at charge, receipt, finality) is accepted only after agreement of ≥2 independent sources at the chain's finality threshold. A single source is a discovery hint. | RISK-015; CF-008. |
| TM-07 | Quotes and routes are proposals. The contract verifies outcomes (caps, minimum output, recipient), never the proposer. | Untrusted providers. |
| TM-08 | Token contracts are untrusted code. Only registry-listed (chainId, address, bytecode hash, implementation hash) tokens are chargeable, and balance deltas are measured, not assumed. | Prompt §10. |
| TM-09 | Time is coarse. `block.timestamp` bounds deadlines and cadence only; the system tolerates skew within a configured bound and never uses time as an entropy source. | Validator-controlled timestamps. |
| TM-10 | Keys are scoped by class: executor (submit only), `chargeSigner` (authenticate requests), **`quote` signer (attest prices within bounds only)**, guardian (stop), governance (widen, delayed), deployer (renounced after deployment). Compromise of one class cannot escalate into another. | Least privilege. |
| TM-11 | Failure is closed: ambiguity in authorization, token behavior, quote validity, contract identity, finality or transaction status produces no new charge. | Prompt §4/§11. |
| TM-12 | Merchants are authenticated but untrusted with respect to customer funds, and merchant tenants cannot see or affect each other. | Tenant isolation (TB-15). |
| TM-13 | Every privileged or widening change is evented, detected, and delayed by a timelock; stop-only actions are immediate. | Asymmetric delay. |
| TM-14 | A customer can always exit: mandate revoke/pause on `MandateManager` and Permit2 `lockdown` (CLM-026) are never blocked by pause, governance, or any FastPay component. | CF-003; ADR-010. |
| TM-15 | A price attestation can distort only fiat accounting, and only inside registry-held bounds; no quote can raise a per-token hard cap, extend a mandate, or change a recipient ([11](11-dual-cap-model.md)). | Dual cap model; blast radius B2/B4. |
| TM-16 | EIP-7702 delegation is persistent account state. FastPay never creates authorizations; it inspects and records the delegate, treats it as an input to flow selection, and never describes it as temporary ([13](13-eip7702-delegation-inspection.md)). | CLM-016. |
| TM-17 | **A feature flag or any backend switch is never a security boundary.** Capabilities that move funds in a new way (conversion, Draft-standard adapters, signature transports for code-bearing accounts) exist only in router versions whose code contains them and are reachable only through the customer's **router-specific authorization**; on-chain registry state is authoritative; rollout switches can only narrow ([09 §4](09-capability-boundaries.md)). Router v1 contains no conversion code. | Correction 1; ADR-013. |
| TM-18 | Account changes stop charges. The chain refuses a charge unless the customer account's code still matches the customer's pin (`AccountCodeChanged`), and before every unattended charge the backend revalidates what the chain cannot see; a difference blocks the attempt and pauses the mandate (`DELEGATION_UNVERIFIED`). Only the customer can update the pin, and updating it never widens authority ([17](17-account-compatibility-policy.md)). | An account that changed is a different risk; the customer, not FastPay, decides whether to keep paying from it. |
| TM-19 | A quote signer cannot override a mandate: the acceptance of a charge is the conjunction of guards G1…G12, none of which reads the quote, plus the fiat guard which reads it; a quote can only reject or, inside registry bounds, shift fiat accounting ([11 §4.8](11-dual-cap-model.md)). | The signer key class must be the weakest trusted component without being able to widen anything. |

## 4. Trust boundaries

| TB | Boundary | Data crossing | Primary threats | Required controls | Failure behavior | Test |
|---|---|---|---|---|---|---|
| TB-01 | Customer wallet ↔ FastPay web (EIP-1193, WalletConnect) | Account, chain id, **self-reported** capabilities, signatures, tx hashes | Page lies about what is signed; wallet misreports capabilities (RISK-004); look-alike domains; WalletConnect session hijack | Typed data only (TM-05); `termsHash` in every signed payload and recomputed server-side from the displayed terms; capabilities used as hints and re-verified after execution (`atomic` field, chain state); verified-domain badge and pinned origins; WalletConnect verify context | Unknown capability → legacy path; hash mismatch → refuse to proceed | Planner golden vectors; hostile-wallet fixture; terms-hash mismatch test |
| TB-02 | Browser ↔ FastPay API | Session, requests | XSS, CSRF, session theft, enumeration | Sign-in with wallet session bound to origin; strict CSP, SRI, no third-party scripts in checkout; rate limits | Reject, no partial state | DAST; CSP report review |
| TB-03 | Merchant systems ↔ API gateway | API requests, inbound callbacks | Key theft, replay, tenant escape, forged merchant callbacks | Scoped, hashed, rotatable keys; idempotency keys on every mutating call; request signing option; IP allowlist option; per-tenant authorization on every object | 401/403, never fall through to default tenant | Authz matrix tests; tenant-fuzz |
| TB-04 | Core ↔ Chain Gateway ↔ Signer | Charge/activation intents, signed txs | Compromised service crafting arbitrary transactions | Signer accepts **structured intents only**; allowlisted contract + selector; `value=0`; per-key amount/velocity ceilings; no free-form calldata; two-person change control on signer policy | Signer refuses; alert | Signer policy tests; red-team |
| TB-05 | Signer ↔ HSM/KMS | Sign requests | Key export, policy bypass | Non-exportable keys; IAM scoped per key class; CloudTrail-class audit; dual-control key policy changes | Signing disabled | Key ceremony rehearsal |
| TB-06 | Chain Gateway ↔ RPC and indexer providers | Chain data | Equivocation, lag, censorship, eclipsing | ≥2 independent providers + own node for critical reads (TM-06); quorum rule; staleness checks; chain-id verification on every call | Money decisions pause (state `UNKNOWN`); RB-004/005 | Chaos: provider returns wrong data |
| TB-07 | Executor ↔ public mempool | Transaction bytes | Front-running, MEV, copy-cat submission, nonce griefing | No secrets in calldata; request commitments bound to a single outcome; private relay option; nonce manager with gap detection; signed `ChargeRequest` can't be altered | Re-simulate; stuck-nonce runbook (RB-008) | Fork test with adversarial mempool |
| TB-08 | Router ↔ tokens and Permit2 | Calls to external code | Reentrancy via token hooks; non-standard returns; fee-on-transfer; blacklists | Reentrancy lock; safe transfer library; balance-delta checks; registry bytecode-hash check; ERC-777-like and rebasing tokens `BLOCKED` (ASM-022) | Revert whole payment | Token lab; invariant I-ZEROBAL |
| TB-09 | Router ↔ conversion adapters (**ABSENT in v1.0**; Router v1.1+) | Typed route parameters | Arbitrary-call, sandwiching, malicious route | v1.0: **absence** (no code, mechanical check PB-040). v1.1+: typed adapter interface, fixed selectors, registry-listed targets (CF-002); `minOut` by balance delta; price-impact cap; separate audit; conditions C1, C2 | v1.0: not applicable. v1.1+: revert; fallback is a new attempt | v1.0: absence checks. v1.1+: adapter fuzz; fork sandwich test |
| TB-10 | Governance ↔ contracts | Config txs | Admin abuse, upgrade abuse | Multisig + timelock for widening; Guardian stop-only; events; detection on every admin call; no role can touch customer funds (TM-03) | n/a | Role-matrix test; detection test |
| TB-11 | Control plane ↔ compliance vendors | KYB/AML data | Over-sharing PII; vendor breach | Data minimization; DPAs; pseudonymized wallet screening requests; region constraints (OD-020) | Fail closed for onboarding; manual queue | Privacy review |
| TB-12 | Webhook dispatcher ↔ merchant endpoints (egress) | Signed events | SSRF to internal services; spoofed webhooks; replay | Egress proxy with deny-list for internal ranges; HMAC with timestamp and replay window; secret rotation; per-endpoint circuit breaker | Retry with backoff; dead-letter | SSRF tests; replay tests |
| TB-13 | CI/CD ↔ production | Artifacts, deploys | Supply-chain compromise, secret leakage | Pinned dependencies, SBOM, signed artifacts, build provenance, OIDC-federated short-lived deploy credentials, two-person review | Block deploy | Provenance verification gate |
| TB-14 | Staff ↔ admin consoles | Admin actions | Insider abuse, phishing | JIT access, hardware keys, masked PII by default, every action audit-logged, **no console action can change on-chain customer authority** | Deny | Access review; break-glass drill |
| TB-15 | Tenant ↔ tenant | Rows, objects | Cross-tenant read/write | Tenant id in every key; row-level security; per-tenant encryption context | Deny | Tenant-fuzz in CI |
| TB-16 | Quote service ↔ quote-signer ↔ chain | Price requests, signed `PriceQuote` | Price-source manipulation, signer compromise, replay across payments | Dedicated key class and service; signer policy (sources ≥2, tolerance, TTL ≤ registry max); contract checks binding, TTL, bounds, round-up valuation; guardian removes a signer | No quote → no fiat-capped charge (fail closed) | CAP-TV; malicious-signer property tests |
| TB-17 | Migration campaigns ↔ customers | Notices, authorization screens, typed data | Phishing that imitates migration, forged notices, consent fatigue | Official channels only; the **router-specific authorization** shows `newRouter`, its code hash and explorer link; typed data with named fields; the migration explicitly includes revoking the old permission; halting criteria; published verification page ([12 §11](12-router-lifecycle-and-migration.md)) | Halt prompting | Comprehension tests; phishing drill |
| TB-18 | Wallet-installed delegate ↔ FastPay | Account code, ERC-1271 responses | Hostile or drifting delegate; always-valid `isValidSignature`; gas griefing | Inspection record, probe, allowlist at E3, per-signature pre-flight, drift detection ([13](13-eip7702-delegation-inspection.md)) | Restrict or refuse; `msg.sender` flows only | Hostile-delegate fork tests |

## 5. Authority matrix — who can do what to customer funds

`Y` can; `N` cannot; `B` bounded (conditions in the note). This matrix is the **source of truth** for access control design; a contract role that is not here does not exist.

| Principal | Move customer tokens | Choose recipient | Create or widen authority | Revoke or narrow authority | Stop new charges | Resume charges | Enable tokens, adapters, executors | Change fee | Register new router version | Read customer PII |
|---|---|---|---|---|---|---|---|---|---|---|
| Customer | N (own wallet only) | N | **Y** (own wallet only) | **Y** (own, never pausable) | Y (own mandates) | Y (own mandates) | N | N | N | Own data |
| Merchant (API) | **B**: can request a charge only inside an active mandate | N (recipient comes from `MerchantRegistry`, OD-022) | N | N (cancelling a subscription stops future requests) | N | N | N | N | N | Own customers only (minimum fields) |
| `chargeSigner` | **B**: authenticates requests; cannot exceed mandate caps | N | N | N | N | N | N | N | N | N |
| Quote signer | **B**: none directly; attests a price inside registry bounds for a charge someone else submits | N | N | N | N | N | N | N | N | N |
| Executor | **B**: submits; cannot alter signed parameters | N | N | N | N | N | N | N | N | N |
| Quote provider | N | N | N | N | N | N | N | N | N | N |
| Risk service (`RiskPauser`) | N | N | N | N | Y (pause a mandate or merchant; **set the delegation pause bit**) | Y (return to what the customer authorized, never more; clear the delegation bit only after the §7.5 conditions) | N | N | N | Limited |
| Guardian | N | N | N | N | **Y** (pause recurring, Pay Once, or a conversion class; disable token, adapter, executor, quote signer; emergency-disable a router) | N (cannot unpause) | N | N | N | N |
| Governance (multisig + timelock) | N | N | N | N | Y | Y (after delay) | **Y** (new items only: tokens, adapters, signers; from v1.1 opening a conversion class in `ConversionPolicyRegistry`; cannot widen an existing mandate) | **B**: within immutable ceiling (OD-016) | **Y** (register/activate/deprecate/sunset routers with immutable minimum notice; no mandate moves without the customer's router-specific authorization) | N |
| Deployer | N | N | N | N | N | N | N | N | N (renounced after deployment) | N |
| FastPay staff | N | N | N | N | via Risk/Guardian only | via Risk only | N | N | N | JIT, masked |
| Token issuer (external) | **Y** by freezing or upgrading a token — outside FastPay control | | | | | | | | | |
| Permit2 (external) | Immutable code the customer already trusts | | | | | | | | | |

Review rule: any change that turns an `N` into `Y` in columns 1–3 or 6–9 needs an ADR and Security sign-off.


## 6. Untrusted input catalogue

| UI | Input | Threat | Validation rule | On failure |
|---|---|---|---|---|
| UI-01 | Wallet-reported address, chain id, capabilities | Spoofing, stale or false claims | Address checksummed; chain id equals requested chain and re-read via RPC; capabilities normalized to a closed enum; `4100` → `UNKNOWN` | Legacy path or refuse |
| UI-02 | Token metadata (name, symbol, decimals, logo) | Spoofing, malicious decimals | Never used for identity (identity = chainId + address); decimals read from contract and compared with registry; display from registry only | Block token |
| UI-03 | Quotes and routes | Manipulated prices, malicious targets, replay | Provider allowlist; `PriceQuote` bound to `paymentId`, token and exact `amountIn`, signed by a registered signer, TTL-limited, price inside bounds ∩ mandate snapshot; adapter target allowlist | Discard quote |
| UI-04 | Merchant order data (amount, currency, metadata, URLs) | Tampered amounts, open redirect, injection | Amount integer atomic units + currency enum; server-side price lookups; URL allowlist per merchant; metadata size/field limits | 400 |
| UI-05 | Inbound callbacks and webhooks (from vendors) | Spoofing, replay | Signature verification; timestamp window; idempotency by event id | Drop and alert |
| UI-06 | Signatures | Replay, malleability, wrong domain | EIP-712 domain with chainId and verifyingContract; s-value normalized; nonce/ID unused; ERC-1271 checked by `STATICCALL` with no state change and **no artificially low gas cap** (CLM-032: callers should not hard-code gas); executor pre-flight `eth_call` bounds cost before submission; per-account gas anomaly detection | Revert |
| UI-07 | RPC responses | Equivocation, lag, wrong chain | Chain-id check; ≥2 sources for money decisions; block-hash continuity | `UNKNOWN` |
| UI-08 | Third-party indexer responses | Omissions, lag | Discovery only (CF-008); every balance or allowance re-read from chain before use | Ignore |
| UI-09 | WalletConnect proposals, deep links | Session hijack, malicious dapp metadata | Session metadata displayed from verified context; our own relay project id; no autoconnect | Reject |
| UI-10 | Merchant-supplied recipient changes | Payout redirection | Delay + two-party approval + events (OD-022) | Pending change |
| UI-11 | Uploaded KYB documents | Malware, PII leakage | AV scanning, content-type checks, isolated storage, encryption | Quarantine |
| UI-12 | Customer-entered addresses (refund address, notification contact) | Typos, poisoning | Checksum validation, confirm step; refunds go to the payer address by default | Reject |
| UI-13 | Account code and delegate behavior | Unknown or hostile delegate; stale observation | ≥2 RPC sources at one block; delegate code hash and allowlist match; `isValidSignature` probe; record TTL 5 minutes; drift detection | Restrict or refuse |

## 7. What the customer must trust (residual trust, shown in the product)

1. Their wallet software and device.
2. The chain's consensus and finality.
3. The token contracts they choose to pay with (including issuer freeze or upgrade powers).
4. Permit2 (a widely used immutable singleton; verified per chain, EV-P01).
5. FastPay's `PaymentRouter` and `MandateManager` **at the audited, immutable version named in the mandate**, which is the only code that can use their allowance.
6. That the merchant delivers the goods or service (not a protocol property; refund and mediation path in OD-007/OD-018).

Items 3–5 are surfaced in the mandate portal in plain language (B.7).

## 8. Open issues in this model

| # | Issue | Link |
|---|---|---|
| 1 | Hardware wallets may not render typed data meaningfully; consent copy placement depends on RP-21. | ASM-007 |
| 2 | Whether Permit2 supports ERC-1271 owners and witness transfers exactly as assumed has not been verified from source. | EV-P06 |
| 3 | The `RiskPauser` role must be able to pause per merchant and per mandate cheaply; gas cost of mass pause needs a merchant-level switch in `MerchantRegistry`. | D.1 |
| 4 | Key-class separation for the Signer service needs the HSM capability matrix. | RP-15 |
