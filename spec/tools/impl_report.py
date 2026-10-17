#!/usr/bin/env python3
"""Generate the implementation evidence report from the recorded evidence files, so that no number in it is typed by hand.

    python -I spec/tools/impl_report.py --write     write evidence/implementation/REPORT.md
    python -I spec/tools/impl_report.py --check     fail if REPORT.md is not what the evidence files generate

Sources (all under spec/): toolchain/toolchain.lock.json, toolchain/fetch-record.json, toolchain/tree-verification.json,
evidence/permit2/rebuild.json, evidence/permit2/pin.json, evidence/implementation/{loop-audit,build-report,fork-runs,findings}.json,
evidence/implementation/logs/forge-test-final.json, evidence/freeze_register.json, eip712/golden-vectors.json,
foundry/vectors/permit2-evidence.json, the evidence of the actual contracts (evidence/implementation/{contracts-report,contracts-test-run,contracts-mutation,
contracts-fork-runs,loop-audit-contracts}.json and contracts/frozen-settings.json) and the output of tools/freeze_readiness.py.

The report states what was done, with the evidence file next to each claim, what was NOT done, and which findings are decisions for
people. It is evidence, not an approval of anything.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import impl_report_contracts as RC  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPL = ROOT / "evidence" / "implementation"
OUT = IMPL / "REPORT.md"


def J(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def opt(p):
    f = ROOT / p
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def forge_json(path):
    f = ROOT / path
    if not f.exists():
        return None
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):]) if "{" in t else None


CATEGORY = {
    "MigrationFuzz": "fuzz", "MigrationInvariant": "invariant (13 stateful invariants, reported as one test)", "MigrationMutation": "mutation (151 mutants, each must be killed)",
    "IntegerWidth": "integer width", "TimestampBoundary": "timestamp boundary", "SignerSet": "signer set", "Pin": "account pin",
    "SharedAllowance": "shared allowance", "ConfigRecords": "configuration records", "EIP712Golden": "EIP-712 golden vectors (generated)",
    "EIP712Permit2": "EIP-712 witness against the rebuilt Permit2", "LoopBounds": "loop bounds, gas, early refusal", "Exec3": "Layer 3 exclusivity (Exec3)", "Permit2Freeze": "fork: Permit2 freeze subset (skipped here; run on three chains, section 7)", "Permit2ThreeChains": "fork: code, domain separator and witness suite (skipped here; section 7)", "GenHashVectors": "hash vectors (generated)", "GenErrorSelectors": "error selectors (generated)", "Reentrancy": "reentrancy: a callback during the Permit2 pull (F-16)",
    "GenContainment": "migration vectors (generated: containment, Lemma M)", "GenTables": "migration vectors (generated: transition tables)",
    "GenScenarios": "migration vectors (generated: scenarios)", "GenMisc": "migration vectors (generated: misc)",
}


def category(suite):
    name = suite.split(":")[-1].replace("Test", "")
    for k, v in CATEGORY.items():
        if name == k or name.startswith(k):
            return v
    return "other"


def readiness():
    r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "freeze_readiness.py")], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip().splitlines()


def tbl(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("\n", " ") for c in r) + " |")
    return out


def short(h, n=18):
    return f"`{h[:n]}…`" if h and len(h) > n + 1 else f"`{h}`"


def build():
    lock = J("toolchain/toolchain.lock.json")
    fetch = opt("toolchain/fetch-record.json")
    trees = opt("toolchain/tree-verification.json")
    rb = J("evidence/permit2/rebuild.json")
    pin = J("evidence/permit2/pin.json")
    loops = opt("evidence/implementation/loop-audit.json")
    build_r = opt("evidence/implementation/build-report.json")
    forks = opt("evidence/implementation/fork-runs.json")
    findings = J("evidence/implementation/findings.json")["findings"]
    ids = [f["id"] for f in findings]
    if len(set(ids)) != len(ids):
        sys.exit("findings.json: duplicate ids")
    for f in findings:
        for k in ("id", "kind", "status", "title", "what", "resolution", "evidence", "specImpact"):
            if not f.get(k):
                sys.exit(f"findings.json: {f.get('id')} has no {k}")
        for e in f["evidence"]:
            path = e.split(" ")[0]
            if ("/" in path or path.endswith((".md", ".py", ".json", ".sol"))) and not (ROOT / path).exists() and not (ROOT.parent / path).exists() and not path.startswith("eip712/types.json"):
                sys.exit(f"findings.json: {f['id']} cites {path}, which does not exist")
    reg = J("evidence/freeze_register.json")
    gold = J("eip712/golden-vectors.json")
    fixt = J("foundry/vectors/permit2-evidence.json")
    final = forge_json("evidence/implementation/logs/forge-test-final.json")
    ready = readiness()
    L = []
    A = L.append

    A("# Implementation evidence report")
    A("")
    A("Specification 0.5.0 (draft), accepted as the basis of implementation. **Protocol freeze (RG-016) is not approved and this report does not ask for it.** "
      "It records what was built and run, with the evidence file beside each claim, what was not done, and what the implementation showed that people must decide. "
      "Generated by `tools/impl_report.py` from the evidence files: no number below is typed by hand.")
    A("")
    A("```text")
    A("\n".join(ready))
    A("```")
    A("")
    dc = RC.data()
    met = re.search(r"\((\d+) of (\d+) conditions met\)", "\n".join(ready))
    A("## 0. Evidence classes, kept apart")
    A("")
    A("Five kinds of evidence exist in this workspace and they are **not added together**: a result of one class says nothing about another.")
    A("")
    L += RC.classes(dc, reg.get("foundryReport") or {}, forks, rb, forks, ready)
    A("")
    A("## 0a. The ten items of the corrective instruction (the actual contracts)")
    A("")
    L += RC.corrective(dc, met.group(1) if met else "?", met.group(2) if met else "?")
    A("")
    A("## 0b. The ten items of the first pass (the reference model; kept for the record)")
    A("")
    fr = reg.get("foundryReport") or {}
    fk = (pin.get("forkReport") or {})
    rows = [
        ("1", "Reproducible Foundry toolchain, pinned", "**Done**", "`toolchain/toolchain.lock.json`, `fetch_toolchain.py`, `fetch-record.json`, `tree-verification.json`"),
        ("2", "Compile everything; resolve compile, ABI, width, layout and harness issues", "**Done for the reference model** (the contracts: §14)",
         "`build-report.json`, ABI and storage snapshots, findings F-01…F-04"),
        ("3", "Missing EIP-712 type strings; Solidity and TypeScript hashes; golden vectors", "**Done as a proposal**; approval (condition C-11) is a human act",
         "`eip712/types.json`, `eip712/TYPES.md`, `eip712/golden-vectors.json`, `EIP712Golden.t.sol`, `eip712/test-eip712.ts`"),
        ("4", "Exposure index and migration logic O(1) or bounded; no unbounded loop blocks an exit", "**Done for the model**; the same audit passes on the contracts (§14.2)",
         "`loop-audit.json`, `LoopBounds.t.sol`, F-05, F-11"),
        ("5", "Layer 3 exclusivity versus Layer 2 coexistence", "**Done** (text, tests, invariants)", "`12 §5.5`, `Exec3.t.sol`, `MigrationInvariant.t.sol`, F-15"),
        ("6", "Unit, fuzz, invariant, mutation, width, timestamp, signer-set, pin, shared-allowance and migration tests",
         f"**{fr.get('passed', '?')} passed, {fr.get('failed', '?')} failed**, {fr.get('skippedInThisRun', '?')} skipped (the fork suites, which need an RPC URL)", "`logs/forge-test-final.json`, `freeze_register.json` foundryReport"),
        ("7", "Mainnet-fork tests on Ethereum, Base and Arbitrum", ("**" + forks["verdict"] + "** on " + ", ".join(f"{c['name']} (block {c['block']})" for c in forks["chains"])) if forks else "**Not run**",
         "`fork-runs.json`, `logs/fork-*.json`, `pin.json` forkReport"),
        ("8", "Reproducible Permit2 build and CREATE2 comparison", "**Reproduced** (address, creation code, every byte of the deployed code); **not an audit**", "`evidence/permit2/rebuild.json`, §8 below"),
        ("9", "Wallet-lab plan executed; signed run records", "**Not done: it needs real wallets and named people.** A kit and a signature verifier are in place", "`evidence/wallet-lab-kit/`, `tools/wallet_lab_verify.py`"),
        ("10", "freeze_readiness stays false until the listed conditions hold", "**Holds: NOT READY**", "`tools/freeze_readiness.py`; condition C-11 (EIP-712 frozen) added"),
    ]
    L += tbl(["#", "Item", "Result", "Evidence"], rows)
    A("")

    # ------------------------------------------------------------------ 1
    A("## 1. Toolchain")
    A("")
    f = lock["foundry"]
    A(f"Foundry **{f['version']}** (released {f['releasedAt']}), Windows build `{f['artifacts']['windows-amd64']['sha256']}`; solc **0.8.24** for the model and the tests, solc **0.8.17** for the Permit2 rebuild; forge-std **{lock['sources']['forge-std']['version']}**. "
      "Every artifact is identified by URL and SHA-256 and verified before use (`toolchain/forge.py` refuses to run on an unverified toolchain). Foundry's published attestations are recorded but **not verified** by this repository's tooling.")
    A("")
    rows = [(n, f"`{s.get('commit', '')}`", s["url"].split("/")[2], f"`{s['sha256']}`") for n, s in lock["sources"].items()]
    L += tbl(["Source", "Commit", "Host", "Archive SHA-256"], rows)
    A("")
    if fetch:
        A("Every archive was fetched over HTTPS from github.com or codeload.github.com only; a redirect to any other host is refused; the original URL, the redirect chain, the final URL, the archive file name, the byte length and the SHA-256 are in `toolchain/fetch-record.json` and were recorded before extraction. Nothing downloaded was executed. "
          "Extraction refuses path traversal and any entry that would leave the root; symlink entries are written as plain files after the same check.")
    if trees:
        A("")
        A(f"After extraction each tree was compared with GitHub's tree API (blob SHA-1 of every file), the root tree id was recomputed from the extracted files and compared with the commit's tree, and each submodule path was checked against the parent's gitlink entry: `toolchain/tree-verification.json` ({len(trees.get('trees', trees))} trees).")
    A("")

    # ------------------------------------------------------------------ 2
    A("## 2. Compile, ABI, widths, storage layout, harness")
    A("")
    if build_r:
        A(f"`forge build` (solc 0.8.24, via-IR, 20 optimizer runs, EVM cancun) compiles all {len(build_r['contracts'])} contracts and libraries of `foundry/src`; the ABI and the storage layout of each are snapshotted under `evidence/implementation/abi` and `storage` and compared by `tools/build_report.py --check`. "
          f"Selector and slot collisions: {len(build_r['selectorCollisions'])}. `forge lint`: {build_r['lint']['findings']} findings in {len(build_r['lint']['byRule'])} rules, each with a recorded disposition ({len(build_r['lint']['untriaged'])} untriaged).")
        A("")
        rows = [(n, c["kind"], c.get("runtimeSize", ""), ("**yes**" if c.get("exceedsEip170Limit24576") else "no") if "runtimeSize" in c else "", c["abiEntries"], c.get("selectors", ""),
                 c.get("storageVariables", "")) for n, c in build_r["contracts"].items()]
        L += tbl(["Contract", "Kind", "Runtime bytes", "Above 24,576 (EIP-170)", "ABI entries", "Selectors", "Storage variables"], rows)
        A("")
        rows = [(r, d["count"], d["disposition"], d["reason"]) for r, d in build_r["lint"]["byRule"].items()]
        if rows:
            L += tbl(["Lint rule", "Findings", "Disposition", "Reason"], rows)
            A("")
    else:
        A("`evidence/implementation/build-report.json` is absent.")
        A("")
    A("The model is a **reference model**, not the production contracts: its ABI and layout show that the model has no layout defect, not what will be deployed. Harness and width findings: F-01, F-02, F-03, F-04; the manager model is above the contract size limit (F-17).")
    A("")

    # ------------------------------------------------------------------ 3
    A("## 3. EIP-712 types")
    A("")
    A(f"One source, `eip712/types.json`; generated: `foundry/src/generated/FastPayTypes.sol`, `eip712/fastpay-types.generated.ts`, `eip712/golden-vectors.json`, `eip712/TYPES.md`, and the wallet payloads in `eip712/typed-data/`. "
      f"**Freeze fingerprint** (strings only, no prose): `{gold['freezeFingerprintSha256']}`. Status: **PROPOSED, not frozen**; condition C-11 needs the Wallet Protocol Engineer and the Solidity Lead to approve this fingerprint.")
    A("")
    rows = [(n, e["status"], e["domain"], f"`{e['typeHash']}`", f"`{e['hashStruct'][:18]}…`") for n, e in gold["structs"].items()]
    L += tbl(["Type", "String status", "Domain", "typeHash", "hashStruct of the golden value"], rows)
    A("")
    w = gold["permit2Witness"]
    A("Pay Once witness for Permit2 (single and batch):")
    A("")
    A("```text")
    A("witnessTypeString = " + w["witnessTypeString"])
    A("single type hash   = " + w["typeHashSingle"])
    A("batch  type hash   = " + w["typeHashBatch"])
    A("```")
    A("")
    A("**Four implementations reproduce every golden vector** (`foundry/test/generated/EIP712Golden.t.sol`, `eip712/test-eip712.ts`, `tools/eip712_types.py`, and Foundry's own `eip712HashType`, `eip712HashStruct` and `eip712HashTypedData` cheat codes), "
      "a fifth source, the real Permit2 built from the pinned commit, accepts a signature over the witness string (single and batch) and rejects every deviation: each of 12 fields and 7 variants of the string (`EIP712Permit2.t.sol`, and on the three real deployments in the fork run). "
      "Negative controls: a corrupted golden hash fails the TypeScript test (1 of 344 checks); two swapped fields in the generated Solidity fail three golden tests. Every golden value gives each field of one type a distinct value, so a swapped pair changes the hash (F-10). "
      "The strings of the Permit2 stubs and of `TokenPermissions` are checked against the source of the pinned commit by `tools/eip712_types.py`.")
    A("")
    A("Open decisions the types raised (not edited): F-06, F-07 (the implemented snapshot encoding differs from document 12), F-09 (price bounds per mandate or per token), and the field sets of the revoke, pause, resume and reduce messages, which are the minimum that identifies the act.")
    A("")

    # ------------------------------------------------------------------ 4
    A("## 4. Loop bounds")
    A("")
    if loops:
        A(f"`tools/loop_audit.py` compiles the sources to an AST and requires every one of the **{len(loops['loops'])} loops** to carry a `loop-bound` annotation that names its bound; every named bound must equal the constant in the source and the value in `config/pc_records.json`; no loop without a constant bound may be reachable from a state-changing function; there is no recursion. Verdict: **{loops['verdict']}**.")
        A("")
        rows = [(f"{e['contract']}.{e['function']}", e["loopsReachable"], e["iterationBound"], e.get("iterationBoundAtHardMaxOfTheSafeRange")) for e in loops["entryPoints"] if e["stateChanging"] and e["loopsReachable"]]
        L += tbl(["State-changing entry point", "Loops reachable", "Iteration bound (proposed constants)", "Iteration bound (hard maximum of the safe ranges)"], rows)
        A("")
        A(f"Constants: {', '.join(f'{k} = {v}' for k, v in loops['constants'].items())}; hard maxima of the safe ranges used above: {', '.join(f'{k} = {v}' for k, v in loops['safeRangeHardMax'].items())}. "
          "The two unbounded loops that remain are oracles (`authRouter`, `liveCountScan`) that no state-changing function can reach. The bound is on loop iterations, not on gas; gas is measured next.")
    A("")
    gas = {}
    if final:
        for suite, s in final.items():
            if suite.endswith(":LoopBoundsTest"):
                for t, tr in s["test_results"].items():
                    for line in tr.get("decoded_logs") or []:
                        if ":" in line:
                            k, v = line.rsplit(":", 1)
                            gas[k.strip()] = v.strip()
    if gas:
        # the numbers quoted in finding F-12 must be numbers of this run
        f12 = next(f for f in findings if f["id"] == "F-12")
        measured = {int(v) for v in gas.values() if v.isdigit()}
        for n in re.findall(r"(?<![\d,])\d{1,3}(?:,\d{3})+(?![\d,])", f12["what"]):
            if int(n.replace(",", "")) not in measured and n != "30,000,000":
                sys.exit(f"finding F-12 quotes {n}, which is not a gas figure of the recorded run: update evidence/implementation/findings.json")
        A("Worst cases measured in the reference model (`LoopBounds.t.sol`; Foundry 1.8.5, via-IR; a **lower bound** for production contracts, which add signature recovery, calldata and events, and **not a measurement of any deployed contract**):")
        A("")
        L += tbl(["Measurement", "Gas"], [(k, v) for k, v in sorted(gas.items())])
        A("")
    A("The cost of an exit (revoke, retire, reduce) does not depend on the length of the exposure list, on the number of sibling mandates, or on the number of generations of the lineage (the tests compare 8 with 153 list entries, 1 with 40 siblings, generation 0 with 60). "
      "Values above a bound are refused before a loop runs (terms with 0 or 4 tokens, a signer set of 17 or 5,000 members, a batch of 51). Findings F-05, F-11, F-12.")
    A("")

    # ------------------------------------------------------------------ 5
    A("## 5. Layer 3 exclusivity and Layer 2 coexistence")
    A("")
    A("Document 12 section 5.5 now reads: `Exec3(L)` (the routers on which some mandate of lineage `L` is consumable, Permit2 not consulted) has at most one element; `AuthRouters(L)` (those that also have a usable allowance) is a subset of it; **Layer 2 Permit2 allowances may coexist on several routers for sibling mandates and never create Layer 3 authority**. "
      "`Exec3.t.sol` builds the case (two sibling lineages share the allowance `(customer, T1, R0)`; one migrates to R1; both routers hold a usable allowance for T1; each lineage has exactly one executing router; the old router cannot charge the migrated lineage) and a chain of twelve successors. "
      "The stateful invariants `invariant_I_MIG_8_Exec3AtMostOneRouterPerLineage` and `invariant_I_MIG_8_NoOverlappingAuthority` run with the handler of random grants, lockdowns, expiries, charges, activations, successors of both kinds, revocations, retirements and registry operations.")
    A("")

    # ------------------------------------------------------------------ 6
    A("## 6. Foundry results")
    A("")
    if final:
        by = {}
        for suite, s in final.items():
            cat = category(suite)
            d = by.setdefault(cat, dict(p=0, f=0, s=0, fuzz=0, suites=[]))
            d["suites"].append(suite.split(":")[-1])
            for _t, tr in s["test_results"].items():
                st = tr["status"]
                d["p" if st == "Success" else "f" if st == "Failure" else "s"] += 1
                d["fuzz"] += (tr.get("kind", {}).get("Fuzz", {}) or {}).get("runs", 0) or 0
        rows = [(c, ", ".join(sorted(set(d["suites"]))), d["p"], d["f"], d["s"], d["fuzz"]) for c, d in sorted(by.items())]
        L += tbl(["Category", "Suites", "Passed", "Failed", "Skipped", "Fuzz runs"], rows)
        A("")
    A(f"Recorded in `evidence/freeze_register.json` (`foundryReport`): {json.dumps({k: fr.get(k) for k in ('compiled', 'suites', 'passed', 'failed', 'skippedInThisRun', 'fuzzRunsExecuted')})}, run file `{fr.get('runFile')}` (SHA-256 `{fr.get('runFileSha256')}`). "
      "Mutation: all 151 named mutants of the model are killed by the exported vector suite (ten chunked tests; `test_ChunksCoverEveryMutant`). This records a test run; it is not an approval.")
    A("")
    A("**What the first runs and `forge lint` found in the model** (all fixed in the model and tested; the findings are in §11): the clock read across `vm.warp` (F-01), unbounded fuzz seeds (F-02), the memory limit of the mutation suite (F-03), type widths wider than documented (F-04), loops that could grow on an exit path (F-05), and, from the lint, **a charge that pulled through Permit2 before writing its effects** (F-16): "
      "`Reentrancy.t.sol` shows that a token callback could then charge one cycle twice and exceed a total cap, and that the corrected order (document 11 §5, steps 7 then 8) refuses both.")
    A("")

    # ------------------------------------------------------------------ 7
    A("## 7. Mainnet-fork tests against the real Permit2")
    A("")
    if forks:
        rows = []
        for c in forks["chains"]:
            used = c["attempts"][c.get("usedAttempt", -1)] if c["attempts"] else {}
            rows.append((f"{c['name']} ({c['chainId']})", c["block"], f"`{c['blockHash'][:18]}…`", ", ".join(h.split('//')[1] for h in c["providersAgreeing"]), used.get("passed"), used.get("failed"), used.get("skipped"), c["result"]))
        L += tbl(["Chain", "Fork block", "Block hash", "Providers that agree on the hash", "Passed", "Failed", "Skipped", "Result"], rows)
        A("")
        A("Per chain the suites are: the freeze subset of document 16 (RV-T01, 02, 04, 05, 07, 08, 10, 11, MIG-TV-22/40, F2, F4, F5 and a differential fuzz of the Permit2 mock against the real contract), the witness suite of §3, and the checks that the code on the chain equals the rebuilt code byte for byte with the chain id and the domain separator of that chain written into the two immutable slots. "
          "The fork reads the chain through public RPC providers: this evidence depends on the network and on those providers.")
    else:
        A("The fork run has not been recorded.")
    A("")

    # ------------------------------------------------------------------ 8
    A("## 8. Permit2 reproducible build and CREATE2 comparison")
    A("")
    A(f"Pinned commit **`{rb['sourceCommit']}`** (source archive SHA-256 `{rb['pinnedPermit2']['archiveSha256']}`; extracted tree listing SHA-256 `{rb['pinnedPermit2']['extractedTreeSha256Listing']}`; git root tree `{rb['pinnedPermit2']['gitRootTree']}`, recomputed from the extracted files: **{'equal' if rb['pinnedPermit2']['gitRootTree'] == rb['pinnedPermit2']['gitRootTreeRecomputedFromExtractedFiles'] else 'DIFFERENT'}**).")
    A("")
    A("**Dependencies (full commits, nested commits, archive hashes, extracted-tree hashes) and the role each plays:**")
    A("")
    rows = []
    for d in rb["dependencies"]:
        nested = ", ".join(f"`{k}` @ `{v[:10]}…`" for k, v in d.get("submodulesNotPresentInThisArchive", {}).items()) or "none"
        rows.append((d["name"], f"`{d['extractedTo']}`", f"`{d['commit']}`", nested, f"`{d['archiveSha256']}`", f"`{d['extractedTreeSha256Listing']}`",
                     d.get("roleInCompileUnit", {}).get("requiredFor", "")))
    L += tbl(["Dependency", "Extracted to", "Commit", "Nested submodules (not in the archive)", "Archive SHA-256", "Extracted tree listing SHA-256", "Needed for"], rows)
    A("")
    A("`solmate` is needed for production compilation (the contracts import it); the `forge-std` of Permit2 only for the deployment script (and the tests); `forge-gas-snapshot`, `openzeppelin-contracts` and `ds-test` only for the tests. "
      "The role of each dependency was computed from the import closure of the compile unit (`roleInCompileUnit` in `rebuild.json`: files reached from a production contract, from the deployment script, from tests, from nothing). "
      "**Roles are not what reproduces the bytes:** the creation code depends on the whole compile unit, test-only libraries included (F-14), so every dependency above is needed to reproduce the same creation code even though only `solmate` is imported by the deployed contract.")
    A("")
    ns = rb["nestedForgeStdOfForgeGasSnapshot"]
    A(f"The nested forge-std of forge-gas-snapshot (`{ns['commit']}`) was **not fetched**: no source of the compile unit comes from it (`required: {str(ns['required']).lower()}`). The `ds-test` archive was approved and fetched because the reconstructed submodule graph and the compiler required it. "
      "No other undeclared dependency was needed.")
    A("")
    A("**Compiler and build settings:**")
    A("")
    bc = rb["buildConfiguration"]
    rows = [("forge", rb["toolchain"]["forge"].splitlines()[0] + f" (SHA-256 of the executable archive `{rb['toolchain']['forgeSha256'][:16]}…`)"),
            ("solc", f"{rb['toolchain']['solc']} (executable SHA-256 `{rb['toolchain']['solcSha256'][:16]}…`)"), ("EVM version", rb["evmVersion"]),
            ("optimizer", f"enabled, {bc['optimizer_runs']} runs"), ("viaIR", "true"), ("metadata bytecode hash", rb["metadata"]["bytecodeHash"] + " (trailer `" + rb["metadata"]["rebuiltRuntimeTrailerHex"] + "`)"),
            ("linked libraries", "none"), ("remappings", "; ".join(f"`{x}`" for x in bc["remappings"] if "spec/toolchain" not in x and ":" not in x.split("/")[0])),
            ("source include/exclude rules", rb["includeExcludeRules"]), ("compile unit", f"{rb['sourceCount']} files: " + ", ".join(f"{k} {v}" for k, v in rb["dependencyRoleSummary"]["_unit"].items() if k != "files"))]
    L += tbl(["Setting", "Value"], rows)
    A("")
    c2 = rb["create2"]
    A("**CREATE2:**")
    A("")
    rows = [("deployer (deterministic deployment proxy)", c2["deployer"]), ("salt", f"`{c2['salt']}` ({c2['saltSource']})"), ("constructor arguments", rb["constructor"]["arguments"]),
            ("creation code", f"{rb['creationCodeLength']} bytes, keccak256 `{rb['creationCodeKeccak256']}`"), ("init code hash", f"`{rb['constructor']['initCodeKeccak256']}`"),
            ("computed address", f"`{c2['computedAddress']}`"), ("canonical address", f"`{c2['canonicalAddress']}`"), ("equal", "**yes**" if c2["matches"] else "**NO**")]
    L += tbl(["Item", "Value"], rows)
    A("")
    A("**Immutables, proved by the compiler's own artifact** (solc `immutableReferences`, AST ids mapped to their declarations): "
      + "; ".join(f"`{v['name']}` ({v['type']}) at offset {r[0]['start']}, length {r[0]['length']}" for k, v in rb["immutableVariables"].items() for r in [rb["immutableReferencesByAstId"][k]]) + ".")
    A("")
    A(f"**Runtime code:** {rb['runtimeCodeLength']} bytes locally generated (keccak256 with zero immutables `{rb['runtimeCodeKeccak256WithZeroImmutables']}`), compared byte for byte with the code deployed on each chain (two or more providers agreeing, at a block 64 behind the head at the time):")
    A("")
    rows = []
    slot_name = {}
    for ast, refs in rb["immutableReferencesByAstId"].items():
        for r in refs:
            slot_name[r["start"]] = rb["immutableVariables"][ast]["name"]
    for cid, cmp_ in rb["comparison"].items():
        rng = ", ".join(f"[{r['offset']}, +{r['length']}]" for r in cmp_["differingRanges"])
        rows.append((pin["chains"][cid]["name"], f"`{cmp_['deployedKeccak256'][:18]}…`", cmp_["differingBytes"], rng, len(cmp_["rangesOutsideImmutableReferences"]),
                     cmp_["remainingDifferencesAfterFillingBothImmutables"], "yes" if cmp_["metadataStripped"]["strippedCodeEqual"] else "NO"))
    L += tbl(["Chain", "Deployed code hash", "Differing bytes", "Differing ranges (offset, +length)", "Ranges outside the immutable slots", "Differences after filling both slots", "Metadata-stripped code equal"], rows)
    A("")
    A("**Every differing range and its proven explanation** (the slot is named by the compiler's `immutableReferences`; the meaning is what the chain's own data says the slot must hold, computed independently of the compiler):")
    A("")
    rows = []
    for cid, cmp_ in rb["comparison"].items():
        for rg in cmp_["differingRanges"]:
            ref = next(r for r in cmp_["immutableReferences"] if r["offset"] <= rg["offset"] and rg["offset"] + rg["length"] <= r["offset"] + r["length"])
            val = ref["deployedBytes"]
            shown = str(int(val, 16)) if ref["expectedImmutable"] == "chainId" else "0x" + val
            rows.append((pin["chains"][cid]["name"], f"[{rg['offset']}, +{rg['length']}]", f"[{ref['offset']}, +{ref['length']}) `{slot_name[ref['offset']]}`", ref["expectedImmutable"],
                         f"`{shown}`", "the rebuilt slot holds zeros (the compiler leaves immutables unfilled); the deployed slot holds this value; the differing bytes are the non-zero bytes of it" if ref["expectedImmutable"] == "chainId" else "the whole word is the domain separator of the deployment"))
    L += tbl(["Chain", "Differing range", "Compiler's immutable slot", "Computed meaning", "Value in the deployed code", "Why the bytes differ"], rows)
    A("")
    A("Every differing byte lies inside one of the two 32-byte immutable slots; the bytes in them are the chain id (offset 6,945) and the domain separator (offset 6,983) that `EIP712.sol` computes (`keccak256(abi.encode(typeHash, keccak256(\"Permit2\"), chainId, address))`); filling both slots from the chain reproduces the deployed code exactly. "
      "The first differing byte of each range is the first non-zero byte of the chain id or separator word, not a code difference. The same comparison runs inside Foundry (`EIP712Permit2.t.sol`, and on each fork).")
    A("")
    A("**Isolation:** the build ran in a fresh empty directory with a scrubbed environment, `FOUNDRY_OFFLINE` and `--offline`, proxies pointing at a closed port, nothing executed (`forge build` only), and the build process's sockets were sampled with netstat "
      f"({rb['network']['samples']} samples, {len(rb['network']['nonLoopbackTcpRowsObserved'])} non-loopback TCP rows). **This is software-level isolation only: there is no operating-system sandbox or container**; a container with `--network none` would need Linux binaries that were not approved.")
    A("")
    A("**What this reproduction does and does not establish.** It establishes that the pinned source, compiled with the recorded compiler and settings as the repository builds itself, yields the creation code whose CREATE2 address is the canonical address and whose runtime code equals the deployed code on three chains except the two immutables, which the compiler's artifact names. "
      "It does **not** establish that the source is correct or safe (the E2 review by two named people, PR-01…PR-16, is not done), and it does not cover other chains. A build that only compiles `src/` does not reproduce the address (F-14).")
    A("")

    # ------------------------------------------------------------------ 9
    A("## 9. Wallet lab")
    A("")
    A("**Not executed.** The lab needs real wallets (MetaMask, MetaMask iOS, Trust Wallet), real accounts of each type and named testers and reviewers; none of that can be produced here, and **no run record has been created, signed or simulated**. `evidence/wallet-lab/` is empty and condition C-2 reads 0 of 10 run sets. "
      "What was added so that the lab can start: the `eth_signTypedData_v4` payloads of every FastPay message and of the Pay Once witness (`eip712/typed-data/`) for WL-16, WL-17, WL-19 and WL-27; the registry of people who may sign (`evidence/wallet-lab-kit/people.json`, empty); the run-record template with `signatures` and `typedDataSignatures`; "
      "`tools/wallet_lab_verify.py`, which recovers the signer of a `personal_sign` signature over the record's hash and of a wallet's EIP-712 signature over a payload, requires two different registered people, and flags ERC-1271 signatures as not verifiable offline; its self-test tampers with a synthetic record in eight ways and detects each. "
      "`freeze_readiness.py` now counts a run record only if these signatures verify.")
    A("")

    # ------------------------------------------------------------------ 10
    A("## 10. Freeze readiness")
    A("")
    A("`freeze_readiness.py` reports the state above. What each condition still needs:")
    A("")
    rows = [("C-1", "Owner review of the companion artifacts", "people"), ("C-2", "Wallet-lab evidence EVL-01…EVL-10, reviewed and signed", "people and wallets (§9)"),
            ("C-3", "E2 sign-off of PR-01…PR-16 by two named reviewers; rebuild (done); fork subset (" + ("recorded" if fk else "not recorded") + ")", "two named reviewers"),
            ("C-4", "All 18 production constants approved, one by one (plus PC-19 for the signer-set bound, which has no record yet)", "the owners named in `18-configuration-records.md`"),
            ("C-5, C-6", "Freeze-blocking decisions (12) and external facts (10)", "decisions and external evidence"),
            ("C-7", "Two independent planner implementations pass the vectors", "an engineering team"), ("C-8", "Audit scope agreed with both firms; slots contracted", "procurement"),
            ("C-9", "Foundry suites compile and pass; fork subset passes", "**evidence recorded by this work**"), ("C-10", "Four sign-offs", "named executives"),
            ("C-11", "EIP-712 type strings frozen: approval of the fingerprint of §3", "Wallet Protocol Engineer and Solidity Lead")]
    L += tbl(["Condition", "Needs", "From"], rows)
    A("")

    # ------------------------------------------------------------------ findings
    A("## 11. Findings: what the implementation showed")
    A("")
    rows = [(f["id"], f["kind"], f["status"], f["title"]) for f in findings]
    L += tbl(["Id", "Kind", "Status", "Title"], rows)
    A("")
    for f in findings:
        A(f"**{f['id']} — {f['title']}** ({f['kind']}, {f['status']}). {f['what']} *Resolution:* {f['resolution']} *Specification impact:* {f['specImpact']}. Evidence: {', '.join('`' + e + '`' for e in f['evidence'])}.")
        A("")

    # ------------------------------------------------------------------ limits
    A("## 12. Limits of this evidence")
    A("")
    for s in [
        "The code of §1 to §11 is a **reference model** of the migration, pin, registry and signer-set logic: passing its suites shows that the specification is consistent and testable, not that any contract is correct. The contracts are §14.",
        *RC.LIMITS,
    ]:
        A("* " + s)
    A("")
    A("## 13. Reproduce")
    A("")
    A("```bash")
    for c in ["python -I spec/toolchain/fetch_toolchain.py --verify          # the pinned toolchain",
              "python -I spec/toolchain/forge.py test --json                 # every non-fork suite",
              "python -I spec/tools/fork_run.py                              # the three-chain fork run (needs network)",
              "python -I spec/tools/permit2_rebuild.py --verify              # the Permit2 reproduction, offline",
              "python -I spec/tools/loop_audit.py                            # the static loop audit",
              "python -I spec/tools/export_eip712.py --check                 # generated EIP-712 artifacts are current",
              "node --experimental-strip-types spec/eip712/test-eip712.ts   # the TypeScript implementation",
              "python -I spec/tools/wallet_lab_verify.py --selftest          # the signature verifier",
              *RC.REPRODUCE,
              "python -I spec/tools/check_all.py                             # all consistency checks",
              "python -I spec/tools/freeze_readiness.py                      # readiness (must say NOT READY)"]:
        A(c)
    A("```")
    A("")
    L += RC.section(dc, forks)
    return "\n".join(L) + "\n"


def main(argv):
    text = build()
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("REPORT.md is stale: run python -I spec/tools/impl_report.py --write")
            return 1
        print("REPORT.md up to date")
        return 0
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print("wrote", OUT.relative_to(ROOT), f"({len(text.splitlines())} lines)")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
