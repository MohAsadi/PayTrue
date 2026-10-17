# 16 — Protocol Freeze Decision Report

| Field | Value |
|---|---|
| Artifact | FP-REL-004 |
| Version | 0.5.0 (0.4: new) |
| Report date | 2026-10-16 |
| **Decision** | **PROTOCOL FREEZE (RG-016) IS NOT APPROVED.** The gate is open. No signature has been given. The v0.4 direction is accepted for **testnet engineering** only (DEC-16) |
| Why | Four things the sponsor named are not complete. (1) **Shared-allowance migration:** reworked in 0.5 ([12 §5.3.1](12-router-lifecycle-and-migration.md)); its reference model now compiles and passes its suites ([implementation evidence report](evidence/implementation/REPORT.md)), but it is not reviewed by its owners and not audited. (2) **Account-pin semantics:** specified in 0.5 ([17 §5](17-account-compatibility-policy.md)), same status. (3) **Pinned Permit2 review:** the commit is pinned and every PR item is answered from an automated read with citations (E1, pinned), the rebuild comparison is done (the pinned source reproduces the canonical CREATE2 address and the deployed code on three chains, apart from the two immutables the compiler names) and the freeze subset of the fork tests passes on Ethereum mainnet, Base, Arbitrum One ([implementation evidence report](evidence/implementation/REPORT.md)), but the E2 sign-off by two named reviewers is not done (§5). (4) **Wallet-lab evidence:** 0 of the 10 run sets required for the freeze (§9); the lab cannot be run from the authoring environment. The production-blocking constants are 0 of 18 approved (§7, [18](18-configuration-records.md)) and several freeze-blocking decisions are open (§3) |
| Owner | Principal Blockchain Architect (decision), Technical Program Manager (register) |
| Reviewers | Head of Security (veto), VP Eng, QA Lead, Head of Compliance, Solidity Lead |
| Dependencies | [14](14-protocol-freeze-pack.md) (checklist, fingerprints, testnet scope), [11](11-dual-cap-model.md), [12](12-router-lifecycle-and-migration.md), [15](15-wallet-lab-matrix.md), [17](17-account-compatibility-policy.md), [08](08-production-blockers-and-release-gates.md) |
| Definition of Done | The report lists, with owners and evidence ids: every accepted decision, every unresolved decision, every unverified external fact and what would change if it turns out adverse, the constants split into testnet-safe and production-blocking, the exact audit scope, the exact wallet-lab evidence required, and the Permit2 source review to run; it states plainly that nothing is approved. |

**Nothing in this workspace is audited, legally reviewed, or tested on any wallet or chain.** This report is a status and decision document; it does not approve anything. When evidence arrives the status tables below are updated and the sign-off block (§10) is completed by the people named there.

## 1. What approval requires, and where each condition stands

The status column is **computed from recorded evidence** by `python -I spec/tools/freeze_readiness.py` (it reads [evidence/](evidence/README.md) and [config/pc_records.json](config/pc_records.json); prose never satisfies a condition). Today it prints **NOT READY (1 of 11 conditions met)**.

| # | Condition for approving RG-016 | Status today |
|---|---|---|
| C-1 | This report and its companion artifacts are complete **and reviewed by their owners**: [14](14-protocol-freeze-pack.md) checklist and fingerprints, [15](15-wallet-lab-matrix.md), [17](17-account-compatibility-policy.md) (the seven-field `AccountPin`, signature-capability binding), [11 §4](11-dual-cap-model.md) (quote schema, signer-set emergency removal), [12 §5](12-router-lifecycle-and-migration.md) (predicates, shared-allowance modes, snapshot), [13 §7](13-eip7702-delegation-inspection.md) revalidation, [18](18-configuration-records.md) | **Drafted** (0.5); no owner review recorded |
| C-2 | **Wallet-lab evidence** of §9: EVL-01…EVL-10 (the freeze subset; EVL-11…EVL-15 gate mode enablement and R6) produced and reviewed | **Not produced (0 / 10)**; `evidence/wallet-lab/` is empty |
| C-3 | **Pinned Permit2 source review** of §5 (PR-01…PR-16) at E2, the rebuild comparison, and the **freeze subset of its fork tests** (RV-T01, 02, 04, 05, 07, 11 on a plain EOA, and MIG-TV-22/40) passing | **Partly done, not met.** Done: commit pinned; answers to PR-01…16 recorded from an automated read with citations (E1, pinned); deployed code read from three chains; selector audit clean. **Done since:** the rebuild comparison (reproduced, `evidence/permit2/rebuild.json`) and the fork subset (RV-T01, 02, 04, 05, 07, 11 and MIG-TV-22/40 on Ethereum mainnet, Base, Arbitrum One, `evidence/implementation/fork-runs.json`). **Not done:** E2 sign-off by two named reviewers (0 / 16) |
| C-4 | Every production-blocking constant of §7 approved **as its own configuration record** ([18](18-configuration-records.md)) | **0 / 18 approved** (17 constants of 0.4 plus PC-18; all `PROPOSED`) |
| C-5 | Every freeze-blocking unresolved decision of §3 closed | **Open** (12 of 12) |
| C-6 | Every freeze-blocking external fact of §4 closed or carried as a recorded risk with an owner | **Open** (9 of 9) |
| C-7 | Two independent planner implementations pass TV-01…36, TV-PO-1…12, CAP-TV-01…32, DRV-01…25, ACP-TV-01…44, MIG-TV-01…45 | **Not built** |
| C-8 | Audit scope of §8 agreed with both audit firms; slots contracted | **Not started** |
| C-9 | **Executable suites:** the Foundry suites of [foundry/](foundry/) (exported vectors, fuzz, invariant, mutation, integer-width, timestamp-boundary, shared-allowance) compile and pass against the reference model, and the fork subset passes against Permit2 | **Recorded** (`foundryReport` in the register): the suites compile under Foundry v1.8.5 / solc 0.8.24 and 278 tests pass, 0 fail (21 suites; the fork suites are run separately and pass on three chains, [implementation evidence report](evidence/implementation/REPORT.md)). This is a test run of the reference model, not an approval and not a test of contracts |
| C-10 | Sign-offs by the Principal Architect, the CISO (veto), the VP Engineering and the QA Lead (§10) | **None given** |
| C-11 | The **EIP-712 type strings are frozen**: the Wallet Protocol Engineer and the Solidity Lead approve the fingerprint of [eip712/TYPES.md](eip712/TYPES.md) (computed from [eip712/types.json](eip712/types.json); a later change of any string voids the approval) | **Not approved**; the strings are a proposal (FZ-22, [14 §8](14-protocol-freeze-pack.md) point 5) |

The freeze may be approved only when all eleven are satisfied. A condition that cannot be satisfied may be carried as a **recorded risk** only if it is not marked freeze-blocking below and the CISO accepts it in writing. **Nothing in this report marks the freeze approved; the shared-allowance migration rework, the account-pin semantics, the pinned Permit2 review and the wallet-lab evidence are each still open or unreviewed (C-1, C-2, C-3).**

## 2. Accepted decisions

"Sponsor-accepted" means the sponsor directed or accepted the direction in writing in the conversation record. "Specified, review pending" means the direction is accepted but the specification in this workspace has not been reviewed or approved by the owners; its ADR is `Proposed`.

| DEC | Decision | Basis | Specified in | Status |
|---|---|---|---|---|
| DEC-01 | `PaymentRouter` and `MandateManager` are immutable and versioned; router lifecycle with immutable minimum notice | Directive of 2026-10-13 (item 3) | [06 ADR-001](06-initial-architecture.md), [12 §3](12-router-lifecycle-and-migration.md) | Sponsor-accepted; specified, review pending |
| DEC-02 | Dual cap model: on-chain per-token hard caps plus fiat caps through signed expiring quotes with bounded inputs | Directive (item 4) | [11](11-dual-cap-model.md) | Sponsor-accepted; specified, review pending |
| DEC-03 | Direct stablecoin settlement ON in v1.0; **conversion code absent from Router v1**; conversion as a separately audited Router v1.1 adopted by opt-in; general-token conversion only after audit and token-lab approval | Directive (item 1) and correction 1 | [09](09-capability-boundaries.md), ADR-013 | Sponsor-accepted |
| DEC-04 | Migration is mandate lineage; a successor needs a router-specific customer authorization and the old router permission revoked | Correction 2 | [12 §5](12-router-lifecycle-and-migration.md), ADR-015 | Sponsor-accepted; **v0.4 predicates specified, review pending** |
| DEC-05 | **Account Compatibility Policy** replaces backend-only revalidation: five account modes, a permission matrix (unattended charges only in verified modes), an on-chain account pin, backend revalidation for what the chain cannot see | v0.4 instruction (item 1) | [17](17-account-compatibility-policy.md), ADR-018, OD-029 (reversed) | Sponsor-accepted direction; specified, review pending |
| DEC-06 | `activateSuccessor` has exact boolean predicates; a migration snapshot is computed on chain; migration cannot increase expiry, merchant scope, token scope, remaining caps, fee cap or slippage cap; cycle identity is independent of the router | v0.4 instruction (items 2 and 3) | [12 §5.3](12-router-lifecycle-and-migration.md), [11 §3.1](11-dual-cap-model.md) | Sponsor-accepted direction; specified, review pending |
| DEC-07 | `PriceQuote` v1 has fifteen fields, versioned signer sets with rotation, and a non-override proof | v0.4 instruction (item 4) | [11 §4](11-dual-cap-model.md), ADR-016 | Sponsor-accepted direction; specified, review pending |
| DEC-08 | Schedule dependencies are explicit FS, SS and FF with lags; the Monte Carlo runs at work-package level; results are labeled exploratory | v0.4 instruction (item 5) | [07 §3](07-delivery-plan.md), [jira/dependencies.csv](jira/dependencies.csv) | Sponsor-accepted; implemented |
| DEC-09 | `program` stays an epic profile and is restricted to coordination; delivery work belongs to the feature, protocol, security, data, compliance, infrastructure and migration profiles | v0.4 instruction (item 6) | [07 §6.2](07-delivery-plan.md), [jira/revisions_v04.py](jira/revisions_v04.py) | Sponsor-accepted; implemented and linted |
| DEC-10 | Primary Permit2 revocation flow is `Permit2.lockdown` by transaction, backed by fork tests RV-T01…12; the signed zero-amount permit stays disabled until ZP-T01…08 and the wallet lab pass | v0.4 instruction (item 7) and correction 7 | [05 §2.2](05-evm-authorization-decision-tree.md), ADR-019 | Sponsor-accepted; tests specified, not run |
| DEC-11 | Epic profiles replace the universal six-story-type rule | Correction 5 | [07 §6.2](07-delivery-plan.md) | Sponsor-accepted; implemented |
| DEC-12 | Pay Once (`SignatureTransfer`) and recurring (`AllowanceTransfer` plus mandate) are separate protocols | Directive | [10](10-pay-once-protocol.md), ADR-014 | Sponsor-accepted; specified, review pending |
| DEC-13 | MetaMask is `documented` (E1) and lab `UNTESTED`; Trust Wallet is `UNKNOWN`; no wallet support or deployment claim is made without E3 evidence | Directive | [15](15-wallet-lab-matrix.md), [02](02-source-register.md) | Sponsor-accepted |
| DEC-14 | FastPay ships no EIP-7702 delegate and never requests an authorization; wallet-managed upgrades are preferred and inspected; delegation is described as persistent | Directive (item 2) | [13](13-eip7702-delegation-inspection.md), ADR-007 | Sponsor-accepted |
| DEC-15 | No mainnet deployment is started; no final legal or security approval is claimed | Master prompt | all | Standing constraint |
| DEC-16 | The v0.4 direction is **accepted for testnet engineering**; protocol freeze remains blocked until the conditions of §1 are met | Sponsor instruction of 2026-10-16 | this report | Sponsor-accepted |
| DEC-17 | A Permit2 allowance is shared by every mandate of a customer on a router and token; `activateSuccessor` has **normal** and **emergency** migration, an on-chain exposure index, and never unfunds a sibling in normal mode | Sponsor instruction of 2026-10-16 (item 1) | [12 §5.3](12-router-lifecycle-and-migration.md), ADR-015 | Sponsor-directed; specified, review pending; open points OD-035 |
| DEC-18 | `AccountPin` is a seven-field typed struct with a stated split between what the contract verifies and what stays off chain; ERC-1271 evidence is bound to the pin and invalidated on any delegate, implementation, wallet-version or code-hash change | Sponsor instruction (items 2 and 3) | [17 §5](17-account-compatibility-policy.md), ADR-018 | Sponsor-directed; specified, review pending; open points OD-037 |
| DEC-19 | A compromised quote signer gets no grace period; planned rotation honors only previously issued quotes for a bounded period | Sponsor instruction (item 5) | [11 §4.7](11-dual-cap-model.md), ADR-016 | Sponsor-directed; specified, review pending; OD-036 open |
| DEC-20 | The roadmap is split into three tiers: testnet reference implementation, private mainnet beta, full GA platform, each with P50/P75/P90 per milestone | Sponsor instruction (item 6) | [07 §3](07-delivery-plan.md) | Sponsor-directed; implemented; exploratory |
| DEC-21 | The production-blocking constants are individually approved configuration records | Sponsor instruction (item 7) | [18](18-configuration-records.md) | Sponsor-directed; records drafted, none approved |

The estimate and the schedule are not decisions; they are labeled exploratory ([07 §3](07-delivery-plan.md)).

## 3. Unresolved decisions

"Freeze" = freeze-blocking (must be closed before RG-016); "Later" = needed by the gate shown. Recommendations are mine and unapproved.

| UD | Decision | Options | Recommendation | Owner | Needed | Freeze |
|---|---|---|---|---|---|---|
| UD-01 | **Production-blocking constants** (§7), 18 values (the 17 of 0.4 plus `MAX_EXPOSED_TOKENS_PER_ROUTER`, PC-18) | See §7 and [18](18-configuration-records.md): each is its own record | See §7 | Principal Architect, Head of Security, Head of Compliance | Freeze | **Yes** |
| UD-02 | OD-003 charge authentication tier (executor-only, merchant-held signer, tiered) | (a)(b)(c) | (c) tiered; the interface of `ChargeRequest` depends on it | Principal Architect + Merchant PM | Freeze | **Yes** |
| UD-03 | OD-007 refund funding and `RefundManager` interface | (a) merchant pushes; (b) bounded pre-authorization; (c) reserve | (b) with merchant-signed requests, (a) fallback | Payments PM + Compliance | Freeze | **Yes** |
| UD-04 | CF-002 `activateBySig` calls token `permit` and Permit2 `permit` itself, or a fixed-shape `ActivationHelper` | Manager or helper | Decide with the external-call allowlist (I-EXTCALL) in view; a helper keeps the manager's call surface smaller | Principal Architect | Freeze | **Yes** |
| UD-05 | OD-023 governance and guardian structure: roles are frozen; thresholds, signers, timelock minimum | Per OD-023 | Roles as in [04 §5](04-context-and-trust-boundaries.md); delays are production-blocking constants (PC-14) | Head of Security | Freeze (delays) | **Yes** |
| UD-06 | OD-028 delegation allowlist governance (evidence, approvers, retest) | Per OD-028 | E3, two approvers, pinned code hash and probe fingerprint ([13 §8](13-eip7702-delegation-inspection.md)) | Wallet Protocol Eng + Security | Freeze | **Yes** |
| UD-07 | OD-032 which account modes are ON at launch | (a) all, (b) `PLAIN_EOA`, (c) `PLAIN_EOA` plus rows as the lab produces them | (c) | Head of Product + Wallet Protocol Eng | Freeze | **Yes** |
| UD-08 | Quote signer set threshold (k-of-n) versus any single registered signer | k-of-n or any-of | Any-of with ≥2 keys held by independent custodians and immediate no-grace removal (KR-4/KR-8, [11 §4.7](11-dual-cap-model.md)); revisit with data | Principal Architect + Security | Freeze (verifier logic) | **Yes** |
| UD-09 | Pin for contract accounts and proxy delegates: bytecode only, or a registry-listed `implementationOf` reader | [17 open point 1](17-account-compatibility-policy.md) | Bytecode only in v1 (no external call in `consume`); the delegate's code hash is checked by opcode; contract modes OFF until rows exist | Principal Architect | Freeze | **Yes** |
| UD-10 | OD-001 operating entity and licensing route | (a)(b)(c) | Do not choose before the counsel memo; contracts stay neutral | Head of Compliance | RG-008 | No |
| UD-11 | OD-017 Layer-2 horizon (13 months) and renewal prompts | Fixed or tiered | Start at 13 months; Risk may shorten | Principal PM | Planner parameter | No |
| UD-12 | OD-022 merchant recipient change delay and approvals | Delay and parties | ≥ 48 h, two-party (the minimum is PC-17) | Merchant PM + Risk | Freeze (minimum) | **Yes** |
| UD-13 | OD-025 conversion governance (v1.1) | Per OD-025 | As [09 §4–§6](09-capability-boundaries.md) | CISO + HoC | v1.1 | No |
| UD-14 | OD-031 squad shape, contractors, scope | [07 §2.3](07-delivery-plan.md) | Rebalance and contractors on the contract and core path | VP Eng + Head of Product | Before the audit start | No (affects dates only) |
| UD-15 | Audit firm split (by contract set or by emphasis) and formal-verification tool | [14 §8](14-protocol-freeze-pack.md) | Money flow versus lifecycle and signatures; tool chosen by the firms | Head of Security | Before the audit start | No |
| UD-16 | Whether the experimental zero-amount permit is ever worth enabling | After ZP-T and WL-31 | Decide only on evidence | AA/Protocol Eng | After the fork tests | No |
| UD-17 | OD-037 `AccountPin` shape: `delegateCodeHash` checked in `consume` (second cold `EXTCODEHASH`) or only at activation and signed messages; pin per mandate with a batch update, or per customer; `implementationFamily` a signed label or attested by an on-chain registry | [17 §11](17-account-compatibility-policy.md) points 5–7 | Per mandate with batch update; `delegateCodeHash` in `consume`; label only (no new contract) | Principal Architect + Solidity Lead | Freeze | **Yes** |
| UD-18 | OD-035 Shared-allowance mode boundary: `SECURITY` deprecation is `EMERGENCY` (interrupts siblings) or `NORMAL`; whether normal migration also requires a right-sized residual rather than only a bounded one | [12 §15](12-router-lifecycle-and-migration.md) points 6, 7 | `SECURITY` is `EMERGENCY`; `Bounded` on chain, right-sizing in the planner | Principal Architect + Head of Security + Product | Freeze | **Yes** |
| UD-19 | OD-036 Whether the guardian may promote a pre-registered standby signer set after an emergency removal (shortens the recovery from the 72 h timelock) | [11 §4.7](11-dual-cap-model.md) KR-9 | No (guardian stays stop-only) | Head of Security | Before the audit | No |

## 4. Unverified external facts

Each row is a fact the design stands on that no one has verified at the level needed. "If adverse" says what would change. Evidence levels are those of the [README](README.md).

| UX | Fact | Evidence now | Needed | If adverse, what changes | Closing evidence | Freeze |
|---|---|---|---|---|---|---|
| UX-01 | An allowance is usable in the block whose timestamp equals its expiration; `transferFrom` reverts only if `block.timestamp > expiration` | **E1 pinned** (`AllowanceTransfer.sol:79` at `cc306b6`, automated read; §5.3 PR-07) | E2 + E3 | The predicate `Unusable ≡ a = 0 ∨ e < now` shifts by a second; MIG-TV-22 changes | PR-07, PR-08; RV-T04; MIG-TV-22 | **Yes** |
| UX-02 | `lockdown`, `approve(…,0,0)` and `invalidateNonces` act on the **caller's** allowances; `lockdown` sets amount to 0 and leaves expiration and nonce; `invalidateNonces` rises by at most 65,535 | **E1 pinned** (`AllowanceTransfer.sol:97-126`; PR-05, PR-06) | E2 + E3 | The primary revocation flow and the old-permission predicates (O1N, O1E) change | PR-04…PR-06; RV-T01…T12 | **Yes** |
| UX-03 | A signer with code is verified only via ERC-1271; there is no `ecrecover` fallback | **E1 pinned** (`SignatureVerification.sol:26-45`; PR-09) | E2 + E3 | The `sig1271` gate, signature transports and ZP-T06 change | PR-09; WL-12; ZP-T05/06 | **Yes** |
| UX-04 | `SignatureTransfer` signs `msg.sender` as spender; the destination `to` is not signed; the witness type string must follow the stated format | **E1 pinned** (`PermitHash.sol:85-94`; PR-10) | E2 | Pay Once binding of the recipient through the witness | PR-10, PR-11; PO fork tests | **Yes** |
| UX-05 | `EXTCODEHASH` of a delegated account is `keccak256(0xef0100 ‖ delegate)`, of an unused account 0, of a funded account `keccak256("")`, on each launch chain and in a type-4 transaction | E1 (EIP text) | E3 | The pin predicate and the sentinel `PIN_EOA` change | EV-P10, EV-P13; WL-33 | **Yes** |
| UX-06 | MetaMask: which delegate it installs, whether the upgrade persists, how a customer reverts it | E1 documentation (names no delegate, states no persistence) | E3 | Mode classification, allowlist row, copy | WL-05, WL-11, WL-11b, WL-15 | **Yes** (first rows) |
| UX-07 | Whether any wallet's delegate or any smart-account wallet validates **real Permit2 signatures** via ERC-1271 | Unknown | E3 | Default of `sig1271`; whether signature transports and the MIXED migration stay in v1.0 | WL-12, WL-30 | **Yes** |
| UX-08 | Whether the post-upgrade delegate can be named in advance (`expectedDelegateAfterUpgrade`) | Unknown | E3 | The `ATOMIC_READY` upgrade path is not requested (TV-30) | WL-34 | No (fallback exists) |
| UX-09 | EIP-712, EIP-1193, EIP-1271, EIP-5792 and EIP-7702 texts say what the claims say (error codes, status codes, persistence, opcode behavior) | E1 (tool-summarized) | E2 | Planner status mapping; revalidation wording | RP-01 | **Yes** |
| UX-10 | Permit2 treats an undeployed signer as an EOA (no ERC-6492) | Inferred | E2 | Counterfactual-account handling | PR-12 | No |
| UX-11 | Permit2 bytecode on each launch chain equals the pinned build | **E3 for what is deployed** (same 9,152-byte runtime code on Ethereum, Base and Arbitrum One; differs only in two immutables; masked hash equal; §5.2). **Source-to-bytecode match reproduced** (the CREATE2 address and every byte of the deployed code except the two immutables, on three chains; [implementation evidence report](evidence/implementation/REPORT.md) §8) | E3 (rebuild, CREATE2 address check) | Chain list; `permit2.verified` gate; the per-chain hash is not constant | EV-P01, EV-P14 | No (RG-004) |
| UX-12 | Trust Wallet capabilities | None found | E3 | Nothing in the protocol; only the launch claim | Discovery run EVL-09 | No |
| UX-13 | Token behavior for launch tokens (approve-zero-first, no-return, hooks, upgradeability) | E0 | E3 | Token eligibility; revocation flows per token | EV-P04, EV-P11 | No (listing) |
| UX-14 | Finality, reorg history and EVM version of the first mainnets | E0/E1 | E2/E3 | Backend finality constants; possible opcode limits | RP-04, RP-22 | No |
| UX-15 | Audit firms' slots, prices and the premium for lineage migration and quote verification | E0 | Quotes | Dates; scope split | RP-16 | No |
| UX-16 | Regulatory perimeter and notice duties for router migration | None | Counsel letters | Notice constants (PC-01/02); licensing route | RP-09, RP-26 | **Yes** for PC-01/02 only |
| UX-17 | Whether a wallet **version update** changes the delegate address or its code hash (visible to the pin) or only a proxy implementation or storage (invisible to the chain, caught by layer B) | None | E3 (two successive builds) | Which signature-capability triggers the chain catches and which only the backend does ([17 §5.6](17-account-compatibility-policy.md)); weight on layer B | WL-38, WL-37; EVL-15 | No (the design covers both outcomes) |
| UX-18 | `EXTCODEHASH` of a delegate address is stable on the launch chains: its code cannot be replaced at the same address (EIP-6780 semantics of `SELFDESTRUCT`) | E1 (EIP text; per-chain adoption not checked) | E3 per chain | The `delegateCodeHash` check in `consume` would not detect a redeploy; only layer B would (ASM-036) | WL-37; per-chain fork test | **Yes** (the pin design depends on it) |

## 5. The pinned Permit2 source review

**Purpose.** Replace E1 (retrieval-tool summaries of a branch tip) with E2 for every Permit2 claim the design stands on, then hand each claim to a fork test. **Status in 0.5: the commit is pinned, every PR item has an answer with file and line citations from an automated read of the pinned source, and the deployed code was read from three chains; the rebuild comparison and the fork subset are done ([implementation evidence report](evidence/implementation/REPORT.md)); the named-human E2 sign-off is not, so condition C-3 is not met.**

### 5.1 The pin

Machine-readable record: [evidence/permit2/pin.json](evidence/permit2/pin.json); re-checked by `python -I spec/tools/permit2_pin_check.py [--online]` (SRC-003).

| Item | Value |
|---|---|
| Repository | `Uniswap/permit2` |
| **Pinned commit** | **`cc306b601f172c51bc04334a109e98340456620b`** (2022-11-17, "feat: fix docs link (#152)"), tree `0d35aeb758e99510961089df8f7dfd94b256e58f` |
| Why this commit | The repository's own tag named `0x000000000022D473030F116dDEE9F6B43aC78BA3` (the canonical Permit2 address) points at it. **A tag label is a hint, not proof** that the deployment was built from it (§5.5) |
| Branch head when read | `main` = `cc56ad0f3439c502c246fc5cfcc3db92bb8b7219` (2023-09-29), 19 commits later. In the three deployed contracts the later commits change only import paths, add the `IEIP712` interface with `override`, and remove two comments; `Permit2Lib.sol` (a library, never deployed) is rewritten. No logic of `AllowanceTransfer`, `SignatureTransfer`, `EIP712` or `SignatureVerification` differs (read from the compare patch). The audited-and-deployed question is therefore about the pin, and the head is informational |
| Compiler settings at the pin | `solc 0.8.17`, `bytecode_hash = none`, `optimizer = true`, `via_ir = true`, `optimizer_runs = 1000000` (`foundry.toml`); EVM version not stated in `foundry.toml`: the rebuild used `london` and reproduced the canonical address |
| What was read | 17 files (`src/**/*.sol`, `foundry.toml`, `README.md`, `remappings.txt`); for each, the Git blob SHA-1 computed locally **equals** the one in the repository tree at the pin (integrity of the text read), and a SHA-256 is recorded |
| Also present at the pin, not read | `audits/ABDKAudit.pdf`, `audits/Chainsecurity.pdf`; `script/DeployPermit2.s.sol` (read: deploys with `new Permit2{salt: SALT}()` and `SALT = 0x…d3af2663da51c10215000000`, a CREATE2 deployment, so the vanity address commits to the creation code, §5.5) |

### 5.2 The deployed code (evidence E3 for what is deployed)

`eth_getCode(0x000000000022D473030F116dDEE9F6B43aC78BA3)` read at one block per chain from at least two independent providers (five on Ethereum):

| Chain | Block | Providers agreeing | Runtime code length | `keccak256(code)` |
|---|---|---|---|---|
| Ethereum 1 | 26,200,868 | 5 | 9,152 bytes | `0xc67d1657868aa5146eaf24fb879fb1fdec3d2d493b3683a61c9c2f4fb2851131` |
| Base 8453 | 52,657,059 | 2 | 9,152 bytes | `0xa67739abc3ede9dbdc0491636c67d6a14ac07fab9030c3f509b1eb7b11dff8ed` |
| Arbitrum One 42161 | 515,194,580 | 2 | 9,152 bytes | `0x9e51dcb64cf56fc09a82cb41edbc17c6a2250f18dbd1b91e884c0aca02acd57c` |

**The three hashes differ, and they must:** `EIP712.sol:10-20` stores `_CACHED_CHAIN_ID` and `_CACHED_DOMAIN_SEPARATOR` as **immutables**, which the compiler writes into the runtime code. The code is identical byte for byte except two 32-byte words at offsets 6,945 (chain id) and 6,983 (domain separator); each word equals the value derived from `EIP712.sol` (`keccak256(abi.encode(typeHash, keccak256("Permit2"), chainid, address))`; the type hash has **no version field**). With those two words zeroed the three chains give the same **masked hash `0x463331fa7a0d5f07488e42c37b461bb56a822145c161a821fbafe7d4e916b546`**. Consequences for the specification: a per-chain code hash is **not** a chain-independent constant (PC-13, EV-P01: the comparison must mask the immutables or rebuild per chain); `permit2CodeHash` in the chain configuration is stored per chain.

**Selector audit.** Every 4-byte `PUSH4` value in the Ethereum dispatcher is one of the 15 external functions of the pinned source (`allowance`, `approve`, two `permit`, two `transferFrom`, `lockdown`, `invalidateNonces`, `DOMAIN_SEPARATOR`, `nonceBitmap`, four `permit*TransferFrom`, `invalidateUnorderedNonces`); no other selector is present. So the deployed contract has **no admin, upgrade, pause or additional function** (PR-15, PR-16 at the bytecode level; the same dispatcher is on the other chains because the masked code is identical).

### 5.3 The answers (PR-01 … PR-16)

Each answer cites file and line at the pin. **Status of every row: answered from an automated read (E1, pinned); E2 needs two named reviewers to read the same passages independently; the fork test named in the last column is not run.** No answer contradicts an earlier E1 claim.

| PR | Answer at `cc306b6` | Citation | Decision it feeds / fork test |
|---|---|---|---|
| PR-01 | The domain is `EIP712Domain(string name,uint256 chainId,address verifyingContract)` with name `"Permit2"` and **no version**. The separator is cached in an immutable with the chain id; `DOMAIN_SEPARATOR()` returns the cache only if `block.chainid` equals the cached chain id and rebuilds it otherwise, so a chain fork cannot replay across chain ids. The two immutables appear in the deployed code at the offsets above with the expected values | `EIP712.sol:10-33`; deployed code §5.2 | Cross-chain replay; fork test on two chain ids |
| PR-02 | `approve(token, spender, amount, expiration)` writes `allowance[msg.sender][token][spender]`: amount and expiration **overwrite** the stored values (so a later `approve` for the same router changes everything every sibling mandate relies on); **`expiration = 0` stores `block.timestamp`** (the allowance is usable only in that block); the nonce is untouched; event `Approval` | `AllowanceTransfer.sol:26-30`; `libraries/Allowance.sol:34-42` | R-L2-NO-MAX; R-L2-SHARED (F2); ZP-T02; RV-T08 |
| PR-03 | `permit(owner, PermitSingle, signature)`: (1) `block.timestamp > sigDeadline` reverts `SignatureExpired`; (2) `signature.verify(hash, owner)`; (3) `_updateApproval`: `allowed.nonce != nonce` reverts `InvalidNonce`, then amount, expiration (0 → `block.timestamp`) and `nonce + 1` are stored in one word; event `Permit`. **Anyone may submit**; there is no `msg.sender` check; the spender is inside the signed data | `AllowanceTransfer.sol:33-40, 131-142`; `libraries/Allowance.sol:13-30` | Activation by signature; replay; ZP-T01/03/04 |
| PR-04 | `transferFrom` reads `allowance[from][token][msg.sender]`, so **the caller is the spender**; reverts `AllowanceExpired(expiration)` iff `block.timestamp > expiration`; reverts `InsufficientAllowance(max)` if `amount > stored`; **`uint160.max` is never decremented**; the stored amount is decreased **before** the token call; then solmate `safeTransferFrom(from, to, amount)` | `AllowanceTransfer.sol:59-94` | Charge pulls; R-L2-NO-MAX; shared budget (F4); RV-T01/02 |
| PR-05 | `lockdown(TokenSpenderPair[])`: the owner is `msg.sender`; for each pair **only `amount` is set to 0**; expiration and nonce are untouched; event `Lockdown(owner, token, spender)` (token and spender not indexed); no array-length restriction | `AllowanceTransfer.sol:97-110` | **Primary revocation flow**; sibling effect (F3); RV-T01/03/05/06 |
| PR-06 | `invalidateNonces(token, spender, newNonce)`: owner is `msg.sender`; reverts `InvalidNonce` unless `newNonce > old`; reverts `ExcessiveInvalidation` if `newNonce − old > type(uint16).max`, so **at most 65,535 per call**; event `NonceInvalidation` | `AllowanceTransfer.sol:113-126` | Killing unsubmitted signed permits; RV-T09/10 |
| PR-07 | An allowance is expired iff **`block.timestamp > allowed.expiration`**; it is therefore **usable in the block whose timestamp equals the expiration** and unusable one second later | `AllowanceTransfer.sol:79` | **Predicates O1N/O1E `Unusable ≡ a = 0 ∨ e < now`**; MIG-TV-22/40; RV-T04 |
| PR-08 | `PackedAllowance { uint160 amount; uint48 expiration; uint48 nonce }` is one storage word; `allowance(owner, token, spender)` is the public mapping getter and returns the stored triple unchanged | `interfaces/IAllowanceTransfer.sol:77-84`; `AllowanceTransfer.sol:23`; `libraries/Allowance.sol:45-47` | Planner input `permit2.{amount,expiration,nonce}`; verification V2 |
| PR-09 | `verify`: if `claimedSigner.code.length == 0` it accepts a 65-byte or a 64-byte (EIP-2098) signature through `ecrecover` (zero address → `InvalidSignature`, other address → `InvalidSigner`); **otherwise** it calls `isValidSignature(hash, signature)` and requires the magic value; **there is no `ecrecover` fallback for a signer with code**. A 7702-delegated account has code (length 23), so it takes the ERC-1271 path | `libraries/SignatureVerification.sol:21-46` | `sig1271` gate; ZP-T05/06; WL-12 |
| PR-10 | `permitWitnessTransferFrom` hashes `typeHash(stub ‖ witnessTypeString)`, the `TokenPermissions` hash, **`msg.sender` as spender**, `nonce`, `deadline` and `witness`. The destination `to` is **not** in the hash: the spender chooses it, so a recipient must be bound through the witness. The witness type string is supplied by the caller and **not validated** by Permit2 (it must follow EIP-712 ordering and include `TokenPermissions`) | `libraries/PermitHash.sol:31-32, 85-94`; `SignatureTransfer.sol:32-43` | Pay Once `PayOnceIntent`; S-1; PO fork tests |
| PR-11 | The unordered nonce bit is **consumed before the signature is verified**, in this order: deadline, requested amount ≤ permitted, nonce, signature, transfer. `invalidateUnorderedNonces(wordPos, mask)` ORs the mask into the **caller's** bitmap | `SignatureTransfer.sol:61-68, 132-158` | Pay Once replay; PO fork tests |
| PR-12 | A signer **without code** takes the `ecrecover` path, so an undeployed (counterfactual) contract account is treated as an EOA: a contract-signature fails with `InvalidSigner` or `InvalidSignature`; ERC-6492 is not supported | `libraries/SignatureVerification.sol:26-41` | Counterfactual accounts ([17 §2.2](17-account-compatibility-policy.md)) |
| PR-13 | Events: `Approval(owner, token, spender, amount, expiration)`; `Permit(owner, token, spender, amount, expiration, nonce)`; `Lockdown(owner, token, spender)`; `NonceInvalidation(owner, token, spender, newNonce, oldNonce)`; `UnorderedNonceInvalidation(owner, word, mask)`. **`transferFrom` and `permitTransferFrom` emit no Permit2 event**; a pull is visible only as the token's own `Transfer` event | `AllowanceTransfer.sol:29, 107, 125, 141`; `SignatureTransfer.sol:135`; `_transfer` has no `emit` | Indexer and verification V2/V5: pulls are indexed from **token** events and reconciled with `allowance` reads, not from Permit2 events |
| PR-14 | The token call is solmate `SafeTransferLib.safeTransferFrom` (handles no-return tokens) after the allowance state is updated; **Permit2 has no reentrancy guard of its own**, so a token with hooks can call back into the caller (the router) while a pull is in progress; the router's reentrancy and zero-balance guarantees (`I-ZEROBAL`) carry that risk, not Permit2 | `AllowanceTransfer.sol:86-93`; `SignatureTransfer.sol:68, 125` | ASM-022 (hook tokens excluded); token lab |
| PR-15 | **No** owner, admin, upgrade, pause, `delegatecall` or `selfdestruct` in `src/`; the only state is the allowance mapping, the nonce bitmap and two immutables; the deployed dispatcher exposes exactly the 15 functions of §5.2; deployment is CREATE2 with a fixed salt (`script/DeployPermit2.s.sol`). Audit PDFs (ABDK, ChainSecurity) are in the repository and were **not read** | `src/**` (grep); deployed code §5.2; `script/DeployPermit2.s.sol` | Trust assumption "immutable code the customer already trusts" |
| PR-16 | The functions that can change an owner's allowance, nonce or nonce bitmap are exactly: `approve`, `permit` (two overloads), `transferFrom` (two overloads, decrement only), `lockdown`, `invalidateNonces`, and, for the signature path, the four `permit*TransferFrom` and `invalidateUnorderedNonces`. The selector audit of §5.2 shows no other function exists in the deployed code | `AllowanceTransfer.sol`, `SignatureTransfer.sol`; deployed code §5.2 | Completeness of the revocation and authority model |

### 5.4 What the review changed in the design

1. **PR-02 and PR-05 make the shared allowance explicit.** `approve` overwrites amount and expiration and `lockdown` zeroes the amount for the pair `(token, spender)`; neither can be scoped to one mandate. This is the basis of the 0.5 migration rework ([12 §5.3.1](12-router-lifecycle-and-migration.md): facts F1…F6, normal and emergency migration, sibling mandates).
2. **PR-13: no Permit2 event on a pull.** Any design or runbook that waits for a Permit2 event to confirm a charge is wrong; confirmation is the token `Transfer` event plus the `allowance` read. (No document of this workspace relied on such an event; the indexer requirement is now explicit.)
3. **§5.2: the per-chain code hash is not constant** because of the two immutables; PC-13 and EV-P01 are restated with a masked hash.
4. **PR-07 confirms** the boundary of the 0.4 correction (`e < now`) at source level; it moves UX-01 from E1 (branch tip) to E1 (pinned commit) pending E2 and the fork test.
5. **No contradiction** of an earlier E1 claim was found, so RISK-034 is not triggered by this read; the open risk is that the read is automated and unreviewed.

### 5.5 What is not established, and how it closes

| Open item | Why it matters | How it closes (evidence) |
|---|---|---|
| **E2 sign-off.** Two named reviewers (the AA/Protocol Engineer and a Security reviewer) read the same passages independently and sign each PR row | An automated read can mis-summarize (G-03); E2 requires a named human | `humanReview` entries in `pin.json` (`reviewers`, `signedAt`, `level: "E2"`) for PR-01…PR-16 |
| **Rebuild.** Compile the pinned commit with the recorded settings and compare with the deployed code | The tag is a label, not proof | EV-P01. **A stronger check than comparing runtime code:** the address is a CREATE2 address (`SALT` in the deploy script), so rebuilding the creation code and deriving `keccak256(0xff ‖ deployer ‖ SALT ‖ keccak256(initCode))[12:]` must reproduce `0x000000000022D473030F116dDEE9F6B43aC78BA3` exactly; that proves source, compiler and settings in one step. Needs `solc 0.8.17` and the deployer address (not recorded here) — a toolchain the authoring environment does not have. Result goes to `rebuild.matches` in `pin.json`. **Result of 2026-10-16: reproduced** (`evidence/permit2/rebuild.json`; the build needs the whole compile unit of the repository, finding F-14) |
| **Fork tests.** RV-T01, 02, 04, 05, 07, 11 (plain EOA) and MIG-TV-22/40 against the canonical contract | Source text is not behavior (token interaction, account types) | [foundry/test/fork/Permit2Freeze.t.sol](foundry/test/fork/Permit2Freeze.t.sol) written, **not compiled or run**; results go to `forkReport` in `pin.json` |
| **Audit reports** (ABDK, ChainSecurity) read and their scope and findings recorded | Trust assumption PR-15 | Source Register entry; no claim is made from them today |
| **Other launch chains** beyond the three read | UX-11 | Same observation per chain, at least two providers |

**Fork tests.** For the freeze: RV-T01, 02, 04, 05, 07 and 11 on a plain EOA, and MIG-TV-22/40 (they decide the `lockdown` semantics, the usability boundary and the last-lineage cleanup of O1N). The full RV-T01…12 across token classes, chains and account types, and ZP-T01…08, belong to `EPIC-P1-REVOKE` and gate RG-002/RG-004.

**Output when complete.** The Permit2 behavior note (this section with E2 signatures), the Source Register update (SRC-003 and the CLM items upgraded to E2, G-09 and G-10 closed or restated), EV-P12, EV-P14 and EV-P15, and the fork-test reports. A contradiction of an E1 claim opens a CF item and RISK-034, and the affected predicates are changed together with the documents.

## 6. Testnet-safe constants

These may take **test values** on testnets, in a build tagged `-testconst`. The rules: (T-1) a `-testconst` build differs from the audited source **only** in the constants listed here (checked by a build-diff that masks them); (T-2) it is never promoted and carries the label UNAUDITED; (T-3) every behavior that depends on one of these constants is also run once on a fork with the production value and a time warp before the audit starts; (T-4) governance configuration (not code) differs freely.

| Constant | Production proposal | Testnet value | Kind | Why it is safe to vary |
|---|---|---|---|---|
| `MIN_NOTICE_STANDARD` | 180 days | 20 minutes | immutable in `RouterRegistry` | Only the speed of the lifecycle test changes; the guard logic is identical |
| `MIN_NOTICE_SECURITY` | 60 days | 10 minutes | same | same |
| `RETENTION` | 365 days | 1 hour | same | same |
| `ROLLBACK_WINDOW` | 30 days | 15 minutes | registry parameter | Governance-adjustable even in production |
| Timelock delay for propose/activate/deprecate | 72 hours | 2 minutes | governance configuration | Not contract logic |
| Merchant recipient change delay | ≥ 48 hours | 5 minutes | `MerchantRegistry` minimum | Test speed only |
| `MAX_QUOTE_TTL` | 300 seconds | 30 seconds | verifier / registry ceiling | Only the speed of the quote tests changes; the TTL check is identical |
| `QUOTE_SET_GRACE` | 300 seconds (`[MAX_QUOTE_TTL, 2·MAX_QUOTE_TTL]`) | 60 seconds (at least the testnet `MAX_QUOTE_TTL` of 30 seconds) | compile-time constant of the verifier library | Exercises rotation quickly; the emergency-removal path has no grace and is unaffected |
| `MAX_EXPOSED_TOKENS_PER_ROUTER` (PC-18) | 8 | 3 | immutable in `MandateManager` | Lets the `ExposureLimit` and the emergency-mode enumeration tests run with few tokens; the checks are identical |
| `FEE_CEILING_BPS` | to be set by Finance (OD-016) | any value that lets ceiling tests run | immutable in `FeeController` | A different ceiling does not change the check |
| Governance and guardian thresholds and signers | per OD-023 | 1-of-1 or 2-of-3 test keys | deployment configuration | Roles and separation are identical |
| Permit2 address per chain | verified canonical address | testnet address or a deployment from the pinned commit | constructor argument | Per-chain by definition |
| Backend: `EVIDENCE_TTL`, `MAX_OBSERVATION_AGE`, `RECHECK_BEFORE_SIGN`, `RETEST_GRACE`, `sigTtlSeconds`, finality constants, limits | per [13](13-eip7702-delegation-inspection.md), [07](07-delivery-plan.md) | shortened where it speeds testing | backend configuration | No contract effect |

## 7. Production-blocking constants

These are compile-time, immutable or practically unchangeable after deployment. Each needs a **decision record and evidence before the audited bytecode is final**; the audit covers the exact values. "Proposal" is mine and unapproved. **From 0.5 each constant is its own configuration record** ([18](18-configuration-records.md), data in [config/pc_records.json](config/pc_records.json)) with owner, unit, rationale, evidence, safe range, test, release gate and an approval block per approver; **none is signed** (0 of 18). The table below is the summary; the record is authoritative.

| PC | Constant | Proposal | Enforced where | Why it blocks | Decision and evidence needed | Owner | Status |
|---|---|---|---|---|---|---|---|
| PC-01 | `MIN_NOTICE_STANDARD` | 180 days | `RouterRegistry`, immutable | Governance can lengthen, never shorten; a wrong value strands customers or delays fixes | Counsel view on notice duties (RP-26); comprehension tests | Head of Compliance + Principal Architect | OPEN |
| PC-02 | `MIN_NOTICE_SECURITY` | 60 days | same | Same | Same; security-response analysis | Head of Security | OPEN |
| PC-03 | `RETENTION` before RETIRED | 365 days | same | Same | Support and legal retention analysis | Head of Compliance | OPEN |
| PC-04 | `MAX_BATCH` entries per migration-plan step (and mandates per pin batch; was: successors per authorization) | 10; safe range `[4, 20]`; measured on the contracts at the EVM schedule of the compiler's target, not on the chains | compile-time constant (`MigrationQueue`, `MandateGateway`) | Gas bound of a step (ADR-022): 50 does not fit, about 30 million gas | Fork gas measurement (RP-19) on the three chains | Solidity Lead | OPEN |
| PC-05 | `FEE_CEILING_BPS` | to be set by Finance | `FeeController`, immutable | The ceiling protects customers from fee changes forever | Unit-economics model with measured gas (PB-017) | Finance + Principal PM | OPEN |
| PC-06 | `MAX_QUOTE_TTL` | 300 seconds | verifier / registry ceiling | Bounds how stale a price attestation can be | Risk analysis with depeg replay (RP-14) | Risk Lead | OPEN |
| PC-07 | `MAX_BAND_WIDTH_BPS` (largest allowed width of a price band) | 500 bps | registry ceiling, immutable | Bounds the quote-signer blast radius B2 whatever governance does | Same | Risk Lead | OPEN |
| PC-08 | `QUOTE_SET_GRACE` | 300 seconds, safe range `[MAX_QUOTE_TTL, 2·MAX_QUOTE_TTL]`; bounds **planned rotation only** (a compromised signer gets no grace, [11 §4.7](11-dual-cap-model.md)) | compile-time constant | Rotation must not kill honest quotes nor leave retired keys valid | Rotation drill | Head of Security | OPEN |
| PC-09 | EIP-712 names, versions and type strings (`FastPay Quote`/`1`, `FastPay Mandates`/`1`, `PayOnceIntent`, `ActivationTerms`, `SuccessorAuthorization`, `AccountPinUpdate`, `AccountPinsUpdate` and the nested `AccountPin`; **the type strings of `ActivationTerms` and of the revoke, pause, reduce and resume messages are now written as a proposal in [eip712/types.json](eip712/types.json) and are not approved (FZ-22)**) and the hash tags (`fastpay.lineage.v1`, `.mandate.v1`, `.cycle.v1`, `.route.direct.v1`, `.pin.eoa.v1`, `.migration.snapshot.v1`) | As in documents 10, 11, 12, 17 | Contract constants | Any change breaks every signature and identifier; wallets display these names | Fingerprints FG-xx recorded; two implementations reproduce the vectors | Principal Architect | OPEN |
| PC-10 | Window lengths: DAY 86,400 s, WEEK 604,800 s, THIRTY_DAYS 2,592,000 s | As stated | Contract constants | Define every cap window grid | Product copy review ("per 30 days") | Payments PM | OPEN |
| PC-11 | `MAX_TOKENS_PER_MANDATE` | 3 | Contract array bound | Gas and audit bound | Usability and gas data | Product Designer + Solidity Lead | OPEN |
| PC-12 | `MAX_ROUTERS_LIVE` (ACTIVE or DEPRECATED per chain) | 2 | Registry guard | Limits phishing surface and campaign complexity | Migration rehearsal | Principal Architect | OPEN |
| PC-13 | Permit2 address per chain | Canonical address, verified | Constructor, immutable | A wrong address is catastrophic and cannot be fixed | EV-P01, EV-P14: runtime code from two RPCs per chain equals the pinned build **with the two per-chain immutables masked** (three chains; the rebuild reproduces it, [implementation evidence report](evidence/implementation/REPORT.md) §8) | Solidity Lead | OPEN |
| PC-14 | Timelock minimum delay and the guardian's powers | 72 h; stop-only | Deployment configuration, hard to change | Governance safety | OD-023 decided; ceremony rehearsal | Head of Security | OPEN |
| PC-15 | `PIN_EOA`, `KECCAK_EMPTY` handling in `PIN_OK`, and the `PIN_WELLFORMED` rules of the seven-field `AccountPin` | As [17 §5.1–§5.2](17-account-compatibility-policy.md) | Contract constants | Defines which accounts are charged and which pins can be stored | EV-P13 | Principal Architect | OPEN |
| PC-16 | Cycle rule: `cycleIndex ≤ floor((t − anchor) / periodSeconds)`, late cycles allowed | As [11 §3.1](11-dual-cap-model.md) | Contract logic | Defines settle-once identity forever | Payments PM sign-off for non-fixed plans (open point 6) | Principal Architect | OPEN |
| PC-17 | Minimum recipient-change delay | ≥ 48 hours | `MerchantRegistry`, immutable minimum | Protects customers from recipient swaps | UD-12 | Merchant PM + Risk | OPEN |
| PC-18 | `MAX_EXPOSED_TOKENS_PER_ROUTER` (**new in 0.5**: bounds the exposure index of [12 §5.3.1](12-router-lifecycle-and-migration.md)) | 8; safe range `[MAX_TOKENS_PER_MANDATE, MAX_BATCH · MAX_TOKENS_PER_MANDATE]` | compile-time constant of `MandateManager` | Too low blocks customers with many subscriptions (`ExposureLimit`); too high makes the emergency-mode enumeration's gas unbounded | Fork gas measurement (RP-19); data on tokens per customer (none yet) | Solidity Lead + Principal Architect | OPEN |
| PC-19 | `MAX_SIGNERS_PER_SET` (**new in 0.5, implementation evidence**: bounds the member loops of a quote-signer set, [11 §4.7](11-dual-cap-model.md)) | 16; safe range `[2, 64]` | compile-time constant of `SignerSetRegistry` | Too high: the activation of a replacement set (the emergency rotation) may not fit a block; too low: no key redundancy | Internal measurement (done on the contracts: the check is O(1)); fork measurement (RP-19) | Solidity Lead + Head of Security | OPEN |

**Backend-tunable, not blocking:** `EVIDENCE_TTL`, `MAX_OBSERVATION_AGE`, `RECHECK_BEFORE_SIGN`, `RETEST_GRACE`, probe gas budget, persistent-indeterminate thresholds, `sigTtlSeconds`, `l2HorizonSeconds`, default quote TTL (120 s), band widths inside the ceiling, limits and breakers, retry budgets, finality thresholds, cohort schedule, dunning.

## 8. Exact audit scope

Applies to **Router v1.0 and its registries** at a single commit and a single build, with the production constants of §7. Router v1.1, `ConversionPolicyRegistry`, adapters and the v1.1 manager are **not** in this audit (absent; separate later audit). The process rules are in [14 §5](14-protocol-freeze-pack.md).

### 8.1 In scope: contracts and external or public functions

| Contract / library | Functions (names; signature-level list is frozen with the specification) | What the auditors must examine |
|---|---|---|
| `MandateManager` | `activate`, `activateSuccessor`, `updateAccountPin`, `revoke`, `retire`, `pause`, `resume`, `reduce`, `setPauseBit`, `spendNonce`, `consume`; views `mandateView`, `pinHashOf`, `partiesOf`, `isConsumable`, `live`, `exposedCount`, `exposedAt`, `exposedUnionCount`, `lineages`, `usedNonce` | The predicates A1…O1N/O1E of [12 §5.3](12-router-lifecycle-and-migration.md) one by one (each with a passing and a failing case), the **router mode** derivation and the **exposure index** (never an under-count, bounded, updated in the same transaction as every transition), the claim that `activateSuccessor` writes nothing to Permit2 and no sibling; the snapshot and containment K.1…K.9 against Lemma M; the seven-field `AccountPin` (`PIN_WELLFORMED`, `PIN_OK` with the delegate's code hash, `pinVersion` monotonicity, `AUTH` and the signature mode) in `consume`, `activate*` and the pin updates; identifier derivations; counters and windows across generations; settle-once; pause semantics (exit never blocked); nonce and deadline handling of every signed message |
| `UsageLedger` | `charge` (the manager only), views | Only the manager can write; counters move if and only if `consume` succeeded; windows and lazy reset on the grid anchored at `anchorStartsAt`; the caps and the fee bound; the cycle record |
| `SuccessorValidator` | `validate` (view, called with STATICCALL) | Every predicate A3, R1…R3, X1, K1, G1, X2, C1/C2, O1N/O1E one by one; that it cannot write; that the manager re-checks the lineage constants and the exposure bound whatever it said |
| `MandateGateway` | `activateBySig`, `activateSuccessorBySig`, `revokeBySig`, `pauseBySig`, `resumeBySig`, `reduceBySig`, `updateAccountPinBySig`, `updateAccountPinsBySig`, `updateAccountPins` | Domain separation (the manager is the verifying contract); nonce spent before the call; the stored pin governs `AUTH`; exits accepted through either signature path; the gateway can do no more than the customer can |
| `MigrationQueue` | `open`, `step`, `skip`, `abort`, `expire` | The hash chain and its termination; that a step is atomic and bounded by `MAX_BATCH`; that the queue may call only `activateSuccessor`; authority of `open`, `skip` and `abort` |
| `PaymentRouter` v1 | `charge`, `chargeInitial`, `payOnceWithSignature`, `payOnceWithSignatureAndPermit`, `payOnce`, `payOnceWithAuthorization` | External-call allowlist; Permit2 pull; fee; recipient resolution at charge time; zero-balance guarantee; `minOut`; witness binding and nonce handling of Pay Once; quote consumption and use of only `(fiatValueMinor, quoteDigest)`; token quirks; no `tx.origin`; reentrancy |
| `RouterRegistry` | `propose`, `cancel`, `activate`, `deprecate`, `extendSunset`, `sunset`, `retire`, `emergencyDisable`, `clearEmergency`, `isChargeable`, `isBindable`, `markSettled`, views | Lifecycle monotonicity; immutable notice constants; at most two live routers; rollback window; consistency of `isBindable` and `isChargeable`; shared Pay Once settlement record |
| `TokenPolicyRegistry` | `list`, `setStatus`, `publishBounds`, `setPriceSourceSet`, `block_`, views `tokenVersion`, `quoteContext`, `bandOf`, `currentBoundsVersion` | `SWAP_ONLY` unlistable; version counters change exactly when [11 §4.7](11-dual-cap-model.md) says; bounds versions append-only and at most `MAX_BAND_WIDTH_BPS` wide (ADR-020); the guardian can only block; ceiling `MAX_QUOTE_TTL`, `MAX_BAND_WIDTH_BPS` |
| `SignerSetRegistry` | `proposeSignerSet`, `activateSignerSet`, `removeQuoteSigner`, `stopSignerSet`, view `verifySigner` | Signer-set rotation with a bounded grace for **previously issued quotes only**; **emergency removal with no grace, permanent tombstones, a set stop, and `proposeSignerSet` rejecting tombstoned keys** (SR-1…SR-7); guardian can only remove or stop and can never add; at most `MAX_SIGNERS_PER_SET` members; the check is O(1) (ADR-023) |
| `MerchantRegistry` | `register`, `proposeRecipient`, `acceptRecipient`, `setChargeSigner`, `pauseMerchant` | Delay and two-party approval; recipient swap during a pending charge |
| `ExecutorRegistry`, `FeeController`, `RefundManager`, `EmergencyGuardian` | `add`/`remove`; `setFee`; `refund`; `pauseCharge`, `pausePayOnce`, `blockToken`, `removeExecutor`, `removeQuoteSigner`, `stopSignerSet`, `emergencyDisableRouter` | Role separation; immutable fee ceiling; refund allowance bounds; the guardian can only stop |
| `QuoteVerifier` (library) | `verify` | Q1…Q20; digest and domain construction; ECDSA low-`s`; boundary conditions; overflow; replay across payments, payers, tokens, chains, routers; returns only `(fiatValueMinor, quoteDigest)` |
| `SignatureVerifier` (library) | ECDSA and ERC-1271 validation helpers | Malleability; `STATICCALL` without an artificial gas cap (CLM-032); return-data validation; reentrancy; ECDSA by the account key accepted for accounts with code (pin updates and revocations) |
| Deployment scripts and manifest schema | roles, timelocks, constants, bytecode verification, absence checks | Mis-set roles or constants; the `-testconst` diff rule |

### 8.2 Out of scope (stated in the engagement)

Permit2 (third-party; the **integration assumptions** in §4 UX-01…UX-04 are in scope); token contracts; wallets and delegates; the multisig implementation used for governance (its configuration is in scope); all backend services (code review and the penetration test); Router v1.1 and everything conversion-related; native-asset handling; ERC-3009 token behavior beyond the router's call.

### 8.3 Properties to attack

`I-MANDATE`, `I-CAP-TOKEN`, `I-CAP-FIAT`, `I-QUOTE`, **`I-QUOTE-NI`**, `I-BOUNDS-SNAPSHOT`, `I-ONCE`, `I-MINOUT`, `I-RECIPIENT`, `I-ZEROBAL`, `I-NOARB`, `I-EXTCALL`, `I-EXIT`, `I-ADMIN`, `I-REPLAY`, `I-TIME`, `I-SNAPSHOT`, `I-PO-NOSTANDING`, `I-PO-WITNESS`, **`I-MIG-1…11`**, `I-L2-NOMAX`, **`I-ACCT-PIN`**, **`I-ACCT-NOWIDEN`**, **`I-ACCT-SIG`**, **`I-ACCT-VERSION`**, **SR-1…SR-7** (signer sets), the on-chain part of `I-DELEG`. Formal verification or independent review of `I-CAP-TOKEN`, `I-CAP-FIAT`, `I-ONCE`, `I-MINOUT`, **`I-MIG-9`, `I-MIG-10` and `I-QUOTE-NI`** (PB-003).

### 8.4 Specific questions the auditors are asked to answer

1. Can any sequence of calls leave two routers able to pull under one lineage (I-MIG-8)?
2. Is there any input for which `Contained` is true and a payment accepted by the successor is rejected by the predecessor in the same state? (it must not be; Lemma M)
3. Can a stale signed `SuccessorAuthorization`, `AccountPinUpdate`, revoke or pause be replayed across chains, contracts, mandates or generations?
4. Can `updateAccountPin` change anything but the pin, or be used to widen a rejected payment?
5. Can a quote signer cause a charge that guards G1…G12 reject, or settle a cycle twice (I-QUOTE-NI, I-ONCE)?
6. Is the allowance-usability predicate exactly Permit2's, at the boundary (UX-01)?
7. Can any external call reach a target outside the allowlist, and is there any conversion selector or adapter reference (absence checks)?
8. Do the immutable constants of §7 hold at the values in the bytecode, and can governance or the guardian change any of them?
9. Can any sequence of activations, successors, revocations, retirements and token removals make the exposure index an **under-count** (`I-MIG-10`), and can an over-count ever make a normal migration retain an unbounded allowance or an emergency migration miss an exposed token?
10. Can `activateSuccessor` of either kind, or any other call made on behalf of one customer, change a sibling mandate, a sibling lineage or a Permit2 allowance (`I-MIG-11`)?
11. Is there an account state (code hash, delegate code hash, signature mode, pin version) for which an ERC-1271 signature is accepted although `PIN_OK` fails, or a pin update accepted with a non-consecutive `pinVersion` (`I-ACCT-SIG`, `I-ACCT-VERSION`)?
12. Can a removed quote signer be accepted in any set version at any time after its removal, re-registered, or revived by governance or the guardian (SR-1, SR-4, SR-7)?

### 8.5 What the auditors receive

The specification documents at the recorded fingerprints ([14 §2](14-protocol-freeze-pack.md)); the vectors (quote, snapshot, pin) and the tools that produce them; the Permit2 behavior note of §5; the invariant list and tests; the threat model; the absence-check procedure; deployment scripts; token behavior matrix; fork results; known issues; a one-business-day contact.

## 9. Exact wallet-lab evidence required

"Freeze" = needed to approve RG-016. Each row is a set of run records ([15 §4](15-wallet-lab-matrix.md)) on the exact wallet version and platform, reviewed by a second person, stored with checksums. **None has been produced.**

| EVL | Wallet and platform | Account (mode) | Tests ([15](15-wallet-lab-matrix.md)) | Evidence artifact | Pass criterion | Freeze |
|---|---|---|---|---|---|---|
| EVL-01 | MetaMask, Chrome extension | A0 (`PLAIN_EOA`) | WL-01, 02, 03, 04, 08, 09, 10, 32, 33 | Raw `wallet_getCapabilities` and `wallet_sendCalls` outputs per test chain; receipts; `EXTCODEHASH` values | Capability JSON captured for every chain; atomicity proven (WL-08); mode `PLAIN_EOA`; pins as [17 §5.1](17-account-compatibility-policy.md) | **Yes** |
| EVL-02 | MetaMask, Chrome extension | A1 (accept the upgrade prompt) | WL-05, 11, 11b, 33, 34, **37** | Upgrade prompt screenshots; delegate address, code hash, proxy and probes; designator hash; **`EXTCODEHASH(delegate)` across providers and restarts**; persistence observations | Delegate recorded from two RPCs; designator hash equals `keccak256(0xef0100 ‖ delegate)`; delegate code hash stable or its instability recorded (UX-18); whether the delegate can be named in advance (UX-08) | **Yes** |
| EVL-03 | MetaMask, Chrome extension | A1 | WL-12, **39** | Permit2 `PermitSingle` and witness signatures submitted on a test chain; **FastPay typed data signed through ERC-1271 and submitted to the reference contracts** | Accept or reject recorded with the revert path; matches [17 §2](17-account-compatibility-policy.md) `sig1271` rule (UX-03, UX-07); `AUTH` accepts while the pin holds and refuses after a delegate code-hash change (ACP-TV-38…40) | **Yes** |
| EVL-04 | MetaMask, Chrome extension | A1 | WL-14, 35 | Delegate-change, upgrade-after-activation and revert runs with the simulated `AccountCodeChanged` | Charge simulation reverts; re-verification with one signature resumes; revalidation diff sets match DRV-04…06, 10 | **Yes** |
| EVL-05 | MetaMask, Chrome extension | A1 | WL-15 | The wallet's revert-to-EOA path: steps, on-chain result, time | Code cleared (or the behavior recorded); instructions captured for the customer copy | **Yes** |
| EVL-06 | MetaMask, iOS | A0, A1 | WL-01…05, 11, 32, 33 | As EVL-01/02 on iOS | Discovery rows; differences from the extension recorded | **Yes** (discovery) |
| EVL-07 | MetaMask, Chrome extension | A0, A1 | WL-19 (candidate tokens), **40** | Token `approve(0)`, `lockdown`, `approve(…,0,0)`, `invalidateNonces` executed from the wallet; **the shared-slot `approve`, a partial and a full `lockdown`** | Each takes effect as RV-T specifies and as MIG-TV-30…34 specify for the shared allowance; wallet display and gas noted | **Yes** |
| EVL-08 | MetaMask, Chrome extension | A0, A1 | WL-16, 17, 18, **36** | Typed-data prompts for activation (with the nested `AccountPin`), successor authorization, `AccountPinUpdate`; transaction previews | Each named field (all seven of the pin) readable, or the wallet classified `opaque` with a UX constraint | **Yes** |
| EVL-09 | Trust Wallet, iOS/Android/extension | A0 (A1 if offered) | WL-01, 02, 04, 05, 06 | Raw capability output and `wallet_sendCalls` behavior | A first factual row; the verdict may remain `UNKNOWN` | **Yes** (discovery) |
| EVL-10 | Synthetic fixtures (no real wallet) | Hostile and swappable delegates, proxies, lying RPC | WL-08, 13, 14 with DRV-04…13, 24 and ACP-TV-03…44 | Fixture run logs | Every fixture is classified and handled as specified | **Yes** |
| EVL-11 | Coinbase Wallet / Base Account | A3 (`SMART_4337`) | WL-30, 32, 12 | Contract-account signature and mode classification | Decides whether `SMART_4337` can ever be ON; not needed to freeze | No (mode enablement) |
| EVL-12 | Safe{Wallet} | A3 (`WALLET_1271`) | WL-30, 32 | Same | Same | No (mode enablement) |
| EVL-13 | Ledger/Trezor through MetaMask | A4 | WL-21 | Typed-data display on the device | `hardwarePath` classified | No (R6) |
| EVL-14 | WalletConnect variants | per wallet | WL-22, 23 | Method pass-through | Separate register rows | No (R6) |
| EVL-15 | MetaMask, Chrome extension, **two successive builds** | A1 | WL-38 | Observations before and after the wallet update: delegate, delegate code hash, proxy implementation, probes, reported version | Each change mapped to a trigger of [17 §5.6](17-account-compatibility-policy.md); decides what the chain catches and what only layer B does (UX-17) | No (mode enablement) |

The Compatibility Register v0 built from EVL-01…EVL-10 is the exhibit for C-2. The experimental zero-amount permit (WL-31) is **not** needed for the freeze; the flag stays off.

## 10. Approval record

| Role | Name | Decision | Date | Conditions |
|---|---|---|---|---|
| Principal Blockchain Architect (accountable) | — | **NOT SIGNED** | — | C-1…C-11 |
| CISO (veto) | — | **NOT SIGNED** | — | |
| VP Engineering | — | **NOT SIGNED** | — | |
| QA Lead | — | **NOT SIGNED** | — | |
| Head of Product (informed) | — | — | — | |

## 11. How this report is maintained

The command `python -I spec/tools/check_all.py` runs all consistency checks (identifiers, links, vectors, fingerprints, the backlog generator, the executable model checks, the Foundry export and lint, the configuration records, the Permit2 pin record and the freeze-readiness lint). `python -I spec/tools/freeze_readiness.py` prints the eleven conditions of §1 from recorded evidence and **must report READY (`--require-ready`) before anyone records an approval in §10**; `python -I spec/tools/permit2_pin_check.py --online` re-reads the chains and the repository. When a document changes: run `python -I spec/tools/freeze_fingerprints.py --write` and `python -I spec/tools/sync_vectors.py --write`; update the status columns above from the Evidence Register; never change a status to "closed" without an `EV-` link. A freeze approved on this report is recorded in the gate register, and every later change to a fingerprinted section is a Freeze Change Request ([14 §7](14-protocol-freeze-pack.md)).
