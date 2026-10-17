"""Revision 0.3 overlay on the frozen v0.2 epic data (data_p0.py .. data_post.py).

Everything that changed in v0.3 is here, in one place:
  * PROFILE      - every epic's profile (feature, protocol, research, security, data, compliance, infrastructure, migration, program)
  * REVISE       - changed estimates (with a cause breakdown that must sum to the change), names, acceptance, stories
  * DROP         - epics removed
  * NEW          - epics added
`apply()` mutates model.EPICS. After it runs every epic has: prev_pw (v0.2 estimate), why03 (cause attribution), profile.

Cause tags for v0.3 (TAGS03):
  S  swap/conversion code absent from Router v1 (work removed from v1.0, added to v1.1 prep)
  L  mandate lineage, successor activation and primary revocation flows
  D  delegation revalidation before unattended charges (DELEGATION_UNVERIFIED)
  Q  signed quote schema formalization and cap classification
  P  epic profiles (story types that do not apply are no longer estimated or created)
  M  other
"""
import sys
import model
from model import SQUADS as S

TAGS03 = {
    "S": "Swap/conversion code absent from Router v1; conversion planned as Router v1.1",
    "L": "Mandate lineage, successor activation, primary revocation flows",
    "D": "Delegation revalidation before every unattended charge; DELEGATION_UNVERIFIED",
    "Q": "Signed quote schema formalization and three-class cap classification",
    "P": "Epic profiles (story types that do not apply are no longer created or estimated)",
    "M": "Other",
}

PROFILE = {
    # P0
    "EPIC-P0-DOCS": "program", "EPIC-P0-SOURCES": "research", "EPIC-P0-WALLETLAB": "research", "EPIC-P0-TOKENLAB": "research",
    "EPIC-P0-PLANNER": "protocol", "EPIC-P0-PROTO": "research", "EPIC-P0-THREAT": "security", "EPIC-P0-LEGAL": "compliance",
    "EPIC-P0-DESIGN": "feature", "EPIC-P0-PRODUCT": "research", "EPIC-P0-INFRA": "infrastructure", "EPIC-P0-HIRING": "program",
    "EPIC-P0-AUDITSEL": "program", "EPIC-P0-PROTOSPEC": "protocol",
    # P1
    "EPIC-P1-CONTRACTS": "protocol", "EPIC-P1-PAYONCE": "protocol", "EPIC-P1-FLAGS": "feature", "EPIC-P1-QUOTE": "feature",
    "EPIC-P1-MIGRATION": "migration", "EPIC-P1-DELEGATION": "feature", "EPIC-P1-FORK": "infrastructure", "EPIC-P1-CORE": "feature",
    "EPIC-P1-LEDGER": "data", "EPIC-P1-CHAINGW": "feature", "EPIC-P1-SIGNER": "feature", "EPIC-P1-MANDATE": "feature",
    "EPIC-P1-TOKENREG": "feature", "EPIC-P1-SECPROG": "security", "EPIC-P1-AUDITPREP": "security", "EPIC-P1-OBS": "infrastructure",
    "EPIC-P1-REVOKE": "security",
    # P2
    "EPIC-P2-ORCH": "feature", "EPIC-P2-CHECKOUT": "feature", "EPIC-P2-PORTAL": "feature", "EPIC-P2-MERCHANT": "feature",
    "EPIC-P2-COMPLIANCE": "compliance", "EPIC-P2-DEVDOC": "feature", "EPIC-P2-RUNBOOKS": "infrastructure", "EPIC-P2-TESTNET": "program",
    "EPIC-P2-AUDIT": "security", "EPIC-P2-PENTEST": "security", "EPIC-P2-SUBS": "feature", "EPIC-P2-DOGFOOD": "program",
    "EPIC-P2-SANDBOX": "feature", "EPIC-P2-RISKCON": "feature", "EPIC-P2-LOAD": "infrastructure", "EPIC-P2-REFUNDS": "feature",
    "EPIC-P2-LEGALPACK": "compliance", "EPIC-P2-A11YL10N": "feature", "EPIC-P2-DEPLOYPREP": "protocol", "EPIC-P2-RECON": "data",
    "EPIC-P2-PORTALS": "feature", "EPIC-P2-COMPOPS": "compliance", "EPIC-P2-SUPPORTPREP": "program", "EPIC-P2-MIGSVC": "migration",
    # P3
    "EPIC-P3-DEPLOY": "protocol", "EPIC-P3-CANARY": "program", "EPIC-P3-LIMITS": "compliance", "EPIC-P3-IRDR": "infrastructure",
    "EPIC-P3-BOUNTY": "security", "EPIC-P3-SUPPORT": "program", "EPIC-P3-RECONPROD": "data", "EPIC-P3-LEGALGO": "compliance",
    "EPIC-P3-TUNE": "infrastructure", "EPIC-P3-T1START": "feature", "EPIC-P3-TOKENOPS": "program", "EPIC-P3-ITERATE": "feature",
    "EPIC-P3-MIGDRILL": "migration",
    # P4
    "EPIC-P4-CHAINS": "protocol", "EPIC-P4-T1": "feature", "EPIC-P4-BOUNTYPUB": "security", "EPIC-P4-SCALE": "infrastructure",
    "EPIC-P4-FRAUD": "compliance", "EPIC-P4-I18N": "feature", "EPIC-P4-MERCHANTOPS": "compliance", "EPIC-P4-DATA": "data",
    "EPIC-P4-SECCONT": "security", "EPIC-P4-COMPEXP": "compliance", "EPIC-P4-ITERATE": "feature", "EPIC-P4-DRDRILLS": "infrastructure",
    "EPIC-P4-MIGGAME": "migration", "EPIC-P4-V11PREP": "research",
    # P5
    "EPIC-P5-GA": "program", "EPIC-P5-OPSMAT": "infrastructure", "EPIC-P5-DOCS": "feature", "EPIC-P5-DRILLS": "infrastructure",
    "EPIC-P5-SLALEGAL": "compliance", "EPIC-P5-SUPPORT247": "program", "EPIC-P5-PERFCOST": "infrastructure", "EPIC-P5-RELREADY": "program",
    # P6
    "EPIC-P6-ROUTERV11": "protocol", "EPIC-P6-AUDITV11": "security", "EPIC-P6-OPTIN": "migration",
    "EPIC-P6-ADAPTER": "protocol", "EPIC-P6-ADAPTERAUDIT": "security", "EPIC-P6-CONVBACKEND": "feature", "EPIC-P6-TOKENLABSTABLE": "research",
    "EPIC-P6-FLAGROLLOUT": "program", "EPIC-P6-REPEAT": "feature", "EPIC-P6-VARSUBS": "feature", "EPIC-P6-CHAINS2": "protocol",
    "EPIC-P6-QUOTEPAIRS": "feature", "EPIC-P6-COMPLV11": "compliance", "EPIC-P6-OPSV11": "infrastructure", "EPIC-P6-BAU": "program",
    # P7
    "EPIC-P7-ROUTERV2": "protocol", "EPIC-P7-AUDITV2": "security", "EPIC-P7-MIGCAMP": "migration", "EPIC-P7-GENCONV": "protocol",
    "EPIC-P7-ORACLE": "protocol", "EPIC-P7-TOKENLABGEN": "research", "EPIC-P7-USAGE": "feature", "EPIC-P7-TOPUP": "feature",
    "EPIC-P7-SPLITS": "feature", "EPIC-P7-WHITELABEL": "feature", "EPIC-P7-PARTNERAPI": "feature", "EPIC-P7-COMPLV2": "compliance",
    "EPIC-P7-BAU": "program",
}

DROP = {
    "EPIC-P1-CONVBOUND": ("S", "Conversion boundary plumbing removed from v1.0: conversion code is absent from Router v1; specification-only work moved into EPIC-P0-PROTOSPEC, build work into EPIC-P6-ROUTERV11"),
}


def R(pw=None, why=None, **fields):
    d = dict(fields)
    if pw is not None:
        d["pw"] = pw
    d["why03"] = why or {}
    return d


REVISE = {
    # ------------------------------------------------------------------ P0
    "EPIC-P0-DOCS": R(4, {"P": -1}),
    "EPIC-P0-SOURCES": R(13, {"D": 1, "P": -1},
        accept="Every design-load-bearing claim in Parts C and D is at evidence level E2 or higher; EV-P01, EV-P02, EV-P06, EV-P10 and EV-P11 closed; contradictions logged as CF items."),
    "EPIC-P0-WALLETLAB": R(17, {"D": 1, "P": -1}),
    "EPIC-P0-TOKENLAB": R(6, {"S": -2, "L": 1},
        name="Token behavior lab v0 (RP-07) including primary revocation-flow checks (EV-P11)",
        accept="Launch-candidate stablecoins on 2 chains tested for 12 behavior classes and for the primary revocation flows (token approve(0), Permit2 lockdown and approve(...,0,0)); registry seed produced; listing criteria written.",
        impl=[("Token behavior suite covering 12 behavior classes and the primary revocation flows, on fork",
               "Each class has a mock token and a pass/fail test the router must satisfy; revocation flows pass for approve-zero-first and no-return tokens."),
              ("Run on launch-candidate stablecoins on Base and Arbitrum",
               "Matrix with evidence links including EV-P11 rows; Security has reviewed the listing criteria.")],
        ops=("Listing workflow runbook: signers, evidence, expiry", "One listing dry run end to end with two approvers.")),
    "EPIC-P0-PLANNER": R(9, {"S": -1},
        accept="Two independent implementations pass TV-01..TV-26, TV-PO-1..TV-PO-12, CAP-TV-01..CAP-TV-13 and DRV-01..DRV-25 byte-for-byte; a differential fuzz of 100,000 random inputs yields zero divergences; the quote digest vector of document 11 section 4.6 is reproduced."),
    "EPIC-P0-PROTO": R(13, {"S": -2, "L": 1},
        name="Fork prototype (spike): mandate lineage, router, quote verification, Pay Once witness",
        accept="On a mainnet fork: activation by batch and by legacy path, one charge, gasless revoke, router paused while revoke still works, a successor mandate on a second router with lineage counters preserved and the old permission required to be unusable, a quote-verified charge, a Pay Once witness transfer; per-step gas recorded; all code tagged SPIKE and kept out of the production repository; no conversion code written.",
        impl=[("MandateManager and Router skeleton with activate, charge, revoke and activateSuccessor (lineage counters, old-permission check)",
               "Demonstrated on a mainnet fork per the epic acceptance; router paused while revoke still works; successor rejected while the old allowance is usable."),
              ("Spikes: quote verification with price bounds (document 11 section 4), a Pay Once witness transfer, and lockdown versus approve(...,0,0) revocation",
               "Each spike demonstrates its claim on a fork."),
              ("Gas measurement per planner step on forks (RP-19)", "Gas table by step and chain at p50 and p90 gas prices.")],
        test=("Fork tests for the migration partial states Q0..Q3 and for router-paused revoke",
              "All states are reproduced; revoke works while the router is paused.")),
    "EPIC-P0-THREAT": R(8, {"S": -1, "D": 1},
        accept="The 31 prompt-section-18 threats plus quote-signer compromise, migration phishing, delegation drift and revalidation abuse each have all template fields; the top 10 by risk have named tests; an external reviewer has signed off."),
    "EPIC-P0-LEGAL": R(5, {},
        accept="Counsel memo covers Q-01..Q-20 for each candidate jurisdiction (Q-03 on conversion is answered for v1.1 planning and is not on the v1.0 critical path); OD-001 is decided or deferred with reasons and a date; notice-duty guidance for router migration delivered; trademark report delivered."),
    "EPIC-P0-DESIGN": R(16, {"D": 1},
        name="Design foundations and flows (activation, Pay Once, dual-cap consent, router-specific authorization, delegation display and re-verification)",
        accept="Flows exist for planner paths A-D, refusal, PO-1..PO-6, dual-cap consent, router-specific successor authorization, delegation display and DELEGATION_UNVERIFIED re-verification; component specs pass WCAG 2.2 AA checks; RTL variants for checkout; a usability test with 8 participants shows at least 80% state both limits and how to revoke (PROPOSAL)."),
    "EPIC-P0-AUDITSEL": R(3, {},
        name="Audit and pen-test vendor selection (v1.0 scope: no conversion code)",
        accept="RFIs sent to at least 4 firms; the v1.0 contract scope is priced and the later Router v1.1 scope is priced separately (ASM-027); two audit firms contracted with slots from the planned freeze week; pen-test vendor shortlisted.",
        impl=[("RFI to at least four audit firms and book slots", "Two engagement letters with start dates."),
              ("Price the v1.0 contract scope and, separately, the Router v1.1 scope", "Two quotes per firm; ASM-027 updated with the figures.")]),
    "EPIC-P0-PROTOSPEC": R(16, {"Q": 2, "L": 1, "D": 1, "S": -2},
        name="Protocol specification set and freeze pack (mandate lineage, payment, Pay Once, dual cap and quote schema, router lifecycle, delegation revalidation, contracts D.1)",
        accept="Part C and D specifications exist for MandateManager (lineage, three pause bits), PaymentRouter v1 (both protocols, no conversion code), RouterRegistry, TokenPolicyRegistry, QuoteVerifier, MerchantRegistry, ExecutorRegistry, FeeController, RefundManager and EmergencyGuardian with storage, roles, events, errors and invariants; the protocol freeze checklist of document 14 is complete and reviewed by Security and Solidity; the quote vector is reproduced by two implementations.",
        impl=[("Mandate and payment specification: states, guards, events, customer copy keys, errors, three pause bits", "Every state transition has guard, event, API, copy key, contract check and test cases."),
              ("Contract-by-contract specification D.1 with storage layouts, access control and the external-call allowlist", "Each contract lists responsibility, trust boundary, storage, roles, functions, events, errors, invariants and attack surface."),
              ("Freeze pack: checklist, audit scope, testnet scope, wallet-lab matrix, quote schema and vectors", "Documents 14 and 15 reviewed; every freeze item has an owner and evidence.")]),
    # ------------------------------------------------------------------ P1
    "EPIC-P1-CONTRACTS": R(101, {"S": -14, "L": 4, "D": 2, "Q": 1},
        name="Core contracts v0.9 and Foundry suites (Router v1 without conversion code; mandate lineage; dual caps)",
        deps="RG-016 (protocol freeze); EPIC-P0-PROTOSPEC; EPIC-P0-PROTO", risk="H: logic bug (RISK-001)",
        accept="Every invariant in 06 section 4.1 has an invariant or property test; the invariant suite runs at least 1,000,000 calls with zero violations; branch coverage at least 95% on core contracts; static analysis has no unresolved high findings; the absence checks of 09 section 7 pass (no conversion selectors, call targets within the allowlist, no tx.origin); the quote digest and type hashes equal the vector of document 11; role-matrix and fee-ceiling tests pass.",
        evidence="Foundry reports; coverage report; absence-check report; vector reproduction",
        impl=[("MandateManager: mandates and lineages, dual caps with windows and fiat counters, activation by msg.sender and by EIP-712/ERC-1271 signature, three pause bits, revoke, reduce, extensionsHash must be zero",
               "All mandate state transitions in 06 section 3.3 are implemented with guards and events; counters follow 11 section 3 and live in the lineage."),
              ("PaymentRouter Protocol B: charge and chargeInitial via Permit2 AllowanceTransfer with QuoteVerifier, fee, registry recipient, zero-balance guarantee",
               "I-MANDATE, I-CAP-TOKEN, I-CAP-FIAT, I-QUOTE, I-ONCE, I-MINOUT and I-ZEROBAL hold in fuzz and invariant runs."),
              ("RouterRegistry and activateSuccessor: lifecycle, immutable notice minimums, containment checks, the old-permission-unusable check against Permit2, SUPERSEDED revocation",
               "MIG-TV-01..18 pass on a fork; MIN_NOTICE constants are immutable; exits are unblockable (I-MIG-4)."),
              ("TokenPolicyRegistry (SWAP_ONLY cannot be listed), MerchantRegistry, ExecutorRegistry, FeeController, EmergencyGuardian with separate switches, SignatureVerifier",
               "Role matrix equals 04 section 5; guardian cannot unpause or enable; fee ceiling is immutable.")],
        sec=("Reentrancy, access-control, arithmetic-rounding and external-call review, static analysis, and the no-dynamic-target and no-tx.origin checks",
             "Findings rated high or above are fixed; the static checks fail the build on any call with a caller-supplied target or any tx.origin use."),
        obs=("Event and custom-error catalogue for caps, quotes, lineage, lifecycle and pause bits",
             "Every state change emits an event; every revert reason is distinct and documented for monitoring."),
        mig=("Storage layouts frozen, interface versioning, deployment-manifest schema with several router versions per chain",
             "Layouts are checked in CI against the frozen file; the manifest records router versions and the absence-check result."),
        ops=("Deployment scripts dry-run on forks and guardian switch drill on testnet",
             "A scripted deployment reproduces the manifest twice; the guardian pause switches are exercised.")),
    "EPIC-P1-PAYONCE": R(21, {"S": -1}),
    "EPIC-P1-FLAGS": R(10, {"S": -4},
        name="Rollout-switch service with two-person enabling and fail-closed evaluation (a flag is not a security boundary)",
        accept="Enabling a flag needs two approvers and evidence ids; disabling needs one; every change is audited and evented; an unreachable service evaluates to false; flags are evaluated at plan and execution time; documentation and UI never describe a flag as a protection."),
    "EPIC-P1-QUOTE": R(31, {"Q": 1},
        accept="Quotes follow PriceQuote v1 exactly (document 11 section 4): validity predicate Q1-Q20, ECDSA-only signers, TTL at most the registry maximum; the quote-signer holds a separate HSM key class and refuses out-of-policy requests; quote issuance p95 under 500 ms; the digest vector is reproduced by the backend."),
    "EPIC-P1-MIGRATION": R(20, {"L": 2},
        name="Router lifecycle and lineage migration: orchestrator foundations, successor authorization builder, MigrationPlan, rehearsal harness",
        accept="MigrationPlan steps S1 (grant new), S2 (revoke old), S3 (activate successor) are produced and verified for ATOMIC_BATCH, MIXED and TX_SEQUENCE; MIG-TV-01..18 pass on a fork; the router-specific authorization renders named fields in the lab wallets.",
        impl=[("router_versions, mandate_lineages and mandate_generations tables, registry mirror, lifecycle event ingestion",
               "State of every router version and lineage is reproducible from chain events."),
              ("SuccessorAuthorization typed-data builder and MigrationPlan generation with the forced order S1, S2, S3 across ATOMIC_BATCH, MIXED, TX_SEQUENCE",
               "Partial states Q0..Q3 are reachable and re-plannable; no duplicate prompts; no zero-amount permit step unless the experimental flag is on."),
              ("Rehearsal harness: scripted deprecate, migrate, sunset, retire on a fork or testnet", "A full cycle runs unattended and produces a report.")],
        test=("MIG-TV-01..18 on a fork and chaos tests killing the wallet at each step",
              "All pass; every interruption leaves a re-plannable state.")),
    "EPIC-P1-DELEGATION": R(22, {"D": 6},
        name="Delegation inspector and revalidation: DelegationRecord, DelegationEvidence, classification, probes, per-charge revalidation, pause integration",
        accept="Every plan carries a delegation record under 5 minutes old; every unattended charge attempt passes the revalidation of document 13 section 7 or is blocked; DRV-01..DRV-25 pass; the policy table reproduces on synthetic delegates; DELEGATION_UNVERIFIED pauses and clears as specified; pre-flight aborts on a code-hash change.",
        evidence="Fork tests; vector run; record and evidence samples",
        impl=[("Inspection procedure, DelegationRecord storage and immutable DelegationEvidence rows",
               "Records are written from two agreeing RPC sources at one block, with proxy resolution and three-probe fingerprints."),
              ("Revalidation service: compare observation with evidence and return OK, INDETERMINATE or MISMATCH with exact diff sets; stamp attempts",
               "DRV-01..25 pass byte-for-byte; the orchestrator never signs an unattended charge without an OK stamp."),
              ("DELEGATION_UNVERIFIED pause: backend state, on-chain pause bit, customer re-verification flow, automatic clear rule, merchant reason code",
               "Pause, clear and re-verification paths pass DRV-21..23; no clear by time alone."),
              ("Classification, allowlist matching and the sig1271 gate feeding the planner",
               "TV-18..20 and TV-23 pass with real records.")],
        sec=("Probe safety review: fixed gas budget, no side effects, hostile-delegate handling; abuse of the pause path by an attacker toggling a delegate",
             "Probe cannot be used to trigger state changes; always-valid delegates are refused; pause toggling cannot widen authority."),
        obs=("Metrics and alerts: revalidation outcomes by diff code, pause counts and time-to-clear, false-positive rate, probe results",
             "Alert on a spike of one unknown delegate, any MAGIC probe, and an INDETERMINATE rate above threshold."),
        test=("Hostile-delegate fork tests plus swaps between plan, revalidation and signing",
              "Each is classified and handled as specified; EV-P07 evidence stored; DRV-24 passes."),
        mig=("Record and evidence schema versioning; evidence renewal rules",
             "Schema changes are additive; silent renewal of identical evidence works (DRV-15a)."),
        ops=("Allowlist review runbook, weekly unknown-delegate triage, and the support playbook for DELEGATION_UNVERIFIED",
             "First review held; entries need E3 evidence and two approvers; role-play completed.")),
    "EPIC-P1-FORK": R(16, {"S": -2},
        impl=[("Fork harness with pinned block heights, cached state and adversarial mempool simulation", "Reproducible runs; flake rate under 1%."),
              ("Token-lab results gate registry listings and revocation-flow evidence (EV-P11)", "A listing without lab evidence is rejected by CI.")]),
    "EPIC-P1-LEDGER": R(31, {"S": -3},
        accept="The database forbids UPDATE and DELETE on postings; property tests show debits equal credits per journal and asset over 1,000,000 random journals; scenarios direct payment, platform fee, failed payment, full refund, reorg reversal, reconciliation adjustment pass; fiat values are stored in minor units; replay of fork chain data reconciles at 100%; conversion journals are specified but not implemented before v1.1.",
        impl=[("Immutable double-entry ledger, chart of accounts and posting API keyed by chain, tx hash and log index", "Postings are immutable; corrections are reversals."),
              ("Scenarios: direct payment, fee, failure, full refund, reorg reversal, reconciliation adjustment", "Each scenario has golden journals."),
              ("Fiat valuation fields stored in minor units alongside atomic units and the quote evidence reference", "Fiat in minor units; the quote and its sourcesCommit are linked to the journal.")]),
    "EPIC-P1-CHAINGW": R(38, {"D": 2},
        accept="A chaos suite (lying RPC, lagging provider, 10,000 simulated reorgs) shows zero false FINALIZED; the nonce manager recovers from an injected stuck nonce; quorum disagreement yields UNKNOWN, never a charge; account code, nonce and balance reads are quorum-backed and a pre-charge observation API meets p95 under 1.5 s (PROPOSAL)."),
    "EPIC-P1-SIGNER": R(22, {"D": 2},
        accept="A 200-case policy test: every out-of-policy intent is refused (wrong contract, wrong selector, value not zero, over ceiling, rate limit, missing or invalid quote on a fiat-capped charge, missing or stale revalidation stamp on an unattended charge); the key ceremony is rehearsed; signing disables itself on policy-engine failure."),
    "EPIC-P1-MANDATE": R(34, {"L": 2},
        impl=[("Mandate compiler: fiat and token caps, windows, boundsVersion, termsHash", "CAP-TV-01..03 pass; termsHash is stable across implementations."),
              ("Activation sessions, re-planning from chain state and verification V1-V4", "Sessions resume without duplicate prompts."),
              ("Lineage-aware mandate service: successor generations, revisions with price-change consent, containment checks before a plan is offered", "A revision requires fresh consent; lineage history is queryable; a migration plan is never offered with wider terms.")]),
    "EPIC-P1-TOKENREG": R(23, {"S": -3},
        name="Token registry service and console, price bounds, quote-signer set, drift watchers",
        accept="Registry entries contain every field in prompt section 10 that v1 uses plus price bounds; a SWAP_ONLY listing is rejected in v1; the bytecode/implementation watcher detects a simulated proxy upgrade within 2 blocks and auto-blocks the token.",
        impl=[("Registry service and console with versioning and approval workflow", "Two approvers for listing; every change is evented."),
              ("Price-bound configuration and quote-signer set with timelocked on-chain sync", "On-chain and off-chain registry versions match."),
              ("Bytecode, implementation and issuer-event watchers", "Simulated upgrade detected within 2 blocks.")]),
    "EPIC-P1-AUDITPREP": R(13, {"S": -3},
        name="Audit readiness package (Router v1 without conversion code, registries, quote verification, lineage migration)",
        accept="Package includes specs, invariants, threat model, deployment scripts, test evidence, the absence-check report and the external-call allowlist; an internal pre-audit review has no open high findings; code freeze at the planned freeze week."),
    # ------------------------------------------------------------------ P2
    "EPIC-P2-ORCH": R(38, {"S": -1, "D": 1},
        accept="State-machine tests cover every allowed and prohibited transition in 06 section 3.2; a chaos test with timeouts at each step produces zero second-token charges while UNKNOWN; the on-chain once-per-cycle race test passes; quotes are acquired and re-acquired correctly before submission; delegation revalidation precedes quoting and signing of every unattended attempt and a failure never falls back to another token."),
    "EPIC-P2-PORTAL": R(23, {"D": 1},
        name="Customer mandate portal v0 (limits, usage, revoke, delegation status and re-verification, migration prompts)",
        accept="A customer can view both cap families and usage, pause, revoke (gasless via revokeBySig), request Permit2 lockdown by transaction, see delegation status and re-verify after a DELEGATION_UNVERIFIED pause, and complete a lineage migration; revoke takes effect on chain in the next block and the portal shows chain-verified status."),
    "EPIC-P2-MERCHANT": R(33, {"S": -1}),
    "EPIC-P2-COMPLIANCE": R(19, {"P": -1}),
    "EPIC-P2-RUNBOOKS": R(10, {"S": -1, "D": 1},
        name="Runbook stubs RB-001..RB-032 and detection backlog (RB-033 conversion kill switch arrives with v1.1)",
        accept="32 stubs each with trigger, detection, severity and owner (including RB-031 migration campaign and RB-032 emergency router disablement); the detection backlog is mapped to the section-23 list, to delegation revalidation outcomes and to router lifecycle changes."),
    "EPIC-P2-TESTNET": R(30, {"P": -4}),
    "EPIC-P2-AUDIT": R(65, {"S": -8, "L": 1},
        name="Two parallel audits (Router v1 without conversion code, registries, quote verification, lineage migration), remediation, re-review",
        accept="All critical and high findings fixed and re-reviewed by the finding firm; medium and low triaged with written rationale; final reports archived; the audit scope statement lists in-scope and out-of-scope contracts and states that no conversion code exists in v1.0; RG-005 criteria met."),
    "EPIC-P2-DOGFOOD": R(14, {"P": -2},
        accept="One full lifecycle (activate, 6 cycles, pause, resume, revoke, refund, and one router migration by successor mandate) per supported path with ledger reconciliation at 100%.",
        impl=[("Run FastPay's own subscription on testnets across wallets and paths", "Lifecycle completed per path."),
              ("Router migration exercised by internal accounts using a successor mandate", "Successor completes, the old permission is shown revoked, and counters carry over.")]),
    "EPIC-P2-RISKCON": R(42, {"S": -2},
        accept="Risk can pause a mandate, merchant, token and set the delegation pause bit, and cannot widen authority (tested); the admin console cannot change on-chain customer authority; the P1 subset of section-23 detections, including quote-signer and revalidation rules, is implemented with alert routing tested; the limit engine enforces BACKEND_ONLY controls with two-approver loosening."),
    "EPIC-P2-LEGALPACK": R(23, {"S": -1},
        accept="Counsel signs consent and disclosure copy per jurisdiction, including dual-cap, delegation, router-specific authorization and migration-notice keys; DPIA completed; data-subject request process tested end to end."),
    "EPIC-P2-DEPLOYPREP": R(27, {"S": -1},
        name="Mainnet deployment tooling, ceremony and migration rehearsal (absence proof, lineage lifecycle)",
        accept="The deployment script produces a signed manifest (including the absence-check result) and verifies bytecode against the audited build on forks of 2 chains; governance and guardian multisig plus timelock are rehearsed on testnet; a full router deprecate-migrate-sunset-retire cycle using successor mandates is rehearsed (PB-006).",
        impl=[("Deployment pipeline, manifest signing, absence checks and independent bytecode verification", "Two parties reproduce the manifest."),
              ("Multisig, timelock and guardian configuration scripts and ceremony rehearsal", "Rehearsal produces the expected on-chain roles."),
              ("Full router lifecycle rehearsal on testnet with lineage successors", "Registry transitions, notices, successor activation and old-permission revocation all complete.")]),
    "EPIC-P2-COMPOPS": R(31, {"P": -1}),
    "EPIC-P2-SUPPORTPREP": R(15, {"P": -1}),
    "EPIC-P2-MIGSVC": R(32, {"L": 2},
        impl=[("Campaign, cohort and notice engine with halting criteria", "Cohort stages and halts work in staging."),
              ("Notice delivery across portal, consented channels and merchant webhooks with unsubscribe and language handling", "Delivery receipts stored; no duplicate notices."),
              ("Pre-deprecation dry-run report (M11), billing-aligned prompt timing (M6) and the Q2 hold that suppresses charge attempts and dunning during a half-finished migration (M12)",
               "Report generated for a synthetic router with 10,000 mandates; a mandate in Q2 produces no failed charge and no dunning notice and the hold expires after 24 hours.")]),
    # ------------------------------------------------------------------ P3
    "EPIC-P3-DEPLOY": R(26, {"S": -2},
        name="Mainnet deployment ceremony (Router v1, no conversion code)",
        accept="Contracts are deployed on Base and Arbitrum One from the signed manifest; bytecode is verified by two independent parties; deployer privileges are renounced; timelock and multisig configured; contracts verified on explorers (PB-012); the manifest records the absence-check result: no conversion selectors, no conversion contract (PB-040).",
        obs=("Code-hash, role and external-call-allowlist monitors", "Monitors page on any drift."),
        evidence="Signed manifest; verification records; absence-check report"),
    "EPIC-P3-CANARY": R(62, {"P": -4}),
    "EPIC-P3-LIMITS": R(27, {"P": -1}),
    "EPIC-P3-BOUNTY": R(13, {"S": -1},
        name="Private bug bounty (scope: contracts, lineage migration, quote verification, delegation revalidation)",
        impl=[("Program scope, rewards and rules, with an explicit statement that no conversion code exists in v1.0", "Published."),
              ("Triage workflow and fix pipeline", "SLA met in the first 30 days.")]),
    "EPIC-P3-SUPPORT": R(24, {"P": -2}),
    "EPIC-P3-LEGALGO": R(21, {"S": -1},
        accept="Written counsel confirmation for each launch jurisdiction covering consent, notices, delegation wording and router-specific authorizations (no conversion is offered in v1.0); licences or partner agreements in place."),
    "EPIC-P3-TOKENOPS": R(15, {"S": -2, "P": -1},
        accept="Weekly registry review; depeg and issuer-event playbooks exercised; revocation-flow evidence (EV-P11) refreshed for every listed token."),
    "EPIC-P3-MIGDRILL": R(16, {},
        accept="A full lifecycle on a mainnet canary with internal accounts: register a candidate router, activate, deprecate with the minimum notice enforced, migrate through every partial state Q0..Q3 with successor mandates, sunset, and verify that a successor can still be created after sunset; zero stranded mandates; old permissions verified unusable before each successor activates.",
        impl=[("Deploy a candidate router version on canary and run the lifecycle", "All transitions occur with expected events."),
              ("Run migration with each transport and forced interruptions", "Q0..Q3 handled; the old-permission check rejects an early S3."),
              ("Verify post-sunset successor creation and rollback within the window", "Both succeed.")]),
    # ------------------------------------------------------------------ P4
    "EPIC-P4-FRAUD": R(74, {"P": -2}),
    "EPIC-P4-MERCHANTOPS": R(42, {"P": -2}),
    "EPIC-P4-COMPEXP": R(42, {"P": -2}),
    "EPIC-P4-V11PREP": R(40, {"S": 4},
        name="v1.1 readiness: Router v1.1 scope and plan, adapter selection, token-lab pair plans, peg and price-bound research, legal Q-03",
        accept="A written v1.1 plan: Router v1.1 and ConversionPolicyRegistry scope and audit plan, chosen stable-pair adapter design, pair list with lab plans, band proposals from historical depeg replay, counsel answer on Q-03, opt-in migration plan, and a staged rollout schedule.",
        mig=("Plan the opt-in lineage migration to Router v1.1 (no forced migration of Router v1 customers)", "Written plan reviewed by Compliance and Support; the audit firms confirm the Router v1.1 scope.")),
    # ------------------------------------------------------------------ P5
    "EPIC-P5-GA": R(80, {"P": -4},
        accept="Every GA prerequisite in prompt section 25 has evidence in the Release Gate Register; go/no-go signed by Head of Product, VP Engineering, CISO and Head of Compliance; the absence evidence for conversion code and the migration-readiness evidence are current."),
    "EPIC-P5-DRILLS": R(42, {"S": -2},
        name="Final IR, DR and chaos exercises",
        accept="Exercises on all Sev-1 runbooks completed in the 90 days before GA, including RB-032; open actions closed.",
        impl=[("Final exercise program", "Complete."), ("Revalidation and migration failure scenarios in the exercises", "Included and timed.")]),
    "EPIC-P5-SLALEGAL": R(21, {"S": -1},
        accept="Counsel-approved final terms in every jurisdiction, including router-lifecycle notice terms."),
    "EPIC-P5-SUPPORT247": R(42, {"P": -2}),
    "EPIC-P5-RELREADY": R(20, {"P": -2}),
}

# ---------------------------------------------------------------------- P6/P7 text revisions (post-GA estimates are not re-attributed)
POST_TEXT = {
    "EPIC-P6-ADAPTER": dict(
        deps="EPIC-P4-V11PREP; EPIC-P6-ROUTERV11",
        accept="The adapter takes typed parameters only, calls only registry-listed targets with fixed selectors, enforces minOut by balance delta and a price-impact cap, returns residue, and passes I-NOARB and I-ZEROBAL on forks with adversarial ordering; conversion through it is reachable only when conditions C1 and C2 hold (the router version contains conversion code and the registry has approved the adapter and the pair).",
        mig=("Confirm registration in ConversionPolicyRegistry needs no router migration beyond Router v1.1 itself", "Registration on a testnet deployment of Router v1.1 succeeds without redeploying the router.")),
    "EPIC-P6-ADAPTERAUDIT": dict(
        mig=("Impact on audited code: the adapter registers into the already-audited Router v1.1", "Auditors confirm no router change is needed for registration.")),
    "EPIC-P6-CONVBACKEND": dict(
        deps="EPIC-P6-ROUTERV11; EPIC-P6-ADAPTER",
        mig=("No schema migration to enable: fields are additive and used only for Router v1.1 mandates", "Enabling touches configuration and the new router only.")),
    "EPIC-P6-TOKENLABSTABLE": dict(
        name="Token-lab approvals for stable pairs (defines and issues labApprovalHash records)",
        impl=[("Define the approval record format and registry fields, then run the token lab for each candidate pair on forks and testnets", "Full evidence per pair; format reviewed by Security."),
              ("Issue and register approvals in ConversionPolicyRegistry", "Registry shows a non-zero labApprovalHash for approved pairs only.")]),
    "EPIC-P6-FLAGROLLOUT": dict(
        deps="EPIC-P6-AUDITV11; EPIC-P6-ADAPTERAUDIT; EPIC-P6-CONVBACKEND; EPIC-P6-TOKENLABSTABLE; EPIC-P6-OPTIN",
        name="Staged rollout of stable conversion (rollout switch R) and kill-switch drills",
        accept="Stages internal, one merchant, cohort, general availability each pass exit metrics and a hold period; conditions C1 (customers opted in to Router v1.1) and C2 (ConversionPolicyRegistry class open, adapter and pair registered) are verified at each stage; R is enabled by two approvers; the kill switch closes R in under 60 seconds and C2 via the guardian in the drill; R is never counted as a protection."),
    "EPIC-P6-REPEAT": dict(mig=("Repeat-purchase mandates ship with Router v1.1 (opt-in), not as a change to Router v1", "A Router v1 customer is unaffected; the successor path is exercised.")),
    "EPIC-P6-QUOTEPAIRS": dict(
        name="PriceQuote v2 (route-bound) and pair-specific bands, peg monitoring",
        accept="PriceQuote v2 uses its own domain version and type hash and cannot validate on Router v1; pair bands apply with intersection semantics; independent-source peg monitoring tightens off-chain limits automatically; false-rejection rate is within target in replay."),
    "EPIC-P7-GENCONV": dict(
        mig=("The general route class needs new code: it ships in Router v2 (or a v1.x router) and is adopted by opt-in successor mandates", "A successor to the new router completes with the old permission revoked.")),
    "EPIC-P7-ORACLE": dict(
        mig=("Oracle-referenced bounds need a new verifier version, shipped with the new router", "Existing mandates are unaffected; adoption is by opt-in successor.")),
}

NEW = [
    dict(id="EPIC-P1-REVOKE", phase="P1", name="Primary revocation flows: portal and SDK flows, plan validator, per-token verification (EV-P11)", squad=S["PROTO"], pw=8,
         why03={"L": 8}, deps="EPIC-P0-TOKENLAB; EPIC-P1-CONTRACTS", risk="M: token quirks (RISK-031)",
         accept="Token approve(0), Permit2 lockdown and approve(...,0,0), invalidateNonces and MandateManager revoke/revokeBySig work for every listed token and chain on forks; the plan validator rejects any plan with a zero-amount permit step while the experimental flag is off; the portal and SDK expose the primary flows with accurate cost and gas wording.",
         evidence="EV-P11 fork results; validator tests", target="RG-004", labels="SECURITY-CRITICAL",
         impl=[("Portal and SDK revocation flows: L3 revoke (gasless), L2 lockdown, L1 approve(0), nonce invalidation", "Flows work on testnets across the wallet matrix; no flow claims to be gasless unless it is."),
               ("Plan validator that rejects experimental or unsupported revocation steps", "NC-17 and MIG-TV-16 pass.")],
         sec=("Review of revocation edge cases: ZERO_FIRST tokens, no-return tokens, expired allowances, nonce griefing", "No case leaves a usable permission without the customer being told."),
         obs=("Revocation outcomes and time-to-effect metrics", "Customers' revoke-to-confirmation p95 measured; failures alerted."),
         test=("Fork tests per token and chain at the pinned Permit2 commit (EV-P11)", "All primary flows pass for every listed token; failures block listing."),
         mig=("Migration of any legacy approval-management screens to the new flows", "Old screens redirect; no data loss."),
         ops=("Support playbook for failed or partial revocations", "Role-play completed.")),
    dict(id="EPIC-P6-ROUTERV11", phase="P6", name="Router v1.1: typed conversion entrypoints, PriceQuote v2 verification, ConversionPolicyRegistry integration", squad=S["PROTO"], pw=60,
         why03={}, deps="EPIC-P4-V11PREP; RG-012", risk="H: new fund-moving logic (RISK-001, RISK-014)",
         accept="Router v1.1 adds typed conversion entrypoints for Protocols A and B, PriceQuote v2 verification, minOut by balance delta, price-impact checks and residue return, and consults ConversionPolicyRegistry (class open, adapter code hash, pair approval hash); every v1 invariant still holds; I-NOARB holds (adapter targets only from the registry); it is registered through the lifecycle as a new version with its own domain.",
         evidence="Invariant runs; fork tests; absence checks inverted for the new router", target="RG-013", labels="SECURITY-CRITICAL,FINANCIAL-CONTROL",
         impl=[("Conversion entrypoints and route handling for recurring and Pay Once", "Realized output at least the signed minimum; residue returned; router balance unchanged."),
               ("ConversionPolicyRegistry: route classes, approved pairs with labApprovalHash, adapters with code hash, guardian close", "C2 enforced on chain; guardian can close a class at once."),
               ("PriceQuote v2 and PayOnceIntentV2 under new domain versions", "A v1 signature cannot validate on v1.1 and vice versa.")],
         sec=("Adversarial review of conversion paths: sandwiching, malicious tokens, adapter reentrancy, rounding", "No finding rated high or above remains."),
         obs=("Events and metrics for conversion: realized price impact, residue, reverts by reason", "Dashboards and alerts specified and tested on forks."),
         test=("Invariants and fork tests with adversarial ordering and depegged pools", "Loss bounded by minOut and caps in every scenario."),
         mig=("Opt-in adoption: successor mandates to Router v1.1; Router v1 unaffected", "A lineage migration to v1.1 completes on a fork with counters preserved."),
         ops=("Deployment, registration and emergency-disable drills for the new router", "Drills completed on testnet.")),
    dict(id="EPIC-P6-AUDITV11", phase="P6", name="Independent audit of Router v1.1 and ConversionPolicyRegistry, remediation, re-review", squad=S["PROTO"], pw=40,
         why03={}, deps="EPIC-P6-ROUTERV11", risk="H: findings volume (RISK-012)",
         accept="A new-router-version audit (full review of changed and new paths, not only a diff) with no open critical or high findings; reports archived; RG-013 criterion 1 met.",
         evidence="Audit report; remediation log", target="RG-013", labels="SECURITY-CRITICAL,PRODUCTION-BLOCKER",
         impl=[("Auditor support and fix development", "Questions answered within 1 business day."),
               ("Re-review and report publication", "Firm confirms closure of critical and high findings.")],
         sec=("Fix review for new attack surface", "Reviewed by someone outside the author's squad."),
         obs=("Audit findings tracker with severities, owners and ages", "Visible weekly to TPM and CISO."),
         test=("Regression of v1 and v1.1 suites after fixes", "Green before merge."),
         mig=("Interface freeze for Router v1.1", "Changes after freeze need an exception."),
         ops=("Disclosure plan for the report", "Counsel-reviewed.")),
    dict(id="EPIC-P6-OPTIN", phase="P6", name="Opt-in migration to Router v1.1: campaign tooling, consent copy and rollout", squad=S["CORE"], pw=30,
         why03={}, deps="EPIC-P6-ROUTERV11; EPIC-P2-MIGSVC", risk="M: response rate (ASM-028)",
         accept="Customers can opt in to Router v1.1 with a router-specific successor authorization that states the new capability (conversion), its risks and the old permission revocation; customers who do nothing remain on Router v1 unchanged; new customers can start on Router v1.1; campaign metrics show opt-in rate and zero stranded mandates.",
         evidence="Campaign report; comprehension test", target="RG-013", labels="PRIVACY-CRITICAL",
         impl=[("Opt-in prompts and consent copy explaining token substitution, slippage bounds and price-impact limits", "At least 80% of test participants state what conversion changes (PROPOSAL)."),
               ("Cohort rollout reusing the migration orchestrator", "Stages and halts work.")],
         sec=("Phishing and misleading-consent review for opt-in prompts", "Findings closed; no dark patterns."),
         obs=("Opt-in funnel and substitution-rate metrics", "Visible per cohort."),
         test=("Simulation with non-responders and interrupted migrations", "No mandate is stranded."),
         mig=("Rollback: successor back to Router v1 within the rollback window", "Rehearsed."),
         ops=("Support playbook for opt-in questions", "Role-play completed.")),
]


# ---------------------------------------------------------------------- apply
def apply():
    by_id = {e["id"]: e for e in model.EPICS}
    for e in model.EPICS:
        e["prev_pw"] = e["pw"]
        e["why03"] = {}
        e["profile"] = None
    model.DROPPED = []
    for eid, (tag, note) in DROP.items():
        e = by_id.pop(eid)
        model.EPICS.remove(e)
        model.DROPPED.append((eid, e["prev_pw"], tag, note))
    for eid, ch in REVISE.items():
        if eid not in by_id:
            sys.exit(f"revision for unknown epic {eid}")
        e = by_id[eid]
        why = ch.pop("why03", {})
        for k, v in ch.items():
            e[k] = v
        e["why03"] = why
        delta = e["pw"] - e["prev_pw"]
        if sum(why.values()) != delta:
            sys.exit(f"{eid}: why03 sums to {sum(why.values())} but pw - prev_pw = {delta}")
        for k in why:
            if k not in TAGS03:
                sys.exit(f"{eid}: unknown tag {k}")
    for eid, ch in POST_TEXT.items():
        if eid not in by_id:
            sys.exit(f"post text for unknown epic {eid}")
        for k, v in ch.items():
            by_id[eid][k] = v
    for n in NEW:
        n = dict(n)
        why = n.pop("why03")
        model.epic(n["id"], n["phase"], n["name"], n["squad"], n["pw"], None, {}, n["deps"], n["risk"], n["accept"],
                   n["evidence"], n["target"], n.get("labels", ""), impl=n["impl"], sec=n["sec"], obs=n["obs"],
                   test=n["test"], mig=n["mig"], ops=n["ops"])
        e = model.EPICS[-1]
        e["prev_pw"] = 0
        e["why03"] = why
        e["profile"] = None
        if why and sum(why.values()) != e["pw"]:
            sys.exit(f"{n['id']}: why03 must sum to pw for a new epic")
    ids = {e["id"] for e in model.EPICS}
    for e in model.EPICS:
        e["profile"] = PROFILE.get(e["id"])
        if e["profile"] is None:
            sys.exit(f"{e['id']}: no profile assigned")
    extra = set(PROFILE) - ids
    if extra:
        sys.exit(f"profiles for unknown epics: {sorted(extra)}")
