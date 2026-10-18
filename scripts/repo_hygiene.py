#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Repository hygiene checks for the public PayTrue repository (standard library only).

    python -I scripts/repo_hygiene.py                  run every check on the tracked files
    python -I scripts/repo_hygiene.py --staged         check only the files staged for commit (used by the pre-commit hook)
    python -I scripts/repo_hygiene.py --history        also scan every commit for private keys and well-known token formats
    python -I scripts/repo_hygiene.py --only size,secrets,spdx
    python -I scripts/repo_hygiene.py --json           machine-readable result

Checks: size, forbidden, secrets, spdx, vendored, required, hosts, protected, packages (and history with --history).
The settings are in scripts/hygiene.config.json. A FAIL exits with code 1; a WARN does not.

What this does NOT do: it is not a substitute for GitHub secret scanning and push protection, for a dependency audit, or for a legal review.
"""
import argparse
import fnmatch
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "scripts" / "hygiene.config.json").read_text(encoding="utf-8"))

PRIVATE_KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TOKEN_FORMATS = {
    "github token": re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    "github fine-grained token": re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    "aws access key id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "stripe live key": re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    "slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "google api key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "npm token": re.compile(r"npm_[A-Za-z0-9]{36}"),
}
GENERIC_SECRET = re.compile(r"""(?i)(secret|api[_-]?key|password|passwd|token|private[_-]?key)["']?\s*[:=]\s*["']([A-Za-z0-9_/+=-]{16,})["']""")
HEX_PRIVATE_KEY = re.compile(r"""(?i)(private[_-]?key|priv[_-]?key)["' ]*[:=]\s*["']?(0x)?[0-9a-f]{64}\b""")
RPC_WITH_KEY = re.compile(r"https?://[A-Za-z0-9.-]*(infura\.io|alchemy\.com|quiknode\.pro|ankr\.com)/[A-Za-z0-9_/-]*[A-Za-z0-9]{24,}")
SPDX = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+\- ()]+?)\s*(?:\*/)?\s*$", re.M)
COPYLEFT = re.compile(r"\b(A?GPL|LGPL|SSPL|BUSL|UNLICENSED)\b")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def tracked_files(staged):
    if staged:
        names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split("\n")
    else:
        # tracked files AND files that are not tracked yet but would be added (not ignored): a new file is checked before it is committed
        names = git("ls-files", "--cached", "--others", "--exclude-standard").split("\n")
    return sorted(set(n for n in names if n and (ROOT / n).is_file()))


def read_text(rel):
    try:
        return (ROOT / rel).read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def under(rel, prefixes):
    return any(rel.startswith(p) for p in prefixes)


class Result:
    def __init__(self):
        self.rows = []

    def add(self, name, level, detail):
        self.rows.append({"check": name, "level": level, "detail": detail})


# ---------------------------------------------------------------------------------------------------------------- checks
def check_size(files, res):
    fail, warn = CONFIG["maxFileMiB"] * 1024 * 1024, CONFIG["warnFileMiB"] * 1024 * 1024
    bad = [(f, (ROOT / f).stat().st_size) for f in files if (ROOT / f).stat().st_size >= fail]
    big = [(f, (ROOT / f).stat().st_size) for f in files if warn <= (ROOT / f).stat().st_size < fail]
    for f, s in bad:
        res.add("size", "FAIL", f"{f} is {s / 1048576:.1f} MiB (limit {CONFIG['maxFileMiB']} MiB; GitHub rejects 100 MiB and warns at 50 MiB)")
    for f, s in big:
        res.add("size", "WARN", f"{f} is {s / 1048576:.1f} MiB (warning from {CONFIG['warnFileMiB']} MiB): compress or move it to release assets")
    if not bad and not big:
        res.add("size", "PASS", f"no tracked file reaches {CONFIG['warnFileMiB']} MiB")
    elif not bad:
        res.add("size", "PASS", f"no tracked file reaches {CONFIG['maxFileMiB']} MiB")


def check_forbidden(files, res):
    problems = []
    for f in files:
        base = f.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(base, p) for p in CONFIG["allowTrackedPatterns"]):
            continue
        if any(fnmatch.fnmatch(base, p) or fnmatch.fnmatch(f, p) for p in CONFIG["forbiddenTrackedPatterns"]):
            problems.append(f"{f}: a file of a type that must not be tracked (keys, environment files, binaries, archives, media)")
        if any(fnmatch.fnmatch(f, p) for p in CONFIG["privateEvidencePatterns"]):
            problems.append(f"{f}: wallet-lab raw artifacts are private by default (README, section Contributing); publish a redacted one only by a reviewed `git add -f`")
    for p in problems:
        res.add("forbidden", "FAIL", p)
    if not problems:
        res.add("forbidden", "PASS", "no key, environment file, binary, archive or private-evidence artifact is tracked")


def check_encoding(files, res):
    """Text is UTF-8 without a byte-order mark. GitHub shows UTF-16 (what `echo x > file` writes in Windows PowerShell 5) as garbage, and the other checks read files leniently."""
    skip = tuple(CONFIG["encodingSkipSuffixes"])
    problems = []
    for f in files:
        if f.lower().endswith(skip):
            continue
        try:
            b = (ROOT / f).read_bytes()
        except OSError:
            continue
        if b[:3] == b"\xef\xbb\xbf":
            kind = "a UTF-8 byte-order mark"
        elif b[:2] in (b"\xff\xfe", b"\xfe\xff"):
            kind = "UTF-16 (GitHub renders it as garbage)"
        elif b"\x00" in b:
            kind = "NUL bytes"
        else:
            try:
                b.decode("utf-8")
                continue
            except UnicodeDecodeError as e:
                kind = f"invalid UTF-8 at byte {e.start}"
        problems.append(f"{f}: {kind}; store text as UTF-8 without a byte-order mark")
    for p in problems:
        res.add("encoding", "FAIL", p)
    if not problems:
        res.add("encoding", "PASS", f"{len(files)} tracked files are UTF-8 without a byte-order mark (or a listed binary type)")


def check_secrets(files, res):
    hits = []
    for f in files:
        if under(f, CONFIG["secretAllowPaths"]):
            continue
        text = read_text(f)
        if not text:
            continue
        if PRIVATE_KEY_BLOCK.search(text):
            hits.append(f"{f}: a private key block")
        for name, rx in TOKEN_FORMATS.items():
            if rx.search(text):
                hits.append(f"{f}: a {name}")
        if f.endswith((".md", ".json", ".py", ".ts", ".js", ".mjs", ".sol", ".sh", ".yml", ".yaml", ".toml", ".env", ".txt")):
            for m in GENERIC_SECRET.finditer(text):
                literal = m.group(2)
                if re.fullmatch(r"0x[0-9a-fA-F]+", literal):
                    continue  # an address or a hash, not a credential (typed-data payloads are full of them)
                start = text.rfind("\n", 0, m.start()) + 1
                end = text.find("\n", m.end())
                line = text[start:end if end >= 0 else len(text)]
                if "hygiene: allow-secret" in line:
                    continue  # an explicit, reviewable marker on a dummy value in a test or an example
                hits.append(f"{f}:{text.count(chr(10), 0, m.start()) + 1}: a long literal assigned to a secret-like name: {m.group(0)[:60]} (a dummy value needs `hygiene: allow-secret` on its line)")
            for rx, label in ((HEX_PRIVATE_KEY, "a 32-byte hex literal assigned to a private-key name"), (RPC_WITH_KEY, "an RPC URL that carries a provider key")):
                m = rx.search(text)
                if m:
                    hits.append(f"{f}: {label}: {m.group(0)[:60]}")
    for h in hits:
        res.add("secrets", "FAIL", h)
    if not hits:
        res.add("secrets", "PASS", f"no private key block, well-known token format or secret-like literal in {len(files)} files "
                                   f"(allow-listed upstream paths: {', '.join(CONFIG['secretAllowPaths'])})")


def check_spdx(files, res):
    problems = []
    own = CONFIG["ownSpdx"]
    for f in files:
        if not f.endswith(".sol"):
            continue
        head = "\n".join(read_text(f).split("\n")[:4])
        m = SPDX.search(head.replace("\r", ""))
        ident = m.group(1).strip() if m else None
        if under(f, CONFIG["thirdPartySourcePrefixes"]):
            if ident not in CONFIG["allowedThirdPartySpdx"]:
                problems.append(f"{f}: third-party file with SPDX {ident!r}; allowed: {CONFIG['allowedThirdPartySpdx']}")
        elif ident != own:
            problems.append(f"{f}: SPDX is {ident!r}, expected {own}")
    for f in files:
        if f.endswith((".sol", ".py", ".ts", ".js", ".mjs")) and not under(f, CONFIG["thirdPartySourcePrefixes"]):
            m = SPDX.search(read_text(f)[:400].replace("\r", ""))
            if m and COPYLEFT.search(m.group(1)):
                problems.append(f"{f}: copyleft or unlicensed SPDX identifier {m.group(1)!r}")
    for p in sorted(set(problems)):
        res.add("spdx", "FAIL", p)
    if not problems:
        n = sum(1 for f in files if f.endswith(".sol") and not under(f, CONFIG["thirdPartySourcePrefixes"]))
        res.add("spdx", "PASS", f"{n} own Solidity files carry SPDX {own}; third-party files carry only {CONFIG['allowedThirdPartySpdx']}")


def check_vendored(files, res):
    bad = [f for f in files if under(f, CONFIG["forbiddenTrackedPrefixes"])]
    for f in bad[:20]:
        res.add("vendored", "FAIL", f"{f}: build output, toolchain binary or vendored third-party tree must not be tracked (fetch it with spec/toolchain/fetch_toolchain.py)")
    if len(bad) > 20:
        res.add("vendored", "FAIL", f"... and {len(bad) - 20} more files under forbidden prefixes")
    if not bad:
        res.add("vendored", "PASS", "no toolchain binary, generated build run, build output or vendored dependency tree is tracked")


def check_required(res):
    missing = [f for f in CONFIG["requiredFiles"] if not (ROOT / f).exists()]
    for f in missing:
        res.add("required", "FAIL", f"{f} is missing")
    if not missing:
        res.add("required", "PASS", f"all {len(CONFIG['requiredFiles'])} required public files exist")


def check_hosts(files, res):
    rx = re.compile(CONFIG["deniedHostPattern"], re.I)
    bad = []
    for f in files:
        if f.split("/")[0] in CONFIG["hostCheckDirs"] or f.startswith(".github/"):
            m = rx.search(read_text(f))
            if m:
                bad.append(f"{f}: mentions {m.group(0)}")
    for b in bad:
        res.add("hosts", "FAIL", b + " (code, deployment files and examples must not depend on a PayTrue-hosted service)")
    if not bad:
        res.add("hosts", "PASS", f"no PayTrue-hosted domain in {', '.join(CONFIG['hostCheckDirs'])}")


def keccak256(data):
    spec = importlib.util.spec_from_file_location("eip712_vectors", ROOT / "spec" / "tools" / "eip712_vectors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.keccak256(data).hex()


def check_protected(res):
    """The cryptographic identifiers that a blind find-and-replace of the product name would change (README, section Contributing)."""
    problems = []
    for item in CONFIG["protectedIdentifiers"]:
        s = item["string"]
        if keccak256(s.encode("utf-8")) != item["keccak256"]:
            problems.append(f"{item['id']}: the recorded keccak256 does not match the recorded string {s!r}: the configuration itself was edited")
            continue
        for rel in item["mustAppearIn"]:
            if s not in read_text(rel):
                problems.append(f"{item['id']}: {s!r} no longer appears in {rel}. A protected identifier was renamed or removed; "
                                f"changing it is a new domain or a new tag and needs an impact analysis and the regeneration of every dependent artifact")
    for p in problems:
        res.add("protected", "FAIL", p)
    if not problems:
        res.add("protected", "PASS", f"{len(CONFIG['protectedIdentifiers'])} protected cryptographic identifiers are unchanged and present where they are used")


def check_packages(res):
    problems = []
    pkgs = sorted((ROOT / "packages").glob("*/package.json")) if (ROOT / "packages").exists() else []
    for p in pkgs:
        d = json.loads(p.read_text(encoding="utf-8"))
        rel = p.relative_to(ROOT).as_posix()
        if d.get("license") != CONFIG["ownSpdx"]:
            problems.append(f"{rel}: license is {d.get('license')!r}")
        for key in ("repository", "files", "exports", "engines", "description"):
            if key not in d:
                problems.append(f"{rel}: missing {key!r}")
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            if d.get(key):
                problems.append(f"{rel}: has {key}; the packages are dependency-free by policy (add it to the third-party table of the README and to the policy first)")
        if CONFIG.get("packagesMustBePrivateUntilRelease") and d.get("private") is not True:
            problems.append(f"{rel}: must stay \"private\": true until a release is approved by the maintainers")
    for p in problems:
        res.add("packages", "FAIL", p)
    if not problems:
        res.add("packages", "PASS", f"{len(pkgs)} packages: Apache-2.0, dependency-free, publish-gated")


def check_history(res):
    revs = git("rev-list", "--all").split()
    if not revs:
        res.add("history", "PASS", "no commits")
        return
    pats = [PRIVATE_KEY_BLOCK.pattern] + [rx.pattern for rx in TOKEN_FORMATS.values()]
    pattern = "|".join(f"({p})" for p in pats)
    out = subprocess.run(["git", "grep", "-I", "-l", "-E", pattern, *revs, "--", ".", ":!spec/foundry/lib/forge-std"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if out:
        for line in out.split("\n")[:20]:
            res.add("history", "FAIL", f"{line}: private key block or token format in history (rotate the secret; do not rewrite history without the owner's decision)")
    else:
        res.add("history", "PASS", f"no private key block or well-known token format in any of {len(revs)} commits")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    files = tracked_files(args.staged)
    res = Result()
    wanted = {x.strip() for x in args.only.split(",") if x.strip()}

    def on(name):
        return not wanted or name in wanted
    if on("size"):
        check_size(files, res)
    if on("forbidden"):
        check_forbidden(files, res)
    if on("encoding"):
        check_encoding(files, res)
    if on("secrets"):
        check_secrets(files, res)
    if on("spdx"):
        check_spdx(files, res)
    if on("vendored"):
        check_vendored(files, res)
    if on("required") and not args.staged:
        check_required(res)
    if on("hosts"):
        check_hosts(files, res)
    if on("protected") and not args.staged:
        check_protected(res)
    if on("packages") and not args.staged:
        check_packages(res)
    if args.history and on("history"):
        check_history(res)
    fails = [r for r in res.rows if r["level"] == "FAIL"]
    if args.json:
        print(json.dumps({"files": len(files), "failures": len(fails), "rows": res.rows}, indent=1))
    else:
        for r in res.rows:
            print(f"{r['level']:<4} {r['check']:<10} {r['detail']}")
        print(f"hygiene: {'FAILED' if fails else 'ok'} ({len(files)} files checked, {len(fails)} failures)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
