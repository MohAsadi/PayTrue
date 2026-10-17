#!/usr/bin/env python3
"""Run the tests of the ACTUAL FastPay contracts and record the result (evidence class: FastPay contracts).

    python -I spec/tools/contracts_tests.py            forge test --json -vv in contracts/ ; writes evidence/implementation/logs/contracts-forge-test.json
                                                        (raw) and evidence/implementation/contracts-test-run.json (summary)
    python -I spec/tools/contracts_tests.py --check    the summary on disk equals the raw log and every test passed

The summary is what the implementation report reads: per suite the number of tests passed, failed and skipped; for the stateful fuzz the runs,
calls and reverts and the coverage lines that the handler prints; the gas measurements (the named logs of Gas.t.sol). Nothing is typed by hand.
Evidence classes are kept apart: this file says nothing about the reference model (spec/foundry), the Permit2 rebuild or the wallet lab.
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORGE = ROOT / "toolchain" / "forge.py"
RAW = ROOT / "evidence" / "implementation" / "logs" / "contracts-forge-test.json"
SUMMARY = ROOT / "evidence" / "implementation" / "contracts-test-run.json"


def run():
    r = subprocess.run([sys.executable, "-I", str(FORGE), "--project", "contracts", "test", "--json", "-vv"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=3600)
    out = (r.stdout or "")
    i = out.find("{")
    if i < 0:
        sys.exit("no JSON from forge:\n" + (r.stderr or "")[-2000:])
    return json.loads(out[i:]), r.returncode


def forge_version():
    r = subprocess.run([sys.executable, "-I", str(FORGE), "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[0] if r.returncode == 0 else "unknown"


def summarize(raw, forge_ver):
    suites, gas, coverage = [], [], []
    tp = tf = ts = 0
    inv = {}
    for name, s in sorted(raw.items()):
        p = f = k = 0
        for tname, t in s["test_results"].items():
            st = t["status"]
            if st == "Success":
                p += 1
            elif st == "Skipped":
                k += 1
            else:
                f += 1
            kind = t.get("kind", {})
            if "Invariant" in kind:
                inv[tname] = {"runs": kind["Invariant"].get("runs"), "calls": kind["Invariant"].get("calls"), "reverts": kind["Invariant"].get("reverts")}
            for line in t.get("decoded_logs", []) or []:
                m = re.match(r"^\s*(.+?):\s+(\d+)\s*$", line)
                if m and name.endswith("GasTest"):
                    gas.append({"test": tname.split("(")[0], "name": m.group(1), "value": int(m.group(2))})
                if line.strip().startswith("coverage:"):
                    coverage.append(line.strip())
        suites.append({"suite": name, "passed": p, "failed": f, "skipped": k})
        tp, tf, ts = tp + p, tf + f, ts + k
    return {"schema": 1, "tool": "tools/contracts_tests.py", "forge": forge_ver, "project": "contracts", "total": tp + tf + ts, "passed": tp, "failed": tf, "skipped": ts,
            "suites": suites, "invariants": inv, "gas": gas, "handlerCoverage": coverage[-10:],
            "note": "The reference-model suites (spec/foundry), the Permit2 fork tests and the wallet lab are separate evidence and are not counted here."}


def main(argv):
    if "--check" in argv:
        if not RAW.exists() or not SUMMARY.exists():
            print("contracts test run: missing (run python -I spec/tools/contracts_tests.py)")
            return 1
        raw = json.loads(RAW.read_text(encoding="utf-8"))
        cur = json.loads(SUMMARY.read_text(encoding="utf-8"))
        want = summarize(raw, cur["forge"])
        if want != {k: v for k, v in cur.items() if k != "generatedAt"}:
            print("contracts test run: the summary does not match the raw log")
            return 1
        if cur["failed"]:
            print(f"contracts test run: {cur['failed']} failing tests recorded")
            return 1
        print(f"contracts test run: {cur['passed']} passed, {cur['skipped']} skipped, 0 failed (recorded)")
        return 0
    raw, code = run()
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8", newline="\n")
    s = summarize(raw, forge_version())
    s["generatedAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    SUMMARY.write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8", newline="\n")
    for x in s["suites"]:
        print(f"  {x['suite']:<55} {x['passed']:>4} passed {x['failed']:>3} failed {x['skipped']:>3} skipped")
    print(f"contracts: {s['passed']} passed, {s['failed']} failed, {s['skipped']} skipped (forge exit {code})")
    return 0 if s["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
