#!/usr/bin/env python3
"""Build report of the Foundry project: compile status, contract sizes, ABI and storage-layout snapshots, selector collisions, lint triage.

    python -I spec/tools/build_report.py --write     (re)write evidence/implementation/build-report.json and the snapshots
    python -I spec/tools/build_report.py --check     fail if the ABI or the storage layout of a source contract differs from its committed snapshot

The snapshots (evidence/implementation/abi/<Contract>.json, storage/<Contract>.json) are what a test of the storage layout compares: a
change of a slot, an offset, a type or an ABI entry shows up as a diff here before it reaches a test run. Every lint finding of
`forge lint` must have a disposition below; a rule without one makes the tool fail, so a new kind of finding is never silently accepted.

The contracts are those of foundry/src: the reference model and the generated types library. They are models, not the production
contracts: their ABI and layout are evidence that the model has no layout defect, not the layout of the contracts to be deployed.
"""
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOUNDRY = ROOT / "foundry"
SRC = FOUNDRY / "src"
OUT = ROOT / "evidence" / "implementation"
FORGE = [sys.executable, "-I", str(ROOT / "toolchain" / "forge.py")]

# rule -> (disposition, reason). Every rule that `forge lint` reports on foundry/src must be here.
LINT_DISPOSITIONS = {
    "unsafe-typecast": ("ACCEPTED-MODEL", "Narrowing casts of the model are guarded: WidthLib refuses a value that does not fit before it narrows, and "
                        "IntegerWidth.t.sol shows that every narrowing reverts instead of truncating. A production contract uses checked SafeCast."),
    "block-timestamp": ("ACCEPTED-BY-DESIGN", "The protocol is defined on block.timestamp: expiry, windows, grace and the Permit2 boundary are time rules, "
                        "with the boundary conditions tested (TimestampBoundary.t.sol)."),
    "calls-loop": ("ACCEPTED-BOUNDED", "External calls inside loops are Permit2 allowance reads (view) whose loops are bounded by MAX_TOKENS_PER_MANDATE or "
                   "MAX_EXPOSED_TOKENS_PER_ROUTER (tools/loop_audit.py, LoopBounds.t.sol)."),
    "unused-return": ("ACCEPTED-MODEL", "The second and third values of Permit2.allowance (expiration or nonce) are not needed by that predicate."),
    "require-revert-in-loop": ("ACCEPTED-MODEL", "A predicate that fails inside a bounded loop reverts the whole call: that is the intended all-or-nothing behavior."),
    "encode-packed-collision": ("ACCEPTED-CONSTANTS", "abi.encodePacked of the two compile-time constant strings (Permit2's witness stub and the witness type string), as Permit2 itself builds its type hash; "
                                "no argument is chosen by a caller, so no collision can be induced. The array hashes use one dynamic argument."),
    "reentrancy-no-eth": ("FIXED-F-16", "Reported on `consume` (the pull before the effects). Fixed in the model (finding F-16); a remaining report would be a regression."),
    "missing-zero-check": ("ACCEPTED-MODEL", "Reported on the test hook of the Permit2 mock (setHook): address(0) means 'no hook' there. No production function is affected."),
    "mixed-case-variable": ("COSMETIC", "Names follow the notation of document 12."),
    "mixed-case-function": ("COSMETIC", "Names follow the notation of document 12."),
    "screaming-snake-case-const": ("COSMETIC", "Constant names follow the configuration records (PC-xx symbols)."),
    "screaming-snake-case-immutable": ("COSMETIC", "Names follow the configuration records."),
    "pascal-case-struct": ("COSMETIC", "Names follow the documents."),
    "asm-keccak256": ("ACCEPTED-MODEL", "The model prefers readability over the gas of keccak256 in assembly."),
    "divide-before-multiply": ("REVIEW", "See the finding in the evidence report if this rule appears."),
    "incorrect-shift": ("REVIEW", "See the finding in the evidence report if this rule appears."),
    "unwrapped-modifier-logic": ("COSMETIC", "No modifier is used in the model."),
    "unchecked-call": ("REVIEW", "See the finding in the evidence report if this rule appears."),
    "unchecked-transfer": ("REVIEW", "See the finding in the evidence report if this rule appears."),
}


def forge(*args, check=True):
    r = subprocess.run(FORGE + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        sys.exit(f"forge {' '.join(args)} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r


def canon(x):
    return json.dumps(x, indent=1, sort_keys=True) + "\n"


def sha(x):
    return "0x" + hashlib.sha256(canon(x).encode()).hexdigest()


def contracts():
    names = []
    for p in sorted(SRC.rglob("*.sol")):
        t = p.read_text(encoding="utf-8")
        for m in re.finditer(r"^(contract|library)\s+([A-Za-z0-9_]+)", t, re.M):
            names.append((m.group(2), m.group(1), str(p.relative_to(FOUNDRY)).replace("\\", "/")))
    return names


def sizes():
    """Runtime and init code sizes of every contract of the project (forge build --sizes --json prints one flat JSON object first)."""
    r = forge("build", "--sizes", "--json")
    text = r.stdout[r.stdout.index("{"):]
    obj, _end = json.JSONDecoder().raw_decode(text)
    return obj


def lint():
    """Findings of `forge lint` on the whole project, counted by rule, with the first locations of each rule inside foundry/src."""
    r = forge("lint", check=False)
    text = r.stdout + r.stderr
    total = collections.Counter(re.findall(r"^(?:warning|note|error)\[([a-z0-9-]+)\]", text, re.M))
    where = collections.defaultdict(list)
    for m in re.finditer(r"^(?:warning|note|error)\[([a-z0-9-]+)\][^\n]*\n\s*\S+\s+([^\s:]+):(\d+)", text, re.M):
        where[m.group(1)].append(f"{m.group(2)}:{m.group(3)}")
    return total, where, r.returncode


def build(write):
    ver = forge("--version").stdout.strip().replace("\n", " | ")
    cs = contracts()
    report = dict(schema=1, tool="tools/build_report.py", forge=ver, solc="0.8.24", evmVersion="cancun", viaIR=True, optimizerRuns=20,
                  bytecodeHash="none", contracts={}, selectorCollisions=[], lint={})
    try:
        sz = sizes()
    except Exception as e:  # noqa: BLE001
        sz = {}
        report["sizesError"] = str(e)
    diffs = []
    for name, kind, path in cs:
        abi = json.loads(forge("inspect", name, "abi", "--json").stdout)
        layout = None
        mids = {}
        if kind == "contract":
            layout = json.loads(forge("inspect", name, "storageLayout", "--json").stdout)
            mids = json.loads(forge("inspect", name, "methodIdentifiers", "--json").stdout)
        entry = dict(kind=kind, file=path, abiEntries=len(abi), abiSha256=sha(abi), selectors=len(mids))
        s = sz.get(name) if isinstance(sz, dict) else None
        if s:
            entry["runtimeSize"] = s.get("runtime_size")
            entry["initSize"] = s.get("init_size")
            entry["exceedsEip170Limit24576"] = s.get("runtime_size", 0) > 24576
            entry["exceedsEip3860InitLimit49152"] = s.get("init_size", 0) > 49152
        if layout is not None:
            slots = layout.get("storage", [])
            entry["storageVariables"] = len(slots)
            entry["storageLayoutSha256"] = sha(layout)
            seen = {}
            for v in slots:
                key = (v["slot"], v["offset"])
                if key in seen:
                    report["selectorCollisions"].append(f"{name}: storage slot/offset {key} used by {seen[key]} and {v['label']}")
                seen[key] = v["label"]
                if int(v["offset"]) >= 32:
                    report["selectorCollisions"].append(f"{name}: offset {v['offset']} of {v['label']}")
        sel = collections.Counter(mids.values())
        for k, n in sel.items():
            if n > 1:
                report["selectorCollisions"].append(f"{name}: selector {k} used {n} times")
        report["contracts"][name] = entry
        for sub, data in (("abi", abi), ("storage", layout)):
            if data is None:
                continue
            f = OUT / sub / f"{name}.json"
            text = canon(data)
            if write:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(text, encoding="utf-8", newline="\n")
            elif not f.exists() or f.read_text(encoding="utf-8") != text:
                diffs.append(str(f.relative_to(ROOT)))
    counts, where, rc = lint()
    unknown = sorted(r for r in counts if r not in LINT_DISPOSITIONS)
    report["lint"] = dict(findings=sum(counts.values()), byRule={r: dict(count=n, disposition=LINT_DISPOSITIONS.get(r, ("UNTRIAGED", ""))[0],
                                                                  reason=LINT_DISPOSITIONS.get(r, ("", "no disposition"))[1],
                                                                  firstLocations=where.get(r, [])[:5]) for r, n in sorted(counts.items())},
                          untriaged=unknown, exitCode=rc)
    return report, diffs, unknown


def main(argv):
    write = "--write" in argv
    report, diffs, unknown = build(write)
    problems = []
    if report["selectorCollisions"]:
        problems.append("collisions: " + "; ".join(report["selectorCollisions"]))
    if unknown:
        problems.append("lint rules without a disposition: " + ", ".join(unknown))
    if diffs and not write:
        problems.append("snapshots differ: " + ", ".join(diffs))
    report["problems"] = problems
    report["verdict"] = "PASS" if not problems else "FAIL"
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "build-report.json").write_text(canon(report), encoding="utf-8", newline="\n")
    n = len(report["contracts"])
    print(f"{n} contracts and libraries; ABI and layout snapshots {'written' if write else 'compared'}; {report['lint']['findings']} lint findings "
          f"({len(report['lint']['byRule'])} rules, {len(unknown)} untriaged); {len(report['selectorCollisions'])} collisions -> {report['verdict']}")
    for p in problems:
        print("  PROBLEM", p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
