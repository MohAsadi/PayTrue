#!/usr/bin/env python3
"""Fetch and verify the pinned toolchain of toolchain.lock.json (revision 0.5 implementation).

Run:   python -I spec/toolchain/fetch_toolchain.py                 download what is missing, verify every SHA-256, extract
       python -I spec/toolchain/fetch_toolchain.py --verify        verify what is on disk only (no network); exit 1 on any mismatch
       python -I spec/toolchain/fetch_toolchain.py --record        as the first form, and write the SHA-256 of archives addressed by commit
                                                                   (forge-std, solmate, permit2 and its submodules) into the lock when it is still null
       python -I spec/toolchain/fetch_toolchain.py --verify-trees  compare every extracted source archive with the git tree of its commit
                                                                   (GitHub API, read-only): every blob of the commit must be present with the same blob SHA-1
       python -I spec/toolchain/fetch_toolchain.py --refetch NAME  delete NAME's archive and extracted tree and fetch it again under the policy below

Policy (enforced in `fetch`, not by convention)
  * https only. Every redirect target is checked against the allow-list of the artifact's kind before it is followed; a redirect to any other host
    aborts the download and nothing is written:
      source archives (github.com/<owner>/<repo>/archive/<commit>.zip)  github.com, codeload.github.com
      Foundry release assets                                               github.com, objects.githubusercontent.com, release-assets.githubusercontent.com
      solc                                                                 binaries.soliditylang.org
  * the SHA-256 is computed on the downloaded file BEFORE anything is extracted; a mismatch deletes the file and fails the run.
  * nothing downloaded is executed, except that the pinned `forge` and `solc` binaries are what the toolchain is for (their SHA-256 is verified
    first). No script from any archive is run; archives are only unpacked, with a path-traversal check.
  * every fetch is recorded (URL, redirect chain, final host, SHA-256, size, commit, time) in toolchain/fetch-record.json.

Layout under spec/toolchain/ (created here): _download/ (archives exactly as downloaded), bin/ (Foundry), solc/, permit2-build/permit2/ (the pinned
Permit2 tree and its four submodules under lib/), fetch-record.json, tree-verification.json; and spec/foundry/lib/forge-std.
Foundry's published sigstore attestations are NOT verified here (that needs a Sigstore client).
"""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import shutil
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
LOCK = HERE / "toolchain.lock.json"
RECORD = HERE / "fetch-record.json"
TREES = HERE / "tree-verification.json"
DL = HERE / "_download"
UA = {"User-Agent": "fastpay-spec-toolchain"}

ALLOWED = {
    "archive": {"github.com", "codeload.github.com"},
    "foundry": {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"},
    "solc": {"binaries.soliditylang.org"},
}


def kind_of(url):
    u = urllib.parse.urlparse(url)
    if u.netloc == "binaries.soliditylang.org":
        return "solc"
    if "/archive/" in u.path and u.netloc == "github.com":
        return "archive"
    return "foundry"


class Policed(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed):
        self.allowed = allowed
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlparse(newurl)
        if u.scheme != "https" or u.netloc not in self.allowed:
            raise SystemExit(f"REDIRECT REJECTED: {req.full_url} -> {newurl} (host {u.netloc!r} is not in {sorted(self.allowed)})")
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def plat():
    return "windows-amd64" if platform.system().lower() == "windows" else "linux-amd64"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log_record(entry):
    recs = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else []
    recs = [r for r in recs if r.get("name") != entry["name"]] + [entry]
    RECORD.write_text(json.dumps(recs, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def fetch(name, url, dest, commit=None):
    u = urllib.parse.urlparse(url)
    kind = kind_of(url)
    if u.scheme != "https" or u.netloc not in ALLOWED[kind]:
        raise SystemExit("URL scheme or host not allowed: " + url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    handler = Policed(ALLOWED[kind])
    opener = urllib.request.build_opener(handler)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with opener.open(urllib.request.Request(url, headers=UA), timeout=300) as r, open(tmp, "wb") as f:
        final = r.geturl()
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.replace(dest)
    log_record({"name": name, "url": url, "archiveFilename": dest.name, "kind": kind, "redirectChain": handler.chain, "finalUrl": final,
                "finalHost": urllib.parse.urlparse(final).netloc, "allowedHosts": sorted(ALLOWED[kind]), "commit": commit,
                "bytes": dest.stat().st_size, "sha256": sha256(dest),
                "retrievedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})


def ensure(name, url, dest, want, offline, commit=None):
    if dest.exists() and (want is None or sha256(dest) == want):
        return sha256(dest), "present"
    if offline:
        return (sha256(dest) if dest.exists() else None), "missing or differs"
    if dest.exists():
        dest.unlink()
    fetch(name, url, dest, commit)
    got = sha256(dest)
    if want is not None and got != want:
        dest.unlink()
        raise SystemExit(f"SHA-256 MISMATCH for {url}\n  expected {want}\n  got      {got}\n  the file was deleted")
    return got, "downloaded"


def extract_zip(archive, to, strip_top=False):
    """Extract with path-traversal protection. A symlink entry is NEVER created as a link: its target text is written as a regular file (the same
    bytes as the git blob of the link) after checking that the target is relative and stays inside the archive root; the entries are returned."""
    to.mkdir(parents=True, exist_ok=True)
    root = to.resolve()
    symlinks = []
    with zipfile.ZipFile(archive) as z:
        for m in z.infolist():
            name = m.filename
            if strip_top:
                parts = name.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue
                name = parts[1]
            if name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts or ":" in name.split("/")[0]:
                raise SystemExit("unsafe path in archive: " + m.filename)
            target = (to / name).resolve()
            if not str(target).startswith(str(root)):
                raise SystemExit("unsafe path in archive: " + m.filename)
            is_link = ((m.external_attr >> 16) & 0o170000) == 0o120000
            if m.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                data = z.read(m)
                if is_link:
                    dest_txt = data.decode("utf-8", "replace")
                    resolved = (target.parent / dest_txt).resolve()
                    if dest_txt.startswith(("/", "\\")) or not str(resolved).startswith(str(root)):
                        raise SystemExit(f"symlink escapes the archive root: {m.filename} -> {dest_txt}")
                    symlinks.append({"path": name, "target": dest_txt})
                target.write_bytes(data)
    return symlinks


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git_tree_sha1(entries):
    """Root tree object id from (path, mode, sha1hex) entries (blobs and gitlinks); mode strings as git writes them (100644, 100755, 120000, 160000)."""
    def build(items):
        names = {}
        for path, mode, sha in items:
            head, _, rest = path.partition("/")
            names.setdefault(head, []).append((rest, mode, sha))
        out = []
        for head, sub in names.items():
            if len(sub) == 1 and sub[0][0] == "":
                out.append((head, sub[0][1], bytes.fromhex(sub[0][2])))
            else:
                out.append((head, "40000", bytes.fromhex(build(sub))))
        out.sort(key=lambda e: e[0].encode() + (b"/" if e[1] == "40000" else b""))
        body = b"".join(m.encode() + b" " + n.encode() + b"\0" + h for n, m, h in out)
        return hashlib.sha1(b"tree %d\0" % len(body) + body).hexdigest()
    return build(entries)


def tree_sha256_listing(dest, skip_prefixes=()):
    """A SHA-256 over the sorted lines `path<TAB>sha256(content)` of every file below dest (nested pinned submodules excluded)."""
    lines = []
    for p in sorted(q for q in dest.rglob("*") if q.is_file()):
        rel = str(p.relative_to(dest)).replace("\\", "/")
        if any(rel.startswith(sp + "/") for sp in skip_prefixes):
            continue
        lines.append(f"{rel}\t{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest(), len(lines)


def verify_tree(name, s, dest):
    """Compare the extracted tree with the git tree of the commit: same blobs (SHA-1), no extra files. Submodule entries are listed, not expected."""
    parts = urllib.parse.urlparse(s["url"]).path.strip("/").split("/")
    owner, repo = parts[0], parts[1]
    api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{s['commit']}?recursive=1"
    with urllib.request.urlopen(urllib.request.Request(api, headers=dict(UA, Accept="application/vnd.github+json")), timeout=120) as r:
        tree = json.loads(r.read())
    if tree.get("truncated"):
        raise SystemExit(f"{name}: GitHub truncated the tree listing; cannot verify")
    with urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/git/commits/{s['commit']}", headers=dict(UA, Accept="application/vnd.github+json")),
                                timeout=120) as r:
        commit_obj = json.loads(r.read())
    if commit_obj["sha"] != s["commit"]:
        raise SystemExit(f"{name}: the API returned another commit")
    tree["sha"] = commit_obj["tree"]["sha"]          # the commit's root tree object id (the trees endpoint echoes the commit id)
    expected = {t["path"]: t for t in tree["tree"] if t["type"] == "blob"}
    submodules = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "commit"}
    local = {str(p.relative_to(dest)).replace("\\", "/"): p for p in dest.rglob("*") if p.is_file()}
    # files that belong to a nested pinned submodule extracted under this tree are not part of this commit
    nested = [pth for pth in submodules if any(k.startswith(pth + "/") for k in local)]
    mism = [p for p, t in expected.items() if p not in local or git_blob_sha1(local[p].read_bytes()) != t["sha"]]
    extra = [p for p in local if p not in expected and not any(p.startswith(n + "/") for n in nested)]
    # the root tree id recomputed from the LOCAL file contents (modes from the commit's tree, gitlinks as listed) must equal the commit's tree id
    ents = [(p, expected[p]["mode"], git_blob_sha1(local[p].read_bytes())) for p in expected if p in local]
    ents += [(p, "160000", sha) for p, sha in submodules.items()]
    local_root = git_tree_sha1(ents) if not mism else None
    sha256_tree, nfiles = tree_sha256_listing(dest, nested)
    return {"name": name, "repo": f"{owner}/{repo}", "commit": s["commit"], "rootTree": tree["sha"], "localRootTreeRecomputed": local_root,
            "rootTreeEqual": local_root == tree["sha"], "sha256Listing": sha256_tree, "filesHashed": nfiles, "blobsInCommit": len(expected),
            "blobsMatched": len(expected) - len(mism), "mismatchedOrMissing": mism[:50], "extraLocalFiles": extra[:50],
            "submoduleEntriesNotInArchive": submodules, "nestedPinnedSubmodulesExtractedHere": nested,
            "verified": (not mism) and (not extra) and local_root == tree["sha"]}


def main():
    argv = sys.argv[1:]
    offline = "--verify" in argv
    record = "--record" in argv
    trees = "--verify-trees" in argv
    refetch = argv[argv.index("--refetch") + 1] if "--refetch" in argv else None
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    p = plat()
    report = []
    fo = lock["foundry"]["artifacts"][p]
    arch = DL / fo["url"].rsplit("/", 1)[1]
    got, st = ensure("foundry " + lock["foundry"]["version"], fo["url"], arch, fo["sha256"], offline)
    report.append(("foundry " + lock["foundry"]["version"], st, got))
    bindir = HERE / fo["extractTo"]
    if st != "missing or differs" and not (bindir / ("forge.exe" if p.startswith("windows") else "forge")).exists():
        if arch.suffix == ".zip":
            extract_zip(arch, bindir)
        else:
            bindir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(arch) as t:
                t.extractall(bindir, filter="data")
    for ver, spec in lock["solc"]["versions"].items():
        a = spec[p]
        got, st = ensure(f"solc {ver}", a["url"], HERE / "solc" / a["file"], a["sha256"], offline)
        report.append((f"solc {ver}", st, got))
    # sources: extraction order follows the lock (the Permit2 tree before its submodules)
    for name, s in lock["sources"].items():
        if len(s["commit"]) != 40 or any(c not in "0123456789abcdef" for c in s["commit"]):
            raise SystemExit(f"{name}: the commit must be a full 40-character hex hash")
        arch = DL / (name + "-" + s["commit"] + ".zip")
        dests = [(HERE / e).resolve() for e in (s["extractTo"] if isinstance(s["extractTo"], list) else [s["extractTo"]])]
        if refetch == name:
            if arch.exists():
                arch.unlink()
            for d in dests:
                if d.exists():
                    shutil.rmtree(d)
        got, st = ensure(name, s["url"], arch, s["sha256"], offline, s["commit"])
        if s["sha256"] is None:
            if record and not offline:
                s["sha256"] = got
                st += "; sha256 recorded"
            else:
                st += "; sha256 NOT in the lock (run with --record once)"
        for d in dests:
            if st.startswith(("present", "downloaded")) and not (d.exists() and any(q.is_file() for q in d.rglob("*"))):
                links = extract_zip(arch, d, strip_top=True)
                st += f"; extracted to {d.relative_to(HERE.parent).as_posix()}" + (f" ({len(links)} symlink entries written as plain files)" if links else "")
        report.append((name + " " + s["commit"][:10], st, got))
    if (record or refetch) and not offline:
        LOCK.write_text(json.dumps(lock, indent=1) + "\n", encoding="utf-8")
    bad = 0
    for what, st, got in report:
        print(f"{what:44s} {st:55s} sha256 {got}")
        if st.startswith("missing"):
            bad += 1
    if trees:
        results = []
        for name, s in lock["sources"].items():
            for e in (s["extractTo"] if isinstance(s["extractTo"], list) else [s["extractTo"]]):
                dest = (HERE / e).resolve()
                r = verify_tree(name, s, dest)
                r["extractedTo"] = dest.relative_to(HERE.parent).as_posix()
                results.append(r)
        # the submodule path: the pinned parent commit must list a submodule at the path this archive was extracted to, with exactly this commit
        for r in results:
            dest = HERE.parent / r["extractedTo"]
            parents = [(q, HERE.parent / q["extractedTo"]) for q in results if q is not r and str(dest).startswith(str(HERE.parent / q["extractedTo"]) + os.sep)]
            if parents:
                parent, pdir = max(parents, key=lambda x: len(str(x[1])))
                rel = dest.relative_to(pdir).as_posix()
                entry = parent["submoduleEntriesNotInArchive"].get(rel)
                r["submodulePath"] = {"parent": parent["name"], "parentCommit": parent["commit"], "path": rel, "parentEntryCommit": entry, "matches": entry == r["commit"]}
                r["verified"] = r["verified"] and entry == r["commit"]
            else:
                r["submodulePath"] = None
        for r in results:
            sp = r["submodulePath"]
            print(f"tree {r['name']:36s} {r['extractedTo'].replace('toolchain/permit2-build/permit2/', '')[:44]:44s} blobs {r['blobsMatched']}/{r['blobsInCommit']}  extra {len(r['extraLocalFiles'])}  "
                  f"submodule path {'-' if sp is None else ('OK' if sp['matches'] else 'WRONG')}  {'VERIFIED' if r['verified'] else 'NOT VERIFIED'}")
            bad += 0 if r["verified"] else 1
        TREES.write_text(json.dumps({"verifiedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "trees": results},
                                    indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("TOOLCHAIN OK" if not bad else "TOOLCHAIN INCOMPLETE OR NOT VERIFIED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
