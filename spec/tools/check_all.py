#!/usr/bin/env python3
"""Run every consistency check of the specification workspace (revision 0.5).

Run:   python -I spec/tools/check_all.py

Checks
  1. identifier cross-references: every ID family that is referenced is defined somewhere (table first cell, heading, or range)
  2. relative markdown links resolve to files
  3. protocol vectors written into the documents equal the computed ones            (tools/sync_vectors.py --verify)
  4. freeze fingerprints recorded in document 14 equal the current text            (tools/freeze_fingerprints.py --verify)
  5. the backlog generator's own checks (profiles, program rule, attribution, schedule freshness)  (jira/build_backlog.py --check)
  6. executable model checks: Lemma M, clause necessity, no overlapping authority, the pin predicate, the shared-allowance and signer-set
     explorations, the AUTH truth table, mutation analysis of the exported vectors, atomicity  (tools/model_checks.py)
  7. the Foundry export (spec/foundry/vectors, src/Errors.sol, src/Mutants.sol, test/generated) is up to date  (tools/export_foundry.py --verify)
  8. structural lint of the Solidity files (nothing is compiled: there is no toolchain)                         (tools/solidity_lint.py)
  9. the configuration records (document 18) verify against config/pc_records.json and document 16             (tools/build_config_records.py --verify)
 10. the recorded Permit2 pin is internally consistent (`permit2_pin_check.py --online` re-reads the chains)     (tools/permit2_pin_check.py)
 11. no document claims a freeze approval while freeze_readiness.py says NOT READY                               (tools/freeze_readiness.py --lint)
 12. the EIP-712 artifacts (Solidity library, golden test, TypeScript types, vectors, wallet payloads) are generated from
     eip712/types.json and current; the Python encoder reproduces the documents' quote and pin vectors            (tools/export_eip712.py --check)
 13. the TypeScript implementation reproduces every golden vector (needs Node 22.18 or later)                      (eip712/test-eip712.ts)
 14. the Permit2 fixtures of the Foundry tests are exactly the rebuilt code recorded in evidence/permit2           (tools/export_permit2_fixtures.py --check)
 15. every loop of foundry/src is annotated with its bound and no unbounded loop is reachable from a state change (tools/loop_audit.py)
 16. the wallet-lab signature verifier detects every tampering of a synthetic record                              (tools/wallet_lab_verify.py --selftest)
 17. findings and report: the generated implementation report is current and every finding is well formed        (tools/impl_report.py --check)
 18. the actual contracts (contracts/): frozen settings equal foundry.toml, every runtime at most 22,000 bytes and the same bytes as forge's
     build, no DELEGATECALL, CALLCODE, SELFDESTRUCT, ORIGIN, CREATE or CREATE2, low-level calls on the allow-list     (tools/contracts_report.py --check)
 19. every loop of contracts/src is annotated and bounded, calls through interfaces followed                           (tools/loop_audit.py --project contracts)
 20. the recorded test run of the contracts is consistent with its raw log and has no failure                          (tools/contracts_tests.py --check)
 21. the cross-language EIP-712 record is for the current types and golden vectors and every implementation agreed      (tools/eip712_crosscheck.py --check)
Exit code 1 if any check fails. Fingerprints are expected to differ while documents are being edited: rerun
`freeze_fingerprints.py --write` once the text is final.
"""
import collections
import pathlib
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC = pathlib.Path(__file__).resolve().parent.parent
PY = [sys.executable, "-I"]

FAMILIES = (r"ADR-\d{3}|RG-\d{3}|PB-\d{3}|OD-\d{3}|ASM-\d{3}|CF-\d{3}|RISK-\d{3}|CLM-\d{3}|EV-P\d{2}|EV-\d{3}|RP-\d{2}|TM-\d{2}|TB-\d{2}|SRC-\d{3}|RB-\d{3}"
            r"|Q-\d{2}|TV-PO-\d{1,2}|MIG-TV-\d{2}|CAP-TV-\d{2}|ACP-TV-\d{2}|TV-\d{2}|SV-\d{2}|NC-\d{2}|DRV-\d{2}|G-\d{2}"
            r"|RV-T\d{2}|ZP-T\d{2}|WL-\d{2}|EVL-\d{2}|PC-\d{2}|UD-\d{2}|UX-\d{2}|DEC-\d{2}|FZ-\d{2}|FG-\d{2}|PR-\d{2}"
            r"|I-(?:MIG-\d|[A-Z]+(?:-[A-Z0-9]+)*)")
ID = re.compile(r"(?<![A-Za-z0-9])(" + FAMILIES + r")(?![A-Za-z0-9])")
RANGE = re.compile(r"((?:ADR|PB|OD|ASM|CF|RISK|CLM|RP|TM|TB|SRC|RB|TV|SV|NC|EV-P|DRV|G|MIG-TV|CAP-TV|ACP-TV|TV-PO|I-MIG|RV-T|ZP-T|WL|EVL|PC|UD|UX|DEC|FZ|FG|PR)-?)(\d+)\s*(?:…|\.\.\.?)\s*(?:[A-Z]+-)?(?:[A-Z]+-)?(?:T)?(\d+)")
IGNORE = re.compile(r"^(G-\d|DRV-0[0-9]b|WL-\d{2}b)")      # prose-defined or lettered variants


def check_ids():
    files = sorted(SPEC.glob("*.md"))
    defined, refs = set(), collections.defaultdict(set)
    for f in files:
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("|"):
                cells = line.split("|")
                first = cells[1] if len(cells) > 2 else ""
                defined.update(ID.findall(first))
            h = re.match(r"^#{2,4}\s+(.*)", line)
            if h:
                defined.update(ID.findall(h.group(1)))
            for x in ID.findall(line):
                refs[x].add(f.name)
        for a, b, c in RANGE.findall(text):
            w = len(b)
            for n in range(int(b), int(c) + 1):
                defined.add(f"{a}{n:0{w}d}")
                defined.add(f"{a}{n}")
    # EV-P ranges are written EV-P07…P11; DRV-15a style lettered rows define their base
    missing = sorted((k, sorted(v)) for k, v in refs.items() if k not in defined and not IGNORE.match(k))
    stale = []
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bI-CAP\b(?!-)", line):
                stale.append(f"{f.name}:{i}")
    return missing, stale, len(defined), len(refs)


def check_links():
    bad = []
    for md in sorted(SPEC.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", text):
            tgt = m.group(1)
            if tgt.startswith("http"):
                continue
            if not (SPEC / tgt).exists():
                bad.append((md.name, tgt))
    return sorted(set(bad))


def run(args):
    r = subprocess.run(PY + args, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(SPEC))
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    failed = []
    missing, stale, nd, nr = check_ids()
    print(f"[1] identifiers: {nd} defined, {nr} referenced")
    for k, v in missing:
        print("    UNDEFINED", k, v)
    for s in stale:
        print("    STALE I-CAP", s)
    if missing or stale:
        failed.append("identifiers")
    bad = check_links()
    print(f"[2] links: {'ok' if not bad else bad}")
    if bad:
        failed.append("links")
    for label, args in (("[3] vectors", ["tools/sync_vectors.py", "--verify"]), ("[4] fingerprints", ["tools/freeze_fingerprints.py", "--verify"]),
                        ("[5] backlog", ["jira/build_backlog.py", "--check"]),
                        ("[6] model checks", ["tools/model_checks.py", "--trials", "20000"]),
                        ("[7] foundry export", ["tools/export_foundry.py", "--verify"]),
                        ("[8] solidity lint", ["tools/solidity_lint.py"]),
                        ("[9] configuration records", ["tools/build_config_records.py", "--verify"]),
                        ("[10] permit2 pin record", ["tools/permit2_pin_check.py"]),
                        ("[11] freeze-readiness lint", ["tools/freeze_readiness.py", "--lint"]),
                        ("[12] eip712 artifacts", ["tools/export_eip712.py", "--check"]),
                        ("[14] permit2 fixtures", ["tools/export_permit2_fixtures.py", "--check"]),
                        ("[15] loop audit", ["tools/loop_audit.py"]),
                        ("[16] wallet-lab verifier", ["tools/wallet_lab_verify.py", "--selftest"]),
                        ("[17] implementation report", ["tools/impl_report.py", "--check"]),
                        ("[18] contracts report", ["tools/contracts_report.py", "--check"]),
                        ("[19] contracts loop audit", ["tools/loop_audit.py", "--project", "contracts"]),
                        ("[20] contracts test run", ["tools/contracts_tests.py", "--check"]),
                        ("[21] eip712 cross-language record", ["tools/eip712_crosscheck.py", "--check"])):
        code, out = run(args)
        last = out.splitlines()[-1] if out else ""
        print(f"{label}: {'ok' if code == 0 else 'FAILED'} - {last}")
        if code:
            print("    " + out.replace("\n", "\n    ")[:1500])
            failed.append(label)
    node = subprocess.run(["node", "--experimental-strip-types", "eip712/test-eip712.ts"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(SPEC))
    print(f"[13] eip712 TypeScript: {'ok' if node.returncode == 0 else 'FAILED'} - {(node.stdout + node.stderr).strip().splitlines()[-1] if (node.stdout + node.stderr).strip() else ''}")
    if node.returncode:
        failed.append("[13] eip712 TypeScript")
    print("ALL CHECKS PASSED" if not failed else "FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
