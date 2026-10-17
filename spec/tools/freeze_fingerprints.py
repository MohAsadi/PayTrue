#!/usr/bin/env python3
"""Content fingerprints of the normative sections that the protocol freeze covers (revision 0.3).

Run:   python -I spec/tools/freeze_fingerprints.py            print the table
       python -I spec/tools/freeze_fingerprints.py --write    patch the FINGERPRINTS block of spec/14-protocol-freeze-pack.md
       python -I spec/tools/freeze_fingerprints.py --verify   exit 1 if any section differs from the fingerprints recorded in document 14

A fingerprint is the SHA-256 of a section's text with line endings normalized to LF and trailing spaces removed. Before the freeze the
fingerprints are candidates and change with every edit. At freeze, document 14 records the approved values; from then on a change to any
listed section is a Freeze Change Request (document 14, section 7), and `--verify` is part of the release pipeline.
"""
import hashlib
import pathlib
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SPEC = pathlib.Path(__file__).resolve().parent.parent
DOC14 = SPEC / "14-protocol-freeze-pack.md"

# (id, file prefix, heading prefix that starts the section, what it fixes)
SECTIONS = [
    ("FG-01", "05-", "## 2. Protocol B", "Three authorization layers; separation rules; revocation flows (§2.1)"),
    ("FG-02", "05-", "## 5. Canonical input", "Planner input and normalization (JCS canonical form)"),
    ("FG-03", "05-", "## 7. Decision tree", "Decision tree and normative pseudocode"),
    ("FG-04", "05-", "## 9. Golden test vectors", "Planner vectors TV-01…TV-36"),
    ("FG-05", "06-", "## 4. Contract architecture", "Contracts, entry points and system invariants"),
    ("FG-06", "09-", "## 7. Mechanical absence", "Absence and presence checks for conversion code"),
    ("FG-07", "10-", "## 2. On-chain design", "Pay Once: spender binding, witness, entrypoints, nonces"),
    ("FG-08", "10-", "## 7. Golden vectors", "Pay Once planner vectors TV-PO-1…12"),
    ("FG-09", "11-", "## 2. The three cap classes", "Classification of every cap and limit"),
    ("FG-10", "11-", "## 3. Mandate fields", "Mandate fields, counters, extensionsHash"),
    ("FG-11", "11-", "## 4. The signed quote schema", "PriceQuote v1: fifteen fields, domain, signer sets and rotation, validity predicate Q1–Q20, non-override proof, canonical JSON, versioning, test vector"),
    ("FG-12", "11-", "## 5. Charge-time algorithm", "On-chain charge algorithm"),
    ("FG-13", "12-", "## 4. The lineage model", "Mandate lineage"),
    ("FG-14", "12-", "## 5. Migration state machine", "States, transitions, activateSuccessor predicates, router modes and the shared-allowance rules, exposure index, plan kinds, partial states, revision vs migration"),
    ("FG-15", "12-", "## 12. Invariants and tests", "I-MIG-1…11 and MIG-TV-01…45"),
    ("FG-16", "13-", "## 3. What is inspected", "DelegationRecord, DelegationEvidence, probes, observation procedure"),
    ("FG-17", "13-", "## 7. Revalidation before every unattended charge", "Revalidation rule, results, pseudocode, pause state and clearing"),
    ("FG-18", "13-", "## 11. Golden vectors", "DRV-01…DRV-25"),
    ("FG-19", "17-", "## 2. Account modes", "Observation, allowlist row, mode predicates"),
    ("FG-20", "17-", "## 3. Permission matrix", "Permission of each mode; UNATTENDED_OK predicate"),
    ("FG-21", "17-", "## 5. The on-chain account pin", "AccountPin struct, PIN_WELLFORMED, PIN_OK, AUTH, what the contract verifies versus off chain, signature capability and its invalidation"),
    ("FG-22", "17-", "## 9. Test vectors ACP-TV", "ACP-TV-01…44 and pin constants"),
    ("FG-23", "11-", "### 4.7 Signer sets", "Signer-set planned rotation and emergency removal; SR-1…SR-7"),
    ("FG-24", "12-", "#### 5.3.1 The shared allowance", "Permit2 facts F1…F6, router mode, exposure index, normal and emergency migration, sibling rules"),
]

TABLE_HEAD = ["| FG | Document and section | Fixes | SHA-256 (first 16 hex) | Full SHA-256 |", "|---|---|---|---|---|"]


def normalize(text):
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip("\n") + "\n"


def section_text(path, start_prefix):
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    in_code = False
    start = None
    level = None
    for i, ln in enumerate(lines):
        if ln.startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        if start is None:
            if ln.startswith(start_prefix):
                start = i
                level = len(ln) - len(ln.lstrip("#"))
        else:
            m = re.match(r"^(#+) ", ln)
            if m and len(m.group(1)) <= level:
                return normalize("\n".join(lines[start:i]))
    if start is None:
        raise SystemExit(f"section not found: {path.name}: {start_prefix}")
    return normalize("\n".join(lines[start:]))


def compute():
    rows = []
    for fid, prefix, heading, fixes in SECTIONS:
        matches = sorted(SPEC.glob(prefix + "*.md"))
        if not matches:
            raise SystemExit(f"no document with prefix {prefix}")
        path = matches[0]
        h = hashlib.sha256(section_text(path, heading).encode("utf-8")).hexdigest()
        rows.append((fid, path.name, heading.lstrip("# ").strip(), fixes, h))
    return rows


def table(rows):
    out = list(TABLE_HEAD)
    for fid, doc, heading, fixes, h in rows:
        out.append(f"| {fid} | {doc} — {heading} | {fixes} | `{h[:16]}` | `{h}` |")
    return "\n".join(out)


def recorded():
    text = DOC14.read_text(encoding="utf-8")
    m = re.search(r"<!-- BEGIN:FINGERPRINTS -->(.*?)<!-- END:FINGERPRINTS -->", text, re.S)
    if not m:
        raise SystemExit("FINGERPRINTS block not found in document 14")
    return dict(re.findall(r"\| (FG-\d+) \|.*?`([0-9a-f]{64})` \|", m.group(1)))


if __name__ == "__main__":
    rows = compute()
    if "--write" in sys.argv:
        text = DOC14.read_text(encoding="utf-8")
        pat = re.compile(r"(<!-- BEGIN:FINGERPRINTS -->)(.*?)(<!-- END:FINGERPRINTS -->)", re.S)
        if not pat.search(text):
            sys.exit("FINGERPRINTS block not found in document 14")
        DOC14.write_text(pat.sub(lambda m: f"{m.group(1)}\n{table(rows)}\n{m.group(3)}", text), encoding="utf-8")
        print(f"wrote {len(rows)} fingerprints")
    elif "--verify" in sys.argv:
        rec = recorded()
        bad = [fid for fid, _, _, _, h in rows if rec.get(fid) != h]
        if bad:
            print("sections changed since the recorded fingerprints:", ", ".join(bad))
            sys.exit(1)
        print("all fingerprints match")
    else:
        print(table(rows))
