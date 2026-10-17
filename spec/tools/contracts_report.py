#!/usr/bin/env python3
"""Static evidence about the ACTUAL FastPay contracts (I:\\CryptoGateway\\contracts), separate from the reference model.

    python -I spec/tools/contracts_report.py            write evidence/implementation/contracts-report.json and print the verdict
    python -I spec/tools/contracts_report.py --check    exit 1 unless the report on disk is current and the verdict is PASS

What it checks, and how:
  [1] SETTINGS   contracts/foundry.toml equals contracts/frozen-settings.json: solc 0.8.24, evm cancun, no via-IR, optimizer on with 200 runs,
                 no bytecode hash and no CBOR metadata, no code-size-limit override. A runtime that does not fit is split, never tuned.
  [2] SIZES      the runtime size of every deployable contract, from solc compiled here with the frozen settings, must be at most 22,000 bytes
                 (the target of this revision) and, necessarily, under the 24,576 bytes of EIP-170. The same bytecode must be the one that forge
                 built (the keccak of the runtime code of every artifact in contracts/out equals the one compiled here).
  [3] OPCODES    the disassembly of every runtime (the code instructions only: the trailing data section is cut with the help of the source map) must contain no DELEGATECALL,
                 CALLCODE, SELFDESTRUCT, ORIGIN, CREATE or CREATE2. (There is no generic delegatecall, no tx.origin, and no contract creates contracts.)
  [4] LOWCALLS   every low-level call in the sources (the address members call, staticcall, delegatecall, callcode, send, transfer; every Yul call
                 instruction) must be on the allow-list below, with its reason. The only one is the ERC-1271 STATICCALL to the customer's account.
  [5] TARGETS    the typed external calls of every contract are listed (I-EXTCALL): which contract types it can call. A target outside the fixed
                 set of the system, Permit2 and the token interface fails.
  [6] LOOPS      the loop audit of the contracts (tools/loop_audit.py --project contracts) has no problem.
  [7] SELECTORS  the external functions and their selectors, per contract (the ABI that the report of the tests refers to).
This is a static check of the code that was compiled. It is not an audit and it does not say that the contracts are correct.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = ROOT.parent / "contracts"
SRC = CONTRACTS / "src"
OUTDIR = CONTRACTS / "out"
SOLC = ROOT / "toolchain" / "solc" / "solc-0.8.24.exe"
FROZEN = CONTRACTS / "frozen-settings.json"
LOOPS = ROOT / "evidence" / "implementation" / "loop-audit-contracts.json"
REPORT = ROOT / "evidence" / "implementation" / "contracts-report.json"

FORBIDDEN_OPCODES = ("DELEGATECALL", "CALLCODE", "SELFDESTRUCT", "ORIGIN", "CREATE", "CREATE2")
LOW_LEVEL_MEMBERS = ("call", "delegatecall", "staticcall", "callcode", "send", "transfer")
LOW_LEVEL_YUL = ("call", "delegatecall", "staticcall", "callcode", "create", "create2", "selfdestruct", "origin")
# the only low-level instructions allowed: (file, instruction, reason)
ALLOWED_LOW_LEVEL = {
    ("lib/AuthLib.sol", "staticcall"): "ERC-1271 isValidSignature of the customer's account by STATICCALL with no artificial gas cap (CLM-032): the target is the "
                                       "account that the signature claims, the calldata is the fixed selector with the digest and the signature, only one return word is read",
}
# the contract types that a typed external call may reach (the fixed set of the system); everything else fails
ALLOWED_TARGETS = {"IRouterRegistry", "ISignerSetRegistry", "ITokenPolicyRegistry", "IMerchantRegistry", "IExecutorRegistry", "IFeeController",
                   "IMandateManager", "ISuccessorValidator", "IAllowanceTransfer", "ISignatureTransfer", "IERC20", "UsageLedger", "ContainHarness"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def compile_all(settings):
    files = sorted(p for p in SRC.rglob("*.sol"))
    inp = {"language": "Solidity",
           "sources": {str(p.relative_to(SRC)).replace("\\", "/"): {"content": p.read_text(encoding="utf-8")} for p in files},
           "settings": {"evmVersion": settings["evmVersion"], "viaIR": settings["viaIR"],
                        "optimizer": {"enabled": settings["optimizer"]["enabled"], "runs": settings["optimizer"]["runs"]},
                        "metadata": {"bytecodeHash": settings["metadata"]["bytecodeHash"], "appendCBOR": settings["metadata"]["appendCBOR"]},
                        "outputSelection": {"*": {"": ["ast"], "*": ["abi", "evm.deployedBytecode.object", "evm.deployedBytecode.opcodes", "evm.deployedBytecode.sourceMap",
                                                                       "evm.methodIdentifiers"]}}}}
    r = subprocess.run([str(SOLC), "--standard-json"], input=json.dumps(inp), capture_output=True, text=True, check=False)
    out = json.loads(r.stdout)
    errs = [e for e in out.get("errors", []) if e["severity"] == "error"]
    if errs:
        sys.exit("solc: " + errs[0]["formattedMessage"])
    return out, inp["sources"]


def check_settings():
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    toml = tomllib.loads((CONTRACTS / "foundry.toml").read_text(encoding="utf-8"))["profile"]["default"]
    got = {"solc": toml.get("solc_version"), "evmVersion": toml.get("evm_version"), "viaIR": toml.get("via_ir"),
           "optimizer": {"enabled": toml.get("optimizer"), "runs": toml.get("optimizer_runs")},
           "metadata": {"bytecodeHash": toml.get("bytecode_hash"), "appendCBOR": toml.get("cbor_metadata")}}
    want = {k: frozen[k] for k in got}
    problems = []
    for k in want:
        if want[k] != got[k]:
            problems.append(f"foundry.toml {k} = {got[k]!r} but frozen-settings.json says {want[k]!r}")
    if "code_size_limit" in toml:
        problems.append("foundry.toml sets code_size_limit: the EIP-170 limit must apply to every deployment of the tests too")
    return frozen, got, problems


def walk(n, fn):
    if isinstance(n, dict):
        fn(n)
        for v in n.values():
            walk(v, fn)
    elif isinstance(n, list):
        for v in n:
            walk(v, fn)


def scan_ast(out, texts):
    low, targets, selectors = [], {}, {}

    def line_of(path, src):
        return texts[path]["content"].count("\n", 0, int(src.split(":")[0])) + 1

    for path, su in out["sources"].items():
        for node in su["ast"]["nodes"]:
            if node["nodeType"] != "ContractDefinition" or node["contractKind"] not in ("contract", "library"):
                continue
            cname = node["name"]
            tset = targets.setdefault(cname, set())

            def visit(n, path=path, cname=cname, tset=tset):
                nt = n.get("nodeType")
                if nt == "FunctionCall" and n.get("kind") == "functionCall":
                    e = n.get("expression", {})
                    if e.get("nodeType") == "MemberAccess":
                        member = e.get("memberName")
                        base_t = (e.get("expression", {}).get("typeDescriptions", {}) or {}).get("typeString", "") or ""
                        if member in LOW_LEVEL_MEMBERS and base_t.startswith("address"):
                            low.append(dict(file=path, line=line_of(path, n["src"]), contract=cname, instruction=member, kind="address member"))
                        elif base_t.startswith("contract ") or base_t.startswith("contract(") or base_t.startswith("type(contract"):
                            m = re.match(r"contract ([A-Za-z0-9_]+)", base_t)
                            if m and node["contractKind"] == "contract":
                                tset.add(m.group(1))
                if nt == "YulFunctionCall":
                    name = (n.get("functionName") or {}).get("name")
                    if name in LOW_LEVEL_YUL:
                        low.append(dict(file=path, line=line_of(path, n["src"]), contract=cname, instruction=name, kind="yul"))
            walk(node, visit)
            for fn in node["nodes"]:
                if fn["nodeType"] == "FunctionDefinition" and fn["visibility"] in ("external", "public") and fn.get("functionSelector"):
                    sig = fn["name"] + "(" + ",".join(p["typeDescriptions"]["typeString"] for p in fn["parameters"]["parameters"]) + ")"
                    selectors.setdefault(cname, []).append(dict(function=fn["name"], selector="0x" + fn["functionSelector"], mutability=fn["stateMutability"],
                                                              typeStrings=sig))
    return low, {k: sorted(v) for k, v in targets.items()}, selectors


def build():
    frozen, got, problems = check_settings()
    out, texts = compile_all(frozen)
    report = {"schema": 1, "tool": "tools/contracts_report.py", "solc": frozen["solc"], "settings": got, "frozenSettings": frozen["name"] if "name" in frozen else "contracts/frozen-settings.json",
              "settingsFrozenFileSha256": sha(FROZEN.read_bytes()), "sourcesSha256": {}, "contracts": {}, "problems": problems}
    for p in sorted(SRC.rglob("*.sol")):
        report["sourcesSha256"][str(p.relative_to(CONTRACTS)).replace("\\", "/")] = sha(p.read_bytes())
    target, eip170 = frozen["runtimeSizeTargetBytes"], frozen["eip170Bytes"]
    deployable = {}
    for path, cs in out["contracts"].items():
        for cname, c in cs.items():
            obj = c["evm"]["deployedBytecode"]["object"]
            if not obj:
                continue
            deployable[cname] = (path, c)
    for cname, (path, c) in sorted(deployable.items()):
        code = bytes.fromhex(c["evm"]["deployedBytecode"]["object"])
        # the disassembly lists the code and then the data section (type strings and other constants copied by CODECOPY), whose bytes look like
        # opcodes ('2' is ORIGIN): the source map has one entry per CODE instruction, so only that many instructions are scanned
        dep = c["evm"]["deployedBytecode"]
        instr = [t for t in dep["opcodes"].split() if not t.startswith("0x")]
        ops = instr[:len(dep["sourceMap"].split(";"))]
        counts = {op: ops.count(op) for op in FORBIDDEN_OPCODES}
        art = OUTDIR / f"{pathlib.PurePosixPath(path).name}" / f"{cname}.json"
        forge_hash = None
        if art.exists():
            d = json.loads(art.read_text(encoding="utf-8"))
            fb = d.get("deployedBytecode", {}).get("object", "")
            forge_hash = hashlib.sha256(bytes.fromhex(fb[2:] if fb.startswith("0x") else fb)).hexdigest() if fb else None
        entry = {"file": f"src/{path}", "runtimeBytes": len(code), "marginToTarget": target - len(code), "marginToEip170": eip170 - len(code),
                 "runtimeSha256": sha(code), "forgeRuntimeSha256": forge_hash, "sameAsForge": (forge_hash == sha(code)) if forge_hash else None,
                 "codeInstructions": len(ops), "dataInstructionsSkipped": len(instr) - len(ops),
                 "forbiddenOpcodes": counts, "calls": ops.count("CALL"), "staticcalls": ops.count("STATICCALL")}
        report["contracts"][cname] = entry
        if len(code) > target:
            problems.append(f"{cname}: runtime {len(code)} bytes exceeds the target of {target}")
        if len(code) >= eip170:
            problems.append(f"{cname}: runtime {len(code)} bytes reaches EIP-170 ({eip170})")
        for op, n in counts.items():
            if n:
                problems.append(f"{cname}: the runtime contains {n} {op} instruction(s)")
        if forge_hash is not None and forge_hash != sha(code):
            problems.append(f"{cname}: the runtime that forge built differs from the one compiled here with the frozen settings (stale build or other settings)")
    low, targets, selectors = scan_ast(out, texts)
    seen_low = []
    for item in low:
        key = (item["file"], item["instruction"])
        item["allowed"] = key in ALLOWED_LOW_LEVEL
        item["reason"] = ALLOWED_LOW_LEVEL.get(key)
        seen_low.append(item)
        if not item["allowed"]:
            problems.append(f"{item['file']}:{item['line']}: low-level {item['instruction']} is not on the allow-list")
    report["lowLevelCalls"] = seen_low
    for cname, tset in targets.items():
        bad = [t for t in tset if t not in ALLOWED_TARGETS and t != cname and t not in deployable]
        if cname in report["contracts"]:
            report["contracts"][cname]["externalCallTargets"] = [t for t in tset]
        if bad:
            problems.append(f"{cname}: calls a contract type outside the fixed set: {bad}")
    for cname, sel in selectors.items():
        if cname in report["contracts"]:
            report["contracts"][cname]["externalFunctions"] = sorted(sel, key=lambda x: x["function"])
    if LOOPS.exists():
        la = json.loads(LOOPS.read_text(encoding="utf-8"))
        report["loopAudit"] = {"file": str(LOOPS.relative_to(ROOT)), "loops": len(la["loops"]), "verdict": la["verdict"], "problems": la["problems"]}
        if la["verdict"] != "PASS":
            problems.append("the loop audit of the contracts fails")
    else:
        problems.append("evidence/implementation/loop-audit-contracts.json is missing: run tools/loop_audit.py --project contracts")
    report["problems"] = problems
    report["verdict"] = "PASS" if not problems else "FAIL"
    return report


def main(argv):
    report = build()
    text = json.dumps(report, indent=1, sort_keys=False) + "\n"
    if "--check" in argv:
        cur = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
        if cur != text:
            print("contracts report: STALE (run python -I spec/tools/contracts_report.py)")
            return 1
        print(f"contracts report: current, verdict {report['verdict']}")
        return 0 if report["verdict"] == "PASS" else 1
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{'contract':<22}{'runtime B':>10}{'to target':>11}{'to EIP-170':>12}  same as forge")
    for n, e in report["contracts"].items():
        print(f"{n:<22}{e['runtimeBytes']:>10}{e['marginToTarget']:>11}{e['marginToEip170']:>12}  {e['sameAsForge']}")
    for item in report["lowLevelCalls"]:
        print(f"  low-level {item['instruction']} at {item['file']}:{item['line']} allowed={item['allowed']}")
    for p in report["problems"]:
        print("  PROBLEM", p)
    print(f"contracts report: {report['verdict']} -> {REPORT.relative_to(ROOT)}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
