#!/usr/bin/env python3
"""Reproducible rebuild of Permit2 at the pinned commit and the CREATE2 / deployed-code comparison (document 16 section 5.5, EV-P01).

Run:   python -I spec/tools/permit2_rebuild.py --write     build (isolated), compare with the chains, write the evidence files
       python -I spec/tools/permit2_rebuild.py --verify    re-run the comparison offline from the recorded files (no build, no network)
       python -I spec/tools/permit2_rebuild.py --online    like --verify but re-read the deployed code from the chains

What it does, in order (every step aborts the run when it fails; nothing is "assumed to match")
  1. Inputs. `toolchain/fetch_toolchain.py --verify` (SHA-256 of forge, solc and every archive) and `toolchain/tree-verification.json` (every extracted
     tree equals the git tree of its pinned commit, blob by blob, with no extra file) must both be clean; the Permit2 tree must equal the commit of
     evidence/permit2/pin.json; every src blob must equal the recorded Git blob SHA-1.
  2. Isolated build. The verified tree is copied to a fresh empty directory under toolchain/isolated/<run>/; `forge build --offline --force --build-info`
     runs there with a scrubbed environment (no inherited variables except the Windows system root, HOME/USERPROFILE/APPDATA pointing at an empty
     directory, proxies pointing at a closed port, FOUNDRY_OFFLINE=true, FOUNDRY_SOLC = the verified solc 0.8.17). It compiles; it executes no script
     and no test (the `ffi = true` of the project's foundry.toml is irrelevant to `forge build`). This is a software-level isolation, NOT an OS sandbox.
  3. Independent driver. The exact standard-JSON input that forge handed to solc (build-info) is fed to solc directly; the creation and runtime code
     must equal forge's.
  4. CREATE2. `keccak256(0xff ++ deployer ++ SALT ++ keccak256(creationCode))[12:]` against the canonical address.
  5. Immutables. solc's `immutableReferences` give the exact byte ranges of the two immutables; the values expected there on each chain (chain id, domain
     separator derived from EIP712.sol) are computed independently.
  6. Deployed code. The code read from each chain (>= 2 providers) is compared byte for byte with the rebuilt runtime code. The result lists EVERY
     differing byte range, whether it lies inside an immutableReference, whether the deployed bytes equal the expected immutable value, and the number
     of remaining differences outside the references (which must be zero for the reproduction to be reported as successful).
"""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC = pathlib.Path(__file__).resolve().parent.parent
TC = SPEC / "toolchain"
TREE = TC / "permit2-build" / "permit2"
EVID = SPEC / "evidence" / "permit2"
PIN = EVID / "pin.json"
OUT = EVID / "rebuild.json"
WIN = platform.system().lower() == "windows"
CANONICAL = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
DEPLOYER = "0x4e59b44847b379578588920cA78FbF26c0B4956C"     # the deterministic deployment proxy that `new X{salt: S}` uses in a forge script
UA = {"User-Agent": "fastpay-spec-review"}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def lock():
    return json.loads((TC / "toolchain.lock.json").read_text(encoding="utf-8"))


def exe(name):
    return TC / "bin" / (name + (".exe" if WIN else ""))


def solc_path():
    p = "windows-amd64" if WIN else "linux-amd64"
    return TC / "solc" / lock()["solc"]["versions"]["0.8.17"][p]["file"]


def step1_inputs(pin):
    r = subprocess.run([sys.executable, "-I", str(TC / "fetch_toolchain.py"), "--verify"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("toolchain verification failed:\n" + r.stdout + r.stderr)
    trees = json.loads((TC / "tree-verification.json").read_text(encoding="utf-8"))["trees"]
    bad = [t["name"] for t in trees if not t["verified"]]
    if bad:
        sys.exit("trees not verified against their commits: " + ", ".join(bad))
    lk = lock()["sources"]
    by = {t["name"]: t for t in trees}
    for name, s in lk.items():
        if by[name]["commit"] != s["commit"]:
            sys.exit(f"tree record for {name} is for another commit")
    if lk["permit2"]["commit"] != pin["pin"]["commit"]:
        sys.exit("the Permit2 tree is not the pinned commit of evidence/permit2/pin.json")
    for b in pin["sourceBlobs"]:
        f = TREE / b["path"]
        if not f.exists() or git_blob_sha1(f.read_bytes()) != b["gitBlobSha1"]:
            sys.exit("a pinned blob differs: " + b["path"])
    deploy = (TREE / "script" / "DeployPermit2.s.sol").read_text(encoding="utf-8")
    salt_hex = "d3af2663da51c10215000000"
    if salt_hex not in deploy or "new Permit2{salt: SALT}" not in deploy:
        sys.exit("the deploy script does not carry the expected salt and constructor call")
    return {"toolchainVerified": True, "treesVerified": {t["name"]: {"commit": t["commit"], "rootTree": t["rootTree"], "blobs": t["blobsInCommit"]} for t in trees},
            "archives": {n: {"url": s["url"], "commit": s["commit"], "sha256": s["sha256"]} for n, s in lk.items() if n not in ("forge-std",)}}


def isolated_env(home):
    env = {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"), "TEMP": str(home / "tmp"), "TMP": str(home / "tmp"),
           "HOME": str(home), "USERPROFILE": str(home), "APPDATA": str(home / "appdata"), "LOCALAPPDATA": str(home / "localappdata"),
           "PATH": str(TC / "bin"), "FOUNDRY_SOLC": str(solc_path()), "FOUNDRY_OFFLINE": "true", "FOUNDRY_DISABLE_NIGHTLY_WARNING": "1", "NO_COLOR": "1",
           "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "ALL_PROXY": "http://127.0.0.1:9"}
    for k in ("tmp", "appdata", "localappdata"):
        (home / k).mkdir(parents=True, exist_ok=True)
    return env


def watch_network(proc, seen, stop):
    """Sample `netstat` while the build runs and record every TCP row of the build's process that is not loopback (monitoring, not enforcement)."""
    import threading  # noqa: F401
    n = 0
    while not stop.is_set():
        try:
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=20).stdout
            n += 1
            for ln in out.splitlines():
                parts = ln.split()
                if len(parts) >= 5 and parts[-1] == str(proc.pid):
                    foreign = parts[2]
                    if not (foreign.startswith(("127.0.0.1:", "[::1]:", "0.0.0.0:", "[::]:"))):
                        seen.add(ln.strip())
        except Exception:  # noqa: BLE001
            pass
        stop.wait(0.3)
    seen.add(f"__samples__ {n}")


def step2_build(run):
    import threading
    tree = run / "tree"
    shutil.copytree(TREE, tree)
    home = run / "home"
    home.mkdir()
    env = isolated_env(home)
    cmd = [str(exe("forge")), "build", "--root", str(tree), "--offline", "--force", "--build-info"]
    with open(run / "forge-build.log", "w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, cwd=str(tree), env=env, stdout=log, stderr=subprocess.STDOUT)
        seen, stop = set(), threading.Event()
        t = threading.Thread(target=watch_network, args=(proc, seen, stop), daemon=True)
        t.start()
        rc = proc.wait(timeout=3600)
        stop.set()
        t.join(timeout=30)
    log_text = (run / "forge-build.log").read_text(encoding="utf-8", errors="replace")
    if rc:
        sys.exit("forge build failed (see " + str(run / "forge-build.log") + "):\n" + log_text[-1800:])
    art = json.loads((tree / "out" / "Permit2.sol" / "Permit2.json").read_text(encoding="utf-8"))
    infos = sorted((tree / "out" / "build-info").glob("*.json"))
    cfg = subprocess.run([str(exe("forge")), "config", "--root", str(tree), "--json"], cwd=str(tree), env=env, capture_output=True, text=True, encoding="utf-8")
    config = json.loads(cfg.stdout) if cfg.returncode == 0 else {}
    net = {"method": "software only: FOUNDRY_OFFLINE, --offline, proxies at a closed port; the build process was sampled with netstat",
           "samples": next((int(x.split()[1]) for x in seen if x.startswith("__samples__")), 0),
           "nonLoopbackTcpRowsObserved": sorted(x for x in seen if not x.startswith("__samples__")), "environmentVariables": sorted(env)}
    return tree, art, infos, subprocess.run([str(exe("forge")), "--version"], capture_output=True, text=True).stdout.strip(), cmd, config, net, log_text


def import_closure(output_sources, roots):
    graph = {}
    for path, s in output_sources.items():
        graph[path] = [n["absolutePath"] for n in s["ast"]["nodes"] if n["nodeType"] == "ImportDirective"]
    seen, todo = set(), list(roots)
    while todo:
        p = todo.pop()
        if p in seen or p not in graph:
            continue
        seen.add(p)
        todo.extend(graph[p])
    return seen


def dependency_roles(info, dep_dirs):
    """For each dependency directory: how many files are in the compile unit and which kind of root reaches them."""
    out_src = info["output"]["sources"]
    paths = sorted(out_src)
    prod = import_closure(out_src, ["src/Permit2.sol"])
    script = import_closure(out_src, [p for p in paths if p.startswith("script/")])
    test = import_closure(out_src, [p for p in paths if p.startswith("test/")])
    roles = {}
    for name, d in dep_dirs.items():
        # a file belongs to the deepest dependency directory that contains it
        files = [p for p in paths if p.startswith(d + "/") and not any(o != d and o.startswith(d + "/") and p.startswith(o + "/") for o in dep_dirs.values())]
        roles[name] = {"directory": d, "filesInCompileUnit": len(files),
                       "reachedFromProductionContract": sum(1 for p in files if p in prod), "reachedFromDeploymentScript": sum(1 for p in files if p in script),
                       "reachedFromTests": sum(1 for p in files if p in test),
                       "reachedFromNoRoot": sum(1 for p in files if p not in prod and p not in script and p not in test)}
        r = roles[name]
        r["requiredFor"] = ("production compilation (the contract that is deployed)" if r["reachedFromProductionContract"] else
                            "deployment-script compilation" if r["reachedFromDeploymentScript"] else
                            "test compilation" if r["reachedFromTests"] else
                            "not compiled (tooling only: the compile unit contains no file of it)" if r["filesInCompileUnit"] == 0 else "compiled but reached from no root")
    src_files = [p for p in paths if p.startswith("src/")]
    roles["_src"] = {"filesInCompileUnit": len(src_files), "reachedFromProductionContract": sum(1 for p in src_files if p in prod)}
    roles["_unit"] = {"files": len(paths), "script": sum(1 for p in paths if p.startswith("script/")), "test": sum(1 for p in paths if p.startswith("test/")),
                      "src": len(src_files), "lib": sum(1 for p in paths if p.startswith("lib/"))}
    return roles


def immutable_variables(info, refs):
    """Which Solidity variables the AST ids of the compiler's immutableReferences are (proves what sits at each offset)."""
    want, names = set(refs), {}

    def walk(n, path):
        if isinstance(n, dict):
            if n.get("nodeType") == "VariableDeclaration" and str(n.get("id")) in want:
                names[str(n["id"])] = {"name": n["name"], "sourceUnit": path, "mutability": n.get("mutability"), "type": n["typeDescriptions"]["typeString"]}
            for v in n.values():
                walk(v, path)
        elif isinstance(n, list):
            for v in n:
                walk(v, path)
    for path, s in info["output"]["sources"].items():
        walk(s["ast"], path)
    return names


def strip_metadata(code):
    """Solidity appends a CBOR-encoded metadata block; its length is in the last two bytes."""
    n = int.from_bytes(code[-2:], "big")
    return code[:-(n + 2)], code[-(n + 2):]


def step3_solc_direct(infos):
    """Feed the exact input forge gave solc to solc directly; return the Permit2 creation and runtime code."""
    found = None
    for f in infos:
        info = json.loads(f.read_text(encoding="utf-8"))
        inp = json.loads(json.dumps(info["input"]))
        if "src/Permit2.sol" not in inp["sources"]:
            continue
        # forge adds its own path keys to the standard-JSON input (they become command-line flags); solc itself does not accept them
        dropped = {"top": [k for k in inp if k not in ("language", "sources", "settings")],
                   "settings": [k for k in inp["settings"] if k not in ("remappings", "optimizer", "evmVersion", "viaIR", "debug", "metadata", "libraries", "outputSelection", "stopAfter", "modelChecker")]}
        inp = {k: v for k, v in inp.items() if k in ("language", "sources", "settings")}
        inp["settings"] = {k: v for k, v in inp["settings"].items() if k not in dropped["settings"]}
        print("solc direct: keys removed from forge's input (forge-only):", dropped)
        r = subprocess.run([str(solc_path()), "--standard-json"], input=json.dumps(inp), capture_output=True, text=True, encoding="utf-8")
        out = json.loads(r.stdout)
        errs = [e for e in out.get("errors", []) if e["severity"] == "error"]
        if errs:
            sys.exit("solc (direct) errors: " + errs[0]["formattedMessage"][:300])
        evm = out["contracts"]["src/Permit2.sol"]["Permit2"]["evm"]
        found = (info, bytes.fromhex(evm["bytecode"]["object"]), bytes.fromhex(evm["deployedBytecode"]["object"]), evm["deployedBytecode"]["immutableReferences"])
        break
    if not found:
        sys.exit("no build-info contains src/Permit2.sol")
    return found


def create2(salt, init):
    return "0x" + V.keccak256(b"\xff" + bytes.fromhex(DEPLOYER[2:]) + salt + V.keccak256(init))[12:].hex()


def domain_separator(chain_id):
    return V.keccak256(V.keccak256(b"EIP712Domain(string name,uint256 chainId,address verifyingContract)") + V.keccak256(b"Permit2")
                       + V.u(chain_id) + V.addr(CANONICAL))


def rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers=dict(UA, **{"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def read_chain_code_at(cid, providers, address):
    got, block = {}, None
    for url in providers:
        try:
            if block is None:
                block = hex(int(rpc(url, "eth_blockNumber", [])["result"], 16) - 64)
            got[url] = bytes.fromhex(rpc(url, "eth_getCode", [address, block])["result"][2:])
        except Exception:  # noqa: BLE001
            continue
    if len(got) < 2 or len({v for v in got.values()}) != 1:
        sys.exit(f"chain {cid}: fewer than two providers agree on the code of {address}")
    code = next(iter(got.values()))
    return int(block, 16), list(got), {"length": len(code), "keccak256": "0x" + V.keccak256(code).hex()}


def read_chain_code(cid, providers):
    blk, used, info = read_chain_code_at(cid, providers, CANONICAL)
    # the code itself (the helper above returns only its hash for the deployer proxy)
    code = None
    for url in used:
        try:
            code = bytes.fromhex(rpc(url, "eth_getCode", [CANONICAL, hex(blk)])["result"][2:])
            break
        except Exception:  # noqa: BLE001
            continue
    if code is None or "0x" + V.keccak256(code).hex() != info["keccak256"]:
        sys.exit(f"chain {cid}: could not re-read the deployed code consistently")
    return blk, used, code


def diff_ranges(a, b):
    out, i = [], 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def step6_compare(runtime, refs, deployed_by_chain):
    """Byte-for-byte comparison of the rebuilt runtime code with the deployed code of each chain."""
    ranges = sorted({(r["start"], r["length"]) for rs in refs.values() for r in rs})
    res = {}
    for cid, dep in deployed_by_chain.items():
        if len(dep) != len(runtime):
            res[cid] = {"lengthEqual": False, "rebuilt": len(runtime), "deployed": len(dep), "ok": False}
            continue
        diffs = diff_ranges(runtime, dep)
        expected = {int(cid): None}
        words = {}
        # the two immutables: which one is at which reference is learned from the deployed bytes, then checked against independently computed values
        cand = {V.u(int(cid)).hex(): "chainId", domain_separator(int(cid)).hex(): "domainSeparator"}
        explained, unexplained = [], []
        for start, n in diffs:
            inside = any(s <= start and start + n <= s + ln for s, ln in ranges)
            (explained if inside else unexplained).append({"offset": start, "length": n})
        ref_report = []
        for s, ln in ranges:
            val = dep[s:s + ln].hex()
            ref_report.append({"offset": s, "length": ln, "rebuiltBytes": runtime[s:s + ln].hex(), "deployedBytes": val, "expectedImmutable": cand.get(val, "NO EXPECTED VALUE MATCHES"),
                               "rebuiltIsZeroPlaceholder": set(runtime[s:s + ln]) == {0}})
        filled = bytearray(runtime)
        for rr in ref_report:
            if rr["expectedImmutable"] != "NO EXPECTED VALUE MATCHES":
                filled[rr["offset"]:rr["offset"] + rr["length"]] = bytes.fromhex(rr["deployedBytes"])
        sr, mr = strip_metadata(bytes(filled))
        sd, md = strip_metadata(dep)
        res[cid] = {"lengthEqual": True, "differingRanges": [{"offset": s, "length": n} for s, n in diffs], "differingBytes": sum(n for _, n in diffs),
                    "metadataStripped": {"strippedCodeEqual": sr == sd, "strippedLength": len(sd), "trailersEqual": mr == md, "rebuiltTrailer": mr.hex(), "deployedTrailer": md.hex()},
                    "rangesInsideImmutableReferences": explained, "rangesOutsideImmutableReferences": unexplained,
                    "immutableReferences": ref_report, "remainingDifferencesAfterFillingBothImmutables": sum(1 for x, y in zip(filled, dep) if x != y),
                    "deployedKeccak256": "0x" + V.keccak256(dep).hex(), "rebuiltWithImmutablesFilledKeccak256": "0x" + V.keccak256(bytes(filled)).hex(),
                    "ok": (not unexplained) and all(r["expectedImmutable"] != "NO EXPECTED VALUE MATCHES" for r in ref_report)
                    and len({r["expectedImmutable"] for r in ref_report}) == len(ref_report) and bytes(filled) == dep}
    return res


def main():
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    write, verify, online = "--write" in sys.argv, "--verify" in sys.argv, "--online" in sys.argv
    if verify or online:
        old = json.loads(OUT.read_text(encoding="utf-8"))
        runtime = bytes.fromhex((EVID / "permit2-runtime-code.hex").read_text().strip())
        init = bytes.fromhex((EVID / "permit2-creation-code.hex").read_text().strip())
        refs = {"x": [{"start": r["offset"], "length": r["length"]} for r in old["immutableReferences"]]}
        salt = bytes.fromhex(old["create2"]["salt"][2:])
        deployed = {}
        for cid, c in pin["chains"].items():
            if online:
                _, _, code = read_chain_code(cid, c["providers"])
            else:
                code = bytes.fromhex((EVID / f"deployed-code-{cid}.hex").read_text().strip())
            deployed[cid] = code
        cmp_ = step6_compare(runtime, refs, deployed)
        ok = create2(salt, init).lower() == CANONICAL.lower() and all(v["ok"] for v in cmp_.values()) and V.keccak256(init).hex() == old["creationCodeKeccak256"][2:]
        print("verify:", "the recorded rebuild reproduces and matches the deployed code on every chain" if ok else "MISMATCH")
        return 0 if ok else 1

    run = TC / "isolated" / datetime.datetime.now(datetime.timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    run.mkdir(parents=True)
    inputs = step1_inputs(pin)
    tree, art, infos, forge_version, cmd, fconfig, net, build_log = step2_build(run)
    forge_init = bytes.fromhex(art["bytecode"]["object"][2:])
    forge_runtime = bytes.fromhex(art["deployedBytecode"]["object"][2:])
    info, solc_init, solc_runtime, solc_refs = step3_solc_direct(infos)
    drivers_equal = forge_init == solc_init and forge_runtime == solc_runtime
    forge_refs = art["deployedBytecode"]["immutableReferences"]
    refs_equal = sorted((r["start"], r["length"]) for rs in forge_refs.values() for r in rs) == sorted((r["start"], r["length"]) for rs in solc_refs.values() for r in rs)
    salt = bytes.fromhex("0000000000000000000000000000000000000000d3af2663da51c10215000000")
    addr = create2(salt, forge_init)
    deployed, blocks = {}, {}
    for cid, c in pin["chains"].items():
        blk, used, code = read_chain_code(cid, c["providers"])
        deployed[cid] = code
        blocks[cid] = {"block": blk, "providers": used, "length": len(code), "keccak256": "0x" + V.keccak256(code).hex()}
    cmp_ = step6_compare(forge_runtime, forge_refs, deployed)
    # sources and dependencies exactly as handed to the compiler
    srcs = info["input"]["sources"]
    source_hashes = {p: {"sha256": sha256(s["content"].encode("utf-8")), "gitBlobSha1": git_blob_sha1(s["content"].encode("utf-8"))} for p, s in sorted(srcs.items())}
    settings = info["input"]["settings"]
    # dependencies: archive record, extracted-tree hashes, submodule graph and the role of each in the compile unit
    fr = {r["name"]: r for r in json.loads((TC / "fetch-record.json").read_text(encoding="utf-8"))}
    tv = json.loads((TC / "tree-verification.json").read_text(encoding="utf-8"))["trees"]
    lk = lock()["sources"]
    dep_dirs, deps = {}, []
    for t in tv:
        if t["name"] in ("permit2", "forge-std") or not t["extractedTo"].startswith("toolchain/permit2-build/permit2/lib/"):
            continue
        rel = t["extractedTo"][len("toolchain/permit2-build/permit2/"):]
        dep_dirs[t["name"] + "@" + rel] = rel
        f = fr[t["name"]]
        deps.append({"name": t["name"], "extractedTo": rel, "repository": t["repo"], "commit": t["commit"], "archiveUrl": f["url"], "finalUrl": f["finalUrl"],
                     "redirectChain": f["redirectChain"], "archiveFilename": f["archiveFilename"], "archiveBytes": f["bytes"], "archiveSha256": f["sha256"],
                     "retrievedAt": f["retrievedAt"], "gitRootTree": t["rootTree"], "gitRootTreeRecomputedFromExtractedFiles": t["localRootTreeRecomputed"],
                     "extractedTreeSha256Listing": t["sha256Listing"], "filesHashed": t["filesHashed"], "submodulePath": t["submodulePath"],
                     "submodulesNotPresentInThisArchive": t["submoduleEntriesNotInArchive"]})
    roles = dependency_roles(info, dep_dirs)
    for d in deps:
        d["roleInCompileUnit"] = roles[d["name"] + "@" + d["extractedTo"]]
    permit2_tv = next(t for t in tv if t["name"] == "permit2")
    constructor = [e for e in art["abi"] if e["type"] == "constructor"]
    stripped_rebuilt, meta_rebuilt = strip_metadata(forge_runtime)
    res = dict(
        schema=2, tool="tools/permit2_rebuild.py", builtAt=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        toolchain=dict(forge=forge_version, forgeSha256=lock()["foundry"]["artifacts"]["windows-amd64" if WIN else "linux-amd64"]["sha256"],
                       solc=info.get("solcLongVersion"), solcSha256=lock()["solc"]["versions"]["0.8.17"]["windows-amd64" if WIN else "linux-amd64"]["sha256"]),
        isolation=dict(method="fresh empty directory, scrubbed environment, FOUNDRY_OFFLINE and --offline, proxies pointing at a closed port, no script or test executed",
                       osSandbox=False, command=cmd[1:], runDirectory=str(run.relative_to(SPEC)).replace("\\", "/")),
        inputs=inputs, sourceCommit=pin["pin"]["commit"],
        compilerSettings=dict(solc=settings.get("solc", None), optimizer=settings["optimizer"], viaIR=settings.get("viaIR"), evmVersion=settings.get("evmVersion"),
                              metadata=settings.get("metadata"), remappings=settings.get("remappings"), libraries=settings.get("libraries"),
                              outputSelection=settings.get("outputSelection")),
        linkedLibraries=settings.get("libraries") or {}, sourceCount=len(srcs), sourceHashes=source_hashes,
        drivers=dict(forgeAndSolcDirectCreationCodeEqual=forge_init == solc_init, forgeAndSolcDirectRuntimeCodeEqual=forge_runtime == solc_runtime,
                     immutableReferencesEqual=refs_equal),
        create2=dict(deployer=DEPLOYER, salt="0x" + salt.hex(), saltSource="script/DeployPermit2.s.sol at the pinned commit (SALT)", computedAddress=addr,
                     canonicalAddress=CANONICAL, matches=addr.lower() == CANONICAL.lower()),
        creationCodeLength=len(forge_init), creationCodeKeccak256="0x" + V.keccak256(forge_init).hex(),
        runtimeCodeLength=len(forge_runtime), runtimeCodeKeccak256WithZeroImmutables="0x" + V.keccak256(forge_runtime).hex(),
        immutableReferences=[{"offset": s, "length": n} for s, n in sorted({(r["start"], r["length"]) for rs in forge_refs.values() for r in rs})],
        immutableReferencesByAstId={k: v for k, v in forge_refs.items()},
        immutableVariables=immutable_variables(info, forge_refs),
        nestedForgeStdOfForgeGasSnapshot=dict(commit="2c7cbfc6fbede6d7c9e6b17afe997e3fdfe22fef", fetched=False,
                                              sourcesFromItInTheCompileUnit=[p for p in srcs if p.startswith("lib/forge-gas-snapshot/lib/")],
                                              required=bool([p for p in srcs if p.startswith("lib/forge-gas-snapshot/lib/")])),
        deployerProxy={cid: dict(zip(("block", "providers", "code"), (lambda r: (r[0], r[1], r[2]))(read_chain_code_at(cid, c["providers"], DEPLOYER)))) for cid, c in pin["chains"].items()},
        deployedCode=blocks, comparison=cmp_,
        pinnedPermit2=dict(commit=pin["pin"]["commit"], gitRootTree=permit2_tv["rootTree"], gitRootTreeRecomputedFromExtractedFiles=permit2_tv["localRootTreeRecomputed"],
                           archiveSha256=fr["permit2"]["sha256"], archiveUrl=fr["permit2"]["url"], finalUrl=fr["permit2"]["finalUrl"], extractedTreeSha256Listing=permit2_tv["sha256Listing"]),
        dependencies=deps, dependencyRoleSummary={k: v for k, v in roles.items() if k.startswith("_")},
        constructor=dict(abi=constructor, arguments="none (the ABI has no constructor inputs): initCode == creation code", initCodeKeccak256="0x" + V.keccak256(forge_init).hex()),
        evmVersion=fconfig.get("evm_version"), solcVersionPinned=fconfig.get("solc"),
        buildConfiguration={k: fconfig.get(k) for k in ("src", "test", "script", "libs", "out", "solc", "evm_version", "optimizer", "optimizer_runs", "via_ir", "bytecode_hash",
                                                       "cbor_metadata", "use_literal_content", "remappings", "auto_detect_remappings", "skip", "ignored_file_paths",
                                                       "ignored_error_codes", "deny_warnings", "extra_output", "build_info", "sparse_mode", "ffi") if k in fconfig},
        includeExcludeRules="forge default: every .sol file under src, test and script plus every file they import (including lib/); no `skip` and no `ignored_file_paths` unless the buildConfiguration above lists them",
        metadata=dict(bytecodeHash=settings.get("metadata", {}).get("bytecodeHash"), cbor=settings.get("metadata", {}).get("appendCBOR"), rebuiltRuntimeTrailerHex=meta_rebuilt.hex()),
        network=net,
    )
    res["allMatch"] = bool(res["create2"]["matches"] and drivers_equal and refs_equal and all(v["ok"] for v in cmp_.values()))
    print(f"forge {forge_version.splitlines()[0]}; solc {info.get('solcLongVersion')}; {len(srcs)} sources in the compilation unit")
    print(f"drivers: forge == solc direct: creation {forge_init == solc_init}, runtime {forge_runtime == solc_runtime}, immutable references {refs_equal}")
    print(f"creation code {len(forge_init)} bytes keccak256 {res['creationCodeKeccak256']}")
    print(f"CREATE2 {DEPLOYER} salt 0x{salt.hex()} -> {addr}; canonical {CANONICAL}; match: {res['create2']['matches']}")
    print("immutable references:", res["immutableReferences"])
    for cid, v in cmp_.items():
        print(f"chain {cid}: deployed {blocks[cid]['length']} bytes; differing bytes {v.get('differingBytes')} in {len(v.get('differingRanges', []))} ranges; "
              f"outside the immutable references: {len(v.get('rangesOutsideImmutableReferences', []))}; remaining differences after filling both immutables: "
              f"{v.get('remainingDifferencesAfterFillingBothImmutables')}; ok: {v['ok']}")
    print("REPRODUCTION SUCCESSFUL" if res["allMatch"] else "REPRODUCTION NOT ESTABLISHED")
    if write:
        OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        (EVID / "permit2-creation-code.hex").write_text(forge_init.hex() + "\n", encoding="utf-8")
        (EVID / "permit2-runtime-code.hex").write_text(forge_runtime.hex() + "\n", encoding="utf-8")
        for cid, code in deployed.items():
            (EVID / f"deployed-code-{cid}.hex").write_text(code.hex() + "\n", encoding="utf-8")
        pin["rebuild"] = {"matches": res["allMatch"], "record": "evidence/permit2/rebuild.json", "tool": "tools/permit2_rebuild.py",
                          "create2Address": addr, "builtAt": res["builtAt"], "note": "matches is true only if CREATE2, both drivers and a byte-for-byte comparison on every chain agree"}
        PIN.write_text(json.dumps(pin, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("wrote", OUT)
    return 0 if res["allMatch"] else 1


if __name__ == "__main__":
    sys.exit(main())
