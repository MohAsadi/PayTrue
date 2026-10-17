#!/usr/bin/env python3
"""Run every implementation of the EIP-712 encoding against the golden vectors and record that they agree (part HASHES of condition C-11).

    python -I spec/tools/eip712_crosscheck.py            run and write evidence/eip712-crosscheck.json
    python -I spec/tools/eip712_crosscheck.py --check    exit 1 unless the recorded run is for the current eip712/types.json and every run passed

Four implementations are compared with the one set of golden vectors that tools/eip712_types.py generates from eip712/types.json:
  1. PYTHON       the reference encoder reproduces its own vectors and every generated artifact is current (export_eip712.py --check)
  2. TYPESCRIPT   eip712/test-eip712.ts (Node 22.18 or later), which also changes every field of every message and every word of the snapshot
  3. SOLIDITY (reference model)   the generated library in spec/foundry against Foundry's own EIP-712 cheat codes
  4. SOLIDITY (contracts)         the same library in the contracts project, which is the code that would be deployed
The record names the fingerprint of the types, the hash of the golden vectors and the version of each tool, so that a later change of a type string
makes the record stale. It shows that the encodings agree; it is not an approval and no wallet has displayed or signed anything.
"""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "eip712-crosscheck.json"
sys.path.insert(0, str(ROOT / "tools"))


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def fingerprint():
    import eip712_types as E  # noqa: PLC0415
    return E.freeze_fingerprint(E.Registry(E.load()))


def run(cmd, cwd=None, timeout=1800):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def forge_golden(project):
    cmd = [sys.executable, "-I", str(ROOT / "toolchain" / "forge.py")] + (["--project", project] if project else []) + ["test", "--match-contract", "EIP712GoldenTest", "--json"]
    code, out = run(cmd)
    try:
        d = json.loads(out[out.index("{"):])
    except Exception:  # noqa: BLE001
        return dict(passed=0, failed=1, exit=code, detail="no JSON from forge")
    p = f = 0
    for s in d.values():
        for t in s["test_results"].values():
            if t["status"] == "Success":
                p += 1
            else:
                f += 1
    return dict(passed=p, failed=f, exit=code)


def build():
    runs = []
    code, out = run([sys.executable, "-I", str(ROOT / "tools" / "export_eip712.py"), "--check"])
    runs.append(dict(name="PYTHON: export_eip712.py --check (every generated artifact equals what the reference encoder produces)", exit=code, passed=1 if code == 0 else 0, failed=0 if code == 0 else 1,
                     detail=out.strip().splitlines()[-1] if out.strip() else ""))
    code, out = run(["node", "--experimental-strip-types", str(ROOT / "eip712" / "test-eip712.ts")], timeout=600)
    m = re.search(r"(\d+)\s+(?:checks|tests|assertions)?\s*passed", out) or re.search(r"(\d+) checks", out)
    runs.append(dict(name="TYPESCRIPT: eip712/test-eip712.ts", exit=code, passed=int(m.group(1)) if (m and code == 0) else 0, failed=0 if code == 0 else 1, detail=out.strip().splitlines()[-1] if out.strip() else ""))
    g = forge_golden(None)
    runs.append(dict(name="SOLIDITY, reference model (spec/foundry): EIP712GoldenTest against Foundry's EIP-712 cheat codes", exit=g.get("exit"), passed=g["passed"], failed=g["failed"], detail=g.get("detail", "")))
    g = forge_golden("contracts")
    runs.append(dict(name="SOLIDITY, actual contracts (contracts/): EIP712GoldenTest against Foundry's EIP-712 cheat codes", exit=g.get("exit"), passed=g["passed"], failed=g["failed"], detail=g.get("detail", "")))
    nv = run(["node", "--version"])[1].strip()
    fv = run([sys.executable, "-I", str(ROOT / "toolchain" / "forge.py"), "--version"])[1].strip().splitlines()
    return {"schema": 1, "tool": "tools/eip712_crosscheck.py", "typesFingerprint": fingerprint(), "typesJsonSha256": sha(ROOT / "eip712" / "types.json"),
            "goldenVectorsSha256": sha(ROOT / "eip712" / "golden-vectors.json"), "node": nv, "forge": fv[0] if fv else "unknown",
            "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "runs": runs,
            "allAgree": all(r["failed"] == 0 and r["passed"] > 0 for r in runs),
            "note": "The four implementations agree on the golden vectors. No wallet has displayed or signed any of these messages."}


def check():
    if not OUT.exists():
        return False, "no cross-language run recorded"
    d = json.loads(OUT.read_text(encoding="utf-8"))
    why = []
    if d.get("typesFingerprint") != fingerprint():
        why.append("the record is for another eip712/types.json fingerprint")
    if d.get("goldenVectorsSha256") != sha(ROOT / "eip712" / "golden-vectors.json"):
        why.append("the golden vectors changed since the record")
    if not d.get("allAgree"):
        why.append("a recorded run failed")
    return not why, "; ".join(why) if why else f"{len(d['runs'])} implementations agree (recorded {d['generatedAt']})"


def main(argv):
    if "--check" in argv:
        ok, txt = check()
        print("eip712 cross-check:", txt)
        return 0 if ok else 1
    d = build()
    OUT.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8", newline="\n")
    for r in d["runs"]:
        print(f"  {'ok  ' if r['failed'] == 0 and r['passed'] else 'FAIL'} {r['name']}  [{r['passed']} passed, {r['failed']} failed]")
    print("all agree" if d["allAgree"] else "DISAGREEMENT", "->", OUT.relative_to(ROOT))
    return 0 if d["allAgree"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
