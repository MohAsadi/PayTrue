"""Revision 0.4 overlay, applied after revisions_v03.apply().

Changes of 0.4 (documents 11, 12, 16, 17):
  A  Account Compatibility Policy: account modes, on-chain account pin, per-mode permissions, re-verification
  M  Migration snapshot, containment mask, exact `activateSuccessor` predicates, router-independent cycle identity
  Q  PriceQuote v1 completed (fifteen fields), signer-set versions, key rotation, non-override proof
  R  Primary Permit2 revocation proved with fork tests; pinned Permit2 source review
  W  Wallet-lab evidence for the account modes
  P  PROGRAM profile restricted to coordination: delivery work reclassified (no change in estimates)

After apply() every epic carries pw03 (the v0.3 estimate), why04 (cause attribution of the v0.3 -> v0.4 change, which must sum to it)
and profile03 (the v0.3 profile).
"""
import sys
import model

TAGS04 = {
    "A": "Account Compatibility Policy: modes, on-chain account pin, re-verification",
    "M": "Migration snapshot, containment mask, exact successor predicates, router-independent cycle identity",
    "Q": "PriceQuote v1 completed: fifteen fields, signer sets, key rotation, non-override proof",
    "R": "Revocation primitives proved on forks; pinned Permit2 source review",
    "W": "Wallet-lab evidence for the account modes",
}

# Program epics are coordination only. Everything else that was labeled program is delivery or operations work and moves to the
# profile that owns it. The reason is stated so that the move can be challenged.
PROFILE04 = {
    "EPIC-P0-DOCS": ("infrastructure", "CI lint and claim-staleness checks are tooling"),
    "EPIC-P2-TESTNET": ("infrastructure", "operating the alpha environment, faucet and analytics is operations work"),
    "EPIC-P2-DOGFOOD": ("feature", "running the product lifecycle end to end is product validation"),
    "EPIC-P2-SUPPORTPREP": ("feature", "support tooling and playbooks are delivered capabilities"),
    "EPIC-P3-CANARY": ("infrastructure", "canary rollout, partner onboarding and daily go/no-go are production operations"),
    "EPIC-P3-SUPPORT": ("infrastructure", "support operations and the status page are operations"),
    "EPIC-P3-TOKENOPS": ("compliance", "weekly registry review and playbooks are an operated control"),
    "EPIC-P5-SUPPORT247": ("infrastructure", "24x7 coverage is an operated service"),
    "EPIC-P6-FLAGROLLOUT": ("infrastructure", "staged enablement, timelock execution and kill-switch drills are operations"),
    "EPIC-P6-BAU": ("infrastructure", "sustaining engineering and operations are delivery work"),
    "EPIC-P7-BAU": ("infrastructure", "sustaining engineering and operations are delivery work"),
}
PROGRAM_KEEP = {
    "EPIC-P0-HIRING": "staffing",
    "EPIC-P0-AUDITSEL": "procurement and contracting of audit and pen-test vendors",
    "EPIC-P5-GA": "assembly of gate evidence and the go/no-go meeting",
    "EPIC-P5-RELREADY": "release, rollback and communication plans",
}


def R(pw, why, **fields):
    d = dict(fields)
    d["pw"] = pw
    d["why04"] = why
    return d


REVISE04 = {
    "EPIC-P0-PROTOSPEC": R(19, {"A": 2, "M": 1},
        accept_add="The Account Compatibility Policy ([17]) with its modes, permissions, on-chain account pin and update path; the migration snapshot, containment mask and exact `activateSuccessor` predicates ([12 §5.3]); router-independent lineage, mandate and cycle identifiers; `PriceQuote` v1 with fifteen fields and key-rotation rules ([11 §4]); and the freeze-decision report ([16]) leave no unowned item.",
        impl_add=[("Account Compatibility Policy specification: modes, permissions, account pin, re-verification, vectors ACP-TV",
                   "Document 17 reviewed by Security and the Wallet Protocol Engineer; every mode has detection, permissions, evidence and vectors."),
                  ("Migration snapshot, containment mask and identifier derivations, with executable predicates",
                   "The predicates of 12 §5.3 are written as Foundry test oracles; the identifier vectors are reproduced by tools/eip712_vectors.py.")]),
    "EPIC-P0-PLANNER": R(11, {"A": 2},
        accept_add="Vectors ACP-TV-01…24 and planner vectors TV-27…TV-30 (account mode gating, pin in the plan, refusal for UNKNOWN_CODE) pass in both implementations (planner 1.3.0).",
        impl_add=[("Account mode input and account pin output of the planner (planner 1.3.0)",
                   "TV-27…TV-30 pass; an UNKNOWN_CODE account never receives a recurring plan; the pin value in the plan equals PIN_OK for the observed hash.")]),
    "EPIC-P0-WALLETLAB": R(20, {"W": 3},
        accept_add="Run records exist for each account mode (plain EOA, verified 7702 delegation, ERC-4337 account, ERC-1271 wallet) per claimed wallet, meeting the evidence list EVL-01…EVL-10 of [16 §9] (the freeze subset).",
        impl_add=[("Account-mode runs: 7702 delegate capture, 4337 and 1271 account behavior under Permit2, EXTCODEHASH pin behavior per wallet",
                   "Run records for the EVL set; the Compatibility Register carries mode, pin and delegate fields.")]),
    "EPIC-P0-SOURCES": R(15, {"R": 2},
        accept_add="The pinned Permit2 source review of [16 §5] (PR-01…PR-16) is complete at E2 with the commit SHA recorded, and the freeze subset of fork tests (RV-T01, 02, 04, 05, 07, 11 on a plain EOA, and MIG-TV-22) reproduces its claims; the full RV-T and ZP-T suites follow in `EPIC-P1-REVOKE`.",
        impl_add=[("Pinned Permit2 source review against the checklist PR-01…PR-16, with the freeze subset of fork tests",
                   "Reviewer sign-off at E2; each item cites file, function and line at the pinned commit.")]),
    "EPIC-P1-CONTRACTS": R(110, {"A": 3, "M": 4, "Q": 2},
        accept_add="Account pin: `consume` reverts `AccountCodeChanged` unless PIN_OK holds, and `updateAccountPin` needs customer authority and never changes a cap. `activateSuccessor` implements exactly the predicates of 12 §5.3, computes the migration snapshot on chain, requires `widenedMask` to equal the computed mask (zero for a migration) and emits the snapshot hash. Lineage, mandate and cycle identifiers contain no router address. `PriceQuote` v1 has the fifteen fields of 11 §4 and checks Q1…Q20; the non-override properties of 11 §4.8 hold under an adversarial signer.",
        impl_add=[("Account pin: PIN_OK check in consume, `updateAccountPin` by transaction or signature, PIN_EOA sentinel",
                   "ACP-TV and pin fork tests pass for plain, delegated and contract accounts; a pin update never changes a cap."),
                  ("Migration snapshot, containment predicate, widened mask and the exact successor predicates",
                   "Every predicate of 12 §5.3 has a passing and a failing test; the containment fuzz finds no accepted widening."),
                  ("Router-independent identifiers (lineage, mandate, cycle) and the cycle-index rule",
                   "The same (lineage, cycle index) cannot settle twice across routers and generations (MIG-TV-19)."),
                  ("PriceQuote v1 final fields and the signer-set, registry-version, route and source-set checks",
                   "Q1…Q20 tests; vector reproduced; adversarial signer cannot override a mandate.")]),
    "EPIC-P1-MIGRATION": R(23, {"M": 3},
        accept_add="The plans reproduce the atomic and legacy flows of 12 §5.4 with the predicate truth tables, show the widened mask to the customer, and treat the shared Permit2 allowance (all of the customer's lineages on the old router) explicitly.",
        impl_add=[("Snapshot, containment and widened-mask builder; exact atomic and legacy flows with the shared-allowance rule",
                   "MIG-TV-19…MIG-TV-26 pass on a fork; a plan that would leave a sibling lineage unfunded says so before signing.")]),
    "EPIC-P1-MANDATE": R(36, {"M": 2},
        impl_add=[("Lineage creation with subscription reference, billing period and the cycle-index rule independent of router version",
                   "The same subscription and cycle index produce the same payment id under any router and generation.")]),
    "EPIC-P1-DELEGATION": R(30, {"A": 8},
        name="Account Compatibility Policy engine: modes, on-chain pin, inspection, revalidation, re-verification",
        accept_add="The engine classifies every connected account into one of five modes with the detection predicates of [17 §2], applies the permission matrix of [17 §3], builds the account pin for the plan, detects a wallet-managed upgrade after activation, and drives re-verification (customer-signed pin update); ACP-TV-01…24 pass.",
        impl_add=[("Mode classification (plain EOA, verified 7702, ERC-4337, ERC-1271, unknown) from observation and allowlist rows",
                   "ACP-TV-01…24 pass; a code-bearing account without an E3 allowlist row is UNKNOWN_CODE."),
                  ("Account pin builder, pin check pre-flight and the customer-signed pin update flow",
                   "A simulated `AccountCodeChanged` is detected before submission and routed to re-verification; no charge is signed."),
                  ("Detection of wallet-managed upgrades after activation and the merchant-facing reason code",
                   "A plain EOA that becomes a delegated account stops charging, shows the re-verification flow and notifies the merchant with a reason code only.")]),
    "EPIC-P1-QUOTE": R(35, {"Q": 4},
        accept_add="The quote service issues the fifteen-field `PriceQuote` v1 with nonce, signer-set version, registry version, route hash and price-source-set hash; key rotation follows 11 §4.7 (overlap, grace, emergency removal).",
        impl_add=[("Signer-set versioning, rotation with grace and emergency removal; nonce, route hash and source-set hash",
                   "A rotation drill and a removal drill pass: no quote from a removed key validates, in-flight quotes of the previous set validate until the grace ends.")]),
    "EPIC-P1-TOKENREG": R(25, {"Q": 2},
        impl_add=[("Registry: signer sets by version, per-token registry version, price-source-set hash per token and currency",
                   "Version counters change exactly when 11 §4.7 says; every change is evented and timelocked.")]),
    "EPIC-P1-SIGNER": R(23, {"A": 1},
        accept_add="Signer policy refuses an unattended charge whose account-policy stamp is missing, older than 60 seconds, or computed for a different pin."),
    "EPIC-P1-REVOKE": R(11, {"R": 3},
        accept_add="The primary revocation flow (token approve zero, `Permit2.lockdown`, `invalidateNonces`) passes the fork tests RV-T01…RV-T12 of [05 §2.1] at the pinned commit, including accounts that are plain EOAs, 7702-delegated and contract accounts; the zero-amount signed permit stays disabled until ZP-T01…ZP-T08 and the wallet-lab runs pass.",
        impl_add=[("Fork test suite RV-T for the Permit2 revocation primitives and the ZP-T gate for the zero-amount permit",
                   "All RV-T pass; ZP-T results are recorded either way; the flag cannot be enabled without evidence ids.")]),
    "EPIC-P1-AUDITPREP": R(14, {"A": 1}),
    "EPIC-P1-FORK": R(17, {"R": 1}),
    "EPIC-P2-AUDIT": R(69, {"A": 2, "M": 1, "Q": 1},
        accept_add="The audit scope statement is the function-level list of [16 §8] (including the account pin, the successor predicates and the fifteen-field quote)."),
    "EPIC-P6-ROUTERV11": R(70, {"M": 10},
        accept_add="Includes the v1.1 `MandateManager`, which accepts the conversion consent in a non-zero extension field (a v1.0 manager refuses it), and reads cycle records from the previous manager through an immutable address; it is audited with the router. Adoption is a new mandate, not an `activateSuccessor` ([12 §5.7]).",
        impl_add=[("v1.1 MandateManager: conversion consent field, previous-manager cycle lookup, headroom-capped mandates",
                   "A mandate created in the v1.1 manager cannot settle a cycle the v1.0 manager already settled; the consent is signed typed data naming the router and the conversion terms.")]),
    "EPIC-P6-AUDITV11": R(44, {"M": 4},
        accept_add="The audit scope includes the v1.1 `MandateManager` and the previous-manager lookup."),
    "EPIC-P6-OPTIN": R(30, {},
        accept_add="Adoption is a new mandate in the v1.1 manager with caps equal to the old mandate's remaining headroom, the customer's conversion consent, and the old mandate and old router permission revoked ([12 §5.7]); it is never an `activateSuccessor`."),
    "EPIC-P2-PORTAL": R(25, {"A": 2},
        accept_add="The portal shows the account mode and pin status, offers re-verification after an account change, and signs the pin update."),
}


def apply():
    by_id = {e["id"]: e for e in model.EPICS}
    for e in model.EPICS:
        e["pw03"] = e["pw"]
        e["why04"] = {}
        e["profile03"] = e["profile"]
    for eid, ch in REVISE04.items():
        if eid not in by_id:
            sys.exit(f"v0.4 revision for unknown epic {eid}")
        e = by_id[eid]
        ch = dict(ch)
        why = ch.pop("why04")
        acc = ch.pop("accept_add", None)
        add = ch.pop("impl_add", None)
        for k, v in ch.items():
            e[k] = v
        if acc:
            e["accept"] = e["accept"].rstrip() + " " + acc
        if add:
            e["impl"] = list(e["impl"]) + list(add)
        e["why04"] = why
        if sum(why.values()) != e["pw"] - e["pw03"]:
            sys.exit(f"{eid}: why04 sums to {sum(why.values())} but pw - pw03 = {e['pw'] - e['pw03']}")
        for k in why:
            if k not in TAGS04:
                sys.exit(f"{eid}: unknown v0.4 tag {k}")
    for eid, (prof, _why) in PROFILE04.items():
        if eid not in by_id:
            sys.exit(f"profile change for unknown epic {eid}")
        if by_id[eid]["profile"] != "program":
            sys.exit(f"{eid}: expected profile program, found {by_id[eid]['profile']}")
        by_id[eid]["profile"] = prof
    left = {e["id"] for e in model.EPICS if e["profile"] == "program"}
    if left != set(PROGRAM_KEEP):
        sys.exit(f"program epics {sorted(left)} differ from the allowed coordination set {sorted(PROGRAM_KEEP)}")
