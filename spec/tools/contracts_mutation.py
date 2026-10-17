#!/usr/bin/env python3
"""Mutation testing of the ACTUAL FastPay contracts: does the test suite of contracts/test notice each deliberate bug?

    python -I spec/tools/contracts_mutation.py --patterns        check that every mutant's text occurs exactly once (no forge run)
    python -I spec/tools/contracts_mutation.py [--only MM,SV]    run the mutants (ids or id prefixes); writes evidence/implementation/contracts-mutation.json
    python -I spec/tools/contracts_mutation.py --report          print the recorded result

A copy of the contracts project (contracts_mut, next to contracts and spec so that the relative remappings and read permissions of foundry.toml hold) is
mutated one change at a time; `forge test` (all suites except the gas measurements, the stateful fuzz and the fiat vectors, which are slow and
are run in the full suite) must FAIL for the mutant to count as killed. A mutant that does not compile is INVALID and is reported, not counted. A mutant
that survives is a gap in the tests or an equivalent mutant: contracts_mutants.EQUIVALENT lists the equivalent ones with their reason, and the exit
code is 0 only if every survivor is listed there.

This is evidence about the tests, not about the contracts: a high kill rate means that the tests are sensitive to these bugs, not that no other bug exists.
"""
import datetime
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
CONTRACTS = ROOT.parent / "contracts"
WORK = ROOT.parent / "contracts_mut"
OUT = ROOT / "evidence" / "implementation" / "contracts-mutation.json"
FORGE = TOOLS.parent / "toolchain" / "forge.py"
SKIP = "GasTest|InvariantsTest|FiatVectorsTest|Fork"


def load_mutants():
    spec = importlib.util.spec_from_file_location("contracts_mutants", TOOLS / "contracts_mutants.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fresh_copy():
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(CONTRACTS, WORK, ignore=shutil.ignore_patterns("out", "cache", "broadcast"))


def forge(*args, timeout=1500):
    r = subprocess.run([sys.executable, "-I", str(FORGE), "--project", "contracts_mut", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def check_patterns(mod):
    problems = []
    texts = {}
    seen = set()
    for mid, file, old, new, desc in mod.M:
        if mid in seen:
            problems.append(f"{mid}: duplicate id")
        seen.add(mid)
        p = CONTRACTS / "src" / file
        if file not in texts:
            texts[file] = p.read_text(encoding="utf-8")
        n = texts[file].count(old) if old else 0
        if n != 1:
            problems.append(f"{mid} ({file}): the text to replace occurs {n} times: {old[:80]!r}")
        if old == new:
            problems.append(f"{mid}: no change")
    return problems


def selected(mod, only):
    if not only:
        return mod.M
    keys = [k.strip() for k in only.split(",") if k.strip()]
    return [m for m in mod.M if any(m[0] == k or m[0].startswith(k) for k in keys)]


def run(mod, only):
    probs = check_patterns(mod)
    if probs:
        print("\n".join(probs))
        return 2
    fresh_copy()
    code, out = forge("build")
    if code != 0:
        print(out[-2000:])
        return 2
    # the pristine copy must pass, or a "kill" means nothing
    t0 = time.time()
    code, out = forge("test", "--no-match-contract", SKIP)
    if code != 0:
        print("the unmutated contracts fail their tests:\n" + out[-3000:])
        return 2
    base_seconds = round(time.time() - t0, 1)
    # with --only the other results of the last full campaign are kept, and the ones that are run again replace theirs (a campaign of 249 mutants takes an hour)
    order = [m[0] for m in mod.M]
    results = []
    if only and OUT.exists():
        results = [r for r in json.loads(OUT.read_text(encoding="utf-8"))["results"] if r["id"] in order]
    for mid, file, old, new, desc in selected(mod, only):
        path = WORK / "src" / file
        pristine = path.read_text(encoding="utf-8")
        path.write_text(pristine.replace(old, new), encoding="utf-8", newline="")
        t0 = time.time()
        try:
            code, out = forge("test", "--no-match-contract", SKIP, "--fail-fast")
        except subprocess.TimeoutExpired:
            code, out = 99, "timeout"
        finally:
            path.write_text(pristine, encoding="utf-8", newline="")
        secs = round(time.time() - t0, 1)
        if "Compiler run failed" in out or "Error: Compiler" in out:
            status, by = "INVALID", None
            first = next((ln for ln in out.splitlines() if "Error" in ln), "")
        elif code == 0:
            status, by, first = "SURVIVED", None, ""
        else:
            status = "KILLED"
            m = re.search(r"\[FAIL[^\n]*?\]\s+(\S+\(.*?\))", out) or re.search(r"\[FAIL[^\n]*", out)
            by = m.group(1) if m and m.groups() else (m.group(0)[:120] if m else "a failing test")
            first = ""
        results = [r for r in results if r["id"] != mid]
        results.append(dict(id=mid, file=f"src/{file}", description=desc, status=status, killedBy=by, seconds=secs, note=first[:200]))
        results.sort(key=lambda r: order.index(r["id"]))
        print(f"{mid:<6} {status:<9} {secs:>6}s  {desc[:70]}  {('<- ' + str(by)[:60]) if by else ''}", flush=True)
        write(mod, results, base_seconds)
    write(mod, results, base_seconds)
    return summarize(mod, results)


def write(mod, results, base_seconds):
    killed = sum(r["status"] == "KILLED" for r in results)
    survived = [r for r in results if r["status"] == "SURVIVED"]
    invalid = [r for r in results if r["status"] == "INVALID"]
    doc = dict(schema=1, tool="tools/contracts_mutation.py", generatedAt=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               suite="forge test of contracts/test except " + SKIP, baselineSeconds=base_seconds,
               counts=dict(mutants=len(results), killed=killed, survived=len(survived), invalid=len(invalid)),
               equivalent={k: v for k, v in mod.EQUIVALENT.items()}, results=results)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")


def summarize(mod, results):
    killed = sum(r["status"] == "KILLED" for r in results)
    surv = [r for r in results if r["status"] == "SURVIVED"]
    inv = [r for r in results if r["status"] == "INVALID"]
    unexplained = [r for r in surv if r["id"] not in mod.EQUIVALENT]
    print(f"{len(results)} mutants: {killed} killed, {len(surv)} survived ({len(surv) - len(unexplained)} equivalent), {len(inv)} invalid")
    for r in unexplained:
        print("  SURVIVOR", r["id"], r["description"])
    for r in inv:
        print("  INVALID ", r["id"], r["note"])
    return 1 if (unexplained or inv) else 0


def main(argv):
    mod = load_mutants()
    if "--patterns" in argv:
        probs = check_patterns(mod)
        print(f"{len(mod.M)} mutants")
        for p in probs:
            print("  PROBLEM", p)
        return 1 if probs else 0
    if "--report" in argv:
        d = json.loads(OUT.read_text(encoding="utf-8"))
        print(json.dumps(d["counts"]))
        for r in d["results"]:
            if r["status"] != "KILLED":
                print(" ", r["id"], r["status"], r["description"])
        return 0
    only = argv[argv.index("--only") + 1] if "--only" in argv else ""
    return run(mod, only)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
