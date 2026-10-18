## What and why

<!-- One logical change. Say WHY. Link the issue and the specification section. -->

## Checks I ran

<!-- Paste the result lines, not "passed". -->
- [ ] `python -I scripts/repo_hygiene.py`
- [ ] `python -I scripts/check_docs.py`
- [ ] package tests (`node --test ...`) for what I touched
- [ ] `python -I spec/toolchain/forge.py --project contracts test` (if I touched `contracts/`)
- [ ] `python -I spec/tools/check_all.py` (if I touched `spec/`, `contracts/` or evidence)

## Checklist

- [ ] I did not edit a generated file by hand (EIP-712 outputs, `.env.example`, the configuration table of the README, `spec/18-configuration-records.md`, recorded evidence)
- [ ] I did not rename or remove a protected cryptographic identifier (see "Contributing" in the [README](../README.md))
- [ ] New Solidity files start with `// SPDX-License-Identifier: Apache-2.0`; I added no GPL, AGPL, unlicensed or vendored code, and no dependency (or I added its row to the third-party table of the README)
- [ ] No secret, key, `.env`, binary, archive or build output is included; no file is over 20 MiB
- [ ] I did not claim that a wallet works, a component is audited or a constant is approved without evidence
- [ ] I added or changed a test that fails without this change (or I explain why none applies)
- [ ] The documentation says what is **not** done

## Security

- [ ] This change does not widen what a customer authorizes, weaken a guard, or add a way to move funds other than the router's paths
- [ ] If it touches a `SECURITY-CRITICAL`, `FINANCIAL-CONTROL` or `PRIVACY-CRITICAL` item, I asked for a Security reviewer
