"""Backlog model for the FastPay specification (revision 0.3).

The epic records keep the v0.2 shape: implementation stories plus a (summary, acceptance) pair for security, observability, test,
migration and operational readiness, so that the frozen v0.2 data files can be reused. From revision 0.3 the **profile** of an epic
(see PROFILES below, assigned in revisions_v03.py) decides which of those pairs become stories: required types must exist, types that
do not apply are dropped, optional types are kept when the epic has content for them. build_backlog.py enforces this; `epic()` only
refuses to register a record with missing pairs.

Estimates: person-weeks for epics, person-days for stories (first-order, +/-40%). `old_pw` is the v0.1 estimate (None for post-GA
epics); `why` attributes the v0.1 -> v0.2 change and must sum to (pw - old_pw). revisions_v03.py adds `prev_pw` (the v0.2 estimate)
and `why03`, which must sum to the v0.2 -> v0.3 change.

The PHASES table below is the v0.2 plan, kept only for the comparison tables; v0.3 phase windows are derived from the schedule
model's P50 gates (build_backlog.py, phase_windows()).
"""
import sys

FOCUS = 0.70
MIN_SLACK = 0.10

# id, name, weeks label, first week, last week, average headcount, scope ("GA" = through v1.0 GA; "POST" = after GA)
PHASES = [
    ("P0", "Foundations and validation", "W1-W12", 1, 12, 18, "GA"),
    ("P1", "Build alpha (to contract audit freeze)", "W13-W38", 13, 38, 30, "GA"),
    ("P2", "Platform completion, alpha, audits, sandbox", "W39-W62", 39, 62, 46, "GA"),
    ("P3", "Private mainnet beta", "W63-W76", 63, 76, 50, "GA"),
    ("P4", "Public beta", "W77-W96", 77, 96, 50, "GA"),
    ("P5", "GA readiness (v1.0)", "W97-W108", 97, 108, 50, "GA"),
    ("P6", "v1.1: stablecoin conversion enablement, repeat and variable billing", "W109-W124", 109, 124, 50, "POST"),
    ("P7", "v2.0: general-token conversion, Router v2, new surfaces (indicative)", "W125-W152", 125, 152, 50, "POST"),
]

# v0.1 plan, kept for the comparison table
OLD_PLAN = [
    ("P0", "W1-W10", 89), ("P1", "W11-W34", 418), ("P2", "W35-W52", 404),
    ("P3", "W53-W66", 400), ("P4", "W67-W88", 666), ("P5", "W89-W102", 380),
]

TAGS = {
    "A": "Conversion boundary, adapter registry, feature-flag service (directive item 1)",
    "B": "Dual cap model: signed quotes, price bounds, quote-signer key class (directive item 4)",
    "C": "Router lifecycle and migration protocol (directive item 3)",
    "D": "EIP-7702 inspection and recording; Permit2 code-bearing account handling (directive item 2)",
    "E": "Pay Once separated onto SignatureTransfer (directive item: separate protocols)",
    "F": "Story-type completeness: security, observability, test, migration and operational-readiness work now estimated explicitly (directive item 5)",
    "G": "Scope moved to v1.1 / v2.0 by the new version boundaries (negative)",
    "H": "Other planning changes (version boundaries, document set)",
}

SQUADS = {
    "LEAD": "Leadership and Program",
    "PROD": "Product and Design",
    "PROTO": "Protocol and Contracts",
    "CORE": "Payments Core",
    "CHAIN": "Chain Infrastructure",
    "CHECK": "Checkout and Merchant Experience",
    "PLAT": "Platform, SRE and Security Engineering",
    "QA": "Quality",
    "COMP": "Compliance, Risk and Privacy",
    "DEVX": "DevEx, Support and Partnerships",
}

STORY_OWNER = {
    "SEC": "Security Engineering (reviewer outside the squad)",
    "OBS": "Platform, SRE and Security Engineering",
    "TST": "Quality (with the owning squad)",
    "OPS": "SRE / Incident Operations (named per epic)",
}

EPICS = []
REMOVED = []   # (old epic id, old pw, cause tag, note)
_ids = set()


def _pair(name, value, epic_id):
    if (not isinstance(value, tuple)) or len(value) != 2 or not all(isinstance(x, str) and x.strip() for x in value):
        sys.exit(f"{epic_id}: '{name}' must be a (summary, acceptance) pair of non-empty strings")
    return value


def epic(id_, phase, name, squad, pw, old_pw, why, deps, risk, accept, evidence, target,
         labels="", old_id=None, *, impl, sec, obs, test, mig, ops):
    if id_ in _ids:
        sys.exit(f"duplicate epic id {id_}")
    _ids.add(id_)
    if not impl or not isinstance(impl, list):
        sys.exit(f"{id_}: needs at least one implementation story")
    impl = [_pair("impl", x, id_) for x in impl]
    sec, obs, test, mig, ops = (_pair(n, v, id_) for n, v in
                                (("sec", sec), ("obs", obs), ("test", test), ("mig", mig), ("ops", ops)))
    if old_pw is not None:
        delta = pw - old_pw
        if sum(why.values()) != delta:
            sys.exit(f"{id_}: 'why' sums to {sum(why.values())} but pw - old_pw = {delta}")
        for k in why:
            if k not in TAGS:
                sys.exit(f"{id_}: unknown cause tag {k}")
    EPICS.append(dict(id=id_, phase=phase, name=name, squad=squad, pw=pw, old_pw=old_pw, why=why,
                      deps=deps, risk=risk, accept=accept, evidence=evidence, target=target,
                      labels=labels, old_id=old_id, impl=impl, sec=sec, obs=obs, test=test, mig=mig, ops=ops))


def removed(old_id, old_pw, tag, note):
    REMOVED.append((old_id, old_pw, tag, note))


# ====================================================================== revision 0.3 additions
# Epic profiles replace the universal "six story types" rule. A profile lists which story types an epic of that
# kind MUST have, which it MAY have (kept when the epic has real content), and which do not apply (dropped).
#   IMP  primary work (shown as "Research task" for research, "Compliance control" for compliance, "Program action" for program)
#   SEC security   OBS observability   TST test   MIG migration requirement   OPS operational readiness
#   EVD  evidence and sign-off (generated from the epic's evidence field)
STORY_TYPES = ["IMP", "SEC", "OBS", "TST", "MIG", "OPS", "EVD"]
PROFILES = {
    "feature":        dict(required={"IMP", "SEC", "OBS", "TST", "OPS"}, optional={"MIG"}, na={"EVD"},
                           why="User-visible or service capability: build, secure, observe, test, operate; migration only where state or APIs are touched"),
    "protocol":       dict(required={"IMP", "SEC", "OBS", "TST", "MIG", "EVD"}, optional={"OPS"}, na=set(),
                           why="Contracts, planners, specs: interface/versioning and audit evidence are mandatory; events and errors are the observability"),
    "research":       dict(required={"IMP", "EVD"}, optional={"SEC", "TST", "OPS"}, na={"OBS", "MIG"},
                           why="Questions answered with evidence; no runtime to observe or migrate"),
    "security":       dict(required={"SEC", "TST", "OBS", "OPS", "EVD"}, optional={"IMP", "MIG"}, na=set(),
                           why="Assessments, audits, tooling: review, attack tests, detection, response, evidence"),
    "data":           dict(required={"IMP", "SEC", "OBS", "TST", "MIG", "OPS"}, optional={"EVD"}, na=set(),
                           why="Stores and pipelines: privacy and access, data-quality tests, backfill and schema migration, ownership"),
    "compliance":     dict(required={"IMP", "EVD", "TST", "OPS"}, optional={"SEC", "OBS", "MIG"}, na=set(),
                           why="Controls and legal work: control design, counsel or regulator sign-off, dry-run testing, staffing and escalation"),
    "infrastructure": dict(required={"IMP", "SEC", "OBS", "TST", "OPS"}, optional={"MIG", "EVD"}, na=set(),
                           why="Platform and operations: hardening, observability, DR and chaos tests, runbooks; promotion/rollback where applicable"),
    "migration":      dict(required={"IMP", "SEC", "OBS", "TST", "MIG", "OPS"}, optional={"EVD"}, na=set(),
                           why="Moving customers or data between versions: tooling, consent integrity, funnel metrics, rehearsal, rollback, communications"),
    "program":        dict(required={"IMP", "EVD", "OPS"}, optional={"SEC", "TST"}, na={"OBS", "MIG"},
                           why="COORDINATION ONLY: staffing, procurement and contracting of vendors, gate-evidence assembly and sign-off meetings, release, rollback and communication planning, status and risk reporting. Delivery work (code, tooling, tests, audits, controls, operations, migrations) belongs to the feature, protocol, security, data, compliance, infrastructure and migration profiles and is prohibited here (checked by the generator)"),
}
# Words that mark delivery work; a program epic's implementation stories may not use them (build_backlog.py lint)
PROGRAM_BANNED = r"\b(implement\w*|build|code|coding|deploy\w*|tooling|lint|pipeline|database|script\w*|drill\w*|runbook\w*|on-call|canary|rollout|kill-switch|kyb|aml|sanction\w*|migrat\w*|monitor\w*|dashboard\w*|infrastructure|testnet|faucet|status page|playbook\w*|24x7|support (operations|tooling)|sustaining)\b"
IMP_LABEL = {"research": "Research task", "compliance": "Compliance control", "program": "Program action"}

SQUAD_HC = {"Leadership and Program": 5, "Product and Design": 7, "Protocol and Contracts": 7, "Payments Core": 8,
            "Chain Infrastructure": 3, "Checkout and Merchant Experience": 5, "Platform, SRE and Security Engineering": 5,
            "Quality": 3, "Compliance, Risk and Privacy": 4, "DevEx, Support and Partnerships": 3}
PRIORITY_SQUADS = {"Protocol and Contracts", "Chain Infrastructure", "Quality"}     # hired first (wallet lab is on the freeze path)
