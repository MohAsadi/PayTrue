# scripts

Standard-library Python; run with `python -I` from the repository root.

| Script | What it does |
|---|---|
| `devnet.py` | Starts the pinned `anvil`, installs Permit2 at its canonical address, deploys the PayTrue contracts with `contracts/script/Deploy.s.sol`, writes and validates a deployment manifest. `--once` stops the chain afterwards. Needs the toolchain fetched; touches no network |
| `validate_deployment.py` | Validates a deployment manifest; refuses a `canonical` one without a protocol-freeze approval and audit references |
| `repo_hygiene.py` | Sizes, forbidden files, secrets (tree, and history with `--history`), SPDX headers, vendored trees, required public files, hosted-domain references, protected cryptographic identifiers, package policy. Settings in `hygiene.config.json`. `--staged` is for a pre-commit hook |
| `test_repo_hygiene.py` | Tests of the checker: it must FAIL on a private key, a token, a secret-like literal, an unmarked dummy, a wrong SPDX header, an oversized file, a key or archive, a vendored tree, a hosted domain in code, a package with a dependency, and a renamed protected identifier |
| `check_docs.py` | Every relative link of the public Markdown files resolves, and every `#anchor` has a heading |

Install the hygiene check as a pre-commit hook (optional):

```bash
printf '#!/bin/sh\nexec python -I scripts/repo_hygiene.py --staged\n' > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

None of these scripts approves anything: they check, they report, and they exit non-zero on a failure.
