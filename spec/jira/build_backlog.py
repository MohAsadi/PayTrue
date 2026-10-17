#!/usr/bin/env python3
"""Build the FastPay Jira backlog (revision 0.5).

Run:   python -I spec/jira/build_backlog.py [--check]
Reads: model.py, data_p0.py data_p1.py data_p2.py data_p3_p5.py data_post.py (frozen v0.2), revisions_v03.py, revisions_v04.py and
       revisions_v05.py (overlays), schedule_results.json (written by `python -I schedule_model.py --write`)
Writes: backlog.csv (Jira CSV import) and patches the marked blocks of spec/07-delivery-plan.md.
`--check` validates and lints without writing anything.

Rules enforced (exit code 1 on violation):
  * every epic has a profile; its story types satisfy the profile: all REQUIRED types present, no NOT-APPLICABLE type present,
    optional types only where the epic has content for them (revision 0.3 replaced the universal six-story-type rule);
  * every story and epic has non-trivial acceptance criteria (lint) and a per-type, per-profile definition of done;
  * every dependency that names an EPIC-* exists; every EPIC-* mentioned in the spec documents exists (or is a recorded old/dropped id);
  * each epic's story-days sum to pw * 5;
  * the estimate changes v0.2 -> v0.3, v0.3 -> v0.4 and v0.4 -> v0.5 are fully attributed to causes;
  * the schedule results on disk were produced from the current epics, dependencies and parameters (hash check).
"""
import csv
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SPEC = HERE.parent

import model  # noqa: E402
import data_p0, data_p1, data_p2, data_p3_p5, data_post  # noqa: E402,F401
import revisions_v03  # noqa: E402
import revisions_v04  # noqa: E402
import revisions_v05  # noqa: E402
import stories as ST  # noqa: E402
from overrides import SUMMARY as SUMMARY_OVERRIDE  # noqa: E402

revisions_v03.apply()
revisions_v04.apply()
revisions_v05.apply()
import schedule_model as sm  # noqa: E402

E = model.EPICS
BY_ID = {e["id"]: e for e in E}
VERSION_OF = {"P0": "v1.0", "P1": "v1.0", "P2": "v1.0", "P3": "v1.0", "P4": "v1.0", "P5": "v1.0", "P6": "v1.1", "P7": "v2.0"}
GA_PHASES = ["P0", "P1", "P2", "P3", "P4", "P5"]
PHASE_NAME = {p[0]: p[1] for p in model.PHASES}

TYPE_NAME, BASE_WEIGHT, FIELD = ST.TYPE_NAME, ST.BASE_WEIGHT, ST.FIELD
MIN_ACCEPT_CHARS = 60
MIN_SUMMARY_CHARS = 18
RESULTS_FILE = HERE / "schedule_results.json"


def type_label(typ, profile):
    if typ == "IMP" and profile in model.IMP_LABEL:
        return model.IMP_LABEL[profile]
    return TYPE_NAME[typ]


# ---------------------------------------------------------------- definitions of done (per type, refined per profile)
DOD = {
    "IMP": "Implemented and code-reviewed; unit and integration tests merged; demonstrated in staging; contributes to the epic acceptance criteria without weakening them.",
    "SEC": "Security review completed by a reviewer outside the owning squad; every finding rated high or above is fixed or carries a time-boxed, owner-approved exception; residual risk recorded in the Risk Register.",
    "OBS": "Metrics, redacted logs and alerts exist with documented thresholds and an owner; each alert is fired once in a staging test and reaches the right on-call; no secrets or personal data in telemetry.",
    "TST": "Automated tests run in CI and pass, including negative and failure cases; results are attached to the epic evidence; a failing test blocks release.",
    "MIG": "Migration and rollback steps are written, rehearsed in staging and shown to preserve data and customer state; rollback completes within the agreed time; compatibility with the previous version is stated.",
    "OPS": "A named owner, a runbook or checklist and escalation contacts exist; the task has been exercised once (drill, table-top or dry run) and the gaps found are closed or ticketed.",
    "EVD": "Evidence items are collected and linked in the Evidence Register with checksums or stable links; every acceptance criterion of the epic and every release-gate criterion it supports maps to an artifact; the pack is reviewed by someone outside the owning squad; the named approver's sign-off is recorded, or the gap is logged as a production blocker.",
}
DOD_BY = {
    ("IMP", "research"): "The question is answered from primary sources at evidence level E2 or higher, or recorded as unresolved with the missing test named; claims and contradictions are entered in the Source Register; a second reviewer has read the cited passages; options and a recommendation are written down for the owner of the decision.",
    ("IMP", "compliance"): "The control or legal work product is documented with owner, frequency and evidence; it is reviewed by counsel or the compliance officer; it has been executed once in a dry run; open gaps are ticketed with owners.",
    ("IMP", "program"): "The action is completed with a named owner and date; evidence is linked; dependent squads are notified; the plan or gate register reflects the result.",
    ("IMP", "protocol"): "Specification or code is reviewed against the frozen interface; the vectors or invariants that belong to it pass in CI; any deviation from the frozen documents is a recorded, approved change.",
    ("IMP", "data"): "The store or pipeline is implemented with schema, ownership and retention defined; data-quality checks run in CI; it is demonstrated end to end on staging data.",
    ("IMP", "infrastructure"): "Infrastructure is defined as code, reviewed and applied to staging through the normal pipeline; drift detection is on; the change is reproducible from a clean environment.",
    ("SEC", "research"): "Source-integrity and handling controls are reviewed (retrieval hashes, mirrored copies, no secrets in notes); a reviewer outside the squad has confirmed it.",
    ("SEC", "compliance"): "Handling of regulated or personal data in this work is reviewed by Security and Privacy; access is least-privilege; findings rated high or above are closed.",
    ("SEC", "data"): "Access control, encryption, retention and personal-data minimization are reviewed by Security and Privacy; findings rated high or above are fixed or carry a time-boxed exception.",
    ("OBS", "protocol"): "Events and custom errors cover every state change and revert reason, are documented, and are consumed by at least one monitor or indexer test; no monitor depends on an undocumented event.",
    ("OBS", "data"): "Data-quality, freshness and reconciliation metrics exist with thresholds and owners; each alert is fired once in staging and reaches the right person.",
    ("OBS", "security"): "Detections for the covered threats exist with severity, owner and a tested route to on-call; each fires once on a seeded case.",
    ("TST", "protocol"): "Test vectors, unit, fuzz and invariant suites for this scope run in CI; coverage targets in the epic are met; a failing vector or invariant blocks the freeze or release.",
    ("TST", "compliance"): "The control is exercised in a dry run on realistic cases, including false-positive and failure cases; results are reviewed by the control owner; gaps are ticketed.",
    ("TST", "data"): "Data-quality, reconciliation and replay tests run in CI on fixtures or chain data, including privacy and access tests; results are attached to the evidence.",
    ("TST", "infrastructure"): "A fault-injection, disaster-recovery or chaos test is executed in a non-production environment; recovery time and data-loss figures are recorded; rollback is rehearsed.",
    ("TST", "security"): "Attack and abuse cases from the threat model are executed against the system; each case has an expected control and an observed result; failures block release.",
    ("TST", "migration"): "The migration is rehearsed end to end, including interruption at every step and rollback, on a fork or staging; no run leaves a customer in an unrecoverable state.",
    ("MIG", "protocol"): "Interface and storage-layout changes are versioned and checked against the frozen files in CI; compatibility with the previous version is stated; no change merges without a version decision.",
    ("MIG", "data"): "Schema changes and backfills are scripted, rehearsed on a copy of realistic data, reversible, and shown to preserve counts and balances.",
    ("MIG", "migration"): "The customer-facing migration step is rehearsed end to end including interruption and rollback; communications are drafted and approved; no customer is stranded.",
    ("MIG", "security"): "Versioning and change-control for the security artifact are defined; a change after freeze needs a recorded exception.",
    ("OPS", "compliance"): "Staffing, escalation path and service level are named; a table-top or dry run has been held; counsel and regulator contacts are recorded.",
    ("OPS", "infrastructure"): "A runbook, owner, on-call route and capacity or cost limits exist; the procedure was exercised once and the gaps found are closed or ticketed.",
    ("OPS", "program"): "Owner, cadence and escalation path are written down and have operated for at least one cycle.",
}
VAGUE = re.compile(r"^(pass(es)?|live|named|done|defined|published|reviewed|complete(d)?|green|staffed|tracked|approved|specified|captured|sustainable|documented|maintained|rota|closed|none|safe|reversible|signed|held|booked|enforced|idempotent|per policy|dashboards?|policy|visible|weekly|monthly|daily|metrics|rules live)\.?$", re.I)


def dod(typ, profile):
    return DOD_BY.get((typ, profile), DOD[typ])


def final_accept(typ, profile, detail):
    base = dod(typ, profile)
    detail = detail.strip()
    if len(detail) < 12 or VAGUE.match(detail):
        return base                           # a vague one-word outcome adds nothing; the standard definition of done stands
    if typ == "IMP" and len(detail) >= 40:
        return detail + " " + base
    return f"{base} Specifically: {detail}"


# ---------------------------------------------------------------- stories
def story_items(e):
    present = ST.types_present(e)
    items = []
    if "IMP" in present:
        items += [("IMP", n, s, a) for n, (s, a) in enumerate(e["impl"], 1)]
    for typ, key in FIELD.items():
        if typ in present:
            items.append((typ, 1) + tuple(e[key]))
    if "EVD" in present:
        summ = f"Evidence pack and sign-off: {e['evidence'].strip().rstrip('.')}"
        acc = (f"Evidence assembled for {e['target']}: {e['evidence'].strip().rstrip('.')}. "
               f"Each epic acceptance criterion is mapped to an artifact and the approver's sign-off is recorded.")
        items.append(("EVD", 1, summ, acc))
    return items


def allocate_days(e, items):
    total = e["pw"] * 5
    present = {it[0] for it in items}
    norm = sum(BASE_WEIGHT[t] for t in present)
    n_imp = sum(1 for it in items if it[0] == "IMP")
    raw = [total * BASE_WEIGHT[it[0]] / norm / (n_imp if it[0] == "IMP" else 1) for it in items]
    alloc = [max(1, int(r)) for r in raw]
    diff = total - sum(alloc)
    order = sorted(range(len(items)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    k = 0
    while diff > 0:
        alloc[order[k % len(order)]] += 1
        diff -= 1
        k += 1
    while diff < 0:
        big = max((i for i in range(len(items)) if alloc[i] > 1), key=lambda i: alloc[i])
        alloc[big] -= 1
        diff += 1
    return alloc


def build_stories():
    out = []
    for e in E:
        items = story_items(e)
        days = allocate_days(e, items)
        for (typ, n, summ, acc), d in zip(items, days):
            sid = e["id"].replace("EPIC-", "STORY-", 1) + f"-{typ}{n}"
            owner = e["squad"] if typ in ("IMP", "MIG") else model.STORY_OWNER.get(typ, "Release owner for the gate (named per epic)")
            out.append(dict(id=sid, epic=e["id"], type=typ, profile=e["profile"], label=type_label(typ, e["profile"]),
                            summary=SUMMARY_OVERRIDE.get(sid, summ), accept=final_accept(typ, e["profile"], acc), detail=acc,
                            days=d, owner=owner))
    return out


# ---------------------------------------------------------------- schedule results
def load_results():
    if not RESULTS_FILE.exists():
        return None
    return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- validation
def validate(stories, results):
    errs = []
    for e in E:
        for dep in re.findall(r"EPIC-[A-Z0-9]+-[A-Z0-9]+", e["deps"]):
            if dep not in BY_ID:
                errs.append(f"{e['id']}: dependency {dep} does not exist")
        if len(e["accept"]) < MIN_ACCEPT_CHARS:
            errs.append(f"{e['id']}: epic acceptance too thin")
        if e["profile"] not in model.PROFILES:
            errs.append(f"{e['id']}: unknown profile {e['profile']}")
    seen = set()
    for s in stories:
        if s["id"] in seen:
            errs.append(f"duplicate story id {s['id']}")
        seen.add(s["id"])
        if len(s["summary"]) < MIN_SUMMARY_CHARS:
            errs.append(f"{s['id']}: summary too short: {s['summary']!r}")
        if len(s["accept"]) < MIN_ACCEPT_CHARS:
            errs.append(f"{s['id']}: acceptance too thin ({len(s['accept'])} chars): {s['accept']!r}")
    for e in E:
        mine = [s for s in stories if s["epic"] == e["id"]]
        got = sum(s["days"] for s in mine)
        if got != e["pw"] * 5:
            errs.append(f"{e['id']}: story days {got} != {e['pw'] * 5}")
        prof = model.PROFILES[e["profile"]]
        types = {s["type"] for s in mine}
        missing = prof["required"] - types
        if missing:
            errs.append(f"{e['id']} ({e['profile']}): missing required story types {sorted(missing)}")
        forbidden = types & prof["na"]
        if forbidden:
            errs.append(f"{e['id']} ({e['profile']}): story types not applicable to the profile: {sorted(forbidden)}")
        extra = types - prof["required"] - prof["optional"] - {"IMP"}
        if extra:
            errs.append(f"{e['id']} ({e['profile']}): unexpected story types {sorted(extra)}")
    allowed_old = {e["old_id"] for e in E if e["old_id"]} | {d[0] for d in model.DROPPED}
    for md in sorted(SPEC.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        text = re.sub(r"<!-- BEGIN:(\w+) -->.*?<!-- END:\1 -->", "", text, flags=re.S)
        for ref in set(re.findall(r"EPIC-P[0-9]-[A-Z0-9]+", text)):
            if ref not in BY_ID and ref not in allowed_old:
                errs.append(f"{md.name}: refers to unknown epic {ref}")
    # estimate change fully attributed
    total_new = sum(e["pw03"] for e in E if e["phase"] in GA_PHASES)
    total_old = sum(e["prev_pw"] for e in E if e["phase"] in GA_PHASES) + sum(d[1] for d in model.DROPPED)
    tags = {k: 0 for k in revisions_v03.TAGS03}
    for e in E:
        if e["phase"] in GA_PHASES:
            for k, v in e["why03"].items():
                tags[k] += v
    for _, pw, tag, _ in model.DROPPED:
        tags[tag] -= pw
    if sum(tags.values()) != total_new - total_old:
        errs.append(f"v0.3 attribution {sum(tags.values())} != change {total_new - total_old}")
    ga04 = sum(sum(e["why04"].values()) for e in E if e["phase"] in GA_PHASES)
    if ga04 != sum(e["pw04"] - e["pw03"] for e in E if e["phase"] in GA_PHASES):
        errs.append("v0.4 attribution does not match the change in GA-scope estimates")
    for e in E:
        if sum(e["why05"].values()) != e["pw"] - e["pw04"]:
            errs.append(f"{e['id']}: v0.5 attribution {sum(e['why05'].values())} != change {e['pw'] - e['pw04']}")
        for k in e["why05"]:
            if k not in revisions_v05.TAGS05:
                errs.append(f"{e['id']}: unknown v0.5 cause tag {k}")
    ga05 = sum(sum(e["why05"].values()) for e in E if e["phase"] in GA_PHASES)
    if ga05 != sum(e["pw"] - e["pw04"] for e in E if e["phase"] in GA_PHASES):
        errs.append("v0.5 attribution does not match the change in GA-scope estimates")
    # the tier-1 scope table must name gating epics with fractions in (0, 1]
    for eid, frac in sm.TRI_SCOPE.items():
        if eid not in BY_ID or not (0 < frac <= 1):
            errs.append(f"TRI_SCOPE: {eid} unknown or fraction {frac} outside (0, 1]")
    # PROGRAM is coordination only: no delivery vocabulary in its implementation stories, and only the allowed epics
    banned = re.compile(model.PROGRAM_BANNED, re.I)
    for e in E:
        if e["profile"] != "program":
            continue
        if e["id"] not in revisions_v04.PROGRAM_KEEP:
            errs.append(f"{e['id']}: profile program is reserved for coordination epics {sorted(revisions_v04.PROGRAM_KEEP)}")
        for s, a in e["impl"]:
            m = banned.search(s + " " + a)
            if m:
                errs.append(f"{e['id']}: program epic contains delivery vocabulary {m.group(0)!r} in an implementation story: {s!r}")
    if not (HERE / "dependencies.csv").exists():
        errs.append("dependencies.csv missing: run `python -I spec/jira/schedule_model.py --write`")
    # schedule results freshness
    if results is None:
        errs.append("schedule_results.json missing: run `python -I spec/jira/schedule_model.py --write`")
    elif results["hash"] != sm.input_hash():
        errs.append("schedule_results.json is stale (epics, dependencies or parameters changed): re-run `python -I spec/jira/schedule_model.py --write`")
    return errs


# ---------------------------------------------------------------- schedule-derived phase windows and capacity
def phase_windows(results):
    """Phase boundaries from the P50 of the gates in the recommended scenario (rule stated in document 07)."""
    ms = results["tiers"]["GA"]["scenarios"][results["recommended"]]["ms"]
    p50 = {k: v[0] for k, v in ms.items()}
    g = lambda node: p50[node]
    ends = {"P0": g("G_RG001"), "P1": g("G_RG002"), "P2": g("G_BETA"), "P3": g("G_PUBBETA")}
    ga = g("G_GA")
    ends["P5"] = ga
    ends["P4"] = max(ends["P3"] + 1, ga - 12)
    rec = results["scenarios"][results["recommended"]]
    _PRIO["p"] = set(rec.get("priority", []))

    def fit(pid, start, gate_end, min_len):
        """Post-GA phases: at least as long as in v0.2, long enough for the gate, and long enough that demand stays within 90% of capacity."""
        n = max(min_len, gate_end - start + 1)
        while phase_demand(pid) > 0.9 * avg_headcount(start, start + n - 1, rec["hc"]) * n * model.FOCUS:
            n += 1
        return start + n - 1
    ends["P6"] = fit("P6", ga + 1, g("G_RG013"), 16)
    ends["P7"] = fit("P7", ends["P6"] + 1, g("G_RG014"), 28)
    out, start = {}, 1
    for pid in ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]:
        end = max(ends[pid], start)
        out[pid] = (start, end)
        start = end + 1
    return out


def avg_headcount(w0, w1, hc):
    """Average headcount of the organization over weeks w0..w1 (median hiring ramp)."""
    T = sm.T_RAMP[1]
    tot = 0.0
    for sq, n in hc.items():
        r0 = sm.R0_PRIORITY if sq in results_priority() else sm.R0_GENERAL
        tot += n * (sm._g(w1, r0, T) - sm._g(w0 - 1, r0, T)) / (w1 - w0 + 1)
    return tot


_PRIO = {}


def results_priority():
    return _PRIO["p"]


def phase_demand(pid):
    return sum(e["pw"] for e in E if e["phase"] == pid)


def ga_ms(results, scen, node):
    """P50 / P75 / P90 of a node in the GA-tier results for a scenario."""
    return results["tiers"]["GA"]["scenarios"][scen]["ms"][node]


def md_capacity(results):
    rec = results["scenarios"][results["recommended"]]
    _PRIO["p"] = set(rec.get("priority", []))
    hc = rec["hc"]
    win = phase_windows(results)
    rows = ["| Phase | Weeks (recommended P50) | Avg headcount | Capacity (pw) | Demand (pw) | Utilization in the window | Cumulative utilization | Check |",
            "|---|---|---|---|---|---|---|---|"]
    ok = True
    tc = td = 0
    cum_c = cum_d = 0
    for pid in ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]:
        w0, w1 = win[pid]
        avg = avg_headcount(w0, w1, hc)
        cap = avg * (w1 - w0 + 1) * model.FOCUS
        dem = phase_demand(pid)
        util = dem / cap if cap else 0
        cum_c += cap
        cum_d += dem
        cum = cum_d / cum_c
        flag = "OK" if cum <= 1 - model.MIN_SLACK else "OVERLOADED"
        if pid in GA_PHASES:
            ok &= cum <= 1 - model.MIN_SLACK
            tc += cap
            td += dem
        rows.append(f"| {pid} {PHASE_NAME[pid]} | W{w0}-W{w1} ({w1 - w0 + 1}) | {avg:.0f} | {cap:.0f} | {dem} | {util * 100:.0f}% | {cum * 100:.0f}% | {flag} |")
        if pid == "P5":
            rows.append(f"| **v1.0 GA total (P0-P5)** | W1-W{w1} | | **{tc:.0f}** | **{td}** | **{td / tc * 100:.0f}%** | | |")
    agg, pw = results["aggregate"]["ga"], results["aggregate"]["pw"]
    text = "\n".join(rows)
    text += (f"\n\nUtilization is demand over the capacity of the whole organization. The phase windows are cut at the P50 dates of the gates, but epics start from their own dependencies, so work of a later phase "
             f"is often done inside an earlier window; the **cumulative** column removes that boundary effect and is the one the check uses (above {int((1 - model.MIN_SLACK) * 100)}% the plan would need more capacity than exists). "
             f"Low utilization shows where work is bound by one squad or by an external wait. Aggregate-capacity-only view: {pw} pw of GA-scope work over a 50-person organization on the same hiring ramp "
             f"finishes at about W{agg:.0f}; the exploratory critical-path view in section 3 gives W{ga_ms(results, 'as_organized', 'G_GA')[0]} (P50, as organized) and "
             f"W{ga_ms(results, results['recommended'], 'G_GA')[0]} (P50, recommended).")
    return text, ok


V04_PUBLISHED = "P50 W167 / P75 W183 / P90 W198 (recommended squads); P50 W198 as organized (one network ending at GA)"


def tier_rec(results, tier, node):
    """P50 / P75 / P90 of a node for the recommended squads in a tier."""
    return results["tiers"][tier]["scenarios"][results["recommended"]]["ms"][node]


def wk(v):
    return f"W{v[0]} / W{v[1]} / W{v[2]}"


def md_delta(results):
    ga03 = sum(e["pw03"] for e in E if e["phase"] in GA_PHASES)
    ga04 = sum(e["pw04"] for e in E if e["phase"] in GA_PHASES)
    ga05 = sum(phase_demand(p) for p in GA_PHASES)
    ga_old = sum(e["prev_pw"] for e in E if e["phase"] in GA_PHASES) + sum(d[1] for d in model.DROPPED)
    post03 = sum(e["pw03"] for e in E if e["phase"] in ("P6", "P7"))
    post04 = sum(e["pw04"] for e in E if e["phase"] in ("P6", "P7"))
    post05 = sum(phase_demand(p) for p in ("P6", "P7"))
    post_old = sum(e["prev_pw"] for e in E if e["phase"] in ("P6", "P7"))
    tags03 = {k: 0 for k in revisions_v03.TAGS03}
    for e in E:
        if e["phase"] in GA_PHASES:
            for k, v in e["why03"].items():
                tags03[k] += v
    for _, pw, tag, _ in model.DROPPED:
        tags03[tag] -= pw
    assert sum(tags03.values()) == ga03 - ga_old, (sum(tags03.values()), ga03, ga_old)
    tags04 = {k: 0 for k in revisions_v04.TAGS04}
    for e in E:
        if e["phase"] in GA_PHASES:
            for k, v in e["why04"].items():
                tags04[k] += v
    assert sum(tags04.values()) == ga04 - ga03, (sum(tags04.values()), ga04, ga03)
    tags05 = {k: 0 for k in revisions_v05.TAGS05}
    for e in E:
        if e["phase"] in GA_PHASES:
            for k, v in e["why05"].items():
                tags05[k] += v
    assert sum(tags05.values()) == ga05 - ga04, (sum(tags05.values()), ga05, ga04)
    lines = ["| Plan | v1.0 GA demand (pw) | Schedule (weeks from the start of Phase 0) | Basis |", "|---|---|---|---|",
             f"| v0.1 | {sum(x[2] for x in model.OLD_PLAN)} | GA {model.OLD_PLAN[-1][1].split('-')[1]} | Aggregate capacity |",
             f"| v0.2 | {ga_old} | GA W{[p for p in model.PHASES if p[0] == 'P5'][0][4]} | Aggregate capacity (per-phase headcount) |",
             f"| v0.3 | {ga03} | GA P50 W173 (recommended squads) in the v0.3 model | Critical path with a uniform 50% overlap rule (superseded) |",
             f"| v0.4 | {ga04} | GA {V04_PUBLISHED} | Critical path at work-package level with FS/SS/FF dependencies and lags; one network (superseded by the three tiers) |",
             f"| **v0.5 (this revision)** | **{ga05}** | **EXPLORATORY, recommended squads, P50 / P75 / P90:** testnet reference exit (TRI-4) {wk(tier_rec(results, 'TRI', 'G_TRI4'))}; "
             f"private beta go (PMB-12) {wk(tier_rec(results, 'PMB', 'G_BETA'))}; GA go (GA-14) {wk(tier_rec(results, 'GA', 'G_GA'))} | Three scoped networks (§3.1); the v0.5 estimates below; three new pre-freeze waits |",
             f"| Change in demand, v0.4 → v0.5 | {ga05 - ga04:+d} ({(ga05 - ga04) / ga04 * 100:+.1f}%) | | |",
             "", "v0.4 → v0.5, by cause (ESTIMATES, first order, ±40%; the cause letters are defined for this revision only):", "",
             "| Cause | Meaning | Change in v1.0 GA demand (pw) |", "|---|---|---|"]
    for k, v in revisions_v05.TAGS05.items():
        lines.append(f"| {k} | {v} | {tags05[k]:+d} |")
    lines.append(f"| | **Total** | **{sum(tags05.values()):+d}** |")
    lines += ["", "v0.4 → v0.5, by epic (every epic whose estimate changed):", "", "| Epic | v0.4 → v0.5 (pw) | Causes |", "|---|---|---|"]
    changed = [e for e in E if e["pw"] != e["pw04"]]
    for e in sorted(changed, key=lambda x: (-abs(x["pw"] - x["pw04"]), x["id"])):
        why = ", ".join(f"{k} {v:+d}" for k, v in e["why05"].items())
        lines.append(f"| {e['id']} | {e['pw04']} → {e['pw']} ({e['pw'] - e['pw04']:+d}) | {why} |")
    lines.append("")
    lines.append(f"Post-GA scope (v1.1 and v2.0): {post_old} pw in v0.2 → {post03} pw in v0.3 → {post04} pw in v0.4 → {post05} pw in v0.5 (no v0.5 change).")
    lines.append("")
    lines.append("Earlier revisions, compactly. v0.3 → v0.4, by cause:")
    lines.append("")
    lines.append("| Cause | Meaning | Change in v1.0 GA demand (pw) |")
    lines.append("|---|---|---|")
    for k, v in revisions_v04.TAGS04.items():
        lines.append(f"| {k} | {v} | {tags04[k]:+d} |")
    lines.append(f"| | **Total** | **{sum(tags04.values()):+d}** |")
    lines.append("")
    top04 = sorted([e for e in E if e["pw04"] != e["pw03"]], key=lambda x: (-abs(x["pw04"] - x["pw03"]), x["id"]))[:8]
    lines.append("Largest changes in v0.4: " + "; ".join(f"{e['id']} {e['pw03']} → {e['pw04']} ({e['pw04'] - e['pw03']:+d})" for e in top04) + ".")
    lines.append("")
    lines.append("v0.2 → v0.3, by cause: " + "; ".join(f"{k} {tags03[k]:+d}" for k in revisions_v03.TAGS03) + f"; total {sum(tags03.values()):+d} "
                 "(S swap and conversion code absent from Router v1; L lineage, successor activation and primary revocation flows; D delegation revalidation; Q quote schema and cap classes; P epic profiles; M other).")
    lines.append("")
    lines.append(f"Profile changes in v0.4 (the `program` profile is restricted to coordination; no estimate changed): {sum(1 for e in E if e['profile'] != e['profile03'])} epics moved out of `program` ("
                 + "; ".join(f"{e['id']} to {e['profile']}" for e in E if e["profile"] != e["profile03"]) + ").")
    lines.append("")
    lines.append("Removed in v0.3: " + "; ".join(f"{oid} ({pw} pw, cause {tag})" for oid, pw, tag, _ in model.DROPPED) + ". Added in v0.3: "
                 + "; ".join(f"{e['id']} ({e['pw03']} pw)" for e in E if e["prev_pw"] == 0) + ".")
    return "\n".join(lines)


def est_chain(e):
    vals = []
    for v in ([e["prev_pw"]] if e["prev_pw"] else []) + [e["pw03"], e["pw04"], e["pw"]]:
        if not vals or vals[-1] != v:
            vals.append(v)
    return vals


def est_text(e):
    """Estimate history for the Jira export (ASCII)."""
    vals = est_chain(e)
    if e["prev_pw"] == 0:
        return f"new in 0.3 ({' -> '.join(str(v) for v in vals)})"
    return " -> ".join(str(v) for v in vals)


def est_md(e):
    vals = est_chain(e)
    txt = " → ".join(str(v) for v in vals)
    return f"{txt} (new in 0.3)" if e["prev_pw"] == 0 else txt


def md_epics(stories, results):
    count = {}
    for s in stories:
        count[s["epic"]] = count.get(s["epic"], 0) + 1
    win = phase_windows(results)
    out = []
    for pid in ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]:
        w0, w1 = win[pid]
        out.append(f"#### {pid} — {PHASE_NAME[pid]} (W{w0}-W{w1}, recommended P50) — {VERSION_OF[pid]}\n")
        out.append("| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for e in [x for x in E if x["phase"] == pid]:
            acc = e["accept"].replace("|", "/")
            out.append(f"| {e['id']} | {e['name']} | {e['profile']} | {e['squad']} | {est_md(e)} | {e['deps']} | {e['risk']} | {acc} | {e['target']} | {count[e['id']]} |")
        out.append("")
    return "\n".join(out)


def md_profiles(stories):
    n_epics = {p: sum(1 for e in E if e["profile"] == p) for p in model.PROFILES}
    n_story = {p: sum(1 for s in stories if s["profile"] == p) for p in model.PROFILES}
    names = lambda ts: ", ".join(t for t in model.STORY_TYPES if t in ts) or "—"
    lines = ["| Profile | Required story types | Optional (kept when the epic has content) | Not applicable | Why | Epics | Stories |",
             "|---|---|---|---|---|---|---|"]
    for p, d in model.PROFILES.items():
        lines.append(f"| {p} | {names(d['required'])} | {names(d['optional'])} | {names(d['na'])} | {d['why']} | {n_epics[p]} | {n_story[p]} |")
    lines.append("")
    lines.append("Story-type codes: IMP implementation (shown as *Research task*, *Compliance control* or *Program action* for those profiles), SEC security, OBS observability, TST test, MIG migration requirement, OPS operational readiness, EVD evidence and sign-off.")
    lines.append("")
    lines.append("**The `program` profile is coordination only.** Allowed: " + "; ".join(f"{k.replace('EPIC-', '')} ({v})" for k, v in revisions_v04.PROGRAM_KEEP.items())
                 + ". Prohibited: any delivery work that belongs to the feature, protocol, security, data, compliance, infrastructure or migration profiles. "
                 "The generator fails if a program epic is not in the allowed list or if its implementation stories use delivery vocabulary (code, tooling, deploy, drill, runbook, rollout, KYB, AML, migration execution, monitoring, support operations and similar). "
                 f"Epics moved out of `program` in v0.4: {sum(1 for e in E if e['profile'] != e['profile03'])}.")
    na_loss = sum(1 for e in E if e["profile"] in ("research", "program"))
    evd = sum(1 for s in stories if s["type"] == "EVD")
    lines.append("")
    lines.append(f"Effects of the profile rule: research and program epics ({na_loss}) carry no observability or migration stories; {evd} evidence-and-sign-off stories exist. "
                 "In the current data every optional type has real content, so all optional stories are kept.")
    return "\n".join(lines)


def md_storystats(stories):
    types = model.STORY_TYPES
    cnt = {(p, t): 0 for p in model.PROFILES for t in types}
    days = {t: 0 for t in types}
    by_type = {t: 0 for t in types}
    for s in stories:
        cnt[(s["profile"], s["type"])] += 1
        days[s["type"]] += s["days"]
        by_type[s["type"]] += 1
    lines = ["| Story type | Stories | Person-days |", "|---|---|---|"]
    for t in types:
        lines.append(f"| {TYPE_NAME[t]} | {by_type[t]} | {days[t]} |")
    lines.append(f"| **Total** | **{len(stories)}** | **{sum(days.values())}** |")
    lines.append("")
    lines.append("Stories by profile and type:")
    lines.append("")
    lines.append("| Profile | Epics | " + " | ".join(types) + " |")
    lines.append("|---|---|" + "---|" * len(types))
    for p in model.PROFILES:
        n = sum(1 for e in E if e["profile"] == p)
        lines.append(f"| {p} | {n} | " + " | ".join(str(cnt[(p, t)]) if cnt[(p, t)] else "—" for t in types) + " |")
    lines.append("")
    lines.append(f"Coverage check (enforced by the generator): all **{len(E)}** epics satisfy their profile (required story types present, none that do not apply) and carry acceptance criteria; each epic's story-days sum to its estimate.")
    lines.append("")
    lines.append("**Status of the backlog: a planning baseline, not implementation-complete.** Every epic is decomposed to story level so that the work its profile requires is visible, but stories in later phases are coarse. They are split, re-estimated and re-sequenced at each phase planning gate; acceptance thresholds marked PROPOSAL are open to change; estimates are first-order (±40%).")
    return "\n".join(lines)



LEAD_DESC = {
    "L_LEGAL_MEMO": "Counsel perimeter memo (RP-09)", "L_OD001": "Decision on OD-001 after the memo",
    "L_LICENSE": "Licensing: licensed-partner route or own licence (mixture)", "L_GOLIVE": "Go-live review and filings after the licence route is in place",
    "L_AUDIT_AVAIL": "Wait for audit slots after the contract audit freeze", "L_AUDIT_RUN": "Two audits in parallel: the later of two draws",
    "L_REREVIEW": "Re-review by the finding firm after remediation", "L_PENTEST": "Penetration test and red team after feature complete",
    "L_PENTEST_RETEST": "Retest after fixes", "L_WALLET_FIX": "Wallet-lab fixes and retest after the E3 runs",
    "L_CHAIN_EVID": "Chain evidence: finality observation and chaos tests", "L_RECON_TESTNET": "Testnet reconciliation observation (14 consecutive days plus slack)",
    "L_BETA_STABILITY": "Private-beta stability (four consecutive weeks of matched reconciliation, no Sev-1)",
    "L_BOUNTYPUB": "Public bug bounty and contest or extended review", "L_SLO8": "Sustained SLOs after the public beta decision",
    "L_V11_AUDIT_AVAIL": "v1.1: wait for audit slots", "L_V11_AUDIT_RUN": "v1.1: Router v1.1 audit run", "L_V11_REREVIEW": "v1.1: re-review",
    "L_ADAPTER_AUDIT": "v1.1: adapter audit", "L_V20_AUDIT": "v2.0: audit of the general route class and oracle verifier",
    "L_V20_NOTICE": "v2.0: minimum notice before a router sunset",
    "L_COUNSEL_NOTICE": "Counsel view on router-migration notice duties (RP-26); freeze-blocking for PC-01 and PC-02 (UX-16)",
    "L_PERMIT2_E2": "Second-reviewer sign-off at E2 of the pinned Permit2 source review (PR-01 to PR-16)",
    "L_PC_APPROVAL": "Approval rounds for the individually approved production-blocking constants (PC-01 to PC-18)",
}
# Why each new pre-freeze wait has the range it has (all ASSUMPTIONS)
WAIT_WHY = {
    "L_COUNSEL_NOTICE": "Counsel is engaged in week 1 and a written view on notice duties across the launch jurisdictions is a multi-week task; it blocks only the two notice constants, but those are freeze-blocking",
    "L_PERMIT2_E2": "A second reviewer reads the pinned source after the first review is built; one to four weeks of availability and rework, no external vendor assumed",
    "L_PC_APPROVAL": "Each constant is approved by its named owner after the specification and the lab subset exist; rounds of questions and a second round for contested values",
}


def graph_text(tier):
    N = sm.net(tier)
    bt, _ = sm.edge_stats(tier)
    return (f"{len(N['nodes'])} nodes ({sum(1 for v in N['nodes'].values() if v['kind'] == 'wp')} work packages), {len(N['edges'])} typed dependencies "
            f"({bt.get('FS', 0)} FS, {bt.get('SS', 0)} SS, {bt.get('FF', 0)} FF)")


def md_model():
    P = [("Hiring ramp, final strength reached in (weeks, triangular low / mode / high)", sm.T_RAMP),
         ("Start-up strength: share of final squad strength at week 0 (general / squads hired first)", (sm.R0_GENERAL, sm.R0_PRIORITY)),
         ("Squads hired first (recommended scenario adds Payments Core)", sorted(model.PRIORITY_SQUADS)),
         ("Focus factor (meetings, support, review)", model.FOCUS),
         ("Run-wide effort factor (low / mode / high)", sm.G_FACTOR), ("Per work package and squad effort factor (low / mode / high)", sm.N_FACTOR),
         ("Runs per scenario", results_n()),
         ] + [(f"Graph, {sm.TIERS[t]['name'].split(':')[0].lower()} ({t})", graph_text(t)) for t in sm.TIER_ORDER]
    lines = ["**Status of every number in this section: EXPLORATORY.** The model is a tool for seeing which constraints bind, not a forecast.", "",
             "| Parameter | Value |", "|---|---|"]
    for k, v in P:
        lines.append(f"| {k} | {v if not isinstance(v, (list, tuple)) else ' / '.join(str(x) for x in v)} |")
    lines.append("")
    lines.append("**Scoped networks (revision 0.5).** The model runs three networks. Tier 3 (GA) is the full network. Tier 2 (PMB) is the full network pruned to the ancestors of G_BETA (any dependency type), so work after the private-beta decision no longer competes for squads in that simulation. "
                 "Tier 1 (TRI) is a separate network: the epics of `TRI_SCOPE` with their person-weeks scaled by the stated fraction, the wallet lab through its two special nodes, the tier-1 gates G_TRI2 to G_TRI4 and G_FREEZE; "
                 "a dependency on a gate or epic outside the tier is dropped, except that a wait for the audit freeze or the testnet-alpha gate becomes a wait for G_TRI2 (`TRI_MAP`). "
                 "The simulation core is the same for all three and is deterministic for a fixed seed; the same seed and run count are used for every tier. "
                 "The squad sizes of the 'recommended' scenario were found for tier 3 under the v0.4 estimates and were not searched again, so they are not tuned for tiers 1 and 2.")
    lines.append("")
    lines.append("**Work packages.** Every gating epic is split by its story types into up to three packages: **B** build (implementation, research task, compliance control, program action), "
                 "**A** assurance (security, test, observability) and **R** readiness (migration requirement, operational readiness, evidence and sign-off), sized by the story-type weights. "
                 "Squads do the packages of the epics they own (shares for epics that span squads are in `SPLIT`).")
    lines.append("")
    lines.append("**Dependency types and lags.** Each dependency is explicit; none is a global rule. FS: the successor starts after the predecessor finishes (+ lag). SS: the successor starts after the predecessor starts (+ lag). "
                 "FF: the successor finishes after the predecessor finishes (+ lag). A lag is in weeks, computed once as a fraction of the predecessor's nominal duration. The rules (every edge, with its rule, is in [jira/dependencies.csv](jira/dependencies.csv)):")
    lines.append("")
    lines.append("| Edge | Type | Lag | Rule |")
    lines.append("|---|---|---|---|")
    lines.append(f"| build → assurance, same epic | SS and FF | SS {sm.INTRA_B_TO_A[1]:.0%} of the build's nominal duration; FF {sm.INTRA_B_TO_A_FF:g} week | Tests and reviews start while the build is under way and finish after it |")
    lines.append(f"| build → readiness, same epic | SS | {sm.INTRA_B_TO_R[1]:.0%} of the build's nominal duration | Readiness work starts late in the build |")
    lines.append("| assurance → readiness, same epic | FF | 0 | Readiness cannot finish before the assurance finishes |")
    lines.append(f"| predecessor epic of profile research, program or compliance → successor build | FS | 0 | A decision, finding or evidence is needed whole |")
    lines.append(f"| any other predecessor epic → successor build | SS | {sm.CROSS_BUILD[1]:.0%} of the predecessor build's nominal duration | The successor consumes an interface once half of it exists |")
    lines.append("| predecessor assurance → successor assurance | FF | 0 | A successor's tests cannot finish before the predecessor's |")
    lines.append("| epic → gate or wait | FS | 0 | A gate needs the work; design gates (freeze, audit freeze, Phase 1 exit, feature complete) need build and assurance packages, release gates need all three |")
    lines.append("| gate or wait → epic | FS | 0 | An epic does not start before the gate it depends on |")
    lines.append("")
    lines.append("Explicit overrides: " + "; ".join(f"{a.replace('EPIC-', '')} → {b.replace('EPIC-', '')} {typ}" + (f" +{frac:.0%}" if frac else "")
                                                   for (a, b), (typ, frac) in sm.EDGE_OVERRIDE.items()) + ".")
    lines.append("")
    lines.append("External waits and reviews (weeks, triangular low / mode / high; random per run):")
    lines.append("")
    lines.append("| Wait | Meaning | Low / mode / high |")
    lines.append("|---|---|---|")
    for nid, (kind, deps, spec) in sm.SPECIAL.items():
        if kind == "lead":
            reps = f" (max of {spec[3]} draws)" if len(spec) > 3 else ""
            lines.append(f"| {nid} | {LEAD_DESC.get(nid, nid)} | {spec[0]} / {spec[1]} / {spec[2]}{reps} |")
        elif kind == "mix":
            p, a, b = spec
            lines.append(f"| {nid} | {LEAD_DESC.get(nid, nid)} | {int(p * 100)}%: {a[0]} / {a[1]} / {a[2]}; otherwise {b[0]} / {b[1]} / {b[2]} |")
    lines.append("")
    gates = [(nid, spec) for nid, (kind, deps, spec) in sm.SPECIAL.items() if kind == "gate"]
    lines.append("Gate reviews add a short random time after their last prerequisite: " + ", ".join(f"{n} {s[0]}/{s[1]}/{s[2]}" for n, s in gates[:6]) + ", and similar for the others (see `SPECIAL` in the model).")
    lines.append("")
    lines.append("**What the model does:** schedules the work packages with the typed dependencies above; gives each squad a capacity curve and a queue (one package at a time, longest remaining path first); adds the waits; "
                 "reports when each gate is first reached, over many random draws. **What it does not:** model non-gating work (" + sm.NON_GATING_NOTE + "), assumed to use capacity that gating work leaves free; "
                 "model people moving between squads or part-time sharing; model hiring beyond the ramp; know the real audit calendar or counsel's timeline; account for scope cuts. "
                 "A queue discipline that favours the longest path can delay small readiness packages of an early phase, which gives some gates a heavy upper tail (Phase 0 exit in every scenario without extra contractors); with the v0.5 estimates this effect also lies on the chain to the private beta and to GA in a large share of runs (the criticality tables and the queue-rule sensitivity of section 3.5 show how large), so the tier-2 and tier-3 dates contain queueing that a staffing rule would remove. "
                 "Every one of these is a reason the dates depend on the inputs. The two scenarios that matter most for a decision are the squad shape (OD-031) and the contractor option.")
    return "\n".join(lines)


def results_n():
    r = load_results()
    return f"{r['n_runs']:,}" if r else "n/a"


SCEN_COLS = [("as_organized", "As organized"), ("recommended", "Recommended squads"), ("recommended_contractors", "Recommended + 7 contractors")]
TIER_TITLE = {"TRI": "Tier 1 — testnet reference implementation (TRI)", "PMB": "Tier 2 — private mainnet beta (PMB)", "GA": "Tier 3 — full GA platform (GA)"}


GROUP_WORD = {"R": "readiness", "A": "assurance", "B": "build"}


def top_id(results, tier):
    t = results["tiers"][tier]
    return next(m["id"] for m in t["milestones"] if m["node"] == t["top"])


def md_tiers(results):
    T = results["tiers"]
    ga_work = T["GA"]["graph"]["work_pw"]
    lines = ["| Tier | Top gate | Nodes | Work packages | Typed dependencies (FS / SS / FF) | Work in the network (pw) | Share of the GA network | Scenarios simulated |",
             "|---|---|---|---|---|---|---|---|"]
    for t in sm.TIER_ORDER:
        g = T[t]["graph"]
        bt = g["by_type"]
        lines.append(f"| {TIER_TITLE[t]} | {top_id(results, t)} ({T[t]['top']}) | {g['nodes']} | {g['wps']} | {g['edges']} ({bt.get('FS', 0)} / {bt.get('SS', 0)} / {bt.get('FF', 0)}) | "
                     f"{g['work_pw']:.0f} | {g['work_pw'] / ga_work * 100:.0f}% | {len(T[t]['scenarios'])} |")
    lines.append("")
    ga_nodes, pmb_nodes = sm.net("GA")["nodes"], sm.net("PMB")["nodes"]
    epics_ga = {v["epic"] for v in ga_nodes.values() if v["epic"]}
    epics_pmb = {v["epic"] for v in pmb_nodes.values() if v["epic"]}
    wholly_out = sorted(epics_ga - epics_pmb)
    partly = {}
    for n, v in ga_nodes.items():
        if v["epic"] in epics_pmb and n not in pmb_nodes:
            partly.setdefault(v["epic"], []).append(v["grp"])
    short = lambda x: x.replace("EPIC-", "")
    by_missing = {}
    for e, g in partly.items():
        by_missing.setdefault("".join(sorted(g)), []).append(short(e))
    out_pw =sum(sum(sum((ga_nodes[n]["work"] or {}).values()) for n in ga_nodes if ga_nodes[n]["epic"] == e) for e in wholly_out)
    lines.append(f"Tier 2 is the GA network pruned to the ancestors of G_BETA. Gating epics with no work package in it ({len(wholly_out)} epics, {out_pw:.0f} pw): "
                 + ", ".join(short(x) for x in wholly_out) + ". "
                 + (f"Epics with only some packages in it ({len(partly)}): " + "; ".join(
                     f"the {k} package ({GROUP_WORD.get(k, k)}) is not simulated for " + ", ".join(sorted(v)) for k, v in sorted(by_missing.items()))
                    + ". A package that no gate on the way to RG-010 waits for (typically readiness paperwork) is therefore not simulated in tier 2, "
                      "although it competes for squads in the GA network. " if partly else ""))
    lines.append("")
    lines.append("Tier 1 is a separate network of the epics in `TRI_SCOPE` with scaled work (§3.4); epics not listed there are not in it. "
                 f"Epics not scheduled in any tier (non-gating): {sm.NON_GATING_NOTE}.")
    return "\n".join(lines)


def pretty_dep(d):
    base, _, grp = d.partition(":")
    if grp:
        return f"{base.replace('EPIC-', '')} ({ {'B': 'build', 'BA': 'build, assurance'}.get(grp, grp) })"
    return f"{base.replace('EPIC-', '')} (all packages)" if base.startswith("EPIC-") else base


def md_triscope(results):
    by_id = {e["id"]: e for e in E}
    lab = by_id["EPIC-P0-WALLETLAB"]
    lines = ["| Epic | Name | Owner squad | v0.5 estimate (pw) | Fraction in tier 1 (**ASSUMPTION**) | Tier 1 work (pw) |", "|---|---|---|---|---|---|"]
    tot = 0.0
    full = 0.0
    rows = [(eid, by_id[eid], f) for eid, f in sm.TRI_SCOPE.items()]
    rows.append(("EPIC-P0-WALLETLAB", lab, 1.0))
    for eid, e, f in sorted(rows, key=lambda r: r[0]):
        w = e["pw"] * f
        tot += w
        full += e["pw"]
        via = " (through W_LAB_MIN, then W_LAB_REST)" if eid == "EPIC-P0-WALLETLAB" else ""
        lines.append(f"| {eid}{via} | {e['name']} | {e['squad']} | {e['pw']} | {f:.2f} | {w:.1f} |")
    lines.append(f"| **Total** | {len(rows)} epics | | **{full:.0f}** | | **{tot:.1f}** |")
    g = results["tiers"]["TRI"]["graph"]
    assert abs(tot - g["work_pw"]) < 0.5, (tot, g["work_pw"])
    n_gating = len(sm.GATING)
    lines.append("")
    lines.append(f"The fractions are editable inputs (`TRI_SCOPE` in [jira/schedule_model.py](jira/schedule_model.py)); changing one changes tier 1 only. "
                 f"Every gating epic not listed ({n_gating + 1 - len(rows)} of {n_gating + 1}, counting the wallet-lab epic that the model schedules through its special nodes) is out of tier 1. "
                 f"The generator rejects a fraction outside (0, 1] and an epic that no tier-1 gate waits for.")
    lines.append("")
    lines.append("Gates of the three networks that this revision adds or changes, with their explicit prerequisites (FS from every listed package; `(build, assurance)` means the readiness package is not needed):")
    lines.append("")
    lines.append("| Gate | Milestone | Waits for | Review time after the last prerequisite (weeks, low / mode / high) |")
    lines.append("|---|---|---|---|")
    ids = {m["node"]: m["id"] for m in results["tiers"]["TRI"]["milestones"]}
    for nid in ("G_FREEZE", "G_TRI2", "G_TRI3", "G_TRI4"):
        kind, deps, spec = sm.SPECIAL[nid]
        epic_deps = [d for d in deps if d.startswith("EPIC-")]
        if len(epic_deps) > 8:
            rest = [pretty_dep(d) for d in deps if not d.startswith("EPIC-")]
            txt = ", ".join(rest) + f" and all packages of every one of the {len(epic_deps)} epics of `TRI_SCOPE`"
        else:
            txt = ", ".join(pretty_dep(d) for d in deps)
        mlabel = next(m["label"] for m in results["tiers"]["TRI"]["milestones"] if m["node"] == nid)
        lines.append(f"| {nid} | {ids[nid]} {mlabel} | {txt} | {spec[0]} / {spec[1]} / {spec[2]} |")
    lines.append("")
    lines.append("New explicit waits before the protocol freeze (all three also feed G_FREEZE in tiers 2 and 3; every range is an **ASSUMPTION** that needs a named owner and approval):")
    lines.append("")
    lines.append("| Wait | Meaning | Starts | Low / mode / high (weeks) | Why this range |")
    lines.append("|---|---|---|---|---|")
    for nid in ("L_COUNSEL_NOTICE", "L_PERMIT2_E2", "L_PC_APPROVAL"):
        kind, deps, spec = sm.SPECIAL[nid]
        start = "week 0 (no prerequisite)" if not deps else "after " + " and ".join(pretty_dep(d) for d in deps)
        lines.append(f"| {nid} | {LEAD_DESC[nid]} | {start} | {spec[0]} / {spec[1]} / {spec[2]} | {WAIT_WHY[nid]} |")
    fd = results.get("freeze_drivers")
    if fd:
        lines.append("")
        lines.append("Which prerequisite determines the finish of the protocol freeze, as a share of 1,000 runs per row (a prerequisite that is not listed never determined it; "
                     "`#A` is the assurance package of an epic). This shows how much each new wait matters **in this generation**, not how much it could matter:")
        lines.append("")
        lines.append("| Network | Scenario | Prerequisites that determine the freeze |")
        lines.append("|---|---|---|")
        for tier in sm.TIER_ORDER:
            for key, label in SCEN_COLS:
                row = fd[tier][key]
                lines.append(f"| {TIER_TITLE[tier].split(' — ')[0]} ({tier}) | {label} | " + ", ".join(f"{k or 'none'} {v:.1f}%" for k, v in row.items()) + " |")
    return "\n".join(lines)


def md_schedule(results):
    T = results["tiers"]
    lines = [f"**EXPLORATORY — not a commitment.** Three roadmap tiers, each a Monte Carlo over its own network at work-package level (sizes in §3.1): {results['n_runs']:,} runs per scenario, seed {results['seed']}. "
             "P50 / P75 / P90 are the weeks (from the start of Phase 0) by which that fraction of runs has reached the milestone; the inputs are the assumptions of §3.4. "
             "Tiers 1 and 2 are simulated for the three scenarios below; tier 3 for six (the table after the three tiers). Each tier is simulated alone and competes only with its own work for the squads, "
             "so a tier's dates are neither the sum nor the continuation of another tier's."]
    lines += ["", "Headline: the last milestone of each tier (P50 / P75 / P90):", "",
              "| Tier | Last milestone | " + " | ".join(h for _, h in SCEN_COLS) + " |", "|---|---|" + "---|" * len(SCEN_COLS)]
    for t in sm.TIER_ORDER:
        td = T[t]
        m = next(x for x in td["milestones"] if x["node"] == td["top"])
        cells = [(f"**W{v[0]}** / W{v[1]} / W{v[2]}" if k == "recommended" else wk(v)) for k, v in ((k, td["scenarios"][k]["ms"][td["top"]]) for k, _ in SCEN_COLS)]
        lines.append(f"| {TIER_TITLE[t]} | {m['id']} {m['label']} | " + " | ".join(cells) + " |")
    for t in sm.TIER_ORDER:
        td = T[t]
        lines += ["", f"**{TIER_TITLE[t]}** — P50 / P75 / P90 by scenario:", "",
                  "| ID | Milestone | " + " | ".join(f"{h} (P50 / P75 / P90)" for _, h in SCEN_COLS) + " |", "|---|---|" + "---|" * len(SCEN_COLS)]
        for m in td["milestones"]:
            cells = []
            for k, _ in SCEN_COLS:
                v = td["scenarios"][k]["ms"][m["node"]]
                cells.append(f"**W{v[0]}** / W{v[1]} / W{v[2]}" if k == "recommended" else wk(v))
            lines.append(f"| {m['id']} | {m['label']} | " + " | ".join(cells) + " |")
    lines += ["", "Tier 3 under all six scenarios (the two licensing scenarios change only the legal path):", "",
              "| Scenario | Protocol freeze P50 | Phase 1 exit P50 | Private beta P50 | GA P50 | GA P75 | GA P90 |", "|---|---|---|---|---|---|---|"]
    for key, v in T["GA"]["scenarios"].items():
        m = v["ms"]
        lines.append(f"| {results['scenarios'][key]['label']} | W{m['G_FREEZE'][0]} | W{m['G_RG002'][0]} | W{m['G_BETA'][0]} | W{m['G_GA'][0]} | W{m['G_GA'][1]} | W{m['G_GA'][2]} |")
    return "\n".join(lines)


def md_criticality(results):
    T = results["tiers"]
    lines = []
    for t in sm.TIER_ORDER:
        td = T[t]
        top = td["top"]
        lines += [f"**{TIER_TITLE[t]}** — share of runs in which an epic (any of its work packages) or a gate lies on the chain that determines {top_id(results, t)} ({top}); "
                  "columns: " + " | ".join(h for _, h in SCEN_COLS) + ":", "",
                  "| Epic or gate | " + " | ".join(h for _, h in SCEN_COLS) + " |", "|---|" + "---|" * len(SCEN_COLS)]
        crit = {k: td["scenarios"][k]["crit"] for k, _ in SCEN_COLS}
        keys = [k for k, _ in sorted(crit["recommended"].items(), key=lambda x: -x[1])[:12]]
        for k in keys:
            lines.append(f"| {k} | " + " | ".join(f"{crit[s].get(k, 0):.0f}%" for s, _ in SCEN_COLS) + " |")
        lines.append("")
        cw = td["scenarios"]["recommended"]["crit_wp"]
        lines.append("Work packages most often on the recommended critical chain: " + ", ".join(f"{k} {v:.0f}%" for k, v in list(cw.items())[:8]) + ".")
        lines.append("")
    return "\n".join(lines).rstrip()


def md_queue_rule(results):
    """The queue-rule sensitivity: the recommended squads with and without serving every Phase 0 package first."""
    q = results["queue_rule"]
    T = results["tiers"]
    rows = [("TRI", "G_TRI4"), ("PMB", "G_RG001"), ("PMB", "G_RG002"), ("PMB", "G_BETA"), ("GA", "G_RG001"), ("GA", "G_BETA"), ("GA", "G_GA")]
    lines = ["| Tier and milestone | Model queue rule: longest remaining path first (P50 / P75 / P90) | Phase 0 packages served first (P50 / P75 / P90) | Difference at P50 (weeks) |", "|---|---|---|---|"]
    for tier, node in rows:
        m = next(x for x in T[tier]["milestones"] if x["node"] == node)
        a = T[tier]["scenarios"][results["recommended"]]["ms"][node]
        b = q[tier]["ms"][node]
        lines.append(f"| {m['id']} {m['label']} | {wk(a)} | {wk(b)} | {b[0] - a[0]:+d} |")
    lines.append("")
    lines.append("Both columns use the recommended squads. The first column is the published tier table. The second changes one thing in the model: a Phase 0 package, and the wallet-lab nodes, are served before any other package when a squad becomes free "
                 "(`first` in the `recommended_p0_first` scenario of `make_scenarios`). It is a sensitivity on the staffing rule, **not** a published scenario, and it changes no number in §3.2.")
    return "\n".join(lines)


def md_load(results):
    rec = results["scenarios"][results["recommended"]]
    T = results["tiers"]
    lines = ["| Squad | Headcount (as organized) | Headcount (recommended) | Tier 1 network work (pw) | Tier 2 network work (pw) | Tier 3 network work (pw) | GA-scope demand, all P0-P5 epics (pw) | Full-strength weeks of that demand, as organized |",
             "|---|---|---|---|---|---|---|---|"]
    for sq, hc, d, wk_ in results["squad_load"]:
        lines.append(f"| {sq} | {hc} | {rec['hc'].get(sq, hc)} | {T['TRI']['graph']['work_by_squad'][sq]:.0f} | {T['PMB']['graph']['work_by_squad'][sq]:.0f} | "
                     f"{T['GA']['graph']['work_by_squad'][sq]:.0f} | {d:.0f} | {wk_:.0f} |")
    lines.append(f"| **Total** | | | **{T['TRI']['graph']['work_pw']:.0f}** | **{T['PMB']['graph']['work_pw']:.0f}** | **{T['GA']['graph']['work_pw']:.0f}** | | |")
    lines.append("")
    lines.append("Network work counts the work packages and special work nodes each tier simulates (including audit-support, pen-test and wallet-E3 work); the GA-scope column sums all epics of phases P0-P5, scheduled or not.")
    lines.append("")
    base, rows = results["sensitivity"]["baseline"], results["sensitivity"]["rows"]
    lines.append(f"Sensitivity (tier 3, as organized): change in P50 (weeks) when two people join one squad at full strength from week 0 (baseline P50: contract audit freeze W{base['G_CONTRACT_FREEZE']:.0f}, "
                 f"Phase 1 exit W{base['G_RG002']:.0f}, private beta W{base['G_BETA']:.0f}, GA W{base['G_GA']:.0f}); noise is about ±1.5 weeks:")
    lines.append("")
    lines.append("| Squad (+2 people) | Audit freeze | Phase 1 exit | Private beta | GA |")
    lines.append("|---|---|---|---|---|")
    for sq, d in rows:
        lines.append(f"| {sq} | {d['G_CONTRACT_FREEZE']:+.1f} | {d['G_RG002']:+.1f} | {d['G_BETA']:+.1f} | {d['G_GA']:+.1f} |")
    return "\n".join(lines)


# ---------------------------------------------------------------- CSV
def priority(risk):
    return {"H": "High", "M": "Medium", "L": "Low"}.get(risk.strip()[0], "Medium")


def write_csv(stories):
    cols = ["Issue id", "Issue Type", "Summary", "Description", "Parent", "Epic Name", "Priority", "Labels", "Component/s",
            "Original Estimate", "Story Type", "Epic Profile", "Owner Role", "Dependencies", "Risk", "Acceptance Criteria", "Evidence",
            "Release Target", "Phase", "Scope Version", "Estimate Change"]
    ids = {e["id"]: i for i, e in enumerate(E, 1)}
    n = len(E)
    rows = []
    for e in E:
        labels = ["fastpay", e["phase"], VERSION_OF[e["phase"]].replace(".", "_"), "profile_" + e["profile"]] + [x for x in e["labels"].split(",") if x]
        types = [t for t in model.STORY_TYPES if any(s["epic"] == e["id"] and s["type"] == t for s in stories)]
        mig = next((s for s in stories if s["epic"] == e["id"] and s["type"] == "MIG"), None)
        ops = next((s for s in stories if s["epic"] == e["id"] and s["type"] == "OPS"), None)
        desc = ["%s" % e["name"], "", f"Phase: {e['phase']} | Version: {VERSION_OF[e['phase']]} | Profile: {e['profile']}",
                f"Owner squad: {e['squad']} | Estimate: {e['pw']} person-weeks ({est_text(e)})",
                f"Dependencies: {e['deps']}", f"Risk: {e['risk']}", "", f"Acceptance criteria: {e['accept']}", f"Evidence: {e['evidence']}", ""]
        if mig:
            desc.append(f"Migration requirements: {mig['summary']} -- {mig['accept']}")
        if ops:
            desc.append(f"Operational-readiness task: {ops['summary']} -- {ops['accept']}")
        desc += ["", "Story types in this epic (profile %s): %s." % (e["profile"], ", ".join(TYPE_NAME[t] for t in types))]
        rows.append({"Issue id": ids[e["id"]], "Issue Type": "Epic", "Summary": f"[{e['id']}] {e['name']}", "Description": "\n".join(desc),
                     "Parent": "", "Epic Name": e["id"], "Priority": priority(e["risk"]), "Labels": " ".join(labels),
                     "Component/s": e["squad"], "Original Estimate": f"{e['pw']}w", "Story Type": "", "Epic Profile": e["profile"],
                     "Owner Role": e["squad"], "Dependencies": e["deps"], "Risk": e["risk"], "Acceptance Criteria": e["accept"],
                     "Evidence": e["evidence"], "Release Target": e["target"], "Phase": e["phase"],
                     "Scope Version": VERSION_OF[e["phase"]], "Estimate Change": est_text(e)})
    label_extra = {"SEC": "security", "OBS": "observability", "TST": "test", "MIG": "migration", "OPS": "ops_readiness", "IMP": "implementation", "EVD": "evidence"}
    for s in stories:
        e = BY_ID[s["epic"]]
        n += 1
        kind = {"MIG": "Migration requirement: ", "OPS": "Operational-readiness task: ", "EVD": "Evidence and sign-off: "}.get(s["type"], "")
        summary_text = s["summary"][len("Evidence pack and sign-off: "):] if s["type"] == "EVD" and s["summary"].startswith("Evidence pack") else s["summary"]
        desc = "\n".join([f"{kind}{summary_text}", "", f"Epic: {e['id']} ({e['name']})", f"Epic profile: {e['profile']}",
                          f"Story type: {s['label']}", f"Owner: {s['owner']}", f"Estimate: {s['days']} person-days",
                          f"Dependencies: {e['deps']}", f"Risk: {e['risk']}", "",
                          f"Acceptance criteria: {s['accept']}", f"Epic evidence: {e['evidence']}"])
        rows.append({"Issue id": n, "Issue Type": "Story", "Summary": f"[{s['id']}] {s['summary']}", "Description": desc,
                     "Parent": ids[e["id"]], "Epic Name": "", "Priority": priority(e["risk"]),
                     "Labels": " ".join(["fastpay", e["phase"], VERSION_OF[e["phase"]].replace(".", "_"), "profile_" + e["profile"], label_extra[s["type"]]]),
                     "Component/s": e["squad"], "Original Estimate": f"{s['days']}d", "Story Type": s["label"], "Epic Profile": e["profile"],
                     "Owner Role": s["owner"], "Dependencies": e["deps"], "Risk": e["risk"], "Acceptance Criteria": s["accept"],
                     "Evidence": e["evidence"], "Release Target": e["target"], "Phase": e["phase"],
                     "Scope Version": VERSION_OF[e["phase"]], "Estimate Change": ""})
    with open(HERE / "backlog.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def patch(path, tag, content):
    text = path.read_text(encoding="utf-8")
    pat = re.compile(rf"(<!-- BEGIN:{tag} -->)(.*?)(<!-- END:{tag} -->)", re.S)
    if not pat.search(text):
        sys.exit(f"marker {tag} not found in {path}")
    path.write_text(pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text), encoding="utf-8")


def all_blocks(stories, results, cap_md):
    """Every generated block of document 07, by marker name."""
    return {"CAPACITY": cap_md, "DELTA": md_delta(results), "TIERS": md_tiers(results), "SCHEDULE": md_schedule(results),
            "CRITICALITY": md_criticality(results), "QUEUERULE": md_queue_rule(results), "LOAD": md_load(results), "MODEL": md_model(), "TRISCOPE": md_triscope(results),
            "EPICS": md_epics(stories, results), "PROFILES": md_profiles(stories), "STORYSTATS": md_storystats(stories)}


def stale_blocks(path, blocks):
    text = path.read_text(encoding="utf-8")
    out = []
    for tag, content in blocks.items():
        m = re.search(rf"<!-- BEGIN:{tag} -->(.*?)<!-- END:{tag} -->", text, re.S)
        if not m:
            out.append(f"{tag}: marker missing in {path.name}")
        elif m.group(1) != f"\n{content}\n":
            out.append(f"{tag}: generated block in {path.name} is stale")
    return out


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    check_only = "--check" in sys.argv
    results = load_results()
    stories = build_stories()
    errs = validate(stories, results)
    if errs:
        print(f"{len(errs)} validation problem(s):")
        for x in errs[:60]:
            print("  -", x)
        if len(errs) > 60:
            print(f"  ... and {len(errs) - 60} more")
        sys.exit(1)
    cap_md, ok = md_capacity(results)
    print(cap_md)
    print(f"\n{len(E)} epics, {len(stories)} stories")
    if not ok:
        print("\nWARNING: at least one v1.0 phase window is more than %d%% utilized in the recommended scenario" % int((1 - model.MIN_SLACK) * 100))
        sys.exit(1)
    plan = SPEC / "07-delivery-plan.md"
    blocks = all_blocks(stories, results, cap_md)
    if check_only:
        stale = stale_blocks(plan, blocks)
        if stale:
            print(f"{len(stale)} generated block(s) of {plan.name} out of date: run `python -I spec/jira/build_backlog.py`")
            for x in stale:
                print("  -", x)
            sys.exit(1)
        print("check passed")
        sys.exit(0)
    n = write_csv(stories)
    for tag, content in blocks.items():
        patch(plan, tag, content)
    print(f"\nwrote backlog.csv with {n} issues")
