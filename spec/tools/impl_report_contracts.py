"""The part of the implementation report that is about the ACTUAL FastPay contracts and the evidence classes (read by tools/impl_report.py).

Nothing here is typed by hand: every number is read from an evidence file under spec/evidence/implementation or from contracts/. The five classes of
evidence are reported apart, and each says what it does NOT show.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPL = ROOT / "evidence" / "implementation"
CONTRACTS = ROOT.parent / "contracts"


def opt(p):
    f = pathlib.Path(p)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def tbl(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("\n", " ") for c in r) + " |")
    return out


def gas_of(run, key):
    for g in (run or {}).get("gas", []):
        if g["name"] == key:
            return g["value"]
    return None


def data():
    return dict(
        report=opt(IMPL / "contracts-report.json"),
        loops=opt(IMPL / "loop-audit-contracts.json"),
        tests=opt(IMPL / "contracts-test-run.json"),
        mut=opt(IMPL / "contracts-mutation.json"),
        forks=opt(IMPL / "contracts-fork-runs.json"),
        frozen=opt(CONTRACTS / "frozen-settings.json"),
        pc=opt(ROOT / "config" / "pc_records.json"),
    )


def pc_value(d, symbol):
    for r in (d["pc"] or {}).get("records", []):
        for q in r["proposal"].get("quantities", []):
            if q["symbol"] == symbol:
                return q["value"], q.get("hardMin"), q.get("hardMax"), r["id"]
    return None


def classes(d, fr, pin_fork, rb, forks_model, ready_line):
    """The five classes of evidence, each with its result and its limit."""
    t, m, f, r = d["tests"], d["mut"], d["forks"], d["report"]
    rows = []
    rows.append(("A. Reference model (`spec/foundry`)", f"{fr.get('passed', '?')} passed, {fr.get('failed', '?')} failed, {fr.get('skippedInThisRun', '?')} skipped (the Permit2 fork suites); 151 of 151 model mutants killed",
                 "A model of the logic, not the code that will be deployed. Its gas is the model's.", "`evidence/implementation/logs/forge-test-final.json`, `model_checks.py`"))
    if t:
        mut = f"; mutation of the contracts: {m['counts']['killed']} of {m['counts']['mutants'] - m['counts']['invalid']} valid mutants killed" if m else "; mutation not run"
        rows.append(("B. FastPay contracts (`contracts/`)", f"{t['passed']} passed, {t['failed']} failed, {t['skipped']} skipped (the fork variants, without a fork){mut}; every runtime at most {d['frozen']['runtimeSizeTargetBytes']:,} bytes: "
                     f"largest {max(c['runtimeBytes'] for c in r['contracts'].values() if c['file'].startswith('src/') and c['runtimeBytes'] > 100):,}",
                     "Compiled and tested on the rebuilt Permit2 and a local EVM. Not audited. The Python model and the Solidity model are not the code under test here.",
                     "`contracts-test-run.json`, `contracts-report.json`, `contracts-mutation.json`, `loop-audit-contracts.json`"))
    else:
        rows.append(("B. FastPay contracts (`contracts/`)", "**Not run**", "", ""))
    rows.append(("C. Permit2 rebuild", "Reproduced: canonical address, creation code and every byte of the deployed code except the two named immutables" if rb else "not recorded",
                 "Software-level isolation; the comparison reads public RPC providers; not an audit of Permit2.", "`evidence/permit2/rebuild.json`"))
    rows.append(("D. Permit2 fork (reference-model freeze suites)", ("**" + pin_fork["verdict"] + "** on " + ", ".join(f"{c['name']} (block {c['block']})" for c in pin_fork["chains"])) if pin_fork else "not run",
                 "Reads the chains through public RPC providers.", "`fork-runs.json`"))
    if f:
        rows.append(("D2. FastPay contracts on the forks", ("**" + f["verdict"] + "** on " + ", ".join(f"{c['name']} (block {c['block']})" for c in f["chains"])),
                     "The contracts run against each chain's REAL Permit2 and state; the gas schedule is the compiler target's (cancun), NOT the chain's: Arbitrum's accounting is not modelled and no chain's per-transaction cap is enforced.",
                     "`contracts-fork-runs.json`"))
    else:
        rows.append(("D2. FastPay contracts on the forks", "**Not run**", "", ""))
    rows.append(("E. Wallet lab", "**Not done.** It needs real wallets and named reviewers; a kit and a signature verifier exist, no run record exists and none was simulated.",
                 "Wallet rendering of every typed message is untested.", "`evidence/wallet-lab-kit/`, `tools/wallet_lab_verify.py`"))
    return tbl(["Class of evidence", "Result", "What it does not show", "Files"], rows)


def corrective(d, ready_met, ready_total):
    t, r, m, f = d["tests"], d["report"], d["mut"], d["forks"]
    batch = pc_value(d, "MAX_BATCH")
    sig = pc_value(d, "MAX_SIGNERS_PER_SET")
    sizes = {n: c["runtimeBytes"] for n, c in (r or {}).get("contracts", {}).items() if c["file"].startswith("src/") and c["runtimeBytes"] > 100}
    biggest = max(sizes, key=sizes.get) if sizes else None
    step = gas_of(t, "worst-case step, tx gas estimate")
    rows = [
        ("1", "Resolve F-06, F-07 and F-09; `eip712/types.json` the single source; regenerate everything",
         "**Done**: the types file generates the Solidity library (both projects), the TypeScript, the Python golden vectors, the Foundry golden tests, the wallet payloads and `TYPES.md`; the hashes of the snapshot and of the terms agree in Python, TypeScript, the Solidity model and the contracts",
         "`eip712/types.json`, `export_eip712.py --check`, `Differential.t.sol`, F-06, F-07, F-09"),
        ("2", "`customer`, `anchorStartsAt` and `boundsVersion` in the migration snapshot", "**Done** (26 words; no ADR showed any of them unnecessary)", "ADR-020, `snapshotEncoding`, `TermsHashParity.t.sol`"),
        ("3", "Price bounds in a versioned token-currency registry; the mandate pins currency and bounds version", "**Done**: append-only versions, width ceiling (PC-07), intersection of the pinned and the current band, K.6", "ADR-020, `Quote.t.sol`, `BoundsVersion.t.sol`"),
        ("4", "Split the manager: every runtime at most 22,000 bytes, optimizer frozen, no generic delegatecall, cross-contract invariants kept",
         (f"**Done**: {len(sizes)} contracts; the largest is {biggest} at {sizes[biggest]:,} bytes; no DELEGATECALL, CALLCODE, SELFDESTRUCT, ORIGIN, CREATE or CREATE2 in any runtime; settings frozen in `contracts/frozen-settings.json`" if sizes else "**Not run**"),
         "ADR-021, `contracts-report.json`, `Deployment.t.sol`, `ManagerAlone.t.sol`"),
        ("5", "A bounded, resumable migration state machine; a conservative provisional `MAX_BATCH`; re-measured on the actual contracts and the target chains",
         (f"**Done on the contracts and their forks**: plan, step, skip, abort, expire; `MAX_BATCH` = {batch[0]} (was 50; a step of 50 does not fit); a worst-case step of {batch[0]} costs about {step:,} gas of transaction cost on the compiler's schedule. **Not done**: the chains' own gas accounting and per-transaction caps (RP-19)" if batch and step else "**Not run**"),
         "ADR-022, `Queue.t.sol`, `Gas.t.sol`, PC-04"),
        ("6", "A separate configuration record for `MAX_SIGNERS_PER_SET`; signer verification O(1)", (f"**Done**: PC-19 (proposal {sig[0]}, range [{sig[1]}, {sig[2]}], status PROPOSED); `verifySigner` costs the same gas for sets of 1, 2, 8 and 16 (asserted)" if sig else "**Not done**"),
         "ADR-023, `Registries.t.sol`, `config/pc_records.json`"),
        ("7", "Compile and test the actual contracts; report the five classes separately",
         (f"**Done**: §0 above keeps them apart; the contracts: {t['passed']} passed, {t['failed']} failed, {t['skipped']} skipped" if t else "**Not run**"), "§14, `contracts-test-run.json`"),
        ("8", "Execute the ten wallet-lab run sets with named reviewers and real wallets", "**Not done, and not doable by an engineer alone**: it needs real wallets and named people. No record was created or simulated", "`evidence/wallet-lab-kit/`"),
        ("9", "C-11 stays unmet until canonical EIP-712 types, cross-language hashes, wallet signatures, a versioning policy and two reviewer approvals are complete",
         "**Holds: C-11 is unmet** (see the readiness block at the top; its parts are listed there one by one)", "`tools/freeze_readiness.py`, `eip712/types.json` (`versioning`)"),
        ("10", "Re-run `freeze_readiness` after the above; report every unmet condition without waiver", f"**Done: NOT READY** ({ready_met} of {ready_total} conditions met)", "§10"),
    ]
    return tbl(["#", "Item of the corrective instruction", "Result", "Evidence"], rows)


def section(d, pin_fork):
    L = []
    A = L.append
    r, t, m, f, lp, fz = d["report"], d["tests"], d["mut"], d["forks"], d["loops"], d["frozen"]
    A("## 14. The FastPay contracts")
    A("")
    A("The contracts of `I:\\CryptoGateway\\contracts` are the code that would be deployed; this section reports them and only them. The reference model of §6, the Permit2 rebuild "
      "(§8), the Permit2 forks (§7) and the wallet lab (§9) are other evidence and are reported there.")
    A("")
    if not r:
        A("**Not run.**")
        return L
    A("### 14.1 Settings and sizes")
    A("")
    s = r["settings"]
    A(f"Frozen settings (`contracts/frozen-settings.json`, equal to `contracts/foundry.toml`): solc {fz['solc']}, EVM {fz['evmVersion']}, via-IR {fz['viaIR']}, optimizer {fz['optimizer']['runs']} runs, "
      f"bytecode hash `{fz['metadata']['bytecodeHash']}`, CBOR metadata {fz['metadata']['appendCBOR']}, no `code_size_limit` override. Target: at most {fz['runtimeSizeTargetBytes']:,} bytes of runtime code per contract; EIP-170: {fz['eip170Bytes']:,}.")
    A("")
    rows = []
    for n, c in sorted(r["contracts"].items()):
        if not c["file"].startswith("src/") or c["runtimeBytes"] <= 100:
            continue
        rows.append((n, f"{c['runtimeBytes']:,}", f"{c['marginToTarget']:,}", f"{c['marginToEip170']:,}", "yes" if c["sameAsForge"] else str(c["sameAsForge"]),
                     ", ".join(f"{k}:{v}" for k, v in c["forbiddenOpcodes"].items() if v) or "none", ", ".join(c.get("externalCallTargets", [])) or "-"))
    L += tbl(["Contract", "Runtime bytes", "To the 22,000 target", "To EIP-170", "Same bytes as forge's build", "Forbidden opcodes found", "Typed external call targets"], rows)
    A("")
    A("Low-level calls in the sources: " + "; ".join(f"`{i['instruction']}` at `{i['file']}:{i['line']}` ({'allowed: ' + i['reason'] if i['allowed'] else 'NOT ALLOWED'})" for i in r["lowLevelCalls"]) + ".")
    A("")
    A(f"Verdict of `tools/contracts_report.py`: **{r['verdict']}**" + (": " + "; ".join(r["problems"]) if r["problems"] else "") + ".")
    A("")
    A("### 14.2 Loop bounds")
    A("")
    if lp:
        ep = [e for e in lp["entryPoints"] if e["stateChanging"] and e["iterationBound"]]
        ep = sorted(ep, key=lambda e: -e["iterationBound"])[:8]
        A(f"`tools/loop_audit.py --project contracts`: {len(lp['loops'])} loops, {len(lp['problems'])} problems, verdict **{lp['verdict']}**. Every loop carries its bound and the constant that bounds it; "
          "calls through interfaces are followed to the contract that implements them. The entry points with the largest bound of iterations (a bound, not gas):")
        A("")
        L += tbl(["Entry point", "Iteration bound", "At the hard maximum of the safe ranges"], [(f"{e['contract']}.{e['function']}", e["iterationBound"], e["iterationBoundAtHardMaxOfTheSafeRange"]) for e in ep])
        A("")
    A("### 14.3 Tests")
    A("")
    if t:
        L += tbl(["Suite", "Passed", "Failed", "Skipped"], [(x["suite"], x["passed"], x["failed"], x["skipped"]) for x in t["suites"]])
        A("")
        A(f"Total {t['total']}: **{t['passed']} passed, {t['failed']} failed, {t['skipped']} skipped** ({t['forge']}). The skipped tests are the fork variants of the suites, which need a fork "
          "(§14.5). The stateful fuzz of the real contracts recomputes its invariants from a ghost list of every mandate: " + "; ".join(f"`{k}`: {v['runs']} runs, {v['calls']} calls" for k, v in t["invariants"].items()) + ".")
        A("")
        if t.get("handlerCoverage"):
            A("What the last run of the stateful fuzz actually did (so that a campaign that only hits refusals cannot pass unnoticed): " + "; ".join(c.replace("coverage: ", "") for c in t["handlerCoverage"][:10]) + ".")
            A("")
        A("Differential evidence against the reference model: `Differential.t.sol` runs the contract's `containedMask` on every one of the 742 exported containment tuples, the contract's terms and snapshot hashes on the "
          "nine exported hash cases (TH_00 to TH_08), and the fiat valuation of the exported vectors through the real router and ledger. The golden EIP-712 test is generated for the contracts' library too and agrees with "
          "Foundry's own EIP-712 cheat codes.")
        A("")
    A("### 14.4 Mutation testing of the contracts")
    A("")
    if m:
        c = m["counts"]
        A(f"`tools/contracts_mutation.py` changes the contracts one text at a time and runs the suites (without the gas measurements and the stateful fuzz): **{c['killed']} killed, {c['survived']} survived, "
          f"{c['invalid']} did not compile** out of {c['mutants']}. " + (
              "Survivors, each with the reason it is accepted: " + "; ".join(f"{x['id']} ({m['equivalent'].get(x['id'], 'NOT EXPLAINED')})" for x in m["results"] if x["status"] == "SURVIVED") + "." if c["survived"] else "No mutant survived."))
        A("")
        by = {}
        for x in m["results"]:
            by.setdefault(x["file"], [0, 0])
            by[x["file"]][0 if x["status"] == "KILLED" else 1] += 1
        L += tbl(["Source file", "Killed", "Not killed (survived or invalid)"], [(k, v[0], v[1]) for k, v in sorted(by.items())])
        A("")
        A("A kill rate shows that the tests are sensitive to these bugs; it does not show that no other bug exists.")
        A("")
    else:
        A("Not run.")
        A("")
    A("### 14.5 Gas, `MAX_BATCH` and the forks")
    A("")
    if t:
        g = {x["name"]: x["value"] for x in t["gas"]}
        rows = [(k, f"{v:,}") for k, v in g.items() if any(w in k for w in ("activate", "charge", "revoke", "k=10", "marginal", "extrapolated", "worst-case", "budget", "MAX_BATCH"))]
        L += tbl(["Measurement (cold accounts and slots, compiler's EVM schedule)", "Gas"], rows)
        A("")
        b = pc_value(d, "MAX_BATCH")
        A(f"`MAX_BATCH` is provisionally **{b[0]}** (PC-04, range [{b[1]}, {b[2]}]): a step of {b[0]} worst-case entries (three tokens each, eight exposed tokens on each router, old allowances locked down) "
          "must fit half of 2^24 gas (the per-transaction cap of EIP-7825, an assumption about the launch chains that this repository did not verify); the guard test fails if the constant and the contracts drift apart. "
          "A step of 50, the value of OD-026, can no longer be run (the queue refuses it); from the marginal cost of an entry (two recorded steps) its cost extrapolates to the figure in the table above, about 30 million gas.")
        A("")
    if f:
        rows = []
        for c in f["chains"]:
            used = c["attempts"][c.get("usedAttempt", -1)] if c["attempts"] else {}
            rows.append((f"{c['name']} ({c['chainId']})", c["block"], f"`{c['blockHash'][:18]}…`", used.get("passed"), used.get("failed"), used.get("skipped"), c["result"]))
        L += tbl(["Chain", "Fork block", "Block hash", "Passed", "Failed", "Skipped", "Result"], rows)
        A("")
        A("On each fork the suites of the contracts (charge, quote, Pay Once, successor, queue, gas) run against the real Permit2 of the chain. The gas schedule is the compiler target's, not the chain's: "
          "Arbitrum's gas accounting (ArbOS, the L1 data component) is **not modelled**, and no chain's per-transaction gas cap is enforced by a fork. RP-19 is therefore not closed.")
        A("")
    else:
        A("The fork run of the contracts has not been recorded.")
        A("")
    A("### 14.6 What is not built")
    A("")
    A("Router v1.0 as built has `charge` and `payOnceWithSignature` only. **Not built in this pass:** `chargeInitial`, `payOnceWithSignatureAndPermit`, `payOnceWithAuthorization`, `payOnce`, `RefundManager`, "
      "`EmergencyGuardian`, a plan opened by relayed signature (needs a typed plan message, which types.json does not have), the typed charge request (F-19), deployment scripts, and a manifest of deployed addresses. "
      "The `recipientPolicy` of a mandate is opaque (F-18).")
    A("")
    return L


LIMITS = [
    "The **FastPay contracts** are tested, mutation-tested and fork-run by the people who wrote them, with tests that the same people wrote. Nothing here has been reviewed by a second person or audited.",
    "The contracts' gas is measured on the EVM gas schedule of the compiler's target. The chains' own accounting (Arbitrum's in particular) and their per-transaction gas caps are not measured: RP-19 is open for them.",
    "A fork test runs the contracts against a chain's real Permit2 and state through public RPC providers: it depends on the network and on those providers.",
    "Four implementations of EIP-712 agree with each other, with the real Permit2 and with Foundry's own cheat codes; none of them has been shown to a wallet. Wallet rendering and signatures (WL-16/17/27 and the ten run sets) are untested, and C-11 stays unmet.",
    "The Permit2 comparison is software-level; Foundry's sigstore attestations were recorded, not verified.",
    "The owners' approval of every constant (all 19 records are PROPOSED), of the type strings and of the architecture (ADR-020 to ADR-023), the E2 review of Permit2 and the wallet lab remain human work.",
]

REPRODUCE = [
    "python -I spec/tools/export_eip712.py --check                 # the generated types, in both projects",
    "python -I spec/toolchain/forge.py --project contracts test    # the actual contracts",
    "python -I spec/tools/contracts_tests.py                       # record that run (contracts-test-run.json)",
    "python -I spec/tools/contracts_report.py                      # settings, sizes, opcodes, low-level calls, targets",
    "python -I spec/tools/loop_audit.py --project contracts        # loop bounds of the contracts",
    "python -I spec/tools/contracts_mutation.py                    # mutation testing of the contracts (about an hour)",
    "python -I spec/tools/fork_run.py --project contracts          # the contracts on the three forks (needs network)",
]
