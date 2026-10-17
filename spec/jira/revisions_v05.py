"""Revision 0.5 estimate overlay, applied after revisions_v04.apply().

Changes of 0.5 that move estimates (documents 11, 12, 14, 16, 17):
  S  Shared-allowance migration: on-chain exposure index, NORMAL and EMERGENCY modes of `activateSuccessor`, sibling handling
  A  Account pin precision: seven-field struct, delegate-code check, signature-mode gating, pin version, signature-capability invalidation
  V  Foundry export of the Python models; fuzz, invariant, mutation, integer-width, timestamp-boundary and shared-allowance suites
  K  Signer-set emergency removal: tombstones, set stop, bounded rotation grace
  C  Production-blocking constants as individually approved configuration records
  P  Permit2 pinned commit, deployed-bytecode comparison and pinned source review

All increases are ESTIMATES (first order, +/-40%). After apply() every epic carries pw04 (the v0.4 estimate) and why05 (cause attribution of
the v0.4 -> v0.5 change, which must sum to it); apply() exits with an error if it does not.
"""
import sys
import model

TAGS05 = {
    "S": "Shared-allowance migration: on-chain exposure index, normal and emergency modes, sibling handling",
    "A": "Account pin precision: struct, delegate-code check, signature-mode gating, pin version, signature-capability invalidation",
    "V": "Foundry export of the Python models; fuzz, invariant, mutation, integer-width, timestamp-boundary and shared-allowance suites",
    "K": "Signer-set emergency removal: tombstones, set stop, bounded rotation grace",
    "C": "Production-blocking constants as individually approved configuration records",
    "P": "Permit2 pinned commit, deployed-bytecode comparison and pinned source review",
}


def R(pw, why, **fields):
    d = dict(fields)
    d["pw"] = pw
    d["why05"] = why
    return d


REVISE05 = {
    "EPIC-P0-PROTOSPEC": R(30, {"S": 2, "A": 2, "V": 3, "K": 1, "C": 3},
        accept_add="The specification set also contains: the NORMAL and EMERGENCY modes of `activateSuccessor` with the on-chain exposure index per (customer, router, token) and the sibling rules ([12 §5.3]); the seven-field `AccountPin` with the `EXTCODEHASH` checks of the account and of the delegate, the signature-mode gate, the pin version and the invalidation of signature capability ([17]); the signer-set emergency-removal rules (immediate tombstone for a compromised signer, set stop by the guardian, retired-set grace bounded by `QUOTE_SET_GRACE`) ([11 §4.7]); the export rules that turn the Python vectors and models into Foundry suites; and each production-blocking constant PC-01…PC-18 as a configuration record (owner, unit, rationale, evidence, safe range, test, release gate, approval block) ready for approval one by one ([16 §7]).",
        impl_add=[("Shared-allowance migration specification: NORMAL and EMERGENCY modes of `activateSuccessor`, exposure index and sibling rules",
                   "The predicates are written as executable oracles and MIG-TV-30…45 are reproduced by the Python model; a reviewer outside the squad has checked every sibling case."),
                  ("Account pin specification: seven-field struct, delegate-code check, signature-mode gating, pin version and signature-capability invalidation",
                   "ACP-TV-25…44 are reproduced by the Python model; every field states the modes in which it is checked and the event that invalidates it."),
                  ("Foundry export specification: which Python vectors and models become Solidity tests, and the suite list (vectors, fuzz, invariant, mutation, integer width, timestamp boundary, shared allowance)",
                   "The export format is fixed and reviewed; every vector family has a target test contract and a regeneration rule."),
                  ("Signer-set emergency removal specification: tombstones, set stop and bounded rotation grace",
                   "CAP-TV-23…32 are reproduced by the Python model; the text states that a compromised signer has no grace period and can never be registered again."),
                  ("Production-blocking constants PC-01…PC-18 as configuration records with an approval block each",
                   "Every record has owner, unit, rationale, evidence, safe range, test, release gate and an approval block that stays empty until the named approver signs it; none is marked approved by this work.")]),
    "EPIC-P0-SOURCES": R(19, {"P": 4},
        accept_add="The Permit2 commit is pinned (SHA recorded); the deployed bytecode on each launch chain is compared with the pinned build with the immutables masked and any chain that differs is excluded, not assumed equal; the source review answers PR-01…PR-16 at E2 with a second reviewer's sign-off.",
        impl_add=[("Pinned Permit2 commit and deployed-bytecode comparison across chains with the immutables masked",
                   "The comparison reproduces on two machines; a chain whose masked bytecode differs from the pinned build is recorded as excluded with the diff attached."),
                  ("Second-reviewer pass over the pinned source review at E2",
                   "A named second reviewer has read each cited passage of PR-01…PR-16; an item they dispute is reopened and is not counted as answered.")]),
    "EPIC-P0-WALLETLAB": R(24, {"A": 4},
        accept_add="The per-mode runs also cover account-pin precision: the delegate code hash and implementation family per wallet, which signature modes each wallet supports (signature-mode gating), and what a wallet or delegate version change does to the pin and to signature capability (WL-36…40, evidence EVL-15).",
        impl_add=[("Account-pin precision runs: delegate code hash and implementation family per wallet, signature-mode gating, behavior after a wallet or delegate version change",
                   "Run records for WL-36…40; the Compatibility Register carries the pin version, the signature mode and the observed invalidation trigger for each row.")]),
    "EPIC-P0-PLANNER": R(13, {"S": 1, "A": 1},
        accept_add="The planner computes siblings (live mandates of the same customer on the same router and token), never emits a lockdown that would unfund a sibling in NORMAL mode, sizes the new router's shared allowance for the sum of the migrated lineages, and emits the seven-field account pin; MIG-TV-30…45 and ACP-TV-25…44 pass in both implementations.",
        impl_add=[("Sibling computation, NORMAL or EMERGENCY mode choice and shared-allowance sizing in the planner",
                   "MIG-TV-30…45 pass in both implementations; a NORMAL plan never revokes an allowance that a sibling still relies on."),
                  ("Seven-field account pin and signature-mode input in the planner output",
                   "ACP-TV-25…44 pass in both implementations; a plan whose signature mode is not allowed for the account mode is refused.")]),
    "EPIC-P1-CONTRACTS": R(126, {"S": 6, "A": 5, "K": 2, "V": 3},
        accept_add="`activateSuccessor` has two modes. NORMAL (router still trusted): the old Permit2 allowance may remain only while a sibling mandate of the same customer still relies on the router, and must be zero or expired for a token once no sibling uses it. EMERGENCY (router disabled, sunset, retired or security-deprecated): every token of every mandate of the customer on that router has an unusable allowance first. An on-chain exposure index counts live mandates per (customer, router, token). The `AccountPin` is the seven-field struct; `consume` checks `EXTCODEHASH` of the account and of the delegate; signature capability is bound to the pin and revoked when the delegate, the implementation, the wallet version or the code hash changes. The quote-signer registry supports an immediate tombstone (a compromised signer has no grace and is never registrable again), honors a retired signer set only for quotes issued before retirement and for at most `QUOTE_SET_GRACE`, and lets the guardian stop a whole set. The Foundry suites exported from the Python models (vectors, fuzz, invariant, mutation, integer width, timestamp boundary, shared allowance) run in CI.",
        impl_add=[("On-chain exposure index per (customer, router, token) and the NORMAL and EMERGENCY modes of `activateSuccessor`",
                   "MIG-TV-30…45 pass on a fork; the index equals the number of live mandates in every fuzzed sequence; NORMAL mode with no remaining sibling and a usable allowance reverts, with a sibling it succeeds; EMERGENCY mode reverts if any token of any mandate of the customer on that router has a usable allowance."),
                  ("Seven-field `AccountPin`: account mode, account code hash (the delegation designator hash for 7702 accounts), delegate address, delegate code hash, implementation family, pin version, signature mode",
                   "ACP-TV-25…44 pass; the pin digest vector is reproduced by the Python model; a pin update by anyone but the customer is rejected and never changes a cap."),
                  ("`consume` checks: `EXTCODEHASH` of the account and of the delegate, signature-mode gate, and revocation of signature capability when delegate, implementation, wallet version or code hash changes",
                   "A delegate swap or a wallet-version change reverts before any transfer and invalidates the signature capability bound to the old pin; the boundary cases (an account with no code, an account whose code is a delegation designator, a delegate with no code) each have a test."),
                  ("Signer-set emergency removal: tombstone (never re-registrable), guardian set stop and retired-set grace bounded by `QUOTE_SET_GRACE`",
                   "CAP-TV-23…32 pass; no quote from a tombstoned signer validates from the block after the removal; a quote issued after a set was retired never validates and one issued before validates for at most `QUOTE_SET_GRACE`."),
                  ("Foundry suites generated from the Python models: vectors, fuzz, invariant, mutation, integer width, timestamp boundary and shared allowance",
                   "All suites run in CI; the mutation run records its surviving mutants; a test at `block.timestamp` equal to an expiration passes for the Permit2 allowance and for the mandate expiry.")]),
    "EPIC-P1-MIGRATION": R(27, {"S": 4},
        accept_add="The planners compute siblings, never emit a lockdown that would unfund a sibling in NORMAL mode, size the new router's shared allowance for the sum of the migrated lineages, and in EMERGENCY mode make every token of every mandate of the customer on the old router unusable first; the orchestrator holds siblings instead of failing their charges.",
        impl_add=[("Sibling-aware migration plans: NORMAL and EMERGENCY flows, shared-allowance sizing for the sum of the migrated lineages, sibling hold",
                   "MIG-TV-30…45 pass on a fork; a plan that would unfund a sibling is never emitted in NORMAL mode; a sibling is held and produces neither a failed charge nor a dunning notice while a migration is in flight.")]),
    "EPIC-P1-DELEGATION": R(35, {"A": 5},
        accept_add="The engine builds the seven-field account pin (the account code hash is the delegation designator hash for 7702 accounts), compares the delegate code hash and implementation family, gates signature modes per account mode and pin version, and treats a change of delegate, implementation, wallet version or code hash as an invalidation of signature capability that routes the customer to re-verification; ACP-TV-25…44 pass.",
        impl_add=[("Seven-field pin builder: account code hash, delegate address and code hash, implementation family, pin version and signature mode",
                   "ACP-TV-25…44 pass; the built pin equals PIN_OK for the observed hashes and no pin is built from an unobserved delegate code hash."),
                  ("Signature-mode gating and signature-capability invalidation after a delegate, implementation, wallet-version or code-hash change",
                   "A wallet-managed upgrade after activation invalidates the capability, pauses unattended charges for that account and starts re-verification; no charge is signed on the stale pin.")]),
    "EPIC-P1-QUOTE": R(38, {"K": 3},
        accept_add="A compromised signer is removed by an immediate tombstone with no grace period; a retired signer set is honored only for quotes issued before retirement and for at most `QUOTE_SET_GRACE`; the guardian can stop a whole set; the service stops requesting signatures from a tombstoned or stopped set at its next refresh.",
        impl_add=[("Emergency removal in the quote service: tombstone and set-stop propagation, refusal to issue under a retired set after its grace",
                   "A removal drill measures the time from the removal transaction to the first refused quote against the removal-latency target of OD-034; no quote is issued under a tombstoned signer after the service has observed the removal.")]),
    "EPIC-P1-TOKENREG": R(27, {"K": 2},
        accept_add="The registry stores signer tombstones (never re-registrable), the set-stop flag and the end of the retired-set grace; every change is evented, and emergency removal and set stop take effect immediately.",
        impl_add=[("Registry: signer tombstones, guardian set stop and bounded retired-set grace",
                   "A tombstoned signer cannot be added again by any path, including a timelocked proposal; set stop and emergency removal are evented and effective in the next block.")]),
    "EPIC-P1-FORK": R(24, {"V": 6, "P": 1},
        accept_add="The Foundry suites exported from the Python models (vectors, fuzz, invariant, mutation, integer width, timestamp boundary, shared allowance) run in CI on forks of 2 chains together with the fork tests of the Permit2 freeze subset at the pinned commit; the export tool is the only source of these tests.",
        impl_add=[("Foundry export harness (`tools/export_foundry.py`): Solidity tests written from the Python vectors",
                   "The generated tests are byte-reproducible from the vectors; a changed vector without regenerated tests fails CI."),
                  ("Fuzz, invariant, integer-width and timestamp-boundary suites over the exported models",
                   "Each suite has stated bounds and seeds; a counterexample is stored as a regression vector; the timestamp-boundary suite covers `block.timestamp` equal to each expiration."),
                  ("Mutation testing, the shared-allowance suite and the fork tests of the Permit2 freeze subset",
                   "Surviving mutants are listed with a reason; the shared-allowance suite covers NORMAL and EMERGENCY modes with one to five siblings; the freeze-subset fork tests pass at the pinned commit.")]),
    "EPIC-P1-SIGNER": R(24, {"A": 1},
        accept_add="Signer policy also refuses an unattended charge whose account-policy stamp names a signature mode that the pin does not allow."),
    "EPIC-P1-AUDITPREP": R(15, {"V": 1},
        accept_add="The audit package includes the generated Foundry suites with the instructions to regenerate them from the Python vectors, the mutation report with its surviving mutants, and the integer-width and timestamp-boundary results."),
    "EPIC-P1-REVOKE": R(13, {"V": 1, "P": 1},
        accept_add="RV-T and ZP-T are exported to Foundry and run at the pinned Permit2 commit and against the deployed bytecode with the immutables masked on each launch chain; the case of a lockdown that would unfund a sibling mandate is a named test.",
        impl_add=[("Run RV-T and ZP-T at the pinned commit and against the deployed bytecode, including the lockdown-versus-sibling case",
                   "All RV-T pass and the ZP-T results are recorded; the lockdown-versus-sibling test fails when a sibling's allowance would be removed in NORMAL mode.")]),
    "EPIC-P2-MIGSVC": R(35, {"S": 3},
        accept_add="The campaign engine computes siblings per customer and router, holds sibling mandates (no failed charge and no dunning) while a migration is in flight, sequences the lockdown after the last sibling has moved in NORMAL mode, and switches to the EMERGENCY flow when the router is disabled, sunset, retired or security-deprecated.",
        impl_add=[("Sibling hold, last-sibling lockdown sequencing and the EMERGENCY switch in the campaign engine",
                   "For a customer with three mandates on one router the first two migrations leave the allowance in place and the last one revokes it; an emergency campaign makes every token unusable first; no sibling produces a failed charge or a dunning notice.")]),
    "EPIC-P2-PORTAL": R(27, {"A": 2},
        accept_add="The portal shows the full pin (mode, delegate, delegate code hash, implementation family, pin version, signature mode), says in plain words what a pin update changes and that it never changes a cap, and shows when and why signature capability was invalidated."),
    "EPIC-P3-MIGDRILL": R(17, {"S": 1},
        accept_add="The drill includes a customer with two sibling mandates on the old router (NORMAL mode: the allowance stays until the last sibling has moved) and one EMERGENCY-mode run in which the router is disabled and every token of every mandate is made unusable first."),
}


def apply():
    by_id = {e["id"]: e for e in model.EPICS}
    for e in model.EPICS:
        e["pw04"] = e["pw"]
        e["why05"] = {}
    for eid, ch in REVISE05.items():
        if eid not in by_id:
            sys.exit(f"v0.5 revision for unknown epic {eid}")
        e = by_id[eid]
        ch = dict(ch)
        why = ch.pop("why05")
        acc = ch.pop("accept_add", None)
        add = ch.pop("impl_add", None)
        for k, v in ch.items():
            e[k] = v
        if acc:
            e["accept"] = e["accept"].rstrip() + " " + acc
        if add:
            for pair in add:
                if (not isinstance(pair, tuple)) or len(pair) != 2 or not all(isinstance(x, str) and x.strip() for x in pair):
                    sys.exit(f"{eid}: impl_add entries must be (summary, acceptance) pairs of non-empty strings")
            e["impl"] = list(e["impl"]) + list(add)
        e["why05"] = why
        if sum(why.values()) != e["pw"] - e["pw04"]:
            sys.exit(f"{eid}: why05 sums to {sum(why.values())} but pw - pw04 = {e['pw'] - e['pw04']}")
        for k in why:
            if k not in TAGS05:
                sys.exit(f"{eid}: unknown v0.5 tag {k}")
