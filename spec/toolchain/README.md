# The pinned toolchain

Everything that compiles or tests the contracts uses **one pinned toolchain**: Foundry v1.8.5, solc 0.8.24 (and 0.8.17 for the Permit2 rebuild), forge-std v1.9.7, and the Permit2 source tree at
commit `cc306b601f172c51bc04334a109e98340456620b` with its submodules. [`toolchain.lock.json`](toolchain.lock.json) records the URL, the commit and the SHA-256 of every artifact, for
Windows and for Linux (amd64).

```bash
python -I spec/toolchain/fetch_toolchain.py            # download what is missing, verify every SHA-256, extract (about 150 MB; needs the network)
python -I spec/toolchain/fetch_toolchain.py --verify   # verify what is on disk; no network; exit 1 on any mismatch
python -I spec/toolchain/forge.py --project contracts test      # run the pinned forge with the pinned solc (refuses to run if the toolchain does not verify)
python -I spec/toolchain/forge.py --tool anvil --help           # the pinned anvil and cast are available the same way
```

## Policy, enforced by the tool

- https only; every redirect target is checked against an allow-list for the kind of artifact (`github.com` and `codeload.github.com` for source archives, GitHub's release hosts for Foundry,
  `binaries.soliditylang.org` for solc). A redirect anywhere else aborts the download.
- The SHA-256 of a download is computed **before** anything is extracted; a mismatch deletes the file and fails.
- Nothing downloaded is executed except the pinned `forge`, `cast`, `anvil` and `solc` binaries, after their hash was verified. No script from any archive is run; archives are only unpacked, with a
  path-traversal check.
- Every fetch is recorded in `fetch-record.json`; `--verify-trees` compares each extracted source archive with the git tree of its commit.
- Foundry's sigstore attestations are **not** verified (that needs a Sigstore client).

## What is tracked and what is not

Tracked: `toolchain.lock.json`, `fetch_toolchain.py`, `forge.py`, `fetch-record.json`, `tree-verification.json`, this file.
**Not tracked** (ignored, re-fetched on demand): `bin/`, `_download/`, `solc/`, `permit2-build/` (Permit2's source tree and its dependencies, some of which are copyleft: see
the "License" section of the [root README](../../README.md#license-third-party-code-and-the-name)) and `isolated/` (the directory of a Permit2 rebuild run). `spec/foundry/lib/forge-std` is written by the fetch and is tracked (MIT OR Apache-2.0).

## Platforms

The lock pins Windows (`windows-amd64`) and Linux (`linux-amd64`) artifacts. The maintainers developed and ran everything on **Windows**. The Linux entries are pinned by hash but the Linux path has
**not been exercised** by the maintainers; the CI jobs that use it are marked advisory until a first green run. macOS is not pinned.
