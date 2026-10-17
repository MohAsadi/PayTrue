#!/usr/bin/env python3
"""Export the Permit2 evidence of this repository as fixtures for the Foundry tests.

    python -I spec/tools/export_permit2_fixtures.py --write | --check

Reads  evidence/permit2/pin.json and evidence/permit2/rebuild.json and the two code files of the rebuild (it recomputes their hashes);
writes foundry/vectors/permit2-creation-code.hex, permit2-runtime-code.hex (the rebuilt code with zero immutables) and
permit2-evidence.json (hashes, immutable offsets and names, per-chain deployed-code hashes, chain ids, the CREATE2 inputs).
The Foundry tests refuse to run on a fixture whose hash differs from the pinned one.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EV = ROOT / "evidence" / "permit2"
VEC = ROOT / "foundry" / "vectors"


def build():
    pin = json.loads((EV / "pin.json").read_text(encoding="utf-8"))
    rb = json.loads((EV / "rebuild.json").read_text(encoding="utf-8"))
    creation = bytes.fromhex((EV / "permit2-creation-code.hex").read_text().strip())
    runtime = bytes.fromhex((EV / "permit2-runtime-code.hex").read_text().strip())
    assert V.hx(V.keccak256(creation)) == rb["creationCodeKeccak256"], "creation code does not match rebuild.json"
    assert len(creation) == rb["creationCodeLength"] and len(runtime) == rb["runtimeCodeLength"]
    assert V.hx(V.keccak256(runtime)) == rb["runtimeCodeKeccak256WithZeroImmutables"], "runtime code does not match rebuild.json"
    assert rb["allMatch"] is True and rb["create2"]["matches"] is True, "the rebuild record does not claim a reproduction"
    names = {}
    for ast, refs in rb["immutableReferencesByAstId"].items():
        for r in refs:
            names[rb["immutableVariables"][ast]["name"]] = r["start"]
    chains = {}
    for cid, c in rb["comparison"].items():
        chains[cid] = dict(name=pin["chains"][cid]["name"], deployedCodeKeccak256=c["deployedKeccak256"],
                           rebuiltWithImmutablesFilledKeccak256=c["rebuiltWithImmutablesFilledKeccak256"],
                           recordedDomainSeparator="0x" + pin["chains"][cid]["domainSeparator"])
        assert c["deployedKeccak256"] == c["rebuiltWithImmutablesFilledKeccak256"] and c["ok"] is True
    ev = dict(schema=1, source="evidence/permit2/rebuild.json", pinnedCommit=rb["sourceCommit"] if "sourceCommit" in rb else None,
              canonicalAddress=rb["create2"]["canonicalAddress"], deployer=rb["create2"]["deployer"], salt=rb["create2"]["salt"],
              creationCodeKeccak256=rb["creationCodeKeccak256"], creationCodeLength=len(creation),
              runtimeCodeKeccak256WithZeroImmutables=rb["runtimeCodeKeccak256WithZeroImmutables"], runtimeCodeLength=len(runtime),
              immutableOffsets=names, chains=chains,
              deployerProxyCodeKeccak256=next(iter(rb["deployerProxy"].values()))["code"]["keccak256"])
    assert len({v["code"]["keccak256"] for v in rb["deployerProxy"].values()}) == 1
    return {
        VEC / "permit2-creation-code.hex": "0x" + creation.hex(),
        VEC / "permit2-runtime-code.hex": "0x" + runtime.hex(),
        VEC / "permit2-evidence.json": json.dumps(ev, indent=1) + "\n",
    }


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [str(p.relative_to(ROOT)) for p, t in files.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        if bad:
            print("stale permit2 fixtures:", ", ".join(bad))
            return 1
        print("permit2 fixtures: up to date")
        return 0
    if "--write" in argv:
        VEC.mkdir(parents=True, exist_ok=True)
        for p, t in files.items():
            p.write_text(t, encoding="utf-8", newline="\n")
            print("wrote", p.relative_to(ROOT))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
