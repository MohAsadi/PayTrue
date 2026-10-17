#!/usr/bin/env python3
"""Compute whether protocol freeze (RG-016) may be requested, from recorded evidence only (revision 0.5).

The conditions are those of document 16 section 1. A condition is satisfied only by files under spec/evidence/ (and
spec/config/pc_records.json); prose in the documents never satisfies one. This tool never approves anything: it reports, and with
--require-ready it fails unless every condition holds.

Run:  python -I spec/tools/freeze_readiness.py                  report (exit 0 whatever the state)
      python -I spec/tools/freeze_readiness.py --require-ready  exit 1 unless READY (use before anyone records an approval)
      python -I spec/tools/freeze_readiness.py --lint           exit 1 if a document claims an approval while the tool says NOT READY
"""
import hashlib
import json
import pathlib
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC = pathlib.Path(__file__).resolve().parent.parent
EVID = SPEC / "evidence"

# EVL rows required for the freeze (document 16 section 9): id -> (wallet, set of WL tests that need a reviewed PASS run)
FREEZE_EVL = {
    "EVL-01": ("MetaMask", {"WL-01", "WL-02", "WL-03", "WL-04", "WL-08", "WL-09", "WL-10", "WL-32", "WL-33"}),
    "EVL-02": ("MetaMask", {"WL-05", "WL-11", "WL-11b", "WL-33", "WL-34", "WL-37"}),
    "EVL-03": ("MetaMask", {"WL-12", "WL-39"}),
    "EVL-04": ("MetaMask", {"WL-14", "WL-35"}),
    "EVL-05": ("MetaMask", {"WL-15"}),
    "EVL-06": ("MetaMask iOS", {"WL-01", "WL-02", "WL-03", "WL-04", "WL-05", "WL-11", "WL-32", "WL-33"}),
    "EVL-07": ("MetaMask", {"WL-19", "WL-40"}),
    "EVL-08": ("MetaMask", {"WL-16", "WL-17", "WL-18", "WL-36"}),
    "EVL-09": ("Trust Wallet", {"WL-01", "WL-02", "WL-04", "WL-05", "WL-06"}),
    "EVL-10": ("Synthetic fixtures", {"WL-08", "WL-13", "WL-14"}),
}
RUN_FIELDS = ("runId", "testId", "wallet", "walletVersion", "platform", "accountType", "chainId", "startedAt", "tester", "reviewer",
              "raw", "result", "evidenceId", "evl")
PR_IDS = [f"PR-{i:02d}" for i in range(1, 17)]
FORK_FREEZE = ["RV-T01", "RV-T02", "RV-T04", "RV-T05", "RV-T07", "RV-T11", "MIG-TV-22"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_signatures(record):
    """A run record counts only if the tester and the reviewer, both registered in evidence/wallet-lab-kit/people.json, signed it."""
    sys.path.insert(0, str(SPEC / "tools"))
    import wallet_lab_verify as W  # noqa: PLC0415
    return W.verify_record(record, W.load_people())


def wallet_lab():
    """EVL rows with a complete, reviewed, checksummed set of PASS records. Returns (complete ids, problems)."""
    root = EVID / "wallet-lab"
    runs = []
    problems = []
    if root.exists():
        for p in sorted(root.rglob("*.json")):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                problems.append(f"{p.name}: not JSON")
                continue
            miss = [f for f in RUN_FIELDS if not r.get(f)]
            if miss:
                problems.append(f"{p.name}: missing {', '.join(miss)}")
                continue
            if r["tester"] == r["reviewer"]:
                problems.append(f"{p.name}: tester and reviewer are the same person")
                continue
            bad = [a["name"] for a in r["raw"] if not (p.parent / a["name"]).exists() or sha256(p.parent / a["name"]) != a.get("sha256")]
            if bad:
                problems.append(f"{p.name}: artifact missing or checksum mismatch: {', '.join(bad)}")
                continue
            sig_problems, _notes = _verify_signatures(r)
            if sig_problems:
                problems.append(f"{p.name}: signatures: {sig_problems[0]}")
                continue
            runs.append(r)
    done = set()
    for evl, (_wallet, tests) in FREEZE_EVL.items():
        have = {r["testId"] for r in runs if r["evl"] == evl and r["result"] == "PASS"}
        if tests <= have:
            done.add(evl)
    return done, problems, len(runs), runs


def permit2():
    p = EVID / "permit2" / "pin.json"
    if not p.exists():
        return False, ["no pin record"]
    ev = json.loads(p.read_text(encoding="utf-8"))
    why = []
    review = ev.get("humanReview", {})
    for pr in PR_IDS:
        rv = review.get(pr)
        if not rv or len({x for x in rv.get("reviewers", [])}) < 2 or not rv.get("signedAt") or rv.get("level") != "E2":
            why.append(f"{pr}: no E2 sign-off by two named reviewers")
    if not ev.get("rebuild", {}).get("matches"):
        why.append("no rebuild comparison (source to deployed bytecode)")
    fork = ev.get("forkReport", {})
    for t in FORK_FREEZE:
        if fork.get(t) != "PASS":
            why.append(f"fork test {t} not recorded as PASS")
    return not why, why


def constants():
    p = SPEC / "config" / "pc_records.json"
    if not p.exists():
        return False, "records file absent", 0, 0
    data = json.loads(p.read_text(encoding="utf-8"))
    recs = data["records"] if isinstance(data, dict) and "records" in data else data
    total = len(recs)
    approved = sum(1 for r in recs if r.get("status") == "APPROVED")
    return approved == total and total >= 18, f"{approved} of {total} approved", approved, total


TYPED_DATA_TESTS = ("WL-16", "WL-17", "WL-27", "WL-36")     # a real wallet signs the mandate, the successor authorization, the Pay Once witness and the pin


def eip712_freeze(reg):
    """C-11: the EIP-712 types are frozen. It is MET only when all five parts hold; each part is reported, none is waived:
      TYPES        eip712/types.json is complete and every generated artifact (Solidity in both projects, TypeScript, vectors, payloads) is current
      HASHES       the Python, TypeScript and both Solidity implementations agree on the golden vectors (a recorded run for the CURRENT fingerprint)
      SIGNATURES   real wallets signed the typed messages: a reviewed, signature-verified PASS run record for each of WL-16, WL-17, WL-27 and WL-36
      VERSIONING   the versioning policy (rules V1 to V6) is in the file and in the fingerprint
      APPROVALS    two different named people (the Wallet Protocol Engineer and the Solidity Lead) approved the exact fingerprint
    """
    import subprocess  # noqa: PLC0415
    sys.path.insert(0, str(SPEC / "tools"))
    import eip712_types as E  # noqa: PLC0415
    reg_e = E.Registry(E.load())
    current = E.freeze_fingerprint(reg_e)
    parts = []

    r = subprocess.run([sys.executable, "-I", str(SPEC / "tools" / "export_eip712.py"), "--check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    parts.append(("TYPES", r.returncode == 0, "the generated artifacts are current" if r.returncode == 0 else "a generated artifact is stale"))

    import eip712_crosscheck as X  # noqa: PLC0415
    okh, txt = X.check()
    parts.append(("HASHES", okh, txt))

    _d, _p, _n, runs = wallet_lab()
    have = {r["testId"] for r in runs if r["result"] == "PASS"}
    missing = [t for t in TYPED_DATA_TESTS if t not in have]
    parts.append(("SIGNATURES", not missing, "a reviewed run record exists for every typed-data test" if not missing else "no reviewed wallet run record for " + ", ".join(missing)))

    rules = (E.load().get("versioning") or {}).get("rules", [])
    okv = len(rules) >= 6      # the rules are part of the fingerprint (freeze_fingerprint hashes them), so approving the fingerprint approves the policy
    parts.append(("VERSIONING", okv, f"{len(rules)} rules in the file and in the fingerprint" if okv else "the versioning policy is missing"))

    rec = reg.get("eip712Freeze")
    why = []
    if not rec:
        why.append(f"no approval of fingerprint {current[:12]}… recorded")
    else:
        if rec.get("fingerprint") != current:
            why.append("the approved fingerprint differs from the current eip712/types.json")
        roles = {a.get("role"): a for a in rec.get("approvers", []) if a.get("name") and a.get("signedAt") and a.get("evidenceId")}
        for need in ("Wallet Protocol Engineer", "Solidity Lead"):
            if need not in roles:
                why.append(f"no named approval by the {need}")
        if len({a["name"] for a in roles.values()}) < 2:
            why.append("the two approvers must be two different people")
    parts.append(("APPROVALS", not why, "two named approvals of the current fingerprint" if not why else "; ".join(why)))

    ok = all(p[1] for p in parts)
    return ok, " | ".join(f"{n} {'met' if o else 'NOT MET'}: {t}" for n, o, t in parts)


def conditions():
    reg = json.loads((EVID / "freeze_register.json").read_text(encoding="utf-8"))
    out = []
    out.append(("C-1", "Companion artifacts complete and reviewed", False, "drafted in 0.5; no owner review recorded"))
    done, problems, nruns, _runs = wallet_lab()
    out.append(("C-2", "Wallet-lab evidence EVL-01…EVL-10 produced and reviewed", len(done) == len(FREEZE_EVL),
                f"{len(done)} of {len(FREEZE_EVL)} complete ({nruns} valid run records){'; problems: ' + '; '.join(problems[:3]) if problems else ''}"))
    ok, why = permit2()
    out.append(("C-3", "Pinned Permit2 review at E2, rebuild and fork subset", ok, "satisfied" if ok else f"{len(why)} open items (first: {why[0]})"))
    ok, txt, _a, _t = constants()
    out.append(("C-4", "Production-blocking constants approved one by one", ok, txt))
    open_ud = sorted(k for k, v in reg["freezeBlockingDecisions"].items() if v != "CLOSED")
    out.append(("C-5", "Freeze-blocking unresolved decisions closed", not open_ud, f"{len(open_ud)} open of {len(reg['freezeBlockingDecisions'])}"))
    open_ux = sorted(k for k, v in reg["freezeBlockingFacts"].items() if v not in ("CLOSED", "RECORDED_RISK"))
    out.append(("C-6", "Freeze-blocking external facts closed or carried as recorded risks", not open_ux, f"{len(open_ux)} open of {len(reg['freezeBlockingFacts'])}"))
    out.append(("C-7", "Two independent planner implementations pass the vectors", len(reg["plannerImplementations"]) >= 2,
                f"{len(reg['plannerImplementations'])} implementations recorded"))
    out.append(("C-8", "Audit scope agreed with both firms; slots contracted", len(reg["auditEngagements"]) >= 2,
                f"{len(reg['auditEngagements'])} engagements recorded"))
    fr = reg.get("foundryReport")
    cr = reg.get("contractsReport")
    ok_model = bool(fr) and fr.get("compiled") is True and fr.get("failed") == 0 and fr.get("passed", 0) > 0
    ok_contracts = bool(cr) and cr.get("compiled") is True and cr.get("failed") == 0 and cr.get("passed", 0) > 0
    detail = ("MODEL " + ("%d passed, %d failed, %d skipped" % (fr["passed"], fr["failed"], fr.get("skippedInThisRun", 0)) if fr else "no run recorded")
              + " | CONTRACTS " + ("%d passed, %d failed, %d skipped, largest runtime %d bytes" % (cr["passed"], cr["failed"], cr.get("skippedInThisRun", 0), cr.get("runtimeBytesLargest", 0)) if cr else "no run recorded"))
    out.append(("C-9", "Foundry suites of the reference model AND of the actual contracts compile and pass; fork subset passes", ok_model and ok_contracts, detail))
    signed = [k for k, v in reg["signoffs"].items() if v]
    out.append(("C-10", "Sign-offs: Principal Architect, CISO (veto), VP Engineering, QA Lead", len(signed) == len(reg["signoffs"]),
                f"{len(signed)} of {len(reg['signoffs'])} given"))
    ok11, why11 = eip712_freeze(reg)
    out.append(("C-11", "EIP-712 type strings frozen: approved by the Wallet Protocol Engineer and the Solidity Lead", ok11, why11))
    return out


def lint(ready):
    """A document may not claim an approval while the evidence says NOT READY."""
    bad = []
    if ready:
        return bad
    t16 = (SPEC / "16-freeze-decision-report.md").read_text(encoding="utf-8")
    if not re.search(r"\*\*PROTOCOL FREEZE \(RG-016\) IS NOT APPROVED", t16):
        bad.append("16: the decision line does not say NOT APPROVED")
    sec = t16.split("## 10. Approval record", 1)[-1].split("## 11.", 1)[0]
    for line in sec.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 5 and cells[1] and cells[3] and not cells[3].startswith(("Decision", "---")) and "NOT SIGNED" not in cells[3] and cells[3] != "—":
            bad.append(f"16 section 10: a sign-off row is not 'NOT SIGNED': {cells[1]}")
    for f in sorted(SPEC.glob("*.md")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(?i)\b(freeze|RG-016)\b[^.\n]{0,40}\b(is|was|has been) approved\b", line) and not re.search(r"(?i)not approved|until|before|only when|may be approved|\b(when|once|if|unless|after|whether)\b", line):
                bad.append(f"{f.name}:{i}: claims an approval")
    return bad


def main():
    conds = conditions()
    ready = all(c[2] for c in conds)
    print("PROTOCOL FREEZE (RG-016) READINESS from recorded evidence")
    for cid, text, ok, detail in conds:
        print(f"  {cid:5s} {'MET    ' if ok else 'NOT MET'}  {text}  [{detail}]")
    met = sum(1 for c in conds if c[2])
    print(f"READY ({met} of {len(conds)} conditions met)" if ready else f"NOT READY ({met} of {len(conds)} conditions met)")
    if "--lint" in sys.argv:
        bad = lint(ready)
        for b in bad:
            print("  LINT", b)
        print("lint: ok" if not bad else "lint: FAILED")
        return 1 if bad else 0
    if "--require-ready" in sys.argv and not ready:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
