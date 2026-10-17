# 15 — Wallet Lab Matrix

| Field | Value |
|---|---|
| Artifact | FP-QA-004 |
| Version | 0.5.0 (0.3: new; 0.4: account modes, pin tests WL-32…WL-35, exact freeze evidence in [16 §9](16-freeze-decision-report.md); 0.5: tests WL-36…WL-40 for the `AccountPin` struct, the delegate code hash, wallet-version changes, FastPay typed data under ERC-1271 and the shared allowance) |
| Status | DRAFT — **nothing in this document has been run**; every wallet row is `UNTESTED`, Trust Wallet is `UNKNOWN` |
| Owner | QA Lead (lab), Wallet Protocol Engineer (test design) |
| Reviewers | Principal Blockchain Architect, Head of Security, Product Designer |
| Dependencies | [02](02-source-register.md) EV-P03, EV-P07…P11, RP-05/06/21/25/27/28; [05](05-evm-authorization-decision-tree.md) §3, §10, §11; [10](10-pay-once-protocol.md); [11](11-dual-cap-model.md) §8; [12](12-router-lifecycle-and-migration.md) §5; [13](13-eip7702-delegation-inspection.md); [17](17-account-compatibility-policy.md) |
| Definition of Done | Every wallet row names its platforms, account types and the test sets it must pass; every test has a procedure, a pass criterion, the evidence to capture and the field or gate it feeds; every account the lab creates is classified into an Account Compatibility Policy mode by the predicates of [17 §2](17-account-compatibility-policy.md) and its pin is recorded; the verdict is a deterministic function of recorded runs; no wallet is described as supported without an E3 row inside its retest window. |

**Rule.** Vendor documentation is the *vendor says* column and never a FastPay claim. FastPay's support statement for a wallet is computed from lab runs by §5 and is shown to merchants and customers only for rows at **E3** that are inside their retest window. MetaMask's documentation is `documented` (CLM-040/043, E1); its lab verdict is `UNTESTED`. Trust Wallet is `UNKNOWN`: no documentation was found (G-04), and absence of evidence is not evidence of absence.

## 1. Scope and cost

| Item | Value |
|---|---|
| Purpose | Produce Compatibility Register rows ([05 §10](05-evm-authorization-decision-tree.md)) with raw evidence; discover what the planner flags (`atomic`, `sig1271`, upgrade behavior, hardware path) are allowed to be |
| Where it gates | **R3 testnet alpha:** the minimum set (§6, column R3). **R6 private beta:** full set for every claimed wallet (RG-003, PB-008, PB-009, PB-043). **Public beta and GA:** rows added per wallet only with their own evidence |
| Chains | Sepolia, Base Sepolia, Arbitrum Sepolia (testnets). Mainnet only as a low-value canary after RG-005/RG-006, to confirm that a testnet result transfers (wallets may differ between networks) |
| Effort in the plan | `EPIC-P0-WALLETLAB` (the lab and first matrix, Phase 0) and `W_WALLET_E3` (24 pw, E3 re-runs on the real build during alpha); see [07](07-delivery-plan.md) |
| Safety | Test keys only on lab devices; no production secrets; no real customer accounts; funds limited to faucet and canary amounts; evidence is redacted before storage |

## 2. Dimensions

### 2.1 Wallets (rows), in priority order

| Priority | Wallet | Platforms | Vendor says (source, level) | FastPay verdict |
|---|---|---|---|---|
| L0 | MetaMask | Chrome extension; iOS; Android | **Documented, E1 (CLM-040/043):** EIP-5792 with `atomic` `supported`/`ready` per account and chain; upgrade to a MetaMask smart account through EIP-7702 when `ready`; `wallet_sendCalls` atomic-only; listed networks include Ethereum, BNB Smart Chain, OP, Base, Polygon, Arbitrum; **Avalanche not listed**; the delegate is not named and persistence is not stated | `UNTESTED` |
| L0 | Coinbase Wallet / Base Account (smart wallet) | Browser, iOS, Android | Listed as an EIP-5792 wallet (CLM-041, E1); spend-permission module exists (CLM-042, E0) | `UNTESTED` |
| L0 | Safe{Wallet} (contract account) | Web | Listed (CLM-041, E1) | `UNTESTED` |
| L0 | **Trust Wallet** | iOS; Android; extension | **No documentation found (G-04)** | **`UNKNOWN`** |
| L1 | Rainbow, Rabby, Phantom (EVM) | Extension and/or mobile | Not mentioned (CLM-041) | `UNTESTED` |
| L1 | Ledger and Trezor through a host wallet | Hardware | Not examined | `UNTESTED` |
| L1 | WalletConnect-connected variants of the above | Mobile deep link and QR | Capabilities may differ from the native connector | `UNTESTED` |
| L2 | Ambire, TokenPocket, Openfort, thirdweb, Reown embedded wallets | Mixed | Listed, atomic status not stated (CLM-041) | `UNTESTED` (not part of any v1.0 claim unless a merchant segment needs it) |

L0 wallets are the launch-claim candidates; a wallet that is not in the Compatibility Register at E3 is served by the non-batching paths and never described as supported.

### 2.2 Account types (columns)

| Code | Account type | ACP mode ([17](17-account-compatibility-policy.md)) | How the lab creates it |
|---|---|---|---|
| A0 | EOA, never delegated | `PLAIN_EOA`; pin `PIN_EOA` | Fresh test key in the wallet |
| A1 | EOA delegated through the **wallet-managed upgrade** (`atomicRequired: true` prompt) | `EOA_7702_VERIFIED` once an E3 row exists; until then `UNKNOWN_CODE` | Accept the wallet's upgrade prompt on a fresh test key |
| A2 | EOA delegated to a **third-party or unrecognized** delegate | `UNKNOWN_CODE` (expected) | A test key delegated outside the wallet (a signed EIP-7702 authorization sent by the lab, never by FastPay), then imported |
| A3 | Native smart contract account (Safe, Coinbase smart wallet, ERC-4337 account) | `SMART_4337` or `WALLET_1271` per the row's kind; `UNKNOWN_CODE` without a row | Created through the wallet |
| A4 | Hardware-backed account through a host wallet | Mode of the host account | Ledger or Trezor test device behind MetaMask or similar |

### 2.3 Test sets

| Set | Contains | Applies to |
|---|---|---|
| **CORE** | WL-01…WL-10, WL-16, WL-18, WL-19, WL-24, WL-25 | Every wallet × platform × A0 |
| **BATCH** | WL-04…WL-09 on the account types the wallet batches for | Wallets reporting or claiming `wallet_sendCalls` |
| **DELEG** | WL-11…WL-15 | Every account type in A1, A2 for any wallet that upgrades or imports delegated accounts |
| **SIG** | WL-12, WL-20, WL-27, WL-28 | Wallets where signature transports might be used (`sig1271` gate) and Pay Once |
| **SMART** | WL-30 plus WL-12 | A3 |
| **HW** | WL-21 | A4 |
| **MIG** | WL-17, WL-29 | Wallets in a launch claim, before RG-015 |
| **WC** | WL-22, WL-23 | Every wallet used through WalletConnect |
| **ACP** | WL-32…WL-35 | Every wallet × platform for A0 and A1, and for A3 where the wallet creates contract accounts |

## 3. Tests

Pass criteria are written so that a run either passes or produces evidence for a verdict. Error codes are those of EIP-5792 as retrieved (CLM-007). "Record" means: store the raw wallet output verbatim in the evidence store and the structured result in the run record (§4).

### 3.1 Capability and batching

| ID | Test | Procedure | Pass criterion | Feeds |
|---|---|---|---|---|
| WL-01 | Capabilities before authorization | Call `wallet_getCapabilities` before `eth_requestAccounts` | Wallet returns `4100` or a documented result. Record. Outcome is **never** read as "unsupported" (NC-02) | Planner `UNKNOWN` handling |
| WL-02 | Capabilities per chain | After authorization, call it for each test chain and account type; record `atomic` ∈ {`supported`, `ready`, `unsupported`, absent} | Raw JSON captured for every cell; absent chain recorded as "not supported there" (CLM-003) | `rawGetCapabilities`, `atomic` |
| WL-03 | Capability stability | Repeat WL-02 after reload, account switch, network switch and a wallet update | Same result, or a recorded change with its trigger | Retest policy |
| WL-04 | Atomic batch on a `supported` account | `wallet_sendCalls` with `atomicRequired: true`, two harmless calls | One bundle; `wallet_getCallsStatus` reaches 200; `atomic: true`; on-chain effects of both calls | `sendCalls`, `atomicObserved` |
| WL-05 | Upgrade on a `ready` account | Same, on an A0 account reporting `ready` | Upgrade prompt shown (`upgradePrompt: offered`); on approval status becomes `supported` and WL-04 passes; on refusal the documented error (`5750` or `4001`) is returned | `upgradePrompt`, `upgradeRejectCode`; A1 creation |
| WL-06 | Unsupported account | `atomicRequired: true` on an account that cannot batch | Error `5760` (or `5700`); with `atomicRequired: false` the behavior is recorded (sequential or error) | `NO_BATCH` verdict |
| WL-07 | Error paths | Unsupported chain (`5710`), duplicate id (`5720`), oversized bundle (`5740`) | Codes as documented; no partial execution | `statusCodesObserved` |
| WL-08 | **Atomicity violation probe** | Batch whose second call reverts after a first call that changes state | **No state change from the first call** on chain. Any partial application is a violation: verdict `BROKEN` and flag `ATOMIC_VIOLATING` (NC-01) | Safety verdict |
| WL-09 | Status and receipts | Poll `wallet_getCallsStatus` through 100 → 200; compare receipts with chain | Receipts equal the chain; the `atomic` boolean is recorded; more than one receipt per bundle is recorded (CLM-043) | Verification step V1 |
| WL-10 | Hidden extra call | Batch with an additional call that the page did not add (NC-10) | Wallet preview shows every call; if not, `txPreview: raw` and a UX constraint is recorded | `txPreview`; PB-012 |

### 3.2 Delegation (EIP-7702)

| ID | Test | Procedure | Pass criterion | Feeds |
|---|---|---|---|---|
| WL-11 | Delegate capture | After WL-05 (A1) and for A2: run the inspection procedure of [13 §3.4](13-eip7702-delegation-inspection.md); record account code, designator, delegate address, runtime code hash, proxy and implementation, explorer verification, three ERC-1271 probes | A complete `DelegationRecord` from two agreeing RPCs; the vendor's documentation is **not** used to identify code (G-07) | EV-P09; `delegate{}` in the register; allowlist v0 |
| WL-11b | Persistence | After the upgrade: let a later transaction fail; restart the wallet; check other chains | Delegation remains as in CLM-016; whether the wallet sets it on other chains (including `chain_id` 0 authorizations) is recorded | Account-state assumptions; RISK-021 |
| WL-12 | **Permit2 under ERC-1271** | From a delegated (A1/A2) and a smart-contract (A3) account, sign (a) a Permit2 `PermitSingle` and (b) a `SignatureTransfer` witness permit through the wallet; submit both to Permit2 on the test chain | Recorded accept/reject with the revert path. **Expected from CLM-050: a code-bearing signer is accepted only if the delegate's `isValidSignature` succeeds**; any other outcome is a finding that changes the `sig1271` gate | EV-P07; `sig1271` default |
| WL-13 | Always-valid delegate | Hostile fixture: delegate returning the magic value for any input | Probe class `MAGIC`; account classified `EOA_7702_UNKNOWN`; FastPay mode refused; risk case opened (NC-14) | Hostile-wallet fixtures |
| WL-14 | Delegate or code change between plan and signing | Swap the delegate (or the delegate's implementation) after the plan is produced, before and after signing, and between two unattended charges | Revalidation returns `MISMATCH` with the exact diff set of the matching vector (DRV-04 to DRV-06, DRV-10; a change between the check and signing: DRV-24); the attempt is blocked and the mandate pauses as `DELEGATION_UNVERIFIED` | Revalidation parameters (RP-28) |
| WL-15 | Customer reverts the delegation | Use the wallet's own "switch back" path; then re-read the account | Code cleared to empty (or the wallet's behavior recorded); time taken; instructions captured; FastPay reclassifies to `EOA`; existing mandates stay valid on chain ([13 §6](13-eip7702-delegation-inspection.md)) | `revocationPath`; support playbook |

### 3.3 Display, signing and revocation

| ID | Test | Procedure | Pass criterion | Feeds |
|---|---|---|---|---|
| WL-16 | Typed-data readability: mandate | Sign the activation typed data (nested structs, caps, token, merchant, router) | Each named field of the consent screen is visible and readable, or the wallet is classified `opaque`; screenshot of every prompt | `typedDataRenderable`; PB-009 |
| WL-17 | Router-specific authorization | Sign the successor authorization ([12 §5.3](12-router-lifecycle-and-migration.md)) | Router address, `toRouter` identity and the terms hash are visible; an opaque display is recorded as a UX constraint and as input for the verification page | PB-048; RG-015 |
| WL-18 | Transaction preview | Show the activation batch with contracts verified on the explorer and the ABI registered | Preview class recorded: `simulation`, `decoded` or `raw`; calls decoded where the wallet reads ABIs | `txPreview`; PB-012 |
| WL-19 | Primary revocation flows | From the wallet, execute: token `approve(Permit2, 0)`, `Permit2.lockdown`, `Permit2.approve(token, router, 0, 0)`, `invalidateNonces`; and FastPay `revoke` and `revokeBySig` | Each takes effect on chain as specified ([05 §2.1](05-evm-authorization-decision-tree.md)); the wallet shows what is being revoked; costs and gas wording recorded | EV-P11; PB-050 |
| WL-20 | Signature transports | Sign a `PermitSingle` without sending; submit later through a relayer | Wallet allows signing without sending; `sigDeadline` is visible; replay and expiry behave as specified | `RELAYED_SIGNATURES` flag |
| WL-21 | Hardware path | A4: attempt WL-16 and WL-18 | `hardwarePath` ∈ {`ok`, `opaque`, `unsupported`}; blind-signing requirement recorded; consent does not rely on the device display (ASM-006/007) | PB-009; RP-21 |
| WL-22 | WalletConnect | Repeat WL-02, WL-04 and WL-16 through a WalletConnect session | Method allowlists and capability pass-through recorded; differences from the native connector recorded | Separate register rows |
| WL-23 | Mobile hand-off | Deep link to the wallet and return to the browser; kill and reopen the browser | The activation session resumes without a duplicate prompt | Session design |
| WL-24 | Account or network switch mid-flow | Switch account or chain while a plan is waiting | The plan is re-made from chain state; no stale authorization is submitted | Planner re-plan rules |
| WL-25 | Rejection and timeout | Reject each prompt; let each prompt expire | `4001` or the wallet's code recorded; state machine ends in a defined state; no charge | Error taxonomy |

### 3.4 Pay Once, smart accounts, migration and experimental flows

| ID | Test | Procedure | Pass criterion | Feeds |
|---|---|---|---|---|
| WL-27 | Pay Once witness display | Sign `PayOnceIntent` ([10 §2.1](10-pay-once-protocol.md)) | Recipient, amount, token, deadline and payment id are readable; otherwise `opaque` and Pay Once uses a transaction path | PO path selection |
| WL-28 | Pay Once alternates | Exact `approve`, ERC-2612 permit and direct-transaction paths (PO-2, PO-3, PO-6) | Each works or is recorded as unsupported; ERC-3009 only with its flag | PO-1…PO-6 eligibility |
| WL-29 | Migration consent end to end | Run MIG-TV-01…04 and, for the shared allowance, MIG-TV-30, 33 and 44 (normal partial, emergency, no-S2 plan) with the wallet (grant new, revoke old for the pairs the mode requires, activate successor) over each transport the wallet supports | Order S1, S2, S3 holds (S2 absent in a partial plan); partial states Q0…Q3 and Q3s re-plan without duplicate prompts | RG-015; PB-048 |
| WL-30 | Smart-account signatures | A3: a Permit2 signature for Safe or the Coinbase smart wallet, including a wallet that signs asynchronously or needs a pre-approved hash | `isValidSignature` returns success with the real signature; asynchronous signing is recorded as a constraint on `sigDeadline` | `sig1271` for smart accounts |
| WL-31 | **Experimental** zero-amount `permit` revocation | Lab only: sign a `PermitSingle` with amount 0; submit; read allowance, expiry and nonce | Result recorded either way. It stays `revocation.zeroPermit.enabled = off`; a positive result adds an *experimental* note and never changes the primary flows (EV-P08) | EV-P08; RP-27 |

### 3.5 Account Compatibility Policy (modes and pin)

| ID | Test | Procedure | Pass criterion | Feeds |
|---|---|---|---|---|
| WL-32 | Mode classification | For each account (A0, A1, A2, A3) run the observation of [13 §3.4](13-eip7702-delegation-inspection.md) and evaluate the predicates of [17 §2.2](17-account-compatibility-policy.md) | The computed mode equals the expected mode of §2.2 (A0 `PLAIN_EOA`; A1 `EOA_7702_VERIFIED` with a row; A2 `UNKNOWN_CODE`; A3 per row); the three probe results and the proxy fingerprint are recorded | Register `mode`; ACP-TV-01…12 |
| WL-33 | Pin values | Read `EXTCODEHASH` of the account at each stage: unused (0), funded (`keccak256("")`), after the wallet upgrade (designator hash), after revert, for a contract account | Values equal the pin predicates of [17 §5.1](17-account-compatibility-policy.md); the designator hash equals `keccak256(0xef0100 ‖ delegate)` for the delegate recorded by WL-11 | EV-P13; ACP-TV-13…17 |
| WL-34 | Predicted post-upgrade delegate | On an `ATOMIC_READY` account, execute the activation batch with the pin predicted from the row's `expectedDelegateAfterUpgrade`; repeat with a deliberately wrong prediction | Correct prediction: `activate` succeeds; wrong prediction: the batch reverts atomically with nothing applied | `expectedDelegateAfterUpgrade` (ASM-032); ACP-TV-22 |
| WL-35 | Upgrade or delegate change after activation | With an active mandate, (a) accept the wallet's upgrade prompt, (b) change the delegate, (c) revert to a plain account, (d) upgrade a proxy implementation (contract account) | (a)–(c): the charge simulation reverts `AccountCodeChanged`, the mandate pauses, re-verification with one signature resumes charging; (d): the pin stays valid and the backend reports `DELEGATE_PROXY_IMPL` | S-B…S-E of [17 §7](17-account-compatibility-policy.md); RP-28 data |
| WL-36 | `AccountPin` display | Sign `ActivationTerms` and `AccountPinUpdate` whose nested `AccountPin` has all seven fields ([17 §5.1](17-account-compatibility-policy.md)) | Each of `accountMode`, `accountCodeHash`, `delegate`, `delegateCodeHash`, `implementationFamily`, `pinVersion`, `signatureMode` is visible and readable, or the wallet is classified `opaque` for the pin and the portal shows the pin in full before the prompt; screenshot of every prompt | `typedDataRenderable` (pin); PB-055; ACP-TV-25 |
| WL-37 | Delegate code hash and stability | For the delegate recorded by WL-11, read `EXTCODEHASH(delegate)` on two RPCs; repeat after a wallet restart, a browser update and a reinstall; record whether the delegate is a proxy and the implementation | The value is identical across providers and across the restarts, or the instability is recorded; the pinned `delegateCodeHash` equals the value read by `consume`'s opcode | `delegateCodeHash` pin field; ACP-TV-31/32; UX-17, UX-18 |
| WL-38 | Wallet version change | With an active mandate on a pinned account, update the wallet to the next build (needs two builds; one build records `INCONCLUSIVE`) and re-run the observation | Whether the delegate address, delegate code hash, proxy implementation, probe fingerprint or reported version changed is recorded; each change maps to a trigger of [17 §5.6](17-account-compatibility-policy.md) and the capability is revoked by it | UX-17; ACP-TV-41…43; EVL-15 |
| WL-39 | FastPay typed data under ERC-1271 | A1/A3: sign `SuccessorAuthorization`, `AccountPinUpdate` and `revokeBySig` through the account's `isValidSignature`; submit on the testnet contracts (or the reference model on a fork) with `signatureMode = ERC1271`; then change the delegate code hash (a swappable fixture) and repeat | `AUTH` accepts while `PIN_OK` holds and refuses once the delegate code hash changed; exits stay accepted; a wallet that cannot produce a valid signature is recorded and the pin uses `DIRECT_ONLY` | `fastpaySig`; I-ACCT-SIG; ACP-TV-38…40 |
| WL-40 | Shared allowance in the wallet | Two mandates on one router and token: execute the `approve` for the shared slot, a `lockdown` naming a subset of `(token, router)` pairs, the right-sizing `approve` and the full `lockdown` | The wallet shows token, spender, amount and expiration for each pair so the customer can tell a partial lockdown from a full one, or the display is recorded as `opaque` and the portal shows the pairs first; the on-chain effects equal MIG-TV-30…34 | R-L2-SHARED; NC-20, NC-21; PB-054; EVL-07 |

## 4. Evidence format

One **run record** per test × wallet × version × platform × account type × chain:

```text
RunRecord {
  runId, testId, wallet, walletVersion, platform, osVersion, accountType, chainId,
  startedAt, tester, reviewer,
  inputs        { hash of the request payload, planId or fixture id },
  raw           [ { name, sha256, storeUri } ],             # verbatim wallet outputs, RPC responses, receipts
  screenshots   [ { name, sha256, storeUri } ],
  observed      { structured result per test, e.g. atomic, statusCodes[], delegate{}, probes[], revertPath },
  result        PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE,
  findings      [ id ],                                     # linked to the Risk Register or a CF item
  evidenceId    EV-…                                        # immutable store entry
}
```

Rules: a run is repeatable from `inputs`; raw outputs are never edited; a second person reviews every `FAIL` and every `PASS` that feeds a safety flag; a row reaches E3 only when all tests of its sets have a reviewed run on the exact wallet version and platform.

## 5. Verdict function

Verdict is computed, not chosen. For a row (wallet, version, platform, account type, chain):

| Verdict | Condition |
|---|---|
| `BROKEN` | WL-08 failed (partial application of an "atomic" batch), or a safety test (WL-12 false accept, WL-13 undetected, WL-14 undetected) failed, or the wallet signs data the user cannot see for a flow FastPay would rely on. The row also sets a flag that disables the affected transport |
| `SUPPORTED_ATOMIC` | WL-02 reports `supported` or `ready`; WL-04, WL-05 (if `ready`), WL-08, WL-09 pass; CORE passes |
| `SUPPORTED_NON_ATOMIC` | `wallet_sendCalls` works only without atomicity, or only `eth_sendTransaction` sequences work, and CORE passes; the planner uses `TX_SEQUENCE` |
| `NO_BATCH` | `wallet_sendCalls` missing or WL-06 returns the unsupported codes consistently; CORE passes with single transactions |
| `UNTESTED` | Any required test lacks a reviewed run, or the row's `retestBy` date has passed |

Derived fields: `mode` and `pin` from WL-32/WL-33; `expectedDelegateAfterUpgrade` only when WL-34 passed for this wallet version; `sig1271 = VERIFIED` only when WL-12 (and WL-30 for A3) pass on this delegate address, code hash and wallet version; `typedDataRenderable` and `hardwarePath` from WL-16/WL-21; `revocationPath` from WL-15. **Retest triggers:** a new wallet release, a delegate code-hash change observed in production, the 30-day documentation recheck, or any `DELEGATION_UNVERIFIED` cluster. Default `retestBy` = test date + 90 days (PROPOSAL; RP-28 may shorten it).

## 6. Seed matrix (required tests per row; all rows `UNTESTED` unless stated)

R3 = needed for testnet alpha (minimum); R6 = needed for private beta. A dash means not required for that release.

| Wallet | Platform | Account types | Sets | R3 | R6 | Verdict today |
|---|---|---|---|---|---|---|
| MetaMask | Chrome extension | A0, A1, A2, A4 (host) | CORE, BATCH, DELEG, SIG, HW, MIG, ACP | CORE, BATCH, DELEG, ACP | all | `UNTESTED` (documented) |
| MetaMask | iOS | A0, A1 | CORE, BATCH, DELEG, SIG, MIG, WC, ACP | CORE, BATCH, ACP | all | `UNTESTED` (documented) |
| MetaMask | Android | A0, A1 | CORE, BATCH, DELEG, SIG, MIG, WC | CORE | all | `UNTESTED` (documented) |
| Coinbase Wallet / Base Account | Browser; iOS; Android | A3 (and A0 where offered) | CORE, BATCH, SMART, SIG, MIG, WC, ACP | CORE, SMART, ACP | all | `UNTESTED` |
| Safe{Wallet} | Web | A3 | CORE, SMART, MIG | SMART | all | `UNTESTED` |
| **Trust Wallet** | iOS; Android; extension | A0, A1 if offered | CORE, BATCH, DELEG, SIG, WC, ACP | CORE (discovery only) | all, if it is to be claimed | **`UNKNOWN`** |
| Rainbow, Rabby, Phantom (EVM) | Extension; mobile | A0 | CORE, BATCH, SIG | — | before any claim | `UNTESTED` |
| Ledger / Trezor via MetaMask | Hardware | A4 | HW (with CORE on the host) | — | before any claim | `UNTESTED` |
| WalletConnect variants | Mobile | per wallet | WC | — | per wallet | `UNTESTED` |

Trust Wallet's R3 entry is **discovery**: record `wallet_getCapabilities` output and `wallet_sendCalls` behavior so the register has a first factual row. It may remain `UNKNOWN` through R3; it cannot be claimed at R6 without its R6 sets.

**The exact run records required to approve the protocol freeze are listed in [16 §9](16-freeze-decision-report.md) (EVL-01…EVL-10 for the freeze, EVL-11…EVL-15 for mode enablement and R6); nothing in this document substitutes for them.** Run records are stored under `spec/evidence/wallet-lab/` in the format of §4 and counted by [tools/freeze_readiness.py](tools/freeze_readiness.py); **today the directory holds none**.

## 7. Hostile and synthetic fixtures

The lab runs the planner and the revalidation against deterministic fakes in addition to real wallets, so behaviors that no real wallet will exhibit on demand are still tested:

| Fixture | Behavior | Used by |
|---|---|---|
| Lying capabilities | Reports `atomic: supported`, executes two separate transactions | WL-08, NC-01 |
| Non-atomic batcher | Applies the first call and fails the second | WL-08 |
| No-`isValidSignature` delegate | Account has code but no ERC-1271 | WL-12, NC-13, TV-18…20 |
| Always-valid delegate | Magic value for any input | WL-13, NC-14 |
| Swappable delegate | Delegate or implementation changes on command | WL-14, DRV-04…DRV-10, DRV-24 |
| Probe-aware delegate | Behaves normally for the probes and differently for real signatures | Per-signature pre-flight ([13 §4](13-eip7702-delegation-inspection.md)); [13 §7.7](13-eip7702-delegation-inspection.md) |
| Proxy delegate | EIP-1967 and EIP-1167 variants with upgradable implementation | DRV-06, DRV-17 |
| Slow or lying RPC | Delayed or disagreeing providers | DRV-11, DRV-12, DRV-13, NC-12 |

## 8. Reporting and claims

1. The **Compatibility Register** is published as data, dated, with the evidence ids and `retestBy` for each row ([05 §10](05-evm-authorization-decision-tree.md)).
2. FastPay may say "supported" for a row only when its verdict is `SUPPORTED_*`, its evidence is E3 and today is before `retestBy`. For everything else the product says nothing about the wallet, or says that the wallet works through the standard (non-batching) path if that is what the row shows.
3. A `FAIL` of a safety test opens a risk case within one business day and disables the affected transport flag for that row.
4. The weekly lab report lists rows by state, expiring rows and open findings; it is an input to the gate register (RG-003).

## 9. Open points

| # | Point | Owner |
|---|---|---|
| 1 | Devices and OS versions for the mobile rows; a device-farm budget versus an owned set | QA Lead |
| 2 | Whether a Trezor/Ledger blind-signing result is acceptable for any consent (default: no, ASM-006/007) | Product Designer + Head of Security |
| 3 | Obtaining an A2 (third-party-delegated) account on each wallet without the lab acting as an attacker of production users | Wallet Protocol Eng |
| 4 | Whether signature transports are worth their complexity if the lab shows most target wallets batch atomically ([05 §12](05-evm-authorization-decision-tree.md) point 6) | Wallet Protocol Eng + Principal PM |
| 5 | Default `retestBy` window and the trigger list, to be set from RP-28 data | Wallet Protocol Eng |
