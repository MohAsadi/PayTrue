#!/usr/bin/env python3
"""Verify the signatures of wallet-lab run records (document 15 section 4) and of the typed data a wallet signed during a run.

A run record is evidence only if two named people stand behind it. "Signed" means:

  * the people are registered in evidence/wallet-lab-kit/people.json (name -> Ethereum address, role, who registered it and when);
    registration is a human act and is never done by this tool;
  * `signatures.tester` and `signatures.reviewer` are EIP-191 `personal_sign` signatures, made in the person's own wallet, over the ASCII
    message   fastpay-wallet-lab-run-record:v1:<sha256 of the canonical record without its `signatures` member>
    where canonical = JSON with sorted keys, no spaces; the recovered address must equal the registered address of `tester` and
    `reviewer`, and the two people must be different;
  * for a test that signs typed data (WL-16, WL-17, WL-19, WL-27) the record lists `typedDataSignatures`: payload file (one of
    eip712/typed-data), the account that signed and the signature; the digest is recomputed from the payload alone and the recovered
    address must equal the account. A smart-contract account answers ERC-1271 on chain instead: that signature cannot be verified here
    and must be recorded with the on-chain call result (`scheme: erc1271`), which this tool reports as NOT VERIFIED OFFLINE.

Usage:
    python -I spec/tools/wallet_lab_verify.py RECORD.json          verify one record
    python -I spec/tools/wallet_lab_verify.py --all                verify every record under evidence/wallet-lab
    python -I spec/tools/wallet_lab_verify.py --message RECORD.json   print the exact message the tester and the reviewer sign
    python -I spec/tools/wallet_lab_verify.py --selftest           the tool against synthetic records signed with throw-away TEST keys

This tool never signs anything for a person and never writes a record under evidence/wallet-lab.
"""
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_types as E  # noqa: E402
import eip712_vectors as V  # noqa: E402
import secp256k1_min as K  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAB = ROOT / "evidence" / "wallet-lab"
PEOPLE = ROOT / "evidence" / "wallet-lab-kit" / "people.json"
PREFIX = "fastpay-wallet-lab-run-record:v1:"


def canonical(record):
    body = {k: v for k, v in record.items() if k != "signatures"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def record_message(record):
    return (PREFIX + hashlib.sha256(canonical(record)).hexdigest()).encode()


def load_people(path=PEOPLE):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("people", {})


def verify_record(record, people, typed_dir=ROOT / "eip712" / "typed-data"):
    """Returns (problems, notes). No problem means every signature that can be checked offline is valid."""
    problems, notes = [], []
    sigs = record.get("signatures") or {}
    addrs = {}
    for role in ("tester", "reviewer"):
        name = record.get(role)
        s = sigs.get(role)
        if not name:
            problems.append(f"no {role} named")
            continue
        if not s or not s.get("sig"):
            problems.append(f"no signature by the {role} ({name})")
            continue
        person = people.get(name)
        if not person or not person.get("address"):
            problems.append(f"{role} '{name}' is not registered in evidence/wallet-lab-kit/people.json")
            continue
        got = K.recover_signature(K.personal_hash(record_message(record)), s["sig"])
        if got is None or got.lower() != person["address"].lower():
            problems.append(f"the {role}'s signature does not recover to the registered address of '{name}' (recovered {got})")
        addrs[role] = person["address"].lower()
        if s.get("signer") and s["signer"].lower() != person["address"].lower():
            problems.append(f"{role}: the recorded signer differs from the registered address")
    if len(addrs) == 2 and addrs["tester"] == addrs["reviewer"]:
        problems.append("tester and reviewer sign with the same address")
    for ts in record.get("typedDataSignatures", []):
        payload_path = typed_dir / pathlib.Path(ts.get("payload", "")).name
        if not payload_path.exists():
            problems.append(f"typed data payload not found: {ts.get('payload')}")
            continue
        if ts.get("scheme") == "erc1271":
            notes.append(f"{payload_path.name}: ERC-1271 signature of {ts.get('account')}: NOT VERIFIED OFFLINE; needs the recorded on-chain isValidSignature result")
            if not ts.get("onChainCheck"):
                problems.append(f"{payload_path.name}: an ERC-1271 signature without the recorded on-chain check")
            continue
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        digest = E.payload_digest(payload)
        got = K.recover_signature(digest, ts.get("signature", ""))
        if got is None or got.lower() != (ts.get("account") or "").lower():
            problems.append(f"{payload_path.name}: the wallet's signature does not recover to {ts.get('account')} (recovered {got})")
        else:
            notes.append(f"{payload_path.name}: signed by {got}, digest {V.hx(digest)}")
    return problems, notes


def verify_file(path, people=None):
    record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return verify_record(record, people if people is not None else load_people())


def selftest():
    """Synthetic records with throw-away TEST keys: a correct one verifies; every kind of tampering is caught."""
    keys = {n: int.from_bytes(V.keccak256(f"fastpay-wallet-lab-selftest-{n}".encode()), "big") % K.N for n in ("Alice Tester", "Bob Reviewer")}
    people = {n: {"address": K.address_of(K.public_key(k))} for n, k in keys.items()}
    payload_file = ROOT / "eip712" / "typed-data" / "SuccessorAuthorization.json"
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    v, r, s = K.sign(E.payload_digest(payload), keys["Alice Tester"])
    wallet_sig = "0x" + f"{r:064x}{s:064x}{v:02x}"
    rec = {"runId": "SELFTEST", "testId": "WL-17", "tester": "Alice Tester", "reviewer": "Bob Reviewer", "result": "PASS",
           "typedDataSignatures": [{"payload": "SuccessorAuthorization.json", "account": people["Alice Tester"]["address"], "signature": wallet_sig}]}
    msg = K.personal_hash(record_message(rec))
    rec["signatures"] = {}
    for role, name in (("tester", "Alice Tester"), ("reviewer", "Bob Reviewer")):
        v, r, s = K.sign(msg, keys[name])
        rec["signatures"][role] = {"signer": people[name]["address"], "sig": "0x" + f"{r:064x}{s:064x}{v:02x}"}
    problems, _ = verify_record(rec, people)
    assert not problems, problems
    import copy
    for label, mutate in (
        ("a changed result", lambda x: x.__setitem__("result", "FAIL")),
        ("a changed test", lambda x: x.__setitem__("testId", "WL-18")),
        ("an unregistered reviewer", lambda x: x.__setitem__("reviewer", "Mallory")),
        ("tester signs both", lambda x: x["signatures"].__setitem__("reviewer", x["signatures"]["tester"])),
        ("a missing reviewer signature", lambda x: x["signatures"].pop("reviewer")),
        ("a typed-data signature by another key", lambda x: x["typedDataSignatures"][0].__setitem__("account", people["Bob Reviewer"]["address"])),
        ("a typed-data payload other than the one signed", lambda x: x["typedDataSignatures"][0].__setitem__("payload", "RevokeMandate.json")),
    ):
        bad = copy.deepcopy(rec)
        mutate(bad)
        pr, _ = verify_record(bad, people)
        assert pr, f"tampering not detected: {label}"
    same = copy.deepcopy(rec)
    same["reviewer"] = "Alice Tester"
    pr, _ = verify_record(same, people)
    assert pr, "tester equal to reviewer must be refused"
    return True


def main(argv):
    if "--selftest" in argv:
        print("wallet-lab verifier self-test:", "ok" if selftest() else "FAILED")
        return 0
    if "--message" in argv:
        rec = json.loads(pathlib.Path([a for a in argv if not a.startswith("--")][0]).read_text(encoding="utf-8"))
        print(record_message(rec).decode())
        return 0
    people = load_people()
    paths = []
    if "--all" in argv:
        paths = sorted(LAB.rglob("*.json")) if LAB.exists() else []
    else:
        paths = [pathlib.Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        print("no run records to verify (evidence/wallet-lab is empty)" if "--all" in argv else __doc__)
        return 0 if "--all" in argv else 2
    bad = 0
    for p in paths:
        problems, notes = verify_file(p, people)
        status = "ok" if not problems else "FAILED"
        print(f"{p.name}: {status}")
        for n in notes:
            print("   note:", n)
        for pr in problems:
            print("   PROBLEM:", pr)
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
