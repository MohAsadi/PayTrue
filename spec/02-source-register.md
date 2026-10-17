# 02 — Source Register, Evidence Register Seed, and Research Plan

| Field | Value |
|---|---|
| Artifact | FP-PRD-000 (Part 0.1, 0.8) |
| Version | 0.5.0 (SRC-003 pinned; EV-P14, EV-P15 added) |
| Status | DRAFT |
| Owner | Principal PM (register), QA Lead (evidence) |
| Reviewers | Principal Blockchain Architect, Head of Security, Head of Compliance |
| Dependencies | [README](README.md) evidence levels |
| Definition of Done | Every source used by any other artifact has a `SRC-` row; every load-bearing claim has a `CLM-` row at E2 or higher before the artifact that uses it is `APPROVED`; every `RP-` task has an owner and due week. |
| Retrieval date of all entries below | 2026-10-13 (revision 0.2 fetches the same day) |

## 1. Register template

**Source row** (one per document, contract, or dataset):

| Field | Rule |
|---|---|
| `SRC-id` | Stable, never reused |
| Title / publisher | Exact title, issuing body |
| Tier | **T1** normative (standard text, deployed bytecode, statute) · **T2** official vendor/issuer docs & source code · **T3** third-party commentary, trackers, blogs |
| Locator | URL **and** pin: commit SHA, EIP revision, document version, or content hash. A URL alone is not a pin. |
| Status at retrieval | e.g. EIP status `Final` / `Draft` |
| Retrieved (date, by, method) | `direct-fetch` · `search-summary` · `on-chain-read` · `human-reviewed` |
| Evidence level | E0–E3 ([README](README.md)) |
| Recheck by | Date. Default: T1 standards 6 months; vendor wallet docs 30 days; deployments before every release |
| Claims | Linked `CLM-` ids |
| Used by | Artifact ids |
| Owner | Role |

**Claim row** (one per fact a design depends on): `CLM-id`, exact claim (paraphrase, not quote), `SRC-id`, evidence level, design impact (ADR / requirement ids), contradicted-by (if any), status `HOLDS | WEAK | CONTRADICTED | STALE`.

**Evidence row** (one per piece of proof): `EV-id`, claim ids supported, type (`doc-fetch` · `source-review` · `eth_getCode-hash` · `fork-test` · `wallet-lab-run` · `token-lab-run` · `audit-finding` · `legal-memo`), reproduction steps, artifact location (immutable store), reviewer, date, retention.

Rule: a fact that fails the claim template is an `ASSUMPTION` (see [03](03-assumptions-decisions-risks.md)).

## 2. Sources retrieved in this pass

| SRC | Title | Tier | Locator | Status | How retrieved | Level |
|---|---|---|---|---|---|---|
| SRC-001 | EIP-5792: Wallet Call API | T1 | https://eips.ethereum.org/EIPS/eip-5792 (no revision pin — **pin required**) | Final | direct-fetch | E1 |
| SRC-002 | EIP-7702: Set Code for EOAs | T1 | https://eips.ethereum.org/EIPS/eip-7702 (pin required) | Final | direct-fetch | E1 |
| SRC-003 | Uniswap/permit2 repository: `src/**`, `foundry.toml`, `README.md`, deploy script | T2 | https://github.com/Uniswap/permit2 at commit **`cc306b601f172c51bc04334a109e98340456620b`** (2022-11-17; the commit the repository's own tag `0x000000000022D473030F116dDEE9F6B43aC78BA3` points at; blobs recorded in [evidence/permit2/pin.json](evidence/permit2/pin.json)) | retrieval 2026-10-16: Git blob SHA-1 of each of the 17 files equals the repository tree | direct-fetch (GitHub API and raw files, read in an automated session) | **E1 pinned**; E2 pending (two named reviewers) |
| SRC-004 | Permit2 overview | T2 | http://developers.uniswap.org/llms.mdx/docs/protocols/permit2/overview (redirected from docs.uniswap.org) | n/a | direct-fetch | E1 |
| SRC-005 | Uniswap v4 deployments page (lists Permit2 per chain) | T2 | http://developers.uniswap.org/llms.mdx/docs/protocols/v4/deployments | n/a | direct-fetch | E1 |
| SRC-006 | `IAllowanceTransfer.sol`, Uniswap/permit2 `main` | T2 | https://raw.githubusercontent.com/Uniswap/permit2/main/src/interfaces/IAllowanceTransfer.sol (**branch tip, not a commit**) | n/a | direct-fetch | E1 |
| SRC-007 | ERC-2612: Permit Extension for EIP-20 | T1 | https://eips.ethereum.org/EIPS/eip-2612 | Final | direct-fetch | E1 |
| SRC-008 | ERC-3009: Transfer With Authorization | T1 | https://eips.ethereum.org/EIPS/eip-3009 | **Draft** | direct-fetch | E1 |
| SRC-009 | ERC-1271: Standard Signature Validation for Contracts | T1 | https://eips.ethereum.org/EIPS/eip-1271 | Final | direct-fetch | E1 |
| SRC-010 | ERC-7715: Request Permissions from Wallets | T1 | https://eips.ethereum.org/EIPS/eip-7715 | **Draft** | direct-fetch | E1 |
| SRC-011 | EIP-5792 wallet ecosystem list | T3 | https://eip5792.xyz/ecosystem/wallets | n/a | direct-fetch | E1 (incomplete by its own statement) |
| SRC-012 | MetaMask docs: "Send batch transactions" (wallet docs) | T2 | https://docs.metamask.io/wallet/how-to/send-transactions/send-batch-transactions/ (no date or version on page) | n/a | direct-fetch (2026-10-13, revision 0.2) | E1 — **documented** |
| SRC-020 | MetaMask Connect EVM docs: "Send batch transactions" | T2 | https://docs.metamask.io/metamask-connect/evm/guides/send-transactions/batch-transactions.md | n/a | direct-fetch (2026-10-13, revision 0.2) | E1 — **documented** |
| SRC-013 | Base / Coinbase docs: Spend Permissions, SpendPermissionManager | T2 | docs.base.org, docs.cdp.coinbase.com | n/a | **search-summary only** | E0 |
| SRC-014 | Ethereum Foundation blog: Pectra mainnet announcement | T2 | https://blog.ethereum.org/2025/04/23/pectra-mainnet | n/a | direct-fetch (2026-10-13, revision 0.2) | E1 |
| SRC-015 | LI.FI Permit2 docs; 1inch solidity-utils `PERMIT2_ADDRESS_ZKSYNC` | T3 | docs.li.fi; cdn.jsdelivr.net/npm/@1inch/solidity-utils | n/a | **search-summary only** | E0 (corroboration only) |
| SRC-016 | `SignatureVerification.sol`, Uniswap/permit2 `main` | T2 | https://raw.githubusercontent.com/Uniswap/permit2/main/src/libraries/SignatureVerification.sol (**branch tip, not a commit**) | n/a | direct-fetch (revision 0.2) | E1 |
| SRC-017 | `SignatureTransfer.sol`, Uniswap/permit2 `main` | T2 | https://raw.githubusercontent.com/Uniswap/permit2/main/src/SignatureTransfer.sol (branch tip) | n/a | direct-fetch (revision 0.2) | E1 |
| SRC-018 | `AllowanceTransfer.sol`, Uniswap/permit2 `main` | T2 | https://raw.githubusercontent.com/Uniswap/permit2/main/src/AllowanceTransfer.sol (branch tip) | n/a | direct-fetch (revision 0.2) | E1 |
| SRC-019 | `PermitHash.sol`, Uniswap/permit2 `main` | T2 | https://raw.githubusercontent.com/Uniswap/permit2/main/src/libraries/PermitHash.sol (branch tip) | n/a | direct-fetch (revision 0.2) | E1 |

**Not yet retrieved** (needed before the related artifact can be approved): EIP-712, EIP-1193, ERC-20, EIP-4337, ERC-7710, EIP-7201, EIP-2, EIP-170/3860 (size limits), Permit2 audit reports, Permit2 `PermitHash` type strings in full, `Permit2.sol` and the `PackedAllowance` library (expiration-of-zero semantics), WalletConnect specs, Trust Wallet developer docs, each wallet's current docs, each launch chain's finality/RPC/EVM-version documentation, any regulation or guidance (see RP-09…RP-12).

## 3. Claims extracted so far

Impact column points to where the claim is used. "Level" is the claim's level, not the source's potential.

### 3.1 Wallet call API (EIP-5792)

| CLM | Claim | SRC | Level | Impact |
|---|---|---|---|---|
| CLM-001 | EIP-5792 is Final (Standards Track: Interface); requires EIP-1193. | 001 | E1 | [05](05-evm-authorization-decision-tree.md) |
| CLM-002 | Defines `wallet_sendCalls`, `wallet_getCallsStatus`, `wallet_showCallsStatus`, `wallet_getCapabilities`. Apps may fall back to `eth_sendTransaction` when absent. | 001 | E1 | 05 §3 |
| CLM-003 | Capability `atomic` is reported per chain with status `supported` / `ready` / `unsupported`; absence for a chain means batching is not supported there. | 001 | E1 | 05 §3.2 |
| CLM-004 | `atomicRequired: true` obliges the wallet to execute atomically and contiguously, or to upgrade to `supported` first; `false` allows sequential execution without guarantees. | 001 | E1 | 05 §3.2, R-ATOMIC |
| CLM-005 | `wallet_getCapabilities` returns error `4100` if the account is not authorized. | 001 | E1 | 05 §3.1 (treat as UNKNOWN, never as unsupported) |
| CLM-006 | `wallet_getCallsStatus` returns `status` 100 pending, 200 confirmed, 400 offchain failure, 500 complete revert, 600 partial revert, plus an `atomic` boolean and receipts (strict subset of receipt fields). | 001 | E1 | 05 §7 |
| CLM-007 | Error codes: 5700 unsupported non-optional capability, 5710 unsupported chain, 5720 duplicate id, 5730 unknown bundle, 5740 bundle too large, 5750 atomic-ready wallet rejected upgrade, 5760 atomicity not supported; plus 4001 user rejected. | 001 | E1 | 05 §7 |
| CLM-008 | `paymasterService` appears only as an illustrative capability; capability definitions are left to separate ERCs. `optional:true` lets a wallet without support proceed as if absent. | 001 | E1 | OD-002 (sponsorship) |

### 3.2 Delegation (EIP-7702)

| CLM | Claim | SRC | Level | Impact |
|---|---|---|---|---|
| CLM-010 | EIP-7702 is Final (Core). Transaction type `0x04`; authorization tuple `[chain_id, address, nonce, y_parity, r, s]`; signed message prefix `MAGIC = 0x05`. | 002 | E1 | 05 §3.3 |
| CLM-011 | `chain_id` 0 is accepted as "any chain", i.e. an authorization can be replayed across chains. | 002 | E1 | RISK-021; 05 §3.3 |
| CLM-012 | Delegation designator is `0xef0100 ‖ address`; delegating to the zero address clears it. | 002 | E1 | 05 §4 (account classification) |
| CLM-013 | The spec states applications must not expect users to sign authorizations and that there is no safe way to provide that interface; wallets own delegation. | 002 | E1 | ADR-007 (FastPay never requests a raw 7702 authorization) |
| CLM-014 | Security considerations: authorizing party can invalidate an authorization (nonce bump) or sweep assets; initialization can be front-run unless calldata is signed by the EOA key; delegate migration risks storage collisions (ERC-7201 suggested). | 002 | E1 | OD-011; RISK-018 |
| CLM-015 | EIP-7702 shipped in the Pectra hard fork; mainnet activation 2025-05-07 10:05:11 UTC at epoch 364032; the announcement lists "EIP-7702: Set EOA account code". | 014 | E1 (upgraded from E0 in revision 0.2) | context only |
| CLM-016 | **Delegation is persistent account state, not transaction-scoped.** The spec describes the transaction as *permanently* setting the code; a delegation indicator is **not** reverted at the end of the transaction and is not rolled back if the transaction later fails; a later valid authorization overwrites it (last valid tuple wins within one transaction); delegating to the zero address clears it by resetting the code hash to the empty-code hash; protocol-level delegation changes do not touch the account's storage; the delegate's code "has unrestricted access to the account"; `chain_id` may be 0 ("0 or the ID of the current chain"), making an authorization valid on every chain. | 002 | E1 (revision 0.2) | [13](13-eip7702-delegation-inspection.md); ADR-007; RISK-027 |
| CLM-053 | EIP-7702 opcode behavior: for a delegated account `EXTCODESIZE` returns 23 (the designator size) and `EXTCODEHASH` works on the designator without following the delegation (the text states this explicitly for `EXTCODESIZE` and by contrast with delegated execution for `EXTCODEHASH`; `EXTCODECOPY` is implied); `CALL`/`STATICCALL`/`CALLCODE`/`DELEGATECALL` to the account execute the delegate's code in the account's context; a delegation that points to another delegation is not followed beyond the first hop; the spec gives no method for a contract to detect delegation; `tx.origin == msg.sender` is no longer an anti-sandwich or anti-reentrancy guarantee. | 002 | E1 (revision 0.3) | [13](13-eip7702-delegation-inspection.md) §1; OD-029; invariant: no `tx.origin` in FastPay contracts; EV-P10 |

### 3.3 Permit2

| CLM | Claim | SRC | Level | Impact |
|---|---|---|---|---|
| CLM-020 | Canonical Permit2 address is `0x000000000022D473030F116dDEE9F6B43aC78BA3`. | 004, 005 | E1 | Chain config; EV-P01 |
| CLM-021 | Docs state the address is the same on every chain Uniswap supports **except zkSync**, where it is `0x0000000000225e31D15943971F47aD3022F714Fa`. | 004 | E1 (third-party corroboration at E0: SRC-015) | Chain-family adapter rule: never hard-code; registry per chain |
| CLM-022 | The Uniswap v4 deployments page lists the canonical address for Ethereum, Optimism, Base, Arbitrum One, Polygon, Avalanche and BNB Smart Chain (among others). This documents an address; it is **not** a bytecode verification. | 005 | E1 | OD-008; ASM-005 |
| CLM-023 | `AllowanceTransfer`: standing, time-bound allowance; spender may `transferFrom` repeatedly until exhausted or expired; nonce is per (owner, token, spender). | 004 | E1 | ADR-003 |
| CLM-024 | `SignatureTransfer`: one-shot authorization per signature with unordered (bitmap) nonce and a deadline; no standing allowance. | 004 | E1 | Pay Once ([05 §8](05-evm-authorization-decision-tree.md)) |
| CLM-025 | Every ERC-20 needs a one-time standard approval **to Permit2** first; Permit2 docs suggest a max-uint256 approval, which is a broad standing grant to Permit2. | 004 | E1 | The "Layer 1" problem; OD-005 |
| CLM-026 | Interface: `PermitDetails{address token; uint160 amount; uint48 expiration; uint48 nonce}`; `PermitSingle`/`PermitBatch` add `spender` and `sigDeadline`; functions `approve(token,spender,uint160,uint48)`, `permit(owner, PermitSingle|PermitBatch, signature)`, `transferFrom(from,to,uint160,token)`, batch `transferFrom`, `lockdown(TokenSpenderPair[])`, `invalidateNonces(token,spender,uint48)`; view `allowance(user,token,spender)→(amount,expiration,nonce)`; events `Approval`, `Permit`, `Lockdown`, `NonceInvalidation`; errors `AllowanceExpired`, `InsufficientAllowance`, `ExcessiveInvalidation`. | 006 | E1 (branch tip) | Router design; EV-P02 |
| CLM-027 | Permit2 is MIT-licensed, has an `audits` directory, and falls under the Uniswap Labs bug bounty. | 003 | E1 | RP-02 |

Consequence of CLM-026 for design: a Permit2 permit names **token, amount (uint160), expiration (uint48), spender** but **not the merchant, cadence, or recipient**. Merchant-level limits therefore cannot live in Permit2; they must live in FastPay's own contract (Layer 3). This is why the router must be immutable ([ADR-001](06-initial-architecture.md)).

**Permit2 source-level claims (revision 0.2; branch tip, E1)**

| CLM | Claim | SRC | Level | Impact |
|---|---|---|---|---|
| CLM-050 | Signature verification: if the claimed signer has **no code**, the signature is recovered with `ecrecover` (65-byte or 64-byte EIP-2098 form) and must equal the signer; if the signer **has code**, Permit2 calls ERC-1271 `isValidSignature` on it and requires the magic value. There is **no `ecrecover` fallback** for signers with code. A 7702-delegated EOA has code, so its Permit2 signatures are judged by the delegate's `isValidSignature`. | 016 | E1 | [13](13-eip7702-delegation-inspection.md) §5; ADR-017; planner gate `sig1271`; EV-P07 |
| CLM-051 | `SignatureTransfer`: the signed hash includes `msg.sender` as the **spender** (single, batch, with and without witness), token and amount, `nonce`, `deadline`, and for witness variants the `witness` hash and `witnessTypeString`; `transferDetails.to` is chosen by the caller and is **not** in the signed hash, so any recipient binding must be carried in the witness; unordered nonces live in a per-owner bitmap and are consumed **before** signature verification; anyone may call `invalidateUnorderedNonces`, but it only affects the caller's own nonces. | 017, 019 | E1 | [10](10-pay-once-protocol.md); EV-P06 (partly discharged) |
| CLM-052 | `AllowanceTransfer`: `approve`, `lockdown`, `invalidateNonces` act on the **caller's own** allowances (`msg.sender` is the owner); `permit` is callable by anyone but needs the owner's signature and the current nonce; `transferFrom` is callable only by the spender; `transferFrom` reverts with `AllowanceExpired` if `block.timestamp > expiration`; **an allowance stored as `uint160.max` is treated as unlimited and is never decremented**; `lockdown` sets amount to 0 and leaves expiration and nonce unchanged; `invalidateNonces` may raise the nonce by at most 65,535 per call. A signed `permit` carrying amount 0 therefore revokes without a customer transaction. | 018 | **E1 pinned** at `cc306b6` (`AllowanceTransfer.sol:26-30, 59-126`; 0.5 automated read, E2 pending); the revoke-by-zero-permit inference is E0 until tested, EV-P08. Also confirmed in 0.5: the allowance is keyed `(owner, token, spender)` and is therefore shared by every mandate on a router; `approve` **overwrites** amount and expiration; `expiration = 0` stores `block.timestamp` | [05 §6.1](05-evm-authorization-decision-tree.md) R-L2-NO-MAX; [12](12-router-lifecycle-and-migration.md) §6 |

### 3.4 Token-native authorizations and account signatures

| CLM | Claim | SRC | Level | Impact |
|---|---|---|---|---|
| CLM-030 | ERC-2612 is Final. `Permit(owner,spender,value,nonce,deadline)`; nonce is a sequential per-owner counter read from the token; `DOMAIN_SEPARATOR` must be contract- and chain-unique; anyone can submit a signed permit (front-running possible); a relayer can withhold it; a fixed chainId in the domain is a cross-chain replay risk after a fork; EOA-only (the page does not describe ERC-1271 support). | 007 | E1 | Native-permit path (05 §5, R-PERMIT) |
| CLM-031 | ERC-3009 is **Draft**. `transferWithAuthorization` can be front-run from the mempool; `receiveWithAuthorization` requires caller == payee; nonces are random 32-byte values; `validAfter`/`validBefore`; optional `cancelAuthorization`; the page says it does not apply to smart contract accounts. | 008 | E1 | Pay Once token-native path |
| CLM-032 | ERC-1271 is Final. `isValidSignature(bytes32,bytes)` returns `0x1626ba7e` on success; must not modify state; callers must not hard-code gas. | 009 | E1 | SignatureVerifier |
| CLM-033 | ERC-7715 is **Draft**. Method is named `wallet_requestExecutionPermissions` (sibling methods for revoke/list); builds on EIP-4337 and ERC-7710; only an `expiry` rule is defined. | 010 | E1 | OD-010: treat as optional adapter, never a dependency |

### 3.5 Wallet ecosystem and prior art

| CLM | Claim | SRC | Level | Impact |
|---|---|---|---|---|
| CLM-040 | **MetaMask's official docs describe** EIP-5792 batching: `wallet_getCapabilities` reports `atomic` as `supported` or `ready` (chains with neither are omitted); `ready` means MetaMask will prompt the user to upgrade the EOA to a MetaMask smart account (via EIP-7702) and the status becomes `supported` once approved; support is queried per account and optionally per chain; networks named on the page: Ethereum, Gnosis, BNB Smart Chain, OP Mainnet, Base, Polygon, Arbitrum (One, Nova), Unichain, Berachain, plus their test networks; **Avalanche is not listed**; the page says support will expand as networks adopt EIP-7702; for accounts already upgraded to a third-party smart contract account, atomic batching is not supported and the fallback is `eth_sendTransaction`. The pages carry no date or version. **This is documentation, not FastPay evidence of behavior: runtime capability detection remains mandatory.** | 012, 020 | E1 — documented (upgraded from E0 in revision 0.2) | Compatibility Register seed ([05 §10](05-evm-authorization-decision-tree.md)); RP-05 |
| CLM-043 | MetaMask docs further state: `wallet_sendCalls` supports only atomic batches (so `atomicRequired` may be true or false), uses API format `"2.0.0"`, returns an error when atomic execution is unsupported, `atomic` in `wallet_getCallsStatus` is currently always `true` on success, a batch may return more than one receipt (for example `eth_bundle` on an L2), and status 200 means confirmed. The docs **do not** name the delegate contract or its address, **do not** state whether the upgrade persists (they link to end-user docs on switching to or reverting from a smart account), and describe MetaMask Smart Accounts inconsistently as ERC-4337 contract accounts while describing the upgrade through EIP-7702. | 012, 020 | E1 — documented | [13](13-eip7702-delegation-inspection.md): the delegate must be **inspected and recorded**, not inferred from docs; G-07 |
| CLM-041 | The eip5792.xyz list names Coinbase Smart Wallet, Safe, Ambire, MetaMask, Reown AppKit embedded wallet, thirdweb, Openfort, Abstract Global Wallet, TokenPocket, Splits Teams. It does not mention Trust Wallet, Rainbow, Rabby, Phantom or Ledger, gives no atomic-support breakdown, and says it is not exhaustive. | 011 | E1 | Trust Wallet status = **UNKNOWN** (not unsupported) |
| CLM-042 | Base Spend Permissions: a `SpendPermissionManager` (address in vendor docs `0xf85210B21cC50302F477BA56686d2019dC9b67Ad`) lets a smart-account owner grant a spender a per-period allowance with start/end; only the named spender can spend; vendor docs list Arbitrum, Avalanche, Base, Ethereum, Optimism, Polygon; accounts must have the module enabled at creation. | 013 | **E0** | OD-010 (prior art for recurring pulls; adapter candidate) |

## 4. Gaps and drift found in this pass

| # | Finding | Action |
|---|---|---|
| G-01 | Documentation sites redirected (docs.uniswap.org → developers.uniswap.org → `llms.mdx` mirror). Doc URLs are not stable pins. | Pin Permit2 by repository commit SHA and by on-chain bytecode hash, never by doc URL. RP-02/03 |
| G-02 | ERC-7715's method has been renamed since earlier drafts (`wallet_grantPermissions` → `wallet_requestExecutionPermissions` per the retrieved page). | Reinforces: Drafts are never hard dependencies (CF-005). |
| G-03 | The retrieval tool summarizes pages; it cannot prove byte-exact text. | All E1 claims must be re-read by a human at E2 before an artifact using them is `APPROVED`. |
| G-04 | Trust Wallet capability documentation not found. Absence of evidence is not evidence of absence. | RP-05 wallet lab records actual `wallet_getCapabilities` result. |
| G-05 | zkSync Era is a documented Permit2 exception. It is not in the initial chain list but proves the rule "address by chain registry, verified by bytecode". | Chain-config schema carries `permit2Address` and `permit2CodeHash` per chain ([06](06-initial-architecture.md)). |
| G-06 | Permit2 verifies signatures from accounts **with code** only through ERC-1271 (CLM-050). A 7702-delegated EOA therefore cannot use Permit2 signature flows unless its delegate implements a compatible `isValidSignature`. Nothing in the retrieved docs says whether any wallet's delegate does. | Planner gate `sig1271` (default: signature flows refused for code-bearing accounts); EV-P07; RP-25. |
| G-07 | MetaMask's docs name no delegate contract or address, do not state persistence, and describe its smart accounts inconsistently (ERC-4337 vs EIP-7702) (CLM-043). | FastPay records the delegate address and code hash observed at runtime ([13](13-eip7702-delegation-inspection.md)); documentation is not used to identify code. |
| G-08 | `uint160.max` is Permit2's "unlimited, never decremented" sentinel (CLM-052). A sizing rule that clamps to `2^160 - 1` would silently create an unlimited grant. | Fixed in revision 0.2: R-L2-NO-MAX ([05 §6.1](05-evm-authorization-decision-tree.md)). |
| G-09 | Expiration-of-zero semantics, the `PackedAllowance` update, and the nonce increment inside `permit` were not visible in the retrieved files. **0.5: answered at the pinned commit** (`libraries/Allowance.sol:13-42`: expiration 0 stores `block.timestamp`; `permit` writes amount, expiration and `nonce + 1` in one word; PR-02, PR-03, PR-08); E1 pinned, E2 pending. | Human review at E2 (RP-02). |
| G-10 | Permit2's treatment of an expired allowance at the boundary (`block.timestamp > expiration` reverts) was inferred from the retrieved `AllowanceTransfer.sol` text. **0.5: read at the pinned commit** (`AllowanceTransfer.sol:79`; PR-07): the comparison is `>`, so an allowance is usable at `block.timestamp == expiration`; E1 pinned, E2 and the fork test (MIG-TV-22/40) pending | The predicate `Unusable ≡ a = 0 ∨ e < now` ([12 §5.3](12-router-lifecycle-and-migration.md)) depends on it; PR-07, PR-08, MIG-TV-22. RP-30 |
| G-11 | Permit2 verifies signatures of accounts without code with `ecrecover`; an **undeployed** contract account therefore cannot validate (ERC-6492 is not mentioned in the retrieved files) | Counterfactual accounts are not planned for signature flows ([17 §2.2](17-account-compatibility-policy.md)); confirm at the pinned commit (PR-12) |

## 5. Evidence Register — seed

| EV | Supports | Type | Reproduction | Reviewer | Date | State |
|---|---|---|---|---|---|---|
| EV-001 | CLM-001…008 | doc-fetch | GET SRC-001, extract sections *Methods*, *Capabilities*, *Status codes*, *Errors* | none yet | 2026-10-13 | E1 |
| EV-002 | CLM-010…014 | doc-fetch | GET SRC-002 | none yet | 2026-10-13 | E1 |
| EV-003 | CLM-021, 023…025 | doc-fetch | GET SRC-004 | none yet | 2026-10-13 | E1 |
| EV-004 | CLM-020, 022 | doc-fetch | GET SRC-005; table of chains | none yet | 2026-10-13 | E1 |
| EV-005 | CLM-026 | source-review | GET SRC-006 | none yet | 2026-10-13 | E1 (branch tip) |
| EV-006 | CLM-030…033 | doc-fetch | GET SRC-007/008/009/010 | none yet | 2026-10-13 | E1 |
| EV-007 | CLM-041 | doc-fetch | GET SRC-011 | none yet | 2026-10-13 | E1 |
| EV-008 | CLM-040, CLM-043 | doc-fetch | GET SRC-012, SRC-020 | none yet | 2026-10-13 | E1 — documented |
| EV-009 | CLM-050, 051, 052 | source-review | GET SRC-016…019 | none yet | 2026-10-13 | E1 (branch tip) |
| EV-010 | CLM-015 | doc-fetch | GET SRC-014 | none yet | 2026-10-13 | E1 |
| EV-011 | CLM-016 | doc-fetch | GET SRC-002, sections on delegation persistence and clearing | none yet | 2026-10-13 | E1 |
| EV-012 | CLM-053 | doc-fetch | GET SRC-002, sections on opcode behavior and `tx.origin` | none yet | 2026-10-13 | E1 |

**Planned evidence (blocking the claims they name):**

| EV | Needed for | Method | Target |
|---|---|---|---|
| EV-P01 | CLM-020/022: Permit2 present and unmodified on each launch chain | `eth_getCode(0x0000…8BA3)` on ≥2 independent RPCs per chain; hash must equal the hash of bytecode built from the pinned commit **with the two per-chain immutables masked** (the per-chain hash is not constant, EV-P14) and match the explorer-verified source; stronger: rebuild the creation code with the recorded settings and reproduce the CREATE2 address (`script/DeployPermit2.s.sol` salt) | P0-W5 (on-chain half done 2026-10-16, rebuild not done) |
| EV-P02 | CLM-026: interface at the pinned commit | Pin commit; diff against SRC-006 | P0-W2 |
| EV-P03 | CLM-040/041: wallet atomic support | Wallet lab (RP-05): per wallet × version × account type × chain, record `wallet_getCapabilities` raw output, `sendCalls` behavior, status codes, UI screenshots | P0-W4…W8 |
| EV-P04 | Token behaviors for launch tokens | Token lab (RP-07) on mainnet forks | P0-W6 |
| EV-P05 | Chain finality policy | RP-04, RP-22 | P0-W6 |
| EV-P06 | Permit2 behavior assumptions. **Partly discharged at E1 in revision 0.2:** ERC-1271 path for signers with code (CLM-050), spender binding and witness (CLM-051), caller scoping of `lockdown`/`invalidateNonces` (CLM-052). **Remaining:** pinned-commit read at E2, and fork tests | Source review at a pinned commit + fork tests with EOA, smart-account and 7702-delegated owners | P0-W5 |
| EV-P07 | A 7702-delegated EOA's behavior under Permit2 signature flows: delegate with a correct `isValidSignature`, with none, with a hostile one | Fork tests with synthetic delegates, then real wallet delegates in the wallet lab | P0-W8 |
| EV-P08 | Revocation behaviors: `lockdown`, signed zero-amount `permit`, `invalidateNonces`, and the wallet's own "revert from smart account" path, per wallet | Fork tests + wallet lab | P0-W8 |
| EV-P09 | Delegate identity per wallet: delegate address, runtime code hash, proxy/implementation status, explorer verification status, `isValidSignature` probe result, batch behavior | Wallet lab capture using the inspection procedure in [13](13-eip7702-delegation-inspection.md) | P0-W8 |
| EV-P10 | `EXTCODEHASH` and `EXTCODESIZE` of a 7702-delegated account on each launch chain equal the designator's hash and 23 | Fork test with a synthetic delegation; real wallet delegation in the lab | P0-W10 |
| EV-P11 | Primary revocation flows behave as specified for **every listed token and chain**: token `approve(Permit2, 0)` (including `ZERO_FIRST` and no-return tokens), `Permit2.lockdown`, `Permit2.approve(token, router, 0, 0)`, `invalidateNonces`; and `MandateManager.revoke/revokeBySig` | Fork tests at the pinned Permit2 commit; token lab | P0-W10 |
| EV-P12 | Every claim about Permit2 that the design stands on, at a **pinned commit**: usability boundary of an allowance (`block.timestamp > expiration` reverts), expiration-of-zero semantics, `lockdown`/`approve`/`invalidateNonces` effects and callers, `permit` nonce update, signature verification path for signers with code, witness type-string format, unordered nonce bitmaps, `uint160.max` sentinel, events | The review checklist PR-01…PR-16 ([16 §5](16-freeze-decision-report.md)) by a named human reviewer at E2, then the fork tests RV-T01…RV-T12 and MIG-TV-22 | before the protocol freeze |
| EV-P13 | Account pin behavior: `EXTCODEHASH` of an unused account (0), a funded account (`keccak256('')`), a 7702-delegated account (designator hash), a proxy account, a self-destructed account, on each launch chain and through a type-4 transaction | ACP fork tests ([17 §10](17-account-compatibility-policy.md)) and wallet-lab runs WL-05, WL-11 | before the protocol freeze |
| EV-P14 | **Deployed Permit2 code on each launch chain** (recorded 2026-10-16): runtime code read at one block from ≥2 independent providers per chain; length, `keccak256`, the two immutables (chain id at byte 6,945, domain separator at 6,983) and a chain-independent **masked hash**; the set of `PUSH4` selectors equals the 15 external functions of the pinned source | `python -I spec/tools/permit2_pin_check.py --online`; [evidence/permit2/pin.json](evidence/permit2/pin.json). **Done for Ethereum (5 providers), Base (2), Arbitrum One (2): E3 for what is deployed.** The rebuild comparison is EV-P01 and is **not done** | recorded; repeat per new chain |
| EV-P15 | Permit2 **behavior note** at the pinned commit: one answer per PR item with file and line (PR-01…PR-16) | [16 §5.3](16-freeze-decision-report.md); E2 sign-off recorded in `pin.json` `humanReview` | answers recorded (E1 pinned); **E2 sign-off before the protocol freeze** |

## 6. Research plan (Phase 0)

Owners are roles. "Level" is the target level at exit. Weeks are Phase 0 weeks ([07](07-delivery-plan.md)).

| RP | Question | Method | Output | Owner | Due | Level |
|---|---|---|---|---|---|---|
| RP-01 | Do the normative texts say what the claims say? | Human read + pin of EIP-712/1193/1271/2612/3009/4337/5792/7201/7702/7710/7715 and ERC-20 | Pinned SRC rows; claims upgraded or corrected | Wallet Protocol Eng | W2 | E2 |
| RP-02 | What exactly does Permit2 enforce? | Pin commit; read `AllowanceTransfer`, `SignatureTransfer`, `SignatureVerification`; read audit reports; list who may call `lockdown`/`invalidateNonces`; ERC-1271 and witness support | Permit2 behavior note + test list | AA/Protocol Eng | W3 | E2 |
| RP-03 | Is Permit2 on each launch chain the expected bytecode? | `eth_getCode` hash vs reference build, two RPCs + explorer | EV-P01 | Solidity Lead | W5 | E3 |
| RP-04 | Per-chain facts: finality, reorg history, EVM version/opcodes, gas token, block time, RPC options, halt/sequencer history | Chain docs + indexer queries + provider comparison | Chain fact sheet per candidate chain | Chain Infra Lead | W6 | E2 |
| RP-05 | What do real wallets do? | Wallet lab matrix: MetaMask (ext, mobile), Trust Wallet, Coinbase/Base Account, Rainbow, Rabby, Phantom (EVM), Safe, Ledger via MetaMask, WalletConnect-connected variants × EOA/7702-delegated/smart account × launch testnets and mainnet forks | Compatibility Register v0; EV-P03 | QA Lead + Wallet Protocol Eng | W4 start, W8 report | E3 |
| RP-06 | Which 7702 delegates do wallets use and how do they warn users? How does an already-delegated account behave? | Lab + vendor docs + threat intel | Account-type classification table (05 §4) | Wallet Protocol Eng | W6 | E3 |
| RP-07 | How do launch tokens actually behave? | Token lab on forks: approve quirks, return values, blacklist, pause, proxy/upgrade authority, permit variants, fee-on-transfer, rebasing | Token behavior matrix + registry seed | Contract Security Eng | W6 | E3 |
| RP-08 | What can we learn from existing recurring-pull designs? | Read specs/code/audits of Base Spend Permissions, ERC-7715/7710 implementations, Permit2-based subscription schemes | Threat lessons; OD-010 recommendation | Principal Architect | W5 | E2 |
| RP-09 | Regulatory perimeter per candidate jurisdiction (crypto-asset service, custody, transfer, payment, stablecoin, acquiring, licensing triggers) | Counsel memo (§20 questions, [03 §6](03-assumptions-decisions-risks.md)) | Perimeter memo; OD-001 closed | Head of Compliance + external counsel | W8 | E2 (`LEGAL-REVIEW-REQUIRED`) |
| RP-10 | Recurring-payment consent, notice, cancellation and refund-rights requirements | Counsel + consumer-protection review per launch market | Consent-copy constraints for B.9 | Compliance + Content Designer | W8 | E2 |
| RP-11 | Sanctions/AML tooling and Travel Rule applicability to a non-custodial model | Vendor RFI + counsel | Vendor shortlist; applicability opinion | Head of Compliance | W8 | E2 |
| RP-12 | Privacy: are wallet addresses personal data in launch regions; DPIA scope; processor/controller roles | DPO + counsel | DPIA scope doc | Privacy Lead | W7 | E2 |
| RP-13 | DEX and aggregator landscape and liquidity depth for launch tokens | Query pools on forks; vendor docs | Adapter shortlist (supports OD-012) | Solidity Lead | W7 | E2 |
| RP-14 | Price/oracle sources and depeg-detection signals | Source survey; historical depeg replay | Oracle source list | Risk lead + Data Eng | W7 | E2 |
| RP-15 | Cloud/HSM comparison: secp256k1 signing support, FIPS validation level, regions, managed Postgres/K8s, cost | Vendor docs + pricing + proof-of-concept signing | ADR-012 input; closes OD-015 | SRE Lead | W6 | E2 |
| RP-16 | Audit market: firms, lead times, price, competition option | RFIs to ≥4 firms | Shortlist and dates (tests ASM-011) | Head of Security | W6 | E2 |
| RP-17 | Bug-bounty platform options and scope design | Vendor review | Plan outline | Head of Security | W8 | E2 |
| RP-18 | Accessibility and RTL requirements for launch locales | Standards review (WCAG 2.2) + native reviewers | B.10/B.11 baseline | Design Systems Lead | W6 | E2 |
| RP-19 | Gas cost per activation and payment by chain | Fork-measured gas for prototype flows at p50/p90 gas prices | Cost model input for OD-002/OD-016 | Solidity Lead + Finance | W8 | E3 |
| RP-20 | Is the name "FastPay" usable in launch markets? | Counsel trademark search | Clear / conflict report (RISK-013) | General Counsel | W4 | E2 |
| RP-21 | How do hardware wallets display EIP-712 and batched calls? | Lab with Ledger/Trezor via host wallets | Compatibility Register rows; UX constraints | QA Lead | W8 | E3 |
| RP-22 | Observed reorg depth and finality delays per chain | Indexer history queries; provider incident logs | Finality thresholds (feeds OD-008, ADR-006) | Chain Infra Lead | W6 | E3 |
| RP-23 | Current 7702 delegate-phishing patterns and wallet mitigations | Threat intel review | Input to threat model (G.1) | Detection Eng | W6 | E2 |
| RP-24 | Do target merchants want this, in what shape? | 20 structured merchant interviews across SaaS/ecommerce/marketplace | Personas, JTBD, MVP validation | UX Researcher + Payments PM | W7 | n/a (primary research) |
| RP-25 | Which delegates do wallets install, how do they behave under Permit2 (ERC-1271), and how does a customer revert delegation in each wallet? | Wallet lab with the inspection procedure ([13](13-eip7702-delegation-inspection.md)); read wallet delegate source where public; revert-path walkthroughs | Delegate allowlist v0; revocation-path table; EV-P07/P08/P09 | Wallet Protocol Eng + QA Lead | W10 | E3 |
| RP-26 | What notice and sunset periods are workable for router migration, and how do customers respond to migration and upgrade prompts? | Counsel on notice duties; comprehension tests on the migration consent; benchmark of allowance-revocation and re-consent behavior | Parameters for OD-026; consent copy v0 | UX Researcher + Head of Compliance | W10 | E2 |
| RP-27 | Do the primary revocation flows work for every candidate token and wallet, and what do the experimental zero-amount `permit` flows do (EV-P08, EV-P11)? | Fork tests, token lab, wallet lab | Revocation table per token and wallet; decision whether the experimental flag is ever worth enabling | AA/Protocol Eng + Contract Security Eng | W10 | E3 |
| RP-28 | What are the latency, RPC cost and false-positive rate of revalidating the account before each unattended charge ([13 §7](13-eip7702-delegation-inspection.md))? | Measurements on testnet alpha plus wallet-lab delegate swaps | Parameters for `MAX_OBSERVATION_AGE`, `EVIDENCE_TTL`, probe budget; false-positive baseline | Wallet Protocol Eng + Chain Infra Lead | W10 (design), alpha (data) | E3 |
| RP-29 | Which account modes does each target wallet produce, with what delegate, proxy and ERC-1271 behavior, and can the post-upgrade delegate be named in advance (`expectedDelegateAfterUpgrade`)? | Wallet lab runs per [15](15-wallet-lab-matrix.md) and [16 §9](16-freeze-decision-report.md) | Compatibility Register rows with mode, pin and expected-delegate fields; EV-P13 | Wallet Protocol Eng + QA Lead | W10 | E3 |
| RP-30 | Pinned Permit2 source review (extends RP-02): commit SHA recorded; checklist PR-01…PR-16 ([16 §5](16-freeze-decision-report.md)) answered with file, function and line | Human read at a pinned commit; hand-off to fork tests | Permit2 behavior note; EV-P12 | AA/Protocol Eng + a second reviewer | W5 | E2 |

Exit criteria for the research plan (Phase 0 gate RG-001): all `PRODUCTION-BLOCKER` claims in [08](08-production-blockers-and-release-gates.md) have a path to E3; every design-load-bearing claim in Parts C and D is ≥ E2; Compatibility Register v0 published with raw evidence links.

## 7. Maintenance rules

1. A source's `Recheck by` date passing turns its claims `STALE`; artifacts that cite them show a warning in CI until rechecked.
2. A vendor "supported" statement is recorded as a claim about the vendor, never as FastPay's support claim. FastPay's own support matrix is computed only from E3 lab evidence.
3. Contradictions create a `CF-` row ([03 §4](03-assumptions-decisions-risks.md)) before either source is trusted.
4. Production addresses never appear in documents; they live in a signed deployment manifest generated by the release pipeline after on-chain verification.
