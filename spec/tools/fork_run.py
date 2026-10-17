#!/usr/bin/env python3
"""Run the Permit2 fork tests on Ethereum, Base and Arbitrum One at pinned blocks and record the result.

    python -I spec/tools/fork_run.py [--chains 1,8453,42161] [--back 64] [--fuzz-runs N] [--project contracts]

For each chain: ask the RPC providers of evidence/permit2/pin.json for the latest block; choose block = latest - BACK (default 64);
require that at least two providers return the same hash for that block; run `forge test --match-path "test/fork/*"` with ETH_RPC_URL,
FORK_BLOCK and EXPECT_CHAIN_ID set; parse forge's JSON result. Writes evidence/implementation/fork-runs.json (one record per chain: the
provider set, the block number and hash, the forge version, every test with its status and decoded logs, the counts) and the raw output
to evidence/implementation/logs/fork-<chainid>.json. Exit code 0 only if every chain ran and every test passed or was skipped for a
documented reason (none is expected: an unset RPC URL is the only skip, and it is not used here).

With `--project contracts` the same is done for the ACTUAL FastPay contracts (contracts/test/fork: the suites of the contracts run against the real
Permit2 of each chain) and the result goes to evidence/implementation/contracts-fork-runs.json (a separate evidence file: the Permit2 fork evidence and
the fork evidence of the contracts are not mixed).

The fork tests read the chain through public RPC providers: a fork run is network-dependent evidence, unlike the rest of the suite.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PIN = ROOT / "evidence" / "permit2" / "pin.json"
OUT = ROOT / "evidence" / "implementation" / "fork-runs.json"
LOGS = ROOT / "evidence" / "implementation" / "logs"


def rpc(url, method, params, timeout=25):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"content-type": "application/json", "user-agent": "fastpay-evidence/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (https endpoints named in evidence/permit2/pin.json)
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]


def choose_block(cid, providers, back):
    live = []
    for url in providers:
        try:
            if int(rpc(url, "eth_chainId", []), 16) != int(cid):
                continue
            live.append((url, int(rpc(url, "eth_blockNumber", []), 16)))
        except Exception:  # noqa: BLE001
            continue
    if len(live) < 2:
        raise SystemExit(f"chain {cid}: fewer than two providers answered ({[u for u, _ in live]})")
    block = min(b for _, b in live) - back
    hashes = {}
    for url, _ in live:
        try:
            h = rpc(url, "eth_getBlockByNumber", [hex(block), False])["hash"]
            hashes[url] = h
        except Exception:  # noqa: BLE001
            continue
    if len(hashes) < 2 or len(set(hashes.values())) != 1:
        raise SystemExit(f"chain {cid}: providers disagree on or cannot serve block {block}: {hashes}")
    return block, next(iter(hashes.values())), list(hashes)


def gas_of(kind):
    """Gas of a standard test: forge 1.8.5 writes {"Standard": gas}; older versions {"Standalone": {"gas": ...}}."""
    if isinstance(kind.get("Standard"), int):
        return kind["Standard"]
    if isinstance(kind.get("Standalone"), dict):
        return kind["Standalone"].get("gas")
    return None


def forge_version():
    r = subprocess.run([sys.executable, "-I", str(ROOT / "toolchain" / "forge.py"), "--version"], capture_output=True, text=True)
    return r.stdout.strip().replace("\n", " | ")


def run_chain(cid, name, providers, back, fuzz_runs, project=None):
    block, bhash, agreeing = choose_block(cid, providers, back)
    LOGS.mkdir(parents=True, exist_ok=True)
    rec = dict(chainId=int(cid), name=name, block=block, blockHash=bhash, providersAgreeing=agreeing, attempts=[])
    for fork_url in agreeing:
        env = dict(os.environ, ETH_RPC_URL=fork_url, FORK_BLOCK=str(block), EXPECT_CHAIN_ID=str(cid))
        cmd = [sys.executable, "-I", str(ROOT / "toolchain" / "forge.py")] + (["--project", project] if project else []) + ["test", "--match-path", "test/fork/*", "--json", "-vv"]
        if fuzz_runs:
            cmd += ["--fuzz-runs", str(fuzz_runs)]
        t0 = time.time()
        p = subprocess.run(cmd, env=env, capture_output=True, text=True)
        dur = time.time() - t0
        raw = LOGS / (f"{project}-fork-{cid}.json" if project else f"fork-{cid}.json")
        raw.write_text(p.stdout + ("\n--- stderr ---\n" + p.stderr if p.stderr.strip() else ""), encoding="utf-8")
        attempt = dict(forkUrl=fork_url, exitCode=p.returncode, seconds=round(dur, 1), rawOutput=str(raw.relative_to(ROOT)).replace("\\", "/"))
        try:
            data = json.loads(p.stdout[p.stdout.index("{"):])
        except Exception:  # noqa: BLE001
            attempt["parseError"] = True
            rec["attempts"].append(attempt)
            continue
        tests = []
        for suite, s in data.items():
            for tname, tr in s.get("test_results", {}).items():
                tests.append(dict(suite=suite.split(":")[-1], test=tname, status=tr.get("status"), reason=tr.get("reason"),
                                  gas=gas_of(tr.get("kind", {}) or {}),
                                  fuzzRuns=(tr.get("kind", {}).get("Fuzz", {}) or {}).get("runs"),
                                  logs=tr.get("decoded_logs")))
        attempt["tests"] = sorted(tests, key=lambda t: (t["suite"], t["test"]))
        attempt["passed"] = sum(1 for t in tests if t["status"] == "Success")
        attempt["failed"] = sum(1 for t in tests if t["status"] == "Failure")
        attempt["skipped"] = sum(1 for t in tests if t["status"] == "Skipped")
        rec["attempts"].append(attempt)
        if p.returncode == 0 and attempt["failed"] == 0 and attempt["passed"] > 0:
            rec["result"] = "PASS"
            rec["usedAttempt"] = len(rec["attempts"]) - 1
            return rec
    rec["result"] = "FAIL"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", default="1,8453,42161")
    ap.add_argument("--back", type=int, default=64)
    ap.add_argument("--fuzz-runs", type=int, default=0)
    ap.add_argument("--project", default=None, help="run the fork tests of this project (contracts) instead of the Permit2 freeze tests of spec/foundry")
    a = ap.parse_args()
    out = ROOT / "evidence" / "implementation" / ("contracts-fork-runs.json" if a.project else "fork-runs.json")
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    results = []
    for cid in a.chains.split(","):
        c = pin["chains"][cid]
        print(f"chain {cid} {c['name']}: choosing the block and running the fork tests ...", flush=True)
        r = run_chain(cid, c["name"], c["providers"], a.back, a.fuzz_runs, a.project)
        used = r["attempts"][r.get("usedAttempt", -1)] if r["attempts"] else {}
        print(f"  block {r['block']} {r['blockHash']}: {r['result']}  passed {used.get('passed')} failed {used.get('failed')} skipped {used.get('skipped')}", flush=True)
        results.append(r)
    doc = dict(schema=1, tool="tools/fork_run.py", project=a.project or "foundry (reference model, Permit2 freeze tests)", forge=forge_version(), back=a.back, generatedAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               permit2=pin["address"], pinnedCommit=pin["pin"]["commit"], chains=results,
               verdict="PASS" if all(r["result"] == "PASS" for r in results) else "FAIL")
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("verdict", doc["verdict"], "->", out.relative_to(ROOT))
    return 0 if doc["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
