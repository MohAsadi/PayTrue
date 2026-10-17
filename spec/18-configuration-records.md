# 18 — Production Configuration Records

| Field | Value |
|---|---|
| Artifact | FP-REL-005 |
| Version | 0.5.0 (new) |
| Date | 2026-10-16 |
| Status | DRAFT — **no record is approved.** 19 records: 0 approved, 19 proposed, 1 without a value (PC-05, `VALUE_PENDING`). Nothing here is audited, legally reviewed or tested on any chain |
| Owner | Principal Blockchain Architect (accountable), Technical Program Manager (register) |
| Reviewers | Head of Security (CISO, veto), Head of Compliance, Solidity Lead, Risk Lead, Finance, Payments PM, QA Lead |
| Dependencies | [16](16-freeze-decision-report.md) §7 (the constants) and §6 (testnet values), [14](14-protocol-freeze-pack.md) §2 and §7 (fingerprints, change control), [08](08-production-blockers-and-release-gates.md) (gates), [11](11-dual-cap-model.md), [12](12-router-lifecycle-and-migration.md), [17](17-account-compatibility-policy.md), [03](03-assumptions-decisions-risks.md) (OD-016, OD-022, OD-023, OD-026, OD-027, OD-034), [config/pc_records.json](config/pc_records.json), [tools/build_config_records.py](tools/build_config_records.py) |
| Source of this file | **Generated.** Edit `config/pc_records.json`, then run `python -I spec/tools/build_config_records.py --write`; `--verify` fails if this file differs from the data |
| Definition of Done | Every production-blocking constant of [16](16-freeze-decision-report.md) §7, and the constant added in 0.5, has a record with an accountable owner, a unit, a rationale, the evidence required, a safe range, its tests and its release gate; no record is `APPROVED` unless every required approver has signed it with a name, a date and an evidence id; the verifier passes |

**This register does not approve anything.** It turns each constant of [16](16-freeze-decision-report.md) §7 into a record that can be approved, one by one, by the people named in it. Today every record is `PROPOSED` and every signature slot is `NOT SIGNED`. A proposal is an unapproved number written down so that it can be reviewed; it is not a decision, and nothing in this workspace has been audited, legally reviewed, or tested on any wallet or chain.

**Why 19 records.** The sponsor's correction named 17 production-blocking constants (PC-01…PC-17 of [16](16-freeze-decision-report.md) §7). The shared-allowance rework of [12 §5.3.1](12-router-lifecycle-and-migration.md) needs a bound on the exposure index (PC-18 `MAX_EXPOSED_TOKENS_PER_ROUTER`, new in 0.5), and the implementation of the quote-signer sets needs a bound on the members of a set (PC-19 `MAX_SIGNERS_PER_SET`, new in the implementation evidence), so the count has become **19**. The 17 original records keep their numbers; PC-04 was re-measured on the actual contracts (ADR-022).

## 1. Overview

| PC | Symbol | Proposal | Unit | Owner | Gate | Status |
|---|---|---|---|---|---|---|
| PC-01 | `MIN_NOTICE_STANDARD` | 180 days | seconds (180 days = 15,552,000 s) | Head of Compliance; Principal Architect | RG-016 (evidence RG-008; latest RG-002) | PROPOSED |
| PC-02 | `MIN_NOTICE_SECURITY` | 60 days | seconds (60 days = 5,184,000 s) | Head of Security (CISO) | RG-016 (evidence RG-008; latest RG-002) | PROPOSED |
| PC-03 | `RETENTION` | 365 days | seconds (365 days = 31,536,000 s) | Head of Compliance | RG-016 (evidence RG-008; latest RG-002) | PROPOSED |
| PC-04 | `MAX_BATCH` | 10 | count (successors per plan step, or mandates per pin batch) | Solidity Lead | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-05 | `FEE_CEILING_BPS` | **VALUE_PENDING** (Finance, OD-016) | basis points | Finance; Principal PM | RG-016 (evidence RG-008; latest RG-002) | PROPOSED |
| PC-06 | `MAX_QUOTE_TTL` | 300 seconds | seconds | Risk Lead | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-07 | `MAX_BAND_WIDTH_BPS` | 500 bps | basis points | Risk Lead | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-08 | `QUOTE_SET_GRACE` | 300 seconds | seconds | Head of Security (CISO) | RG-016 (evidence RG-002; latest RG-002) | PROPOSED |
| PC-09 | 16 symbols (see the record) | Strings and tags exactly as in the record | exact strings; bytes32 tags | Principal Architect | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-10 | `DAY`, `WEEK`, `THIRTY_DAYS` | 86,400 / 604,800 / 2,592,000 s | seconds | Payments PM | RG-016 (evidence RG-008; latest RG-002) | PROPOSED |
| PC-11 | `MAX_TOKENS_PER_MANDATE` | 3 | count (tokens per mandate) | Product Designer; Solidity Lead | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-12 | `MAX_ROUTERS_LIVE` | 2 | count (routers per chain) | Principal Architect | RG-016 (evidence RG-006; latest RG-002) | PROPOSED |
| PC-13 | `PERMIT2` | Canonical address, verified per chain | address, per chain | Solidity Lead | RG-016 (evidence RG-004; latest RG-004) | PROPOSED |
| PC-14 | `TIMELOCK_MIN_DELAY`, `GUARDIAN_POWERS` | 72 h; stop-only | seconds; function set | Head of Security (CISO) | RG-016 (evidence RG-006; latest RG-002) | PROPOSED |
| PC-15 | `PIN_EOA`, `KECCAK_EMPTY` | As [17 §5.1](17-account-compatibility-policy.md) and [17 §5.2](17-account-compatibility-policy.md) | bytes32; rules | Principal Architect | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-16 | `CYCLE_INDEX_RULE` | `cycleIndex ≤ floor((t − anchor) / periodSeconds)`; late cycles allowed | seconds and cycle index | Principal Architect | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-17 | `MIN_RECIPIENT_CHANGE_DELAY` | at least 48 hours | seconds (48 hours = 172,800 s) | Merchant PM; Risk Lead | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-18 | `MAX_EXPOSED_TOKENS_PER_ROUTER` | 8 | count (distinct tokens per customer per router) | Solidity Lead; Principal Architect | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |
| PC-19 | `MAX_SIGNERS_PER_SET` | 16 | count (members per quote-signer set) | Solidity Lead; Head of Security (CISO) | RG-016 (evidence RG-016; latest RG-002) | PROPOSED |

## 2. Rules

**R-1 Approval.** A record is approved only by its own approval block: every required approver signs, and each signature carries a name, a date and at least one evidence id from the Evidence Register ([02](02-source-register.md)). A statement in a meeting, a value written in another document, a passing test on a testnet or an entry in this register is not an approval.

**R-2 Veto.** The Head of Security (CISO) is a required approver of every record and holds a veto on all of them: all 18 constants are immutable or practically unchangeable parts of `SECURITY-CRITICAL` or `FINANCIAL-CONTROL` documents. A veto stands until withdrawn in writing ([08](08-production-blockers-and-release-gates.md) §2, gate mechanics).

**R-3 Status.** `PROPOSED` is the only status this file carries today. `APPROVED` is set only when every slot of the record is signed; the verifier rejects it otherwise. `VALUE_PENDING` is allowed for PC-05 only: no number is proposed for the fee ceiling.

**R-4 Change after approval.** Changing an approved value is a change request, not an edit: a Freeze Change Request ([14](14-protocol-freeze-pack.md) §7) once the freeze is approved, a re-audit of the affected contract once the audit has started, and a redeploy of the immutable contract. The field `changeControl` of each record says what the change costs. Editing the JSON file of a record that is `APPROVED` without a new signed block is a defect.

**R-5 Testnet values are not evidence.** A `-testconst` build may differ from the audited source only in the constants of [16](16-freeze-decision-report.md) §6 (rule T-1); it is never promoted (T-2); the behavior that depends on each such constant is run once on a fork with the production value and a time warp before the audit starts (T-3). A test that passes with a testnet value says nothing about the production value.

**R-6 Evidence.** The evidence listed in each record is what is required to decide, not what exists. Identifiers are those that exist in the specification; where nothing exists the record says so and names what must be produced. The verifier checks that every identifier exists; it cannot check what the evidence says.

**R-7 Proposals and ranges.** Proposed values come from [16](16-freeze-decision-report.md) §7, [12](12-router-lifecycle-and-migration.md) §13 and OD-026, OD-027, OD-034 and are unapproved. The hard minimum and hard maximum of each record are the author's proposals for the approvers to confirm or change; they are not measurements. Parts of a record that are the author's own proposal are marked in its "Mine, not a decision" paragraph.

**R-8 Gates.** Every constant is approved at the protocol freeze (RG-016) unless the record says its evidence arrives later. The audited bytecode carries the final values, so the audit freeze (RG-002, the code freeze of [08](08-production-blockers-and-release-gates.md) §2) is the latest moment; the audit completed at RG-005 covers those exact values. Where the evidence arrives after the audit freeze (counsel letters, rehearsals, unit economics) the record says so and the approval rests on a recorded risk acceptance; a negative result then costs a redeploy and a re-audit.

**R-9 Not in this register.** `ROLLBACK_WINDOW` (governance-adjustable) and the backend-tunable values listed at the end of [16](16-freeze-decision-report.md) §7 are not production-blocking constants and have no record here.

## 3. Cross-constraints

Each executable constraint is a predicate over the proposed numbers; `--verify` evaluates it on the production proposals (a failure is an error) and, for `both`, on the testnet values (a failure is a warning). Informative constraints are stated for the approvers and are not executable.

| Constraint | Predicate or statement | Records | Scope | On the proposals | On the testnet values |
|---|---|---|---|---|---|
| X-01 | `QUOTE_SET_GRACE >= MAX_QUOTE_TTL` — The grace is at least the longest life of a quote, so no honest quote dies at a rotation ([11 §4.7](11-dual-cap-model.md), KR-3). | PC-06, PC-08 | both | holds | holds |
| X-02 | `QUOTE_SET_GRACE <= 2 * MAX_QUOTE_TTL` — The grace is at most twice the longest life of a quote, so a retired key does not linger ([11 §4.7](11-dual-cap-model.md), KR-3). | PC-06, PC-08 | both | holds | holds |
| X-03 | `MIN_NOTICE_SECURITY <= MIN_NOTICE_STANDARD` — The security notice is never longer than the standard notice. | PC-01, PC-02 | both | holds | holds |
| X-04 | `RETENTION >= MIN_NOTICE_STANDARD` — Customers have at least as long after a sunset to recover as they had before it to prepare. | PC-01, PC-03 | both | holds | holds |
| X-05 | `MAX_EXPOSED_TOKENS_PER_ROUTER >= MAX_TOKENS_PER_MANDATE` — One mandate with the maximum number of tokens must fit in the exposure index. | PC-11, PC-18 | production | holds | not applicable |
| X-06 | `MAX_EXPOSED_TOKENS_PER_ROUTER <= MAX_BATCH * MAX_TOKENS_PER_MANDATE` — The exposure bound does not exceed the token slots of one batch. | PC-04, PC-11, PC-18 | production | holds | not applicable |
| X-07 | `TIMELOCK_MIN_DELAY >= 24 * 3600` — The timelock delay is at least 24 hours. | PC-14 | production | holds | not applicable |
| X-08 | `MIN_RECIPIENT_CHANGE_DELAY >= 48 * 3600` — The recipient-change delay is at least 48 hours (OD-022). | PC-17 | production | holds | not applicable |
| X-09 | `DAY == 86400 and WEEK == 604800 and THIRTY_DAYS == 2592000` — The three window lengths are exactly these numbers of seconds. | PC-10 | production | holds | not applicable |
| X-10 | `WEEK == 7 * DAY and THIRTY_DAYS == 30 * DAY` — The window lengths are whole multiples of the day. | PC-10 | production | holds | not applicable |
| X-11 | `MAX_ROUTERS_LIVE >= 2` — A migration needs the successor and the predecessor to be live together ([12 §3](12-router-lifecycle-and-migration.md)). | PC-12 | production | holds | not applicable |
| X-12 | `MAX_QUOTE_TTL >= 120` — The ceiling admits the default quote TTL of 120 seconds (OD-027; backend-tunable, not a record). | PC-06 | production | holds | not applicable |
| X-13 | Gas of a plan step: `MAX_BATCH` entries of `MAX_TOKENS_PER_MANDATE` tokens each (containment, exposure updates, Permit2 reads) must fit half of the per-transaction gas cap of the launch chains. Measured on the contracts at the EVM schedule of the compiler's target: about 6.5 million gas at the proposal (10), about 30 million at the earlier 50; not measured on the chains (RP-19). | PC-04, PC-11, PC-18, PC-19 | informative | informative | informative |
| X-14 | Replacement cadence: `MIN_NOTICE_STANDARD` and `MAX_ROUTERS_LIVE` together bound how often a router can be replaced; with two live routers a third cannot be activated until the deprecated one is SUNSET, at least `MIN_NOTICE_STANDARD` after its deprecation. | PC-01, PC-12 | informative | informative | informative |
| X-15 | Recovery latency: after emergency removals empty the current quote signer set, fiat-capped charges fail closed until governance's replacement set passes the timelock; `TIMELOCK_MIN_DELAY` is that latency ([11 §4.7](11-dual-cap-model.md), KR-9). | PC-08, PC-14 | informative | informative | informative |
| X-16 | The blast radius B2 depends on both ceilings: `MAX_BAND_WIDTH_BPS` bounds how far a signer can mis-price and `MAX_QUOTE_TTL` for how long ([11 §6](11-dual-cap-model.md)). | PC-06, PC-07 | informative | informative | informative |
| X-17 | One text, one hash: the `AccountPin` string is identical in [12 §5.3](12-router-lifecycle-and-migration.md) and [17 §5.1](17-account-compatibility-policy.md) and equals what PC-09 fixes; `PIN_EOA` is a hash tag (PC-09) and the pin sentinel (PC-15). | PC-09, PC-15 | informative | informative | informative |
| X-18 | Identifier chain: `LINEAGE_TAG`, `MANDATE_TAG` and `CYCLE_TAG` (PC-09) and the cycle rule (PC-16) together define the settle-once identity; a change to one changes `cycleId` and `paymentId`. | PC-09, PC-16 | informative | informative | informative |
| X-19 | Window grid: `DAY`, `WEEK` and `THIRTY_DAYS` (PC-10) are the grids of the lineage counters and `periodSeconds` is lineage data; the cycle rule (PC-16) divides by `periodSeconds`. | PC-10, PC-16 | informative | informative | informative |
| X-20 | Fee ceiling: bounds every mandate's `maxFeeBps` ([11 §3](11-dual-cap-model.md), clause K.8 of [12 §5.3.2](12-router-lifecycle-and-migration.md)) and `setFee`; no numeric constraint can be stated until Finance decides (OD-016). | PC-05 | informative | informative | informative |
| X-21 | Permit2: one address per chain; the masked code hash is chain-independent and the two immutables (chain id at byte 6945, domain separator at byte 6983) differ per chain. | PC-13 | informative | informative | informative |
| X-22 | The guardian's power set is a subset of the guardian row of the authority matrix ([04 §5](04-context-and-trust-boundaries.md)): it stops, never resumes or widens; everything it cannot do waits for the timelock. | PC-14 | informative | informative | informative |
| X-23 | A recipient change is two-party and, if high-risk, sets new charges to `PAUSED_BY_RISK` (OD-022); the delay applies to every change. | PC-17 | informative | informative | informative |

## 4. Records

### PC-01 — MIN_NOTICE_STANDARD: minimum notice before a standard router sunset

| Field | Value |
|---|---|
| **Symbols** | `MIN_NOTICE_STANDARD` |
| **Kind** | immutable registry minimum |
| **Enforced in** | `RouterRegistry`: `deprecate` requires `sunsetNotBefore >= now + MIN_NOTICE_STANDARD`; `extendSunset` accepts later dates only; invariant `I-MIG-6` ([12 §3](12-router-lifecycle-and-migration.md), [12 §13](12-router-lifecycle-and-migration.md), [16 §8.1](16-freeze-decision-report.md)) |
| **Proposed value** | 180 days |
| **Unit** | seconds (180 days = 15,552,000 s) |
| **Testnet value** | 20 minutes (1,200 s) in a `-testconst` build; the guard logic is identical ([16 §6](16-freeze-decision-report.md)); rule T-3 requires one fork run at 180 days with a time warp before the audit starts |
| **Accountable owner** | Head of Compliance; Principal Architect |
| **Consulted** | General Counsel; Incident Ops Lead; Principal PM; Product Designer |
| **Required approvers** | Principal Architect; Head of Compliance; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-008 — The value is immutable in the audited bytecode. The evidence (counsel letters, RG-008; the canary drill, RG-015) can legally arrive later: FZ-03 and UX-16 let the freeze proceed on a documented risk acceptance by the CISO and the Head of Compliance. If counsel's answer contradicts the value after the audit freeze, the cost is a new `RouterRegistry` and a re-audit. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — Before RG-016 an edit of this record and of [12 §13](12-router-lifecycle-and-migration.md); after RG-016 a Freeze Change Request ([14 §7](14-protocol-freeze-pack.md): Principal Architect and CISO); after the audit freeze a re-audit of `RouterRegistry` and a new deployment of it and of every contract that stores its address as an immutable (the contract specification confirms which). |
| **Status** | **PROPOSED** |

**Rationale.** Sunset cannot happen before `deprecation + MIN_NOTICE_STANDARD`, and governance can lengthen the notice but never shorten it ([12 §3](12-router-lifecycle-and-migration.md)). 180 days gives the customer-communication timeline of [12 §11.1](12-router-lifecycle-and-migration.md) room to run in full: the announcement at the start, reminders at 150, 120 and 90 days before sunset, a second-level reminder at 60 days, urgent reminders from 30 days. ASM-028 assumes that with 180 days at least 90% of active mandates migrate before sunset; that assumption is untested.

**Failure it prevents.** A value that is too short strands customers who cannot or will not act in time: their mandates become `MIGRATION_REQUIRED` and stop charging (RISK-026). A value that is too long delays routine retirement and, together with `MAX_ROUTERS_LIVE` (PC-12), limits how often a router can be replaced.

**Mine, not a decision.** The value 180 days is the `PROPOSAL` of [12 §13](12-router-lifecycle-and-migration.md) and OD-026; it is not a decision. The hard minimum (150 days, the first reminder of the [12 §11.1](12-router-lifecycle-and-migration.md) schedule), the hard maximum (365 days) and the statement that a standard replacement needs one notice period each are my proposals for the approvers to confirm or change.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind: `immutable registry minimum`, as [16 §6](16-freeze-decision-report.md) says 'immutable in `RouterRegistry`'; [14 §4.5](14-protocol-freeze-pack.md) says the testnet constants are compile-time values, so the form (Solidity `constant` or constructor immutable) is for the contract specification.

**Evidence required to decide.**

- RP-26: what notice and sunset periods are workable; counsel on notice duties; comprehension tests of the migration consent
- UX-16: regulatory perimeter and notice duties for router migration; freeze-blocking for PC-01 and PC-02 only
- OD-026: router migration parameters (the proposal)
- ASM-028: 90% of mandates migrate within 180 days (untested assumption)
- RISK-026: stranded mandates, low response, phishing that imitates migration prompts
- RP-09: counsel memo on the regulatory perimeter
- PB-048: router migration readiness: rehearsal, canary drill, communications game day
- To be produced: Counsel's view on notice duties by launch jurisdiction (RP-26; no letter exists), the comprehension test of the migration consent (RP-26), and a canary migration drill that measures the share of mandates migrated within the notice (RG-015). Until then the value rests on ASM-028. FZ-03 allows a documented risk acceptance by the CISO and the Head of Compliance at the freeze if the counsel letter is later.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MIN_NOTICE_STANDARD` | 180 days (15,552,000 s) | 150 days (12,960,000 s) | 365 days (31,536,000 s) | seconds |

- Too low: Customers cannot be reached or cannot act before sunset: mandates stop charging (stranded mandates); the first reminders of the [12 §11.1](12-router-lifecycle-and-migration.md) schedule (150 and 120 days before sunset) would fall before the announcement.
- Too high: A router that must be retired for a reason other than security stays DEPRECATED and chargeable for that long. With `MAX_ROUTERS_LIVE` = 2 (PC-12) no further router can be activated until the deprecated one is SUNSET, so the standard replacement cadence slows to one per notice period. The fast paths for a defective router are the security notice (PC-02) and the guardian's stop.
- Can governance move it later: Governance can lengthen the notice of an individual deprecation (a later `sunsetNotBefore`, `extendSunset`) and can never shorten it. The constant itself cannot be changed after deployment in either direction: a different value is a new `RouterRegistry`.
- Place of the proposal in the range: 180 days is 30 days above the hard minimum and 185 days below the hard maximum: in the lower part of the range, so the headroom is mostly toward longer notice.

**Cross-constraints.** X-03, X-04, X-14 (section 3).

**Tests.**

- Existing: I-MIG-6, MIG-TV-06
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MIN_NOTICE_STANDARD`
- Note: No vector exercises the `deprecate` guard itself (`sunsetNotBefore` one second short of, and exactly at, `now + MIN_NOTICE_STANDARD`); only the planned Foundry test and the time-warp fork run of rule T-3 do.

**Open points.**

- Counsel may require different notice by jurisdiction; the constant is one number for every chain and customer (RP-26).

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Compliance | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-02 — MIN_NOTICE_SECURITY: minimum notice before a security-driven router sunset

| Field | Value |
|---|---|
| **Symbols** | `MIN_NOTICE_SECURITY` |
| **Kind** | immutable registry minimum |
| **Enforced in** | `RouterRegistry`: `deprecate` with reason `SECURITY` requires `sunsetNotBefore >= now + MIN_NOTICE_SECURITY` and a security-notice hash; invariant `I-MIG-6` ([12 §3](12-router-lifecycle-and-migration.md), [12 §13](12-router-lifecycle-and-migration.md)) |
| **Proposed value** | 60 days |
| **Unit** | seconds (60 days = 5,184,000 s) |
| **Testnet value** | 10 minutes (600 s) in a `-testconst` build ([16 §6](16-freeze-decision-report.md)) |
| **Accountable owner** | Head of Security (CISO) |
| **Consulted** | Incident Ops Lead; Head of Compliance; Principal PM; Product Designer |
| **Required approvers** | Principal Architect; Head of Compliance; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-008 — Same as PC-01 (UX-16 names both): immutable in the audited bytecode; the counsel letter and the drill can arrive after the audit freeze, in which case the approval rests on a recorded risk acceptance by the CISO and the Head of Compliance (FZ-03), and a negative result costs a new `RouterRegistry` and a re-audit. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — As PC-01: a Freeze Change Request after the freeze; a re-audit and a new `RouterRegistry` after the audit freeze. |
| **Status** | **PROPOSED** |

**Rationale.** The security path inside the immutable lifecycle: a router that is unsafe but not so urgent that the guardian disables it still has to give customers time to migrate. 60 days is the proposal of OD-026. The compressed timeline of [12 §11.1](12-router-lifecycle-and-migration.md) (announcement, three days later, then 30, 14, 7, 3 and 1 days before sunset) fits inside it. Since 0.5 a `SECURITY` deprecation puts the router in emergency mode ([12 §5.3.1](12-router-lifecycle-and-migration.md)), so customers who migrate must lock down every exposed token and their sibling mandates stop until their own successors exist; the notice has to be long enough to do that for every lineage.

**Failure it prevents.** Too short: customers cannot complete a three-step migration before sunset, unmigrated mandates go to `MIGRATION_REQUIRED`, and a short deadline is the pretext a phishing campaign would imitate (RISK-026). Too long: a router that FastPay itself has declared unsafe keeps charging for the whole notice; the immediate path for a real emergency is the guardian's stop, not this constant.

**Mine, not a decision.** 60 days is the proposal of OD-026, not a decision. My additions: the hard minimum of 45 days (the compressed timeline needs more than 33 days because the message three days after the announcement must come before the one 30 days before sunset; 45 leaves about 12 days of margin) and the hard maximum equal to PC-01 (a security notice longer than the standard one makes no sense).

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Hard minimum 45 days and the upper bound tied to PC-01 are my proposals (see 'Mine, not a decision').

**Evidence required to decide.**

- RP-26: notice and sunset periods; counsel on notice duties; comprehension tests
- UX-16: notice duties for router migration; freeze-blocking for PC-01 and PC-02 only
- OD-026: router migration parameters (the proposal)
- RISK-026: migration failure and phishing that imitates migration prompts
- PB-006: lifecycle rehearsed on testnet, including the partial states
- PB-048: router migration readiness
- To be produced: Security-response analysis (16 §7): the time to fix and the time to migrate for a non-emergency router defect, measured in the testnet rehearsal (PB-006) and the canary drill (RG-015), and counsel's view on notice duties for a security-driven change (RP-26): none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MIN_NOTICE_SECURITY` | 60 days (5,184,000 s) | 45 days (3,888,000 s) | 180 days (15,552,000 s) | seconds |

- Too low: Customers cannot finish the migration (three steps, wallet-dependent, with every exposed token locked down in emergency mode) before sunset.
- Too high: A router declared unsafe stays chargeable for longer; the value can never exceed the standard notice (X-03) because then the 'security' path would be slower than the ordinary one.
- Can governance move it later: Governance can only choose a later `sunsetNotBefore` for an individual deprecation. The constant is immutable.
- Place of the proposal in the range: 60 days is 15 days above the hard minimum (45) and 120 days below the hard maximum (180, the proposal of PC-01).

**Cross-constraints.** X-03 (section 3).

**Tests.**

- Existing: I-MIG-6, MIG-TV-35, MIG-TV-06
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MIN_NOTICE_SECURITY`
- Note: MIG-TV-35 covers the router modes (a `SECURITY` deprecation is emergency mode), not the notice guard; no vector tests the guard at the boundary.

**Open points.**

- Whether a `SECURITY` deprecation should be able to use emergency mode for customers who prefer to keep siblings charging during the notice is [12 §15](12-router-lifecycle-and-migration.md) open point 7; it does not change this value.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Compliance | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-03 — RETENTION: minimum time a router stays SUNSET before it can be RETIRED

| Field | Value |
|---|---|
| **Symbols** | `RETENTION` |
| **Kind** | immutable registry minimum |
| **Enforced in** | `RouterRegistry`: `retire` requires the router to have been in SUNSET for at least `RETENTION` ([12 §3](12-router-lifecycle-and-migration.md), [12 §13](12-router-lifecycle-and-migration.md)) |
| **Proposed value** | 365 days |
| **Unit** | seconds (365 days = 31,536,000 s) |
| **Testnet value** | 1 hour (3,600 s) in a `-testconst` build ([16 §6](16-freeze-decision-report.md)) |
| **Accountable owner** | Head of Compliance |
| **Consulted** | Support Lead; Privacy Lead; Principal Architect; Incident Ops Lead |
| **Required approvers** | Head of Compliance; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-008 — Immutable in the audited bytecode. The evidence is internal analysis plus the DPIA retention rules (PB-030, RG-008) and the canary drill (RG-015), so it can arrive after the audit freeze; the approval then rests on a recorded risk acceptance, and a negative result costs a new `RouterRegistry` and a re-audit. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — As PC-01: a Freeze Change Request after the freeze; a re-audit and a new `RouterRegistry` after the audit freeze. |
| **Status** | **PROPOSED** |

**Rationale.** In SUNSET a router cannot charge and cannot be the target of a successor, but customers can still revoke, pause and create successors elsewhere ([12 §3](12-router-lifecycle-and-migration.md)). The reactivation reminders of [12 §11.1](12-router-lifecycle-and-migration.md) run 30, 60 and 90 days after sunset and a clean-up reminder follows retirement. `RETENTION` keeps the router in that state long enough for those flows and for the support and legal retention needs. 365 days is the proposal of OD-026.

**Failure it prevents.** Too short: the reactivation and clean-up windows close early and records tied to the router can be retired before support and legal needs end. Too long: the RETIRED state, which marks the end of the router's life and triggers the 'remove leftover permissions' reminder, arrives late, and the data and monitoring kept per router version accumulate (retention rules of PB-030).

**Mine, not a decision.** 365 days is the proposal of OD-026, not a decision. My additions: the lower bound equal to PC-01 (customers get at least as long after sunset to recover as they had before it to prepare) and the 730-day hard maximum. The support and legal retention analysis that 16 §7 asks for has not been done.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- The lower bound `RETENTION >= MIN_NOTICE_STANDARD` is the constraint requested for this register; no document derives it.

**Evidence required to decide.**

- OD-026: router migration parameters (the proposal)
- PB-030: DPIA complete; retention, data-subject requests
- RP-12: privacy: DPIA scope, controller and processor roles
- PB-048: router migration readiness, including the communications game day
- RP-26: notice and sunset periods; how customers respond to migration prompts
- To be produced: Support-load and legal-retention analysis (16 §7): how long customers actually reactivate after a sunset (canary drill, RG-015) and what retention period counsel and the DPIA require for router-linked evidence: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `RETENTION` | 365 days (31,536,000 s) | 180 days (15,552,000 s) | 730 days (63,072,000 s) | seconds |

- Too low: The reactivation reminders (30, 60, 90 days after sunset) and the clean-up reminder have no window; support and legal retention may be shorter than they need.
- Too high: Retirement is delayed; more per-router state, evidence and monitoring is carried for longer; no further benefit.
- Can governance move it later: Governance may wait longer before calling `retire`; it cannot retire earlier. The constant cannot change after deployment.
- Place of the proposal in the range: 365 days is 185 days above the hard minimum (180, PC-01) and 365 days below the hard maximum (730): in the lower half.

**Cross-constraints.** X-04 (section 3).

**Tests.**

- Existing: none
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_RETENTION`
- Note: None yet: no vector exercises the `retire` guard (SUNSET for at least `RETENTION`); the planned Foundry test and the time-warp fork run of rule T-3 are the only tests.

**Open points.**

- On chain the retention does little: in SUNSET and RETIRED the customer's exits are identical ([12 §3](12-router-lifecycle-and-migration.md)); the value is mainly a support, legal and communications period. The approvers may prefer a shorter value if counsel confirms there is no legal need.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Head of Compliance | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-04 — MAX_BATCH: maximum entries in one migration-plan step and mandates in one pin batch

| Field | Value |
|---|---|
| **Symbols** | `MAX_BATCH` |
| **Kind** | compile-time constant |
| **Enforced in** | `MigrationQueue.step` accepts at most `MAX_BATCH` entries per step (a plan itself has no such bound: it is one word of storage), and `MandateGateway.updateAccountPins` / `updateAccountPinsBySig` at most `MAX_BATCH` mandates ([12 §5.3.1](12-router-lifecycle-and-migration.md), [12 §13](12-router-lifecycle-and-migration.md), [17 §5.3](17-account-compatibility-policy.md), [16 §8.1](16-freeze-decision-report.md), ADR-022) |
| **Proposed value** | 10 |
| **Unit** | count (successors per plan step, or mandates per pin batch) |
| **Testnet value** | None: the production value is kept on testnet; the constant is not in [16 §6](16-freeze-decision-report.md) ([14 §4.5](14-protocol-freeze-pack.md) rule 1) |
| **Accountable owner** | Solidity Lead |
| **Consulted** | Contract Security Engineer; Wallet Protocol Engineer; Product Designer; Chain Infra Lead |
| **Required approvers** | Solidity Lead; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — The value is in the audited bytecode. Its evidence is a fork gas measurement that FZ-37 puts on the freeze checklist, so it can exist before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records FG-14 and FG-24 after the freeze; after the audit freeze a re-audit and a new `MandateManager`, which is adopted only through new mandates signed by every customer ([12 §5.7](12-router-lifecycle-and-migration.md)). |
| **Status** | **PROPOSED** |

**Rationale.** One migration plan moves every lineage a customer has on a router; it is executed in steps ([12 §5.3.1](12-router-lifecycle-and-migration.md), ADR-022). A step runs the containment check, the exposure-index updates, the Permit2 allowance reads and the event of every entry, so the number of entries per step is what keeps a step inside one transaction. The same constant bounds the number of mandates in one pin update batch.

**Failure it prevents.** An unbounded loop or a step that cannot be submitted (the customer could not migrate or re-pin), and on the low side a plan that takes so many transactions that siblings stay unfunded between steps in an emergency migration.

**Mine, not a decision.** 10 is my proposal after a measurement on the actual contracts (contracts/test/Gas.t.sol, forge 1.8.5, Solidity 0.8.24, cancun schedule, every account and slot cold, entries of three tokens drawn from eight exposed tokens on each router, the old allowances locked down): a worst-case entry costs 545,000 to 605,000 gas and about 4,000 bytes of calldata, so a step of 10 costs about 6.5 million gas in a transaction (execution plus intrinsic and calldata). That is 39% of the 16,777,216 gas per transaction that EIP-7825 sets (an assumption about the launch chains, not verified here) and 78% of the budget the test enforces (half of that cap, to leave room for a chain whose schedule is costlier). The value 50 of OD-026 does not fit: it costs about 30 million gas. The hard range [4, 20] is mine: 4 is the least that keeps MAX_EXPOSED_TOKENS_PER_ROUTER <= MAX_BATCH * MAX_TOKENS_PER_MANDATE (X-06); 20 is the largest step that still fits the cap with a margin. The measurement is on the EVM gas schedule of the compiler's target only: Arbitrum's gas accounting and the real limits of the three chains are not measured (RP-19).

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind `compile-time constant`: [16 §7](16-freeze-decision-report.md) says 'immutable'; an array bound does not depend on the deployment, so a constant is the simplest form.
- Enforced in: ADR-022 replaced the single `activateSuccessors` batch of the manager by the plan steps of `MigrationQueue`; [17 §5.3](17-account-compatibility-policy.md) adds `updateAccountPins` (at most `MAX_BATCH`), which [16 §7](16-freeze-decision-report.md) did not mention.

**Evidence required to decide.**

- RP-19: gas cost per activation and payment by chain, measured on forks at p50 and p90 gas prices
- FZ-37: gas per planner step measured on forks (freeze checklist item)
- OD-026: router migration parameters (the proposal)
- PB-006: lifecycle rehearsal on testnet, including batches
- To be produced: Fork measurement of the same step on Ethereum, Base and Arbitrum One at p50 and p90 gas prices (RP-19; the fork harness tools/fork_run.py is extended to the contracts in the implementation evidence); the per-transaction gas cap of each chain at the time of the audit; product data on lineages per customer per router: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_BATCH` | 10 | 4 | 20 | count |

- Too low: Customers with many lineages on one router need several steps; in an emergency migration the lockdown unfunds every sibling at once while the successors are created over several steps ([12 §5.3.1.2](12-router-lifecycle-and-migration.md)); a plan is resumable, so the cost is time, not loss.
- Too high: The gas of a step approaches the per-transaction cap or the budget of a customer's wallet, and the step cannot be submitted; at 50 the cost, extrapolated from the measured marginal cost of an entry, is about 30 million gas, which does not fit any cap that the launch chains are expected to have.
- Can governance move it later: Governance cannot change it. A different bound is a new `MandateManager`.
- Place of the proposal in the range: 10 is 6 above the hard minimum and 10 below the hard maximum: in the middle of the range, and chosen on a measurement (not on a fork).

**Cross-constraints.** X-06, X-13 (section 3).

**Tests.**

- Existing: MIG-TV-18, MIG-TV-38
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_BATCH`
- Note: MIG-TV-18 and MIG-TV-38 test MAX_BATCH accepted and one more rejected, on the model and on the contracts (contracts/test/Queue.t.sol). The gas is measured by contracts/test/Gas.t.sol, whose guard test fails if the constant and the contracts drift apart.

**Open points.**

- The same constant bounds two different batch calls (plan steps and pin updates); they have different costs (a pin update is far cheaper per mandate). Whether they need separate bounds is open.
- The fork measurement on the three chains (RP-19) has not been run on the contracts; the figure above is the EVM schedule of the compiler's target.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Solidity Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-05 — FEE_CEILING_BPS: immutable ceiling of the fee

| Field | Value |
|---|---|
| **Symbols** | `FEE_CEILING_BPS` |
| **Kind** | immutable constructor argument |
| **Enforced in** | `FeeController` (constructor argument stored as an immutable): `setFee` reverts above it; every mandate's `maxFeeBps` must be at most the ceiling ([11 §3](11-dual-cap-model.md)); guard G6 ([11 §4.8](11-dual-cap-model.md)); containment clause K.8 ([12 §5.3.2](12-router-lifecycle-and-migration.md)); invariant `I-MINOUT` |
| **Proposed value** | **VALUE_PENDING** — No value is proposed. Finance sets it (OD-016); the value is undecided |
| **Unit** | basis points of the gross input; OD-016 also lists a minimum fee and gas pass-through, which a basis-point ceiling must still admit |
| **Testnet value** | Any value that lets the ceiling tests run ([16 §6](16-freeze-decision-report.md)); no number is proposed |
| **Accountable owner** | Finance; Principal PM |
| **Consulted** | General Counsel; Merchant PM; Solidity Lead; Chain Infra Lead |
| **Required approvers** | Finance; Principal PM; General Counsel; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-008 — Immutable in the audited bytecode, so Finance must decide before the audit freeze. The evidence is later: unit economics close at RG-007 (PB-017) and the merchant agreement at RG-008 (PB-031). The approval at RG-016 is therefore a decision under uncertainty and rests on a recorded risk acceptance with a stated margin; if the later evidence shows the ceiling is wrong the remedy is a new `FeeController` and router version. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `FeeController` with the contracts that store its address. |
| **Status** | **PROPOSED** |

**Rationale.** The fee ceiling is the one customer protection that survives every governance and fee-controller change: governance may set the fee only inside the immutable ceiling ([04 §5](04-context-and-trust-boundaries.md)), and each mandate carries its own `maxFeeBps` at or below it. Because it is immutable it has to be right for the whole life of the router version.

**Failure it prevents.** Too low: the product loses money at the smallest ticket (PB-017) and the only remedy is a new `FeeController` and router version. Too high: the protection against later fee increases is empty.

**Mine, not a decision.** No number is proposed here and none appears in this record. The safe range is a rule, not a number: the ceiling must be at most the maximum fee the merchant agreement permits and at least the gas plus operations cost at the lowest supported ticket. The rule was requested for this register; the two quantities it refers to do not exist yet.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- No number appears anywhere in this record, in line with the instruction for this register; the verifier rejects any basis-point figure in it.

**Evidence required to decide.**

- OD-016: fee model: basis points on the settled amount, minimum fee, gas pass-through; Finance to set; the ceiling is immutable
- PB-017: gas-sponsorship and fee economics validated on launch chains
- RP-19: gas cost per activation and payment by chain
- ASM-012: recurring-charge gas is paid by executors and recovered through the fee
- PB-031: terms, merchant agreement, liability positions reviewed
- To be produced: The fee model decision of OD-016 (basis points, minimum fee, gas pass-through); the unit-economics model with measured gas (PB-017, RP-19) giving the cost per charge at the lowest supported ticket and at p90 gas for each launch chain; the lowest supported ticket (defined in no document); the maximum fee the merchant agreement permits (PB-031): none of these exists yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `FEE_CEILING_BPS` | pending | a rule, not a number: at least the gas plus operations cost at the lowest supported ticket | a rule, not a number: at most the maximum fee the merchant agreement permits | basis points |

- Rule: At most the maximum fee the merchant agreement permits; at least the gas plus operations cost at the lowest supported ticket. Both bounds are undefined today, so no number can be stated.
- Too low: A fee that covers the gas and operations cost at the lowest supported ticket cannot be charged: the product is unprofitable there and the only remedy is a new `FeeController` and router version.
- Too high: The ceiling exceeds what merchants agreed to pay, or is so high that it protects nobody from a later fee increase; it cannot be lowered later.
- Can governance move it later: Governance can set the fee anywhere up to the ceiling, in both directions ([04 §5](04-context-and-trust-boundaries.md)). The ceiling cannot change.
- Place of the proposal in the range: Not applicable: no value is proposed.

**Cross-constraints.** X-20 (section 3).

**Tests.**

- Existing: I-MINOUT, MIG-TV-20
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_FEE_CEILING_BPS`
- Note: I-MINOUT covers fee <= min(`maxFee`, ceiling); MIG-TV-20 covers the fee-cap clause of containment. The ceiling tests run with any testnet value; at the production value they must be repeated before the audit starts (rule T-3).

**Open points.**

- If OD-016 chooses a minimum fee or a gas pass-through, a ceiling expressed only in basis points of the gross input must still admit the minimum fee at the smallest supported ticket; the lowest supported ticket is not defined in any document.
- The merchant agreement's maximum fee is not drafted (PB-031).

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Finance | no | **NOT SIGNED** | — | — | — |
| Principal PM | no | **NOT SIGNED** | — | — | — |
| General Counsel | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-06 — MAX_QUOTE_TTL: immutable ceiling of the life of a price quote

| Field | Value |
|---|---|
| **Symbols** | `MAX_QUOTE_TTL` |
| **Kind** | immutable registry ceiling |
| **Enforced in** | `TokenPolicyRegistry`: `setMaxQuoteTtl` reverts above `MAX_QUOTE_TTL`; the quote verifier checks `validUntil - issuedAt <= min(mandate.maxQuoteAge, registry.maxQuoteTtl)` (Q12) ([11 §4.2](11-dual-cap-model.md), [11 §4.3](11-dual-cap-model.md), [16 §8.1](16-freeze-decision-report.md)) |
| **Proposed value** | 300 seconds |
| **Unit** | seconds |
| **Testnet value** | 30 seconds in a `-testconst` build ([16 §6](16-freeze-decision-report.md)): only the speed of the quote tests changes and the TTL check is identical. The testnet `QUOTE_SET_GRACE` (60 s, PC-08) is at least this value, so X-01 holds on the testnet values |
| **Accountable owner** | Risk Lead |
| **Consulted** | Chain Infra Lead; Payments PM; Head of Security (CISO); Principal Architect |
| **Required approvers** | Risk Lead; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — Immutable in the audited bytecode. The evidence (a depeg replay and latency data) is internal and can exist before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `TokenPolicyRegistry`, and with it a new signer-set history. |
| **Status** | **PROPOSED** |

**Rationale.** A quote attests a price at `issuedAt`; the TTL bounds how long it can be consumed (Q12). The ceiling is immutable so that governance cannot make quotes arbitrarily stale. 300 seconds is two and a half times the default quote TTL of 120 seconds (OD-027, backend-tunable), which leaves room for submission latency and retries, and it is the unit of the rotation grace (PC-08).

**Failure it prevents.** Stale prices accepted through a depeg (the replay of RP-14) and a longer exposure window for a compromised or mistaken signer (B2, [11 §4.7](11-dual-cap-model.md) KR-5). On the low side, quotes that expire before inclusion, so fiat-capped charges fail closed.

**Mine, not a decision.** 300 seconds is the proposal of [16 §7](16-freeze-decision-report.md), not a decision. The hard minimum of 120 seconds (the default TTL must fit), the hard maximum of 600 seconds and the remark about headroom are mine.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind `immutable registry ceiling` is an addition to the four kinds named for this register: it is a ceiling, not a minimum.
- Enforced in: [16 §7](16-freeze-decision-report.md) says 'verifier / registry ceiling'; the library holds no state, so the ceiling lives in `TokenPolicyRegistry`.

**Evidence required to decide.**

- RP-14: price and oracle sources and depeg-detection signals; historical depeg replay
- OD-027: quote and price-bound design: TTL 120 s, bands, signer topology
- OD-034: quote-signer rotation parameters, including `MAX_QUOTE_TTL`
- ASM-015: a quote fixes the amount for a bounded window
- RP-22: observed reorg depth and finality delays per chain (inclusion latency)
- RISK-025: quote-signer compromise or mis-set bounds distort fiat accounting
- RISK-033: a compromised quote signer signs inside the bounds until removed
- To be produced: Depeg replay (RP-14) showing how far a reference stablecoin's price moves inside the proposed TTL on the launch chains, and measured quote-to-inclusion latency on each launch chain: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_QUOTE_TTL` | 300 seconds | 120 seconds | 600 seconds | seconds |

- Too low: Quotes expire between signing and inclusion; fiat-capped charges fail closed and are retried (an availability loss, B3).
- Too high: A price attestation stays usable longer, so a depeg or a signer compromise is exploitable for longer (bounded by the bands, B2); and the rotation grace (PC-08), which must be at least this long, grows with it.
- Can governance move it later: Timelocked governance can set the registry's `maxQuoteTtl` anywhere up to the ceiling and lower it at once; the ceiling cannot change.
- Place of the proposal in the range: 300 seconds is 180 above the hard minimum and half of the hard maximum.

**Cross-constraints.** X-01, X-02, X-12, X-16 (section 3).

**Tests.**

- Existing: CAP-TV-05, I-QUOTE
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_QUOTE_TTL`
- Note: CAP-TV-05 tests a quote one second over the TTL in force; no vector tests that `setMaxQuoteTtl` rejects a value above the ceiling, so only the planned Foundry test covers the ceiling.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Risk Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-07 — MAX_BAND_WIDTH_BPS: immutable ceiling of the width of a price band

| Field | Value |
|---|---|
| **Symbols** | `MAX_BAND_WIDTH_BPS` |
| **Kind** | immutable registry ceiling |
| **Enforced in** | `TokenPolicyRegistry`: `setBounds` reverts if the width of `[minPriceE18, maxPriceE18]` exceeds the ceiling ([11 §4.3](11-dual-cap-model.md), [16 §8.1](16-freeze-decision-report.md)); mandates snapshot the bounds (`I-BOUNDS-SNAPSHOT`) |
| **Proposed value** | 500 bps |
| **Unit** | basis points (width = ceil(10,000 × (max − min) / min), proposed definition) |
| **Testnet value** | None: not listed in [16 §6](16-freeze-decision-report.md); the production value is kept on testnet |
| **Accountable owner** | Risk Lead |
| **Consulted** | Principal Architect; Payments PM; Head of Security (CISO); Chain Infra Lead |
| **Required approvers** | Risk Lead; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — Immutable in the audited bytecode. The evidence is an internal replay and can exist before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `TokenPolicyRegistry`. |
| **Status** | **PROPOSED** |

**Rationale.** The bands are the on-chain limit of what a quote signer can distort: with a malicious signer inside the bounds the outflow is at most `F / m`, where `m` is the lowest in-band price ([11 §6](11-dual-cap-model.md), B2). The ceiling is immutable so that no governance action can widen a band past a stated blast radius. At the proposal the excess of that bound over the fiat cap is at most about the width of the band, so about 5%. 500 bps is above the roughly ±2% band of OD-027 and ASM-026, so a registry band for a stablecoin has margin and can be widened a little in a stress without a new registry.

**Failure it prevents.** Too high: a malicious or mistaken signer can mis-price by more than the design intends, and B2 grows with the width. Too low: no registry band can be wide enough for the normal price noise of a candidate stablecoin; honest quotes fail with `PriceOutOfBounds` and fiat-capped charges fail closed.

**Mine, not a decision.** 500 bps is the proposal of [16 §7](16-freeze-decision-report.md), not a decision. The definition of 'width' is mine: no document defines it. I propose `ceil(10,000 × (maxPriceE18 − minPriceE18) / minPriceE18)`, measured on the minimum because B2 is stated on the lowest price. Under that definition the ±2% example band (0.98 to 1.02) is 409 bps wide, which is the hard minimum; the hard maximum of 1,000 bps is also mine.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind `immutable registry ceiling` (see PC-06).
- I defined the width and derived the hard minimum from the ±2% example of OD-027 and ASM-026 under that definition.

**Evidence required to decide.**

- RP-14: price and oracle sources and depeg-detection signals; historical depeg replay
- OD-027: static bands for stablecoins, for example ±2%
- ASM-026: bands of roughly ±2% are wide enough to avoid false rejections and narrow enough to bound the blast radius
- RISK-025: quote-signer compromise or mis-set bounds distort fiat accounting
- RISK-033: a compromised quote signer signs inside the bounds until removed
- To be produced: A depeg replay and band-width study per candidate stablecoin on the launch chains (RP-14): the widest band needed to avoid false rejections in normal markets and in a stress: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_BAND_WIDTH_BPS` | 500 bps | 409 bps | 1,000 bps | basis points |

- Too low: The registry cannot hold a band wide enough for a candidate token; honest quotes fail `PriceOutOfBounds`, or the token cannot be listed with fiat caps.
- Too high: The blast radius B2 grows with the band: the excess of the outflow bound over the fiat cap is about the width; at 1,000 bps a 'stablecoin band' no longer bounds anything useful.
- Can governance move it later: Timelocked governance can set bands up to the ceiling and narrow them; an existing mandate keeps the intersection of its snapshot and the current band (`I-BOUNDS-SNAPSHOT`), so a wider band never affects it. The ceiling cannot change.
- Place of the proposal in the range: 500 bps is 91 above the hard minimum and half of the hard maximum.

**Cross-constraints.** X-16 (section 3).

**Tests.**

- Existing: CAP-TV-04, CAP-TV-08, I-BOUNDS-SNAPSHOT, I-QUOTE
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_BAND_WIDTH_BPS`
- Note: No vector tests the ceiling itself (a `setBounds` wider than `MAX_BAND_WIDTH_BPS`); only the planned Foundry test does.

**Open points.**

- The definition of the width (which denominator) is in no document; [11 §12](11-dual-cap-model.md) point 1 leaves the band widths to the Risk Lead and the Principal Architect. If the denominator is the midpoint the hard minimum becomes 400 bps.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Risk Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-08 — QUOTE_SET_GRACE: grace for quotes issued before a planned signer-set rotation

| Field | Value |
|---|---|
| **Symbols** | `QUOTE_SET_GRACE` |
| **Kind** | compile-time constant |
| **Enforced in** | `QuoteVerifier` library, check Q13: `block.timestamp <= retiredAt(v) + QUOTE_SET_GRACE` for a quote of a retired signer set `v` ([11 §4.2](11-dual-cap-model.md), [11 §4.7](11-dual-cap-model.md)) |
| **Proposed value** | 300 seconds (at least `MAX_QUOTE_TTL`) |
| **Unit** | seconds |
| **Testnet value** | 60 seconds ([16 §6](16-freeze-decision-report.md)): at least the testnet `MAX_QUOTE_TTL` of 30 seconds (PC-06), so X-01 holds on the testnet values; it also equals twice that value, the upper edge of X-02 |
| **Accountable owner** | Head of Security (CISO) |
| **Consulted** | Risk Lead; Principal Architect; SRE Lead; Contract Security Engineer |
| **Required approvers** | Risk Lead; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-002 — The value is in the audited bytecode. The evidence is a rotation drill that needs the built contracts and is part of the testnet alpha, which completes at RG-002; the drill can only move the value inside `[MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL]`, so the approval at RG-016 fixes the formula and the drill confirms the number before the audit freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records FG-11 and FG-23 after the freeze; after the audit freeze a re-audit of `QuoteVerifier` and a redeploy of every contract that links it (`PaymentRouter` and `TokenPolicyRegistry`), that is a new router version. |
| **Status** | **PROPOSED** |

**Rationale.** New semantics in 0.5: the grace bounds only the honoring of quotes issued before a planned rotation (`issuedAt < retiredAt(v)` and `now <= retiredAt(v) + QUOTE_SET_GRACE`). A key believed compromised gets no grace: it is tombstoned at once and Q1 fails for it in every set version ([11 §4.7](11-dual-cap-model.md), KR-4). At a planned rotation the old set is retired at `retiredAt`; quotes already issued under it must stay consumable for as long as a quote can live (`MAX_QUOTE_TTL`), otherwise honest quotes die at every rotation. Hence the range from `MAX_QUOTE_TTL` to twice that.

**Failure it prevents.** Honest quotes dying at a rotation (grace too short) and, in the other direction, a retired key's quotes and the retired key itself lingering longer than needed (grace too long). The grace never applies to a removed key.

**Mine, not a decision.** 300 seconds equals [16 §7](16-freeze-decision-report.md) and OD-034 (`QUOTE_SET_GRACE = MAX_QUOTE_TTL = 300 s`); it is not a decision. The range `[MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL]` is stated in [11 §4.7](11-dual-cap-model.md). Placing the proposal at the lower edge is mine: it is the shortest grace that kills no honest quote, and no measured need for more exists.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind `compile-time constant` (see the open point on libraries).
- The approvers of this record are the CISO, the Risk Lead and the Principal Architect: [16 §7](16-freeze-decision-report.md) names the Head of Security as owner, and the grace is a property of the quote path.

**Evidence required to decide.**

- OD-034: quote-signer rotation parameters: grace, TTL, rotation period, removal latency, set size
- OD-027: quote and price-bound design
- RISK-033: a compromised quote signer signs inside the bounds until removed
- RISK-025: quote-signer compromise or mis-set bounds
- UD-08: quote signer set threshold versus any single registered signer
- PB-041: dual cap model and signed quote schema proven
- To be produced: A rotation drill (16 §7): a planned rotation and an emergency removal on a fork and on testnet with the production grace and a time warp (rule T-3), with the quote service's switch-over time measured: none yet. It is scenario 11 of the testnet alpha ([14 §4.4](14-protocol-freeze-pack.md)).

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `QUOTE_SET_GRACE` | 300 seconds | 300 seconds | 600 seconds | seconds |

- Too low: Below `MAX_QUOTE_TTL` the grace can cut off honest quotes that are still inside their own `validUntil`: fiat-capped charges fail at every rotation.
- Too high: Above `2 * MAX_QUOTE_TTL`: no further effect on chain (from `MAX_QUOTE_TTL` upward the grace is not the binding limit for a quote that satisfies Q11 and Q12; see the open point); in operation the old HSM keys are kept until `QUOTE_SET_GRACE` plus the log-retention period has passed (KR-7), so a longer grace lengthens custody of a retired key.
- Can governance move it later: Governance cannot change it. A removed key gets no grace at all, whatever this value is.
- Place of the proposal in the range: At the lower edge of the range: 300 seconds equals `MAX_QUOTE_TTL` and is 300 below the upper edge.

**Cross-constraints.** X-01, X-02, X-15 (section 3).

**Tests.**

- Existing: CAP-TV-14, CAP-TV-15, CAP-TV-25, CAP-TV-26, CAP-TV-16, CAP-TV-23, CAP-TV-24, CAP-TV-30
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_QUOTE_SET_GRACE`
- Note: CAP-TV-14, 15, 25 and 26 test the grace boundary (the second after the grace, a quote issued at `retiredAt`); CAP-TV-16, 23, 24 and 30 test that a removed key has no grace. No vector tests a grace outside the range, because the value is a constant: only the planned Foundry test does.

**Open points.**

- A Solidity library has no constructor and no immutables, so 'immutable in the verifier library' ([16 §6](16-freeze-decision-report.md)) can only mean a compile-time `constant` of the library (or an immutable of the calling contract passed in). This record says compile-time constant.
- For `QUOTE_SET_GRACE >= MAX_QUOTE_TTL` the grace conjunct of Q13 is never the binding one for a quote that also passes Q11 and Q12: consumption is already bounded by `issuedAt + MAX_QUOTE_TTL`, which is earlier than `retiredAt + MAX_QUOTE_TTL`. The upper edge `2 * MAX_QUOTE_TTL` therefore has no on-chain effect; its effect is operational (KR-7). If the approvers want the upper bound to mean something on chain they need a different rule.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Risk Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-09 — EIP-712 names, versions, type strings and hash tags

| Field | Value |
|---|---|
| **Symbols** | `QUOTE_DOMAIN_NAME`, `QUOTE_DOMAIN_VERSION`, `MANDATES_DOMAIN_NAME`, `MANDATES_DOMAIN_VERSION`, `PRICE_QUOTE_TYPEHASH`, `PAY_ONCE_INTENT_TYPESTRING`, `ACTIVATION_TERMS_TYPEHASH`, `SUCCESSOR_AUTHORIZATION_TYPEHASH`, `ACCOUNT_PIN_TYPEHASH`, `ACCOUNT_PIN_UPDATE_TYPEHASH`, `ACCOUNT_PINS_UPDATE_TYPEHASH`, `LINEAGE_TAG`, `MANDATE_TAG`, `CYCLE_TAG`, `ROUTE_DIRECT_TAG`, `SNAPSHOT_TAG` |
| **Proposed identifiers** | all except `ACCOUNT_PIN_TYPEHASH`, `LINEAGE_TAG`, `MANDATE_TAG`, `CYCLE_TAG`, `ROUTE_DIRECT_TAG`, `SNAPSHOT_TAG`: no document names the others (proposed by the author of this record) |
| **Kind** | compile-time constant |
| **Enforced in** | Contract constants: `MandateManager` (domain `FastPay Mandates`; `ActivationTerms`, `SuccessorAuthorization`, `AccountPinUpdate`, `AccountPinsUpdate`, `AccountPin`; identifier and snapshot tags), `PaymentRouter` and `QuoteVerifier` (domain `FastPay Quote`, `PriceQuote`, route tag), the Pay Once witness in `PaymentRouter` (`PayOnceIntent`) |
| **Proposed value** | As in documents 10, 11, 12 and 17: the exact strings are in the table of this record |
| **Unit** | exact ASCII strings and bytes32 tags (keccak256 of the tag string); no numeric range |
| **Testnet value** | None: the same strings on every chain and build; a `-testconst` build must not differ in them (rule T-1) |
| **Accountable owner** | Principal Architect |
| **Consulted** | Solidity Lead; Wallet Protocol Engineer; QA Lead; Product Designer; Backend Lead |
| **Required approvers** | Principal Architect; Solidity Lead; Wallet Protocol Engineer; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — [14 §0](14-protocol-freeze-pack.md) lists every EIP-712 domain and type string among the frozen items and FG-07, FG-10, FG-11, FG-14, FG-21 and FG-22 are recorded at the freeze; the strings are in the audited bytecode. The evidence (two implementations reproducing the vectors, FZ-42) is part of the freeze checklist. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records the fingerprints of the sections named in the table ([14 §7](14-protocol-freeze-pack.md)); every signature and identifier changes; a v2 under a new version string rather than an edit of v1; a re-audit and a redeploy of the contracts that hold the string. |
| **Status** | **PROPOSED** |

**Rationale.** Every signature a customer, a quote signer or a wallet produces is bound to these strings: a change of a name or version alters the domain separator, a change of a type string alters the type hash, a change of a tag alters the lineage, mandate, cycle, route and pin identifiers. They are public API, wallets display the names, and they are in the bytecode, so they cannot change without invalidating every signature and identifier.

**Failure it prevents.** Silent divergence between contract, backend and wallet (a signature that verifies in one and not in another) and cross-protocol replay: the domains and versions keep `PriceQuote` apart from the mandate messages, and a new version string and type hash keep a v2 apart from v1 ([11 §4.5](11-dual-cap-model.md)).

**Mine, not a decision.** The strings are those of documents 10, 11, 12 and 17 as they read today (rows marked QUOTED), the `AccountPin` struct as in [17 §5.1](17-account-compatibility-policy.md), and the tags as in `tools/eip712_vectors.py`. The symbol names, other than the tag names and `ACCOUNT_PIN_TYPEHASH`, are my proposals. Some strings are not spelled anywhere (`ActivationTerms`, the typed data of the revoke, pause, reduce and resume messages, the full encoding behind the snapshot tag and the Pay Once witness string; [14 §8](14-protocol-freeze-pack.md) point 5, FZ-22): this record cannot be approved until they are.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Symbol names other than the tag names and `ACCOUNT_PIN_TYPEHASH` are my proposals.
- `PIN_EOA` appears in the table because [16 §7](16-freeze-decision-report.md) lists its tag here; its symbol and its test belong to PC-15.
- `ACCOUNT_PIN_TYPEHASH` is listed here and not in PC-15: [17 §5.1](17-account-compatibility-policy.md) says a change of the type string is a protocol change under PC-09 and PC-15.

**Evidence required to decide.**

- FZ-13: digest of the quote schema reproduced by two independent implementations
- FZ-22: all EIP-712 domains and type strings listed once
- FZ-42: digest and type hashes equal in the contract prototype, the backend and the vector tool
- PB-051: signed quote schema frozen and reproduced
- UX-04: Permit2 witness type-string format
- UX-09: texts of EIP-712 and related standards say what the claims say
- PR-10: what `permitWitnessTransferFrom` hashes and the witness type-string format
- RP-01: pinned reading of the normative texts
- EVL-08: typed-data prompts for activation and successor authorization in the wallet lab
- To be produced: Two independent implementations reproduce the vectors: done for the contract prototype side (generated Solidity), the backend side (TypeScript) and two more (Python, Foundry cheat codes), see the implementation evidence report; the type strings are written (FZ-22, proposal); still open: approval of the fingerprint (C-11), the fingerprints recorded at the freeze ([14 §2](14-protocol-freeze-pack.md)), a wallet-lab check of the displayed names (EVL-08; none yet).

**Safe range.**

- Too low: Not applicable: the values are strings, not an ordered quantity.
- Too high: Not applicable. Any deviation (a character, a space after a comma, a different field order, another version string) changes a hash and breaks verification everywhere the string is used.
- Can governance move it later: Governance cannot change them. A change is a new typed-data version (a new version string and type hash, as `PriceQuote` v2 in [11 §4.5](11-dual-cap-model.md)), new contracts and new signatures.
- Place of the proposal in the range: The only acceptable values are the exact strings of the table.

**Cross-constraints.** X-17, X-18 (section 3).

**Tests.**

- Existing: ACP-TV-34, CAP-TV-09, CAP-TV-21, EIP712Golden.t.sol, EIP712Permit2.t.sol, I-PO-WITNESS, I-REPLAY, MIG-TV-17, MIG-TV-19, Permit2ThreeChains.t.sol, eip712/test-eip712.ts
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_EIP712_NAMES_TAGS_AND_TYPES`
- Note: The golden vectors of `eip712/golden-vectors.json` (written by `tools/eip712_types.py`) are reproduced by the generated Solidity library (`EIP712Golden.t.sol`), by the TypeScript module (`eip712/test-eip712.ts`) and by Foundry's own EIP-712 cheat codes; the quote and pin vectors of `tools/eip712_vectors.py` are reproduced by the same encoder. `EIP712Permit2.t.sol` has the Permit2 rebuilt from the pinned commit accept the witness string.

**Open points.**

- The strings marked DERIVED are the implementer's proposal, assembled from the field lists of [10 §2.1](10-pay-once-protocol.md), [11 §3](11-dual-cap-model.md), [12 §5.3.2](12-router-lifecycle-and-migration.md) and [17 §5.3, §5.4](17-account-compatibility-policy.md); none carries an approval. Approval is condition C-11 of `tools/freeze_readiness.py` (the Wallet Protocol Engineer and the Solidity Lead approve the fingerprint printed in `eip712/TYPES.md`).
- `reduceBySig`, `pauseBySig`, `resumeBySig` and `revokeBySig`: the field sets (customer, mandate id, deadline, nonce; for reduce also the old and the new terms hash) are the minimum that identifies the act. Whether the customer should also sign a pin version in `ResumeMandate` is open.
- `fastpay.migration.snapshot.v1`: the implemented encoding (25 words, `eip712/types.json` snapshotEncoding) does not hash `customer`, `anchorStartsAt` and `boundsVersion`, which [12 §5.3.2](12-router-lifecycle-and-migration.md) lists in the snapshot terms, and it orders the cap table (perPaymentMax, totalMax, dayMax, ...) differently from the typed data (perPaymentMax, dayMax, ..., totalMax). Reported as findings F-06 and F-07; changing the encoding is a decision for the Principal Architect because the hash is signed and its tag is a frozen item (FG-14).
- The Pay Once witness string is now written and shown against the real Permit2 built from the pinned commit; whether the batch form (merchant and fee as two permitted entries) or a single transfer plus a separate fee transfer is used is still the open question 2 of [10 §8](10-pay-once-protocol.md). Both forms are covered.
- Type widths: [11 §3](11-dual-cap-model.md) gives `maxChargesPerPeriod` as `uint16`, `minIntervalSeconds` as `uint32`, the fiat caps as `uint64` and `maxQuoteAgeSeconds` as `uint32`; the typed data uses exactly these widths, and the reference model enforces them (`TermsShape`, finding F-04).

**Sub-items**

| Sub-item | Symbol | Exact value | Specified in | Fingerprint (FG) | keccak256 of the exact value | String status | Why it is fixed |
|---|---|---|---|---|---|---|---|
| Quote domain name | QUOTE_DOMAIN_NAME | `FastPay Quote` | [11 §4.1](11-dual-cap-model.md) | FG-11 | `0xd003b34a2da733a446ac06729e0c953f5b080dbd13bdfd3b4ea83a61bc284d30` | QUOTED | Wallets display it; it is hashed into the quote domain separator, so a change invalidates every quote signature |
| Quote domain version | QUOTE_DOMAIN_VERSION | `1` | [11 §4.1](11-dual-cap-model.md) | FG-11 | `0xc89efdaa54c0f20c7adf612882df0950f5a951637e0307cdcb4c672f298b8bc6` | QUOTED | Keeps `PriceQuote` v1 apart from a v2, which gets version `2` and a new type hash ([11 §4.5](11-dual-cap-model.md)) |
| Mandates domain name | MANDATES_DOMAIN_NAME | `FastPay Mandates` | [12 §5.3](12-router-lifecycle-and-migration.md) | FG-14 | `0xed345e4b13fb27d8593d4308bc2e940615cba3572a35c442b76ca1beb38d491f` | QUOTED | Wallets display it; it is hashed into the domain separator of every customer-signed mandate message |
| Mandates domain version | MANDATES_DOMAIN_VERSION | `1` | [12 §5.3](12-router-lifecycle-and-migration.md) | FG-14 | `0xc89efdaa54c0f20c7adf612882df0950f5a951637e0307cdcb4c672f298b8bc6` | QUOTED | Keeps this message set apart from a later one; a change invalidates every stored authorization |
| `PriceQuote` type string | PRICE_QUOTE_TYPEHASH | `PriceQuote(bytes32 paymentId,address payer,address token,uint256 amountIn,uint16 currency,uint256 priceE18,uint64 issuedAt,uint64 validAfter,uint64 validUntil,uint256 nonce,uint32 signerSetVersion,uint64 registryVersion,uint32 boundsVersion,bytes32 routeHash,bytes32 priceSourceSetHash)` | [11 §4.1](11-dual-cap-model.md); vector in [11 §4.6](11-dual-cap-model.md) | FG-11 | `0x384641be814e75f4dce15c63df78fd013ed6055d9b4aeb1c855dc0ed3ec275c4` | QUOTED | The type hash every quote signature commits to; field names, types and order are part of it |
| `PayOnceIntent` witness struct (signed under Permit2's domain, not a FastPay domain) | PAY_ONCE_INTENT_TYPEHASH | `PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)` | [10 §2.1](10-pay-once-protocol.md) (field list); [eip712/types.json](eip712/types.json) | FG-07 | `0x18d7c79fe9b89aeef53539395bf2e1ef5b39739f2e54b35d6c1ea86c43688ccb` | DERIVED | The witness the customer signs binds recipient and amounts; the struct is hashed into the Permit2 witness |
| Pay Once `witnessTypeString` (what the router passes to `permitWitnessTransferFrom`) | PAY_ONCE_WITNESS_TYPESTRING | `PayOnceIntent witness)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)` | [eip712/types.json](eip712/types.json); format of Permit2 `PermitHash.sol` at the pinned commit | FG-07 | `0xd5d455884ced4e3dafbbabc027e37acac38039bf22053b6cd4f3be2d427b5c7c` | DERIVED | Permit2 hashes this string without checking it; any deviation fails the signature (shown against the real Permit2 for 7 variants), so the router hard-codes it |
| Permit2 single witness type string (stub and witness string) | PERMIT2_WITNESS_TRANSFER_FROM_TYPEHASH | `PermitWitnessTransferFrom(TokenPermissions permitted,address spender,uint256 nonce,uint256 deadline,PayOnceIntent witness)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)` | [eip712/types.json](eip712/types.json); `PermitHash.sol` `_PERMIT_WITNESS_TRANSFER_FROM_TYPEHASH_STUB` | FG-07 | `0xe9e5a628726ac516218746dbe0f05e9577c33a78ab77c80d80869a9dc2fdb8eb` | DERIVED | The type hash Permit2 computes for a single witness transfer: the signature is over this string |
| Permit2 batch witness type string (stub and witness string) | PERMIT2_BATCH_WITNESS_TRANSFER_FROM_TYPEHASH | `PermitBatchWitnessTransferFrom(TokenPermissions[] permitted,address spender,uint256 nonce,uint256 deadline,PayOnceIntent witness)PayOnceIntent(bytes32 paymentId,bytes32 merchantId,address recipient,address feeRecipient,address token,uint256 grossAmountIn,uint256 merchantAmount,uint256 feeAmount,address payer,uint64 validUntil,bytes32 termsHash,bytes32 quoteHash)TokenPermissions(address token,uint256 amount)` | [eip712/types.json](eip712/types.json); `PermitHash.sol` `_PERMIT_BATCH_WITNESS_TRANSFER_FROM_TYPEHASH_STUB` | FG-07 | `0xd62ccbc65c7e41d263a5467d0eb498512db256c3c6faef1b089f014c5355e36b` | DERIVED | The type hash Permit2 computes for the batch witness transfer (merchant and fee in one call, document 10 §2.2) |
| `ActivationTerms` with its nested `MandateTerms`, `TokenTerms`, `FiatTerms` and `AccountPin` (encodeType) | ACTIVATION_TERMS_TYPEHASH | `ActivationTerms(address customer,address router,bytes32 routerCodeHash,uint32 routerVersion,uint256 creationNonce,MandateTerms terms,AccountPin accountPin,uint64 deadline)AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)FiatTerms(uint16 currency,uint64 perPaymentMaxMinor,uint64 dayMaxMinor,uint64 weekMaxMinor,uint64 thirtyDayMaxMinor,uint64 periodMaxMinor,uint64 totalMaxMinor,uint32 maxQuoteAge,uint32 boundsVersion)MandateTerms(bytes32 merchantId,bytes32 recipientPolicy,bytes32 subscriptionRef,uint64 periodSeconds,uint64 anchorStartsAt,uint64 expiresAt,TokenTerms[] tokens,FiatTerms fiat,uint16 maxChargesPerPeriod,uint32 minIntervalSeconds,uint16 maxFeeBps,bytes32 extensionsHash)TokenTerms(address token,uint256 perPaymentMax,uint256 dayMax,uint256 weekMax,uint256 thirtyDayMax,uint256 periodMax,uint256 totalMax)` | [eip712/types.json](eip712/types.json); fields from [11 §3](11-dual-cap-model.md), [12 §5.3.2](12-router-lifecycle-and-migration.md), [17 §5.3](17-account-compatibility-policy.md) | none yet (FG-21 covers only the pin) | `0xe74ad9d665ad7aa0f27b6f69ba3e14227434a9a282d81f0529ac2e3cf0776d61` | DERIVED | The mandate terms the customer signs at activation; the wallet shows every field, including the nested pin |
| `MandateTerms` with its nested types (its hashStruct is `termsHash` of [12 §5.3](12-router-lifecycle-and-migration.md)) | MANDATE_TERMS_TYPEHASH | `MandateTerms(bytes32 merchantId,bytes32 recipientPolicy,bytes32 subscriptionRef,uint64 periodSeconds,uint64 anchorStartsAt,uint64 expiresAt,TokenTerms[] tokens,FiatTerms fiat,uint16 maxChargesPerPeriod,uint32 minIntervalSeconds,uint16 maxFeeBps,bytes32 extensionsHash)FiatTerms(uint16 currency,uint64 perPaymentMaxMinor,uint64 dayMaxMinor,uint64 weekMaxMinor,uint64 thirtyDayMaxMinor,uint64 periodMaxMinor,uint64 totalMaxMinor,uint32 maxQuoteAge,uint32 boundsVersion)TokenTerms(address token,uint256 perPaymentMax,uint256 dayMax,uint256 weekMax,uint256 thirtyDayMax,uint256 periodMax,uint256 totalMax)` | [eip712/types.json](eip712/types.json); fields from [11 §3](11-dual-cap-model.md), [12 §5.3.2](12-router-lifecycle-and-migration.md), [17 §5.3](17-account-compatibility-policy.md) | none yet | `0x9fecb76cdb169444849bb4564cf3ab6584b3d78cb367c2b0ca7f9b69d9612136` | DERIVED | `auth.newTermsHash = termsHash(N)` (predicate A3) and `ReduceMandate.newTermsHash` are hashStruct of this type |
| `RevokeMandate` | REVOKE_MANDATE_TYPEHASH | `RevokeMandate(address customer,bytes32 mandateId,uint64 deadline,uint256 nonce)` | [eip712/types.json](eip712/types.json); the message is named in [17 §5.4](17-account-compatibility-policy.md) / [06 §3](06-initial-architecture.md) | none yet | `0xa77b96a416e42fe084b07266fbb92af55717f72f5ec95374c63ebfee3caa0ac5` | DERIVED | Gasless revoke of the active mandate of a lineage; exits are never gated by the signature mode ([17 §5.4](17-account-compatibility-policy.md)) |
| `PauseMandate` | PAUSE_MANDATE_TYPEHASH | `PauseMandate(address customer,bytes32 mandateId,uint64 deadline,uint256 nonce)` | [eip712/types.json](eip712/types.json); the message is named in [17 §5.4](17-account-compatibility-policy.md) / [06 §3](06-initial-architecture.md) | none yet | `0x9ab43f67f7cdd186af60ca48a057bdd17446d08757779e9506e0e83affa40b04` | DERIVED | Gasless pause of the customer's own pause bit |
| `ResumeMandate` | RESUME_MANDATE_TYPEHASH | `ResumeMandate(address customer,bytes32 mandateId,uint64 deadline,uint256 nonce)` | [eip712/types.json](eip712/types.json); the message is named in [17 §5.4](17-account-compatibility-policy.md) / [06 §3](06-initial-architecture.md) | none yet | `0x0b6de585bd5705f05d9e260d5951e24a1518ae1a1b83da19dcad489dd476e1a7` | DERIVED | Clears the customer's own pause bit; grants nothing new |
| `ReduceMandate` | REDUCE_MANDATE_TYPEHASH | `ReduceMandate(address customer,bytes32 mandateId,bytes32 oldTermsHash,bytes32 newTermsHash,uint64 deadline,uint256 nonce)` | [eip712/types.json](eip712/types.json); the message is named in [17 §5.4](17-account-compatibility-policy.md) / [06 §3](06-initial-architecture.md) | none yet | `0x6f1f4b7fa4ac9c2085fe75c091a15cd6d81bc22f126434a129a65412a823fee4` | DERIVED | Narrowing-only reduction: the old terms hash must equal the stored one and the new terms must be contained in it |
| `SuccessorAuthorization` with its nested `AccountPin` (EIP-712 encodeType: the referenced struct is appended) | SUCCESSOR_AUTHORIZATION_TYPEHASH | `SuccessorAuthorization(address customer,bytes32 lineageId,bytes32 predecessorId,uint8 kind,bytes32 newTermsHash,address newRouter,bytes32 newRouterCodeHash,uint32 newRouterVersion,bytes32 termsSnapshotHash,uint32 widenedMask,AccountPin accountPin,uint64 deadline,uint256 nonce)AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)` | [12 §5.3](12-router-lifecycle-and-migration.md) | FG-14 | `0x0a86c2ac458cd20311931d0d8a92dcf30ab8088189b6510f327cbeb13a72d741` | QUOTED | The customer's router-specific authorization of a successor; the new router, its code hash and the pin are part of it |
| `AccountPin` (new in 0.5) | ACCOUNT_PIN_TYPEHASH | `AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)` | [17 §5.1](17-account-compatibility-policy.md), [12 §5.3](12-router-lifecycle-and-migration.md) | FG-21 | `0xa080d57e052584c73c3f7c5069eb0bccf7ce7d0326916d81ecda5f8867f57ec4` | QUOTED | The pin struct is signed in three messages and hashed into the mandate; seven fields in this order |
| `AccountPinUpdate` with its nested `AccountPin` (encodeType) | ACCOUNT_PIN_UPDATE_TYPEHASH | `AccountPinUpdate(address customer,bytes32 mandateId,AccountPin newPin,uint64 deadline,uint256 nonce)AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)` | [17 §5.3](17-account-compatibility-policy.md) | FG-21 | `0x0e22d83b1dc4e6f4b1c6f4e2246ae1bd4fb1f915961f60c72692177ed09e4ab8` | QUOTED | The customer's signed pin update for one mandate; the version check uses `newPin.pinVersion`, so the message carries no old version |
| `AccountPinsUpdate` (batch) with its nested `AccountPin` (encodeType) | ACCOUNT_PINS_UPDATE_TYPEHASH | `AccountPinsUpdate(address customer,bytes32[] mandateIds,AccountPin newPin,uint64 deadline,uint256 nonce)AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)` | [17 §5.3](17-account-compatibility-policy.md) | FG-21 | `0xb642c366bb9b921cd388a122c8bfb8199df7f1971bdac9275958ce1f9a8f8908` | QUOTED | The customer's signed pin update for several mandates at once (at most `MAX_BATCH`); every named mandate must be at the same stored version |
| Lineage tag | LINEAGE_TAG | `fastpay.lineage.v1` | [11 §3.1](11-dual-cap-model.md) | FG-10; FG-13 | `0xbf83254ba89afa77ea2c40c1c20ce6b11934c50e327179d94462f39f2aa718ca` | QUOTED | Domain-separates `lineageId`; a change alters every lineage id |
| Mandate tag | MANDATE_TAG | `fastpay.mandate.v1` | [11 §3.1](11-dual-cap-model.md) | FG-10; FG-13 | `0x0945ea3d0f624223c05a4649c8e90b730e0955e6c384b0c6495dc8d46ca84a47` | QUOTED | Domain-separates `mandateId`; a change alters every mandate id |
| Cycle tag | CYCLE_TAG | `fastpay.cycle.v1` | [11 §3.1](11-dual-cap-model.md) | FG-10; FG-13 | `0x1b3b500f4535f791b4c727ae471cd2d9a515d37b0f981805b68a4420165b214c` | QUOTED | Domain-separates `cycleId`; a change alters every cycle and payment id, so the settle-once record would not match |
| Direct-route tag | ROUTE_DIRECT_TAG | `fastpay.route.direct.v1` | [11 §4.1](11-dual-cap-model.md) | FG-11 | `0x48a89266632b4264377511a397d72a77f3b9d62cd378b304495771cc80eac486` | QUOTED | Domain-separates the direct-settlement `routeHash` inside every quote |
| Migration snapshot tag | SNAPSHOT_TAG | `fastpay.migration.snapshot.v1` | [12 §5.3.2](12-router-lifecycle-and-migration.md) names the constant; the full string is in `tools/eip712_vectors.py` and, abbreviated, in [16 §7](16-freeze-decision-report.md) | FG-14 | `0x4aad20bbdc76b59b6c54f2654e80c83256a985795153592e09edf6ed88fa0092` | QUOTED (tool only) | Domain-separates `termsSnapshotHash`, which the customer signs in a successor authorization |
| Account-pin sentinel tag (owned by PC-15) | PIN_EOA | `fastpay.pin.eoa.v1` | [17 §5.1](17-account-compatibility-policy.md); vector in [17 §9](17-account-compatibility-policy.md) | FG-21; FG-22 | `0x8b07c3b3a0bc8c34a9a1a11064f80e35587006d2afc562b5114a4d9071547ba5` | QUOTED | The sentinel that stands for 'no code' in a plain-EOA pin; a change makes every stored plain-EOA pin invalid ([17 §5.1](17-account-compatibility-policy.md)) |

String status: QUOTED = the text appears in the cited document (checked by the verifier as a warning); DERIVED = built by the author from a field list; NOT_SPECIFIED = no document spells it. A hash is shown only for a complete string; for `SuccessorAuthorization` it is the hash of the encodeType, the primary string followed by `AccountPin`, as EIP-712 requires for a struct that nests another.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Solidity Lead | no | **NOT SIGNED** | — | — | — |
| Wallet Protocol Engineer | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-10 — Window lengths: DAY, WEEK, THIRTY_DAYS

| Field | Value |
|---|---|
| **Symbols** | `DAY`, `WEEK`, `THIRTY_DAYS` |
| **Kind** | compile-time constant |
| **Enforced in** | `MandateManager` window-index computation `index = floor((t - anchor) / windowLength)` for `DAY`, `WEEK`, `THIRTY_DAYS`; the billing-period window is the lineage's `periodSeconds`, which is data, not a constant ([11 §2.1](11-dual-cap-model.md) rows 2 to 5, [11 §3](11-dual-cap-model.md)) |
| **Proposed value** | DAY 86,400 s, WEEK 604,800 s, THIRTY_DAYS 2,592,000 s |
| **Unit** | seconds |
| **Testnet value** | None: the production values are kept on testnet ([14 §4.5](14-protocol-freeze-pack.md) rule 1) |
| **Accountable owner** | Payments PM |
| **Consulted** | Product Designer; Head of Compliance; General Counsel; Solidity Lead; Principal Architect |
| **Required approvers** | Payments PM; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-008 — The values are in the audited bytecode and are definitions. The evidence is a copy review and counsel's view on the 'monthly' wording (RG-008, PB-029): if counsel requires calendar months the design of the windows changes, which after the audit freeze is a re-audit; the approval then rests on a recorded risk acceptance. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `MandateManager`, adopted only through new mandates ([12 §5.7](12-router-lifecycle-and-migration.md)); the counters of every lineage would be re-gridded. |
| **Status** | **PROPOSED** |

**Rationale.** Every cap window is a fixed-length window anchored at the lineage's first `startsAt`; counters and successors share the same grid, so these lengths define what 'per day', 'per week' and 'per 30 days' mean for every existing and future mandate. `THIRTY_DAYS` is exactly 2,592,000 seconds, not a calendar month, and the consent copy says 'per 30 days' ([11 §3](11-dual-cap-model.md)).

**Failure it prevents.** A different length silently changes the customer-visible promise (a cap that resets earlier or later than the copy says) and re-grids the counters of every lineage.

**Mine, not a decision.** The three values are definitions, not tunable numbers: there is no judgment in them. What the approvers decide is whether the set day, week, 30 days (plus the per-lineage billing period) is the right set; calendar months are not offered ([11 §12](11-dual-cap-model.md) point 2).

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Symbols are the window names of [16 §7](16-freeze-decision-report.md) and [11 §2.1](11-dual-cap-model.md); the code names are not fixed in any document.

**Evidence required to decide.**

- RP-10: recurring-payment consent, notice, cancellation and refund-rights requirements
- PB-029: recurring-payment consent copy legally reviewed
- RISK-010: recurring-payment consent or cancellation rules are not met
- To be produced: Product copy review of 'per 30 days' with a comprehension test (at least 80% can state both numbers, [11 §8](11-dual-cap-model.md)) and counsel's view on 'monthly' wording by jurisdiction (RP-10): none yet. [11 §12](11-dual-cap-model.md) point 2 (30-day windows against calendar months) must be closed by the Payments PM and counsel.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `DAY` | 86,400 seconds | 86,400 seconds | 86,400 seconds | seconds |
| `WEEK` | 604,800 seconds | 604,800 seconds | 604,800 seconds | seconds |
| `THIRTY_DAYS` | 2,592,000 seconds | 2,592,000 seconds | 2,592,000 seconds | seconds |

- Too low: Not applicable as a range: any value other than the stated one is wrong. A shorter window makes caps reset earlier than the copy says.
- Too high: Not applicable as a range. A longer window makes caps reset later than the copy says and lets a customer be charged less often than expected.
- Can governance move it later: Governance cannot change them; they are constants of `MandateManager`.
- Place of the proposal in the range: The proposal is the only acceptable value: minimum and maximum are equal.

**Cross-constraints.** X-09, X-10, X-19 (section 3).

**Tests.**

- Existing: CAP-TV-07, CAP-TV-13, MIG-TV-10, I-CAP-TOKEN, I-MIG-3
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_WINDOW_LENGTHS`
- Note: CAP-TV-07 tests two charges straddling a window boundary; CAP-TV-13 and MIG-TV-10 test that a successor keeps the window grid and the usage.

**Open points.**

- [11 §12](11-dual-cap-model.md) point 2: 30-day windows against calendar months for subscription copy.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Payments PM | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-11 — MAX_TOKENS_PER_MANDATE: maximum number of tokens in one mandate

| Field | Value |
|---|---|
| **Symbols** | `MAX_TOKENS_PER_MANDATE` |
| **Kind** | compile-time constant |
| **Enforced in** | `MandateManager`: the token array of a mandate (`activate`, `activateBySig`, `activateSuccessor*`) is rejected above the bound; every loop over the mandate's tokens (containment K.3 and K.4, the snapshot hash, predicate G1 and the old-allowance predicates of [12 §5.3](12-router-lifecycle-and-migration.md)) is bounded by it ([11 §3](11-dual-cap-model.md), [16 §8.1](16-freeze-decision-report.md)) |
| **Proposed value** | 3 |
| **Unit** | count (tokens per mandate) |
| **Testnet value** | None: the production value is kept on testnet; not in [16 §6](16-freeze-decision-report.md) |
| **Accountable owner** | Product Designer; Solidity Lead |
| **Consulted** | Contract Security Engineer; Wallet Protocol Engineer; Payments PM; Principal Architect |
| **Required approvers** | Solidity Lead; Product Designer; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — In the audited bytecode. The gas evidence is FZ-37 on the freeze checklist; the usability data can come from the design work before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `MandateManager`, adopted only through new mandates ([12 §5.7](12-router-lifecycle-and-migration.md)). |
| **Status** | **PROPOSED** |

**Rationale.** A mandate lists the tokens it may charge, each with its own caps. The bound limits the gas of every loop over those tokens (successor activation reads a Permit2 allowance per token, containment and the snapshot hash loop over them) and the audit surface, and it limits how many tokens one signature authorizes. A mandate needs at least two tokens for a fallback (token fallback is scenario 2 of [14 §4.4](14-protocol-freeze-pack.md)).

**Failure it prevents.** Unbounded loops and a consent screen that lists more tokens than a customer can read; on the low side, a mandate that cannot offer a fallback token.

**Mine, not a decision.** 3 is the proposal of [16 §7](16-freeze-decision-report.md), not a decision; no document derives it ('gas and audit bound'). The hard minimum 2 (a fallback needs a second token) and the hard maximum 6 are mine.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Owner: [16 §7](16-freeze-decision-report.md) names the Product Designer and the Solidity Lead together; both are owners here.

**Evidence required to decide.**

- ASM-009: at most 10 tokens per chain are enabled at launch
- RP-19: gas measured on forks
- UD-01: production-blocking constants (the freeze decision)
- To be produced: Usability data on how many launch tokens a customer wants to allow per mandate and how often the fallback is used (testnet alpha: none yet) and fork gas of the loops at the bound (RP-19: none yet).

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_TOKENS_PER_MANDATE` | 3 | 2 | 6 | count |

- Too low: A mandate cannot offer a fallback token (2 is the minimum for a fallback) or several launch stablecoins; customers must sign again or lose the fallback.
- Too high: Every loop over the tokens grows linearly (two Permit2 reads per token at a successor activation, the containment loop, the snapshot hash, `consume` calldata, the exposure index); `MAX_BATCH * MAX_TOKENS_PER_MANDATE` bounds the token slots of a batch (X-06); and a single signature authorizes more tokens.
- Can governance move it later: Governance cannot change it. A larger bound is a new `MandateManager`, adopted through new mandates ([12 §5.7](12-router-lifecycle-and-migration.md)).
- Place of the proposal in the range: 3 is one above the hard minimum and half of the hard maximum.

**Cross-constraints.** X-05, X-06, X-13 (section 3).

**Tests.**

- Existing: MIG-TV-09
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_TOKENS_PER_MANDATE`
- Note: MIG-TV-09 covers an extra token in a successor (`TermsNotContained`), not the bound itself. No vector tests an activation with the bound and the bound plus one; only the planned Foundry test does.

**Open points.**

- The error name for a mandate with too many tokens is not specified.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Solidity Lead | no | **NOT SIGNED** | — | — | — |
| Product Designer | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-12 — MAX_ROUTERS_LIVE: routers that may be ACTIVE or DEPRECATED on one chain

| Field | Value |
|---|---|
| **Symbols** | `MAX_ROUTERS_LIVE` |
| **Kind** | compile-time constant |
| **Enforced in** | `RouterRegistry`: after an activation at most `MAX_ROUTERS_LIVE` routers per chain are ACTIVE or DEPRECATED ([12 §3](12-router-lifecycle-and-migration.md), control M8 of [12 §7](12-router-lifecycle-and-migration.md), [12 §13](12-router-lifecycle-and-migration.md)) |
| **Proposed value** | 2 |
| **Unit** | count (routers per chain) |
| **Testnet value** | None: the production value is kept on testnet; not in [16 §6](16-freeze-decision-report.md) |
| **Accountable owner** | Principal Architect |
| **Consulted** | Principal PM; Incident Ops Lead; Product Designer |
| **Required approvers** | Principal Architect; Principal PM; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-006 — In the audited bytecode. The evidence is a rehearsal that needs built contracts (PB-006 blocks RG-006) and a canary drill (RG-015), so it arrives after the audit freeze; the approval at RG-016 rests on the design argument and a recorded risk acceptance, and a failed rehearsal costs a new `RouterRegistry` and a re-audit. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `RouterRegistry`. |
| **Status** | **PROPOSED** |

**Rationale.** Each live router is a spender customers may have funded and an address a phishing campaign can imitate (RISK-026), and each adds a migration campaign. Two live routers are the minimum for any migration: a deprecation needs an ACTIVE successor ([12 §3](12-router-lifecycle-and-migration.md)), so the successor and its predecessor are live together.

**Failure it prevents.** Too high: more simultaneous campaigns and a larger phishing surface. Too low (1): no router can ever be replaced, because the successor cannot be ACTIVE while the predecessor still is.

**Mine, not a decision.** 2 is the proposal of OD-026 and control M8, not a decision. The hard maximum 3 is mine: a third live router would allow a rollback target next to a migration in flight, but nothing in the documents asks for it.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind `compile-time constant`: [16 §7](16-freeze-decision-report.md) says 'registry guard' without saying whether it is immutable; the intro of [16 §7](16-freeze-decision-report.md) says every PC is compile-time, immutable or practically unchangeable. If the Principal Architect wants governance to adjust it, it stops being a production-blocking constant and needs an immutable ceiling instead.

**Evidence required to decide.**

- OD-026: router migration parameters (the proposal)
- PB-006: lifecycle rehearsed on testnet: deprecate, migrate, sunset, retire, rollback
- PB-048: router migration readiness: canary drill and communications game day
- RISK-026: stranded mandates and phishing that imitates migration prompts
- TB-17: trust boundary for migration communications
- To be produced: The testnet rehearsal of a full deprecate, migrate, sunset, retire and rollback cycle (PB-006) and the canary drill (RG-015), showing that two live routers suffice, including a rollback during a notice period: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_ROUTERS_LIVE` | 2 | 2 | 3 | count |

- Too low: At 1 no router can be replaced; the lifecycle is impossible.
- Too high: More routers are live at once: more phishing surface, more campaigns, and more partly migrated customers to track; the proof of no overlapping authority (`I-MIG-8`) does not depend on the count, but the operations do.
- Can governance move it later: Governance cannot change it.
- Place of the proposal in the range: At the hard minimum: 2 is the tightest workable value.

**Cross-constraints.** X-11, X-14 (section 3).

**Tests.**

- Existing: none
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_ROUTERS_LIVE`
- Note: None yet: no vector tests that an activation which would make a third router live reverts; M8 is a control of [12 §7](12-router-lifecycle-and-migration.md), not a vector. Only the planned Foundry test and the rehearsal do.

**Open points.**

- With `MAX_ROUTERS_LIVE` = 2 and a standard notice of `MIN_NOTICE_STANDARD`, a third router cannot be activated until the deprecated one is SUNSET (X-14).

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Principal PM | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-13 — Permit2 address per chain

| Field | Value |
|---|---|
| **Symbols** | `PERMIT2` |
| **Proposed identifiers** | all of them: no document names these identifiers (proposed by the author of this record) |
| **Kind** | immutable constructor argument |
| **Enforced in** | Constructor argument stored as an immutable in `PaymentRouter` and `MandateManager` (and in an `ActivationHelper` if UD-04 chooses one); the deployment manifest per chain and the `permit2.verified` gate ([14 §4.1](14-protocol-freeze-pack.md), [16 §6](16-freeze-decision-report.md)) |
| **Proposed value** | Canonical address 0x000000000022D473030F116dDEE9F6B43aC78BA3 on a chain only if its runtime code matches the pinned build; verified per chain |
| **Unit** | address (20 bytes), per chain id |
| **Testnet value** | A testnet address or a deployment from the pinned commit ([16 §6](16-freeze-decision-report.md)); a testnet address is never evidence for a mainnet claim ([14 §4.1](14-protocol-freeze-pack.md)) |
| **Accountable owner** | Solidity Lead |
| **Consulted** | Chain Infra Lead; Contract Security Engineer; Wallet Protocol Engineer; Principal Architect |
| **Required approvers** | Solidity Lead; Chain Infra Lead; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-004; evidence closes at RG-004 — The rule is decided at RG-016. The reads of EV-P14 exist for three chains, but the rebuild comparison does not (UX-11: not freeze-blocking, closes at RG-004), so each chain needs its own approval before it is enabled, and the audit runs against the canonical address on forks. This deviates from 'before the audit freeze': the address is a deployment argument and is masked in the bytecode comparison; a risk acceptance covers the interval. A chain whose evidence is missing is excluded from the signature. |
| **Change control** | FCR, REDEPLOY — Before deployment an edit of this record and the manifest; after deployment a new deployment of every contract that holds the address (a new router version); if the audited source is unchanged only the deployment script and manifest are re-audited; a wrong address found after funds are at risk is a security incident (guardian stop). |
| **Status** | **PROPOSED** |

**Rationale.** Permit2 is the one external contract every customer allowance and every pull goes through ([04 §5](04-context-and-trust-boundaries.md): immutable code the customer already trusts). The router and the manager call a fixed address that is baked in at deployment. A wrong address is catastrophic and cannot be fixed ([16 §7](16-freeze-decision-report.md)).

**Failure it prevents.** Using a non-canonical or modified Permit2 on a chain (ASM-005). The address is documented as the same on many chains with a zkSync exception ([08 §4](08-production-blockers-and-release-gates.md)), so it has to be verified chain by chain, not assumed.

**Mine, not a decision.** The canonical address is the documented one. The rule 'use the canonical address only if the runtime code equals the build from the pinned commit' is [14 §4.1](14-protocol-freeze-pack.md)'s rule for testnets, extended by me to mainnets. The chain list, the code length (9,152 bytes), the masked code hash and the two offsets are those recorded in EV-P14 and [16 §5.2](16-freeze-decision-report.md); this record only repeats them, and the verifier compares them with [evidence/permit2/pin.json](evidence/permit2/pin.json) but cannot repeat the on-chain reads.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Gate: latest approval gate RG-004 for each chain instead of the audit freeze, for the reason in the gate row.
- The symbol `PERMIT2` is my proposal; no document names the immutable.

**Evidence required to decide.**

- EV-P14: deployed Permit2 code on Ethereum, Base and Arbitrum One recorded on 2026-10-16: length, hash, the two immutables and the masked hash; E3 for what is deployed
- EV-P01: the rebuild comparison of the pinned build with the deployed code; not done
- EV-P15: Permit2 behavior note at the pinned commit; E2 sign-off pending
- UX-11: Permit2 bytecode on each launch chain equals the pinned build: E3 for what is deployed, source-to-bytecode match not established; closes at RG-004
- ASM-005: Permit2 is at the canonical address with unmodified bytecode on every launch chain
- PB-004: Permit2 present and unmodified on every enabled chain; continuous monitoring live
- PR-15: absence of admin, upgrade and pause functions; deployment method and audit reports
- RP-03: is Permit2 on each launch chain the expected bytecode
- FZ-36: chain facts for the first mainnets: Permit2 bytecode hash from two RPCs
- CLM-022: documents list addresses, not bytecode
- EV-P12: pinned Permit2 source review record
- To be produced: The rebuild comparison (EV-P01): compile the pinned commit with the recorded compiler settings and either reproduce the canonical address from the CREATE2 formula or compare the runtime code with the two immutables masked. It is not done: it needs solc 0.8.17 and the deployer address, and the authoring environment has no such toolchain ([16 §5.5](16-freeze-decision-report.md)). The E2 sign-off of the review by two named reviewers (EV-P15) is also pending. For every chain added later, the same reads as EV-P14.

**Safe range.**

- Rule: Exactly one acceptable address per chain: the canonical address, and only if its runtime code equals the pinned build after masking the two per-chain immutables.
- Too low: Not applicable: an address has no order.
- Too high: Not applicable. Any other address, or the canonical address with different code, is a wrong value: calls go to the wrong contract or fail, and customers' allowances are to a spender the contracts do not use.
- Can governance move it later: Governance cannot change it: it is immutable in each deployed contract.
- Place of the proposal in the range: The only acceptable value is the canonical address per verified chain.

**Cross-constraints.** X-21 (section 3).

**Tests.**

- Existing: I-EXTCALL
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_PERMIT2_ADDRESS`
- Note: `I-EXTCALL` fixes the call targets of Router v1 (Permit2 among them). A fork test per chain must read the code at the manifest address and compare its length and masked hash; that test is the planned Foundry test and part of EV-P01. None exists.

**Open points.**

- The source-to-bytecode match is not established; the address is a CREATE2 address, so a successful rebuild proves source, compiler and settings in one step ([16 §5.5](16-freeze-decision-report.md)).
- [14 §4.1](14-protocol-freeze-pack.md) names the testnets and not the mainnets; the three chains here are the ones read in EV-P14.
- The two immutables differ per chain, so the deployed bytecode compared with the audited build must mask them, and a per-chain code hash is not a chain-independent constant.

**Per-chain rows (recorded in EV-P14; the verifier compares them with the pin record)**

| Chain | Chain id | Address | Runtime code length (bytes) | Masked code hash (chain-independent) | Per-chain immutables | Evidence state |
|---|---|---|---|---|---|---|
| Ethereum | 1 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | 9,152 | `463331fa7a0d5f07488e42c37b461bb56a822145c161a821fbafe7d4e916b546` | chain id at byte 6945 and domain separator at byte 6983, 32 bytes each; the values differ per chain | Recorded in EV-P14 ([16 §5.2](16-freeze-decision-report.md), [evidence/permit2/pin.json](evidence/permit2/pin.json)): read at one block from at least two providers; E3 for what is deployed; the source-to-bytecode match is NOT established |
| Base | 8453 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | 9,152 | `463331fa7a0d5f07488e42c37b461bb56a822145c161a821fbafe7d4e916b546` | chain id at byte 6945 and domain separator at byte 6983, 32 bytes each; the values differ per chain | Recorded in EV-P14 ([16 §5.2](16-freeze-decision-report.md), [evidence/permit2/pin.json](evidence/permit2/pin.json)): read at one block from at least two providers; E3 for what is deployed; the source-to-bytecode match is NOT established |
| Arbitrum One | 42161 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | 9,152 | `463331fa7a0d5f07488e42c37b461bb56a822145c161a821fbafe7d4e916b546` | chain id at byte 6945 and domain separator at byte 6983, 32 bytes each; the values differ per chain | Recorded in EV-P14 ([16 §5.2](16-freeze-decision-report.md), [evidence/permit2/pin.json](evidence/permit2/pin.json)): read at one block from at least two providers; E3 for what is deployed; the source-to-bytecode match is NOT established |

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Solidity Lead | no | **NOT SIGNED** | — | — | — |
| Chain Infra Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-14 — Timelock minimum delay and the guardian's powers

| Field | Value |
|---|---|
| **Symbols** | `TIMELOCK_MIN_DELAY`, `GUARDIAN_POWERS` |
| **Proposed identifiers** | all of them: no document names these identifiers (proposed by the author of this record) |
| **Kind** | deployment configuration that is practically hard to change (this is the kind of the delay; the guardian's power set is not configuration but the function list of `EmergencyGuardian`, a compile-time property of the code) |
| **Enforced in** | The governance timelock (minimum delay for propose, activate and deprecate and for every widening action: [04 §5](04-context-and-trust-boundaries.md), TM-13); the `EmergencyGuardian` function list ([16 §8.1](16-freeze-decision-report.md), [04 §5](04-context-and-trust-boundaries.md)) |
| **Proposed value** | 72 h; stop-only |
| **Unit** | seconds (72 hours = 259,200 s) for the delay; a fixed set of stop functions for the guardian |
| **Testnet value** | 2 minutes (120 s) for the timelock delay ([16 §6](16-freeze-decision-report.md)); guardian and governance thresholds and signers are test keys; the guardian's power set is identical |
| **Accountable owner** | Head of Security (CISO) |
| **Consulted** | Principal Architect; SRE Lead; Contract Security Engineer; Incident Ops Lead |
| **Required approvers** | Principal Architect; Board or its delegate; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-006 — UD-05 makes the delays freeze-blocking, and the deployment scripts that set them are in the audit scope ([16 §8.1](16-freeze-decision-report.md)). The ceremony rehearsal (PB-007) completes at RG-006, after the audit freeze, so the approval rests on a recorded risk acceptance; a change of the delay is a governance operation, a change of the guardian's powers is new code. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — The delay: a Freeze Change Request, then a governance operation through the timelock. The guardian's power set: a Freeze Change Request, a re-audit and a redeploy of `EmergencyGuardian`, plus an ADR and Security sign-off ([04 §5](04-context-and-trust-boundaries.md), review rule). |
| **Status** | **PROPOSED** |

**Rationale.** Governance's widening actions (new routers, tokens and signers, fee changes inside the ceiling, clearing an emergency) wait for the timelock so that monitoring, FastPay's own alerts and customers can react; stop-only actions are immediate and cannot widen anything (TM-13, [04 §5](04-context-and-trust-boundaries.md)). 72 hours includes a weekend. The guardian's power set is what keeps 'immediate' safe. The delay is also the recovery latency after emergency removals empty the current quote signer set: fiat-capped charges fail closed until the replacement set has passed the timelock ([11 §4.7](11-dual-cap-model.md), KR-9).

**Failure it prevents.** Too short: a malicious or mistaken widening takes effect before anyone can see it. Too long: legitimate fixes wait. A guardian with a power beyond stopping would turn the emergency path into a widening path.

**Mine, not a decision.** 72 hours and stop-only are proposals ([12 §13](12-router-lifecycle-and-migration.md), OD-023), not decisions. The range of 24 to 168 hours is mine. 'Practically hard to change' is my judgement: the timelock implementation is not named in any document, and a delay that can be changed only through the timelock itself is hard to change, while one that a multisig can edit directly is not.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind: the delay is 'deployment configuration that is practically hard to change'; the guardian's powers are compile-time. One kind field covers both with a note.
- Symbols `TIMELOCK_MIN_DELAY` and `GUARDIAN_POWERS` are my proposals; no document names them.
- The Board (or its delegate) is a required approver because OD-023 names the Board as co-owner.

**Evidence required to decide.**

- OD-023: guardian and governance structure: thresholds, signers, timelocks
- UD-05: OD-023 decision; the delays are production-blocking constants; freeze-blocking
- OD-026: router migration parameters, including the 72-hour timelock
- PB-007: governance multisig and timelock, guardian multisig, key classes constituted
- TM-13: privileged and widening changes are evented, detected and delayed; stop-only actions are immediate
- TM-14: a customer can always exit
- To be produced: OD-023 decided (signers, thresholds, delay: none yet); a ceremony rehearsal of propose, wait, activate and of a guardian stop on testnet (PB-007: none yet); a recovery drill after an emptied quote signer set that measures the cost of the delay ([11 §4.7](11-dual-cap-model.md) KR-9: none yet).

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `TIMELOCK_MIN_DELAY` | 72 hours (259,200 s) | 24 hours (86,400 s) | 168 hours (604,800 s) | seconds |

- Too low: Customers and monitoring cannot see a malicious or mistaken widening before it takes effect.
- Too high: Legitimate changes wait: recovery from an emptied quote signer set, clearing a wrongly set emergency, router activation. The stop-only guardian cannot compensate for slow widening.
- Can governance move it later: Changing the delay is itself a governance action. If it goes through the timelock, lowering it takes a full current delay and can be seen coming; whether the code enforces a floor is open. The guardian's power set cannot be changed without new code (04 §5 review rule: any 'no' turned into 'yes' needs an ADR and Security sign-off).
- Place of the proposal in the range: 72 hours is 48 above the hard minimum and 96 below the hard maximum.

**Cross-constraints.** X-07, X-15, X-22 (section 3).

**Tests.**

- Existing: I-ADMIN, I-EXIT, CAP-TV-32, CAP-TV-31
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_TIMELOCK_MIN_DELAY_AND_GUARDIAN`
- Note: I-ADMIN is the role-matrix test; CAP-TV-32 and CAP-TV-31 test that the guardian cannot add a signer or set or clear a tombstone. No vector tests that a widening action reverts before the delay has elapsed.

**Open points.**

- The timelock implementation is not chosen; whether it enforces a minimum delay in code determines whether 24 hours is a floor or only a convention.
- Whether the guardian may promote a pre-registered standby signer set to shorten the recovery is an open decision of [11 §4.7](11-dual-cap-model.md) (KR-9); the default is that it may not.

**Guardian powers (sub-items)**

| Power | Function | Allowed | Source |
|---|---|---|---|
| Pause new recurring charges | `pauseCharge` | Allowed (stop) | [16 §8.1](16-freeze-decision-report.md), [04 §5](04-context-and-trust-boundaries.md) |
| Pause Pay Once | `pausePayOnce` | Allowed (stop) | [16 §8.1](16-freeze-decision-report.md), [04 §5](04-context-and-trust-boundaries.md) |
| Block a token | `blockToken` | Allowed (stop) | [16 §8.1](16-freeze-decision-report.md) |
| Remove an executor | `removeExecutor` | Allowed (stop) | [16 §8.1](16-freeze-decision-report.md) |
| Remove (tombstone) a quote signer or stop a signer set | `removeQuoteSigner`, `stopSignerSet` | Allowed (stop; no grace) | [16 §8.1](16-freeze-decision-report.md), [11 §4.7](11-dual-cap-model.md) |
| Emergency-disable a router | `emergencyDisableRouter` | Allowed (stop) | [16 §8.1](16-freeze-decision-report.md), [12 §3](12-router-lifecycle-and-migration.md) |
| Resume, unpause or undo any of the above | none | Not allowed | [04 §5](04-context-and-trust-boundaries.md), [12 §3](12-router-lifecycle-and-migration.md) |
| Enable or add anything: token, executor, adapter, quote signer, signer set, router | none | Not allowed (CAP-TV-32 for signers and sets) | [04 §5](04-context-and-trust-boundaries.md), [11 §4.7](11-dual-cap-model.md) |
| Change the fee, choose a recipient, create or widen authority, move customer tokens, clear a tombstone | none | Not allowed | [04 §5](04-context-and-trust-boundaries.md), [11 §4.7](11-dual-cap-model.md) |

The function names are those of the `EmergencyGuardian` row of [16 §8.1](16-freeze-decision-report.md) and the signer-set functions of [11 §4.7](11-dual-cap-model.md); [04 §5](04-context-and-trust-boundaries.md) is the source of truth for the matrix.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Board or its delegate | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-15 — Account-pin constants and rules: PIN_EOA, KECCAK_EMPTY, the PIN_OK handling and PIN_WELLFORMED

| Field | Value |
|---|---|
| **Symbols** | `PIN_EOA`, `KECCAK_EMPTY` |
| **Kind** | compile-time constant |
| **Enforced in** | `MandateManager`: `PIN_WELLFORMED` and `PIN_OK` in `activate*`, `activateSuccessor*`, `updateAccountPin*` and every `consume` ([17 §5.2](17-account-compatibility-policy.md), [17 §5.3](17-account-compatibility-policy.md)) |
| **Proposed value** | As [17 §5.1](17-account-compatibility-policy.md) and [17 §5.2](17-account-compatibility-policy.md): `PIN_EOA`, `KECCAK_EMPTY`, the `PIN_OK` handling of both, and the `PIN_WELLFORMED` rules of the seven-field `AccountPin` |
| **Unit** | bytes32 constants and predicate rules; no numeric range |
| **Testnet value** | None: the same constants on every chain and build |
| **Accountable owner** | Principal Architect |
| **Consulted** | QA Lead; Solidity Lead; Contract Security Engineer; Backend Lead |
| **Required approvers** | Principal Architect; Wallet Protocol Engineer; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — In the audited bytecode and covered by FG-21 and FG-22. EV-P13 is required 'before the protocol freeze' by the Evidence Register. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records FG-21 and FG-22; a re-audit and a new `MandateManager`; every stored pin hash would be invalid, so customers would have to re-pin (`updateAccountPin`) or sign new mandates. |
| **Status** | **PROPOSED** |

**Rationale.** `PIN_OK` decides which accounts FastPay may charge. The sentinel and `KECCAK_EMPTY` handling accept a plain EOA whether its `EXTCODEHASH` is 0 (unused account) or `KECCAK_EMPTY` (funded account) and make a delegated or contract account equal only itself. Since 0.5 the pin is a typed struct whose shape `PIN_WELLFORMED` fixes; its layout is its type string, which PC-09 fixes.

**Failure it prevents.** A wrong handling either stops every plain-EOA customer (a false mismatch) or accepts an account that has gained code (a false match). A malformed pin could be signed and stored if the shape were not enforced.

**Mine, not a decision.** The sentinel string and the rules are those of [17 §5](17-account-compatibility-policy.md); they are not decisions. The proposal has no number: every value in this record is an exact constant or a predicate, so there is nothing of mine to tune.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- The planned test covers `PIN_EOA` and `KECCAK_EMPTY`; `PIN_WELLFORMED` and `PIN_OK` are predicates and are covered by ACP-TV vectors.
- A numeric schema constant is not part of this record: [17 §5.3](17-account-compatibility-policy.md) says none exists and that the layout is the type string (PC-09).

**Evidence required to decide.**

- UX-05: `EXTCODEHASH` of a delegated, unused and funded account on each launch chain
- EV-P10: `EXTCODEHASH` and `EXTCODESIZE` of a 7702-delegated account on each launch chain
- EV-P13: account pin behavior on each launch chain and through a type-4 transaction
- UD-09: pin for contract accounts: bytecode only or a registry-listed reader
- RISK-030: the pin pauses legitimate customers (false positives)
- RISK-032: for contract-account modes only the proxy bytecode is pinned
- CLM-053: opcode behavior of delegated accounts
- To be produced: EV-P13: `EXTCODEHASH` of an unused account (0), a funded account (`KECCAK_EMPTY`), a 7702-delegated account (designator hash), a proxy account and a self-destructed account on each launch chain and through a type-4 transaction, by fork tests and wallet-lab runs (WL-05, WL-11, WL-33): none yet.

**Safe range.**

- Too low: Not applicable as a range. A looser `PIN_OK` or `PIN_WELLFORMED` accepts an account whose code changed or a pin that no mode can produce.
- Too high: Not applicable as a range. A stricter `PIN_OK` (for example one that rejects `KECCAK_EMPTY` for a plain EOA) refuses funded accounts; a stricter `PIN_WELLFORMED` refuses pins the lab shows real wallets need.
- Can governance move it later: Governance cannot change them.
- Place of the proposal in the range: The proposal is the only acceptable value: the bytes32 constants and the predicates are exact.

**Cross-constraints.** X-17 (section 3).

**Tests.**

- Existing: ACP-TV-01, ACP-TV-02, ACP-TV-13, ACP-TV-14, ACP-TV-15, ACP-TV-16, ACP-TV-17, ACP-TV-25, ACP-TV-26, ACP-TV-27, ACP-TV-28, ACP-TV-29, ACP-TV-30, ACP-TV-34, I-ACCT-PIN, I-ACCT-NOWIDEN
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_PIN_EOA_AND_KECCAK_EMPTY`
- Note: `tools/model_checks.py` check [4] and `self_check()` in `tools/eip712_vectors.py` check the predicate on a Python model; they test nothing on a chain.

**Open points.**

- `PIN_WELLFORMED` is unreviewed by the wallet lab: the shape each mode must have (for example that mode 2 requires a non-empty delegate code hash and a non-zero `implementationFamily`) rests on the lab rows that do not exist yet (EVL-02, EVL-08).

**Sub-items**

| Sub-item | Symbol | Value or rule | Specified in | Fingerprint (FG) | Status |
|---|---|---|---|---|---|
| Account-pin sentinel | PIN_EOA | `keccak256` of the ASCII string `fastpay.pin.eoa.v1`: `0x8b07c3b3a0bc8c34a9a1a11064f80e35587006d2afc562b5114a4d9071547ba5` | [17 §5.1](17-account-compatibility-policy.md); vector in [17 §9](17-account-compatibility-policy.md) | FG-21; FG-22 | QUOTED |
| Hash of the empty byte string | KECCAK_EMPTY | `keccak256` of the empty byte string: `0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` | [17 §2.2](17-account-compatibility-policy.md), [17 §5.1](17-account-compatibility-policy.md) | FG-19; FG-21 | QUOTED |
| Handling of the sentinel in `PIN_OK` | PIN_EOA | A pin with `accountMode` 1 is satisfied by an `EXTCODEHASH` of 0 or `KECCAK_EMPTY` and by nothing else; modes 2 to 4 compare the code hash (and in mode 2 the delegate's code hash) for equality | [17 §5.2](17-account-compatibility-policy.md) | FG-21 | QUOTED |
| Well-formedness | PIN_WELLFORMED | The shape each mode must have (`pinVersion >= 1`, `accountMode` in 1 to 4, per-mode constraints on the other fields). Not restated here: [17 §5.2](17-account-compatibility-policy.md) is the single text | [17 §5.2](17-account-compatibility-policy.md) | FG-21 | QUOTED |
| Pin type hash and layout | ACCOUNT_PIN_TYPEHASH | Listed in PC-09 (the string and its hash). The layout of the struct is its type string; there is no separate schema constant ([17 §5.3](17-account-compatibility-policy.md)), and changing the string is a protocol change under PC-09 and PC-15 | [17 §5.1](17-account-compatibility-policy.md), [17 §5.3](17-account-compatibility-policy.md) | FG-21 | QUOTED |

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Wallet Protocol Engineer | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-16 — Cycle rule: cycleIndex ≤ floor((t − anchor) / periodSeconds), late cycles allowed

| Field | Value |
|---|---|
| **Symbols** | `CYCLE_INDEX_RULE` |
| **Proposed identifiers** | all of them: no document names these identifiers (proposed by the author of this record) |
| **Kind** | compile-time constant (contract logic, not a number) |
| **Enforced in** | `MandateManager.consume`: guard G9 and `cycleSettled[lineageId][cycleIndex]` ([11 §3.1](11-dual-cap-model.md), [11 §4.8](11-dual-cap-model.md), [11 §5](11-dual-cap-model.md) step 3) |
| **Proposed value** | `cycleIndex ≤ floor((t − anchor) / periodSeconds)`; late cycles are allowed; future cycles are not |
| **Unit** | seconds (`periodSeconds`, `anchorStartsAt`, `t`) and cycle index (uint64) |
| **Testnet value** | None: the same rule on every chain and build |
| **Accountable owner** | Principal Architect |
| **Consulted** | Payments PM; Solidity Lead; Head of Compliance |
| **Required approvers** | Principal Architect; Payments PM; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — In the audited bytecode and covered by FG-10 and FG-12. The evidence is a business sign-off that can be given before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records FG-10 and FG-12; a re-audit and a new `MandateManager`; a manager replacement keeps the once-per-cycle record only through the previous-manager lookup of [12 §5.7](12-router-lifecycle-and-migration.md). |
| **Status** | **PROPOSED** |

**Rationale.** The rule says which billing cycle a charge belongs to and, with `cycleSettled`, makes a cycle settle at most once for the whole life of a lineage, across routers and generations ([11 §3.1](11-dual-cap-model.md), `I-ONCE`). 'Late cycles allowed' means an unsettled cycle stays chargeable after its period has passed (retries); 'no future cycles' means a customer is never charged ahead of the period.

**Failure it prevents.** Too strict (only the current cycle is chargeable): a failed charge cannot be retried after its period ends. Too lax (future cycles allowed): bulk pre-collection. Unbounded lateness (the rule as written): a cycle from long ago can still be charged while the mandate lives.

**Mine, not a decision.** The rule is that of [11 §3.1](11-dual-cap-model.md), not a decision. The remark that lateness has no bound is mine: nothing limits how old an unsettled cycle may be except the mandate's expiry, its caps and the minimum interval.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Kind `compile-time constant` for contract logic: none of the four kinds describes a rule, and a rule compiled into the contract is the closest.
- Symbol `CYCLE_INDEX_RULE` is my proposal (the planned test is named after the rule, `test_ConfigRange_CYCLE_RULE`).

**Evidence required to decide.**

- ADR-009: once-per-cycle settlement
- ADR-015: migration is mandate lineage; cycle identity independent of the router
- UD-01: production-blocking constants (the freeze decision)
- To be produced: The Payments PM's sign-off for plans that are not fixed-period ([11 §12](11-dual-cap-model.md) point 6: none yet), a business decision on lateness (whether a cycle older than some number of periods should stop being chargeable: none yet), and counsel's view on charging a cycle after its period has passed (PB-029: none yet).

**Safe range.**

- Too low: A stricter rule (only the current cycle, or a short lateness bound) forbids retries across a period boundary; revenue is lost and merchants dispute charges.
- Too high: A looser rule (future cycles allowed, or no bound on lateness) permits pre-collection or charges for periods long past.
- Can governance move it later: Governance cannot change it: it is contract logic and it defines `cycleId` and `paymentId` semantics.
- Place of the proposal in the range: The proposal is the rule as written; there is no numeric range.

**Cross-constraints.** X-18, X-19 (section 3).

**Tests.**

- Existing: MIG-TV-11, MIG-TV-19, CAP-TV-21, I-ONCE, I-TIME
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_CYCLE_RULE`
- Note: MIG-TV-11, MIG-TV-19 and CAP-TV-21 test settle-once across generations and routers. No vector tests `cycleIndex` one above the allowed index (a future cycle) or a late cycle after its period; only the planned Foundry test does.

**Open points.**

- The rule needs `t ≥ anchorStartsAt` and `periodSeconds > 0`; guard G1 (`startsAt ≤ now`) and the lineage creation rules are expected to guarantee both; the contract specification should say so.
- Lateness is unbounded: whether a bound (for example a number of periods) is wanted is a Payments PM and counsel question.
- [11 §12](11-dual-cap-model.md) point 6: cycle semantics for plans that are not fixed-period are not defined.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Payments PM | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-17 — MIN_RECIPIENT_CHANGE_DELAY: minimum delay before a payout recipient change takes effect

| Field | Value |
|---|---|
| **Symbols** | `MIN_RECIPIENT_CHANGE_DELAY` |
| **Proposed identifiers** | all of them: no document names these identifiers (proposed by the author of this record) |
| **Kind** | immutable registry minimum |
| **Enforced in** | `MerchantRegistry`: `proposeRecipient` and `acceptRecipient`; a change takes effect no earlier than the delay and needs two parties (merchant admin and FastPay risk, OD-022) ([16 §8.1](16-freeze-decision-report.md)) |
| **Proposed value** | at least 48 hours |
| **Unit** | seconds (48 hours = 172,800 s) |
| **Testnet value** | 5 minutes (300 s) in a `-testconst` build ([16 §6](16-freeze-decision-report.md)) |
| **Accountable owner** | Merchant PM; Risk Lead |
| **Consulted** | Principal Architect; Head of Compliance; Payments PM |
| **Required approvers** | Merchant PM; Risk Lead; Principal Architect; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — UD-12 makes the minimum freeze-blocking; the value is in the audited bytecode. The evidence (merchant interviews and a drill) can exist before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request after the freeze; after the audit freeze a re-audit and a new `MerchantRegistry`, with the merchant registrations it holds. |
| **Status** | **PROPOSED** |

**Rationale.** Settlement goes to the recipient `MerchantRegistry` resolves at charge time (`I-RECIPIENT`), so a recipient swap redirects every future charge of every customer of that merchant. The delay gives the merchant, FastPay risk, monitoring and the customer portal time to see and stop a malicious or mistaken change. OD-022 asks for at least 48 hours, two-party approval, an event, a webhook and a portal display, and for high-risk changes to set new charges to `PAUSED_BY_RISK`.

**Failure it prevents.** A swap by a compromised merchant admin account (RISK-006). On the high side, a merchant stuck with a compromised payout address while the delay runs.

**Mine, not a decision.** At least 48 hours is the proposal of OD-022 and UD-12, not a decision. The hard maximum of 168 hours and the choice to place the proposal at the hard minimum are mine; the symbol is a proposed identifier (no document names the constant).

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Symbol `MIN_RECIPIENT_CHANGE_DELAY` is my proposal; [16 §7](16-freeze-decision-report.md) calls it 'minimum recipient-change delay'.

**Evidence required to decide.**

- OD-022: merchant recipient binding: resolved from the registry with a delay of at least 48 hours and two-party approval
- UD-12: the recipient change delay and approvals; freeze-blocking for the minimum
- RISK-006: merchant API key or charge signer compromised; recipient-change delay as a control
- RP-24: merchant interviews
- To be produced: Merchant interviews on payout rotation practice (RP-24: none yet) and a recipient-change drill that includes a high-risk change setting new charges to `PAUSED_BY_RISK`: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MIN_RECIPIENT_CHANGE_DELAY` | 48 hours (172,800 s) | 48 hours (172,800 s) | 168 hours (604,800 s) | seconds |

- Too low: Customers and monitoring have less than 48 hours to catch a swap; the minimum is set by OD-022.
- Too high: A merchant whose payout wallet is compromised cannot move away from it until the delay has passed (the merchant's own pause is the mitigation; to be confirmed with the Merchant PM).
- Can governance move it later: Governance can lengthen the delay for a merchant or globally and cannot shorten it below the constant. The constant is immutable.
- Place of the proposal in the range: At the hard minimum: 48 hours is the lowest value the safe range allows, so there is no headroom toward shorter.

**Cross-constraints.** X-08, X-23 (section 3).

**Tests.**

- Existing: I-RECIPIENT
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MIN_RECIPIENT_CHANGE_DELAY`
- Note: `I-RECIPIENT` covers settlement to the registry recipient valid at charge time. No vector tests the delay (a change one second before the delay and at it); only the planned Foundry test does.

**Open points.**

- Whether the merchant can pause its own charges while a change is pending (so that the delay protects without blocking a compromised-wallet response) is not specified.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Merchant PM | no | **NOT SIGNED** | — | — | — |
| Risk Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-18 — MAX_EXPOSED_TOKENS_PER_ROUTER: bound of the exposure index  (NEW IN 0.5)

**New in 0.5.** The sponsor-stated count of 17 production-blocking constants has become 18 because the shared-allowance rework of [12 §5.3.1](12-router-lifecycle-and-migration.md) needs a bound: the exposure index and the emergency check enumerate every token a customer's live mandates use on one router, and without a bound the gas of that enumeration is unbounded.

| Field | Value |
|---|---|
| **Symbols** | `MAX_EXPOSED_TOKENS_PER_ROUTER` |
| **Kind** | compile-time constant |
| **Enforced in** | `MandateManager`: the maximum number of distinct tokens across all of one customer's live mandates bound to one router; an activation that would exceed it reverts `ExposureLimit` (predicate X2 of `activateSuccessor`; `activate*`) ([12 §5.3](12-router-lifecycle-and-migration.md), [12 §5.3.1](12-router-lifecycle-and-migration.md), [12 §13](12-router-lifecycle-and-migration.md)) |
| **Proposed value** | 8 |
| **Unit** | count (distinct tokens per customer per router) |
| **Testnet value** | 3 tokens in a `-testconst` build ([16 §6](16-freeze-decision-report.md)): it lets the `ExposureLimit` and the emergency-mode enumeration tests run with few tokens; the checks are identical |
| **Accountable owner** | Solidity Lead; Principal Architect |
| **Consulted** | Wallet Protocol Engineer; Product Designer; Payments PM; Contract Security Engineer |
| **Required approvers** | Solidity Lead; Principal Architect; Payments PM; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — In the audited bytecode. The gas evidence is FZ-37 on the freeze checklist; the product data on tokens per customer cannot exist before the beta, so the value is decided on the gas argument and a recorded risk acceptance for the usability side. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records FG-14, FG-24 and FG-15; after the audit freeze a re-audit and a new `MandateManager`, adopted only through new mandates ([12 §5.7](12-router-lifecycle-and-migration.md)). |
| **Status** | **PROPOSED** |

**Rationale.** In an emergency migration the contract requires every token any live mandate of the customer uses on the old router to have no usable Permit2 allowance (predicate O1E), and the plan's `lockdown` names every such pair. The exposure index supplies the list ([12 §5.3.1](12-router-lifecycle-and-migration.md)). The enumeration costs at least one external call to Permit2 and one cold storage read per exposed token (unmeasured); the bound is what keeps that gas, and the size of the lockdown, finite.

**Failure it prevents.** Too high: the emergency check and the lockdown grow without a limit, up to the point a customer cannot migrate in an emergency. Too low: customers with many subscriptions are refused on activation with `ExposureLimit` until they revoke or retire something (an expired mandate that is not retired still counts: MIG-TV-36).

**Mine, not a decision.** 8 is the proposal stated for this register and in [12 §13](12-router-lifecycle-and-migration.md), not a decision, and no data stands behind it. The range `[MAX_TOKENS_PER_MANDATE, MAX_BATCH * MAX_TOKENS_PER_MANDATE]` is the range requested for this register. The owner is my proposal: [16 §7](16-freeze-decision-report.md) has no row for this constant. With ASM-009 (at most 10 tokens per chain at launch) a bound of 10 or more would never bite at launch; 8 can.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Owner: [16 §7](16-freeze-decision-report.md) has no PC-18 row; the Solidity Lead (gas) and the Principal Architect (design of [12](12-router-lifecycle-and-migration.md)) are proposed.
- Kind `compile-time constant`: [12 §13](12-router-lifecycle-and-migration.md) says 'immutable in `MandateManager`'.

**Evidence required to decide.**

- RP-19: gas measured on forks
- FZ-37: gas per planner step measured on forks (freeze checklist item)
- ASM-009: at most 10 tokens per chain are enabled at launch
- RISK-002: a Layer-2 allowance larger than needed amplifies a router bug
- To be produced: Fork gas measurement of the exposure-index updates and of the emergency check at 3, 8, 30 exposed tokens (RP-19: none yet on the chains; on the contracts the bound of 8 is measured inside the worst-case plan step, contracts/test/Gas.t.sol), and product data on distinct tokens per customer per router from the testnet alpha and the private beta: none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_EXPOSED_TOKENS_PER_ROUTER` | 8 | 3 | 30 | count |

- Too low: Customers with many subscriptions across many tokens are refused with `ExposureLimit` on activation, a customer-facing error that needs copy and a path (revoke, retire).
- Too high: The emergency check (one Permit2 read per exposed token) and the lockdown grow without bound; each exposed token is also an allowance that stays at risk until it is locked down.
- Can governance move it later: Governance cannot change it. A larger bound is a new `MandateManager`, adopted through new mandates ([12 §5.7](12-router-lifecycle-and-migration.md)).
- Place of the proposal in the range: 8 is 5 above the hard minimum and 22 below the hard maximum: at the low end of the range.

**Cross-constraints.** X-05, X-06, X-13 (section 3).

**Tests.**

- Existing: MIG-TV-37, MIG-TV-43, MIG-TV-33, MIG-TV-34, MIG-TV-38, I-MIG-10
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_EXPOSED_TOKENS_PER_ROUTER`
- Note: MIG-TV-37 tests eight exposed tokens accepted and a ninth refused; MIG-TV-43 and `I-MIG-10` test that the index never under-counts. None measures gas.

**Open points.**

- `ExposureLimit` is customer-facing: it needs a copy key and a planner pre-check so that a customer is told before signing.
- [12 §15](12-router-lifecycle-and-migration.md) open point 8: the gas of the index and of the O1E enumeration at the bound is not measured.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Solidity Lead | no | **NOT SIGNED** | — | — | — |
| Principal Architect | no | **NOT SIGNED** | — | — | — |
| Payments PM | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

### PC-19 — MAX_SIGNERS_PER_SET: bound of a quote-signer set  (NEW IN 0.5)

**New in 0.5 (implementation evidence).** The implementation of the signer sets needs a bound that no document stated: the members of a set are looped over when a set is proposed and when it is activated (the emergency rotation), and without a bound the gas of the activation that must always succeed is unbounded. Finding F-04 of the implementation report asked for this record; it was written when the contracts were built.

| Field | Value |
|---|---|
| **Symbols** | `MAX_SIGNERS_PER_SET` |
| **Kind** | compile-time constant |
| **Enforced in** | `SignerSetRegistry.proposeSignerSet`: a set has at most `MAX_SIGNERS_PER_SET` members; a larger proposal reverts `TooManySigners` before any loop runs. `verifySigner` (Q1 and Q13) is O(1) whatever the size of a set: it reads the tombstone, the set and the membership flag, never the member list ([11 §4.7](11-dual-cap-model.md), ADR-023) |
| **Proposed value** | 16 |
| **Unit** | count (members per quote-signer set) |
| **Testnet value** | None: the production value is kept on testnet; the constant is not in [16 §6](16-freeze-decision-report.md) |
| **Accountable owner** | Solidity Lead; Head of Security (CISO) |
| **Consulted** | Contract Security Engineer; Risk Lead; Chain Infra Lead |
| **Required approvers** | Solidity Lead; Risk Lead; Head of Security (CISO) (veto) |
| **Release gate** | RG-016; latest RG-002; evidence closes at RG-016 — In the audited bytecode. Its evidence is an internal measurement that can exist before the freeze. |
| **Change control** | FCR, RE-AUDIT, REDEPLOY — A Freeze Change Request that re-records the registry's fingerprint; after the audit freeze a re-audit and a new `SignerSetRegistry`. |
| **Status** | **PROPOSED** |

**Rationale.** A quote-signer set is a list of keys. Proposing a set writes each member, and activating it (the emergency rotation after a signer compromise) reads each member to refuse a key that was removed after the proposal. Those two loops are the only loops over members; the check that runs on every charge does not loop. The bound keeps the activation, the one transaction that must always fit in a block, finite.

**Failure it prevents.** Too high: a proposal that cannot be activated in one block, so an emergency rotation fails exactly when it is needed. Too low: no room for key redundancy (two operators, two regions) and for overlapping old and new members during a planned rotation.

**Mine, not a decision.** 16 is my proposal; no document stated a bound. The measurement on the contracts (contracts/test/Registries.t.sol): `verifySigner` costs the same gas for a set of 1, 2, 8 and 16 members (O(1), asserted equal), and proposing and activating a set of 16 stays well inside one block. The hard range [2, 64] is mine: 2 is the least that gives any redundancy; 64 keeps the proposal under about 3 million gas by linear extrapolation of the measurement at 16.

**Judgements made in this record** (to be confirmed or reversed by the approvers):

- Owner: no row of [16 §7](16-freeze-decision-report.md) existed; the Solidity Lead (gas) and the Head of Security (the key set) are proposed.
- Kind `compile-time constant`: the bound is an array bound, like PC-11.

**Evidence required to decide.**

- RISK-033: a compromised quote signer signs inside the bounds until removed
- KR-3: the grace and the bounds of a rotation (11 §4.7)
- To be produced: Fork gas measurement of the activation at 16 members on each launch chain (RP-19: none yet); the operational size of the quote-signer key set (Risk Lead, Head of Security): none yet.

**Safe range.**

| Quantity | Proposal | Hard minimum | Hard maximum | Unit |
|---|---|---|---|---|
| `MAX_SIGNERS_PER_SET` | 16 | 2 | 64 | count |

- Too low: A set of one has no redundancy: losing the key halts every fiat-capped charge until an emergency rotation is activated.
- Too high: Proposal and activation grow linearly; a larger set is also a larger attack surface (every member can sign a quote inside the bounds).
- Can governance move it later: Governance cannot change it. A different bound is a new `SignerSetRegistry`.
- Place of the proposal in the range: 16 is 14 above the hard minimum and 48 below the hard maximum: at the low end of the range.

**Cross-constraints.** X-13 (section 3).

**Tests.**

- Existing: CAP-TV-23…32
- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `test_ConfigRange_MAX_SIGNERS_PER_SET`
- Note: CAP-TV-23…32 test the rotation and the removal on the model; contracts/test/Registries.t.sol tests the bound (17 members refused), the activation and that the check is O(1).

**Open points.**

- The registry of the signer sets is a separate contract from `TokenPolicyRegistry` in the implementation (ADR-023); [06 §4](06-initial-architecture.md) still lists them together.

**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):

| Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|
| Solidity Lead | no | **NOT SIGNED** | — | — | — |
| Risk Lead | no | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

## 5. Approval register

Every slot of every record, in one table. A slot is changed only by editing the `approval` block of its record in the data file (R-1); this table follows.

| PC | Required approver | Veto | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|---|---|
| PC-01 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-01 | Head of Compliance | no | **NOT SIGNED** | — | — | — |
| PC-01 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-02 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-02 | Head of Compliance | no | **NOT SIGNED** | — | — | — |
| PC-02 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-03 | Head of Compliance | no | **NOT SIGNED** | — | — | — |
| PC-03 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-03 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-04 | Solidity Lead | no | **NOT SIGNED** | — | — | — |
| PC-04 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-04 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-05 | Finance | no | **NOT SIGNED** | — | — | — |
| PC-05 | Principal PM | no | **NOT SIGNED** | — | — | — |
| PC-05 | General Counsel | no | **NOT SIGNED** | — | — | — |
| PC-05 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-06 | Risk Lead | no | **NOT SIGNED** | — | — | — |
| PC-06 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-06 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-07 | Risk Lead | no | **NOT SIGNED** | — | — | — |
| PC-07 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-07 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-08 | Risk Lead | no | **NOT SIGNED** | — | — | — |
| PC-08 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-08 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-09 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-09 | Solidity Lead | no | **NOT SIGNED** | — | — | — |
| PC-09 | Wallet Protocol Engineer | no | **NOT SIGNED** | — | — | — |
| PC-09 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-10 | Payments PM | no | **NOT SIGNED** | — | — | — |
| PC-10 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-10 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-11 | Solidity Lead | no | **NOT SIGNED** | — | — | — |
| PC-11 | Product Designer | no | **NOT SIGNED** | — | — | — |
| PC-11 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-11 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-12 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-12 | Principal PM | no | **NOT SIGNED** | — | — | — |
| PC-12 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-13 | Solidity Lead | no | **NOT SIGNED** | — | — | — |
| PC-13 | Chain Infra Lead | no | **NOT SIGNED** | — | — | — |
| PC-13 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-13 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-14 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-14 | Board or its delegate | no | **NOT SIGNED** | — | — | — |
| PC-14 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-15 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-15 | Wallet Protocol Engineer | no | **NOT SIGNED** | — | — | — |
| PC-15 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-16 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-16 | Payments PM | no | **NOT SIGNED** | — | — | — |
| PC-16 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-17 | Merchant PM | no | **NOT SIGNED** | — | — | — |
| PC-17 | Risk Lead | no | **NOT SIGNED** | — | — | — |
| PC-17 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-17 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-18 | Solidity Lead | no | **NOT SIGNED** | — | — | — |
| PC-18 | Principal Architect | no | **NOT SIGNED** | — | — | — |
| PC-18 | Payments PM | no | **NOT SIGNED** | — | — | — |
| PC-18 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |
| PC-19 | Solidity Lead | no | **NOT SIGNED** | — | — | — |
| PC-19 | Risk Lead | no | **NOT SIGNED** | — | — | — |
| PC-19 | Head of Security (CISO) | yes | **NOT SIGNED** | — | — | — |

## 6. Testnet values and the `-testconst` rule

Only the constants of [16](16-freeze-decision-report.md) §6 may take a different value in a `-testconst` build. All other production-blocking constants keep their intended values on testnet ([14](14-protocol-freeze-pack.md) §4.5, rule 1).

| PC | Production proposal | Testnet value |
|---|---|---|
| PC-01 | 180 days | 20 minutes (1,200 s) in a `-testconst` build; the guard logic is identical ([16 §6](16-freeze-decision-report.md)); rule T-3 requires one fork run at 180 days with a time warp before the audit starts |
| PC-02 | 60 days | 10 minutes (600 s) in a `-testconst` build ([16 §6](16-freeze-decision-report.md)) |
| PC-03 | 365 days | 1 hour (3,600 s) in a `-testconst` build ([16 §6](16-freeze-decision-report.md)) |
| PC-04 | 10 | None: the production value is kept on testnet; the constant is not in [16 §6](16-freeze-decision-report.md) ([14 §4.5](14-protocol-freeze-pack.md) rule 1) |
| PC-05 | VALUE_PENDING | Any value that lets the ceiling tests run ([16 §6](16-freeze-decision-report.md)); no number is proposed |
| PC-06 | 300 seconds | 30 seconds in a `-testconst` build ([16 §6](16-freeze-decision-report.md)): only the speed of the quote tests changes and the TTL check is identical. The testnet `QUOTE_SET_GRACE` (60 s, PC-08) is at least this value, so X-01 holds on the testnet values |
| PC-07 | 500 bps | None: not listed in [16 §6](16-freeze-decision-report.md); the production value is kept on testnet |
| PC-08 | 300 seconds | 60 seconds ([16 §6](16-freeze-decision-report.md)): at least the testnet `MAX_QUOTE_TTL` of 30 seconds (PC-06), so X-01 holds on the testnet values; it also equals twice that value, the upper edge of X-02 |
| PC-09 | Strings and tags exactly as in the record | None: the same strings on every chain and build; a `-testconst` build must not differ in them (rule T-1) |
| PC-10 | 86,400 / 604,800 / 2,592,000 s | None: the production values are kept on testnet ([14 §4.5](14-protocol-freeze-pack.md) rule 1) |
| PC-11 | 3 | None: the production value is kept on testnet; not in [16 §6](16-freeze-decision-report.md) |
| PC-12 | 2 | None: the production value is kept on testnet; not in [16 §6](16-freeze-decision-report.md) |
| PC-13 | Canonical address, verified per chain | A testnet address or a deployment from the pinned commit ([16 §6](16-freeze-decision-report.md)); a testnet address is never evidence for a mainnet claim ([14 §4.1](14-protocol-freeze-pack.md)) |
| PC-14 | 72 h; stop-only | 2 minutes (120 s) for the timelock delay ([16 §6](16-freeze-decision-report.md)); guardian and governance thresholds and signers are test keys; the guardian's power set is identical |
| PC-15 | As [17 §5.1](17-account-compatibility-policy.md) and [17 §5.2](17-account-compatibility-policy.md) | None: the same constants on every chain and build |
| PC-16 | `cycleIndex ≤ floor((t − anchor) / periodSeconds)`; late cycles allowed | None: the same rule on every chain and build |
| PC-17 | at least 48 hours | 5 minutes (300 s) in a `-testconst` build ([16 §6](16-freeze-decision-report.md)) |
| PC-18 | 8 | 3 tokens in a `-testconst` build ([16 §6](16-freeze-decision-report.md)): it lets the `ExposureLimit` and the emergency-mode enumeration tests run with few tokens; the checks are identical |
| PC-19 | 16 | None: the production value is kept on testnet; the constant is not in [16 §6](16-freeze-decision-report.md) |

## 7. How to use the verifier

```text
python -I spec/tools/build_config_records.py --write     regenerate this file from spec/config/pc_records.json
python -I spec/tools/build_config_records.py --verify    run the checks; exit code 1 if any fails (--strict: warnings fail too)
python -I spec/tools/build_config_records.py             print the summary line
```

Checks: **[1]** every PC row of [16](16-freeze-decision-report.md) §7 has a record and the numbers agree (testnet values against §6); **[2]** every required field is present and non-empty; **[3]** every numeric proposal lies inside its safe range and every display agrees with its number; **[4]** the cross-constraints of section 3 hold; **[5]** no record is `APPROVED` without complete signatures; **[6]** every referenced identifier exists; **[7]** this file equals the generated text and its links resolve; **[8]** warnings for drift against the documents, the vector tool and the Foundry file.

**To record an approval:** produce the evidence and register its `EV-` id; each approver fills `name`, `date`, `evidenceIds` and sets `decision` to `SIGNED` in the record's `approval` block; when every slot (including the CISO's) is signed set `status` to `APPROVED`; run `--write` and `--verify`. After the freeze a change is a Freeze Change Request (R-4).

**What the verifier cannot do:** judge whether a value is right, read the content of evidence, or check anything on a chain. A passing run says the register is complete, consistent and honest about its state; it says nothing about the constants themselves.
