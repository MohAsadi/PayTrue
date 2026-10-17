#!/usr/bin/env python3
"""Synchronise computed protocol vectors into the documents (revision 0.4).

Run:   python -I spec/tools/sync_vectors.py --write     patch the generated blocks
       python -I spec/tools/sync_vectors.py --verify    exit 1 if a block, or a hex constant quoted elsewhere, differs from the computed value

Generated blocks (between <!-- BEGIN:NAME --> and <!-- END:NAME -->):
  VEC_QUOTE      document 11 section 4.6   PriceQuote v1 inputs, identifiers, hashes
  VEC_SNAPSHOT   document 12 section 5.3.4 migration snapshot hash and containment results
  VEC_PIN        document 17 section 9      account-pin constants, ACCOUNT_PIN_TYPEHASH, the three example pins and their hashStruct (0.5)

`--verify` also checks that selected hash constants written by hand in prose (document 17) equal the computed ones.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC = pathlib.Path(__file__).resolve().parent.parent


def quote_block():
    v = V.VECTOR
    q = v["quote"]
    r = V.quote_vector()
    rows = [
        ("`chainId`", v["chainId"]),
        ("`verifyingContract` (router A) / router B", f"`{v['router']}` / `{v['routerB']}`"),
        ("`mandateManager`", f"`{v['mandateManager']}`"),
        ("`customer` = `payer`", f"`{v['customer']}`"),
        ("`merchantId` / `subscriptionRef`", f"`0x{'aa' * 32}` / `0x{'bb' * 32}`"),
        ("`creationNonce` / `cycleIndex`", f"{v['creationNonce']} / {v['cycleIndex']}"),
        ("`token` / decimals", f"`{q['token']}` / {v['tokenDecimals']}"),
        ("`amountIn` / `currency` / `priceE18`", f"{q['amountIn']:,} / {q['currency']} / `100e18`"),
        ("`issuedAt` / `validAfter` / `validUntil`", f"{q['issuedAt']:,} / {q['validAfter']:,} / {q['validUntil']:,}"),
        ("`nonce` / `signerSetVersion` / `registryVersion` / `boundsVersion`", f"{q['nonce']} / {q['signerSetVersion']} / {q['registryVersion']} / {q['boundsVersion']}"),
        ("`priceSourceSetHash` = `keccak256(\"fastpay-test-source-set-v1\")`", f"`{r['priceSourceSetHash']}`"),
        ("`routeHash` = `keccak256(abi.encode(tag(\"fastpay.route.direct.v1\"), chainId, token))`", f"`{r['routeHash']}`"),
        ("`lineageId`", f"`{r['lineageId']}`"),
        ("`mandateId` (generation 0)", f"`{r['mandateId0']}`"),
        ("`cycleId`", f"`{r['cycleId']}`"),
        ("`paymentId` (recurring)", f"`{r['paymentId']}`"),
        ("**EIP712Domain type hash**", f"`{r['domainTypeHash']}`"),
        ("**`PriceQuote` type hash**", f"`{r['priceQuoteTypeHash']}`"),
        ("**Domain separator** (router A)", f"`{r['domainSeparator']}`"),
        ("**Struct hash**", f"`{r['structHash']}`"),
        ("**Digest** (router A)", f"`{r['digest']}`"),
        ("Digest for the same message on router B (must differ)", f"`{r['digestOnRouterB']}`"),
        ("`fiatValueMinor`", f"{r['fiatValueMinor']:,} (cents)"),
    ]
    lines = ["| Item | Value |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]
    lines.append("")
    lines.append("`TAG(s)` is `keccak256(s)` as ASCII; the type string of `PriceQuote` is the one in §4.1 with no spaces after commas.")
    return "\n".join(lines)


def snapshot_block():
    out = V.snapshot_vector()
    pred, _ok = V.snapshot_reference()
    lines = ["| Case | Result |", "|---|---|",
             f"| `snapshotHash` of the predecessor snapshot below (26 words, `eip712/types.json` `snapshotEncoding`; `lineageId` `0x77…77`, `predecessorId` `0x78…78`, generation {pred['generation']}, customer `{pred['customer']}`) | `{out['snapshotHash']}` |",
             f"| `hashStruct(MandateTerms)` of the same terms (the `newTermsHash` of a successor with these terms) | `{out['termsHash']}` |"]
    for k, val in out.items():
        if k in ("snapshotHash", "termsHash"):
            continue
        ok, why = val
        lines.append(f"| {k} | {'contained' if ok else 'rejected (' + ', '.join(why) + ')'} |")
    lines.append("")
    lines.append("Predecessor: two tokens (`0x5555…55`, `0x6666…66`), per-payment cap 51,020,409 and 30-day cap 51,020,409 each, total cap 612,244,908 each; fiat 5,000 per payment, 5,000 per 30 days, 60,000 total (USD); "
                 "expiry 1,900,000,000; anchor 1,800,000,000; quote age 120 s; `boundsVersion` 1 (the band of a version is read from the registry and never changes, so a migration keeps the version: "
                 "version +1 and version -1 are both rejected); one charge per period, minimum interval 86,400 s; fee cap 100 bps; `extensionsHash` 0. "
                 "The narrower successor has one token, lower caps, an earlier expiry and a lower fee cap, and the same bounds version.")
    return "\n".join(lines)


def pin_block():
    p = V.pin_vectors()
    lines = ["| Constant | Value |", "|---|---|",
             f"| `KECCAK_EMPTY` | `{p['keccakEmpty']}` |", f"| `PIN_EOA = keccak256(\"fastpay.pin.eoa.v1\")` | `{p['pinEOA']}` |",
             f"| Designator code for `D1 = 0xabab…ab` | `{p['designatorCodeD1']}` |", f"| `H1 = keccak256(0xef0100 ‖ D1)` | `{p['designatorHashD1']}` |",
             f"| `H2 = keccak256(0xef0100 ‖ D2)`, `D2 = 0xcdcd…cd` | `{p['designatorHashD2']}` |",
             f"| **`ACCOUNT_PIN_TYPEHASH`** = `keccak256` of the type string of §5.1 (no spaces after commas) | `{p['accountPinTypeHash']}` |",
             f"| `keccak256(\"fastpay-test-delegate-code-v1\")` (delegate code hash of the example 7702 pin) | `{p['testDelegateCodeHash']}` |",
             f"| `keccak256(\"fastpay-test-account-code-v1\")` (account code hash of the example 4337 pin) | `{p['testAccountCodeHash']}` |",
             f"| `keccak256(\"test-wallet/delegator/1\")` (family of the example 7702 pin) | `{p['familyDelegator']}` |",
             f"| `keccak256(\"test-wallet/account/1\")` (family of the example 4337 pin) | `{p['familyAccount']}` |",
             f"| **Example pin 1** `pinEoa`: mode 1, `PIN_EOA`, delegate 0, delegate code hash 0, family 0, `pinVersion` 1, `signatureMode` 1: `hashStruct` | `{p['pinHashEoa']}` |",
             f"| **Example pin 2** `pin7702`: mode 2, `H1`, `D1`, the delegate code hash and family above, `pinVersion` 1, `signatureMode` 2: `hashStruct` | `{p['pinHash7702']}` |",
             f"| **Example pin 3** `pin4337`: mode 3, the account code hash and family above, delegate 0, delegate code hash 0, `pinVersion` 1, `signatureMode` 2: `hashStruct` | `{p['pinHash4337']}` |"]
    return "\n".join(lines)


BLOCKS = {"VEC_QUOTE": ("11-dual-cap-model.md", quote_block), "VEC_SNAPSHOT": ("12-router-lifecycle-and-migration.md", snapshot_block),
          "VEC_PIN": ("17-account-compatibility-policy.md", pin_block)}


def patch(text, name, content):
    pat = re.compile(rf"(<!-- BEGIN:{name} -->)(.*?)(<!-- END:{name} -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"marker {name} not found")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def current(text, name):
    m = re.search(rf"<!-- BEGIN:{name} -->\n?(.*?)\n?<!-- END:{name} -->", text, re.S)
    return m.group(1) if m else None


def prose_checks():
    """Hash constants quoted by hand in document 17 prose must equal the computed ones."""
    p = V.pin_vectors()
    t = (SPEC / "17-account-compatibility-policy.md").read_text(encoding="utf-8")
    bad = []
    for label, val in (("PIN_EOA", p["pinEOA"]), ("H1", p["designatorHashD1"]), ("H2", p["designatorHashD2"]), ("KECCAK_EMPTY", p["keccakEmpty"])):
        if val not in t:
            bad.append(label)
    return bad


def main():
    verify = "--verify" in sys.argv
    write = "--write" in sys.argv
    if not (verify or write):
        print("use --write or --verify")
        return 2
    bad = []
    changed = []
    for name, (doc, fn) in BLOCKS.items():
        path = SPEC / doc
        raw = path.read_bytes().decode("utf-8")
        crlf = "\r\n" in raw                    # the documents use CRLF: read as LF, write back with the line ending the file had
        text = raw.replace("\r\n", "\n")
        want = fn()
        if write:
            new = patch(text, name, want)
            if new != text:                      # do not touch a document whose block is already current
                path.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
                changed.append(name)
        else:
            have = current(text, name)
            if have is None or have.strip() != want.strip():
                bad.append(name)
    if verify:
        bad += ["prose:" + b for b in prose_checks()]
        if bad:
            print("out of sync:", ", ".join(bad))
            return 1
        print("all vector blocks and quoted constants match")
    else:
        print("wrote", ", ".join(changed) if changed else "nothing (every block is already current)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
