#!/usr/bin/env python3
"""Record run results in the evidence files that tools/freeze_readiness.py reads. It records what a run file says and nothing else.

    python -I spec/tools/record_evidence.py --foundry evidence/implementation/logs/forge-test-final.json
        -> evidence/freeze_register.json  foundryReport   (compiled, suites, passed, failed, skipped, tool versions, the sha256 of the run file)
    python -I spec/tools/record_evidence.py --fork evidence/implementation/fork-runs.json
        -> evidence/permit2/pin.json      forkReport      (RV-T01 ... PASS only if the test passed on every chain run), forkRuns (blocks)
    python -I spec/tools/record_evidence.py --contracts
        -> evidence/freeze_register.json  contractsReport (the ACTUAL contracts: tests, sizes, loop audit, mutation, forks; read from their evidence files)

Neither call approves anything: freeze_readiness.py still decides from all eleven conditions, and the human reviews (E2), the wallet lab,
the constants, the decisions and the sign-offs are outside what a run can produce. `--foundry` refuses a run file that has a failure or
no test at all; `--fork` records FAIL for a test that failed on any chain and records nothing for a chain that did not run.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / "evidence" / "freeze_register.json"
PIN = ROOT / "evidence" / "permit2" / "pin.json"
FORK_IDS = {"RV_T01": "RV-T01", "RV_T02": "RV-T02", "RV_T03": "RV-T03", "RV_T04": "RV-T04", "RV_T05": "RV-T05", "RV_T06": "RV-T06", "RV_T07": "RV-T07",
            "RV_T08": "RV-T08", "RV_T10": "RV-T10", "RV_T11": "RV-T11", "MIG_TV_22": "MIG-TV-22"}


def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def versions():
    out = subprocess.run([sys.executable, "-I", str(ROOT / "toolchain" / "forge.py"), "--version"], capture_output=True, text=True).stdout.strip()
    return out.replace("\n", " | ")


def parse_forge_json(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    data = json.loads(text[text.index("{"):])
    n = dict(passed=0, failed=0, skipped=0)
    suites = 0
    fuzz_runs = 0
    for _suite, s in data.items():
        suites += 1
        for _t, tr in s.get("test_results", {}).items():
            st = tr.get("status")
            n["passed" if st == "Success" else "failed" if st == "Failure" else "skipped"] += 1
            fuzz_runs += (tr.get("kind", {}).get("Fuzz", {}) or {}).get("runs", 0) or 0
    return suites, n, fuzz_runs, data


def trim(data):
    """The part of a forge run that evidence needs: per test the status, reason, kind (gas, fuzz runs), duration, counterexample and decoded logs.
    The traces and raw logs of a run are most of its size (tens of megabytes) and are kept only in the gzip of the raw file."""
    out = {}
    for suite, s in data.items():
        out[suite] = {"duration": s.get("duration"), "warnings": s.get("warnings"), "test_results": {
            n: {k: tr.get(k) for k in ("status", "reason", "counterexample", "kind", "duration", "decoded_logs")} for n, tr in s.get("test_results", {}).items()}}
    return out


def record_foundry(path):
    import gzip
    raw = pathlib.Path(path).resolve()
    suites, n, fuzz, data = parse_forge_json(raw)
    if n["failed"] or n["passed"] == 0:
        sys.exit(f"refusing to record: {n} in {path}")
    trimmed_path = raw.with_name("forge-test-final.json")
    gz_path = raw.with_name("forge-test-final.raw.json.gz")
    gz_path.write_bytes(gzip.compress(raw.read_bytes(), 9, mtime=0))
    trimmed_path.write_text(json.dumps(trim(data), indent=1) + "\n", encoding="utf-8", newline="\n")
    if raw != trimmed_path:
        raw.unlink()
    reg = json.loads(REG.read_text(encoding="utf-8"))
    rel = str(trimmed_path.relative_to(ROOT)).replace("\\", "/")
    reg["foundryReport"] = dict(compiled=True, suites=suites, passed=n["passed"], failed=n["failed"], skippedInThisRun=n["skipped"],
                                fuzzRunsExecuted=fuzz, tool=versions(), solc="0.8.24 (via-IR, 20 optimizer runs, cancun)", runFile=rel,
                                runFileSha256=sha256_file(trimmed_path), rawRunFileGzip=str(gz_path.relative_to(ROOT)).replace("\\", "/"),
                                rawRunFileGzipSha256=sha256_file(gz_path),
                                scope="every suite of spec/foundry/test; the fork suites (test/fork) are skipped in this run because no RPC URL is set and are "
                                      "reported by evidence/implementation/fork-runs.json",
                                note="recorded by tools/record_evidence.py from the run file; this records a test run, not an approval")
    REG.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"foundryReport recorded: {suites} suites, {n['passed']} passed, {n['failed']} failed, {n['skipped']} skipped, {fuzz} fuzz runs")


def record_fork(path):
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    per_test = {}
    runs = {}
    for ch in doc["chains"]:
        used = ch["attempts"][ch.get("usedAttempt", -1)] if ch["attempts"] else None
        runs[str(ch["chainId"])] = dict(name=ch["name"], block=ch["block"], blockHash=ch["blockHash"], result=ch["result"],
                                        passed=used.get("passed") if used else None, failed=used.get("failed") if used else None)
        for t in (used or {}).get("tests", []):
            m = re.match(r"test(?:Fuzz)?_(RV_T\d\d|MIG_TV_22)", t["test"])
            if m:
                per_test.setdefault(FORK_IDS[m.group(1)], {})[str(ch["chainId"])] = t["status"]
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    n_chains = len(doc["chains"])
    report = {}
    for tid, by in sorted(per_test.items()):
        report[tid] = "PASS" if len(by) == n_chains and all(s == "Success" for s in by.values()) else "FAIL"
    pin["forkReport"] = report
    pin["forkRuns"] = dict(file=str(pathlib.Path(path).resolve().relative_to(ROOT)).replace("\\", "/"), fileSha256=sha256_file(path), forge=doc["forge"],
                           pinnedCommit=doc["pinnedCommit"], chains=runs,
                           note="a test is PASS only if it passed on every chain listed; recorded by tools/record_evidence.py")
    ne = [x for x in pin.get("notEstablished", []) if not x.startswith("rebuild of the pinned source")]
    if report and all(v == "PASS" for v in report.values()):
        ne = [x for x in ne if not x.startswith("fork tests")]
        ne.append("fork tests: only the subset in forkReport, on the chains and blocks of forkRuns, against the mock tokens of the tests")
    pin["notEstablished"] = ne
    PIN.write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("forkReport:", report)


def record_contracts():
    """The evidence of the actual contracts, read from the files that the tools of the contracts wrote. It refuses a failing run and a stale file."""
    impl = ROOT / "evidence" / "implementation"
    summ = json.loads((impl / "contracts-test-run.json").read_text(encoding="utf-8"))
    rep = json.loads((impl / "contracts-report.json").read_text(encoding="utf-8"))
    loops = json.loads((impl / "loop-audit-contracts.json").read_text(encoding="utf-8"))
    if summ["failed"] or not summ["passed"]:
        sys.exit(f"refusing to record: the contracts run has {summ['failed']} failures and {summ['passed']} passes")
    if rep["verdict"] != "PASS" or loops["verdict"] != "PASS":
        sys.exit("refusing to record: the contracts report or the loop audit of the contracts does not pass")
    reg = json.loads(REG.read_text(encoding="utf-8"))
    mut = impl / "contracts-mutation.json"
    forks = impl / "contracts-fork-runs.json"
    rec = dict(compiled=True, passed=summ["passed"], failed=summ["failed"], skippedInThisRun=summ["skipped"], suites=len(summ["suites"]), tool=summ["forge"],
               solc="0.8.24 (no via-IR, 200 optimizer runs, cancun)", runFile="evidence/implementation/contracts-test-run.json", runFileSha256=sha256_file(impl / "contracts-test-run.json"),
               reportFileSha256=sha256_file(impl / "contracts-report.json"), runtimeBytesLargest=max(c["runtimeBytes"] for c in rep["contracts"].values() if c["file"].startswith("src/") and c["runtimeBytes"] > 100),
               loopsAudited=len(loops["loops"]),
               note="recorded by tools/record_evidence.py --contracts; this records a test run of the actual contracts, not an approval and not an audit")
    if mut.exists():
        m = json.loads(mut.read_text(encoding="utf-8"))
        rec["mutation"] = dict(m["counts"], file="evidence/implementation/contracts-mutation.json", fileSha256=sha256_file(mut))
    if forks.exists():
        f = json.loads(forks.read_text(encoding="utf-8"))
        rec["forks"] = dict(verdict=f["verdict"], chains={str(c["chainId"]): dict(block=c["block"], result=c["result"]) for c in f["chains"]}, file="evidence/implementation/contracts-fork-runs.json",
                            fileSha256=sha256_file(forks))
    reg["contractsReport"] = rec
    REG.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"contractsReport recorded: {rec['passed']} passed, {rec['failed']} failed, {rec['skippedInThisRun']} skipped; mutation {rec.get('mutation', {}).get('killed', '-')} killed; forks {rec.get('forks', {}).get('verdict', '-')}")


def main(argv):
    if argv == ["--contracts"]:
        record_contracts()
        return 0
    if len(argv) == 2 and argv[0] == "--foundry":
        record_foundry(argv[1])
        return 0
    if len(argv) == 2 and argv[0] == "--fork":
        record_fork(argv[1])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
