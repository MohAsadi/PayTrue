#!/usr/bin/env python3
"""Check the pinned Permit2 reference of document 16 section 5 (revision 0.5).

What this establishes, and what it does not
  * ESTABLISHES (E1 pinned / E3 on chain): the commit, tag and source file blobs that were read; the runtime code deployed at the canonical
    address on each launch chain (length, hash, the two per-chain immutables, a chain-independent masked hash); that the set of 4-byte
    selectors in the deployed dispatcher equals the set of external functions of the pinned source (no extra function).
  * DOES NOT ESTABLISH: that the pinned source compiles to the deployed bytecode (needs a rebuild with the recorded compiler settings;
    EV-P01 stays open) and does not replace the named human review at E2 (PR-01...PR-16).

Run:  python -I spec/tools/permit2_pin_check.py              offline: the recorded evidence is internally consistent
      python -I spec/tools/permit2_pin_check.py --online     also re-read the chains and the repository (needs network; read-only requests)
Evidence file: spec/evidence/permit2/pin.json (written by hand from a recorded run on 2026-10-16; `--online --update` rewrites the
observation fields but never the pin).
"""
import hashlib
import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC = pathlib.Path(__file__).resolve().parent.parent
EVID = SPEC / "evidence" / "permit2" / "pin.json"
UA = {"User-Agent": "fastpay-spec-review"}

EXPECTED_FUNCTIONS = [
    "allowance(address,address,address)", "approve(address,address,uint160,uint48)",
    "permit(address,((address,uint160,uint48,uint48),address,uint256),bytes)",
    "permit(address,((address,uint160,uint48,uint48)[],address,uint256),bytes)",
    "transferFrom(address,address,uint160,address)", "transferFrom((address,address,uint160,address)[])",
    "lockdown((address,address)[])", "invalidateNonces(address,address,uint48)", "DOMAIN_SEPARATOR()",
    "nonceBitmap(address,uint256)",
    "permitTransferFrom(((address,uint256),uint256,uint256),(address,uint256),address,bytes)",
    "permitWitnessTransferFrom(((address,uint256),uint256,uint256),(address,uint256),address,bytes32,string,bytes)",
    "permitTransferFrom(((address,uint256)[],uint256,uint256),(address,uint256)[],address,bytes)",
    "permitWitnessTransferFrom(((address,uint256)[],uint256,uint256),(address,uint256)[],address,bytes32,string,bytes)",
    "invalidateUnorderedNonces(uint256,uint256)",
]


def selector(sig):
    return V.keccak256(sig.encode())[:4].hex()


def push4_values(code):
    out, i = set(), 0
    while i < len(code):
        op = code[i]
        if 0x60 <= op <= 0x7F:
            n = op - 0x5F
            if n == 4:
                out.add(code[i + 1:i + 5].hex())
            i += 1 + n
        else:
            i += 1
    return out


def domain_separator(chain_id, address):
    return V.keccak256(V.keccak256(b"EIP712Domain(string name,uint256 chainId,address verifyingContract)")
                       + V.keccak256(b"Permit2") + V.u(chain_id) + V.addr(address))


def mask(code, chain_id, address, offs):
    m = bytearray(code)
    for o, w in ((offs["chainId"], V.u(chain_id)), (offs["domainSeparator"], domain_separator(chain_id, address))):
        if code[o:o + 32] != w:
            return None
        m[o:o + 32] = bytes(32)
    return V.keccak256(bytes(m)).hex()


def rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers=dict(UA, **{"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def offline(ev):
    bad = []
    addr = ev["address"]
    for cid, c in ev["chains"].items():
        want = domain_separator(int(cid), addr).hex()
        if c["domainSeparator"] != want:
            bad.append(f"chain {cid}: recorded domain separator differs from the EIP712.sol derivation")
        if len(c["providers"]) < 2:
            bad.append(f"chain {cid}: fewer than two independent providers recorded")
    masked = {c["maskedCodeHash"] for c in ev["chains"].values()}
    if len(masked) != 1 or ev["maskedCodeHash"] not in masked:
        bad.append("masked code hashes differ across chains or from the pin")
    if len(ev["selectors"]) != len(EXPECTED_FUNCTIONS) or sorted(ev["selectors"]) != sorted(selector(s) for s in EXPECTED_FUNCTIONS):
        bad.append("recorded selector set differs from the external functions of the pinned source")
    for f in ev["sourceBlobs"]:
        if len(f["gitBlobSha1"]) != 40 or len(f["sha256"]) != 64:
            bad.append("malformed blob record " + f["path"])
    if ev["pin"]["commit"] != ev["tag"]["commit"]:
        bad.append("the pinned commit is not the commit of the recorded tag")
    return bad


def online(ev):
    bad = []
    addr = ev["address"]
    for cid, c in ev["chains"].items():
        block, hashes = None, {}
        for url in c["providers"]:
            try:
                if block is None:
                    block = hex(int(rpc(url, "eth_blockNumber", [])["result"], 16) - 64)
                code = bytes.fromhex(rpc(url, "eth_getCode", [addr, block])["result"][2:])
            except Exception as e:  # noqa: BLE001
                print(f"    chain {cid} {url}: {type(e).__name__}")
                continue
            hashes[url] = (V.keccak256(code).hex(), len(code), mask(code, int(cid), addr, ev["immutableOffsets"]),
                           push4_values(code) == {selector(s) for s in EXPECTED_FUNCTIONS})
        vals = {(h, n, m, s) for h, n, m, s in hashes.values()}
        ok = len(hashes) >= 2 and len(vals) == 1 and next(iter(vals))[0] == c["codeHash"] and next(iter(vals))[2] == ev["maskedCodeHash"] \
            and next(iter(vals))[3] and next(iter(vals))[1] == ev["runtimeCodeLength"]
        print(f"    chain {cid}: providers answering {len(hashes)}, code hash {'matches' if ok else 'DIFFERS'}")
        if not ok:
            bad.append(f"chain {cid}: on-chain code differs from the record, or fewer than two providers answered")
    pin = ev["pin"]
    try:
        tree = json.loads(get(f"https://api.github.com/repos/{pin['repo']}/git/trees/{pin['commit']}?recursive=1"))
        shas = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "blob"}
        for f in ev["sourceBlobs"]:
            if shas.get(f["path"]) != f["gitBlobSha1"]:
                bad.append("repository blob differs: " + f["path"])
        print(f"    repository: {len(ev['sourceBlobs'])} recorded blobs compared with commit {pin['commit'][:10]}")
    except Exception as e:  # noqa: BLE001
        bad.append(f"repository read failed: {type(e).__name__}")
    return bad


def main():
    ev = json.loads(EVID.read_text(encoding="utf-8"))
    bad = offline(ev)
    print(f"offline: {len(ev['chains'])} chains, {len(ev['sourceBlobs'])} source blobs, {len(ev['selectors'])} selectors: {'consistent' if not bad else 'INCONSISTENT'}")
    if "--online" in sys.argv:
        bad += online(ev)
    for b in bad:
        print("  FAIL", b)
    print("PERMIT2 PIN CHECK PASSED" if not bad else "PERMIT2 PIN CHECK FAILED")
    print("note: source-to-bytecode equality (rebuild) and the E2 review are NOT established by this tool")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
