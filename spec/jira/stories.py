"""Story-type rules shared by the backlog generator (build_backlog.py) and the schedule model (schedule_model.py).

An epic's profile (model.PROFILES) decides which story types it carries. Story types fall into three work-package groups used by the
schedule model: B build (implementation, research task, compliance control, program action), A assurance (security, test, observability)
and R readiness (migration requirement, operational readiness, evidence and sign-off).
"""
import model

TYPE_NAME = {"IMP": "Implementation", "SEC": "Security", "OBS": "Observability", "TST": "Test", "MIG": "Migration requirement",
             "OPS": "Operational readiness", "EVD": "Evidence and sign-off"}
BASE_WEIGHT = {"IMP": 0.50, "SEC": 0.10, "OBS": 0.08, "TST": 0.18, "MIG": 0.06, "OPS": 0.08, "EVD": 0.07}
FIELD = {"SEC": "sec", "OBS": "obs", "TST": "test", "MIG": "mig", "OPS": "ops"}
GROUP = {"IMP": "B", "SEC": "A", "TST": "A", "OBS": "A", "MIG": "R", "OPS": "R", "EVD": "R"}
GROUP_NAME = {"B": "build", "A": "assurance", "R": "readiness"}


def types_present(e):
    """Story types the epic carries, in generation order."""
    prof = model.PROFILES[e["profile"]]
    out = []
    if "IMP" not in prof["na"]:
        out.append("IMP")
    out += [t for t in FIELD if t not in prof["na"]]
    if "EVD" in prof["required"] or ("EVD" in prof["optional"] and len(e["evidence"].strip()) >= 12):
        out.append("EVD")
    return out


def wp_shares(e):
    """Share of the epic's effort in each work-package group (sums to 1; groups with no story type are absent)."""
    present = types_present(e)
    norm = sum(BASE_WEIGHT[t] for t in present)
    sh = {"B": 0.0, "A": 0.0, "R": 0.0}
    for t in present:
        sh[GROUP[t]] += BASE_WEIGHT[t] / norm
    return {g: v for g, v in sh.items() if v > 0}
