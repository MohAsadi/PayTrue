# Checkout configuration-record list (proposed)

| Field | Value |
|---|---|
| Artifact | FP-API-003 (new, proposed) |
| Version | 0.1.0 |
| Date | 2026-10-17 |
| Status | **PROPOSED. Nothing in it is approved.** Every approval slot is `NOT SIGNED`. Not protocol evidence |
| Owner | Payments PM (accountable), Technical Program Manager (list) |
| Governing document | [19 — Checkout session and wallet-connection profile](../19-checkout-session-and-wallet-connect-profile.md) §6 |

## 0. What this list is, and what it is not

This is the list of the configuration records of the checkout service. Today it holds **one** record, CSR-01, the **session lifetime**.

**It is not the register of production-blocking constants.** That register is [18 — Configuration records](../18-configuration-records.md) (PC-01 to PC-19, generated from `config/pc_records.json`). A record here is backend configuration with no contract effect ([18](../18-configuration-records.md) R-9). Consequently:

- a record of this list has no PC number and is **not counted** by condition C-4 of `freeze_readiness.py` (which still reads "0 of 19 approved");
- it does not change that tool's result or any freeze fingerprint;
- it cannot become a production-blocking constant except through [16](../16-freeze-decision-report.md) §7, which adds a PC record.

| ID | Symbols | Proposal | Unit | Kind | Status |
|---|---|---|---|---|---|
| CSR-01 | `SESSION_LIFETIME_MIN`, `SESSION_LIFETIME_DEFAULT`, `SESSION_LIFETIME_MAX` | 600, 1,800, 86,400 | seconds | Backend-configured policy bound, off chain | **PROPOSED** |

Other values that document 19 leaves unset (`MIN_SIGN_WINDOW`, the attempt limit per session, `sigTtl`, the finality rule per chain, the retention periods) have **no record here**: no value is proposed for them, and each would need its own record before it is used (doc 19 OPN-05, OPN-09, OPN-15). The numbers of the proposed API and events (doc 19 OPN-17) are proposals in the [API catalog](api-catalog.md) and the [event catalog](event-catalog.md), not records.

## 1. CSR-01 — session lifetime

| Field | Value |
|---|---|
| Symbols | `SESSION_LIFETIME_MIN`, `SESSION_LIFETIME_DEFAULT`, `SESSION_LIFETIME_MAX` (proposed identifiers: no document names them) |
| Kind | Backend-configured policy bound; off chain; no contract effect |
| Enforced in | The checkout-session service: validation at session creation (TR-01) and the timer of TR-23 |
| Proposed values | `SESSION_LIFETIME_MIN` **600 s** (10 minutes): the minimum lifetime a merchant may configure. `SESSION_LIFETIME_DEFAULT` **1,800 s** (30 minutes): the lifetime when `expires_in` is omitted (CSD-11). `SESSION_LIFETIME_MAX` **86,400 s** (24 hours): the maximum lifetime a merchant may configure |
| Unit | Seconds |
| Hard minimum and maximum (the author's proposal) | MIN: 600 to 1,800. DEFAULT: `SESSION_LIFETIME_MIN` to `SESSION_LIFETIME_MAX`. MAX: 1,800 to 604,800 (7 days) |
| Testnet value | Same as the proposal; no shorter test value is proposed |
| Accountable owner | Payments PM |
| Consulted | Product Designer, Head of Security, Privacy Lead, Payments Core lead, Merchant PM |
| Required approvers | Payments PM; Head of Security (CISO); Privacy Lead |
| Release gate | None assigned. It must be approved before the first release that exposes hosted checkout beyond internal testnet use; the TPM assigns the gate (RG-006 covers the webhook and frontend controls of the same release) |
| Change control | A configuration change with notice to the CISO. A change applies to **new** sessions only: an existing session keeps its `expiresAt` (doc 19 PX-09). No redeploy, no re-audit |
| Status | **PROPOSED** |

**Rationale.** A session must outlive several quotes and a human signing step, including the time to open a phone wallet and scan a code, and must not outlive the facts it displays (price, recipient, terms) for long. The default of 30 minutes was chosen by the sponsor (CSD-11). The minimum of 10 minutes is twice `MAX_QUOTE_TTL` (300 s, PC-06, proposed): a 5 minute minimum, which equals that ceiling, would leave no room to replace an expired quote and then sign. The maximum of 24 hours is long enough for a merchant that wants a customer to return later and short enough that the displayed terms do not go stale; a link that must live longer is a Payment Link (S03), which creates a new session per visit.

**Failure it prevents.** Too short: customers on a phone wallet cannot finish, and every quote expires before signing. Too long: stale terms and a stale merchant recipient are shown for a long time, and a leaked URL stays useful.

**Mine, not a decision.** The three numbers, the hard ranges, the choice of 10 minutes over the 5 minutes mentioned earlier in the conversation, the 7-day hard maximum, and the owner and approvers. The only number that comes from the sponsor is the default of 30 minutes.

**Cross-constraints.** `SESSION_LIFETIME_MIN ≥ 2 · MAX_QUOTE_TTL` (600 ≥ 2 · 300 holds on the proposals); `SESSION_LIFETIME_MIN ≤ SESSION_LIFETIME_DEFAULT ≤ SESSION_LIFETIME_MAX` (holds). Informative: the default quote TTL of 120 s (OD-027) is at most one tenth of the default lifetime (holds).

**Rules of document 19 that use it.** ER-01 to ER-10 and TR-01, TR-08, TR-23. The signature deadline, the quote validity and `PayOnceIntent.validUntil` are each at most `expiresAt` (ER-02 to ER-04).

**Evidence required to decide.** None exists. To be produced: usability tests with a phone wallet and a hardware wallet (time from the first screen to the signature), the distribution of signing times from the testnet alpha, and a Privacy and Security view on stale-link exposure.

**Tests.** None yet. The creation validation and the timer need unit tests; the rules ER-01 to ER-10 need state-machine tests (doc 19 §22.3, AC-05 to AC-07).

**Open points.** The three bounds are not approved (doc 19 OPN-10). `MIN_SIGN_WINDOW` and `sigTtl` have no approved value (doc 19 OPN-05).

**Approval block**

| Required approver | Decision | Name | Date | Evidence ids |
|---|---|---|---|---|
| Payments PM | **NOT SIGNED** | — | — | — |
| Head of Security (CISO) | **NOT SIGNED** | — | — | — |
| Privacy Lead | **NOT SIGNED** | — | — | — |
